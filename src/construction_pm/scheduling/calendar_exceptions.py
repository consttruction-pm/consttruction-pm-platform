from __future__ import annotations

"""Shared-Core calendar exception precedence and inheritance semantics.

The module is deliberately independent of persistence and UI.  A calendar
layer can provide its standard rule plus local exceptions and inherited
exceptions; this resolver determines the single effective rule for a date.
"""

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Iterable, Mapping, Tuple

from .calendar import CalendarInputDate
from .calendar_system import CalendarSystem, JalaliDate


class CalendarExceptionType(str, Enum):
    NONWORK = "NONWORK"
    TOTAL_WORK_HOURS = "TOTAL_WORK_HOURS"
    DETAILED_WORK_HOURS = "DETAILED_WORK_HOURS"
    RESET_TO_STANDARD = "RESET_TO_STANDARD"


Interval = Tuple[time, time]


@dataclass(frozen=True)
class CalendarException:
    """One immutable date-specific calendar override."""

    date: CalendarInputDate
    kind: CalendarExceptionType
    calendar_system: CalendarSystem = CalendarSystem.GREGORIAN
    total_work_hours: Decimal | None = None
    intervals: Tuple[Interval, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.calendar_system, CalendarSystem):
            raise TypeError("calendar_system must be CalendarSystem")
        if isinstance(self.date, JalaliDate):
            if self.calendar_system is not CalendarSystem.JALALI:
                raise ValueError("Jalali input requires a Jalali calendar system")
            object.__setattr__(self, "date", self.date.to_gregorian())
        elif isinstance(self.date, date) and not isinstance(self.date, datetime):
            if self.calendar_system is not CalendarSystem.GREGORIAN:
                raise ValueError("Gregorian date input requires a Gregorian calendar system")
        else:
            raise TypeError("date must be date or JalaliDate")
        if not isinstance(self.kind, CalendarExceptionType):
            raise TypeError("kind must be CalendarExceptionType")
        if self.kind is CalendarExceptionType.TOTAL_WORK_HOURS:
            if self.total_work_hours is None:
                raise ValueError("TOTAL_WORK_HOURS requires total_work_hours")
            hours = Decimal(str(self.total_work_hours))
            if not hours.is_finite() or hours < 0:
                raise ValueError("total_work_hours must be finite and non-negative")
            object.__setattr__(self, "total_work_hours", hours)
        elif self.total_work_hours is not None:
            raise ValueError("total_work_hours is only valid for TOTAL_WORK_HOURS")

        if self.kind is CalendarExceptionType.DETAILED_WORK_HOURS:
            if not self.intervals:
                raise ValueError("DETAILED_WORK_HOURS requires intervals")
            previous_end: time | None = None
            for interval in self.intervals:
                if not isinstance(interval, tuple) or len(interval) != 2:
                    raise ValueError("each interval must be a (start, end) tuple")
                start, end = interval
                if not isinstance(start, time) or not isinstance(end, time):
                    raise ValueError("interval boundaries must be time values")
                if start >= end:
                    raise ValueError("interval start must precede end")
                if previous_end is not None and start < previous_end:
                    raise ValueError("intervals must be ordered and non-overlapping")
                previous_end = end
        elif self.intervals:
            raise ValueError("intervals are only valid for DETAILED_WORK_HOURS")

    def canonical_snapshot(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "date": self.date.isoformat(),
            "kind": self.kind.value,
            "calendar_system": self.calendar_system.value,
        }
        if self.kind is CalendarExceptionType.TOTAL_WORK_HOURS:
            payload["total_work_hours"] = str(self.total_work_hours)
        elif self.kind is CalendarExceptionType.DETAILED_WORK_HOURS:
            payload["intervals"] = [
                [start.isoformat(), end.isoformat()] for start, end in self.intervals
            ]
        return payload


