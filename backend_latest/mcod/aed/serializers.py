from mcod.core.api import fields
from mcod.core.api.jsonapi.serializers import ObjectAttrs, TopLevel
from mcod.core.api.schemas import ExtSchema


class AedIssueSchema(ExtSchema):
    wiersz = fields.Int(allow_none=True)
    kolumna = fields.Str(allow_none=True)
    kod = fields.Str()
    poziom = fields.Str()
    komunikat_pl = fields.Str()
    komunikat_en = fields.Str()

    class Meta:
        ordered = True


class AedValidationReportAttrs(ObjectAttrs):
    standard = fields.Str()
    zgodny = fields.Bool()
    liczba_wierszy = fields.Int()
    liczba_bledow = fields.Int()
    liczba_ostrzezen = fields.Int()
    data_walidacji = fields.Str(allow_none=True)
    zasob_id = fields.Int(allow_none=True)
    problemy = fields.Nested(AedIssueSchema, many=True)

    class Meta:
        object_type = "aed_validation_report"
        url_template = "{api_url}/aed/reports/{ident}"
        ordered = True


class AedValidationReportApiResponse(TopLevel):
    class Meta:
        attrs_schema = AedValidationReportAttrs


class AedConfigAttrs(ObjectAttrs):
    enabled = fields.Bool()
    campaign_name = fields.Str()
    campaign_slogan = fields.Str()
    campaign_logo_url = fields.Str()
    standard = fields.Str()

    class Meta:
        object_type = "aed_config"
        url_template = "{api_url}/aed/config"
        ordered = True


class AedConfigApiResponse(TopLevel):
    class Meta:
        attrs_schema = AedConfigAttrs
