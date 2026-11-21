"""
Building the national AED dataset from all AED v1 resources of all data providers.

1. collect rows of every published AED v1 resource whose newest validation report has no ERRORs,
2. normalise, deduplicate and merge them (mcod.aed.aggregation),
3. store AedRecord + AedSourceLink (national ids stay stable between builds),
4. index records in Elasticsearch (index "aed"),
5. publish the result as an ordinary portal dataset with three resources (CSV, GeoJSON, source links CSV).
"""

import csv
import io
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from django.apps import apps
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.utils import timezone

from mcod.aed import schema
from mcod.aed.aggregation import SourceRow, aggregate
from mcod.aed.models import DATA_STANDARD_AED_V1, AedRecord, AedSourceLink
from mcod.aed.services import AED_TAG_NAMES, latest_report
from mcod.aed.validation import validate_file

logger = logging.getLogger("mcod")

NATIONAL_DATASET_TITLE = "Defibrylatory AED w Polsce – zbiór krajowy"
NATIONAL_DATASET_TITLE_EN = "AED defibrillators in Poland – national dataset"
NATIONAL_DATASET_NOTES = (
    "Ogólnopolski zbiór danych o automatycznych defibrylatorach zewnętrznych (AED), budowany automatycznie "
    "codziennie z zasobów wszystkich dostawców oznaczonych jako zgodne ze standardem AED v1 (wzorcowy zakres danych). "
    "Rekordy z wielu źródeł są deduplikowane; zasób „aed_powiazania_zrodel.csv” wskazuje źródło każdego rekordu. "
    "Gotowość urządzenia nie jest polem pliku – wylicza ją API portalu (/aed) w chwili zapytania. "
    "W nagłym zatrzymaniu krążenia najpierw dzwoń 112."
)
NATIONAL_DATASET_NOTES_EN = (
    "Nationwide dataset of automated external defibrillators (AED), built automatically every day from the resources "
    "of all data providers marked as compliant with the AED v1 standard. Records from many sources are deduplicated; "
    'the resource "aed_powiazania_zrodel.csv" shows the source of every record. Device readiness is not a file field – '
    "it is computed by the portal API (/aed). In a cardiac arrest call 112 first."
)
HEALTH_CATEGORY_CODE = "HEAL"
EXTRA_TAGS = {"pl": ["defibrylator", "pierwsza pomoc"], "en": ["defibrillator", "first aid"]}

CSV_COLUMNS_PREFIX = ["id_aed_krajowe"]
CSV_COLUMNS_SUFFIX = ["liczba_zrodel"]
LINK_COLUMNS = ["id_aed_krajowe", "dysponent", "zrodlo_danych", "zrodlo_id", "id_aed", "resource_id", "zrodlo_wygrywajace"]

RESOURCE_CSV = "aed_krajowy.csv"
RESOURCE_GEOJSON = "aed_krajowy.geojson"
RESOURCE_LINKS = "aed_powiazania_zrodel.csv"
RESOURCES = {
    RESOURCE_CSV: ("Defibrylatory AED – zbiór krajowy (CSV)", "text/csv"),
    RESOURCE_GEOJSON: ("Defibrylatory AED – zbiór krajowy (GeoJSON)", "application/geo+json"),
    RESOURCE_LINKS: ("Powiązania rekordów krajowych ze źródłami danych (CSV)", "text/csv"),
}


@dataclass
class BuildResult:
    sources: List[int] = field(default_factory=list)
    skipped_sources: List[int] = field(default_factory=list)
    rows: int = 0
    records: int = 0
    removed: int = 0
    dataset_id: Optional[int] = None

    def as_dict(self) -> dict:
        return {
            "sources": len(self.sources),
            "skipped_sources": len(self.skipped_sources),
            "rows": self.rows,
            "records": self.records,
            "removed": self.removed,
            "dataset_id": self.dataset_id,
        }


# ---------------------------------------------------------------------------------------------------------------
# 1. Sources
# ---------------------------------------------------------------------------------------------------------------


def national_dataset():
    Dataset = apps.get_model("datasets", "Dataset")
    org_id = settings.AED_NATIONAL_ORGANIZATION_ID
    if not org_id:
        return None
    return Dataset.objects.filter(organization_id=org_id, title=NATIONAL_DATASET_TITLE).order_by("id").first()


def source_resources():
    Resource = apps.get_model("resources", "Resource")
    queryset = Resource.objects.filter(
        data_standard=DATA_STANDARD_AED_V1, status="published", dataset__status="published"
    ).select_related("dataset")
    own = national_dataset()
    return queryset.exclude(dataset_id=own.pk) if own else queryset