@dataclass(frozen=True)
class EffectiveCalendarDateRule:
    """The single calendar rule that scheduling should consume for one date."""

    date: date
    source: str
    kind: CalendarExceptionType | None
    is_working: bool
    total_work_hours: Decimal | None = None
    intervals: Tuple[Interval, ...] = ()

    def canonical_snapshot(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "date": self.date.isoformat(),
            "source": self.source,
            "kind": self.kind.value if self.kind is not None else None,
            "is_working": self.is_working,
        }
        if self.total_work_hours is not None:
            payload["total_work_hours"] = str(self.total_work_hours)
        if self.intervals:
            payload["intervals"] = [
                [start.isoformat(), end.isoformat()] for start, end in self.intervals
            ]
        return payload


class CalendarExceptionResolver:
    """Resolve local-over-inherited-over-standard date semantics."""

    def __init__(
        self,
        *,
        standard_is_working: bool,
        standard_total_work_hours: Decimal | None = None,
        standard_intervals: Iterable[Interval] = (),
    ) -> None:
        if not isinstance(standard_is_working, bool):
            raise TypeError("standard_is_working must be bool")
        intervals = tuple(standard_intervals)
        if standard_total_work_hours is not None:
            hours = Decimal(str(standard_total_work_hours))
            if not hours.is_finite() or hours < 0:
                raise ValueError("standard_total_work_hours must be finite and non-negative")
            standard_total_work_hours = hours
        self.standard = EffectiveCalendarDateRule(
            date=date.min,
            source="standard",
            kind=None,
            is_working=standard_is_working,
            total_work_hours=standard_total_work_hours,
            intervals=intervals,
        )

    @staticmethod
    def _apply(
        target_date: CalendarInputDate,
        exception: CalendarException,
        *,
        source: str,
        standard: EffectiveCalendarDateRule,
    ) -> EffectiveCalendarDateRule:
        if exception.date != target_date:
            raise ValueError("exception date does not match target date")

        if exception.kind is CalendarExceptionType.RESET_TO_STANDARD:
            return EffectiveCalendarDateRule(
                target_date,
                source,
                exception.kind,
                standard.is_working,
                standard.total_work_hours,
                standard.intervals,
            )
        if exception.kind is CalendarExceptionType.NONWORK:
            return EffectiveCalendarDateRule(target_date, source, exception.kind, False)
        if exception.kind is CalendarExceptionType.TOTAL_WORK_HOURS:
            return EffectiveCalendarDateRule(
                target_date,
                source,
                exception.kind,
                True,
                exception.total_work_hours,
                (),
            )
        if exception.kind is CalendarExceptionType.DETAILED_WORK_HOURS:
            return EffectiveCalendarDateRule(
                target_date,
                source,
                exception.kind,
                True,
                None,
                exception.intervals,
            )
        raise ValueError(f"unsupported calendar exception type: {exception.kind}")

    @staticmethod
    def _by_date(values: Iterable[CalendarException]) -> Mapping[date, CalendarException]:
        result: dict[date, CalendarException] = {}
        for value in values:
            if value.date in result:
                raise ValueError(f"duplicate calendar exception for {value.date.isoformat()}")
            result[value.date] = value
        return MappingProxyType(result)

    def resolve(
        self,
        target_date: date,
        *,
        local_exceptions: Iterable[CalendarException] = (),
        inherited_exceptions: Iterable[CalendarException] = (),
    ) -> EffectiveCalendarDateRule:
        if isinstance(target_date, JalaliDate):
            target = target_date.to_gregorian()
        elif isinstance(target_date, date) and not isinstance(target_date, datetime):
            target = target_date
        else:
            raise TypeError("target_date must be date or JalaliDate")
        local = self._by_date(local_exceptions)
        inherited = self._by_date(inherited_exceptions)

        selected = local.get(target)
        if selected is not None:
            return self._apply(target, selected, source="local", standard=self.standard)

        selected = inherited.get(target)
        if selected is not None:
            return self._apply(target, selected, source="inherited", standard=self.standard)

        return EffectiveCalendarDateRule(
            target,
            "standard",
            None,
            self.standard.is_working,
            self.standard.total_work_hours,
            self.standard.intervals,
        )


__all__ = [
    "CalendarException",
    "CalendarExceptionResolver",
    "CalendarExceptionType",
    "EffectiveCalendarDateRule",
]
