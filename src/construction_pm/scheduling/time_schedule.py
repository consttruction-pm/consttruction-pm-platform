from __future__ import annotations

import multiprocessing
import threading
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterable, Mapping

from .calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
    RelationshipLagCalendar,
)
from .schedule_options import StartToStartLagCalculationType
from .relationships import RelationshipType
from .time_calendar import TimeAwareWorkingTimeResolver
from .time_duration import DurationUnit, LagQuantity, TimeQuantity
from .time_forward_pass import TimeActivity, TimeRelationship, TimeScheduledActivity, time_forward_pass
from .time_constraints import TimeActivityConstraint, TimeConstraintViolation, apply_time_latest_constraints, validate_time_late_window
from .time_unit_resolver import CalendarAwareResolver, resolve_calendar_aware


@dataclass(frozen=True)
class TimeScheduleOptions:
    relationship_lag_calendar: RelationshipLagCalendar | None = None
    start_to_start_lag_calculation_type: StartToStartLagCalculationType = (
        StartToStartLagCalculationType.EARLY_START
    )
    data_date: datetime | None = None


@dataclass(frozen=True)
class TimeFloatActivity:
    activity_id: str
    early_start: datetime
    early_finish: datetime
    late_start: datetime
    late_finish: datetime
    total_float_hours: Decimal | None
    free_float_hours: Decimal | None
    total_float_value: Decimal
    free_float_value: Decimal
    float_unit: DurationUnit
    critical: bool


@dataclass(frozen=True)
class TimeScheduleResult:
    activities: Mapping[str, TimeScheduledActivity]
    early_activities: Mapping[str, TimeScheduledActivity]
    late_activities: Mapping[str, TimeScheduledActivity]
    floats: Mapping[str, TimeFloatActivity]
    project_finish: datetime


def _project_resolver(activity: TimeActivity, registry: CalendarResolverRegistry) -> CalendarAwareResolver:
    if activity.calendar_context is None:
        raise ValueError("time-aware activity requires a calendar context")
    return resolve_calendar_aware(registry, activity.calendar_context.project)


def _validate_project_calendar_context(
    activities: Iterable[TimeActivity],
) -> None:
    activity_list = list(activities)
    if not activity_list:
        return
    first = activity_list[0].calendar_context
    if first is None:
        raise ValueError("time-aware activity requires a calendar context")
    project_ref = first.project
    for activity in activity_list[1:]:
        context = activity.calendar_context
        if context is None:
            raise ValueError("time-aware activity requires a calendar context")
        if context.project != project_ref:
            raise ValueError("time-aware activities must share one project calendar")


def _resolver(activity: TimeActivity, registry: CalendarResolverRegistry) -> CalendarAwareResolver:
    if activity.calendar_context is None:
        raise ValueError("time-aware activity requires a calendar context")
    return resolve_calendar_aware(registry, activity.calendar_context.effective_activity())


def _inverse_lag(event: datetime, lag: LagQuantity, resolver: CalendarAwareResolver) -> datetime:
    return resolver.subtract_lag(event, lag)


def _add_signed_lag_for_float(
    event: datetime,
    lag: LagQuantity,
    resolver: CalendarAwareResolver,
) -> datetime:
    """Apply a signed relationship lag for float reconciliation."""
    return resolver.add_lag(event, lag)


def _subtract_duration(
    finish: datetime,
    duration: TimeQuantity,
    resolver: CalendarAwareResolver,
) -> datetime:
    return resolver.subtract_duration(finish, duration)


def _add_duration(
    start: datetime,
    duration: TimeQuantity,
    resolver: CalendarAwareResolver,
) -> datetime:
    return resolver.add_duration(start, duration)


