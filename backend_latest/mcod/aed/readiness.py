"""
Readiness of an AED computed at request time (never stored in files), in the Europe/Warsaw time zone.

Order of rules:
  NIEGOTOWY     – status_urzadzenia != SPRAWNY, or electrodes/battery already expired
  NIEZNANY      – an expiry date is missing, no inspection within the last 90 days (missing date counts as
                  no inspection), or status_weryfikacji != ZWERYFIKOWANY
  WYMAGA_UWAGI  – electrodes or battery expire within 30 days (inclusive)
  GOTOWY        – otherwise

An expiry date means "valid until the end of that day".
"""

from datetime import date, datetime
from typing import Mapping, Optional

from django.utils import timezone

from mcod.aed import opening_hours

READY = "GOTOWY"
NEEDS_ATTENTION = "WYMAGA_UWAGI"
UNKNOWN = "NIEZNANY"
NOT_READY = "NIEGOTOWY"
READINESS_VALUES = (READY, NEEDS_ATTENTION, UNKNOWN, NOT_READY)

INSPECTION_MAX_AGE_DAYS = 90
EXPIRY_WARNING_DAYS = 30


def _as_date(value) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def today() -> date:
    return timezone.localdate()


def readiness(record: Mapping, on_day: Optional[date] = None) -> str:
    on_day = on_day or today()
    electrodes = _as_date(record.get("data_waznosci_elektrod"))
    battery = _as_date(record.get("data_waznosci_baterii"))
    inspection = _as_date(record.get("data_ostatniej_kontroli"))

    if record.get("status_urzadzenia") != "SPRAWNY":
        return NOT_READY
    if any(d is not None and d < on_day for d in (electrodes, battery)):
        return NOT_READY
    if (
        electrodes is None
        or battery is None
        or inspection is None
        or (on_day - inspection).days > INSPECTION_MAX_AGE_DAYS
        or record.get("status_weryfikacji") != "ZWERYFIKOWANY"
    ):
        return UNKNOWN
    if min(electrodes, battery).toordinal() - on_day.toordinal() <= EXPIRY_WARNING_DAYS:
        return NEEDS_ATTENTION
    return READY


def open_now(record: Mapping, moment: Optional[datetime] = None) -> Optional[bool]:
    """True/False, or None when the opening hours cannot be parsed."""
    moment = timezone.localtime(moment) if moment else timezone.localtime()
    return opening_hours.is_open(record.get("godziny_dostepnosci") or "", moment.replace(tzinfo=None))