def collect_rows(resources: Iterable, result: BuildResult) -> List[SourceRow]:
    rows: List[SourceRow] = []
    for resource in resources:
        report = latest_report(resource)
        if report is None or not report.is_compliant or not resource.main_file:
            result.skipped_sources.append(resource.pk)
            continue
        with open(resource.main_file.path, "rb") as f:
            validation = validate_file(f.read(), resource.main_file.name)
        if not validation.is_compliant:  # file changed after the stored report
            result.skipped_sources.append(resource.pk)
            continue
        result.sources.append(resource.pk)
        rows.extend(SourceRow(resource.pk, data) for _, data in validation.records)
    result.rows = len(rows)
    return rows


# ---------------------------------------------------------------------------------------------------------------
# 2–3. Records
# ---------------------------------------------------------------------------------------------------------------


def _existing_ids() -> Dict[Tuple[Optional[int], str], uuid.UUID]:
    return {(link.resource_id, link.id_aed): link.aed_record_id for link in AedSourceLink.objects.all()}


def store_records(rows: List[SourceRow]) -> Tuple[List[AedRecord], List[str]]:
    """Replaces national records with the aggregation of ``rows``. Returns (records, removed record ids)."""
    merged = aggregate(rows)
    existing = _existing_ids()
    used = set()
    records, links = [], []
    for item in merged:
        candidates = [existing.get((r.resource_id, r.data["id_aed"])) for r in item.rows]
        record_id = next((c for c in candidates if c and c not in used), None) or uuid.uuid4()
        used.add(record_id)
        record = AedRecord(id_aed_krajowe=record_id)
        record.set_data(item.data, item.sources_count)
        records.append(record)
        for position, row in enumerate(item.rows):
            links.append(
                AedSourceLink(
                    aed_record_id=record_id,
                    dysponent=row.data.get("dysponent", "")[:300],
                    zrodlo_danych=row.data.get("zrodlo_danych", ""),
                    zrodlo_id=row.data.get("zrodlo_id", "")[:100],
                    id_aed=row.data.get("id_aed", "")[:100],
                    resource_id=row.resource_id,
                    is_primary=position == 0,
                )
            )
    with transaction.atomic():
        removed = [str(pk) for pk in AedRecord.objects.exclude(pk__in=used).values_list("pk", flat=True)]
        AedSourceLink.objects.all().delete()
        AedRecord.objects.filter(pk__in=removed).delete()
        existing_records = {r.pk: r for r in AedRecord.objects.filter(pk__in=used)}
        to_create = [r for r in records if r.pk not in existing_records]
        to_update = []
        for record in records:
            if record.pk in existing_records:
                current = existing_records[record.pk]
                current.set_data(record.data, record.liczba_zrodel)
                current.modified = timezone.now()
                to_update.append(current)
        AedRecord.objects.bulk_create(to_create, batch_size=1000)
        update_fields = [
            "data",
            "liczba_zrodel",
            "miejscowosc",
            "kod_teryt_gminy",
            "status_urzadzenia",
            "dostep_publiczny",
            "szerokosc_geograficzna",
            "dlugosc_geograficzna",
            "modified",
        ]
        AedRecord.objects.bulk_update(to_update, update_fields, batch_size=1000)
        AedSourceLink.objects.bulk_create(links, batch_size=1000)
    return list(AedRecord.objects.all()), removed


# ---------------------------------------------------------------------------------------------------------------
# 4. Files
# ---------------------------------------------------------------------------------------------------------------


def csv_columns() -> List[str]:
    return CSV_COLUMNS_PREFIX + schema.all_field_names() + CSV_COLUMNS_SUFFIX


def record_row(record: AedRecord) -> Dict[str, str]:
    row = {name: record.data.get(name, "") for name in schema.all_field_names()}
    row.update(id_aed_krajowe=str(record.pk), liczba_zrodel=str(record.liczba_zrodel))
    return row


def build_csv(records: Iterable[AedRecord]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=csv_columns(), lineterminator="\n")
    writer.writeheader()
    for record in records:
        writer.writerow(record_row(record))
    return buffer.getvalue().encode("utf-8")


def typed_value(name: str, value: str):
    f = schema.field(name)
    if value == "" or f is None:
        return value if f is None else None
    if f["type"] == "number":
        return float(value)
    if f["type"] == "integer":
        return int(value)
    if f["type"] == "boolean":
        return value == "true"
    return value


def build_geojson(records: Iterable[AedRecord]) -> bytes:
    features = []
    for record in records:
        properties = {name: typed_value(name, value) for name, value in record_row(record).items()}
        properties["liczba_zrodel"] = record.liczba_zrodel
        features.append(
            {
                "type": "Feature",
                "id": str(record.pk),
                "geometry": {"type": "Point", "coordinates": [record.dlugosc_geograficzna, record.szerokosc_geograficzna]},
                "properties": properties,
            }
        )
    collection = {"type": "FeatureCollection", "features": features}
    return json.dumps(collection, ensure_ascii=False).encode("utf-8")


