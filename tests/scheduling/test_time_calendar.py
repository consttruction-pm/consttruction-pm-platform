from datetime import date, datetime, time
from decimal import Decimal

import pytest

from construction_pm.scheduling.time_calendar import (
    TimeAwareWorkingTimeResolver,
    WorkingTimeCalendar,
)


@pytest.fixture
def resolver() -> TimeAwareWorkingTimeResolver:
    return TimeAwareWorkingTimeResolver(
        WorkingTimeCalendar(
            holidays=frozenset({date(2026, 9, 23)}),
            daily_intervals={
                0: ((time(8), time(12)), (time(13), time(17))),
                1: ((time(8), time(12)), (time(13), time(17))),
                2: ((time(8), time(12)), (time(13), time(17))),
                3: ((time(8), time(12)), (time(13), time(17))),
                4: ((time(8), time(12)), (time(13), time(17))),
            },
        )
    )


def test_intervals_are_validated_and_holidays_are_non_working(resolver):
    assert resolver.calendar.intervals_for(date(2026, 9, 23)) == ()
    assert resolver.is_working_datetime(datetime(2026, 9, 22, 9))
    assert not resolver.is_working_datetime(datetime(2026, 9, 22, 12, 30))


def test_normalize_start_skips_break_and_holiday(resolver):
    assert resolver.normalize_start(datetime(2026, 9, 22, 12, 30)) == datetime(2026, 9, 22, 13)
    assert resolver.normalize_start(datetime(2026, 9, 23, 9)) == datetime(2026, 9, 24, 8)


def test_add_working_hours_consumes_multiple_intervals_and_holiday(resolver):
    assert resolver.add_working_hours(datetime(2026, 9, 22, 10), 3) == datetime(2026, 9, 22, 14)
    assert resolver.add_working_hours(datetime(2026, 9, 22, 16), 2) == datetime(2026, 9, 24, 9)


def test_calculate_working_hours_is_decimal_and_deterministic(resolver):
    assert resolver.calculate_working_hours(
        datetime(2026, 9, 22, 10), datetime(2026, 9, 22, 16)
    ) == Decimal("5")
    assert resolver.calculate_working_hours(
        datetime(2026, 9, 22, 10), datetime(2026, 9, 24, 10)
    ) == Decimal("8")


def test_negative_working_hours_are_rejected(resolver):
    with pytest.raises(ValueError):
        resolver.add_working_hours(datetime(2026, 9, 22, 8), -1)


def test_normalize_finish_preserves_interval_end_and_normalizes_after_break(resolver):
    assert resolver.normalize_finish(datetime(2026, 9, 22, 12)) == datetime(2026, 9, 22, 12)
    assert resolver.normalize_finish(datetime(2026, 9, 22, 12, 30)) == datetime(2026, 9, 22, 12)


def test_add_working_hours_from_interval_end_crosses_break(resolver):
    assert resolver.add_working_hours(datetime(2026, 9, 22, 12), 1) == datetime(2026, 9, 22, 14)


def test_subtract_working_hours_across_break_and_holiday(resolver):
    assert resolver.subtract_working_hours(datetime(2026, 9, 24, 9), 2) == datetime(2026, 9, 22, 16)


def test_zero_duration_does_not_cross_nonworking_boundary(resolver):
    assert resolver.add_working_hours(datetime(2026, 9, 22, 12), 0) == datetime(2026, 9, 22, 13)
    assert resolver.subtract_working_hours(datetime(2026, 9, 22, 13), 0) == datetime(2026, 9, 22, 12)


def test_add_then_subtract_preserves_working_cursor_for_fractional_hours(resolver):
    start = datetime(2026, 9, 22, 10, 15, 30, 123456)
    duration = Decimal("2.375")
    finish = resolver.add_working_hours(start, duration)
    assert finish == datetime(2026, 9, 22, 13, 37, 30, 123456)
    assert resolver.subtract_working_hours(finish, duration) == start


def test_subtract_then_add_preserves_working_cursor_for_fractional_hours(resolver):
    finish = datetime(2026, 9, 24, 9, 15, 30, 654321)
    duration = Decimal("2.375")
    start = resolver.subtract_working_hours(finish, duration)
    assert start == datetime(2026, 9, 22, 15, 50, 30, 654321)
    assert resolver.add_working_hours(start, duration) == finish


def test_calculate_working_hours_matches_addition_across_split_intervals(resolver):
    start = datetime(2026, 9, 22, 10, 15, 30, 123456)
    duration = Decimal("2.375")
    finish = resolver.add_working_hours(start, duration)
    assert resolver.calculate_working_hours(start, finish) == duration


def test_calculate_working_hours_matches_subtraction_across_holiday(resolver):
    finish = datetime(2026, 9, 24, 9, 15, 30, 654321)
    duration = Decimal("2.375")
    start = resolver.subtract_working_hours(finish, duration)
    assert resolver.calculate_working_hours(start, finish) == duration
