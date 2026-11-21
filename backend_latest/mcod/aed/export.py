"""
Generators of AED v1 templates and the model data scope workbook.

Everything is derived from ``mcod.aed.schema`` (aed_v1.json) – no field list is defined here.
"""

import csv
import io
import json
from typing import Dict, Iterable, List, Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from mcod.aed import schema

CSV_FILENAME = "wzorcowy_zakres_danych_AED_v1.csv"
XLSX_FILENAME = "wzorcowy_zakres_danych_AED_v1.xlsx"
SCHEMA_FILENAME = "aed_v1.json"

SHEET_DATA = "dane"
SHEET_FIELDS = "opis_pol"
SHEET_DICTIONARIES = "slowniki"
SHEET_RULES = "zasady_pliku"

# Number of data rows covered by Excel data validation (dropdowns) in the "dane" sheet.
XLSX_VALIDATION_ROWS = 5000

_HEADER_FONT = Font(bold=True)
_HEADER_FILL = PatternFill("solid", fgColor="DDEBF7")
_WRAP = Alignment(wrap_text=True, vertical="top")


def template_columns() -> List[str]:
    """Columns of the template: core columns followed by extended ones."""
    return schema.all_field_names()


def _rows_as_lists(rows: Iterable[Dict[str, str]], columns: List[str]) -> List[List[str]]:
    return [[str(row.get(col, "") or "") for col in columns] for row in rows]


def build_csv(with_examples: bool = True) -> bytes:
    """CSV template, UTF-8 (without BOM), comma separator, one header row."""
    columns = template_columns()
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=",", lineterminator="\n")
    writer.writerow(columns)
    if with_examples:
        writer.writerows(_rows_as_lists(schema.examples(), columns))
    return buffer.getvalue().encode("utf-8")


def _style_header(ws, columns_count: int) -> None:
    for col_idx in range(1, columns_count + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _WRAP
    ws.freeze_panes = "A2"


def _set_widths(ws, widths: List[int]) -> None:
    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width


def _add_data_sheet(wb: Workbook, with_examples: bool) -> None:
    ws = wb.active
    ws.title = SHEET_DATA
    columns = template_columns()
    ws.append(columns)
    if with_examples:
        for row in _rows_as_lists(schema.examples(), columns):
            ws.append([value or None for value in row])
    _style_header(ws, len(columns))
    _set_widths(ws, [max(14, len(c) + 4) for c in columns])

    # All cells as text, so that dates stay ISO and numbers keep a dot regardless of Excel locale.
    last_row = XLSX_VALIDATION_ROWS + 1
    for idx in range(1, len(columns) + 1):
        ws.column_dimensions[get_column_letter(idx)].number_format = "@"
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for cell in row:
            cell.number_format = "@"

    enums = schema.enums()
    for idx, name in enumerate(columns, start=1):
        field = schema.field(name)
        values: Optional[List[str]] = None
        if name in enums:
            values = enums[name]
        elif field["type"] == "boolean":
            values = field["trueValues"] + field["falseValues"]
        if not values:
            continue
        letter = get_column_letter(idx)
        dv = DataValidation(
            type="list",
            formula1='"{}"'.format(",".join(values)),
            allow_blank=field["x-aed-presence"] != schema.PRESENCE_REQUIRED,
            showErrorMessage=True,
            errorTitle=name,
            error="Dozwolone wartości / allowed values: {}".format(", ".join(values)),
        )
        dv.add(f"{letter}2:{letter}{last_row}")
        ws.add_data_validation(dv)


def _example_for(field: dict) -> str:
    return str(field.get("example", ""))


def _format_for(field: dict) -> str:
    constraints = field.get("constraints", {})
    base = schema.TYPE_FORMATS[field["type"]]["pl"]
    parts = [base]
    if "pattern" in constraints:
        parts.append("wzorzec: {}".format(constraints["pattern"]))
    if "minimum" in constraints or "maximum" in constraints:
        parts.append("zakres: {}–{}".format(constraints.get("minimum", ""), constraints.get("maximum", "")))
    if "enum" in constraints:
        parts.append("słownik: {}".format(", ".join(constraints["enum"])))
    if constraints.get("unique"):
        parts.append("unikalny w pliku")
    return "; ".join(parts)


def _add_fields_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet(SHEET_FIELDS)
    header = ["kolumna", "opis_pl", "opis_en", "typ", "format", "wymagalnosc", "przyklad"]
    ws.append(header)
    for f in schema.fields():
        ws.append(
            [
                f["name"],
                "{}. {}".format(f["title"]["pl"], f["description"]["pl"]),
                "{}. {}".format(f["title"]["en"], f["description"]["en"]),
                f["type"],
                _format_for(f),
                schema.PRESENCE_LABELS[f["x-aed-presence"]]["pl"],
                _example_for(f),
            ]
        )
    for name in schema.forbidden_field_names():
        reason = schema.forbidden_reason()
        ws.append([name, "KOLUMNA ZAKAZANA – " + reason["pl"], "FORBIDDEN COLUMN – " + reason["en"], "-", "-", "zakazane", "-"])
    _style_header(ws, len(header))
    _set_widths(ws, [26, 60, 60, 10, 40, 22, 28])
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = _WRAP


def _add_dictionaries_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet(SHEET_DICTIONARIES)
    header = ["pole", "wartosc", "znaczenie_pl", "znaczenie_en"]
    ws.append(header)
    for name, values in schema.enums().items():
        labels = schema.enum_labels(name)
        for value in values:
            label = labels.get(value, {})
            ws.append([name, value, label.get("pl", ""), label.get("en", "")])
    for f in schema.fields():
        if f["type"] == "boolean":
            ws.append([f["name"], "true", "tak", "yes"])
            ws.append([f["name"], "false", "nie", "no"])
    _style_header(ws, len(header))
    _set_widths(ws, [26, 24, 50, 50])


def _add_rules_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet(SHEET_RULES)
    header = ["lp", "zasada_pl", "rule_en"]
    ws.append(header)
    for idx, rule in enumerate(schema.file_rules(), start=1):
        ws.append([idx, rule["pl"], rule["en"]])
    _style_header(ws, len(header))
    _set_widths(ws, [5, 90, 90])
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = _WRAP


def build_workbook(with_examples: bool = True) -> Workbook:
    wb = Workbook()
    _add_data_sheet(wb, with_examples)
    _add_fields_sheet(wb)
    _add_dictionaries_sheet(wb)
    _add_rules_sheet(wb)
    return wb


def build_xlsx(with_examples: bool = True) -> bytes:
    buffer = io.BytesIO()
    build_workbook(with_examples).save(buffer)
    return buffer.getvalue()


def build_schema_json() -> bytes:
    return (json.dumps(schema.load_schema(), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
