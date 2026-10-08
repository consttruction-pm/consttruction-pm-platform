from __future__ import annotations

"""Shared-Core calendar exception overlays for authoritative scheduling.

The overlays intentionally decorate the existing calendar objects instead of
copying any scheduling arithmetic. WorkingTimeResolver and
TimeAwareWorkingTimeResolver remain the only arithmetic authorities.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Iterable

from .calendar import WorkingCalendar, WorkingTimeResolver
from .calendar_exceptions import CalendarException, CalendarExceptionResolver, CalendarExceptionType
from .time_calendar import TimeAwareWorkingTimeResolver, WorkingTimeCalendar


@dataclass(frozen=True)
class CalendarExceptionLayers:
    """Explicit local and inherited exception layers for one versioned calendar."""

    local: tuple[CalendarException, ...] = ()
    inherited: tuple[CalendarException, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.local, tuple) or not isinstance(self.inherited, tuple):
            raise TypeError("calendar exception layers must be tuples")
        if not all(isinstance(item, CalendarException) for item in self.local):
            raise TypeError("local exceptions must contain CalendarException items")
        if not all(isinstance(item, CalendarException) for item in self.inherited):
            raise TypeError("inherited exceptions must contain CalendarException items")


class ExceptionAwareWorkingCalendar:
    """Calendar view that applies local > inherited > standard date rules."""

    def __init__(self, calendar: WorkingCalendar, layers: CalendarExceptionLayers) -> None:
        self.calendar = calendar
        self.layers = layers

    @property
    def working_weekdays(self):
        return self.calendar.working_weekdays

    @property
    def holidays(self):
        return self.calendar.holidays

    @property
    def system(self):
        return self.calendar.system

    @property
    def time_period_factors(self):
        return self.calendar.time_period_factors

    def to_gregorian(self, value):
        return self.calendar.to_gregorian(value)

    def holiday_from_calendar_date(self, value):
        return self.calendar.holiday_from_calendar_date(value)

    def effective_rule(self, value: date):
        target = self.calendar.to_gregorian(value)
        return CalendarExceptionResolver(
            standard_is_working=self.calendar.is_working_day(target),
            standard_total_work_hours=self.calendar.hours_per_day,
        ).resolve(
            target,
            local_exceptions=self.layers.local,
            inherited_exceptions=self.layers.inherited,
        )

    def is_working_day(self, value) -> bool:
        return self.effective_rule(self.calendar.to_gregorian(value)).is_working


def _interval_hours(interval: tuple[time, time]) -> Decimal:
    start, end = interval
    anchor = date(2000, 1, 1)
    return (
        Decimal(_timedelta_microseconds(datetime.combine(anchor, end) - datetime.combine(anchor, start)))
        / Decimal("3600000000")
    )


def _timedelta_microseconds(value: timedelta) -> int:
    return (
        value.days * 86_400_000_000
        + value.seconds * 1_000_000
        + value.microseconds
    )


def _hours_to_microseconds(hours: Decimal) -> int:
    microseconds = hours * Decimal("3600000000")
    if microseconds != microseconds.to_integral_value():
        raise ValueError("total_work_hours is more precise than one microsecond")
    return int(microseconds)


def _intervals_for_total_hours(
    target_date: date,
    standard: tuple[tuple[time, time], ...],
    total_hours: Decimal,
) -> tuple[tuple[time, time], ...]:
    """Materialize a total-hours override by consuming standard intervals in order."""
    if total_hours < 0 or not total_hours.is_finite():
        raise ValueError("total_work_hours must be finite and non-negative")
    if total_hours == 0:
        return ()

    remaining = total_hours
    result: list[tuple[time, time]] = []
    for start, end in standard:
        available = _interval_hours((start, end))
        if remaining >= available:
            result.append((start, end))
            remaining -= available
            continue
        end_dt = datetime.combine(target_date, start) + timedelta(
            microseconds=_hours_to_microseconds(remaining)
        )
        result.append((start, end_dt.time()))
        remaining = Decimal("0")
        break

    if remaining != 0:
        raise ValueError("TOTAL_WORK_HOURS_EXCEEDS_STANDARD_CAPACITY")
    return tuple(result)


class ExceptionAwareWorkingTimeCalendar:
    """Working-time calendar view with authoritative effective date rules."""

    def __init__(self, calendar: WorkingTimeCalendar, layers: CalendarExceptionLayers) -> None:
        self.calendar = calendar
        self.layers = layers

    @property
    def system(self):
        return self.calendar.system

    @property
    def working_weekdays(self):
        return self.calendar.working_weekdays

    @property
    def holidays(self):
        return self.calendar.holidays

    @property
    def daily_intervals(self):
        return self.calendar.daily_intervals

    @property
    def time_period_factors(self):
        return self.calendar.time_period_factors

    def _standard_intervals(self, target_date: date) -> tuple[tuple[time, time], ...]:
        return self.calendar.intervals_for(target_date)

    def effective_rule(self, value: date):
        target = value
        standard = self._standard_intervals(target)
        total_hours = None
        if standard:
            total_hours = sum((_interval_hours(interval) for interval in standard), Decimal("0"))
        return CalendarExceptionResolver(
            standard_is_working=bool(standard),
            standard_total_work_hours=total_hours,
            standard_intervals=standard,
        ).resolve(
            target,
            local_exceptions=self.layers.local,
            inherited_exceptions=self.layers.inherited,
        )

    def intervals_for(self, value: date):
        rule = self.effective_rule(value)
        if rule.kind is None or rule.kind is CalendarExceptionType.RESET_TO_STANDARD:
            return self._standard_intervals(value)
        if rule.kind is CalendarExceptionType.NONWORK:
            return ()
        if rule.kind is CalendarExceptionType.DETAILED_WORK_HOURS:
            return rule.intervals
        if rule.kind is CalendarExceptionType.TOTAL_WORK_HOURS:
            standard = self._standard_intervals(value)
            return _intervals_for_total_hours(value, standard, rule.total_work_hours or Decimal("0"))
        raise ValueError(f"unsupported effective calendar rule: {rule.kind}")


def overlay_day_resolver(
    resolver: WorkingTimeResolver,
    *,
    local_exceptions: Iterable[CalendarException] = (),
    inherited_exceptions: Iterable[CalendarException] = (),
) -> WorkingTimeResolver:
    layers = CalendarExceptionLayers(tuple(local_exceptions), tuple(inherited_exceptions))
    if not layers.local and not layers.inherited:
        return resolver
    calendar = getattr(resolver, "calendar", None)
    if not isinstance(calendar, WorkingCalendar):
        raise TypeError("day resolver must use WorkingCalendar")
    return WorkingTimeResolver(ExceptionAwareWorkingCalendar(calendar, layers))


def overlay_time_resolver(
    resolver: TimeAwareWorkingTimeResolver,
    *,
    local_exceptions: Iterable[CalendarException] = (),
    inherited_exceptions: Iterable[CalendarException] = (),
) -> TimeAwareWorkingTimeResolver:
    layers = CalendarExceptionLayers(tuple(local_exceptions), tuple(inherited_exceptions))
    if not layers.local and not layers.inherited:
        return resolver
    calendar = getattr(resolver, "calendar", None)
    if not isinstance(calendar, WorkingTimeCalendar):
        raise TypeError("time resolver must use WorkingTimeCalendar")
    return TimeAwareWorkingTimeResolver(ExceptionAwareWorkingTimeCalendar(calendar, layers))


__all__ = [
    "CalendarExceptionLayers",
    "ExceptionAwareWorkingCalendar",
    "ExceptionAwareWorkingTimeCalendar",
    "overlay_day_resolver",
    "overlay_time_resolver",
]
