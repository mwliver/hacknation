import csv
import io
import json

from django.core.management import call_command
from openpyxl import load_workbook

from mcod.aed import export, schema


def _read_csv(content: bytes):
    return list(csv.reader(io.StringIO(content.decode("utf-8"))))


def test_csv_template_with_examples():
    content = export.build_csv(with_examples=True)
    assert not content.startswith(b"\xef\xbb\xbf")  # UTF-8 without BOM
    rows = _read_csv(content)
    assert rows[0] == schema.all_field_names()
    assert len(rows) == 4
    assert all(len(row) == len(rows[0]) for row in rows)


def test_csv_template_without_examples():
    rows = _read_csv(export.build_csv(with_examples=False))
    assert rows == [schema.all_field_names()]


def test_xlsx_has_all_sheets():
    wb = load_workbook(io.BytesIO(export.build_xlsx()))
    assert wb.sheetnames == ["dane", "opis_pol", "slowniki", "zasady_pliku"]


def test_xlsx_data_sheet():
    ws = load_workbook(io.BytesIO(export.build_xlsx()))["dane"]
    rows = list(ws.iter_rows(values_only=True))
    assert list(rows[0]) == schema.all_field_names()
    assert len(rows) == 4
    lat_idx = rows[0].index("szerokosc_geograficzna")
    assert rows[1][lat_idx] == "52.1050"  # stored as text, dot as decimal separator
    validated = {str(dv.sqref).split(":")[0] for dv in ws.data_validations.dataValidation}
    assert len(validated) == len(schema.enums()) + sum(1 for f in schema.fields() if f["type"] == "boolean")


def test_xlsx_fields_sheet():
    ws = load_workbook(io.BytesIO(export.build_xlsx()))["opis_pol"]
    rows = list(ws.iter_rows(values_only=True))
    assert list(rows[0]) == ["kolumna", "opis_pl", "opis_en", "typ", "format", "wymagalnosc", "przyklad"]
    names = [r[0] for r in rows[1:]]
    assert names == schema.all_field_names() + schema.forbidden_field_names()


def test_xlsx_dictionaries_sheet():
    ws = load_workbook(io.BytesIO(export.build_xlsx()))["slowniki"]
    pairs = {(r[0], r[1]) for r in ws.iter_rows(min_row=2, values_only=True)}
    for name, values in schema.enums().items():
        for value in values:
            assert (name, value) in pairs
    assert ("dostep_publiczny", "true") in pairs


def test_xlsx_rules_sheet():
    ws = load_workbook(io.BytesIO(export.build_xlsx()))["zasady_pliku"]
    rules = [r[1] for r in ws.iter_rows(min_row=2, values_only=True)]
    assert rules == [rule["pl"] for rule in schema.file_rules()]


def test_export_command(tmp_path):
    call_command("export_aed_standard", out=str(tmp_path))
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(
        [export.XLSX_FILENAME, export.CSV_FILENAME, export.SCHEMA_FILENAME]
    )
    with open(tmp_path / export.SCHEMA_FILENAME, encoding="utf-8") as f:
        assert json.load(f) == schema.load_schema()
