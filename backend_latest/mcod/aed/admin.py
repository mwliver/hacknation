"""
AED additions to the existing ResourceAdmin (mcod/resources/admin.py calls these helpers).
With AED_ENABLED=False all helpers return nothing, so the resource admin is unchanged.
"""

from django.conf import settings
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from mcod.aed.services import is_aed_resource, latest_report

AED_TAB = "aed"
REPORT_FIELD = "aed_validation_report"
MAX_ISSUES_IN_ADMIN = 200


def resource_fieldsets(fieldsets, obj=None):
    if not settings.AED_ENABLED:
        return fieldsets
    extra = [(None, {"classes": ("suit-tab", "suit-tab-general"), "fields": ("data_standard",)})]
    if obj is not None and is_aed_resource(obj):
        extra.append((None, {"classes": ("suit-tab", f"suit-tab-{AED_TAB}", "full-width"), "fields": (REPORT_FIELD,)}))
    return (*fieldsets, *extra)


def resource_tabs(obj=None):
    if obj is not None and is_aed_resource(obj):
        return [(AED_TAB, _("AED v1 standard"))]
    return []


def resource_readonly_fields(obj=None):
    if not settings.AED_ENABLED or obj is None:
        return ()
    fields = (REPORT_FIELD,)
    if obj.is_imported:
        fields += ("data_standard",)
    return fields


def aed_validation_report(model_admin, obj):
    report = latest_report(obj) if obj and obj.pk else None
    if report is None:
        return _("The file has not been validated against the AED v1 standard yet.")
    status = (
        format_html('<strong style="color:#1b5e20">✔ {}</strong>', _("Compliant with the AED v1 standard"))
        if report.is_compliant
        else format_html('<strong style="color:#b71c1c">✖ {}</strong>', _("Not compliant – errors found"))
    )
    summary = format_html(
        "<p>{status}</p>"
        "<p>{rows_label}: {rows} · {errors_label}: {errors} · {warnings_label}: {warnings} · {date_label}: {date}</p>"
        '<p><a href="{api_url}/aed/reports/{resource_id}" target="_blank" rel="noopener">{link_label}</a></p>',
        status=status,
        rows_label=_("rows"),
        rows=report.rows_count,
        errors_label=_("errors"),
        errors=report.errors_count,
        warnings_label=_("warnings"),
        warnings=report.warnings_count,
        date_label=_("Validation date"),
        date=report.created.strftime("%Y-%m-%d %H:%M"),
        api_url=settings.API_URL,
        resource_id=obj.pk,
        link_label=_("Full report (API)"),
    )
    issues = report.issues[:MAX_ISSUES_IN_ADMIN]
    if not issues:
        return summary
    rows = format_html_join(
        "",
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>",
        ((i.get("poziom"), i.get("wiersz") or "-", i.get("kolumna") or "-", i.get("kod"), i.get("komunikat_pl")) for i in issues),
    )
    table = format_html(
        '<table class="table table-condensed"><thead><tr><th>{}</th><th>{}</th><th>{}</th><th>{}</th><th>{}</th></tr>'
        "</thead><tbody>{}</tbody></table>",
        _("Level"),
        _("Row"),
        _("Column"),
        _("Code"),
        _("Message"),
        rows,
    )
    more = (
        format_html("<p>{}</p>", _("Only the first %(count)s issues are shown.") % {"count": MAX_ISSUES_IN_ADMIN})
        if len(report.issues) > MAX_ISSUES_IN_ADMIN
        else ""
    )
    return format_html("{}{}{}", summary, table, more)


aed_validation_report.short_description = _("AED v1 validation report")