def _latest_predecessor_start(
    relationship: TimeRelationship,
    successor: TimeScheduledActivity,
    successor_activity: TimeActivity,
    predecessor: TimeActivity,
    registry: CalendarResolverRegistry,
    relationship_lag_calendar: RelationshipLagCalendar | None = None,
) -> datetime:
    if predecessor.calendar_context is None or successor_activity.calendar_context is None:
        raise ValueError("time-aware activities require calendar contexts")
    lag_context = successor_activity.calendar_context
    predecessor_context = predecessor.calendar_context
    if predecessor_context is None:
        raise ValueError("time-aware predecessor requires a calendar context")
    lag_resolver = registry.resolve_relationship_lag(
        lag_context,
        predecessor_context.effective_activity(),
        relationship_lag_calendar,
    )
    if relationship_lag_calendar is RelationshipLagCalendar.TWENTY_FOUR_HOUR:
        lag_resolver = CalendarAwareResolver(
            CalendarReference("24-hour", "1", "working-time"), lag_resolver
        )
    else:
        lag_reference = lag_context.relationship_lag_reference(predecessor_context.effective_activity())
        lag_resolver = resolve_calendar_aware(registry, lag_reference)

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
    relationship_lag_calendar: RelationshipLagCalendar | None = None,
) -> Mapping[str, TimeScheduledActivity]:
    activity_list = list(activities)
    _validate_project_calendar_context(activity_list)
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
    project_finish_resolver = _project_resolver(activity_map[order[0]], registry)
    normalized_finish = project_finish_resolver.normalize_finish(project_finish)

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
            late_finish = _add_duration(late_start, activity.duration, resolver)
        else:
            candidates = [
                _latest_predecessor_start(
                    rel,
                    late[rel.successor_id],
                    activity_map[rel.successor_id],
                    activity,
                    registry,
                    relationship_lag_calendar,
                )
                for rel in rels
            ]
            late_start = min(candidates)
            latest_by_project_finish = _subtract_duration(
                normalized_finish, activity.duration, resolver
            )
            late_start = min(late_start, latest_by_project_finish)
            late_start = apply_time_latest_constraints(activity, late_start, activity.duration, constraint_list, registry)
            late_finish = _add_duration(late_start, activity.duration, resolver)
        validate_time_late_window(activity, late_start, late_finish, constraint_list, registry)
        late[activity_id] = TimeScheduledActivity(activity_id, late_start, late_finish, activity.duration)

    for rel in relationship_list:
        predecessor = late[rel.predecessor_id]
        successor = late[rel.successor_id]
        lag_context = activity_map[rel.successor_id].calendar_context
        predecessor_context = activity_map[rel.predecessor_id].calendar_context
        if lag_context is None or predecessor_context is None:
            raise ValueError("time-aware relationship activities require calendar contexts")
        raw_lag_resolver = registry.resolve_relationship_lag(
            lag_context,
            predecessor_context.effective_activity(),
            relationship_lag_calendar,
        )
        if relationship_lag_calendar is RelationshipLagCalendar.TWENTY_FOUR_HOUR:
            lag_resolver = CalendarAwareResolver(
                CalendarReference("24-hour", "1", "working-time"), raw_lag_resolver
            )
        else:
            lag_reference = lag_context.relationship_lag_reference(predecessor_context.effective_activity())
            lag_resolver = resolve_calendar_aware(registry, lag_reference)
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


_FREE_FLOAT_SEARCH_CEILING = Decimal("10000")
_FREE_FLOAT_LINEAR_PREFIX = 8


def _legacy_free_float_limit(holds) -> Decimal:
    """The pre-P0-C linear probe, retained as the differential oracle.

    Increments the delay from zero and stops at the first delay for which the
    relationship event no longer holds.  If the relationship still holds after
    9999 increments the reported limit is 9999, which is the historical
    sentinel for "no boundary found inside the scan bound".
    """

    delay = Decimal("0")
    for _ in range(10000):
        if not holds(delay):
            break
        delay += Decimal("1")
    return max(Decimal("0"), delay - Decimal("1"))


