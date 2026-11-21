from datetime import date, datetime

import pytest

from mcod.aed import opening_hours as oh

MONDAY = datetime(2026, 11, 23, 10, 0)  # regular Monday
SATURDAY = datetime(2026, 11, 21, 10, 0)
INDEPENDENCE_DAY = datetime(2026, 11, 11, 10, 0)  # Wednesday, public holiday


@pytest.mark.parametrize(
    "value",
    [
        "24/7",
        "Mo-Fr 08:00-16:00",
        "Mo-Fr 08:00-16:00; PH off",
        "Mo-Fr 08:00-12:00,13:00-16:00; Sa 09:00-13:00",
        "Mo,We,Fr 07:00-15:00",
        "Fr-Mo 10:00-20:00",
        "22:00-06:00",
        "Mo-Su 00:00-24:00",
        "Mo-Fr 08:00-16:00; Sa,Su off; PH closed",
        "Mo-Fr",
    ],
)
def test_supported(value):
    assert oh.is_supported(value)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "sunrise-sunset",
        "Mo-Fr 8-16",
        "Jan-Mar Mo 08:00-10:00",
        'Mo-Fr 08:00-16:00 "po uzgodnieniu"',
        "Pn-Pt 08:00-16:00",
        "Mo-Fr 16:00-16:00",
        "Mo-Fr 25:00-26:00",
        "PH",
    ],
)
def test_unsupported(value):
    assert not oh.is_supported(value)
    assert oh.is_open(value, MONDAY) is None


def test_24_7_always_open():
    assert oh.is_open("24/7", INDEPENDENCE_DAY)
    assert oh.parse("Mo-Su 00:00-24:00").always_open


def test_weekday_range():
    assert oh.is_open("Mo-Fr 08:00-16:00", MONDAY)
    assert not oh.is_open("Mo-Fr 08:00-16:00", SATURDAY)
    assert not oh.is_open("Mo-Fr 08:00-16:00", MONDAY.replace(hour=16))  # end exclusive
    assert oh.is_open("Mo-Fr 08:00-16:00", MONDAY.replace(hour=8))


def test_several_ranges_and_rules():
    value = "Mo-Fr 08:00-12:00,13:00-16:00; Sa 09:00-13:00"
    assert not oh.is_open(value, MONDAY.replace(hour=12, minute=30))
    assert oh.is_open(value, SATURDAY)
    assert oh.is_open("Mo-Fr 08:00-16:00; We off", MONDAY)
    assert not oh.is_open("Mo-Su 08:00-16:00; Mo off", MONDAY)  # later rule wins


def test_past_midnight():
    assert oh.is_open("Mo 22:00-06:00", MONDAY.replace(hour=23))
    assert oh.is_open("Mo 22:00-06:00", datetime(2026, 11, 24, 5, 59))  # Tuesday morning
    assert not oh.is_open("Mo 22:00-06:00", datetime(2026, 11, 24, 6, 0))


def test_wrapping_weekday_range():
    assert oh.is_open("Fr-Mo 10:00-20:00", MONDAY)
    assert not oh.is_open("Fr-Mo 10:00-20:00", datetime(2026, 11, 25, 10, 0))


def test_public_holidays():
    assert not oh.is_open("Mo-Fr 08:00-16:00; PH off", INDEPENDENCE_DAY)
    assert oh.is_open("Mo-Fr 08:00-16:00", INDEPENDENCE_DAY)  # PH not specified -> normal day
    assert oh.is_open("Mo-Fr off; PH 09:00-12:00", INDEPENDENCE_DAY)


def test_polish_holidays():
    holidays = oh.polish_public_holidays(2026)
    assert date(2026, 4, 5) in holidays  # Easter Sunday 2026
    assert date(2026, 4, 6) in holidays
    assert date(2026, 6, 4) in holidays  # Corpus Christi
    assert date(2026, 12, 24) in holidays
    assert date(2024, 12, 24) not in oh.polish_public_holidays(2024)
    assert len(holidays) == 14
