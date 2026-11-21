"""
Elasticsearch queries for the national AED index.

Readiness (``gotowosc``) depends on the current date, so it is not stored in the index – it is translated into
date range queries relative to "today" (Europe/Warsaw). ``otwarte_teraz`` cannot be expressed in ES and is applied
on the result window in Python (see ``OPEN_NOW_WINDOW``).
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from elasticsearch_dsl import A, Q

from mcod.aed import readiness as rd
from mcod.aed.aggregation import _comparable
from mcod.aed.documents import AedDocument

HIDDEN_STATUSES = ("NIESPRAWNY",)  # never shown on the map / in the API
NEAREST_EXCLUDED_BY_DEFAULT = ("CZASOWO_NIEDOSTEPNY",)
OPEN_NOW_WINDOW = 2000  # max hits filtered by opening hours in Python
EXPIRY_FIELDS = ("data_waznosci_elektrod", "data_waznosci_baterii")

BBox = Tuple[float, float, float, float]  # min_lon, min_lat, max_lon, max_lat


def _missing(field: str) -> Q:
    return ~Q("exists", field=field)


def _not_ready(today: date) -> Q:
    expired = [Q("range", **{f: {"lt": today.isoformat()}}) for f in EXPIRY_FIELDS]
    return Q("bool", should=[~Q("term", status_urzadzenia="SPRAWNY"), *expired], minimum_should_match=1)


def _unknown_condition(today: date) -> Q:
    oldest_inspection = (today - timedelta(days=rd.INSPECTION_MAX_AGE_DAYS)).isoformat()
    return Q(
        "bool",
        should=[
            *[_missing(f) for f in EXPIRY_FIELDS],
            _missing("data_ostatniej_kontroli"),
            Q("range", data_ostatniej_kontroli={"lt": oldest_inspection}),
            ~Q("term", status_weryfikacji="ZWERYFIKOWANY"),
        ],
        minimum_should_match=1,
    )


def _attention_condition(today: date) -> Q:
    limit = (today + timedelta(days=rd.EXPIRY_WARNING_DAYS)).isoformat()
    return Q("bool", should=[Q("range", **{f: {"lte": limit}}) for f in EXPIRY_FIELDS], minimum_should_match=1)


def readiness_query(value: str, today: date) -> Q:
    """The same rules as mcod.aed.readiness.readiness, expressed as an ES query."""
    not_ready, unknown, attention = _not_ready(today), _unknown_condition(today), _attention_condition(today)
    if value == rd.NOT_READY:
        return not_ready
    if value == rd.UNKNOWN:
        return Q("bool", must=[unknown], must_not=[not_ready])
    if value == rd.NEEDS_ATTENTION:
        return Q("bool", must=[attention], must_not=[not_ready, unknown])
    return Q("bool", must_not=[not_ready, unknown, attention])


def parse_bbox(value: str) -> Optional[BBox]:
    try:
        min_lon, min_lat, max_lon, max_lat = (float(v) for v in value.split(","))
    except (ValueError, AttributeError):
        return None
    if not (-180 <= min_lon < max_lon <= 180 and -90 <= min_lat < max_lat <= 90):
        return None
    return min_lon, min_lat, max_lon, max_lat


def base_search(filters: Dict, today: date, exclude_statuses=HIDDEN_STATUSES):
    s = AedDocument.search()
    for status in exclude_statuses:
        s = s.exclude("term", status_urzadzenia=status)
    if filters.get("miejscowosc"):
        s = s.filter("term", miejscowosc_lc=_comparable(filters["miejscowosc"]))
    if filters.get("kod_teryt_gminy"):
        s = s.filter("prefix", kod_teryt_gminy=filters["kod_teryt_gminy"])
    if filters.get("status_urzadzenia"):
        s = s.filter("term", status_urzadzenia=filters["status_urzadzenia"])
    if filters.get("dostep_publiczny") is not None:
        s = s.filter("term", dostep_publiczny=filters["dostep_publiczny"])
    if filters.get("gotowosc"):
        s = s.filter(readiness_query(filters["gotowosc"], today))
    bbox = filters.get("bbox")
    if bbox:
        min_lon, min_lat, max_lon, max_lat = bbox
        s = s.filter(
            "geo_bounding_box",
            location={"top_left": {"lat": max_lat, "lon": min_lon}, "bottom_right": {"lat": min_lat, "lon": max_lon}},
        )
    return s


def ids_from(response) -> List[str]:
    return [hit.meta.id for hit in response]


def clusters_aggregation(s, precision: int):
    agg = A("geohash_grid", field="location", precision=precision, size=2000)
    agg.metric("centroid", "geo_centroid", field="location")
    s.aggs.bucket("klastry", agg)
    return s


def clusters_from(response) -> List[Dict]:
    buckets = getattr(getattr(response, "aggregations", None), "klastry", None)
    if not buckets:
        return []
    return [
        {
            "geohash": b.key,
            "liczba": b.doc_count,
            "lat": b.centroid.location.lat,
            "lon": b.centroid.location.lon,
        }
        for b in buckets.buckets
    ]


def nearest_search(lat: float, lon: float, max_km: float, limit: int, filters: Dict, today: date, include_unavailable: bool):
    excluded = HIDDEN_STATUSES if include_unavailable else HIDDEN_STATUSES + NEAREST_EXCLUDED_BY_DEFAULT
    s = base_search(filters, today, exclude_statuses=excluded)
    s = s.filter("geo_distance", distance=f"{max_km}km", location={"lat": lat, "lon": lon})
    s = s.sort({"_geo_distance": {"location": {"lat": lat, "lon": lon}, "order": "asc", "unit": "m"}})
    return s[:limit]
