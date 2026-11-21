"""
AED v1 file validator.

``validate_file(content, filename)`` is a pure function (no database access) used both by the Celery task
validating resources marked as AED v1 and by the ``POST /aed/validate`` endpoint.

Row numbers in the report are file line numbers: the header is row 1, the first data row is row 2
(the same as in a spreadsheet). Issues about the whole file have ``row = None``.

Privacy: values from forbidden columns and from ``telefon_kontaktowy`` are never copied into messages or logs.
"""

import csv
import io
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from django.utils import timezone

from mcod.aed import opening_hours, schema
from mcod.aed.geo import close_pairs

logger = logging.getLogger("mcod")

ERROR = "ERROR"
WARNING = "WARNING"

STALE_AFTER_DAYS = 365
NEAR_DUPLICATE_RADIUS_M = 5.0
MAX_VALUE_IN_MESSAGE = 60
SENSITIVE_COLUMNS = {"telefon_kontaktowy"}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_NUMBER_RE = re.compile(r"^-?\d+(\.\d+)?$")
_INTEGER_RE = re.compile(r"^-?\d+$")
_POSTAL_DIGITS_RE = re.compile(r"^\d{5}$")

# code -> (level, message_pl, message_en); messages are str.format templates
MESSAGES: Dict[str, Tuple[str, str, str]] = {
    "UNSUPPORTED_FILE": (
        ERROR,
        "Nieobsługiwany typ pliku. Dozwolone: CSV (UTF-8) lub XLSX bez makr.",
        "Unsupported file type. Allowed: CSV (UTF-8) or XLSX without macros.",
    ),
    "FILE_TOO_LARGE": (
        ERROR,
        "Plik jest za duży do walidacji standardu AED (maks. {limit_mb} MB).",
        "The file is too large for AED standard validation (max {limit_mb} MB).",
    ),
    "UNREADABLE_FILE": (ERROR, "Nie udało się odczytać pliku: {detail}.", "The file could not be read: {detail}."),
    "EMPTY_FILE": (ERROR, "Plik jest pusty – brak wiersza nagłówka.", "The file is empty – no header row."),
    "ENCODING": (
        ERROR,
        "Plik CSV nie jest zapisany w kodowaniu UTF-8. Zapisz go ponownie jako „CSV UTF-8”.",
        'The CSV file is not UTF-8 encoded. Save it again as "CSV UTF-8".',
    ),
    "UTF8_BOM": (
        WARNING,
        "Plik zaczyna się od znacznika BOM. Zalecany jest UTF-8 bez BOM.",
        "The file starts with a BOM. UTF-8 without BOM is recommended.",
    ),
    "DELIMITER": (
        ERROR,
        "Nagłówek nie zawiera przecinków – separatorem pól musi być przecinek (wykryto „{delimiter}”).",
        'The header has no commas – the field separator must be a comma (found "{delimiter}").',
    ),
    "TOO_MANY_ROWS": (
        ERROR,
        "Plik ma więcej niż {limit} wierszy danych. Podziel go na mniejsze pliki.",
        "The file has more than {limit} data rows. Split it into smaller files.",
    ),
    "EMPTY_COLUMN_HEADER": (
        ERROR,
        "Kolumna nr {position} nie ma nazwy w nagłówku (pusta kolumna).",
        "Column no. {position} has no name in the header (empty column).",
    ),
    "DUPLICATE_COLUMN": (
        ERROR,
        "Kolumna „{column}” występuje w nagłówku więcej niż raz.",
        'Column "{column}" appears more than once.',
    ),
    "FORBIDDEN_COLUMN": (
        ERROR,
        "Kolumna „{column}” jest zakazana. " + schema.forbidden_reason()["pl"],
        'Column "{column}" is forbidden. ' + schema.forbidden_reason()["en"],
    ),
    "MISSING_COLUMN": (
        ERROR,
        "Brak wymaganej kolumny „{column}”. Kolumna musi istnieć, nawet jeśli wartości są nieznane.",
        'Missing column "{column}". The column must exist even if the values are unknown.',
    ),
    "UNKNOWN_COLUMN": (
        WARNING,
        "Nieznana kolumna „{column}” – nie należy do standardu AED v1 i zostanie pominięta.{hint_pl}",
        'Unknown column "{column}" – not part of the AED v1 standard, it will be ignored.{hint_en}',
    ),
    "EMPTY_ROW": (ERROR, "Pusty wiersz. Usuń puste wiersze z pliku.", "Empty row. Remove empty rows from the file."),
    "ROW_LENGTH": (
        ERROR,
        "Wiersz ma {actual} komórek, a nagłówek {expected}.",
        "The row has {actual} cells, the header has {expected}.",
    ),
    "REQUIRED_EMPTY": (ERROR, "Pole „{column}” jest wymagane i nie może być puste.", 'Field "{column}" is required.'),
    "INVALID_DATE": (
        ERROR,
        "Niepoprawna data {value}. Wymagany format RRRR-MM-DD, np. 2026-03-31.",
        "Invalid date {value}. Required format YYYY-MM-DD, e.g. 2026-03-31.",
    ),
    "INVALID_NUMBER": (
        ERROR,
        "Niepoprawna liczba {value}. Użyj kropki dziesiętnej, bez spacji i separatorów tysięcy, np. 52.1050.",
        "Invalid number {value}. Use a dot as decimal separator, no spaces or thousands separators, e.g. 52.1050.",
    ),
    "INVALID_INTEGER": (ERROR, "Niepoprawna liczba całkowita {value}.", "Invalid integer {value}."),
    "INVALID_BOOLEAN": (
        ERROR,
        "Niepoprawna wartość logiczna {value}. Dozwolone: true, false.",
        "Invalid boolean {value}. Allowed: true, false.",
    ),
    "INVALID_FORMAT": (
        ERROR,
        "Wartość {value} ma niepoprawny format: {expected_pl}.",
        "Value {value} has an invalid format: {expected_en}.",
    ),
    "TOO_LONG": (ERROR, "Wartość jest za długa (maks. {limit} znaków).", "The value is too long (max {limit} characters)."),
    "OUT_OF_RANGE": (
        ERROR,
        "Wartość {value} jest poza zakresem {minimum}–{maximum}.",
        "Value {value} is out of range {minimum}–{maximum}.",
    ),
    "OUT_OF_POLAND": (
        ERROR,
        "Współrzędna {value} jest poza Polską (dozwolony zakres {minimum}–{maximum}). "
        "Sprawdź, czy nie zamieniono szerokości z długością.",
        "Coordinate {value} is outside Poland (allowed range {minimum}–{maximum}). "
        "Check that latitude and longitude are not swapped.",
    ),
    "ENUM_VALUE": (
        ERROR,
        "Wartość {value} spoza słownika. Dozwolone: {allowed}.",
        "Value {value} is not in the dictionary. Allowed: {allowed}.",
    ),
    "DUPLICATE_ID": (
        ERROR,
        "Identyfikator {value} powtarza się w pliku (pierwszy raz w wierszu {first_row}).",
        "Identifier {value} is duplicated in the file (first seen in row {first_row}).",
    ),
    "FUTURE_UPDATE_DATE": (
        ERROR,
        "Data aktualizacji {value} jest z przyszłości.",
        "Update date {value} is in the future.",
    ),
    "STALE_UPDATE": (
        WARNING,
        "Dane nie były aktualizowane od ponad 12 miesięcy ({value}).",
        "The data has not been updated for more than 12 months ({value}).",
    ),
    "OPENING_HOURS_UNSUPPORTED": (
        WARNING,
        "Godziny {value} nie są w obsługiwanej składni opening_hours (np. 24/7, Mo-Fr 08:00-16:00; PH off). "
        "Status „otwarte teraz” nie będzie wyliczany.",
        "Hours {value} are not in the supported opening_hours syntax (e.g. 24/7, Mo-Fr 08:00-16:00; PH off). "
        '"Open now" will not be computed.',
    ),
    "ELECTRODES_EXPIRED": (
        WARNING,
        "Elektrody straciły ważność ({value}), a urządzenie ma status SPRAWNY.",
        "Electrodes expired ({value}) while the device status is SPRAWNY.",
    ),
    "BATTERY_EXPIRED": (
        WARNING,
        "Bateria straciła ważność ({value}), a urządzenie ma status SPRAWNY.",
        "Battery expired ({value}) while the device status is SPRAWNY.",
    ),
    "NEAR_DUPLICATE_5M": (
        WARNING,
        "Ten AED leży {distance} m od AED z wiersza {other_row}. Sprawdź, czy to nie ten sam defibrylator.",
        "This AED is {distance} m from the AED in row {other_row}. Check whether it is the same device.",
    ),
    "POSTAL_CODE_FORMAT": (
        WARNING,
        "Kod pocztowy {value} bez myślnika – zostanie zapisany jako {normalized}.",
        "Postal code {value} has no dash – it will be stored as {normalized}.",
    ),
}

