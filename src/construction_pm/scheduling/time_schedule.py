from __future__ import annotations

import multiprocessing
import pickle
import threading
from contextlib import AbstractContextManager, ExitStack, contextmanager, nullcontext
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Callable, Iterable, Mapping

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
    *,
    on_late: Callable[[str, TimeScheduledActivity], None] | None = None,
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
        scheduled_late = TimeScheduledActivity(activity_id, late_start, late_finish, activity.duration)
        late[activity_id] = scheduled_late
        # A late record is final once stored: the remaining iterations only
        # touch earlier activities. The hook is how the float pipeline consumes
        # it concurrently; it cannot change ``late`` and defaults to no hook.
        if on_late is not None:
            on_late(activity_id, scheduled_late)

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


def _float_limit_interval_bound(
    relationship: TimeRelationship,
    *,
    activity: TimeActivity,
    base_start: datetime,
    base_finish: datetime,
    successor: TimeScheduledActivity,
    resolver: CalendarAwareResolver,
    lag_resolver: CalendarAwareResolver,
) -> Decimal | None:
    """Exact Free Float delay bound from working-time interval arithmetic.

    Delaying the predecessor and lengthening it by the activity duration are
    both working-time translations, so the delayed event is
    ``add(base, delay)`` and ``required = add(event, lag)``.  The relationship
    holds exactly when ``delay + lag <= working_hours(base, target)``, which
    makes the largest delay a single interval measurement instead of a search.

    Returns ``None`` when the identity is not provable from these inputs:
    day-unit arithmetic, a lag measured in a different calendar, or a lag
    resolver wrapping a different underlying calendar.  The caller then keeps
    the monotone probe search unchanged.
    """
    if activity.duration.unit is not DurationUnit.WORKING_HOUR:
        return None
    if relationship.lag.unit is not DurationUnit.WORKING_HOUR:
        return None
    if resolver.is_working_day_calendar or lag_resolver.is_working_day_calendar:
        return None
    if lag_resolver.resolver is not resolver.resolver:
        return None

    if relationship.type is RelationshipType.FS:
        base, target = base_finish, successor.start
    elif relationship.type is RelationshipType.SS:
        base, target = base_start, successor.start
    elif relationship.type is RelationshipType.FF:
        base, target = base_finish, successor.finish
    elif relationship.type is RelationshipType.SF:
        base, target = base_start, successor.finish
    else:
        return None

    if target < base:
        return Decimal("-1")
    return (
        resolver.calculate_duration(base, target, DurationUnit.WORKING_HOUR)
        - relationship.lag.value
    )


