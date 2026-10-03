from __future__ import annotations

from datetime import date, datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
from typing import Mapping

from .calendar import WorkingTimeResolver
from .calendar_system import CalendarSystem
from .time_calendar import TimeAwareWorkingTimeResolver


class RelationshipLagCalendar(str, Enum):
    PREDECESSOR = "PREDECESSOR_ACTIVITY_CALENDAR"
    SUCCESSOR = "SUCCESSOR_ACTIVITY_CALENDAR"
    TWENTY_FOUR_HOUR = "24_HOUR_CALENDAR"
    PROJECT_DEFAULT = "PROJECT_DEFAULT_CALENDAR"


class Continuous24HourResolver:
    """Exact continuous 24-hour calendar arithmetic for relationship lag."""

    def normalize_start(self, value: date | datetime) -> date:
        if isinstance(value, datetime):
            return value.date()
        if not isinstance(value, date):
            raise TypeError("calendar date must be date or datetime")
        return value

    def normalize_finish(self, value: date | datetime) -> date:
        if isinstance(value, datetime):
            return value.date()
        if not isinstance(value, date):
            raise TypeError("calendar date must be date or datetime")
        return value

    def next_working_day(self, value: date | datetime) -> date:
        return self.normalize_start(value) + timedelta(days=1)

    def previous_working_day(self, value: date | datetime) -> date:
        return self.normalize_finish(value) - timedelta(days=1)

    def add_working_duration(self, start: date | datetime, duration: Decimal | int | float) -> date:
        units = Decimal(str(duration))
        if not units.is_finite() or units < 0 or units != units.to_integral_value():
            raise ValueError("duration must be a non-negative finite whole working day")
        cursor = self.normalize_start(start)
        remaining = int(units)
        if remaining == 0:
            return cursor
        return cursor + timedelta(days=remaining - 1)

    def subtract_working_duration(self, finish: date | datetime, duration: Decimal | int | float) -> date:
        units = Decimal(str(duration))
        if not units.is_finite() or units < 0 or units != units.to_integral_value():
            raise ValueError("duration must be a non-negative finite whole working day")
        cursor = self.normalize_finish(finish)
        remaining = int(units)
        if remaining == 0:
            return cursor
        return cursor - timedelta(days=remaining - 1)

    def calculate_duration(self, start: date | datetime, finish: date | datetime) -> int:
        start_date = self.normalize_start(start)
        finish_date = self.normalize_finish(finish)
        if finish_date < start_date:
            raise ValueError("finish must not precede start")
        return (finish_date - start_date).days + 1

    @staticmethod
    def _hours_microseconds(value: Decimal | int | float) -> int:
        units = Decimal(str(value))
        if not units.is_finite() or units < 0:
            raise ValueError("hours must be a non-negative finite quantity")
        microseconds = units * Decimal("3600000000")
        if microseconds != microseconds.to_integral_value():
            raise ValueError("hours is more precise than one microsecond")
        return int(microseconds)

    @staticmethod
    def _require_datetime(value: datetime, field_name: str) -> datetime:
        if not isinstance(value, datetime):
            raise TypeError(f"{field_name} must be a datetime")
        return value

    def add_working_hours(self, start: datetime, hours: Decimal | int | float) -> datetime:
        start = self._require_datetime(start, "start")
        return start + timedelta(microseconds=self._hours_microseconds(hours))

    def subtract_working_hours(self, finish: datetime, hours: Decimal | int | float) -> datetime:
        finish = self._require_datetime(finish, "finish")
        return finish - timedelta(microseconds=self._hours_microseconds(hours))

    def calculate_working_hours(self, start: datetime, finish: datetime) -> Decimal:
        start = self._require_datetime(start, "start")
        finish = self._require_datetime(finish, "finish")
        if finish < start:
            raise ValueError("finish must not precede start")
        microseconds = (
            (finish - start).days * 86_400_000_000
            + (finish - start).seconds * 1_000_000
            + (finish - start).microseconds
        )
        return Decimal(microseconds) / Decimal("3600000000")


@dataclass(frozen=True)
class CalendarReference:
    """Stable, portable reference to a versioned scheduling calendar."""

    calendar_id: str
    calendar_version: str
    kind: str = "working-day"
    system: CalendarSystem = CalendarSystem.GREGORIAN

    def __post_init__(self) -> None:
        if not isinstance(self.calendar_id, str) or not self.calendar_id.strip():
            raise ValueError("calendar_id must be a non-empty string")
        if not isinstance(self.calendar_version, str) or not self.calendar_version.strip():
            raise ValueError("calendar_version must be a non-empty string")
        if not isinstance(self.kind, str) or self.kind not in {"working-day", "working-time"}:
            raise ValueError("unsupported calendar kind")
        if not isinstance(self.system, CalendarSystem):
            raise ValueError("system must be a CalendarSystem")


@dataclass(frozen=True)
class SchedulingCalendarContext:
    """Explicit calendar assignment for project, activity and relationship lag."""

    project: CalendarReference
    activity: CalendarReference | None = None
    relationship_lag: CalendarReference | None = None

    def effective_activity(self) -> CalendarReference:
        return self.activity or self.project

    def effective_relationship_lag(self) -> CalendarReference:
        return self.relationship_lag or self.effective_activity()

    def relationship_lag_reference(
        self,
        predecessor: CalendarReference,
        option: RelationshipLagCalendar | None = None,
    ) -> CalendarReference | None:
        selected = option
        if selected is None:
            return self.relationship_lag or self.effective_activity()
        if selected is RelationshipLagCalendar.PREDECESSOR:
            return predecessor
        if selected is RelationshipLagCalendar.SUCCESSOR:
            return self.effective_activity()
        if selected is RelationshipLagCalendar.PROJECT_DEFAULT:
            return self.project
        if selected is RelationshipLagCalendar.TWENTY_FOUR_HOUR:
            return None
        raise ValueError(f"unsupported relationship lag calendar: {selected}")


class CalendarResolverRegistry:
    """Resolves stable calendar references to authoritative Shared Core resolvers."""

    def __init__(
        self,
        day_resolvers: Mapping[str, WorkingTimeResolver] | None = None,
        time_resolvers: Mapping[str, TimeAwareWorkingTimeResolver] | None = None,
    ) -> None:
        self._day = dict(day_resolvers or {})
        self._time = dict(time_resolvers or {})

    @staticmethod
    def _key(reference: CalendarReference) -> str:
        return f"{reference.calendar_id}@{reference.calendar_version}"

    def resolve(self, reference: CalendarReference):
        key = self._key(reference)
        if reference.kind == "working-day":
            resolver = self._day.get(key)
        else:
            resolver = self._time.get(key)
        if resolver is None:
            raise KeyError(f"calendar not registered: {key}")
        calendar = getattr(resolver, "calendar", None)
        resolver_system = getattr(calendar, "system", None)
        if resolver_system is not None and resolver_system is not reference.system:
            raise ValueError(
                f"calendar system mismatch for {key}: "
                f"reference={reference.system.value}, resolver={resolver_system.value}"
            )
        return resolver

    def resolve_relationship_lag(
        self,
        successor_context: SchedulingCalendarContext,
        predecessor_reference: CalendarReference,
        option: RelationshipLagCalendar | None = None,
    ):
        if option is None and successor_context.relationship_lag is not None:
            return self.resolve(successor_context.relationship_lag)
        selected = option or RelationshipLagCalendar.SUCCESSOR
        reference = successor_context.relationship_lag_reference(
            predecessor_reference, selected
        )
        if reference is None:
            return Continuous24HourResolver()
        return self.resolve(reference)
