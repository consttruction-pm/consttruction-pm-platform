from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import FrozenSet, Iterable

from .calendar_system import CalendarSystem, JalaliDate
from .calendar_periods import CalendarTimePeriodFactors


CalendarInputDate = date | JalaliDate


@dataclass(frozen=True)
class WorkingCalendar:
    """Framework-neutral working-day calendar with explicit date-system input.

    The Shared Core stores canonical Gregorian dates for arithmetic. When the
    calendar system is Jalali, public calendar-date inputs and holiday inputs
    are converted to Gregorian at the boundary; weekday and arithmetic rules
    therefore remain identical across calendar systems.
    """

    working_weekdays: FrozenSet[int] = frozenset({0, 1, 2, 3, 4})
    holidays: FrozenSet[date] = field(default_factory=frozenset)
    system: CalendarSystem = CalendarSystem.GREGORIAN
    time_period_factors: CalendarTimePeriodFactors = field(default_factory=CalendarTimePeriodFactors)

    def __post_init__(self) -> None:
        invalid = [value for value in self.working_weekdays if value < 0 or value > 6]
        if invalid:
            raise ValueError("working_weekdays must contain values from 0 through 6")
        if not isinstance(self.system, CalendarSystem):
            raise ValueError("system must be a CalendarSystem")
        if any(not isinstance(value, date) or isinstance(value, JalaliDate) for value in self.holidays):
            raise ValueError("holidays must contain canonical Gregorian dates")
        if not isinstance(self.time_period_factors, CalendarTimePeriodFactors):
            raise ValueError("time_period_factors must be CalendarTimePeriodFactors")

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

    @classmethod
    def from_calendar_dates(
        cls,
        *,
        system: CalendarSystem,
        working_weekdays: FrozenSet[int] = frozenset({0, 1, 2, 3, 4}),
        holidays: Iterable[CalendarInputDate] = (),
    ) -> "WorkingCalendar":
        """Build a calendar from dates expressed in the selected system."""
        canonical_holidays = frozenset(
            value if isinstance(value, date) and not isinstance(value, JalaliDate)
            else value.to_gregorian()
            for value in holidays
        )
        return cls(
            working_weekdays=working_weekdays,
            holidays=canonical_holidays,
            system=system,
        )

    def to_gregorian(self, value: CalendarInputDate) -> date:
        if isinstance(value, JalaliDate):
            if self.system is not CalendarSystem.JALALI:
                raise ValueError("Jalali input requires a Jalali calendar")
            return value.to_gregorian()
        if not isinstance(value, date):
            raise TypeError("calendar date must be date or JalaliDate")
        return value

    def holiday_from_calendar_date(self, value: CalendarInputDate) -> date:
        return self.to_gregorian(value)

    def is_working_day(self, value: CalendarInputDate) -> bool:
        canonical = self.to_gregorian(value)
        return canonical.weekday() in self.working_weekdays and canonical not in self.holidays


class WorkingTimeResolver:
    """Single source of truth for working-day arithmetic in the Shared Core."""

    def __init__(self, calendar: WorkingCalendar) -> None:
        self.calendar = calendar

    def is_working_day(self, value: CalendarInputDate) -> bool:
        return self.calendar.is_working_day(value)

    def next_working_day(self, value: CalendarInputDate) -> date:
        cursor = self.calendar.to_gregorian(value) + timedelta(days=1)
        while not self.is_working_day(cursor):
            cursor += timedelta(days=1)
        return cursor

    def previous_working_day(self, value: CalendarInputDate) -> date:
        cursor = self.calendar.to_gregorian(value) - timedelta(days=1)
        while not self.is_working_day(cursor):
            cursor -= timedelta(days=1)
        return cursor

    def normalize_start(self, value: CalendarInputDate) -> date:
        """Move a start date forward to the first working day."""
        cursor = self.calendar.to_gregorian(value)
        while not self.is_working_day(cursor):
            cursor += timedelta(days=1)
        return cursor

    def normalize_finish(self, value: CalendarInputDate) -> date:
        """Move a finish date backward to the last working day."""
        cursor = self.calendar.to_gregorian(value)
        while not self.is_working_day(cursor):
            cursor -= timedelta(days=1)
        return cursor

    def add_working_duration(self, start: CalendarInputDate, duration: Decimal | int | float) -> date:
        """Return the finish date for a working-day duration."""
        units = Decimal(str(duration))
        if not units.is_finite() or units < 0 or units != units.to_integral_value():
            raise ValueError("duration must be a non-negative finite whole working day")
        cursor = self.normalize_start(start)
        remaining = int(units)
        if remaining == 0:
            return cursor
        for _ in range(remaining - 1):
            cursor = self.next_working_day(cursor)
        return cursor

    def subtract_working_duration(self, finish: CalendarInputDate, duration: Decimal | int | float) -> date:
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

    def calculate_duration(self, start: CalendarInputDate, finish: CalendarInputDate) -> int:
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

    def working_days_between(self, start: CalendarInputDate, finish: CalendarInputDate) -> int:
        """Count working days strictly after start and up to finish."""
        start = self.calendar.to_gregorian(start)
        finish = self.calendar.to_gregorian(finish)
        if finish < start:
            raise ValueError("finish must not precede start")
        total = 0
        cursor = start + timedelta(days=1)
        while cursor <= finish:
            if self.is_working_day(cursor):
                total += 1
            cursor += timedelta(days=1)
        return total
