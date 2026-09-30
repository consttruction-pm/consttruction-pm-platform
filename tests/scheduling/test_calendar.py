from datetime import date

import pytest

from construction_pm.scheduling import (
    CalendarSystem,
    JalaliDate,
    WorkingCalendar,
    WorkingTimeResolver,
)


def test_jalali_input_is_converted_to_canonical_gregorian_date():
    calendar = WorkingCalendar.from_calendar_dates(
        system=CalendarSystem.JALALI,
        holidays=[JalaliDate(1405, 7, 8)],
    )
    resolver = WorkingTimeResolver(calendar)
    assert resolver.is_working_day(JalaliDate(1405, 7, 7))
    assert not resolver.is_working_day(JalaliDate(1405, 7, 8))
    assert resolver.normalize_start(JalaliDate(1405, 7, 8)) == date(2026, 10, 1)


def test_jalali_holiday_is_skipped_during_addition_and_subtraction():
    calendar = WorkingCalendar.from_calendar_dates(
        system=CalendarSystem.JALALI,
        holidays=[JalaliDate(1405, 7, 8)],
    )
    resolver = WorkingTimeResolver(calendar)
    assert resolver.add_working_duration(JalaliDate(1405, 7, 7), 2) == date(2026, 10, 1)
    assert resolver.subtract_working_duration(JalaliDate(1405, 7, 9), 2) == date(2026, 9, 29)


def test_jalali_duration_matches_gregorian_duration():
    calendar = WorkingCalendar.from_calendar_dates(system=CalendarSystem.JALALI)
    resolver = WorkingTimeResolver(calendar)
    assert resolver.calculate_duration(JalaliDate(1405, 7, 6), JalaliDate(1405, 7, 8)) == 3
    assert resolver.calculate_duration(date(2026, 9, 28), date(2026, 9, 30)) == 3


def test_gregorian_calendar_rejects_jalali_input():
    resolver = WorkingTimeResolver(WorkingCalendar())
    with pytest.raises(ValueError):
        resolver.normalize_start(JalaliDate(1405, 7, 8))
