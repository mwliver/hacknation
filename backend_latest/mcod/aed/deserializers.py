import marshmallow as ma
from django.utils.translation import gettext_lazy as _

from mcod.aed import schema
from mcod.aed.readiness import READINESS_VALUES
from mcod.aed.search import parse_bbox
from mcod.core.api.schemas import ListingSchema


class BBoxField(ma.fields.Str):
    def _deserialize(self, value, attr, data, **kwargs):
        bbox = parse_bbox(super()._deserialize(value, attr, data, **kwargs))
        if bbox is None:
            raise ma.ValidationError(_("bbox must be: min_lon,min_lat,max_lon,max_lat"))
        return bbox


class _AedFilters(ma.Schema):
    dostep_publiczny = ma.fields.Bool()
    otwarte_teraz = ma.fields.Bool()
    gotowosc = ma.fields.Str(validate=ma.validate.OneOf(READINESS_VALUES))


class AedListRequest(ListingSchema, _AedFilters):
    miejscowosc = ma.fields.Str(validate=ma.validate.Length(max=100))
    kod_teryt_gminy = ma.fields.Str(validate=ma.validate.Regexp(r"^\d{1,7}$"))
    status_urzadzenia = ma.fields.Str(validate=ma.validate.OneOf(schema.enums()["status_urzadzenia"]))
    bbox = BBoxField()
    klastry = ma.fields.Bool(missing=False)
    precyzja = ma.fields.Int(missing=5, validate=ma.validate.Range(1, 12))

    class Meta:
        strict = True
        ordered = True


class AedNearestRequest(_AedFilters):
    lat = ma.fields.Float(required=True, validate=ma.validate.Range(-90, 90))
    lon = ma.fields.Float(required=True, validate=ma.validate.Range(-180, 180))
    limit = ma.fields.Int(missing=5, validate=ma.validate.Range(1, 50))
    max_km = ma.fields.Float(missing=2.0, validate=ma.validate.Range(0.01, 50))
    include_unavailable = ma.fields.Bool(missing=False)

    class Meta:
        strict = True
        ordered = True
