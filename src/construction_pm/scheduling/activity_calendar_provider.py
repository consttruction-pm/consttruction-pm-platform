from __future__ import annotations

"""Activity-aware calendar provider contract for the scheduling core."""

from dataclasses import dataclass
from typing import Protocol

from .calendar import WorkingTimeResolver
from .calendar_context import CalendarReference
from .calendar_resolution import ResolvedActivityCalendars


class ActivityCalendarProvider(Protocol):
    """Supplies the authoritative resolver for a specific activity."""

    def resolver_for(self, activity_id: str) -> WorkingTimeResolver:
        ...

    def reference_for(self, activity_id: str) -> CalendarReference:
        ...


@dataclass(frozen=True)
class ResolvedActivityCalendarProvider:
    """Immutable adapter over version-pinned resolved activity calendars."""

    resolved: ResolvedActivityCalendars

    def resolver_for(self, activity_id: str) -> WorkingTimeResolver:
        return self.resolved.for_activity(activity_id)

    def reference_for(self, activity_id: str) -> CalendarReference:
        return self.resolved.reference_for(activity_id)


def require_activity_calendar_provider(
    provider: ActivityCalendarProvider,
    activity_id: str,
) -> WorkingTimeResolver:
    """Resolve an activity calendar at an explicit calculation boundary."""
    return provider.resolver_for(activity_id)
