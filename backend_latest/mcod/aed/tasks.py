import logging

from django.apps import apps
from django.conf import settings
from sentry_sdk import set_tag

from mcod.core.tasks import extended_shared_task

logger = logging.getLogger("mcod")


@extended_shared_task(ignore_result=False, name="mcod.aed.tasks.validate_aed_resource_task")
def validate_aed_resource_task(resource_id: int):
    """Validates the file of a resource marked as AED v1 (queue: resources)."""
    from mcod.aed.services import is_aed_resource, validate_resource

    set_tag("resource_id", str(resource_id))
    Resource = apps.get_model("resources", "Resource")
    resource = Resource.raw.filter(pk=resource_id).first()
    if not is_aed_resource(resource):
        logger.info("validate_aed_resource_task: resource %s is not an AED v1 resource – skipped", resource_id)
        return {"resource_id": resource_id, "skipped": True}
    report = validate_resource(resource)
    resource.update_es_and_rdf_db()  # refresh aed_validation in the search index
    return {"resource_id": resource_id, "report_id": report.pk, "is_compliant": report.is_compliant}


def schedule_aed_validation(resource) -> bool:
    """
    Called from the resource file validation pipeline (with a resource or its id). Schedules AED validation only
    when the feature is enabled and the resource is marked as AED v1 – other resources are not affected.
    """
    if not settings.AED_ENABLED:
        return False
    if isinstance(resource, int):
        resource = apps.get_model("resources", "Resource").raw.filter(pk=resource).first()
    if getattr(resource, "data_standard", None) != "AED_V1":
        return False
    validate_aed_resource_task.apply_async_on_commit(args=(resource.pk,))
    return True


@extended_shared_task(ignore_result=False, name="mcod.aed.tasks.build_aed_national_dataset_task")
def build_aed_national_dataset_task():
    """Periodic (django_celery_beat) build of the national AED dataset; no-op when AED_ENABLED is False."""
    if not settings.AED_ENABLED:
        return {"skipped": True}
    from mcod.aed.national import build_national_dataset

    return build_national_dataset().as_dict()
