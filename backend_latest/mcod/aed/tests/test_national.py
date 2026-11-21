import csv
import io
import json
from datetime import date, datetime

import falcon
import pytest
import pytz
from django.test import override_settings

from mcod.aed import national, schema
from mcod.aed.management.commands.aed_demo_data import (
    PROVIDERS,
    create_provider_resource,
    get_or_create_organization,
)
from mcod.aed.models import AedRecord, AedSourceLink
from mcod.aed.services import validate_resource
from mcod.resources.models import Resource

TODAY = date(2026, 11, 21)
MONDAY_10 = pytz.timezone("Europe/Warsaw").localize(datetime(2026, 11, 23, 10, 0))
OTWOCK_STATION = (52.10500, 21.26000)
FORBIDDEN_VALUES = ("SEKRET-4321",)

pytestmark = pytest.mark.elasticsearch


@pytest.fixture
def frozen_today(mocker):
    mocker.patch("mcod.aed.validation.timezone.localdate", return_value=TODAY)
    mocker.patch("mcod.aed.record_views._now", return_value=(TODAY, MONDAY_10))


@pytest.fixture
def providers(frozen_today, mocker):
    mocker.patch("mcod.aed.tasks.validate_aed_resource_task.apply_async_on_commit")
    national_org = get_or_create_organization("Krajowy rejestr AED (prototyp)", "krajowy-rejestr-aed-prototyp", "state")
    resources = []
    for file_name, title, slug, institution_type in PROVIDERS:
        resource = create_provider_resource(get_or_create_organization(title, slug, institution_type), file_name)
        assert validate_resource(resource).is_compliant
        resources.append(resource)
    with override_settings(AED_NATIONAL_ORGANIZATION_ID=national_org.pk):
        yield resources


@pytest.fixture
def built(providers):
    return national.build_national_dataset()


def _by_source(source_id_aed: str) -> AedRecord:
    return AedSourceLink.objects.get(id_aed=source_id_aed).aed_record


# ---------------------------------------------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------------------------------------------


def test_three_providers_give_one_dataset_without_duplicates(built, providers):
    assert built.as_dict()["sources"] == 3
    assert built.rows == 13
    assert built.records == 10
    assert AedSourceLink.objects.count() == 13
    # duplicates merged with the right winner
    station = _by_source("OTW-001")
    assert _by_source("OSM-OTW-1") == station
    assert station.liczba_zrodel == 2 and station.data["zrodlo_danych"] == "JST"
    assert station.data["producent"] == "Producent Testowy"  # filled from OSM
    clinic = _by_source("PRZ-001")
    assert _by_source("WAW-JST-1") == clinic and clinic.data["zrodlo_danych"] == "WLASCICIEL"
    assert clinic.data["kod_pocztowy"] == "00-001"  # normalized
    assert _by_source("PRZ-OSM") == _by_source("OSM-WAW-2")  # same OSM node
    assert _by_source("OSM-KRK-1") != _by_source("OSM-KRK-2")  # 40 m apart, the same file


def test_rebuild_keeps_national_ids(built, providers):
    before = {link.id_aed: link.aed_record_id for link in AedSourceLink.objects.all()}
    result = national.build_national_dataset()
    after = {link.id_aed: link.aed_record_id for link in AedSourceLink.objects.all()}
    assert result.records == 10 and before == after


def test_noncompliant_resource_is_skipped(providers):
    Resource.raw.filter(pk=providers[2].pk).update(data_standard=None)
    result = national.build_national_dataset(publish_dataset=False)
    assert result.records == 7  # 4 + 4 - 1 duplicate


def test_published_dataset_and_files(built):
    dataset = national.national_dataset()
    assert dataset.pk == built.dataset_id
    assert dataset.status == "published" and dataset.license_chosen == dataset.LICENSE_CC_BY
    assert dataset.update_frequency == "daily"
    assert set(dataset.tags.values_list("name", flat=True)) >= {"AED", "defibrylator"}
    titles = set(Resource.objects.filter(dataset=dataset).values_list("title", flat=True))
    assert titles == {title for title, _ in national.RESOURCES.values()}


def test_csv_geojson_and_links_files(built):
    records = list(AedRecord.objects.all())
    rows = list(csv.DictReader(io.StringIO(national.build_csv(records).decode("utf-8"))))
    assert len(rows) == 10
    assert list(rows[0]) == ["id_aed_krajowe"] + schema.all_field_names() + ["liczba_zrodel"]
    geojson = json.loads(national.build_geojson(records))
    assert geojson["type"] == "FeatureCollection" and len(geojson["features"]) == 10
    feature = geojson["features"][0]
    assert feature["geometry"]["type"] == "Point" and len(feature["geometry"]["coordinates"]) == 2
    assert isinstance(feature["properties"]["dostep_publiczny"], bool)
    links = list(csv.reader(io.StringIO(national.build_links_csv(AedSourceLink.objects.all()).decode())))
    assert links[0] == national.LINK_COLUMNS and len(links) == 14


# ---------------------------------------------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------------------------------------------


def _attrs(resp):
    return [item["attributes"] for item in resp.json["data"]]


def test_nearest_sorted_by_distance(client14, built):
    lat, lon = OTWOCK_STATION
    resp = client14.simulate_get("/1.4/aed/nearest", params={"lat": lat, "lon": lon, "limit": 5, "max_km": 5})
    assert resp.status == falcon.HTTP_200, resp.text
    items = _attrs(resp)
    distances = [i["odleglosc_m"] for i in items]
    assert distances == sorted(distances) and distances[0] < 5
    assert items[0]["nazwa_obiektu"] == "Dworzec Testowy Otwock"
    assert all(i["miejscowosc"] == "Otwock" for i in items)
    assert {i["gotowosc"] for i in items} <= {"GOTOWY", "WYMAGA_UWAGI", "NIEZNANY", "NIEGOTOWY"}
    assert all("otwarte_teraz" in i for i in items)


