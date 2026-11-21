from mcod.aed import schema
from mcod.aed.aggregation import SourceRow, aggregate, cluster, normalize_row, order_by_priority

BASE = {name: "" for name in schema.all_field_names()}


def _row(resource_id, **data):
    values = dict(BASE)
    values.update(
        {
            "id_aed": "X",
            "dysponent": "Dysponent Testowy",
            "zrodlo_danych": "JST",
            "data_aktualizacji": "2026-10-01",
            "miejscowosc": "Otwock",
            "szerokosc_geograficzna": "52.10500",
            "dlugosc_geograficzna": "21.26000",
            "status_urzadzenia": "SPRAWNY",
        }
    )
    values.update(data)
    return SourceRow(resource_id, values)


# about 0.00018 deg of latitude = 20 m, 0.00036 = 40 m
LAT_20M = "52.10518"
LAT_40M = "52.10536"


def test_same_source_pair_is_one_aed_even_far_away():
    rows = [
        _row(1, id_aed="A", zrodlo_danych="OSM", zrodlo_id="node/1"),
        _row(2, id_aed="B", zrodlo_danych="OSM", zrodlo_id="node/1", szerokosc_geograficzna="52.2"),
    ]
    assert len(aggregate(rows)) == 1


def test_same_source_id_from_other_source_type_is_not_merged():
    rows = [
        _row(1, id_aed="A", zrodlo_danych="OSM", zrodlo_id="1", szerokosc_geograficzna="52.2"),
        _row(2, id_aed="B", zrodlo_danych="APLIKACJA", zrodlo_id="1"),
    ]
    assert len(aggregate(rows)) == 2


def test_duplicate_within_20_m():
    rows = [_row(1, id_aed="A"), _row(2, id_aed="B", zrodlo_danych="OSM", szerokosc_geograficzna=LAT_20M)]
    merged = aggregate(rows)
    assert len(merged) == 1
    assert merged[0].sources_count == 2


def test_no_duplicate_at_40_m():
    rows = [_row(1, id_aed="A"), _row(2, id_aed="B", szerokosc_geograficzna=LAT_40M)]
    assert len(aggregate(rows)) == 2


def test_close_rows_from_the_same_file_are_not_merged():
    rows = [_row(1, id_aed="A"), _row(1, id_aed="B", szerokosc_geograficzna=LAT_20M)]
    assert len(aggregate(rows)) == 2


def test_close_rows_in_different_localities_are_not_merged():
    rows = [_row(1, id_aed="A"), _row(2, id_aed="B", miejscowosc="Józefów", szerokosc_geograficzna=LAT_20M)]
    assert len(aggregate(rows)) == 2


def test_street_compared_only_when_both_known():
    near = {"szerokosc_geograficzna": LAT_20M}
    assert len(aggregate([_row(1, ulica="ul. Testowa"), _row(2, ulica="", **near)])) == 1
    assert len(aggregate([_row(1, ulica="ul. Testowa"), _row(2, ulica="Testowa", **near)])) == 1
    assert len(aggregate([_row(1, ulica="ul. Testowa"), _row(2, ulica="ul. Inna", **near)])) == 2


def test_locality_comparison_ignores_case_and_diacritics():
    rows = [_row(1, miejscowosc="Kraków"), _row(2, miejscowosc="KRAKOW", szerokosc_geograficzna=LAT_20M)]
    assert len(aggregate(rows)) == 1


def test_source_priority():
    order = ["OSM", "INNE", "APLIKACJA", "JST", "WLASCICIEL"]
    rows = [_row(i, id_aed=s, zrodlo_danych=s) for i, s in enumerate(order)]
    assert [r.data["zrodlo_danych"] for r in order_by_priority(rows)] == ["WLASCICIEL", "JST", "APLIKACJA", "INNE", "OSM"]


def test_priority_tie_newer_update_wins():
    rows = [_row(1, id_aed="OLD", data_aktualizacji="2026-01-01"), _row(2, id_aed="NEW", data_aktualizacji="2026-06-01")]
    assert [r.data["id_aed"] for r in order_by_priority(rows)] == ["NEW", "OLD"]


def test_merge_winner_and_filling_empty_fields():
    osm = _row(1, id_aed="O", zrodlo_danych="OSM", zrodlo_id="node/9", producent="Producent Testowy", nazwa_obiektu="OSM")
    owner = _row(2, id_aed="W", zrodlo_danych="WLASCICIEL", nazwa_obiektu="Właściciel", szerokosc_geograficzna=LAT_20M)
    merged = aggregate([osm, owner])[0]
    assert merged.data["nazwa_obiektu"] == "Właściciel"
    assert merged.data["szerokosc_geograficzna"] == LAT_20M  # winner's location
    assert merged.data["producent"] == "Producent Testowy"  # filled from the other source
    assert merged.data["zrodlo_id"] == ""  # identity fields are not mixed between sources
    assert [r.data["id_aed"] for r in merged.rows] == ["W", "O"]


def test_duplicates_are_transitive():
    rows = [
        _row(1, id_aed="A"),
        _row(2, id_aed="B", szerokosc_geograficzna=LAT_20M),
        _row(3, id_aed="C", szerokosc_geograficzna="52.10536"),
    ]
    assert cluster(rows) == [[0, 1, 2]]


def test_normalize_row():
    row = normalize_row(
        {
            "miejscowosc": "  Otwock  ",
            "ulica": "ul.  Testowa",
            "status_urzadzenia": "sprawny",
            "zrodlo_danych": "jst",
            "kod_pocztowy": "05400",
            "dostep_publiczny": "TRUE",
            "pin": "1234",
        }
    )
    assert row["miejscowosc"] == "Otwock"
    assert row["ulica"] == "ul. Testowa"
    assert row["status_urzadzenia"] == "SPRAWNY"
    assert row["zrodlo_danych"] == "JST"
    assert row["kod_pocztowy"] == "05-400"
    assert row["dostep_publiczny"] == "true"
    assert "pin" not in row
    assert set(row) == set(schema.all_field_names())