def _free_float_limit(holds) -> Decimal:
    """Locate the same Free Float boundary as the legacy scan with O(log) probes.

    The legacy scan evaluated delays 0..9999 in order and reported the last
    delay that still held.  Calendar arithmetic is monotone in the delay: a
    later predecessor start can only move ``candidate_start`` and
    ``candidate_finish`` forward (never backward), and the required event is a
    non-decreasing function of that event for every relationship type, signed
    lag and working-time/working-day calendar.  Therefore the predicate is
    true for a prefix ``0..F-1`` and false from ``F`` onward, and the boundary
    can be found by exponential growth followed by a binary search.

    Boundaries are preserved exactly:

    * ``holds(0)`` false -> ``0`` (the legacy loop never advanced).
    * ``F > 0`` -> ``F - 1``.
    * no failure among 0..9999 -> ``9999`` (legacy sentinel), whether or not
      the relationship would still hold at delay 10000.  Evaluating delay
      10000 is only used to disambiguate the search interval; the reported
      value stays 9999.

    The first eight delays are still probed linearly so the common tiny-Free-
    Float case costs exactly what it did before.
    """

    probe = Decimal("0")
    while probe < _FREE_FLOAT_LINEAR_PREFIX:
        if not holds(probe):
            return max(Decimal("0"), probe - Decimal("1"))
        probe += Decimal("1")

    low = probe - Decimal("1")  # last delay known to hold
    high = probe * Decimal("2")
    while high < _FREE_FLOAT_SEARCH_CEILING and holds(high):
        low = high
        high *= Decimal("2")
    if high >= _FREE_FLOAT_SEARCH_CEILING:
        if not holds(_FREE_FLOAT_SEARCH_CEILING):
            high = _FREE_FLOAT_SEARCH_CEILING
        else:
            return _FREE_FLOAT_SEARCH_CEILING - Decimal("1")
    while high - low > Decimal("1"):
        middle = (low + high) // Decimal("2")
        if holds(middle):
            low = middle
        else:
            high = middle
    return high - Decimal("1")


@dataclass(frozen=True)
class _TimeFloatContext:
    """Everything one activity's float calculation needs, and nothing mutable."""

    activity_map: Mapping[str, TimeActivity]
    outgoing: Mapping[str, tuple[TimeRelationship, ...]]
    early: Mapping[str, TimeScheduledActivity]
    late: Mapping[str, TimeScheduledActivity]
    registry: CalendarResolverRegistry
    relationship_lag_calendar: RelationshipLagCalendar | None


def _time_float_context(
    activities: Iterable[TimeActivity],
    relationships: Iterable[TimeRelationship],
    early: Mapping[str, TimeScheduledActivity],
    late: Mapping[str, TimeScheduledActivity],
    registry: CalendarResolverRegistry,
    relationship_lag_calendar: RelationshipLagCalendar | None,
) -> _TimeFloatContext:
    activity_map = {a.id: a for a in activities}
    outgoing: dict[str, list[TimeRelationship]] = {activity_id: [] for activity_id in activity_map}
    for rel in relationships:
        outgoing[rel.predecessor_id].append(rel)
    return _TimeFloatContext(
        activity_map=activity_map,
        outgoing={key: tuple(value) for key, value in outgoing.items()},
        early=early,
        late=late,
        registry=registry,
        relationship_lag_calendar=relationship_lag_calendar,
    )