def test_nearest_limit_and_unavailable(client14, built):
    params = {"lat": 52.2297, "lon": 21.0122, "limit": 10, "max_km": 10}
    names = {i["nazwa_obiektu"] for i in _attrs(client14.simulate_get("/1.4/aed/nearest", params=params))}
    assert "Przychodnia Testowa nr 2" not in names  # CZASOWO_NIEDOSTEPNY skipped by default
    assert "Biurowiec Testowy" not in names  # NIESPRAWNY always hidden
    with_unavailable = client14.simulate_get("/1.4/aed/nearest", params={**params, "include_unavailable": "true"})
    names = {i["nazwa_obiektu"] for i in _attrs(with_unavailable)}
    assert "Przychodnia Testowa nr 2" in names and "Biurowiec Testowy" not in names
    one = client14.simulate_get("/1.4/aed/nearest", params={**params, "limit": 1})
    assert len(one.json["data"]) == 1


def test_nearest_validation(client14, built):
    assert client14.simulate_get("/1.4/aed/nearest", params={"lat": 52}).status == falcon.HTTP_422
    assert client14.simulate_get("/1.4/aed/nearest", params={"lat": 52, "lon": 21, "limit": 500}).status == falcon.HTTP_422


def test_list_and_filters(client14, built):
    resp = client14.simulate_get("/1.4/aed", params={"per_page": 3})
    assert resp.status == falcon.HTTP_200, resp.text
    assert resp.json["meta"]["count"] == 9  # NIESPRAWNY hidden
    assert len(resp.json["data"]) == 3 and "next" in resp.json["links"]

    def count(**params):
        return client14.simulate_get("/1.4/aed", params=params).json["meta"]["count"]

    assert count(miejscowosc="krakow") == 3
    assert count(kod_teryt_gminy="1417") == 3
    assert count(status_urzadzenia="CZASOWO_NIEDOSTEPNY") == 1
    assert count(dostep_publiczny="false") == 1
    assert count(bbox="19.9,50.0,20.0,50.1") == 3
    assert count(gotowosc="WYMAGA_UWAGI") == 1  # OTW-003, electrodes expire in 19 days
    assert count(gotowosc="NIEGOTOWY") == 1  # CZASOWO_NIEDOSTEPNY
    assert count(gotowosc="GOTOWY") + count(gotowosc="NIEZNANY") + 2 == 9
    # Monday 10:00 – everything is open except "sunrise-sunset" (unknown)
    assert count(otwarte_teraz="true") == 8
    assert count(otwarte_teraz="false") == 0


def test_list_clusters(client14, built):
    resp = client14.simulate_get("/1.4/aed", params={"klastry": "true", "precyzja": 3, "per_page": 1})
    clusters = resp.json["meta"]["aggregations"]["klastry"]
    assert sum(c["liczba"] for c in clusters) == 9
    assert all({"geohash", "liczba", "lat", "lon"} <= set(c) for c in clusters)


def test_readiness_filter_matches_computed_value(client14, built):
    for value in ("GOTOWY", "WYMAGA_UWAGI", "NIEZNANY", "NIEGOTOWY"):
        items = _attrs(client14.simulate_get("/1.4/aed", params={"gotowosc": value, "per_page": 100}))
        assert all(i["gotowosc"] == value for i in items)


def test_detail_with_sources(client14, built):
    record = _by_source("OTW-001")
    resp = client14.simulate_get(f"/1.4/aed/{record.pk}")
    assert resp.status == falcon.HTTP_200, resp.text
    attrs = resp.json["data"]["attributes"]
    assert attrs["id_aed_krajowe"] == str(record.pk) and attrs["liczba_zrodel"] == 2
    sources = attrs["zrodla"]
    assert [s["zrodlo_danych"] for s in sources] == ["JST", "OSM"]
    assert sources[0]["zrodlo_wygrywajace"] is True and sources[0]["zasob_id"]
    hidden = _by_source("PRZ-003")
    assert client14.simulate_get(f"/1.4/aed/{hidden.pk}").status == falcon.HTTP_404


def test_stats(client14, built):
    attrs = client14.simulate_get("/1.4/aed/stats").json["data"]["attributes"]
    assert attrs["liczba_aed"] == 9
    assert attrs["liczba_dysponentow"] == 3
    assert attrs["liczba_zrodel_danych"] == 3
    assert attrs["odsetek_z_data_waznosci_elektrod"] == 100.0  # every merged record has the date
    assert sum(attrs["gotowosc"].values()) == 9


def test_api_never_returns_forbidden_or_unknown_fields(client14, built):
    allowed = set(schema.all_field_names()) | {
        "id_aed_krajowe",
        "liczba_zrodel",
        "gotowosc",
        "otwarte_teraz",
        "odleglosc_m",
        "zrodla",
    }
    resp = client14.simulate_get("/1.4/aed", params={"per_page": 100})
    for item in _attrs(resp):
        assert set(item) <= allowed
        assert not set(item) & set(schema.forbidden_field_names())


def test_clusters_survive_other_api_serializers(client14, built):
    """Regression: another TopLevel with aggs_schema must not strip "klastry" from AED responses."""
    client14.simulate_get("/1.4/resources")
    client14.simulate_get("/1.4/datasets")
    resp = client14.simulate_get("/1.4/aed", params={"klastry": "true", "precyzja": 3, "per_page": 1})
    assert sum(c["liczba"] for c in resp.json["meta"]["aggregations"]["klastry"]) == 9