_PATTERN_DESCRIPTIONS = {
    "kod_pocztowy": ("NN-NNN, np. 05-400", "NN-NNN, e.g. 05-400"),
    "kod_teryt_gminy": ("7 cyfr kodu TERC, np. 1417011", "7 digits of the TERC code, e.g. 1417011"),
    "telefon_kontaktowy": ("cyfry bez spacji, opcjonalnie z + na początku", "digits without spaces, optionally starting with +"),
}


@dataclass
class Issue:
    code: str
    level: str
    row: Optional[int] = None
    column: Optional[str] = None
    message_pl: str = ""
    message_en: str = ""

    def as_dict(self) -> dict:
        return {
            "wiersz": self.row,
            "kolumna": self.column,
            "kod": self.code,
            "poziom": self.level,
            "komunikat_pl": self.message_pl,
            "komunikat_en": self.message_en,
        }


@dataclass
class ValidationReport:
    rows: int = 0
    issues: List[Issue] = field(default_factory=list)
    # Validated data rows (only schema columns, stripped strings) with their file row number.
    # Not serialized – used by the national dataset builder.
    records: List[Tuple[int, Dict[str, str]]] = field(default_factory=list, repr=False)
    schema_version: str = schema.SCHEMA_VERSION

    @property
    def errors_count(self) -> int:
        return sum(1 for i in self.issues if i.level == ERROR)

    @property
    def warnings_count(self) -> int:
        return sum(1 for i in self.issues if i.level == WARNING)

    @property
    def is_compliant(self) -> bool:
        return self.errors_count == 0

    def summary(self) -> dict:
        return {
            "standard": self.schema_version,
            "liczba_wierszy": self.rows,
            "liczba_bledow": self.errors_count,
            "liczba_ostrzezen": self.warnings_count,
            "zgodny": self.is_compliant,
        }

    def as_dict(self) -> dict:
        return {**self.summary(), "problemy": [i.as_dict() for i in self.issues]}

    def add(self, code: str, row: Optional[int] = None, column: Optional[str] = None, **params) -> None:
        level, pl, en = MESSAGES[code]
        params.setdefault("column", column)
        self.issues.append(Issue(code, level, row, column, pl.format(**params), en.format(**params)))


