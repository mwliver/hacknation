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
