"""
AED data standard v1 – single source of truth.

All lists of fields, enums, forbidden headers, file rules and examples are read from ``aed_v1.json``.
Other modules (validator, templates, XLSX export, API) must use the helpers below instead of
repeating field names.
"""

import copy
import json
import os
import unicodedata
from functools import lru_cache
from typing import Dict, List, Optional

SCHEMA_VERSION = "AED_V1"
SCHEMA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aed_v1.json")

PRESENCE_REQUIRED = "required"
PRESENCE_IF_KNOWN = "if_known"
PRESENCE_EXTENDED = "extended"
PRESENCES = (PRESENCE_REQUIRED, PRESENCE_IF_KNOWN, PRESENCE_EXTENDED)

PRESENCE_LABELS = {
    PRESENCE_REQUIRED: {"pl": "wymagane", "en": "required"},
    PRESENCE_IF_KNOWN: {"pl": "jeśli znane", "en": "if known"},
    PRESENCE_EXTENDED: {"pl": "rozszerzone (opcjonalna kolumna)", "en": "extended (optional column)"},
}

TYPE_FORMATS = {
    "string": {"pl": "tekst", "en": "text"},
    "number": {"pl": "liczba z kropką dziesiętną", "en": "number with a dot as decimal separator"},
    "integer": {"pl": "liczba całkowita", "en": "integer"},
    "boolean": {"pl": "true / false", "en": "true / false"},
    "date": {"pl": "RRRR-MM-DD", "en": "YYYY-MM-DD"},
}

_POLISH_EXTRA = str.maketrans({"ł": "l", "Ł": "l"})


@lru_cache(maxsize=1)
def _load() -> dict:
    with open(SCHEMA_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_schema() -> dict:
    """Return a deep copy of the full schema (safe to modify by the caller)."""
    return copy.deepcopy(_load())


def fields() -> List[dict]:
    return _load()["fields"]


def field_names(presences=PRESENCES) -> List[str]:
    return [f["name"] for f in fields() if f["x-aed-presence"] in presences]


def core_field_names() -> List[str]:
    """Columns that must exist in every file (required + if known)."""
    return field_names((PRESENCE_REQUIRED, PRESENCE_IF_KNOWN))


def required_field_names() -> List[str]:
    return field_names((PRESENCE_REQUIRED,))


def extended_field_names() -> List[str]:
    return field_names((PRESENCE_EXTENDED,))


def all_field_names() -> List[str]:
    return field_names()


def field(name: str) -> Optional[dict]:
    return _fields_by_name().get(name)


@lru_cache(maxsize=1)
def _fields_by_name() -> Dict[str, dict]:
    return {f["name"]: f for f in fields()}


def enums() -> Dict[str, List[str]]:
    return {f["name"]: f["constraints"]["enum"] for f in fields() if "enum" in f.get("constraints", {})}


def enum_labels(name: str) -> Dict[str, Dict[str, str]]:
    return (field(name) or {}).get("x-aed-enum-labels", {})


def forbidden_field_names() -> List[str]:
    return list(_load()["x-aed-forbidden-fields"])


def forbidden_reason() -> Dict[str, str]:
    return dict(_load()["x-aed-forbidden-reason"])


def source_priority() -> List[str]:
    return list(_load()["x-aed-source-priority"])


def file_rules() -> List[Dict[str, str]]:
    return list(_load()["x-aed-file-rules"])


def examples() -> List[Dict[str, str]]:
    return copy.deepcopy(_load()["x-aed-examples"])


def normalize_header(value) -> str:
    """
    Normalise a column header for comparisons: lower case, no Polish diacritics,
    spaces and dashes replaced with underscores. Used to detect forbidden columns
    regardless of letter case and Polish characters (e.g. "Hasło" -> "haslo").
    """
    text = str(value or "").strip().translate(_POLISH_EXTRA).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    for ch in (" ", "-", "."):
        text = text.replace(ch, "_")
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_")


def is_forbidden_header(value) -> bool:
    return normalize_header(value) in {normalize_header(f) for f in forbidden_field_names()}


def frictionless_schema() -> dict:
    """
    Schema stripped to plain Frictionless Table Schema keys (titles/descriptions in Polish),
    useful for generic tools (e.g. goodtables). The full schema with x-aed-* is in ``load_schema()``.
    """
    plain_fields = []
    for f in fields():
        item = {
            "name": f["name"],
            "type": f["type"],
            "title": f["title"]["pl"],
            "description": f["description"]["pl"],
            "constraints": dict(f.get("constraints", {})),
        }
        for key in ("format", "trueValues", "falseValues"):
            if key in f:
                item[key] = f[key]
        plain_fields.append(item)
    return {"fields": plain_fields, "primaryKey": _load()["primaryKey"], "missingValues": _load()["missingValues"]}
