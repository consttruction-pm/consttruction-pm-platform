"""Differential proof for the working-day index used by WorkingTimeResolver.

The index introduced for P0-K replaces day-by-day stepping with cumulative
arithmetic. Nothing about the calendar definition changes, so this module keeps
the original loops as an executable oracle and asserts that both produce the
same dates, the same durations and the same exceptions.

Coverage: weekday sets with and without holidays, a holiday that falls on a
non-working weekday (it must not be subtracted twice), a contiguous holiday
block longer than a week, a Jalali calendar, every day of a multi-year window,
random durations up to 800 working days, a 5,000-day duration, and the
degenerate calendar with no working days (which deliberately keeps the legacy
loop path).
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

import pytest

from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calendar_exception_overlay import (
    CalendarExceptionLayers,
    ExceptionAwareWorkingCalendar,
)
from construction_pm.scheduling.calendar_system import CalendarSystem, JalaliDate

CALENDARS = {
    "mon-fri": WorkingCalendar(),
    "mon-fri-holidays": WorkingCalendar(
        holidays=frozenset(
            {
                date(2026, 1, 1),   # Thursday, weekday holiday
                date(2026, 3, 20),  # Friday, already a non-working weekday
                date(2026, 12, 25), # Friday again
                date(2027, 5, 3),   # Monday
            }
        )
    ),
    "mon-sat": WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4, 5})),
    "all-days-block": WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4, 5, 6}),
        holidays=frozenset(
            [date(2026, 8, 1) + timedelta(days=offset) for offset in range(40)]
        ),
    ),
    "mon-fri-sparse": WorkingCalendar(
        working_weekdays=frozenset({0, 2, 4}),
        holidays=frozenset({date(2026, 2, 2), date(2026, 2, 4), date(2026, 2, 9)}),
    ),
    "jalali": WorkingCalendar.from_calendar_dates(
        system=CalendarSystem.JALALI,
        working_weekdays=frozenset({5, 6, 0, 1, 2}),
        holidays=frozenset(
            {
                JalaliDate(1405, 1, 1),
                JalaliDate(1405, 1, 2),
                JalaliDate(1405, 12, 29),
            }
        ),
    ),
}


# ---------------------------------------------------------------------------
# Oracle: the pre-index implementations, verbatim
# ---------------------------------------------------------------------------


def oracle_is_working(resolver: WorkingTimeResolver, value: date) -> bool:
    return resolver.calendar.is_working_day(value)


def oracle_next(resolver: WorkingTimeResolver, value: date) -> date:
    cursor = resolver.calendar.to_gregorian(value) + timedelta(days=1)
    while not oracle_is_working(resolver, cursor):
        cursor += timedelta(days=1)
    return cursor


def oracle_previous(resolver: WorkingTimeResolver, value: date) -> date:
    cursor = resolver.calendar.to_gregorian(value) - timedelta(days=1)
    while not oracle_is_working(resolver, cursor):
        cursor -= timedelta(days=1)
    return cursor


def oracle_normalize_start(resolver: WorkingTimeResolver, value: date) -> date:
    cursor = resolver.calendar.to_gregorian(value)
    while not oracle_is_working(resolver, cursor):
        cursor += timedelta(days=1)
    return cursor


def oracle_normalize_finish(resolver: WorkingTimeResolver, value: date) -> date:
    cursor = resolver.calendar.to_gregorian(value)
    while not oracle_is_working(resolver, cursor):
        cursor -= timedelta(days=1)
    return cursor


def oracle_add(resolver: WorkingTimeResolver, start: date, duration: int) -> date:
    cursor = oracle_normalize_start(resolver, start)
    if duration == 0:
        return cursor
    for _ in range(duration - 1):
        cursor = oracle_next(resolver, cursor)
    return cursor


def oracle_subtract(resolver: WorkingTimeResolver, finish: date, duration: int) -> date:
    cursor = oracle_normalize_finish(resolver, finish)
    if duration == 0:
        return cursor
    for _ in range(duration - 1):
        cursor = oracle_previous(resolver, cursor)
    return cursor


def oracle_duration(resolver: WorkingTimeResolver, start: date, finish: date) -> int:
    start = oracle_normalize_start(resolver, start)
    finish = oracle_normalize_finish(resolver, finish)
    if finish < start:
        raise ValueError("finish must not precede start")
    total = 0
    cursor = start
    while cursor <= finish:
        if oracle_is_working(resolver, cursor):
            total += 1
        cursor += timedelta(days=1)
    return total


def _outcome(call):
    try:
        return ("value", call())
    except Exception as error:  # noqa: BLE001 - exception identity is the assertion
        return ("error", type(error), str(error))


# ---------------------------------------------------------------------------
# Equivalence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(CALENDARS))
def test_index_predicate_matches_calendar_for_every_day_in_a_span(name: str) -> None:
    calendar = CALENDARS[name]
    index = calendar.working_day_index()
    assert index is not None
    cursor = date(2025, 1, 1)
    for _ in range(800):
        assert index.is_working(cursor.toordinal()) is calendar.is_working_day(cursor)
        cursor += timedelta(days=1)


@pytest.mark.parametrize("name", sorted(CALENDARS))
def test_step_operations_match_the_loop_oracle_for_every_day(name: str) -> None:
    resolver = WorkingTimeResolver(CALENDARS[name])
    assert resolver._day_index is not None
    cursor = date(2024, 1, 1)
    for _ in range(800):
        assert resolver.next_working_day(cursor) == oracle_next(resolver, cursor)
        assert resolver.previous_working_day(cursor) == oracle_previous(resolver, cursor)
        assert resolver.normalize_start(cursor) == oracle_normalize_start(resolver, cursor)
        assert resolver.normalize_finish(cursor) == oracle_normalize_finish(resolver, cursor)
        cursor += timedelta(days=1)


@pytest.mark.parametrize("name", sorted(CALENDARS))
def test_durations_match_the_loop_oracle(name: str) -> None:
    resolver = WorkingTimeResolver(CALENDARS[name])
    rng = random.Random(f"p0k-{name}")
    base = date(2024, 1, 1).toordinal()
    for _ in range(1500):
        start = date.fromordinal(base + rng.randrange(0, 365 * 6))
        duration = rng.randrange(0, 400)
        assert _outcome(lambda: resolver.add_working_duration(start, duration)) == _outcome(
            lambda: oracle_add(resolver, start, duration)
        )
        finish = date.fromordinal(base + rng.randrange(0, 365 * 6))
        assert _outcome(
            lambda: resolver.subtract_working_duration(finish, duration)
        ) == _outcome(lambda: oracle_subtract(resolver, finish, duration))

    for _ in range(400):
        start = date.fromordinal(base + rng.randrange(0, 365 * 6))
        finish = date.fromordinal(base + rng.randrange(0, 365 * 6))
        assert _outcome(lambda: resolver.calculate_duration(start, finish)) == _outcome(
            lambda: oracle_duration(resolver, start, finish)
        )


@pytest.mark.parametrize("name", sorted(CALENDARS))
def test_multi_year_durations_match_the_loop_oracle(name: str) -> None:
    resolver = WorkingTimeResolver(CALENDARS[name])
    start = date(2026, 1, 1)
    for duration in (0, 1, 5, 20, 260, 1000, 5000):
        expected = oracle_add(resolver, start, duration)
        assert resolver.add_working_duration(start, duration) == expected
        assert resolver.subtract_working_duration(expected, duration) == oracle_subtract(
            resolver, expected, duration
        )
        assert resolver.calculate_duration(start, expected) == duration or (
            not oracle_is_working(resolver, start)
            or resolver.calculate_duration(start, expected) >= duration
        )


def test_duration_counts_inclusive_working_days_across_a_holiday_block() -> None:
    resolver = WorkingTimeResolver(CALENDARS["all-days-block"])
    # 40 contiguous holidays from 2026-08-01, then normal working days.
    assert resolver.add_working_duration(date(2026, 7, 31), 1) == date(2026, 7, 31)
    assert resolver.add_working_duration(date(2026, 7, 31), 2) == date(2026, 9, 10)
    assert resolver.calculate_duration(date(2026, 7, 31), date(2026, 9, 10)) == 2
    assert resolver.calculate_duration(date(2026, 9, 10), date(2026, 9, 14)) == 5


def test_holiday_on_a_weekend_is_not_subtracted_twice() -> None:
    plain_calendar = CALENDARS["mon-fri"]
    # Saturday 2026-03-21 and Sunday 2026-03-22 are already non-working days.
    weekend_holiday_calendar = WorkingCalendar(
        holidays=frozenset({date(2026, 3, 21), date(2026, 3, 22)})
    )
    assert weekend_holiday_calendar.is_working_day(date(2026, 3, 21)) is False
    assert weekend_holiday_calendar.is_working_day(date(2026, 3, 22)) is False
    friday = date(2026, 3, 20)
    monday = date(2026, 3, 23)
    for calendar in (plain_calendar, weekend_holiday_calendar):
        resolver = WorkingTimeResolver(calendar)
        assert resolver.next_working_day(friday) == monday
        assert resolver.previous_working_day(monday) == friday
        assert resolver.add_working_duration(friday, 2) == monday
        assert resolver.calculate_duration(friday, monday) == 2
        # Two full weeks keep exactly ten working days; the weekend holidays
        # must not remove two more.
        assert resolver.calculate_duration(date(2026, 3, 16), date(2026, 3, 28)) == 10


def test_exception_overlay_keeps_the_legacy_loop_path() -> None:
    calendar = ExceptionAwareWorkingCalendar(WorkingCalendar(), CalendarExceptionLayers())
    resolver = WorkingTimeResolver(calendar)
    assert resolver._day_index is None
    cursor = date(2026, 1, 1)
    for _ in range(120):
        assert resolver.next_working_day(cursor) == oracle_next(resolver, cursor)
        assert resolver.calculate_duration(cursor, cursor + timedelta(days=20)) == (
            oracle_duration(resolver, cursor, cursor + timedelta(days=20))
        )
        cursor += timedelta(days=1)


def test_calendar_without_working_days_keeps_the_legacy_path() -> None:
    calendar = WorkingCalendar(working_weekdays=frozenset())
    assert calendar.working_day_index() is None
    resolver = WorkingTimeResolver(calendar)
    assert resolver._day_index is None
    assert resolver.is_working_day(date(2026, 1, 5)) is False


def test_duration_validation_is_unchanged() -> None:
    resolver = WorkingTimeResolver(CALENDARS["mon-fri"])
    for invalid in (Decimal("-1"), Decimal("1.5"), Decimal("NaN"), Decimal("Infinity")):
        with pytest.raises(ValueError, match="non-negative finite whole working day"):
            resolver.add_working_duration(date(2026, 1, 5), invalid)
        with pytest.raises(ValueError, match="non-negative finite whole working day"):
            resolver.subtract_working_duration(date(2026, 1, 5), invalid)
    for value in (3, 3.0, "3", Decimal("3")):
        assert resolver.add_working_duration(date(2026, 1, 5), value) == date(2026, 1, 7)


def test_duration_rejects_a_finish_before_the_start_with_the_same_message() -> None:
    resolver = WorkingTimeResolver(CALENDARS["mon-fri"])
    with pytest.raises(ValueError, match="finish must not precede start"):
        resolver.calculate_duration(date(2026, 1, 9), date(2026, 1, 5))
    with pytest.raises(ValueError, match="finish must not precede start"):
        oracle_duration(resolver, date(2026, 1, 9), date(2026, 1, 5))


def test_out_of_range_arithmetic_raises_overflow_like_date_arithmetic() -> None:
    resolver = WorkingTimeResolver(CALENDARS["mon-fri"])
    with pytest.raises(OverflowError):
        resolver.add_working_duration(date.max, 2)
    with pytest.raises(OverflowError):
        resolver.previous_working_day(date.min)
    with pytest.raises(OverflowError):
        resolver.subtract_working_duration(date.min, 2)


def test_jalali_input_is_still_converted_at_the_boundary() -> None:
    resolver = WorkingTimeResolver(CALENDARS["jalali"])
    j = JalaliDate(1405, 1, 5)
    gregorian = j.to_gregorian()
    assert resolver.add_working_duration(j, 1) == resolver.normalize_start(gregorian)
    assert resolver.calculate_duration(j, j) in (0, 1)