class _FatalFileError(Exception):
    pass


def _quote(value: str, column: Optional[str] = None) -> str:
    if column in SENSITIVE_COLUMNS:
        return "(wartość ukryta)"
    text = value if len(value) <= MAX_VALUE_IN_MESSAGE else value[:MAX_VALUE_IN_MESSAGE] + "…"
    return "„{}”".format(text)


# ---------------------------------------------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------------------------------------------


def _file_kind(content: bytes, filename: str) -> Optional[str]:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    is_zip = content[:4] == b"PK\x03\x04"
    if ext == "xlsx" and is_zip:
        return "xlsx"
    if ext == "csv" and not is_zip:
        return "csv"
    return None


def _read_csv(content: bytes, report: ValidationReport) -> List[List[str]]:
    if content.startswith(b"\xef\xbb\xbf"):
        report.add("UTF8_BOM")
        content = content[3:]
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        report.add("ENCODING")
        raise _FatalFileError()
    try:
        return list(csv.reader(io.StringIO(text, newline=""), delimiter=","))
    except csv.Error as exc:
        report.add("UNREADABLE_FILE", detail=str(exc))
        raise _FatalFileError()


def _xlsx_cell_to_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        return value.date().isoformat() if value.time() == datetime.min.time() else value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)
    return str(value)


