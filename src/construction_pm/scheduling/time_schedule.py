from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Mapping

from .calendar_context import CalendarResolverRegistry
from .relationships import RelationshipType
from .time_calendar import TimeAwareWorkingTimeResolver
from .time_duration import DurationUnit, LagQuantity, TimeQuantity
from .time_forward_pass import TimeActivity, TimeRelationship, TimeScheduledActivity, time_forward_pass
from .time_constraints import TimeActivityConstraint, TimeConstraintViolation, apply_time_latest_constraints, validate_time_early_window


@dataclass(frozen=True)
class TimeFloatActivity:
    activity_id: str
    early_start: datetime
    early_finish: datetime
    late_start: datetime
    late_finish: datetime
    total_float_hours: Decimal
    free_float_hours: Decimal
    critical: bool


@dataclass(frozen=True)
class TimeScheduleResult:
    activities: Mapping[str, TimeScheduledActivity]
    early_activities: Mapping[str, TimeScheduledActivity]
    late_activities: Mapping[str, TimeScheduledActivity]
    floats: Mapping[str, TimeFloatActivity]
    project_finish: datetime


def _resolver(activity: TimeActivity, registry: CalendarResolverRegistry) -> TimeAwareWorkingTimeResolver:
    if activity.calendar_context is None:
        raise ValueError("time-aware activity requires a calendar context")
    resolved = registry.resolve(activity.calendar_context.effective_activity())
    if not isinstance(resolved, TimeAwareWorkingTimeResolver):
        raise TypeError("time-aware scheduling requires a working-time resolver")
    return resolved


def _inverse_lag(event: datetime, lag: LagQuantity, resolver: TimeAwareWorkingTimeResolver) -> datetime:
    if lag.unit is not DurationUnit.WORKING_HOUR:
        raise NotImplementedError("time-aware scheduling requires working-hour lag")
    if lag.value >= 0:
        return resolver.subtract_working_hours(event, lag.value)
    return resolver.add_working_hours(event, -lag.value)


def _subtract_duration(
    finish: datetime,
    duration: TimeQuantity,
    resolver: TimeAwareWorkingTimeResolver,
) -> datetime:
    if duration.unit is not DurationUnit.WORKING_HOUR:
        raise NotImplementedError("time-aware scheduling requires working-hour duration")
    return resolver.subtract_working_hours(finish, duration.value)


def _add_duration(
    start: datetime,
    duration: TimeQuantity,
    resolver: TimeAwareWorkingTimeResolver,
) -> datetime:
    if duration.unit is not DurationUnit.WORKING_HOUR:
        raise NotImplementedError("time-aware scheduling requires working-hour duration")
    return resolver.add_working_hours(start, duration.value)


def _latest_predecessor_start(
    relationship: TimeRelationship,
    successor: TimeScheduledActivity,
    successor_activity: TimeActivity,
    predecessor: TimeActivity,
    registry: CalendarResolverRegistry,
) -> datetime:
    if predecessor.calendar_context is None or successor_activity.calendar_context is None:
        raise ValueError("time-aware activities require calendar contexts")
    # Relationship lag calendar is selected from the successor-side context.
    lag_ref = successor_activity.calendar_context.effective_relationship_lag()
    lag_resolver = registry.resolve(lag_ref)
    if not isinstance(lag_resolver, TimeAwareWorkingTimeResolver):
        raise TypeError("time-aware relationship lag requires a working-time resolver")

    if relationship.type is RelationshipType.FS:
        event = _inverse_lag(successor.start, relationship.lag, lag_resolver)
        return _subtract_duration(event, predecessor.duration, _resolver(predecessor, registry))
    if relationship.type is RelationshipType.SS:
        return _inverse_lag(successor.start, relationship.lag, lag_resolver)
    if relationship.type is RelationshipType.FF:
        event = _inverse_lag(successor.finish, relationship.lag, lag_resolver)
        return _subtract_duration(event, predecessor.duration, _resolver(predecessor, registry))
    if relationship.type is RelationshipType.SF:
        return _inverse_lag(successor.finish, relationship.lag, lag_resolver)
    raise ValueError(f"unsupported relationship type: {relationship.type}")


