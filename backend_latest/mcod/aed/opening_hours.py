"""
Parser of a subset of the OpenStreetMap ``opening_hours`` syntax.

Supported:
  * ``24/7``
  * weekday selectors: ``Mo``..``Su``, ranges (``Mo-Fr``, also wrapping ``Fr-Mo``) and lists (``Mo-Fr,Su``)
  * time ranges ``HH:MM-HH:MM`` (``24:00`` allowed as an end), several per rule (``08:00-12:00,13:00-16:00``),
    ranges past midnight (``22:00-06:00``) belonging to the day they start
  * a rule without a weekday selector applies to every day (``08:00-16:00``)
  * ``off`` / ``closed`` after a selector
  * several rules separated with ``;`` – a later rule replaces earlier ones for the days it selects
  * ``PH off`` / ``PH closed`` (public holidays in Poland), ``PH`` with time ranges, ``PH 24/7``

Anything else raises ``UnsupportedOpeningHours`` – the validator reports it as a WARNING and the API returns
``otwarte_teraz = null``.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Dict, List, Optional, Set, Tuple

DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
MINUTES_IN_DAY = 24 * 60

_TIME_RANGE_RE = re.compile(r"^([01]\d|2[0-4]):([0-5]\d)-([01]\d|2[0-4]):([0-5]\d)$")
_DAY_SELECTOR_RE = re.compile(
    r"^(Mo|Tu|We|Th|Fr|Sa|Su)(-(Mo|Tu|We|Th|Fr|Sa|Su))?(,(Mo|Tu|We|Th|Fr|Sa|Su)(-(Mo|Tu|We|Th|Fr|Sa|Su))?)*$"
)

TimeRange = Tuple[int, int]  # minutes from midnight, end may exceed 24:00 for ranges past midnight


class UnsupportedOpeningHours(ValueError):
    pass


@dataclass
class OpeningHours:
    always_open: bool = False
    # weekday index (0 = Monday) -> list of ranges; missing key = closed
    week: Dict[int, List[TimeRange]] = field(default_factory=dict)
    # None = public holidays not specified (treated as normal days)
    holidays: Optional[List[TimeRange]] = None

    def _ranges_for(self, day: date) -> List[TimeRange]:
        if self.holidays is not None and is_polish_public_holiday(day):
            return self.holidays
        return self.week.get(day.weekday(), [])

    def is_open(self, moment: datetime) -> bool:
        if self.always_open:
            return True
        minute = moment.hour * 60 + moment.minute
        today = moment.date()
        for start, end in self._ranges_for(today):
            if start <= minute < min(end, MINUTES_IN_DAY):
                return True
        yesterday = today - timedelta(days=1)
        for start, end in self._ranges_for(yesterday):
            if end > MINUTES_IN_DAY and minute < end - MINUTES_IN_DAY:
                return True
        return False


def _parse_days(selector: str) -> Set[int]:
    if not _DAY_SELECTOR_RE.match(selector):
        raise UnsupportedOpeningHours(selector)
    result: Set[int] = set()
    for part in selector.split(","):
        if "-" in part:
            first, last = (DAYS.index(p) for p in part.split("-"))
            idx = first
            while True:
                result.add(idx)
                if idx == last:
                    break
                idx = (idx + 1) % 7
        else:
            result.add(DAYS.index(part))
    return result


def _parse_times(value: str) -> List[TimeRange]:
    if value == "24/7":
        return [(0, MINUTES_IN_DAY)]
    ranges = []
    for part in value.split(","):
        match = _TIME_RANGE_RE.match(part.strip())
        if not match:
            raise UnsupportedOpeningHours(value)
        start = int(match.group(1)) * 60 + int(match.group(2))
        end = int(match.group(3)) * 60 + int(match.group(4))
        if start >= MINUTES_IN_DAY or end > MINUTES_IN_DAY or start == end:
            raise UnsupportedOpeningHours(value)
        if end < start:  # past midnight
            end += MINUTES_IN_DAY
        ranges.append((start, end))
    return ranges


def _parse_rule(rule: str) -> Tuple[Optional[Set[int]], bool, List[TimeRange]]:
    """Returns (days or None for all days, is_public_holiday_rule, ranges)."""
    tokens = rule.split()
    if not tokens:
        raise UnsupportedOpeningHours(rule)
    is_ph = tokens[0] == "PH"
    days: Optional[Set[int]] = None
    if is_ph:
        tokens = tokens[1:]
    elif tokens[0][:2] in DAYS:
        days = _parse_days(tokens[0])
        tokens = tokens[1:]
    if len(tokens) != 1:
        if not tokens and days is not None:  # "Mo-Fr" alone means open all day in OSM
            return days, is_ph, [(0, MINUTES_IN_DAY)]
        raise UnsupportedOpeningHours(rule)
    value = tokens[0]
    if value in ("off", "closed"):
        return days, is_ph, []
    return days, is_ph, _parse_times(value)


@lru_cache(maxsize=4096)
def parse(text: str) -> OpeningHours:
    value = (text or "").strip()
    if not value:
        raise UnsupportedOpeningHours(text)
    if value == "24/7":
        return OpeningHours(always_open=True)
    result = OpeningHours()
    for raw_rule in value.split(";"):
        rule = raw_rule.strip()
        if not rule:
            continue
        days, is_ph, ranges = _parse_rule(rule)
        if is_ph:
            result.holidays = ranges
            continue
        for day in days if days is not None else range(7):
            result.week[day] = list(ranges)
    full_week = all(result.week.get(d) == [(0, MINUTES_IN_DAY)] for d in range(7))
    if full_week and result.holidays in (None, [(0, MINUTES_IN_DAY)]):
        return OpeningHours(always_open=True)
    return result


def is_supported(text: str) -> bool:
    try:
        parse(text)
    except UnsupportedOpeningHours:
        return False
    return True


def is_open(text: str, moment: datetime) -> Optional[bool]:
    """True/False, or None when the value cannot be parsed."""
    try:
        return parse(text).is_open(moment)
    except UnsupportedOpeningHours:
        return None


def _easter_sunday(year: int) -> date:
    # Anonymous Gregorian algorithm (Meeus/Jones/Butcher)
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month, day = divmod(h + m - 7 * n + 114, 31)
    return date(year, month, day + 1)


@lru_cache(maxsize=64)
def polish_public_holidays(year: int) -> Set[date]:
    """Statutory public holidays in Poland (ustawa o dniach wolnych od pracy)."""
    easter = _easter_sunday(year)
    holidays = {
        date(year, 1, 1),
        date(year, 1, 6),
        easter,
        easter + timedelta(days=1),
        date(year, 5, 1),
        date(year, 5, 3),
        easter + timedelta(days=49),  # Zielone Świątki
        easter + timedelta(days=60),  # Boże Ciało
        date(year, 8, 15),
        date(year, 11, 1),
        date(year, 11, 11),
        date(year, 12, 25),
        date(year, 12, 26),
    }
    if year >= 2025:
        holidays.add(date(year, 12, 24))
    return holidays


def is_polish_public_holiday(day: date) -> bool:
    return day in polish_public_holidays(day.year)
