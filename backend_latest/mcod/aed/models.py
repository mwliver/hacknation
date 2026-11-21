import uuid

from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import gettext_lazy as _

from mcod.aed.schema import SCHEMA_VERSION

DATA_STANDARD_AED_V1 = SCHEMA_VERSION


class AedValidationReport(models.Model):
    """
    Result of the AED v1 validation of a resource file. The newest report is the current status of the resource.
    Kept separately from ``resources.TaskResult`` so that the meaning of existing validation statuses is unchanged.
    """

    resource = models.ForeignKey(
        "resources.Resource",
        on_delete=models.CASCADE,
        related_name="aed_validation_reports",
        verbose_name=_("Resource"),
    )
    created = models.DateTimeField(auto_now_add=True, verbose_name=_("Created"))
    schema_version = models.CharField(max_length=20, default=SCHEMA_VERSION, verbose_name=_("data standard"))
    file_name = models.CharField(max_length=255, blank=True, verbose_name=_("File"))
    is_compliant = models.BooleanField(default=False, verbose_name=_("compliant with the data standard"))
    rows_count = models.PositiveIntegerField(default=0, verbose_name=_("rows"))
    errors_count = models.PositiveIntegerField(default=0, verbose_name=_("errors"))
    warnings_count = models.PositiveIntegerField(default=0, verbose_name=_("warnings"))
    issues = JSONField(default=list, blank=True, verbose_name=_("issues"))

    class Meta:
        verbose_name = _("AED validation report")
        verbose_name_plural = _("AED validation reports")
        ordering = ("-created", "-id")
        get_latest_by = ("created", "id")

    def __str__(self):
        return f"{self.schema_version} resource={self.resource_id} compliant={self.is_compliant}"

    def summary(self) -> dict:
        return {
            "standard": self.schema_version,
            "zgodny": self.is_compliant,
            "liczba_wierszy": self.rows_count,
            "liczba_bledow": self.errors_count,
            "liczba_ostrzezen": self.warnings_count,
            "data_walidacji": self.created.isoformat() if self.created else None,
        }

    def as_dict(self) -> dict:
        return {**self.summary(), "problemy": self.issues}


class AedRecord(models.Model):
    """
    One AED of the national dataset (after deduplication). Field values of the v1 schema are kept in ``data``
    (the list of fields lives only in mcod/aed/schema/aed_v1.json); columns below are copies used for queries.
    """

    id_aed_krajowe = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data = JSONField(default=dict, verbose_name=_("data"))
    liczba_zrodel = models.PositiveSmallIntegerField(default=1, verbose_name=_("number of sources"))
    miejscowosc = models.CharField(max_length=100, db_index=True, verbose_name=_("locality"))
    kod_teryt_gminy = models.CharField(max_length=7, blank=True, db_index=True, verbose_name=_("TERYT code"))
    status_urzadzenia = models.CharField(max_length=30, db_index=True, verbose_name=_("device status"))
    dostep_publiczny = models.BooleanField(default=False, verbose_name=_("public access"))
    szerokosc_geograficzna = models.FloatField(verbose_name=_("latitude"))
    dlugosc_geograficzna = models.FloatField(verbose_name=_("longitude"))
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("AED (national dataset)")
        verbose_name_plural = _("AEDs (national dataset)")
        ordering = ("miejscowosc", "id_aed_krajowe")

    def __str__(self):
        return f"{self.data.get('nazwa_obiektu', '')} ({self.miejscowosc})"

    def set_data(self, data: dict, sources_count: int) -> None:
        self.data = data
        self.liczba_zrodel = sources_count
        self.miejscowosc = data.get("miejscowosc", "")[:100]
        self.kod_teryt_gminy = data.get("kod_teryt_gminy", "")[:7]
        self.status_urzadzenia = data.get("status_urzadzenia", "")
        self.dostep_publiczny = data.get("dostep_publiczny") == "true"
        self.szerokosc_geograficzna = float(data["szerokosc_geograficzna"])
        self.dlugosc_geograficzna = float(data["dlugosc_geograficzna"])


class AedSourceLink(models.Model):
    """Where a national record comes from: one row per source row merged into the record."""

    aed_record = models.ForeignKey(AedRecord, on_delete=models.CASCADE, related_name="source_links", db_column="id_aed_krajowe")
    dysponent = models.CharField(max_length=300)
    zrodlo_danych = models.CharField(max_length=20)
    zrodlo_id = models.CharField(max_length=100, blank=True)
    id_aed = models.CharField(max_length=100, verbose_name=_("identifier in the source file"))
    resource = models.ForeignKey(
        "resources.Resource", on_delete=models.SET_NULL, null=True, blank=True, related_name="aed_source_links"
    )
    is_primary = models.BooleanField(default=False, verbose_name=_("winning source"))

    class Meta:
        db_table = "aed_source_link"
        verbose_name = _("AED source link")
        verbose_name_plural = _("AED source links")
        ordering = ("-is_primary", "id")
        indexes = [models.Index(fields=["resource", "id_aed"])]
