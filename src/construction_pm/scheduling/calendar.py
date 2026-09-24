from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import FrozenSet, Iterable


@dataclass(frozen=True)
class WorkingCalendar:
    """Framework-neutral working-day calendar.

    Weekday numbers follow Python's Monday=0 ... Sunday=6 convention.
    Holidays are explicit non-working dates. Calendar arithmetic is date-based
    in this first portable slice; Jalali/Gregorian presentation/conversion is
    intentionally outside the arithmetic resolver.
    """

    working_weekdays: FrozenSet[int] = frozenset({0, 1, 2, 3, 4})
    holidays: FrozenSet[date] = field(default_factory=frozenset)

    def is_working_day(self, value: date) -> bool:
        return value.weekday() in self.working_weekdays and value not in self.holidays


class WorkingTimeResolver:
    """Single source of truth for working-day arithmetic in the Shared Core."""

    def __init__(self, calendar: WorkingCalendar) -> None:
        self.calendar = calendar

    def is_working_day(self, value: date) -> bool:
        return self.calendar.is_working_day(value)

    def next_working_day(self, value: date) -> date:
        cursor = value + timedelta(days=1)
        while not self.is_working_day(cursor):
            cursor += timedelta(days=1)
        return cursor

    def previous_working_day(self, value: date) -> date:
        cursor = value - timedelta(days=1)
        while not self.is_working_day(cursor):
            cursor -= timedelta(days=1)
        return cursor

    def normalize_start(self, value: date) -> date:
        """Move a start date forward to the first working day."""
        cursor = value
        while not self.is_working_day(cursor):
            cursor += timedelta(days=1)
        return cursor

    def normalize_finish(self, value: date) -> date:
        """Move a finish date backward to the last working day."""
        cursor = value
        while not self.is_working_day(cursor):
            cursor -= timedelta(days=1)
        return cursor

    def add_working_duration(self, start: date, duration: Decimal | int | float) -> date:
        """Return the finish date for a working-day duration.

        A one-working-day activity starting on a working date finishes on that
        same date, matching activity duration semantics. Zero duration returns
        the normalized start date. Fractional durations are rejected in this
        date-granularity slice and will be handled by the time-of-day resolver.
        """
        units = Decimal(str(duration))
        if units < 0 or units != units.to_integral_value():
            raise ValueError("duration must be a non-negative whole working day")
        cursor = self.normalize_start(start)
        remaining = int(units)
        if remaining == 0:
            return cursor
        for _ in range(remaining - 1):
            cursor = self.next_working_day(cursor)
        return cursor

    def subtract_working_duration(self, finish: date, duration: Decimal | int | float) -> date:
        """Return the start date corresponding to a working-day duration."""
        units = Decimal(str(duration))
        if units < 0 or units != units.to_integral_value():
            raise ValueError("duration must be a non-negative whole working day")
        cursor = self.normalize_finish(finish)
        remaining = int(units)
        if remaining == 0:
            return cursor
        for _ in range(remaining - 1):
            cursor = self.previous_working_day(cursor)
        return cursor

    def calculate_duration(self, start: date, finish: date) -> int:
        """Calculate inclusive working-day duration between two activity dates."""
        start = self.normalize_start(start)
        finish = self.normalize_finish(finish)
        if finish < start:
            raise ValueError("finish must not precede start")
        total = 0
        cursor = start
        while cursor <= finish:
            if self.is_working_day(cursor):
                total += 1
            cursor += timedelta(days=1)
        return total

    def working_days_between(self, start: date, finish: date) -> int:
        """Count working days strictly after start and up to finish."""
        if finish < start:
            raise ValueError("finish must not precede start")
        total = 0
        cursor = start + timedelta(days=1)
        while cursor <= finish:
            if self.is_working_day(cursor):
                total += 1
            cursor += timedelta(days=1)
        return total
