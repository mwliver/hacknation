from mcod.core.api import fields
from mcod.core.api.jsonapi.serializers import ObjectAttrs, TopLevel, TopLevelMeta
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


# ---------------------------------------------------------------------------------------------------------------
# National AED records. Attribute fields are generated from the v1 schema (single source of truth) – only schema
# fields are ever serialized, so forbidden or unknown columns cannot leak into the API.
# ---------------------------------------------------------------------------------------------------------------


class AedSourceSchema(ExtSchema):
    dysponent = fields.Str()
    zrodlo_danych = fields.Str()
    zrodlo_id = fields.Str()
    id_aed = fields.Str()
    zasob_id = fields.Int(allow_none=True)
    zbior_id = fields.Int(allow_none=True)
    zrodlo_wygrywajace = fields.Bool()

    class Meta:
        ordered = True


def _record_attrs_fields() -> dict:
    from mcod.aed import schema

    attrs = {name: fields.Raw(allow_none=True) for name in schema.all_field_names()}
    attrs.update(
        id_aed_krajowe=fields.Str(),
        liczba_zrodel=fields.Int(),
        gotowosc=fields.Str(),
        otwarte_teraz=fields.Bool(allow_none=True),
        odleglosc_m=fields.Int(allow_none=True),
        zrodla=fields.Nested(AedSourceSchema, many=True),
    )
    return attrs


class _AedRecordMeta:
    object_type = "aed"
    url_template = "{api_url}/aed/{ident}"
    ordered = True


AedRecordAttrs = type("AedRecordAttrs", (ObjectAttrs,), {**_record_attrs_fields(), "Meta": _AedRecordMeta})


class AedClusterSchema(ExtSchema):
    geohash = fields.Str()
    liczba = fields.Int()
    lat = fields.Float()
    lon = fields.Float()


class AedAggregations(ExtSchema):
    klastry = fields.Nested(AedClusterSchema, many=True)


class AedTopLevelMeta(TopLevelMeta):
    """Own meta class: TopLevel mutates ``aggregations`` of the meta schema it gets, so it must not be shared."""


class AedRecordApiResponse(TopLevel):
    class Meta:
        attrs_schema = AedRecordAttrs
        meta_schema = AedTopLevelMeta
        aggs_schema = AedAggregations


class AedStatsAttrs(ObjectAttrs):
    liczba_aed = fields.Int()
    liczba_dysponentow = fields.Int()
    liczba_zrodel_danych = fields.Int()
    odsetek_z_data_waznosci_elektrod = fields.Float()
    gotowosc = fields.Raw()
    data_aktualizacji = fields.Str(allow_none=True)

    class Meta:
        object_type = "aed_stats"
        url_template = "{api_url}/aed/stats"
        ordered = True


class AedStatsApiResponse(TopLevel):
    class Meta:
        attrs_schema = AedStatsAttrs
