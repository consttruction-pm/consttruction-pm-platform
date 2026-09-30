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


def _duration_microseconds(value: Decimal | int | float, *, unit: str) -> int:
    """Convert a non-negative duration to exact microseconds.

    Scheduling arithmetic must never silently truncate a supplied duration.
    """

    units = Decimal(str(value))
    if not units.is_finite() or units < 0:
        raise ValueError(f"{unit} must be a finite non-negative value")
    microseconds = units * Decimal("3600000000")
    if microseconds != microseconds.to_integral_value():
        raise ValueError(f"{unit} is more precise than one microsecond")
    return int(microseconds)


def _timedelta_microseconds(value: timedelta) -> int:
    return value.days * 86_400_000_000 + value.seconds * 1_000_000 + value.microseconds


class TimeAwareWorkingTimeResolver:
    """Deterministic datetime arithmetic over a WorkingTimeCalendar."""

    def __init__(self, calendar: WorkingTimeCalendar) -> None:
        self.calendar = calendar
        if not any(calendar.daily_intervals.get(day) for day in calendar.working_weekdays):
            raise ValueError("calendar must define at least one working interval")

    @staticmethod
    def _combine(value_date: date, value_time: time, reference: datetime) -> datetime:
        return datetime.combine(value_date, value_time, tzinfo=reference.tzinfo)

    def is_working_datetime(self, value: datetime) -> bool:
        return any(
            start <= value.time() < end
            for start, end in self.calendar.intervals_for(value.date())
        )

    def normalize_start(self, value: datetime) -> datetime:
        cursor = value
        while True:
            intervals = self.calendar.intervals_for(cursor.date())
            for start, end in intervals:
                if cursor.time() < start:
                    return self._combine(cursor.date(), start, cursor)
                if start <= cursor.time() < end:
                    return cursor
            cursor = self._combine(cursor.date() + timedelta(days=1), time.min, cursor)

    def normalize_finish(self, value: datetime) -> datetime:
        cursor = value
        for _ in range(3660):
            intervals = self.calendar.intervals_for(cursor.date())
            for start, end in reversed(intervals):
                if cursor.time() >= end:
                    return self._combine(cursor.date(), end, cursor)
                if start <= cursor.time() < end:
                    return cursor
            cursor = self._combine(cursor.date() - timedelta(days=1), time.max, cursor)
        raise ValueError("unable to find a working datetime")

    def add_working_hours(self, start: datetime, hours: Decimal | int | float) -> datetime:
        remaining_microseconds = _duration_microseconds(hours, unit="hours")
        cursor = self.normalize_start(start)
        while True:
            intervals = self.calendar.intervals_for(cursor.date())
            progressed = False
            for interval_start, interval_end in intervals:
                begin = self._combine(cursor.date(), interval_start, cursor)
                end = self._combine(cursor.date(), interval_end, cursor)
                if cursor < begin:
                    cursor = begin
                if not (begin <= cursor < end):
                    continue

                capacity_microseconds = _timedelta_microseconds(end - cursor)
                if remaining_microseconds <= capacity_microseconds:
                    return cursor + timedelta(microseconds=remaining_microseconds)
                remaining_microseconds -= capacity_microseconds
                progressed = True
                cursor = end

            # Consume all remaining intervals on this day before advancing.
            # This is essential for calendars with breaks such as 08:00–12:00
            # and 13:00–17:00.
            cursor = datetime.combine(cursor.date() + timedelta(days=1), time.min)
            if progressed or not intervals:
                continue


    def subtract_working_hours(self, finish: datetime, hours: Decimal | int | float) -> datetime:
        remaining_microseconds = _duration_microseconds(hours, unit="hours")
        cursor = self.normalize_finish(finish)
        while True:
            intervals = self.calendar.intervals_for(cursor.date())
            progressed = False
            for interval_start, interval_end in reversed(intervals):
                begin = datetime.combine(cursor.date(), interval_start)
                end = datetime.combine(cursor.date(), interval_end)
                if cursor >= end:
                    cursor = end
                if not (begin < cursor <= end):
                    continue

                capacity_microseconds = _timedelta_microseconds(cursor - begin)
                if remaining_microseconds <= capacity_microseconds:
                    return cursor - timedelta(microseconds=remaining_microseconds)
                remaining_microseconds -= capacity_microseconds
                progressed = True
                cursor = begin

            # Consume earlier intervals on the same day before moving to the
            # previous day; this preserves breaks such as 08:00–12:00/13:00–17:00.
            cursor = datetime.combine(cursor.date() - timedelta(days=1), time.max)
            if progressed or not intervals:
                continue


    def calculate_working_hours(self, start: datetime, finish: datetime) -> Decimal:
        if finish < start:
            raise ValueError("finish must not precede start")

        total = Decimal("0")
        cursor_date = start.date()
        last_date = finish.date()
        while cursor_date <= last_date:
            for interval_start, interval_end in self.calendar.intervals_for(cursor_date):
                begin = self._combine(cursor_date, interval_start, start)
                end = self._combine(cursor_date, interval_end, start)
                left = max(start, begin)
                right = min(finish, end)
                if right > left:
                    seconds = Decimal(str((right - left).total_seconds()))
                    total += seconds / Decimal(3600)
            cursor_date += timedelta(days=1)
        return total