def _time_float_for_activity(
    context: _TimeFloatContext, activity_id: str
) -> TimeFloatActivity:
    """Calculate one activity's float from immutable inputs only.

    The function reads no global state and mutates nothing, so evaluating it in
    a child process yields exactly the value the sequential loop would produce.
    """
    activity_map = context.activity_map
    outgoing = context.outgoing
    early = context.early
    late = context.late
    registry = context.registry
    relationship_lag_calendar = context.relationship_lag_calendar

    activity = activity_map[activity_id]
    resolver = _resolver(activity, registry)
    e = early[activity_id]
    l = late[activity_id]
    if activity.duration.unit is DurationUnit.WORKING_DAY:
        total = Decimal(resolver.resolver.working_days_between(e.start.date(), l.start.date()))
        if l.start < e.start:
            total = -Decimal(resolver.resolver.working_days_between(l.start.date(), e.start.date()))
    else:
        total = resolver.calculate_duration(e.start, l.start, activity.duration.unit)
        if l.start < e.start:
            total = -resolver.calculate_duration(l.start, e.start, activity.duration.unit)

    if not outgoing[activity_id]:
        free = Decimal("0")
    else:
        limits: list[Decimal] = []
        for rel in outgoing[activity_id]:
            successor = early[rel.successor_id]
            if rel.lag.unit not in {DurationUnit.WORKING_HOUR, DurationUnit.WORKING_DAY}:
                raise ValueError("unsupported lag unit")
            lag_context = activity_map[rel.successor_id].calendar_context
            predecessor_context = activity_map[rel.predecessor_id].calendar_context
            if lag_context is None or predecessor_context is None:
                raise ValueError("relationship activities require calendar contexts")
            raw_lag_resolver = registry.resolve_relationship_lag(
                lag_context,
                predecessor_context.effective_activity(),
                relationship_lag_calendar,
            )
            if relationship_lag_calendar is RelationshipLagCalendar.TWENTY_FOUR_HOUR:
                lag_resolver = CalendarAwareResolver(
                    CalendarReference("24-hour", "1", "working-time"), raw_lag_resolver
                )
            else:
                lag_reference = lag_context.relationship_lag_reference(predecessor_context.effective_activity())
                lag_resolver = resolve_calendar_aware(registry, lag_reference)
            if rel.type in {RelationshipType.FS, RelationshipType.FF, RelationshipType.SF, RelationshipType.SS}:
                # Measure slack by delaying the predecessor and checking the
                # relationship event in the authoritative lag calendar.
                def holds_at(delay: Decimal) -> bool:
                    delay_quantity = (
                        TimeQuantity.working_hours(delay)
                        if activity.duration.unit is DurationUnit.WORKING_HOUR
                        else TimeQuantity.working_days(delay)
                    )
                    candidate_start = resolver.add_duration(e.start, delay_quantity)
                    candidate_finish = _add_duration(candidate_start, activity.duration, resolver)
                    if rel.type is RelationshipType.FS:
                        event = candidate_finish
                        required = lag_resolver.add_lag(event, rel.lag)
                        return successor.start >= required
                    if rel.type is RelationshipType.SS:
                        event = candidate_start
                        required = _add_signed_lag_for_float(event, rel.lag, lag_resolver)
                        return successor.start >= required
                    if rel.type is RelationshipType.FF:
                        event = candidate_finish
                        required = _add_signed_lag_for_float(event, rel.lag, lag_resolver)
                        return successor.finish >= required
                    event = candidate_start
                    required = _add_signed_lag_for_float(event, rel.lag, lag_resolver)
                    return successor.finish >= required

                limits.append(_free_float_limit(holds_at))
        free = min(limits) if limits else Decimal("0")

    return TimeFloatActivity(
        activity_id=activity_id,
        early_start=e.start,
        early_finish=e.finish,
        late_start=l.start,
        late_finish=l.finish,
        total_float_hours=total if activity.duration.unit is DurationUnit.WORKING_HOUR else None,
        free_float_hours=min(total, free) if activity.duration.unit is DurationUnit.WORKING_HOUR else None,
        total_float_value=total,
        free_float_value=min(total, free),
        float_unit=activity.duration.unit,
        critical=total <= 0,
    )


# Forked children inherit this context at process creation. Nothing else is
# shared: each child computes independent activities and returns immutable
# records, so the merged mapping is exactly the sequential mapping.
_FLOAT_CONTEXT: _TimeFloatContext | None = None
_FLOAT_FORK_LOCK = threading.Lock()


def _float_chunk(activity_ids: list[str]) -> list[TimeFloatActivity]:
    context = _FLOAT_CONTEXT
    if context is None:
        raise RuntimeError("FLOAT_CONTEXT_NOT_INITIALIZED")
    return [_time_float_for_activity(context, activity_id) for activity_id in activity_ids]


