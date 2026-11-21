from datetime import date, datetime, timedelta

import pytest
import pytz

from mcod.aed.readiness import NEEDS_ATTENTION, NOT_READY, READY, UNKNOWN, open_now, readiness

TODAY = date(2026, 11, 21)


def _record(**overrides):
    record = {
        "status_urzadzenia": "SPRAWNY",
        "status_weryfikacji": "ZWERYFIKOWANY",
        "data_waznosci_elektrod": "2028-01-31",
        "data_waznosci_baterii": "2029-01-31",
        "data_ostatniej_kontroli": "2026-11-01",
    }
    record.update(overrides)
    return record


def _days(n: int) -> str:
    return (TODAY + timedelta(days=n)).isoformat()


def test_ready():
    assert readiness(_record(), TODAY) == READY


@pytest.mark.parametrize("status", ["NIESPRAWNY", "CZASOWO_NIEDOSTEPNY", "NIEZNANY", ""])
def test_not_ready_status(status):
    assert readiness(_record(status_urzadzenia=status), TODAY) == NOT_READY


@pytest.mark.parametrize("field", ["data_waznosci_elektrod", "data_waznosci_baterii"])
def test_not_ready_expired(field):
    assert readiness(_record(**{field: _days(-1)}), TODAY) == NOT_READY
    assert readiness(_record(**{field: _days(0)}), TODAY) == NEEDS_ATTENTION  # valid until the end of the day


def test_not_ready_wins_over_unknown():
    assert readiness(_record(data_waznosci_elektrod=_days(-5), status_weryfikacji="WATPLIWY"), TODAY) == NOT_READY


@pytest.mark.parametrize(
    "overrides",
    [
        {"data_waznosci_elektrod": ""},
        {"data_waznosci_baterii": ""},
        {"data_ostatniej_kontroli": ""},
        {"status_weryfikacji": "NIEZWERYFIKOWANY"},
        {"status_weryfikacji": "WATPLIWY"},
    ],
)
def test_unknown(overrides):
    assert readiness(_record(**overrides), TODAY) == UNKNOWN


def test_inspection_boundary_90_days():
    assert readiness(_record(data_ostatniej_kontroli=_days(-90)), TODAY) == READY
    assert readiness(_record(data_ostatniej_kontroli=_days(-91)), TODAY) == UNKNOWN


@pytest.mark.parametrize("field", ["data_waznosci_elektrod", "data_waznosci_baterii"])
def test_attention_boundary_30_days(field):
    assert readiness(_record(**{field: _days(30)}), TODAY) == NEEDS_ATTENTION
    assert readiness(_record(**{field: _days(31)}), TODAY) == READY


def test_unknown_wins_over_attention():
    assert readiness(_record(data_waznosci_elektrod=_days(10), data_ostatniej_kontroli=""), TODAY) == UNKNOWN


def test_open_now_uses_warsaw_time():
    warsaw = pytz.timezone("Europe/Warsaw")
    record = {"godziny_dostepnosci": "Mo-Fr 08:00-16:00"}
    # 07:30 UTC on Monday = 08:30 in Warsaw (CET)
    assert open_now(record, datetime(2026, 11, 23, 7, 30, tzinfo=pytz.utc)) is True
    assert open_now(record, warsaw.localize(datetime(2026, 11, 23, 7, 30))) is False
    assert open_now({"godziny_dostepnosci": "sunrise-sunset"}) is None
