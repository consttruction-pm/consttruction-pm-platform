from datetime import date

import pytest

from construction_pm.scheduling.calendar_system import (
    CalendarDateError,
    CalendarSystem,
    JalaliDate,
    gregorian_to_jalali,
    jalali_to_gregorian,
)


def test_calendar_system_contract():
    assert CalendarSystem.GREGORIAN.value == "gregorian"
    assert CalendarSystem.JALALI.value == "jalali"


@pytest.mark.parametrize(
    ("gregorian", "jalali"),
    [
        (date(2021, 3, 21), (1400, 1, 1)),
        (date(2024, 3, 20), (1403, 1, 1)),
        (date(2025, 3, 20), (1403, 12, 30)),
        (date(2026, 3, 21), (1405, 1, 1)),
        (date(2026, 9, 30), (1405, 7, 8)),
    ],
)
def test_known_jalali_gregorian_pairs(gregorian, jalali):
    assert gregorian_to_jalali(gregorian) == jalali
    assert jalali_to_gregorian(*jalali) == gregorian


@pytest.mark.parametrize(
    "value",
    [
        JalaliDate(1400, 1, 1),
        JalaliDate(1403, 12, 30),
        JalaliDate(1405, 7, 8),
    ],
)
def test_jalali_round_trip(value):
    assert JalaliDate.from_gregorian(value.to_gregorian()) == value


@pytest.mark.parametrize(
    "value",
    [
        (1400, 0, 1),
        (1400, 13, 1),
        (1400, 1, 0),
    ],
)
def test_invalid_jalali_dates_are_rejected(value):
    with pytest.raises(CalendarDateError):
        JalaliDate(*value)


def test_jalali_date_is_orderable():
    assert JalaliDate(1405, 1, 1) < JalaliDate(1405, 1, 2)
