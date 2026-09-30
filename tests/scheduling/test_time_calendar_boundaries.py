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
    assert resolver.add_working_hours(datetime(2026, 9, 22, 17), 0) == datetime(2026, 9, 24, 8)
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


def test_duration_more_precise_than_one_microsecond_is_rejected(resolver):
    with pytest.raises(ValueError, match="more precise"):
        resolver.add_working_hours(datetime(2026, 9, 22, 8), Decimal("0.0000000001"))


def test_non_finite_duration_is_rejected(resolver):
    with pytest.raises(ValueError, match="finite"):
        resolver.add_working_hours(datetime(2026, 9, 22, 8), Decimal("NaN"))


def test_long_duration_is_not_limited_to_ten_year_horizon(resolver):
    finish = resolver.add_working_hours(datetime(2026, 9, 22, 8), Decimal("20000"))
    assert resolver.subtract_working_hours(finish, Decimal("20000")) == datetime(2026, 9, 22, 8)


def test_timezone_aware_datetime_keeps_timezone_information(resolver):
    from datetime import timezone

    start = datetime(2026, 9, 22, 10, tzinfo=timezone.utc)
    finish = resolver.add_working_hours(start, 1)
    assert finish == datetime(2026, 9, 22, 11, tzinfo=timezone.utc)


def test_calendar_without_any_working_intervals_is_rejected():
    with pytest.raises(ValueError, match="at least one working interval"):
        TimeAwareWorkingTimeResolver(
            WorkingTimeCalendar(
                working_weekdays=frozenset({0, 1, 2, 3, 4}),
                daily_intervals={},
            )
        )