def _read_xlsx(content: bytes, report: ValidationReport, max_rows: int) -> List[List[str]]:
    from openpyxl import load_workbook

    try:
        # read_only + data_only: no formulas are evaluated, no macros are loaded (.xlsm is rejected earlier)
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True, keep_links=False)
    except Exception as exc:  # broken zip / not a workbook
        report.add("UNREADABLE_FILE", detail=type(exc).__name__)
        raise _FatalFileError()
    try:
        sheet = workbook.worksheets[0]
        rows: List[List[str]] = []
        for raw in sheet.iter_rows(values_only=True):
            rows.append([_xlsx_cell_to_str(v) for v in raw])
            if len(rows) > max_rows + 1:
                break
    finally:
        workbook.close()
    # Excel keeps formatted but empty trailing rows/cells – drop them.
    while rows and not any(c.strip() for c in rows[-1]):
        rows.pop()
    if rows:
        header_len = len(rows[0])
        while header_len and not rows[0][header_len - 1].strip():
            header_len -= 1
        rows = [_trim_xlsx_row(r, header_len) for r in rows]
    return rows


def _trim_xlsx_row(row: List[str], header_len: int) -> List[str]:
    extra = row[header_len:]
    if any(c.strip() for c in extra):
        return row
    return row[:header_len]


# ---------------------------------------------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------------------------------------------


def _check_header(header: List[str], report: ValidationReport) -> Dict[int, str]:
    """Returns mapping: column position -> schema field name, for known columns."""
    known = set(schema.all_field_names())
    normalized_known = {schema.normalize_header(n): n for n in known}
    positions: Dict[int, str] = {}
    seen: Dict[str, int] = {}
    if len(header) == 1 and ";" in header[0]:
        report.add("DELIMITER", delimiter=";")
    elif len(header) == 1 and "\t" in header[0]:
        report.add("DELIMITER", delimiter="TAB")
    for idx, raw in enumerate(header):
        name = raw.strip()
        if not name:
            report.add("EMPTY_COLUMN_HEADER", row=1, position=idx + 1)
            continue
        if schema.is_forbidden_header(name):
            report.add("FORBIDDEN_COLUMN", row=1, column=name)
            continue
        if name in seen:
            report.add("DUPLICATE_COLUMN", row=1, column=name)
            continue
        seen[name] = idx
        if name in known:
            positions[idx] = name
        else:
            suggestion = normalized_known.get(schema.normalize_header(name))
            hint_pl = " Czy chodziło o „{}”?".format(suggestion) if suggestion else ""
            hint_en = ' Did you mean "{}"?'.format(suggestion) if suggestion else ""
            report.add("UNKNOWN_COLUMN", row=1, column=name, hint_pl=hint_pl, hint_en=hint_en)
    for name in schema.core_field_names():
        if name not in seen:
            report.add("MISSING_COLUMN", row=1, column=name)
    return positions


# ---------------------------------------------------------------------------------------------------------------
# Cells
# ---------------------------------------------------------------------------------------------------------------


