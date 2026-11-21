import json

import pytest

from mcod.aed import schema

EXPECTED_CORE = [
    "id_aed",
    "dysponent",
    "zrodlo_danych",
    "zrodlo_id",
    "data_aktualizacji",
    "status_weryfikacji",
    "nazwa_obiektu",
    "miejscowosc",
    "ulica",
    "nr_budynku",
    "kod_pocztowy",
    "szerokosc_geograficzna",
    "dlugosc_geograficzna",
    "wewnatrz_budynku",
    "opis_lokalizacji",
    "godziny_dostepnosci",
    "dostep_publiczny",
    "wymaga_kodu_lub_klucza",
    "status_urzadzenia",
    "data_ostatniej_kontroli",
    "data_waznosci_elektrod",
    "data_waznosci_baterii",
]
EXPECTED_IF_KNOWN = [
    "zrodlo_id",
    "ulica",
    "nr_budynku",
    "kod_pocztowy",
    "data_ostatniej_kontroli",
    "data_waznosci_elektrod",
    "data_waznosci_baterii",
]
EXPECTED_EXTENDED = [
    "kod_teryt_gminy",
    "producent",
    "model",
    "numer_seryjny",
    "elektrody_pediatryczne",
    "pietro",
    "telefon_kontaktowy",
]


def test_schema_file_is_valid_json():
    with open(schema.SCHEMA_FILE, encoding="utf-8") as f:
        data = json.load(f)
    assert data["primaryKey"] == "id_aed"


def test_field_groups_match_standard():
    assert schema.core_field_names() == EXPECTED_CORE
    assert [n for n in schema.core_field_names() if n not in schema.required_field_names()] == EXPECTED_IF_KNOWN
    assert schema.extended_field_names() == EXPECTED_EXTENDED


@pytest.mark.parametrize("field", schema.fields(), ids=lambda f: f["name"])
def test_every_field_is_documented_in_pl_and_en(field):
    for key in ("title", "description"):
        assert field[key]["pl"].strip()
        assert field[key]["en"].strip()
    assert field["type"] in schema.TYPE_FORMATS
    assert field["x-aed-presence"] in schema.PRESENCES
    assert field["constraints"]["required"] == (field["x-aed-presence"] == schema.PRESENCE_REQUIRED)
    assert "example" in field


def test_enums():
    assert schema.enums() == {
        "zrodlo_danych": ["WLASCICIEL", "JST", "OSM", "APLIKACJA", "INNE"],
        "status_weryfikacji": ["ZWERYFIKOWANY", "NIEZWERYFIKOWANY", "WATPLIWY"],
        "status_urzadzenia": ["SPRAWNY", "NIESPRAWNY", "CZASOWO_NIEDOSTEPNY", "NIEZNANY"],
    }
    for name, values in schema.enums().items():
        labels = schema.enum_labels(name)
        assert set(labels) == set(values)


def test_source_priority_covers_all_sources():
    assert schema.source_priority() == ["WLASCICIEL", "JST", "APLIKACJA", "INNE", "OSM"]
    assert set(schema.source_priority()) == set(schema.enums()["zrodlo_danych"])


def test_forbidden_fields_are_not_schema_fields():
    assert not set(schema.forbidden_field_names()) & set(schema.all_field_names())


@pytest.mark.parametrize(
    "header, forbidden",
    [
        ("PIN", True),
        ("Hasło", True),
        ("HASLO", True),
        ("kod szafki", True),
        ("Kod-Szafki", True),
        ("Imię Nazwisko", True),
        ("PESEL ", True),
        ("Email_Prywatny", True),
        ("kod_pocztowy", False),
        ("wymaga_kodu_lub_klucza", False),
        ("kod_teryt_gminy", False),
    ],
)
def test_is_forbidden_header(header, forbidden):
    assert schema.is_forbidden_header(header) is forbidden


def test_examples_are_fictional_and_complete():
    examples = schema.examples()
    assert len(examples) == 3
    assert {e["miejscowosc"] for e in examples} == {"Otwock", "Warszawa", "Kraków"}
    for example in examples:
        assert set(schema.core_field_names()) <= set(example)


def test_frictionless_schema_has_plain_keys():
    plain = schema.frictionless_schema()
    assert [f["name"] for f in plain["fields"]] == schema.all_field_names()
    for f in plain["fields"]:
        assert not any(key.startswith("x-aed") for key in f)


def test_load_schema_returns_copy():
    data = schema.load_schema()
    data["fields"].clear()
    assert schema.fields()


def test_frictionless_schema_is_valid_table_schema():
    from tableschema import validate

    assert validate(schema.frictionless_schema())
