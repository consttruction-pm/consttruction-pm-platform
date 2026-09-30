from datetime import date, datetime, time
from decimal import Decimal

import pytest

from construction_pm.scheduling.time_calendar import TimeAwareWorkingTimeResolver, WorkingTimeCalendar


@pytest.fixture
def resolver() -> TimeAwareWorkingTimeResolver:
    return TimeAwareWorkingTimeResolver(
        WorkingTimeCalendar(
            holidays=frozenset({date(2026, 9, 23)}),
            daily_intervals={weekday: ((time(8), time(12)), (time(13), time(17))) for weekday in range(5)},
        )
    )


def test_fractional_hour_addition_preserves_microsecond_precision(resolver):
    start = datetime(2026, 9, 22, 10, 15, 30, 250000)
    assert resolver.add_working_hours(start, Decimal("1.5")) == datetime(2026, 9, 22, 11, 45, 30, 250000)


def test_fractional_hour_subtraction_preserves_microsecond_precision(resolver):
    finish = datetime(2026, 9, 22, 15, 45, 30, 750000)
    assert resolver.subtract_working_hours(finish, Decimal("1.5")) == datetime(2026, 9, 22, 14, 15, 30, 750000)


def test_calculate_working_hours_across_split_intervals_preserves_fractional_precision(resolver):
    start = datetime(2026, 9, 22, 10, 15, 30, 250000)
    finish = datetime(2026, 9, 22, 15, 45, 30, 750000)
    assert resolver.calculate_working_hours(start, finish) == Decimal("4.500138888888888888888888889")


def test_exact_interval_boundaries_are_deterministic(resolver):
    assert resolver.add_working_hours(datetime(2026, 9, 22, 8), 4) == datetime(2026, 9, 22, 12)
    assert resolver.subtract_working_hours(datetime(2026, 9, 22, 12), 4) == datetime(2026, 9, 22, 8)
    assert resolver.add_working_hours(datetime(2026, 9, 22, 12), 0) == datetime(2026, 9, 22, 13)
    assert resolver.subtract_working_hours(datetime(2026, 9, 22, 13), 0) == datetime(2026, 9, 22, 12)
    assert resolver.add_working_hours(datetime(2026, 9, 22, 17), 0) == datetime(2026, 9, 23, 8)
    assert resolver.subtract_working_hours(datetime(2026, 9, 22, 17), 0) == datetime(2026, 9, 22, 17)


def test_consecutive_holidays_are_skipped_without_fixed_day_assumptions():
    holiday_calendar = WorkingTimeCalendar(
        holidays=frozenset({date(2026, 9, 23), date(2026, 9, 24)}),
        daily_intervals={weekday: ((time(8), time(12)), (time(13), time(17))) for weekday in range(5)},
    )
    holiday_resolver = TimeAwareWorkingTimeResolver(holiday_calendar)

    assert holiday_resolver.add_working_hours(
        datetime(2026, 9, 22, 16), 2
    ) == datetime(2026, 9, 25, 9)
    assert holiday_resolver.subtract_working_hours(
        datetime(2026, 9, 25, 9), 2
    ) == datetime(2026, 9, 22, 16)


def test_working_cursor_round_trip_is_exact_at_interval_edges(resolver):
    start = datetime(2026, 9, 22, 8)
    finish = resolver.add_working_hours(start, Decimal("8"))
    assert finish == datetime(2026, 9, 22, 17)
    assert resolver.subtract_working_hours(finish, Decimal("8")) == start
