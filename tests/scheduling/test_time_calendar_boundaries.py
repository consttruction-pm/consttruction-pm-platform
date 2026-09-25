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


def test_fractional_hour_addition_preserves_microsecond_precision(resolver):
    start = datetime(2026, 9, 22, 10, 15, 30, 250000)
    assert resolver.add_working_hours(start, Decimal("1.5")) == datetime(
        2026, 9, 22, 11, 45, 30, 250000
    )


def test_fractional_hour_subtraction_preserves_microsecond_precision(resolver):
    finish = datetime(2026, 9, 22, 15, 45, 30, 750000)
    assert resolver.subtract_working_hours(finish, Decimal("1.5")) == datetime(
        2026, 9, 22, 14, 15, 30, 750000
    )


def test_calculate_working_hours_across_split_intervals_is_exact(resolver):
    assert resolver.calculate_working_hours(
        datetime(2026, 9, 22, 11, 30), datetime(2026, 9, 22, 14, 30)
    ) == Decimal("2")


def test_invalid_interval_order_is_rejected():
    with pytest.raises(ValueError, match="working interval start must precede end"):
        WorkingTimeCalendar(
            daily_intervals={0: ((time(17), time(8)),)},
        )


def test_overlapping_intervals_are_rejected():
    with pytest.raises(ValueError, match="working intervals must not overlap"):
        WorkingTimeCalendar(
            daily_intervals={0: ((time(8), time(12)), (time(11), time(17)))},
        )
