import csv
import io
import json
import os
from collections import Counter
from datetime import date

import pytest
from openpyxl import Workbook

from mcod.aed import schema
from mcod.aed.export import build_csv, build_xlsx
from mcod.aed.validation import ERROR, MESSAGES, WARNING, validate_file

TODAY = date(2026, 11, 21)
FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "validation")
with open(os.path.join(FIXTURES, "manifest.json"), encoding="utf-8") as f:
    MANIFEST = json.load(f)
# Files whose broken structure causes many follow-up issues – only the listed codes are required.
NOT_EXACT = {"delimiter.csv"}


def _fixture(name: str) -> bytes:
    with open(os.path.join(FIXTURES, name), "rb") as f:
        return f.read()


def _validate(content: bytes, filename: str = "aed.csv", **kwargs):
    return validate_file(content, filename, today=TODAY, **kwargs)


def _codes(report):
    return [i.code for i in report.issues]


def _rows(name: str):
    return list(csv.reader(io.StringIO(_fixture(name).decode())))


def _to_csv(rows) -> bytes:
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerows(rows)
    return buffer.getvalue().encode()


def test_valid_file_has_no_issues():
    report = _validate(_fixture("valid.csv"))
    assert report.issues == []
    assert report.is_compliant
    assert report.rows == 3
    assert len(report.records) == 3


def test_generated_templates_are_valid():
    assert _validate(build_csv()).issues == []
    assert _validate(build_xlsx(), "aed.xlsx").issues == []
    empty = _validate(build_csv(with_examples=False))
    assert empty.is_compliant and empty.rows == 0


@pytest.mark.parametrize("name", sorted(MANIFEST))
def test_fixture_rules(name):
    report = _validate(_fixture(name))
    expected = MANIFEST[name]
    found = _codes(report)
    assert not Counter(expected) - Counter(found), found
    if name not in NOT_EXACT:
        assert set(found) == set(expected), found
    expected_levels = {MESSAGES[c][0] for c in expected}
    assert report.is_compliant == (ERROR not in expected_levels)


def test_every_rule_has_a_fixture_or_dedicated_test():
    covered = {code for codes in MANIFEST.values() for code in codes}
    dedicated = {
        "UNSUPPORTED_FILE",
        "FILE_TOO_LARGE",
        "UNREADABLE_FILE",
        "EMPTY_FILE",
        "TOO_MANY_ROWS",
        "DUPLICATE_COLUMN",
        "TOO_LONG",
        "OUT_OF_RANGE",
        "INVALID_INTEGER",
    }
    assert set(MESSAGES) == covered | dedicated


def test_issue_points_to_row_and_column():
    issue = _validate(_fixture("enum_value.csv")).issues[0]
    assert issue.as_dict() == {
        "wiersz": 2,
        "kolumna": "status_urzadzenia",
        "kod": "ENUM_VALUE",
        "poziom": ERROR,
        "komunikat_pl": issue.message_pl,
        "komunikat_en": issue.message_en,
    }
    assert "„DZIALA”" in issue.message_pl and "SPRAWNY" in issue.message_en


def test_report_summary():
    report = _validate(_fixture("electrodes_expired.csv"))
    assert report.summary() == {
        "standard": "AED_V1",
        "liczba_wierszy": 3,
        "liczba_bledow": 0,
        "liczba_ostrzezen": 1,
        "zgodny": True,
    }
    assert set(report.as_dict()) == set(report.summary()) | {"problemy"}


@pytest.mark.parametrize("header", ["PIN", "Hasło", "imie_nazwisko", "PESEL", "Email Prywatny", "kod", "password"])
def test_forbidden_header_variants(header):
    rows = _rows("valid.csv")
    rows[0].append(header)
    for row in rows[1:]:
        row.append("SEKRET-123")
    report = _validate(_to_csv(rows))
    assert _codes(report) == ["FORBIDDEN_COLUMN"]
    assert not report.is_compliant
    assert "SEKRET-123" not in json.dumps(report.as_dict(), ensure_ascii=False)
    assert all("SEKRET-123" not in str(record) for _, record in report.records)


def test_phone_value_never_in_messages():
    rows = _rows("valid.csv")
    idx = rows[0].index("telefon_kontaktowy")
    rows[1][idx] = "48 600 000 000"
    rows[3][idx] = "+48000000001"
    report = _validate(_to_csv(rows))
    assert _codes(report) == ["INVALID_FORMAT"]
    assert "600" not in report.issues[0].message_pl


def test_file_without_extended_columns_is_valid():
    rows = _rows("valid.csv")
    keep = [i for i, name in enumerate(rows[0]) if name in schema.core_field_names()]
    assert _validate(_to_csv([[row[i] for i in keep] for row in rows])).issues == []


