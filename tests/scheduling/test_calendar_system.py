import pytest
from datetime import date

from construction_pm.scheduling.calendar_system import (
    CalendarDateError,
    JalaliDate,
    gregorian_to_jalali,
    jalali_to_gregorian,
)


def test_known_jalali_gregorian_pairs():
    pairs = [
        ((1400, 1, 1), date(2021, 3, 21)),
        ((1403, 1, 1), date(2024, 3, 20)),
        ((1403, 12, 30), date(2025, 3, 20)),
        ((1405, 1, 1), date(2026, 3, 21)),
        ((1405, 7, 8), date(2026, 9, 30)),
    ]
    for jalali, gregorian in pairs:
        assert jalali_to_gregorian(*jalali) == gregorian
        assert gregorian_to_jalali(gregorian) == jalali


def test_jalali_date_round_trip_and_ordering():
    first = JalaliDate(1405, 1, 1)
    second = JalaliDate.from_gregorian(date(2026, 9, 30))
    assert first.to_gregorian() == date(2026, 3, 21)
    assert second == JalaliDate(1405, 7, 8)
    assert first < second


def test_invalid_jalali_month_end_is_rejected():
    with pytest.raises(CalendarDateError):
        JalaliDate(1404, 12, 30)


def test_jalali_leap_day_is_accepted_when_valid():
    assert JalaliDate(1403, 12, 30).to_gregorian() == date(2025, 3, 20)


def test_invalid_jalali_month_and_day_are_rejected():
    with pytest.raises(CalendarDateError):
        JalaliDate(1405, 13, 1)
    with pytest.raises(CalendarDateError):
        JalaliDate(1405, 1, 0)


def test_jalali_leap_year_detection_uses_borkowski_cycle():
    assert JalaliDate(1403, 12, 30)
    assert JalaliDate(1404, 12, 29)
    with pytest.raises(CalendarDateError):
        JalaliDate(1404, 12, 30)


def test_gregorian_boundary_round_trip_around_jalali_new_year():
    pairs = [
        (date(2025, 3, 19), (1403, 12, 29)),
        (date(2025, 3, 20), (1403, 12, 30)),
        (date(2025, 3, 21), (1404, 1, 1)),
        (date(2026, 3, 19), (1404, 12, 29)),
        (date(2026, 3, 20), (1404, 12, 30)),
        (date(2026, 3, 21), (1405, 1, 1)),
    ]
    for gregorian, expected in pairs:
        assert gregorian_to_jalali(gregorian) == expected
        assert jalali_to_gregorian(*expected) == gregorian
