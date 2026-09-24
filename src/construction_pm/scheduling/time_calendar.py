from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import FrozenSet, Mapping, Tuple


@dataclass(frozen=True)
class WorkingTimeCalendar:
    """Time-of-day calendar extension for the Shared Scheduling Core.

    This model is intentionally separate from WorkingCalendar. Existing
    date-based scheduling remains unchanged; this resolver is the authoritative
    extension point for future time-based scheduling and working-time lag.
    Intervals are half-open [start, end).
    """

    working_weekdays: FrozenSet[int] = frozenset({0, 1, 2, 3, 4})
    holidays: FrozenSet[date] = field(default_factory=frozenset)
    daily_intervals: Mapping[int, Tuple[Tuple[time, time], ...]] = field(
        default_factory=lambda: {
            0: ((time(8, 0), time(17, 0)),),
            1: ((time(8, 0), time(17, 0)),),
            2: ((time(8, 0), time(17, 0)),),
            3: ((time(8, 0), time(17, 0)),),
            4: ((time(8, 0), time(17, 0)),),
        }
    )

    def __post_init__(self) -> None:
        for weekday, intervals in self.daily_intervals.items():
            if weekday < 0 or weekday > 6:
                raise ValueError("weekday must be between 0 and 6")
            previous_end: time | None = None
            for start, end in intervals:
                if start >= end:
                    raise ValueError("working interval start must precede end")
                if previous_end is not None and start < previous_end:
                    raise ValueError("working intervals must not overlap")
                previous_end = end

    def intervals_for(self, value: date) -> Tuple[Tuple[time, time], ...]:
        if value in self.holidays or value.weekday() not in self.working_weekdays:
            return ()
        return self.daily_intervals.get(value.weekday(), ())


class TimeAwareWorkingTimeResolver:
    """Deterministic datetime arithmetic over a WorkingTimeCalendar."""

    def __init__(self, calendar: WorkingTimeCalendar) -> None:
        self.calendar = calendar

    def is_working_datetime(self, value: datetime) -> bool:
        return any(
            start <= value.time() < end
            for start, end in self.calendar.intervals_for(value.date())
        )

    def normalize_start(self, value: datetime) -> datetime:
        cursor = value
        for _ in range(3660):
            intervals = self.calendar.intervals_for(cursor.date())
            for start, end in intervals:
                if cursor.time() < start:
                    return datetime.combine(cursor.date(), start)
                if start <= cursor.time() < end:
                    return cursor
            cursor = datetime.combine(cursor.date() + timedelta(days=1), time.min)
        raise ValueError("unable to find a working datetime")

    def normalize_finish(self, value: datetime) -> datetime:
        cursor = value
        for _ in range(3660):
            intervals = self.calendar.intervals_for(cursor.date())
            for start, end in reversed(intervals):
                if cursor.time() >= end:
                    return datetime.combine(cursor.date(), end)
                if start <= cursor.time() < end:
                    return cursor
            cursor = datetime.combine(cursor.date() - timedelta(days=1), time.max)
        raise ValueError("unable to find a working datetime")

    def add_working_hours(self, start: datetime, hours: Decimal | int | float) -> datetime:
        units = Decimal(str(hours))
        if units < 0:
            raise ValueError("hours must be non-negative")
        cursor = self.normalize_start(start)
        remaining = units
        for _ in range(3660):
            intervals = self.calendar.intervals_for(cursor.date())
            progressed = False
            for interval_start, interval_end in intervals:
                begin = datetime.combine(cursor.date(), interval_start)
                end = datetime.combine(cursor.date(), interval_end)
                if cursor < begin:
                    cursor = begin
                if not (begin <= cursor < end):
                    continue

                capacity = Decimal(str((end - cursor).total_seconds())) / Decimal(3600)
                if remaining <= capacity:
                    seconds = remaining * Decimal(3600)
                    return cursor + timedelta(microseconds=int(seconds * Decimal(1_000_000)))
                remaining -= capacity
                progressed = True
                cursor = end

            # Consume all remaining intervals on this day before advancing.
            # This is essential for calendars with breaks such as 08:00–12:00
            # and 13:00–17:00.
            cursor = datetime.combine(cursor.date() + timedelta(days=1), time.min)
            if progressed or not intervals:
                continue
        raise ValueError("working-hour duration exceeds resolver horizon")

    def subtract_working_hours(self, finish: datetime, hours: Decimal | int | float) -> datetime:
        units = Decimal(str(hours))
        if units < 0:
            raise ValueError("hours must be non-negative")
        cursor = self.normalize_finish(finish)
        remaining = units
        for _ in range(3660):
            intervals = self.calendar.intervals_for(cursor.date())
            progressed = False
            for interval_start, interval_end in reversed(intervals):
                begin = datetime.combine(cursor.date(), interval_start)
                end = datetime.combine(cursor.date(), interval_end)
                if cursor >= end:
                    cursor = end
                if not (begin < cursor <= end):
                    continue

                capacity = Decimal(str((cursor - begin).total_seconds())) / Decimal(3600)
                if remaining <= capacity:
                    seconds = remaining * Decimal(3600)
                    return cursor - timedelta(microseconds=int(seconds * Decimal(1_000_000)))
                remaining -= capacity
                progressed = True
                cursor = begin

            # Consume earlier intervals on the same day before moving to the
            # previous day; this preserves breaks such as 08:00–12:00/13:00–17:00.
            cursor = datetime.combine(cursor.date() - timedelta(days=1), time.max)
            if progressed or not intervals:
                continue
        raise ValueError("working-hour duration exceeds resolver horizon")

    def calculate_working_hours(self, start: datetime, finish: datetime) -> Decimal:
        if finish < start:
            raise ValueError("finish must not precede start")

        total = Decimal("0")
        cursor_date = start.date()
        last_date = finish.date()
        while cursor_date <= last_date:
            for interval_start, interval_end in self.calendar.intervals_for(cursor_date):
                begin = datetime.combine(cursor_date, interval_start)
                end = datetime.combine(cursor_date, interval_end)
                left = max(start, begin)
                right = min(finish, end)
                if right > left:
                    seconds = Decimal(str((right - left).total_seconds()))
                    total += seconds / Decimal(3600)
            cursor_date += timedelta(days=1)
        return total