def test_extended_columns_are_validated():
    rows = _rows("valid.csv")
    values = {1: ["1.5", "true", "1417011"], 2: ["300", "false", ""], 3: ["0", "", "12"]}
    for row_idx, row_values in values.items():
        for name, value in zip(["pietro", "elektrody_pediatryczne", "kod_teryt_gminy"], row_values):
            rows[row_idx][rows[0].index(name)] = value
    report = _validate(_to_csv(rows))
    assert [(i.row, i.code) for i in report.issues] == [(2, "INVALID_INTEGER"), (3, "OUT_OF_RANGE"), (4, "INVALID_FORMAT")]


def test_too_long_value():
    report = _validate(_fixture("valid.csv").replace(b"Dworzec Testowy", b"D" * 301))
    assert _codes(report) == ["TOO_LONG"]


def test_duplicate_column():
    rows = _rows("valid.csv")
    rows[0].append("miejscowosc")
    for row in rows[1:]:
        row.append("x")
    assert _codes(_validate(_to_csv(rows))) == ["DUPLICATE_COLUMN"]


def test_enum_and_boolean_case_is_normalized():
    content = _fixture("valid.csv").replace(b"SPRAWNY", b"sprawny").replace(b",true,", b",TRUE,")
    report = _validate(content)
    assert report.issues == []
    assert report.records[0][1]["status_urzadzenia"] == "SPRAWNY"


def test_postal_code_normalized_in_records():
    report = _validate(_fixture("postal_code_format.csv"))
    assert report.records[0][1]["kod_pocztowy"] == "05-400"


@pytest.mark.parametrize(
    "filename, content",
    [
        ("aed.pdf", b"%PDF-1.4"),
        ("aed.xlsm", b"PK\x03\x04rest"),
        ("aed.xls", b"\xd0\xcf\x11\xe0"),
        ("aed.csv", b"PK\x03\x04zip-in-disguise"),
    ],
)
def test_unsupported_file(filename, content):
    assert _codes(_validate(content, filename)) == ["UNSUPPORTED_FILE"]


def test_broken_xlsx():
    assert _codes(_validate(b"PK\x03\x04broken", "aed.xlsx")) == ["UNREADABLE_FILE"]


def test_empty_file():
    assert _codes(_validate(b"")) == ["EMPTY_FILE"]


def test_too_many_rows_csv_and_xlsx():
    assert _codes(_validate(_fixture("valid.csv"), max_rows=2)) == ["TOO_MANY_ROWS"]
    assert _codes(_validate(build_xlsx(), "aed.xlsx", max_rows=2)) == ["TOO_MANY_ROWS"]


def _xlsx_from_rows(rows) -> bytes:
    wb = Workbook()
    for row in rows:
        wb.active.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def test_xlsx_native_types_are_accepted():
    rows = _rows("valid.csv")
    header = rows[0]
    typed = []
    for row in rows[1:]:
        values = []
        for name, value in zip(header, row):
            f = schema.field(name)
            if value and f["type"] == "date":
                value = date.fromisoformat(value)
            elif value and f["type"] == "number":
                value = float(value)
            elif value and f["type"] == "boolean":
                value = value == "true"
            values.append(value if value != "" else None)
        typed.append(values)
    report = _validate(_xlsx_from_rows([header] + typed + [[None] * len(header)]), "aed.xlsx")
    assert report.issues == []
    assert report.records[0][1]["data_aktualizacji"] == "2026-10-01"


def test_xlsx_errors_are_reported_like_csv():
    report = _validate(_xlsx_from_rows(_rows("enum_value.csv")), "aed.xlsx")
    assert [(i.row, i.code) for i in report.issues] == [(2, "ENUM_VALUE")]


def test_near_duplicate_points_to_other_row():
    report = _validate(_fixture("near_duplicate_5m.csv"))
    assert [(i.row, i.code) for i in report.issues] == [(5, "NEAR_DUPLICATE_5M")]
    assert "wiersza 2" in report.issues[0].message_pl
    assert {lvl for lvl, _, _ in MESSAGES.values()} == {ERROR, WARNING}


@pytest.mark.parametrize(
    "updated, codes",
    [
        ("2025-11-21", []),  # exactly 365 days ago
        ("2025-11-20", ["STALE_UPDATE"]),
        ("2026-11-21", []),  # today is not the future
        ("2026-11-22", ["FUTURE_UPDATE_DATE"]),
    ],
)
def test_update_date_boundaries(updated, codes):
    assert _codes(_validate(_fixture("valid.csv").replace(b"2026-10-01", updated.encode()))) == codes