def time_backward_pass(
    activities: Iterable[TimeActivity],
    relationships: Iterable[TimeRelationship],
    early: Mapping[str, TimeScheduledActivity],
    project_finish: datetime,
    registry: CalendarResolverRegistry,
    constraints: Iterable[TimeActivityConstraint] = (),
) -> Mapping[str, TimeScheduledActivity]:
    activity_list = list(activities)
    activity_map = {a.id: a for a in activity_list}
    if set(activity_map) != set(early):
        raise ValueError("early schedule must contain every activity")
    relationship_list = list(relationships)
    constraint_list = list(constraints)
    outgoing: dict[str, list[TimeRelationship]] = {a.id: [] for a in activity_list}
    incoming_count = {a.id: 0 for a in activity_list}
    successors: dict[str, list[str]] = {a.id: [] for a in activity_list}
    for rel in relationship_list:
        if rel.predecessor_id not in activity_map or rel.successor_id not in activity_map:
            raise ValueError("relationship references an unknown activity")
        outgoing[rel.predecessor_id].append(rel)
        successors[rel.predecessor_id].append(rel.successor_id)
        incoming_count[rel.successor_id] += 1

    ready = sorted(a_id for a_id, count in incoming_count.items() if count == 0)
    order: list[str] = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for successor_id in sorted(successors[current]):
            incoming_count[successor_id] -= 1
            if incoming_count[successor_id] == 0:
                ready.append(successor_id)
                ready.sort()
    if len(order) != len(activity_map):
        raise ValueError("activity network contains a cycle")

    early_finish = max(item.finish for item in early.values())
    project_finish_resolver = _resolver(activity_map[order[-1]], registry)
    normalized_finish = project_finish_resolver.normalize_finish(project_finish)
    if normalized_finish < early_finish:
        raise ValueError("project finish cannot be earlier than early project finish")

    late: dict[str, TimeScheduledActivity] = {}
    for activity_id in reversed(order):
        activity = activity_map[activity_id]
        resolver = _resolver(activity, registry)
        rels = sorted(
            outgoing[activity_id],
            key=lambda x: (x.successor_id, x.predecessor_id, x.type.value, str(x.lag.value), x.lag.unit.value),
        )
        if not rels:
            late_finish = normalized_finish
            late_start = _subtract_duration(late_finish, activity.duration, resolver)
            late_start = apply_time_latest_constraints(activity, late_start, activity.duration, constraint_list, registry)
        else:
            candidates = [
                _latest_predecessor_start(rel, late[rel.successor_id], activity_map[rel.successor_id], activity, registry)
                for rel in rels
            ]
            late_start = min(candidates)
            late_start = apply_time_latest_constraints(activity, late_start, activity.duration, constraint_list, registry)
            late_finish = _add_duration(late_start, activity.duration, resolver)
        late[activity_id] = TimeScheduledActivity(activity_id, late_start, late_finish, activity.duration)

    for rel in relationship_list:
        predecessor = late[rel.predecessor_id]
        successor = late[rel.successor_id]
        lag_context = activity_map[rel.successor_id].calendar_context
        if lag_context is None:
            raise ValueError("time-aware successor requires a calendar context")
        lag_resolver = registry.resolve(lag_context.effective_relationship_lag())
        if not isinstance(lag_resolver, TimeAwareWorkingTimeResolver):
            raise TypeError("time-aware relationship lag requires a working-time resolver")
        required = {
            RelationshipType.FS: _inverse_lag(successor.start, rel.lag, lag_resolver),
            RelationshipType.SS: _inverse_lag(successor.start, rel.lag, lag_resolver),
            RelationshipType.FF: _inverse_lag(successor.finish, rel.lag, lag_resolver),
            RelationshipType.SF: _inverse_lag(successor.finish, rel.lag, lag_resolver),
        }[rel.type]
        if rel.type in {RelationshipType.FS, RelationshipType.FF}:
            if predecessor.finish > required:
                raise ValueError(f"backward schedule violates {rel.predecessor_id}->{rel.successor_id}")
        else:
            if predecessor.start > required:
                raise ValueError(f"backward schedule violates {rel.predecessor_id}->{rel.successor_id}")

    return late