def build_links_csv(links: Iterable[AedSourceLink]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(LINK_COLUMNS)
    for link in links:
        writer.writerow(
            [
                str(link.aed_record_id),
                link.dysponent,
                link.zrodlo_danych,
                link.zrodlo_id,
                link.id_aed,
                link.resource_id or "",
                "true" if link.is_primary else "false",
            ]
        )
    return buffer.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------------------------------------------
# 5. Publication as a portal dataset
# ---------------------------------------------------------------------------------------------------------------


def _national_tags():
    Tag = apps.get_model("tags", "Tag")
    tags = []
    for language, base_name in AED_TAG_NAMES.items():
        for name in [base_name] + EXTRA_TAGS[language]:
            tag, _ = Tag.objects.get_or_create(name=name, language=language, defaults={"status": "published"})
            tags.append(tag)
    return tags


def get_or_create_national_dataset():
    Dataset = apps.get_model("datasets", "Dataset")
    Category = apps.get_model("categories", "Category")
    dataset = national_dataset()
    if dataset is not None:
        return dataset
    dataset = Dataset.objects.create(
        title=NATIONAL_DATASET_TITLE,
        title_en=NATIONAL_DATASET_TITLE_EN,
        notes=NATIONAL_DATASET_NOTES,
        notes_en=NATIONAL_DATASET_NOTES_EN,
        organization_id=settings.AED_NATIONAL_ORGANIZATION_ID,
        license_chosen=Dataset.LICENSE_CC_BY,
        update_frequency="daily",
        has_dynamic_data=False,
        has_high_value_data=False,
        has_high_value_data_from_ec_list=False,
        has_research_data=False,
        status="published",
    )
    dataset.categories.set(Category.objects.filter(code=HEALTH_CATEGORY_CODE))
    dataset.tags.set(_national_tags())
    dataset.save()
    logger.info("Created national AED dataset %s", dataset.pk)
    return dataset


def _publish_file(dataset, file_name: str, content: bytes) -> None:
    """Creates the resource or replaces its main file – a new main ResourceFile runs the regular pipeline."""
    Resource = apps.get_model("resources", "Resource")
    ResourceFile = apps.get_model("resources", "ResourceFile")
    title, mimetype = RESOURCES[file_name]
    resource = Resource.objects.filter(dataset=dataset, title=title).order_by("id").first()
    if resource is None:
        resource = Resource.objects.create(
            title=title,
            description=NATIONAL_DATASET_NOTES,
            dataset=dataset,
            has_dynamic_data=False,
            has_high_value_data=False,
            has_high_value_data_from_ec_list=False,
            has_research_data=False,
            contains_protected_data=False,
            status="published",
            data_date=timezone.localdate(),
        )
    else:
        Resource.raw.filter(pk=resource.pk).update(data_date=timezone.localdate())
        ResourceFile.objects.filter(resource=resource, is_main=True).delete()
    ResourceFile.objects.create(
        resource=resource,
        is_main=True,
        file=SimpleUploadedFile(name=file_name, content=content, content_type=mimetype),
    )


def publish(records: List[AedRecord]) -> Optional[int]:
    if not settings.AED_NATIONAL_ORGANIZATION_ID:
        logger.warning("AED_NATIONAL_ORGANIZATION_ID is not set – national AED dataset is not published")
        return None
    links = AedSourceLink.objects.order_by("aed_record_id", "-is_primary", "id")
    with transaction.atomic():
        dataset = get_or_create_national_dataset()
        _publish_file(dataset, RESOURCE_CSV, build_csv(records))
        _publish_file(dataset, RESOURCE_GEOJSON, build_geojson(records))
        _publish_file(dataset, RESOURCE_LINKS, build_links_csv(links))
    return dataset.pk


# ---------------------------------------------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------------------------------------------


def index_records(records: List[AedRecord], removed: List[str]) -> None:
    from mcod.aed.documents import AedDocument

    document = AedDocument()
    if removed:
        document.search().filter("ids", values=removed).delete()
    if records:
        document.update(records, refresh=True)


def build_national_dataset(publish_dataset: bool = True, index: bool = True) -> BuildResult:
    result = BuildResult()
    rows = collect_rows(source_resources(), result)
    records, removed = store_records(rows)
    result.records, result.removed = len(records), len(removed)
    if index:
        index_records(records, removed)
    if publish_dataset:
        result.dataset_id = publish(records)
    logger.info("National AED dataset built: %s", result.as_dict())
    return result
