from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from types import MappingProxyType

from .calendar_periods import CalendarTimePeriodFactors
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
    time_period_factors: CalendarTimePeriodFactors = field(default_factory=CalendarTimePeriodFactors)

    def __post_init__(self) -> None:
        if not isinstance(self.working_weekdays, (frozenset, set)):
            raise ValueError("working_weekdays must be a set of weekday numbers")
        if any(isinstance(weekday, bool) or not isinstance(weekday, int) or weekday < 0 or weekday > 6 for weekday in self.working_weekdays):
            raise ValueError("weekday must be an integer between 0 and 6")
        if not isinstance(self.holidays, (frozenset, set)):
            raise ValueError("holidays must be a set of dates")
        if any(not isinstance(value, date) or isinstance(value, datetime) for value in self.holidays):
            raise ValueError("holidays must contain dates")
        if not isinstance(self.daily_intervals, Mapping):
            raise ValueError("daily_intervals must be a mapping")
        if not isinstance(self.time_period_factors, CalendarTimePeriodFactors):
            raise ValueError("time_period_factors must be CalendarTimePeriodFactors")
        object.__setattr__(self, "working_weekdays", frozenset(self.working_weekdays))
        object.__setattr__(self, "holidays", frozenset(self.holidays))
        object.__setattr__(
            self,
            "daily_intervals",
            MappingProxyType({weekday: tuple(intervals) for weekday, intervals in self.daily_intervals.items()}),
        )
        for weekday, intervals in self.daily_intervals.items():
            if isinstance(weekday, bool) or not isinstance(weekday, int) or weekday < 0 or weekday > 6:
                raise ValueError("weekday must be an integer between 0 and 6")
            if not isinstance(intervals, (tuple, list)):
                raise ValueError("daily intervals must be a sequence")
            previous_end: time | None = None
            for interval in intervals:
                if not isinstance(interval, (tuple, list)) or len(interval) != 2:
                    raise ValueError("working interval must contain start and end times")
                start, end = interval
                if not isinstance(start, time) or not isinstance(end, time):
                    raise ValueError("working interval boundaries must be times")
                if start >= end:
                    raise ValueError("working interval start must precede end")
                if previous_end is not None and start < previous_end:
                    raise ValueError("working intervals must not overlap")
                previous_end = end

    @property
    def hours_per_day(self) -> Decimal:
        return self.time_period_factors.hours_per_day

    @property
    def hours_per_week(self) -> Decimal:
        return self.time_period_factors.hours_per_week

    @property
    def hours_per_month(self) -> Decimal:
        return self.time_period_factors.hours_per_month

    @property
    def hours_per_year(self) -> Decimal:
        return self.time_period_factors.hours_per_year

    def intervals_for(self, value: date) -> Tuple[Tuple[time, time], ...]:
        if not isinstance(value, date) or isinstance(value, datetime):
            raise TypeError("calendar interval lookup requires a date")
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

    @staticmethod
    def _require_datetime(value: object, *, field: str) -> datetime:
        if not isinstance(value, datetime):
            raise TypeError(f"{field} must be a datetime")
        return value

    def is_working_datetime(self, value: datetime) -> bool:
        value = self._require_datetime(value, field="value")
        return any(
            start <= value.time() < end
            for start, end in self.calendar.intervals_for(value.date())
        )

    def normalize_start(self, value: datetime) -> datetime:
        value = self._require_datetime(value, field="value")
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
        value = self._require_datetime(value, field="value")
        cursor = value
        while True:
            intervals = self.calendar.intervals_for(cursor.date())
            for start, end in reversed(intervals):
                if cursor.time() >= end:
                    return self._combine(cursor.date(), end, cursor)
                if start <= cursor.time() < end:
                    return cursor
            cursor = self._combine(cursor.date() - timedelta(days=1), time.max, cursor)

    def add_working_hours(self, start: datetime, hours: Decimal | int | float) -> datetime:
        start = self._require_datetime(start, field="start")
        remaining_microseconds = _duration_microseconds(hours, unit="hours")
        cursor = self.normalize_start(start)
        while True:
            intervals = self.calendar.intervals_for(cursor.date())
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
                cursor = end

            cursor = self._combine(cursor.date() + timedelta(days=1), time.min, cursor)
            continue

    def subtract_working_hours(self, finish: datetime, hours: Decimal | int | float) -> datetime:
        finish = self._require_datetime(finish, field="finish")
        remaining_microseconds = _duration_microseconds(hours, unit="hours")
        cursor = self.normalize_finish(finish)
        while True:
            intervals = self.calendar.intervals_for(cursor.date())
            for interval_start, interval_end in reversed(intervals):
                begin = self._combine(cursor.date(), interval_start, cursor)
                end = self._combine(cursor.date(), interval_end, cursor)
                if cursor >= end:
                    cursor = end
                if not (begin < cursor <= end):
                    continue

                capacity_microseconds = _timedelta_microseconds(cursor - begin)
                if remaining_microseconds <= capacity_microseconds:
                    return cursor - timedelta(microseconds=remaining_microseconds)
                remaining_microseconds -= capacity_microseconds
                cursor = begin

            cursor = self._combine(cursor.date() - timedelta(days=1), time.max, cursor)
            continue

    def calculate_working_hours(self, start: datetime, finish: datetime) -> Decimal:
        start = self._require_datetime(start, field="start")
        finish = self._require_datetime(finish, field="finish")
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
                    total += Decimal(_timedelta_microseconds(right - left)) / Decimal("3600000000")
            cursor_date += timedelta(days=1)
        return total
