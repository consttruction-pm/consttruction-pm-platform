from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Mapping

from .calendar_context import (
    CalendarResolverRegistry,
    RelationshipLagCalendar,
    SchedulingCalendarContext,
)
from .relationships import RelationshipType
from .time_calendar import TimeAwareWorkingTimeResolver
from .time_duration import DurationUnit, LagQuantity, TimeQuantity
from .time_constraints import TimeActivityConstraint, apply_time_earliest_constraints, validate_time_early_window


@dataclass(frozen=True)
class TimeActivity:
    id: str
    duration: TimeQuantity
    calendar_context: SchedulingCalendarContext | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("activity id is required")


@dataclass(frozen=True)
class TimeRelationship:
    predecessor_id: str
    successor_id: str
    type: RelationshipType = RelationshipType.FS
    lag: LagQuantity = LagQuantity.working_hours(0)

    def __post_init__(self) -> None:
        if not self.predecessor_id or not self.successor_id:
            raise ValueError("relationship endpoints are required")
        if self.predecessor_id == self.successor_id:
            raise ValueError("self relationships are not allowed")


@dataclass(frozen=True)
class TimeScheduledActivity:
    activity_id: str
    start: datetime
    finish: datetime
    duration: TimeQuantity


def _resolver_for_activity(
    activity: TimeActivity,
    registry: CalendarResolverRegistry,
) -> TimeAwareWorkingTimeResolver:
    context = activity.calendar_context
    if context is None:
        raise ValueError("time-aware activity requires a calendar context")
    resolver = registry.resolve(context.effective_activity())
    if not isinstance(resolver, TimeAwareWorkingTimeResolver):
        raise TypeError("time-aware activity requires a working-time resolver")
    return resolver


def _add_signed_lag(
    anchor: datetime,
    lag: LagQuantity,
    resolver: TimeAwareWorkingTimeResolver | object,
) -> datetime:
    if lag.unit is not DurationUnit.WORKING_HOUR:
        raise NotImplementedError(
            "working-day lag is not implicitly converted to hours"
        )
    if lag.value >= 0:
        return resolver.add_working_hours(anchor, lag.value)
    return resolver.subtract_working_hours(anchor, -lag.value)


def _add_duration(
    start: datetime,
    duration: TimeQuantity,
    resolver: TimeAwareWorkingTimeResolver,
) -> datetime:
    if duration.unit is not DurationUnit.WORKING_HOUR:
        raise NotImplementedError(
            "working-day duration is not implicitly converted to hours"
        )
    return resolver.add_working_hours(start, duration.value)


def time_forward_pass(
    activities: Iterable[TimeActivity],
    relationships: Iterable[TimeRelationship],
    project_start: datetime,
    registry: CalendarResolverRegistry,
    constraints: Iterable[TimeActivityConstraint] = (),
    relationship_lag_calendar: RelationshipLagCalendar | None = None,
) -> Mapping[str, TimeScheduledActivity]:
    """Earliest-start pass for the explicit working-hour scheduling contract.

    This integration slice supports working-hour durations and signed
    working-hour lag. Working-day conversion remains explicit and is not
    inferred from a fixed hours-per-day assumption.
    """
    activity_list = list(activities)
    activity_map = {a.id: a for a in activity_list}
    if len(activity_map) != len(activity_list):
        raise ValueError("activity ids must be unique")
    if not activity_map:
        return {}

    # The project calendar is authoritative for the project boundary. Activity
    # calendars may differ, but every activity must belong to the same project
    # calendar and the project start must first be normalized in that calendar.
    first_context = activity_list[0].calendar_context
    if first_context is None:
        raise ValueError("time-aware activity requires a calendar context")
    project_ref = first_context.project
    for activity in activity_list[1:]:
        context = activity.calendar_context
        if context is None:
            raise ValueError("time-aware activity requires a calendar context")
        if context.project != project_ref:
            raise ValueError("time-aware activities must share one project calendar")
    project_resolver = registry.resolve(project_ref)
    if not isinstance(project_resolver, TimeAwareWorkingTimeResolver):
        raise TypeError("time-aware project calendar requires a working-time resolver")
    normalized_project_start = project_resolver.normalize_start(project_start)

    relationship_list = list(relationships)
    for rel in relationship_list:
        if rel.predecessor_id not in activity_map or rel.successor_id not in activity_map:
            raise ValueError("relationship references an unknown activity")

    incoming: dict[str, list[TimeRelationship]] = {a.id: [] for a in activity_list}
    outgoing: dict[str, list[str]] = {a.id: [] for a in activity_list}
    counts = {a.id: 0 for a in activity_list}
    for rel in relationship_list:
        incoming[rel.successor_id].append(rel)
        outgoing[rel.predecessor_id].append(rel.successor_id)
        counts[rel.successor_id] += 1

    ready = sorted(k for k, v in counts.items() if v == 0)
    order: list[str] = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for nxt in sorted(outgoing[current]):
            counts[nxt] -= 1
            if counts[nxt] == 0:
                ready.append(nxt)
                ready.sort()
    if len(order) != len(activity_map):
        raise ValueError("activity network contains a cycle")

    constraint_list = list(constraints)
    result: dict[str, TimeScheduledActivity] = {}
    for activity_id in order:
        activity = activity_map[activity_id]
        resolver = _resolver_for_activity(activity, registry)
        start = (
            resolver.normalize_start(normalized_project_start)
            if not incoming[activity_id]
            else None
        )

        for rel in sorted(
            incoming[activity_id],
            key=lambda x: (x.predecessor_id, x.successor_id, x.type.value, str(x.lag.value), x.lag.unit.value),
        ):
            predecessor = result[rel.predecessor_id]
            lag_context = activity_map[rel.successor_id].calendar_context
            if lag_context is None:
                raise ValueError("time-aware successor requires a calendar context")
            lag_resolver = registry.resolve_relationship_lag(
                lag_context,
                activity_map[rel.predecessor_id].calendar_context.effective_activity()
                if activity_map[rel.predecessor_id].calendar_context is not None
                else lag_context.effective_activity(),
                relationship_lag_calendar,
            )
            if not hasattr(lag_resolver, "add_working_hours"):
                raise TypeError("relationship lag resolver must support working-hour arithmetic")
            anchor = {
                RelationshipType.FS: predecessor.finish,
                RelationshipType.SS: predecessor.start,
                RelationshipType.FF: predecessor.finish,
                RelationshipType.SF: predecessor.start,
            }[rel.type]
            target = _add_signed_lag(anchor, rel.lag, lag_resolver)
            if rel.type in {RelationshipType.FF, RelationshipType.SF}:
                candidate = _subtract_duration(target, activity.duration, resolver)
            else:
                candidate = target
            start = candidate if start is None else max(start, candidate)

        assert start is not None
        start = resolver.normalize_start(start)
        start = apply_time_earliest_constraints(activity, start, activity.duration, constraint_list, registry)
        finish = _add_duration(start, activity.duration, resolver)
        validate_time_early_window(activity, start, finish, constraint_list, registry)
        result[activity_id] = TimeScheduledActivity(activity_id, start, finish, activity.duration)

    return result


def _subtract_duration(
    finish: datetime,
    duration: TimeQuantity,
    resolver: TimeAwareWorkingTimeResolver,
) -> datetime:
    if duration.unit is not DurationUnit.WORKING_HOUR:
        raise NotImplementedError(
            "working-day duration is not implicitly converted to hours"
        )
    return resolver.subtract_working_hours(finish, duration.value)
