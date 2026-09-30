from __future__ import annotations

"""Materialize authoritative calendar references into Shared Core resolvers."""

from dataclasses import dataclass
from typing import Mapping

from .authoritative_schedule import ActivityCalendarAssignment, AuthoritativeScheduleInput
from .calendar import WorkingTimeResolver
from .calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
    RelationshipLagCalendar,
    SchedulingCalendarContext,
)


@dataclass(frozen=True)
class ResolvedActivityCalendars:
    """Resolved, version-pinned calendars for one authoritative snapshot."""

    project: WorkingTimeResolver
    activities: Mapping[str, WorkingTimeResolver]
    references: Mapping[str, CalendarReference]

    def for_activity(self, activity_id: str) -> WorkingTimeResolver:
        try:
            return self.activities[activity_id]
        except KeyError as exc:
            raise KeyError(f"activity calendar is not resolved: {activity_id}") from exc

    def reference_for(self, activity_id: str) -> CalendarReference:
        try:
            return self.references[activity_id]
        except KeyError as exc:
            raise KeyError(f"activity calendar reference is not resolved: {activity_id}") from exc


def resolve_authoritative_activity_calendars(
    snapshot: AuthoritativeScheduleInput,
    registry: CalendarResolverRegistry,
) -> ResolvedActivityCalendars:
    """Resolve every activity to its explicit or project calendar.

    Resolution is fail-fast: an invalid/missing versioned calendar is rejected
    before any scheduling calculation can begin.
    """
    project_resolver = registry.resolve(snapshot.project_calendar)
    assignments = {
        assignment.activity_id: assignment for assignment in snapshot.activity_calendar_assignments
    }

    resolved: dict[str, WorkingTimeResolver] = {}
    references: dict[str, CalendarReference] = {}
    for activity in snapshot.activities:
        assignment: ActivityCalendarAssignment | None = assignments.get(activity.id)
        reference = assignment.calendar if assignment is not None else snapshot.project_calendar
        resolver = registry.resolve(reference)
        resolved[activity.id] = resolver
        references[activity.id] = reference

    return ResolvedActivityCalendars(
        project=project_resolver,
        activities=resolved,
        references=references,
    )


def resolve_relationship_lag_calendar(
    snapshot: AuthoritativeScheduleInput,
    registry: CalendarResolverRegistry,
    predecessor_activity_id: str,
    successor_activity_id: str,
    option: RelationshipLagCalendar | None = None,
):
    """Resolve the lag calendar from the authoritative activity assignments."""
    calendars = resolve_authoritative_activity_calendars(snapshot, registry)
    predecessor_reference = calendars.reference_for(predecessor_activity_id)
    successor_reference = calendars.reference_for(successor_activity_id)
    context = SchedulingCalendarContext(
        project=snapshot.project_calendar,
        activity=successor_reference,
    )
    return registry.resolve_relationship_lag(context, predecessor_reference, option)
