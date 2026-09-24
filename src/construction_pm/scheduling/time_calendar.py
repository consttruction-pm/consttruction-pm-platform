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
                    return datetime.combine(cursor.date(), end) - timedelta(microseconds=1)
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
            moved = False
            for interval_start, interval_end in intervals:
                begin = datetime.combine(cursor.date(), interval_start)
                end = datetime.combine(cursor.date(), interval_end)
                if cursor < begin:
                    cursor = begin
                if begin <= cursor < end:
                    capacity = Decimal(str((end - cursor).total_seconds())) / Decimal(3600)
                    if remaining <= capacity:
                        return cursor + timedelta(seconds=float(remaining * Decimal(3600)))
                    remaining -= capacity
                    moved = True
                    break
            cursor = datetime.combine(cursor.date() + timedelta(days=1), time.min)
            if not moved and not intervals:
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
            for interval_start, interval_end in reversed(intervals):
                begin = datetime.combine(cursor.date(), interval_start)
                end = datetime.combine(cursor.date(), interval_end)
                if cursor >= end:
                    cursor = end
                if begin < cursor <= end:
                    capacity = Decimal(str((cursor - begin).total_seconds())) / Decimal(3600)
                    if remaining <= capacity:
                        return cursor - timedelta(seconds=float(remaining * Decimal(3600)))
                    remaining -= capacity
                    cursor = begin
                    break
            cursor = datetime.combine(cursor.date() - timedelta(days=1), time.max)
        raise ValueError("working-hour duration exceeds resolver horizon")

    def calculate_working_hours(self, start: datetime, finish: datetime) -> Decimal:
        if finish < start:
            raise ValueError("finish must not precede start")
        cursor = self.normalize_start(start)
        total = Decimal("0")
        while cursor < finish:
            intervals = self.calendar.intervals_for(cursor.date())
            advanced = False
            for interval_start, interval_end in intervals:
                begin = datetime.combine(cursor.date(), interval_start)
                end = datetime.combine(cursor.date(), interval_end)
                left = max(cursor, begin)
                right = min(finish, end)
                if right > left:
                    total += Decimal(str((right - left).total_seconds())) / Decimal(3600)
                    advanced = True
            cursor = datetime.combine(cursor.date() + timedelta(days=1), time.min)
            if cursor > finish and not advanced:
                break
        return total
