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


def test_gregorian_calendar_rejects_jalali_holiday_input():
    with pytest.raises(ValueError, match="Jalali holiday input"):
        WorkingCalendar.from_calendar_dates(
            system=CalendarSystem.GREGORIAN,
            holidays=[JalaliDate(1405, 7, 8)],
        )


def test_jalali_and_gregorian_resolvers_produce_identical_working_day_arithmetic():
    jalali = WorkingCalendar.from_calendar_dates(
        system=CalendarSystem.JALALI,
        holidays=[JalaliDate(1405, 7, 8)],
    )
    gregorian = WorkingCalendar(
        holidays=frozenset({date(2026, 9, 30)}),
    )
    jalali_resolver = WorkingTimeResolver(jalali)
    gregorian_resolver = WorkingTimeResolver(gregorian)

    assert jalali_resolver.add_working_duration(JalaliDate(1405, 7, 7), 3) == date(2026, 10, 2)
    assert gregorian_resolver.add_working_duration(date(2026, 9, 29), 3) == date(2026, 10, 2)
    assert jalali_resolver.calculate_duration(
        JalaliDate(1405, 7, 7), JalaliDate(1405, 7, 10)
    ) == gregorian_resolver.calculate_duration(date(2026, 9, 29), date(2026, 10, 2))


def test_zero_day_duration_normalizes_start_but_does_not_consume_a_working_day():
    resolver = WorkingTimeResolver(WorkingCalendar())
    assert resolver.add_working_duration(date(2026, 9, 26), 0) == date(2026, 9, 28)


def test_large_day_duration_round_trips_without_fixed_horizon():
    resolver = WorkingTimeResolver(WorkingCalendar())
    start = date(2026, 9, 28)
    finish = resolver.add_working_duration(start, 20000)
    assert resolver.subtract_working_duration(finish, 20000) == start


def test_month_and_year_boundaries_preserve_working_day_count():
    resolver = WorkingTimeResolver(WorkingCalendar())
    assert resolver.calculate_duration(date(2026, 12, 31), date(2027, 1, 1)) == 2
    assert resolver.calculate_duration(date(2026, 3, 20), date(2026, 3, 23)) == 2
