import json
import logging
from types import SimpleNamespace

import falcon
from django.apps import apps
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from werkzeug.utils import secure_filename

from mcod.aed import export, schema
from mcod.aed.serializers import AedConfigApiResponse, AedValidationReportApiResponse
from mcod.aed.services import is_aed_resource, latest_report
from mcod.aed.validation import validate_file
from mcod.core.api.handlers import BaseHdlr
from mcod.core.api.limiter import rate_limiter
from mcod.core.api.views import JsonAPIView
from mcod.core.versioning import versioned

logger = logging.getLogger("mcod-api")

ALLOWED_EXTENSIONS = ("csv", "xlsx")
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def client_ip_key(req: falcon.Request) -> str:
    return (req.access_route[0] if req.access_route else req.remote_addr) or "unknown"


class AedSchemaView:
    """GET /aed/schema – AED v1 Table Schema (plain JSON, the same file as mcod/aed/schema/aed_v1.json)."""

    def on_get(self, request, response, *args, **kwargs):
        response.content_type = "application/json"
        response.text = json.dumps(schema.load_schema(), ensure_ascii=False)


class AedTemplateView:
    """GET /aed/template.csv, /aed/template.xlsx – templates generated from the schema."""

    def __init__(self, file_format: str):
        self.file_format = file_format

    def on_get(self, request, response, *args, **kwargs):
        with_examples = request.get_param_as_bool("przyklady", default=False)
        if self.file_format == "csv":
            response.content_type = "text/csv; charset=utf-8"
            response.data = export.build_csv(with_examples=with_examples)
        else:
            response.content_type = XLSX_MIME
            response.data = export.build_xlsx(with_examples=with_examples)
        response.downloadable_as = f"szablon_AED_v1.{self.file_format}"


class AedValidateView(JsonAPIView):
    """
    POST /aed/validate – checks a CSV/XLSX file against the AED v1 standard **without publishing anything**.
    The file is processed in memory only and discarded after validation; nothing is stored in the database.
    """

    @versioned
    @rate_limiter(limits=settings.AED_VALIDATE_RATE_LIMITS, key_gen=client_ip_key)
    def on_post(self, request, response, *args, **kwargs):
        self.handle(request, response, self.POST, *args, **kwargs)

    class POST(BaseHdlr):
        serializer_schema = AedValidationReportApiResponse

        def clean(self, *args, **kwargs):
            if "multipart/form-data" not in (self.request.content_type or ""):
                raise falcon.HTTPUnsupportedMediaType(description=_("Send the file as multipart/form-data in the 'file' field."))
            max_size = settings.AED_VALIDATE_MAX_FILE_SIZE
            if self.request.content_length and self.request.content_length > max_size + 64 * 1024:
                raise falcon.HTTPPayloadTooLarge(description=_("The file is too large."))
            for part in self.request.get_media():
                if part.name != "file":
                    continue
                filename = secure_filename(part.filename or "")
                ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
                if ext not in ALLOWED_EXTENSIONS:
                    raise falcon.HTTPUnprocessableEntity(description=_("Allowed file types: CSV, XLSX."))
                content = self._read(part, max_size)
                return {"filename": filename, "content": content}
            raise falcon.HTTPUnprocessableEntity(description=_("Missing 'file' field."))

        @staticmethod
        def _read(part, max_size: int) -> bytes:
            data = bytearray()
            while True:
                chunk = part.stream.read(64 * 1024)
                if not chunk:
                    break
                data.extend(chunk)
                if len(data) > max_size:
                    raise falcon.HTTPPayloadTooLarge(description=_("The file is too large."))
            return bytes(data)

        def _get_data(self, cleaned, *args, **kwargs):
            report = validate_file(cleaned["content"], cleaned["filename"])
            cleaned.clear()  # drop file content from the request context
            data = report.as_dict()
            return SimpleNamespace(id="validation", zasob_id=None, data_walidacji=None, **data)


class AedResourceReportView(JsonAPIView):
    """GET /aed/reports/{resource_id} – the newest AED v1 validation report of a published resource."""

    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(BaseHdlr):
        serializer_schema = AedValidationReportApiResponse

        def clean(self, id, *args, **kwargs):
            return {}

        def _get_data(self, cleaned, id, *args, **kwargs):
            Resource = apps.get_model("resources", "Resource")
            resource = Resource.objects.filter(pk=id, status="published").first()
            report = latest_report(resource) if is_aed_resource(resource) else None
            if report is None:
                raise falcon.HTTPNotFound()
            return SimpleNamespace(id=resource.pk, zasob_id=resource.pk, **report.as_dict())


class AedConfigView(JsonAPIView):
    """GET /aed/config – campaign settings for the frontend; the route exists only when AED_ENABLED."""

    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(BaseHdlr):
        serializer_schema = AedConfigApiResponse

        def _get_data(self, cleaned, *args, **kwargs):
            return SimpleNamespace(
                id="aed",
                enabled=settings.AED_ENABLED,
                campaign_name=settings.AED_CAMPAIGN_NAME,
                campaign_slogan=settings.AED_CAMPAIGN_SLOGAN,
                campaign_logo_url=settings.AED_CAMPAIGN_LOGO_URL,
                standard=schema.SCHEMA_VERSION,
            )