def _chunk_activity_ids(activity_ids: list[str], workers: int) -> list[list[str]]:
    if workers <= 1 or len(activity_ids) <= 1:
        return [activity_ids]
    size = max(1, -(-len(activity_ids) // workers))
    return [activity_ids[index : index + size] for index in range(0, len(activity_ids), size)]


def _parallel_time_floats(
    context: _TimeFloatContext, activity_ids: list[str], workers: int
) -> dict[str, TimeFloatActivity]:
    """Evaluate independent activities in forked children, then merge by id.

    Falls back to the sequential loop when the platform has no ``fork`` or when
    the caller is multithreaded, because forking a threaded process is not safe.
    Both paths are exactly equivalent; the fallback changes only speed.
    """
    global _FLOAT_CONTEXT
    chunks = _chunk_activity_ids(activity_ids, workers)
    if len(chunks) <= 1:
        return {activity_id: _time_float_for_activity(context, activity_id) for activity_id in activity_ids}
    if threading.active_count() > 1:
        return {activity_id: _time_float_for_activity(context, activity_id) for activity_id in activity_ids}
    try:
        fork_context = multiprocessing.get_context("fork")
    except ValueError:
        return {activity_id: _time_float_for_activity(context, activity_id) for activity_id in activity_ids}

    with _FLOAT_FORK_LOCK:
        previous = _FLOAT_CONTEXT
        _FLOAT_CONTEXT = context
        pool = fork_context.Pool(processes=len(chunks))
        try:
            chunks_out = pool.map(_float_chunk, chunks)
        finally:
            pool.close()
            pool.join()
            _FLOAT_CONTEXT = previous

    merged: dict[str, TimeFloatActivity] = {}
    for chunk in chunks_out:
        for item in chunk:
            merged[item.activity_id] = item
    return {activity_id: merged[activity_id] for activity_id in activity_ids}


def calculate_time_floats(
    activities: Iterable[TimeActivity],
    relationships: Iterable[TimeRelationship],
    early: Mapping[str, TimeScheduledActivity],
    late: Mapping[str, TimeScheduledActivity],
    registry: CalendarResolverRegistry,
    relationship_lag_calendar: RelationshipLagCalendar | None = None,
    *,
    workers: int = 1,
) -> Mapping[str, TimeFloatActivity]:
    """Calculate every activity's float.

    ``workers`` is an execution-only parameter: it splits independent activity
    calculations across forked processes and merges them in sorted id order.
    It cannot change a value, and the default (1) is the historical sequential
    loop.
    """
    if isinstance(workers, bool) or not isinstance(workers, int) or workers < 1:
        raise ValueError("INVALID_FLOAT_WORKERS")
    context = _time_float_context(
        activities, relationships, early, late, registry, relationship_lag_calendar
    )
    activity_ids = sorted(context.activity_map)
    if workers == 1:
        return {
            activity_id: _time_float_for_activity(context, activity_id)
            for activity_id in activity_ids
        }
    return _parallel_time_floats(context, activity_ids, workers)


def time_schedule(
    activities: Iterable[TimeActivity],
    relationships: Iterable[TimeRelationship],
    project_start: datetime,
    project_finish: datetime | None,
    registry: CalendarResolverRegistry,
    constraints: Iterable[TimeActivityConstraint] = (),
    options: TimeScheduleOptions | None = None,
    *,
    float_workers: int = 1,
) -> TimeScheduleResult:
    activity_list = list(activities)
    _validate_project_calendar_context(activity_list)
    relationship_list = list(relationships)
    constraint_list = list(constraints)
    selected_options = options or TimeScheduleOptions()
    early = time_forward_pass(
        activity_list,
        relationship_list,
        project_start,
        registry,
        constraint_list,
        selected_options.relationship_lag_calendar,
        selected_options.start_to_start_lag_calculation_type,
        selected_options.data_date,
    )
    project_resolver = _project_resolver(activity_list[0], registry) if activity_list else None
    effective_finish = project_finish or max(item.finish for item in early.values())
    if project_resolver is not None:
        effective_finish = project_resolver.normalize_finish(effective_finish)
    late = time_backward_pass(
        activity_list,
        relationship_list,
        early,
        effective_finish,
        registry,
        constraint_list,
        selected_options.relationship_lag_calendar,
    )
    floats = calculate_time_floats(
        activity_list,
        relationship_list,
        early,
        late,
        registry,
        selected_options.relationship_lag_calendar,
        workers=float_workers,
    )
    return TimeScheduleResult(
        activities=early,
        early_activities=early,
        late_activities=late,
        floats=floats,
        project_finish=effective_finish,
    )