def calculate_time_floats(
    activities: Iterable[TimeActivity],
    relationships: Iterable[TimeRelationship],
    early: Mapping[str, TimeScheduledActivity],
    late: Mapping[str, TimeScheduledActivity],
    registry: CalendarResolverRegistry,
) -> Mapping[str, TimeFloatActivity]:
    activity_map = {a.id: a for a in activities}
    outgoing = {a.id: [] for a in activity_map}
    for rel in relationships:
        outgoing[rel.predecessor_id].append(rel)

    result: dict[str, TimeFloatActivity] = {}
    for activity_id in sorted(activity_map):
        activity = activity_map[activity_id]
        resolver = _resolver(activity, registry)
        e = early[activity_id]
        l = late[activity_id]
        total = resolver.calculate_working_hours(e.start, l.start)
        if l.start < e.start:
            total = -resolver.calculate_working_hours(l.start, e.start)

        if not outgoing[activity_id]:
            free = Decimal("0")
        else:
            limits: list[Decimal] = []
            for rel in outgoing[activity_id]:
                successor = early[rel.successor_id]
                if rel.lag.unit is not DurationUnit.WORKING_HOUR:
                    raise NotImplementedError("time-aware float requires working-hour lag")
                lag_context = activity_map[rel.successor_id].calendar_context
                if lag_context is None:
                    raise ValueError("successor requires calendar context")
                lag_resolver = registry.resolve(lag_context.effective_relationship_lag())
                if rel.type in {RelationshipType.FS, RelationshipType.FF, RelationshipType.SF, RelationshipType.SS}:
                    # Measure slack by delaying the predecessor and checking the
                    # relationship event in the authoritative lag calendar.
                    delay = Decimal("0")
                    for _ in range(10000):
                        candidate_start = resolver.add_working_hours(e.start, delay)
                        candidate_finish = _add_duration(candidate_start, activity.duration, resolver)
                        if rel.type is RelationshipType.FS:
                            event = candidate_finish
                            required = _add_signed_lag_for_float(event, rel.lag, lag_resolver)
                            holds = successor.start >= required
                        elif rel.type is RelationshipType.SS:
                            event = candidate_start
                            required = _add_signed_lag_for_float(event, rel.lag, lag_resolver)
                            holds = successor.start >= required
                        elif rel.type is RelationshipType.FF:
                            event = candidate_finish
                            required = _add_signed_lag_for_float(event, rel.lag, lag_resolver)
                            holds = successor.finish >= required
                        else:
                            event = candidate_start
                            required = _add_signed_lag_for_float(event, rel.lag, lag_resolver)
                            holds = successor.finish >= required
                        if not holds:
                            break
                        delay += Decimal("1")
                    limits.append(max(Decimal("0"), delay - Decimal("1")))
            free = min(limits) if limits else Decimal("0")

        result[activity_id] = TimeFloatActivity(
            activity_id=activity_id,
            early_start=e.start,
            early_finish=e.finish,
            late_start=l.start,
            late_finish=l.finish,
            total_float_hours=total,
            free_float_hours=min(total, free),
            critical=total <= 0,
        )
    return result


def _add_signed_lag_for_float(
    anchor: datetime,
    lag: LagQuantity,
    resolver: TimeAwareWorkingTimeResolver,
) -> datetime:
    if lag.unit is not DurationUnit.WORKING_HOUR:
        raise NotImplementedError("time-aware float requires working-hour lag")
    if lag.value >= 0:
        return resolver.add_working_hours(anchor, lag.value)
    return resolver.subtract_working_hours(anchor, -lag.value)


def time_schedule(
    activities: Iterable[TimeActivity],
    relationships: Iterable[TimeRelationship],
    project_start: datetime,
    project_finish: datetime | None,
    registry: CalendarResolverRegistry,
    constraints: Iterable[TimeActivityConstraint] = (),
) -> TimeScheduleResult:
    activity_list = list(activities)
    relationship_list = list(relationships)
    constraint_list = list(constraints)
    early = time_forward_pass(activity_list, relationship_list, project_start, registry, constraint_list)
    effective_finish = project_finish or max(item.finish for item in early.values())
    late = time_backward_pass(activity_list, relationship_list, early, effective_finish, registry, constraint_list)
    floats = calculate_time_floats(activity_list, relationship_list, early, late, registry)
    return TimeScheduleResult(
        activities=early,
        early_activities=early,
        late_activities=late,
        floats=floats,
        project_finish=effective_finish,
    )