def _verified_float_limit(holds_at, bound: Decimal | None) -> Decimal:
    """Turn an interval bound into the last holding integer delay.

    The bound is exact mathematics on measured intervals; the two boundary
    probes make the published value independent of Decimal rounding at the
    boundary.  Without a provable bound the historical monotone search runs
    unchanged.
    """
    if bound is None:
        return _free_float_limit(holds_at)

    ceiling = _FREE_FLOAT_SEARCH_CEILING - Decimal("1")
    candidate = Decimal(int(bound)) if bound > 0 else Decimal("0")
    if candidate > ceiling:
        candidate = ceiling
    if not holds_at(candidate):
        candidate -= 1
    if candidate < ceiling and holds_at(candidate + 1):
        candidate += 1
    return max(Decimal("0"), candidate)


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
    context: _TimeFloatContext,
    activity_id: str,
    late_item: TimeScheduledActivity | None = None,
) -> TimeFloatActivity:
    """Calculate one activity's float from immutable inputs only.

    The function reads no global state and mutates nothing, so evaluating it in
    a child process yields exactly the value the sequential loop would produce.

    ``late_item`` supplies this activity's own late dates when the complete
    ``late`` mapping is not available yet. The calculation below reads
    ``late[activity_id]`` and no other late entry (the free-float probe uses
    early dates only), so passing the single record is exactly equivalent to
    reading it from the mapping. The pipeline that overlaps the backward pass
    uses this to avoid shipping a whole late map that is still being built.
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
    l = late[activity_id] if late_item is None else late_item
    # P6 reports negative Total Float when the late dates precede the early
    # dates.  Compute the magnitude from the earlier/later pair instead of
    # asking the calendar for a reversed interval.
    if activity.duration.unit is DurationUnit.WORKING_DAY:
        if l.start >= e.start:
            total = Decimal(
                resolver.resolver.working_days_between(e.start.date(), l.start.date())
            )
        else:
            total = -Decimal(
                resolver.resolver.working_days_between(l.start.date(), e.start.date())
            )
    else:
        if l.start >= e.start:
            total = resolver.calculate_duration(e.start, l.start, activity.duration.unit)
        else:
            total = -resolver.calculate_duration(l.start, e.start, activity.duration.unit)

    if not outgoing[activity_id]:
        free = Decimal("0")
    else:
        limits: list[Decimal] = []
        # Delay 0 is a no-op on the early dates, so the candidate finish used by
        # the interval bound is the activity's own early finish.
        zero_finish = _add_duration(e.start, activity.duration, resolver)
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

                bound = _float_limit_interval_bound(
                    rel,
                    activity=activity,
                    base_start=e.start,
                    base_finish=zero_finish,
                    successor=successor,
                    resolver=resolver,
                    lag_resolver=lag_resolver,
                )
                limits.append(_verified_float_limit(holds_at, bound))
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


# Forked or spawned children inherit this context at pool creation. Nothing else
# is shared: each child computes independent activities and returns immutable
# records, so the merged mapping is exactly the sequential mapping.
_FLOAT_CONTEXT: _TimeFloatContext | None = None
# One float pool per process at a time. Nested pools would oversubscribe the CPU
# budget and, under ``spawn``, fork bombs.
_FLOAT_POOL_GUARD = threading.Lock()


def _float_pool_initializer(context: _TimeFloatContext) -> None:
    global _FLOAT_CONTEXT
    _FLOAT_CONTEXT = context


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


def _fork_is_safe(*, allow_nested: bool = False) -> bool:
    """True when forking a child cannot inherit another thread's held lock.

    The safety condition is that *this* process has one thread: a child then
    inherits no lock held by a thread that does not exist in the child. Being
    the direct child of another process is not by itself unsafe, but it is
    refused unless the caller explicitly opts in, because naively nesting pools
    multiplies the process count beyond any budget. A dedicated job runner
    (P0-N) opts in only after its parent has reserved the exact slot count it
    may use, so the nested float children stay inside the global budget.
    """
    if multiprocessing.current_process().daemon:
        return False
    if multiprocessing.parent_process() is not None and not allow_nested:
        return False
    if threading.active_count() != 1:
        return False
    return "fork" in set(multiprocessing.get_all_start_methods())


def _spawn_is_safe(context: _TimeFloatContext, *, allow_spawn: bool) -> bool:
    """True when an allowed ``spawn`` child can receive the float context."""
    if not allow_spawn or "spawn" not in set(multiprocessing.get_all_start_methods()):
        return False
    if multiprocessing.current_process().daemon:
        return False
    try:
        pickle.dumps(context)
    except Exception:  # noqa: BLE001 - any pickling failure means "not safe"
        return False
    return True


def _select_float_start_method(
    context: _TimeFloatContext,
    *,
    allow_spawn: bool = False,
    allow_nested: bool = False,
) -> str | None:
    """Return a *safe* process start method for the current process state.

    ``fork`` is only safe while the process has a single thread: a forked child
    of a threaded process can inherit a held lock and deadlock, and the job
    executor always runs calculations on a worker thread.

    In a threaded process ``spawn`` is the only safe alternative, and it is
    only considered when the caller explicitly allows it: on the measured
    reference host the serial cost of transferring the float context to each
    child (~25 us per activity, 11.6 MB at 25k activities) exceeds the
    parallel work (~169 us per activity divided by the slot count), so an
    automatic spawn pool would be slower than the exact sequential loop. A
    platform without ``fork`` (Windows, macOS default) can opt in with
    ``FloatExecutionPolicy(allow_spawn=True)`` when its own transfer cost is
    lower. Anything else — a daemonic child, no usable start method, an
    unpicklable calendar registry — returns ``None`` and the caller uses the
    exact sequential loop.
    """
    if _fork_is_safe(allow_nested=allow_nested):
        return "fork"
    if _spawn_is_safe(context, allow_spawn=allow_spawn):
        return "spawn"
    return None


def _parallel_time_floats(
    context: _TimeFloatContext,
    activity_ids: list[str],
    workers: int,
    admission: Callable[[int], AbstractContextManager[int]] | None = None,
    *,
    allow_spawn: bool = False,
    allow_nested: bool = False,
) -> dict[str, TimeFloatActivity]:
    """Evaluate independent activities in child processes, then merge by id.

    The merge is keyed by activity id and returned in the canonical sorted id
    order, so the result is byte-identical to the sequential loop for any
    worker count. The pool is only used when it is provably safe:

    * never ``fork`` a process that has more than one thread (the job executor
      runs calculations on worker threads); ``spawn`` is only used there when
      the caller explicitly allows it, because its serial context transfer was
      measured to exceed the parallel work;
    * never create a second float pool from inside a float pool;
    * never exceed the granted CPU budget — ``admission`` reserves extra slots
      from the process-wide budget and the pass stays sequential when fewer
      than two slots are granted.

    Every unsuitable state falls back to the exact sequential loop, which
    changes only speed.
    """

    def sequential() -> dict[str, TimeFloatActivity]:
        return {
            activity_id: _time_float_for_activity(context, activity_id)
            for activity_id in activity_ids
        }

    if workers <= 1 or len(activity_ids) <= 1:
        return sequential()
    start_method = _select_float_start_method(
        context, allow_spawn=allow_spawn, allow_nested=allow_nested
    )
    if start_method is None:
        return sequential()
    if not _FLOAT_POOL_GUARD.acquire(blocking=False):
        return sequential()
    try:
        requested = min(workers, len(activity_ids))
        manager = admission(requested) if admission is not None else nullcontext(requested)
        with manager as granted:
            granted = min(requested, int(granted))
            if granted <= 1:
                return sequential()
            chunks = _chunk_activity_ids(activity_ids, granted)
            if len(chunks) <= 1:
                return sequential()
            pool_context = multiprocessing.get_context(start_method)
            try:
                pool = pool_context.Pool(
                    processes=len(chunks),
                    initializer=_float_pool_initializer,
                    initargs=(context,),
                )
            except (OSError, RuntimeError):
                # Process creation is unavailable in this environment.
                return sequential()
            try:
                chunks_out = pool.map(_float_chunk, chunks)
            finally:
                pool.close()
                pool.join()
    finally:
        _FLOAT_POOL_GUARD.release()

    merged: dict[str, TimeFloatActivity] = {}
    for chunk in chunks_out:
        for item in chunk:
            merged[item.activity_id] = item
    return {activity_id: merged[activity_id] for activity_id in activity_ids}


# ---------------------------------------------------------------------------
# P0-M: overlap the backward pass with the per-activity float calculation
# ---------------------------------------------------------------------------
#
# The float of one activity needs its own late dates and the early dates of the
# whole network (Free Float probes successor *early* dates only). The backward
# pass produces one activity's late dates at a time, in reverse topological
# order, and an activity's late dates are final as soon as they are stored.
# A float for activity A therefore depends on A's own backward result and on
# nothing the backward pass does afterwards, so the two passes can run
# concurrently: the parent runs the unchanged backward loop and hands each
# finished activity's late record to child processes that run the unchanged
# `_time_float_for_activity`.
#
# On a deep, narrow network (the benchmark DAG is a chain, depth == size,
# width == 1) the backward pass itself cannot be split: every activity's late
# dates depend on its successor's. The only intra-project parallelism available
# there is exactly this producer/consumer split, and it removes the float phase
# from the critical path instead of shrinking either phase.

_PIPELINE_CONTEXT: _TimeFloatContext | None = None
# One task carries one (id, late) pair per activity, so a batch is a few
# kilobytes and the parent spends microseconds per dispatch while it runs the
# backward loop. The size is calibrated on the reference host: a smaller batch
# costs more IPC per activity, a larger one lengthens the drain tail by one
# batch of float work. Targeting ~32 batches keeps the tail near 3 % of the
# pass at every size measured in the P0-M evidence.
_PIPELINE_TARGET_BATCHES = 32
_PIPELINE_MIN_BATCH = 16
_PIPELINE_MAX_BATCH = 1024
# Below this size the pool start-up cost can exceed the float work hidden
# behind the backward pass (measured: 100 activities are slower pipelined).
# Execution only; a value never depends on it.
_PIPELINE_MIN_ACTIVITIES = 256


def _pipeline_batch_size(activity_count: int) -> int:
    return max(_PIPELINE_MIN_BATCH, min(_PIPELINE_MAX_BATCH, activity_count // _PIPELINE_TARGET_BATCHES))


def _pipeline_initializer(context: _TimeFloatContext) -> None:
    global _PIPELINE_CONTEXT
    _PIPELINE_CONTEXT = context


def _pipeline_chunk(
    items: list[tuple[str, TimeScheduledActivity]],
) -> list[TimeFloatActivity]:
    context = _PIPELINE_CONTEXT
    if context is None:
        raise RuntimeError("FLOAT_PIPELINE_CONTEXT_NOT_INITIALIZED")
    return [
        _time_float_for_activity(context, activity_id, late_item)
        for activity_id, late_item in items
    ]


class _FloatPipeline:
    """Batched dispatch of float work to children while the parent walks back.

    ``submit`` must be called once per activity, with the late record the
    backward pass just stored. ``finish`` waits for every dispatched batch and
    returns the floats in canonical id order, which is what the sequential
    pass returns.
    """

    def __init__(
        self,
        pool: object,
        batch_size: int,
    ) -> None:
        self._pool = pool
        self._batch_size = batch_size
        self._buffer: list[tuple[str, TimeScheduledActivity]] = []
        self._pending: list[object] = []
        self.dispatched_activities = 0
        self.dispatched_batches = 0

    def submit(self, activity_id: str, late_item: TimeScheduledActivity) -> None:
        self._buffer.append((activity_id, late_item))
        if len(self._buffer) >= self._batch_size:
            self._dispatch()

    def _dispatch(self) -> None:
        batch = self._buffer
        self._buffer = []
        self._pending.append(self._pool.apply_async(_pipeline_chunk, (batch,)))
        self.dispatched_activities += len(batch)
        self.dispatched_batches += 1

    def finish(self) -> dict[str, TimeFloatActivity]:
        if self._buffer:
            self._dispatch()
        merged: dict[str, TimeFloatActivity] = {}
        for handle in self._pending:
            for item in handle.get():
                merged[item.activity_id] = item
        self._pending = []
        return {activity_id: merged[activity_id] for activity_id in sorted(merged)}


@contextmanager
def _float_pipeline(
    context_factory: Callable[[], _TimeFloatContext],
    *,
    activity_count: int,
    workers: int,
    admission: Callable[[int], AbstractContextManager[int]] | None,
    allow_spawn: bool = False,
    allow_nested: bool = False,
    batch_size: int | None = None,
):
    """Yield a float pipeline, or ``None`` when the exact sequential path must run.

    The pipeline is used only when every condition that makes child processes
    safe and worthwhile holds: more than one granted slot, a forkable
    single-threaded parent (or an explicitly allowed spawn), no pool already
    active in this process, and enough activities for the pool start-up to be
    hidden. Any other state yields ``None`` and the caller keeps the historical
    behaviour, so execution never changes a value.

    ``context_factory`` builds the immutable float inputs. It is called only
    when a safe start method exists and a child will actually be created, so a
    fallback never pays for building an unused context.
    """

    if batch_size is None:
        batch_size = _pipeline_batch_size(activity_count)
    if workers <= 1 or activity_count < _PIPELINE_MIN_ACTIVITIES:
        yield None
        return
    if _fork_is_safe(allow_nested=allow_nested):
        start_method = "fork"
    elif _spawn_is_safe(context_factory(), allow_spawn=allow_spawn):
        start_method = "spawn"
    else:
        yield None
        return
    if not _FLOAT_POOL_GUARD.acquire(blocking=False):
        yield None
        return
    stack = ExitStack()
    try:
        requested = workers
        grant = admission(requested) if admission is not None else nullcontext(requested)
        granted = min(requested, int(stack.enter_context(grant)))
        # The parent keeps running the backward pass, so it occupies one of the
        # granted slots and the pool gets the rest.
        children = granted - 1
        pool = None
        if children >= 1:
            pool_context = multiprocessing.get_context(start_method)
            try:
                pool = pool_context.Pool(
                    processes=children,
                    initializer=_pipeline_initializer,
                    initargs=(context_factory(),),
                )
            except (OSError, RuntimeError):
                pool = None
        if pool is None:
            yield None
            return
        stack.callback(pool.join)
        stack.callback(pool.close)
        yield _FloatPipeline(pool, batch_size)
    finally:
        stack.close()
        _FLOAT_POOL_GUARD.release()


@dataclass(frozen=True)
class FloatExecutionPolicy:
    """Execution-only settings for the per-activity float pass.

    ``workers`` is an upper bound; ``admission`` lets the caller cap it against
    the one process-wide execution budget. The admission callable returns a
    context manager whose value is the number of slots actually granted. A
    policy never changes a float value: two granted slots and one slot produce
    the same merged mapping.

    ``allow_spawn`` opts a threaded process into a ``spawn`` pool. It defaults
    to ``False`` because transferring the immutable float context to each child
    is serial work that, on the reference host, is larger than the parallel
    gain; the pass then runs the exact sequential loop. Processes that cannot
    ``fork`` at all can enable it when their own transfer cost is lower.

    ``allow_nested_fork`` opts a dedicated, non-daemonic, single-threaded job
    runner into forking float children even though it is itself a child process.
    The global scheduler (P0-N) sets it only after reserving this job's exact
    slot count, and the nested pool is bounded by ``workers``; a process without
    that reservation keeps the default and declines.
    """

    workers: int = 1
    admission: Callable[[int], AbstractContextManager[int]] | None = None
    allow_spawn: bool = False
    allow_nested_fork: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.workers, bool) or not isinstance(self.workers, int) or self.workers < 1:
            raise ValueError("INVALID_FLOAT_WORKERS")
        if self.admission is not None and not callable(self.admission):
            raise ValueError("INVALID_FLOAT_ADMISSION")
        if not isinstance(self.allow_spawn, bool):
            raise ValueError("INVALID_FLOAT_ALLOW_SPAWN")
        if not isinstance(self.allow_nested_fork, bool):
            raise ValueError("INVALID_FLOAT_ALLOW_NESTED_FORK")


def calculate_time_floats(
    activities: Iterable[TimeActivity],
    relationships: Iterable[TimeRelationship],
    early: Mapping[str, TimeScheduledActivity],
    late: Mapping[str, TimeScheduledActivity],
    registry: CalendarResolverRegistry,
    relationship_lag_calendar: RelationshipLagCalendar | None = None,
    *,
    workers: int = 1,
    policy: FloatExecutionPolicy | None = None,
) -> Mapping[str, TimeFloatActivity]:
    """Calculate every activity's float.

    Execution is the only thing ``workers``/``policy`` can change. Independent
    activities are evaluated in child processes when the process state allows it
    and merged in sorted id order; every other state uses the historical
    sequential loop. Neither parameter can change a value.
    """
    if isinstance(workers, bool) or not isinstance(workers, int) or workers < 1:
        raise ValueError("INVALID_FLOAT_WORKERS")
    selected_policy = policy if policy is not None else FloatExecutionPolicy(workers=workers)
    context = _time_float_context(
        activities, relationships, early, late, registry, relationship_lag_calendar
    )
    activity_ids = sorted(context.activity_map)
    if selected_policy.workers == 1:
        return {
            activity_id: _time_float_for_activity(context, activity_id)
            for activity_id in activity_ids
        }
    return _parallel_time_floats(
        context,
        activity_ids,
        selected_policy.workers,
        selected_policy.admission,
        allow_spawn=selected_policy.allow_spawn,
        allow_nested=selected_policy.allow_nested_fork,
    )


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
    float_policy: FloatExecutionPolicy | None = None,
) -> TimeScheduleResult:
    activity_list = list(activities)
    _validate_project_calendar_context(activity_list)
    relationship_list = list(relationships)
    constraint_list = list(constraints)
    # ``calculate_time_floats`` rejects this today; the pipeline path does not
    # call it, so validate here too and keep the contract identical on every
    # execution path.
    if isinstance(float_workers, bool) or not isinstance(float_workers, int) or float_workers < 1:
        raise ValueError("INVALID_FLOAT_WORKERS")
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

    selected_policy = (
        float_policy
        if float_policy is not None
        else FloatExecutionPolicy(workers=float_workers)
    )
    if selected_policy.workers > 1 and activity_list:
        # Float work depends only on its own late record and on early dates
        # that are already final, so it runs while the backward pass walks.
        # The pipeline is created before the pass so its children inherit the
        # immutable inputs by fork; ``None`` means the historical path.
        with _float_pipeline(
            lambda: _time_float_context(
                activity_list,
                relationship_list,
                early,
                {},
                registry,
                selected_options.relationship_lag_calendar,
            ),
            activity_count=len(activity_list),
            workers=selected_policy.workers,
            admission=selected_policy.admission,
            allow_spawn=selected_policy.allow_spawn,
            allow_nested=selected_policy.allow_nested_fork,
        ) as pipeline:
            if pipeline is None:
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
                    policy=float_policy,
                )
            else:
                late = time_backward_pass(
                    activity_list,
                    relationship_list,
                    early,
                    effective_finish,
                    registry,
                    constraint_list,
                    selected_options.relationship_lag_calendar,
                    on_late=pipeline.submit,
                )
                floats = pipeline.finish()
    else:
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
            policy=float_policy,
        )
    return TimeScheduleResult(
        activities=early,
        early_activities=early,
        late_activities=late,
        floats=floats,
        project_finish=effective_finish,
    )
