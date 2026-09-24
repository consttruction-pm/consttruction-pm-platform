from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .calendar import WorkingTimeResolver
from .time_calendar import TimeAwareWorkingTimeResolver


@dataclass(frozen=True)
class CalendarReference:
    """Stable, portable reference to a versioned scheduling calendar."""

    calendar_id: str
    calendar_version: str
    kind: str = "working-day"

    def __post_init__(self) -> None:
        if not self.calendar_id or not self.calendar_version:
            raise ValueError("calendar_id and calendar_version are required")
        if self.kind not in {"working-day", "working-time"}:
            raise ValueError("unsupported calendar kind")


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
        return resolver
