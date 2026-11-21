"""Glue between the pure AED modules and portal models (resources, datasets, tags)."""

import logging
import os
from typing import Optional

from django.conf import settings
from django.db import transaction

from mcod.aed.models import DATA_STANDARD_AED_V1, AedValidationReport
from mcod.aed.validation import ValidationReport, validate_file

logger = logging.getLogger("mcod")

AED_TAG_NAMES = {"pl": "AED", "en": "AED"}


def is_aed_resource(resource) -> bool:
    return bool(settings.AED_ENABLED and resource is not None and resource.data_standard == DATA_STANDARD_AED_V1)


def latest_report(resource) -> Optional[AedValidationReport]:
    return AedValidationReport.objects.filter(resource_id=resource.pk).first()


def report_summary(resource) -> Optional[dict]:
    """Short validation status of an AED resource for API/ES; None for other resources."""
    if not is_aed_resource(resource):
        return None
    report = latest_report(resource)
    return report.summary() if report else {"standard": DATA_STANDARD_AED_V1, "zgodny": None}


def _read_resource_file(resource) -> Optional[tuple]:
    main_file = resource.main_file
    if not main_file:
        return None
    path = main_file.path
    max_size = settings.AED_RESOURCE_MAX_FILE_SIZE
    if os.path.getsize(path) > max_size:
        return os.path.basename(path), None
    with open(path, "rb") as f:
        return os.path.basename(path), f.read()


def validate_resource(resource) -> AedValidationReport:
    """Validates the main file of the resource and stores a new report."""
    file_info = _read_resource_file(resource)
    if file_info is None:
        report = ValidationReport()
        report.add("UNSUPPORTED_FILE")
        file_name = ""
    elif file_info[1] is None:
        report = ValidationReport()
        report.add("FILE_TOO_LARGE", limit_mb=settings.AED_RESOURCE_MAX_FILE_SIZE // (1024 * 1024))
        file_name = file_info[0]
    else:
        file_name, content = file_info
        report = validate_file(content, file_name)
    stored = AedValidationReport.objects.create(
        resource_id=resource.pk,
        schema_version=report.schema_version,
        file_name=file_name[:255],
        is_compliant=report.is_compliant,
        rows_count=report.rows,
        errors_count=report.errors_count,
        warnings_count=report.warnings_count,
        issues=[i.as_dict() for i in report.issues],
    )
    logger.info(
        "AED resource %s validated: compliant=%s errors=%s warnings=%s",
        resource.pk,
        stored.is_compliant,
        stored.errors_count,
        stored.warnings_count,
    )
    return stored


def ensure_aed_tags(dataset) -> None:
    """Adds the portal tags "AED" (pl and en) to the dataset, so AED datasets can be found with the tag filter."""
    from mcod.tags.models import Tag

    if dataset is None:
        return
    with transaction.atomic():
        for language, name in AED_TAG_NAMES.items():
            tag, _ = Tag.objects.get_or_create(name=name, language=language, defaults={"status": "published"})
            if not dataset.tags.filter(pk=tag.pk).exists():
                dataset.tags.add(tag)
