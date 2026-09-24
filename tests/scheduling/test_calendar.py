from datetime import date
from decimal import Decimal

import pytest

from construction_pm.scheduling import WorkingCalendar, WorkingTimeResolver


@pytest.fixture
def resolver() -> WorkingTimeResolver:
    return WorkingTimeResolver(
        WorkingCalendar(
            working_weekdays=frozenset({0, 1, 2, 3, 4}),
            holidays=frozenset({date(2026, 9, 23)}),
        )
    )


def test_working_day_and_holiday(resolver: WorkingTimeResolver) -> None:
    assert resolver.is_working_day(date(2026, 9, 21))
    assert not resolver.is_working_day(date(2026, 9, 23))
    assert not resolver.is_working_day(date(2026, 9, 26))


def test_add_working_duration_skips_weekend_and_holiday(resolver: WorkingTimeResolver) -> None:
    assert resolver.add_working_duration(date(2026, 9, 22), 1) == date(2026, 9, 22)
    assert resolver.add_working_duration(date(2026, 9, 22), 2) == date(2026, 9, 24)
    assert resolver.add_working_duration(date(2026, 9, 25), 2) == date(2026, 9, 28)


def test_subtract_working_duration_is_inverse(resolver: WorkingTimeResolver) -> None:
    finish = date(2026, 9, 28)
    assert resolver.subtract_working_duration(finish, 1) == finish
    assert resolver.subtract_working_duration(finish, 2) == date(2026, 9, 25)


def test_calculate_duration_is_inclusive(resolver: WorkingTimeResolver) -> None:
    assert resolver.calculate_duration(date(2026, 9, 21), date(2026, 9, 24)) == 3
    assert resolver.calculate_duration(date(2026, 9, 25), date(2026, 9, 28)) == 2


def test_zero_duration_normalizes_start(resolver: WorkingTimeResolver) -> None:
    assert resolver.add_working_duration(date(2026, 9, 26), Decimal("0")) == date(2026, 9, 28)


def test_fractional_and_negative_duration_are_rejected(resolver: WorkingTimeResolver) -> None:
    with pytest.raises(ValueError):
        resolver.add_working_duration(date(2026, 9, 21), 1.5)
    with pytest.raises(ValueError):
        resolver.subtract_working_duration(date(2026, 9, 21), -1)
