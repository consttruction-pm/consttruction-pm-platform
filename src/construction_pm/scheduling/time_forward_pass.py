from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Iterable, Mapping

from .calendar_context import CalendarResolverRegistry, SchedulingCalendarContext
from .relationships import RelationshipType
from .time_calendar import TimeAwareWorkingTimeResolver
from .time_duration import DurationUnit, LagQuantity, TimeQuantity


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
    resolver: TimeAwareWorkingTimeResolver,
) -> datetime:
    if lag.unit is not DurationUnit.WORKING_HOUR:
        raise NotImplementedError(
            "working-day lag is not implicitly converted to hours"
        )
    if lag.value >= 0:
        return resolver.add_working_hours(anchor, lag.value)
    # A signed lead requires inverse working-hour arithmetic; do not approximate
    # it with elapsed clock time.
    raise NotImplementedError(
        "negative working-hour lag requires inverse working-time arithmetic"
    )


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
) -> Mapping[str, TimeScheduledActivity]:
    """Earliest-start pass for the explicit working-hour scheduling contract.

    This first integration slice intentionally supports working-hour durations
    and non-negative working-hour lag. Working-day conversion and negative
    time-based lead are separate gates because both require explicit inverse
    calendar semantics rather than elapsed-clock approximations.
    """
    activity_list = list(activities)
    activity_map = {a.id: a for a in activity_list}
    if len(activity_map) != len(activity_list):
        raise ValueError("activity ids must be unique")
    if not activity_map:
        return {}

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

    result: dict[str, TimeScheduledActivity] = {}
    for activity_id in order:
        activity = activity_map[activity_id]
        resolver = _resolver_for_activity(activity, registry)
        start = resolver.normalize_start(project_start) if not incoming[activity_id] else None

        for rel in sorted(
            incoming[activity_id],
            key=lambda x: (x.predecessor_id, x.successor_id, x.type.value, str(x.lag.value), x.lag.unit.value),
        ):
            predecessor = result[rel.predecessor_id]
            lag_context = activity_map[rel.successor_id].calendar_context
            if lag_context is None:
                raise ValueError("time-aware successor requires a calendar context")
            lag_resolver = registry.resolve(lag_context.effective_relationship_lag())
            if not isinstance(lag_resolver, TimeAwareWorkingTimeResolver):
                raise TypeError("time-aware relationship lag requires a working-time resolver")
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
        finish = _add_duration(start, activity.duration, resolver)
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
    remaining = duration.value
    # Inverse arithmetic is deliberately exact over working intervals.
    cursor = finish
    for _ in range(3660):
        intervals = resolver.calendar.intervals_for(cursor.date())
        for interval_start, interval_end in reversed(intervals):
            begin = datetime.combine(cursor.date(), interval_start)
            end = datetime.combine(cursor.date(), interval_end)
            right = min(cursor, end)
            if right <= begin:
                continue
            capacity = (right - begin).total_seconds() / 3600
            if remaining <= 0:
                return cursor
            if remaining <= capacity:
                    return right - timedelta(seconds=float(remaining * Decimal(3600)))
            remaining -= Decimal(str(capacity))
            cursor = begin
        cursor = datetime.combine(cursor.date() - timedelta(days=1), time.max)
    raise ValueError("working-hour duration exceeds resolver horizon")