def _parse_date(value: str) -> Optional[date]:
    if not _DATE_RE.match(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _check_date(name, value, row, report, f, constraints):
    parsed = _parse_date(value)
    if parsed is None:
        report.add("INVALID_DATE", row, name, value=_quote(value, name))
    return parsed


def _check_numeric(name, value, row, report, f, constraints):
    is_number = f["type"] == "number"
    pattern, code = (_NUMBER_RE, "INVALID_NUMBER") if is_number else (_INTEGER_RE, "INVALID_INTEGER")
    if not pattern.match(value):
        report.add(code, row, name, value=_quote(value, name))
        return None
    number = float(value) if is_number else int(value)
    minimum, maximum = constraints.get("minimum"), constraints.get("maximum")
    if (minimum is not None and number < minimum) or (maximum is not None and number > maximum):
        code = "OUT_OF_POLAND" if name in ("szerokosc_geograficzna", "dlugosc_geograficzna") else "OUT_OF_RANGE"
        report.add(code, row, name, value=_quote(value, name), minimum=minimum, maximum=maximum)
        return None
    return number


def _check_boolean(name, value, row, report, f, constraints):
    lowered = value.lower()
    if lowered in f["trueValues"]:
        return True
    if lowered in f["falseValues"]:
        return False
    report.add("INVALID_BOOLEAN", row, name, value=_quote(value, name))
    return None


def _check_string(name, value, row, report, f, constraints):
    if "enum" in constraints:
        upper = value.upper()
        if upper not in constraints["enum"]:
            report.add("ENUM_VALUE", row, name, value=_quote(value, name), allowed=", ".join(constraints["enum"]))
            return None
        return upper
    if name == "kod_pocztowy" and _POSTAL_DIGITS_RE.match(value):
        normalized = "{}-{}".format(value[:2], value[2:])
        report.add("POSTAL_CODE_FORMAT", row, name, value=_quote(value, name), normalized=normalized)
        return normalized
    if "pattern" in constraints and not re.match(constraints["pattern"], value):
        expected_pl, expected_en = _PATTERN_DESCRIPTIONS.get(name, (constraints["pattern"], constraints["pattern"]))
        report.add("INVALID_FORMAT", row, name, value=_quote(value, name), expected_pl=expected_pl, expected_en=expected_en)
        return None
    return value


_TYPE_CHECKERS = {
    "date": _check_date,
    "number": _check_numeric,
    "integer": _check_numeric,
    "boolean": _check_boolean,
    "string": _check_string,
}


def _check_value(name: str, value: str, row: int, report: ValidationReport):
    """Validates one non-empty cell. Returns the typed value or None when invalid."""
    f = schema.field(name)
    constraints = f.get("constraints", {})
    max_length = constraints.get("maxLength")
    if max_length and len(value) > max_length:
        report.add("TOO_LONG", row, name, limit=max_length)
        return None
    return _TYPE_CHECKERS[f["type"]](name, value, row, report, f, constraints)


def _check_row_rules(row_no: int, typed: Dict[str, object], raw: Dict[str, str], today: date, report: ValidationReport):
    updated = typed.get("data_aktualizacji")
    if isinstance(updated, date):
        if updated > today:
            report.add("FUTURE_UPDATE_DATE", row_no, "data_aktualizacji", value=raw["data_aktualizacji"])
        elif updated < today - timedelta(days=STALE_AFTER_DAYS):
            report.add("STALE_UPDATE", row_no, "data_aktualizacji", value=raw["data_aktualizacji"])

    hours = raw.get("godziny_dostepnosci", "")
    if hours and not opening_hours.is_supported(hours):
        report.add("OPENING_HOURS_UNSUPPORTED", row_no, "godziny_dostepnosci", value=_quote(hours))

    if typed.get("status_urzadzenia") == "SPRAWNY":
        for column, code in (("data_waznosci_elektrod", "ELECTRODES_EXPIRED"), ("data_waznosci_baterii", "BATTERY_EXPIRED")):
            expiry = typed.get(column)
            if isinstance(expiry, date) and expiry < today:
                report.add(code, row_no, column, value=raw[column])


# ---------------------------------------------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------------------------------------------


def _check_cells(row_no: int, raw: Dict[str, str], report: ValidationReport) -> Dict[str, object]:
    typed: Dict[str, object] = {}
    for name, value in raw.items():
        if not value:
            if schema.field(name)["x-aed-presence"] == schema.PRESENCE_REQUIRED:
                report.add("REQUIRED_EMPTY", row_no, name)
            continue
        typed_value = _check_value(name, value, row_no, report)
        if typed_value is not None:
            typed[name] = typed_value
    return typed


class _RowsState:
    def __init__(self):
        self.seen_ids: Dict[str, int] = {}
        self.points: List[Tuple[float, float]] = []
        self.point_rows: List[int] = []


def _validate_row(row_no: int, cells: List[str], header_len: int, positions, state: _RowsState, report, today):
    if not any(c.strip() for c in cells):
        report.add("EMPTY_ROW", row_no)
        return
    if len(cells) != header_len:
        report.add("ROW_LENGTH", row_no, actual=len(cells), expected=header_len)
        return
    raw: Dict[str, str] = {name: cells[idx].strip() for idx, name in positions.items()}
    typed = _check_cells(row_no, raw, report)

    id_aed = raw.get("id_aed")
    if id_aed and id_aed in state.seen_ids:
        report.add("DUPLICATE_ID", row_no, "id_aed", value=_quote(id_aed), first_row=state.seen_ids[id_aed])
    elif id_aed:
        state.seen_ids[id_aed] = row_no

    _check_row_rules(row_no, typed, raw, today, report)

    lat, lon = typed.get("szerokosc_geograficzna"), typed.get("dlugosc_geograficzna")
    if lat is not None and lon is not None:
        state.points.append((lat, lon))
        state.point_rows.append(row_no)
    # normalized enums / postal codes replace raw strings
    clean = {**raw, **{k: v for k, v in typed.items() if isinstance(v, str)}}
    report.records.append((row_no, clean))


def validate_rows(rows: List[List[str]], report: ValidationReport, today: date) -> ValidationReport:
    if not rows:
        report.add("EMPTY_FILE")
        return report
    header = rows[0]
    positions = _check_header(header, report)
    state = _RowsState()
    for offset, cells in enumerate(rows[1:]):
        report.rows += 1
        _validate_row(offset + 2, cells, len(header), positions, state, report, today)

    for i, j, distance in close_pairs(state.points, NEAR_DUPLICATE_RADIUS_M):
        report.add(
            "NEAR_DUPLICATE_5M",
            state.point_rows[j],
            "szerokosc_geograficzna",
            distance="{:.1f}".format(distance),
            other_row=state.point_rows[i],
        )
    report.issues.sort(key=lambda i: (i.row or 0, i.level != ERROR))
    return report


def validate_file(
    content: bytes, filename: str, today: Optional[date] = None, max_rows: Optional[int] = None
) -> ValidationReport:
    report = ValidationReport()
    today = today or timezone.localdate()
    max_rows = max_rows or settings.AED_MAX_ROWS
    kind = _file_kind(content, filename or "")
    if kind is None:
        report.add("UNSUPPORTED_FILE")
        return report
    try:
        rows = _read_csv(content, report) if kind == "csv" else _read_xlsx(content, report, max_rows)
    except _FatalFileError:
        return report
    if len(rows) - 1 > max_rows:
        report.add("TOO_MANY_ROWS", limit=max_rows)
        return report
    validate_rows(rows, report, today)
    logger.info("AED validation finished: rows=%s errors=%s warnings=%s", report.rows, report.errors_count, report.warnings_count)
    return report
