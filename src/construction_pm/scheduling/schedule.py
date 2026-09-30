from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable, Iterable, Mapping

from .activity import Activity
from .calculation_context import CalculationContext
from .calendar import WorkingTimeResolver
from .activity_calendar_provider import ActivityCalendarProvider
from .constraints import (
    ActivityConstraint,
    apply_latest_constraint,
    validate_constraint_set,
    validate_late_constraint_window,
)
from .forward_pass import ScheduledActivity, _shift_working_date, _successor_start, _topological_order, forward_pass
from .relationships import Relationship, RelationshipType
from .schedule_options import (
    CriticalActivityPathType,
    ScheduleMode,
    ScheduleOptions,
    StartToStartLagCalculationType,
    TotalFloatCalculationType,
)


@dataclass(frozen=True)
class FloatActivity:
    activity_id: str
    early_start: date
    early_finish: date
    late_start: date
    late_finish: date
    total_float: int
    free_float: int
    critical: bool
    float_path: int | None = None
    float_path_order: int | None = None


@dataclass(frozen=True)
class MultipleFloatPath:
    path_number: int
    activity_ids: tuple[str, ...]


@dataclass(frozen=True)
class ScheduleResult:
    activities: Mapping[str, ScheduledActivity]
    floats: Mapping[str, FloatActivity]
    project_finish: date
    early_activities: Mapping[str, ScheduledActivity] | None = None
    late_activities: Mapping[str, ScheduledActivity] | None = None
    mode: ScheduleMode = ScheduleMode.EARLIEST
    float_paths: tuple[MultipleFloatPath, ...] = ()


def _inverse_event_shift(successor_event: date, lag: int, resolver: WorkingTimeResolver) -> date:
    if lag >= 0:
        # Forward FS/FF event semantics normalize a nonworking predecessor
        # finish before applying the strict event offset. The latest
        # predecessor date may therefore be a nonworking Gregorian day
        # immediately before the successor event (e.g. Friday -> Sunday on a
        # Sunday-Thursday successor calendar).
        candidate = successor_event
        for _ in range(lag + 1):
            candidate -= timedelta(days=1)
        while (
            _successor_event_for_inverse(candidate, lag, resolver) == successor_event
        ):
            candidate += __import__("datetime").timedelta(days=1)
        return candidate - __import__("datetime").timedelta(days=1)
    return resolver.next_working_day(
        resolver.add_working_duration(successor_event, -lag)
    )


def _successor_event_for_inverse(
    predecessor_event: date, lag: int, resolver: WorkingTimeResolver
) -> date:
    anchor = resolver.normalize_start(predecessor_event)
    if anchor == resolver.calendar.to_gregorian(predecessor_event):
        anchor = resolver.next_working_day(anchor)
    return resolver.add_working_duration(anchor, lag + 1)


def _inverse_start_shift(successor_start: date, lag: int, resolver: WorkingTimeResolver) -> date:
    if lag >= 0:
        return resolver.subtract_working_duration(successor_start, lag + 1)
    return resolver.add_working_duration(successor_start, -lag + 1)


def _latest_predecessor_start(
    relationship: Relationship,
    successor: ScheduledActivity,
    predecessor_duration: int,
    resolver: WorkingTimeResolver,
    relationship_lag_resolver: WorkingTimeResolver | None = None,
) -> date:
    lag_resolver = relationship_lag_resolver or resolver
    if relationship.type is RelationshipType.FS:
        predecessor_finish = _inverse_event_shift(successor.start, relationship.lag, lag_resolver)
        return resolver.subtract_working_duration(predecessor_finish, predecessor_duration)

    if relationship.type is RelationshipType.SS:
        return _inverse_start_shift(successor.start, relationship.lag, lag_resolver)

    if relationship.type is RelationshipType.FF:
        predecessor_finish = _inverse_event_shift(successor.finish, relationship.lag, lag_resolver)
        return resolver.subtract_working_duration(predecessor_finish, predecessor_duration)

    if relationship.type is RelationshipType.SF:
        return _inverse_event_shift(successor.finish, relationship.lag, lag_resolver)

    raise ValueError(f"unsupported relationship type: {relationship.type}")


def backward_pass(
    activities: Iterable[Activity],
    relationships: Iterable[Relationship],
    forward: Mapping[str, ScheduledActivity],
    project_finish: date | None,
    resolver: WorkingTimeResolver,
    constraints: Iterable[ActivityConstraint] | None = None,
    calendar_provider: ActivityCalendarProvider | None = None,
    relationship_lag_resolver: Callable[[Relationship], WorkingTimeResolver] | None = None,
) -> Mapping[str, ScheduledActivity]:
    """Calculate latest dates using successor late dates."""
    activity_list = list(activities)
    activity_map = {activity.id: activity for activity in activity_list}
    relationship_list = list(relationships)
    constraint_map: dict[str, list[ActivityConstraint]] = {activity_id: [] for activity_id in activity_map}
    all_constraints = list(constraints or ())
    for constraint in all_constraints:
        if constraint.activity_id not in activity_map:
            raise ValueError("constraint references an unknown activity")
        constraint_map[constraint.activity_id].append(constraint)

    if set(activity_map) != set(forward):
        raise ValueError("forward schedule must contain every activity")

    for activity_id, activity_constraints in constraint_map.items():
        validate_constraint_set(
            activity_constraints,
            activity_map[activity_id].duration,
            calendar_provider.resolver_for(activity_id) if calendar_provider is not None else resolver,
        )

    for rel in relationship_list:
        if rel.predecessor_id not in activity_map or rel.successor_id not in activity_map:
            raise ValueError("relationship references an unknown activity")

    early_project_finish = max(item.finish for item in forward.values())
    if project_finish is not None:
        finish = resolver.normalize_finish(project_finish)
    else:
        finish_resolver = (
            calendar_provider.resolver_for(max(forward, key=lambda k: forward[k].finish))
            if calendar_provider is not None
            else resolver
        )
        finish = finish_resolver.normalize_finish(early_project_finish)

    outgoing: dict[str, list[Relationship]] = {activity_id: [] for activity_id in activity_map}
    for rel in relationship_list:
        outgoing[rel.predecessor_id].append(rel)

    order = _topological_order(activity_map, relationship_list)
    result: dict[str, ScheduledActivity] = {}

    for activity_id in reversed(order):
        activity = activity_map[activity_id]
        activity_resolver = calendar_provider.resolver_for(activity_id) if calendar_provider is not None else resolver
        successors = outgoing[activity_id]

        if not successors:
            late_finish = finish
            late_start = activity_resolver.subtract_working_duration(late_finish, activity.duration)
        else:
            late_start = min(
                _latest_predecessor_start(
                    rel, result[rel.successor_id], activity.duration, activity_resolver,
                    relationship_lag_resolver(rel) if relationship_lag_resolver is not None else None,
                )
                for rel in sorted(
                    successors,
                    key=lambda item: (
                        item.successor_id, item.predecessor_id, item.type.value, item.lag
                    ),
                )
            )
            latest_by_project_finish = activity_resolver.subtract_working_duration(
                finish, activity.duration
            )
            late_start = min(late_start, latest_by_project_finish)
            late_finish = activity_resolver.add_working_duration(late_start, activity.duration)

        for constraint in sorted(
            constraint_map[activity_id], key=lambda item: (item.type.value, item.date)
        ):
            late_start = apply_latest_constraint(
                constraint, late_start, activity.duration, activity_resolver
            )
            late_finish = activity_resolver.add_working_duration(late_start, activity.duration)

        if late_finish > finish:
            raise ValueError(f"backward schedule exceeds project finish for {activity_id}")

        for constraint in sorted(
            constraint_map[activity_id], key=lambda item: (item.type.value, item.date)
        ):
            validate_late_constraint_window(constraint, late_start, late_finish, activity_resolver)

        result[activity_id] = ScheduledActivity(
            activity_id=activity_id,
            start=late_start,
            finish=late_finish,
            duration=activity.duration,
        )

    # P6 lower-bound constraints (Start/Finish No Earlier Than) affect
    # early dates only. They reduce float rather than moving the late schedule.
    # Upper-bound and mandatory constraints remain validated below.

    for relationship in relationship_list:
        if not _relationship_holds(
            relationship,
            result[relationship.predecessor_id],
            result[relationship.successor_id],
            calendar_provider.resolver_for(relationship.successor_id) if calendar_provider is not None else resolver,
            relationship_lag_resolver(relationship) if relationship_lag_resolver is not None else None,
        ):
            raise ValueError(
                f"backward schedule violates relationship {relationship.predecessor_id} -> "
                f"{relationship.successor_id} ({relationship.type.value}, lag={relationship.lag})"
            )

    return result


def _working_delay_between(early: date, delayed: date, resolver: WorkingTimeResolver) -> int:
    if delayed < early:
        return -_working_delay_between(delayed, early, resolver)
    return resolver.working_days_between(early, delayed)


def _relationship_holds(
    relationship: Relationship,
    predecessor: ScheduledActivity,
    successor: ScheduledActivity,
    resolver: WorkingTimeResolver,
    relationship_lag_resolver: WorkingTimeResolver | None = None,
) -> bool:
    lag_resolver = relationship_lag_resolver or resolver
    if relationship.type is RelationshipType.FS:
        required = (
            (
                lambda anchor: lag_resolver.add_working_duration(
                    lag_resolver.next_working_day(anchor)
                    if anchor == lag_resolver.calendar.to_gregorian(predecessor.finish)
                    else anchor,
                    relationship.lag + 1,
                )
            )(lag_resolver.normalize_start(predecessor.finish))
            if relationship.lag >= 0
            else lag_resolver.previous_working_day(
                lag_resolver.subtract_working_duration(predecessor.finish, -relationship.lag)
            )
        )
        return successor.start >= required

    if relationship.type is RelationshipType.SS:
        required = _shift_working_date(predecessor.start, relationship.lag, lag_resolver)
        return successor.start >= required

    if relationship.type is RelationshipType.FF:
        required = _shift_working_date(predecessor.finish, relationship.lag, lag_resolver)
        return successor.finish >= required

    if relationship.type is RelationshipType.SF:
        required = _shift_working_date(predecessor.start, relationship.lag, lag_resolver)
        return successor.finish >= required

    raise ValueError(f"unsupported relationship type: {relationship.type}")


def _free_float(
    activity: Activity,
    early: ScheduledActivity,
    successors: list[Relationship],
    early_schedule: Mapping[str, ScheduledActivity],
    resolver: WorkingTimeResolver,
    relationship_lag_resolver=None,
) -> int:
    if not successors:
        return 0

    limits: list[int] = []
    for rel in successors:
        successor = early_schedule[rel.successor_id]
        delay = 0
        while delay < 10000:
            candidate_start = resolver.add_working_duration(early.start, delay)
            candidate = ScheduledActivity(
                activity_id=early.activity_id,
                start=candidate_start,
                finish=resolver.add_working_duration(candidate_start, activity.duration),
                duration=activity.duration,
            )
            if not _relationship_holds(rel, candidate, successor, resolver, relationship_lag_resolver(rel) if relationship_lag_resolver else None):
                break
            delay += 1
        limits.append(delay - 1)
    return max(0, min(limits))



def _relationship_is_driving(
    relationship: Relationship,
    predecessor: ScheduledActivity,
    successor: ScheduledActivity,
    resolver: WorkingTimeResolver,
    relationship_lag_resolver=None,
) -> bool:
    """Return True when the relationship exactly determines the successor event."""
    lag_resolver = relationship_lag_resolver or resolver
    if relationship.type is RelationshipType.FS:
        if relationship.lag >= 0:
            required = lag_resolver.next_working_day(
                lag_resolver.add_working_duration(predecessor.finish, relationship.lag + 1)
            )
        else:
            required = lag_resolver.previous_working_day(
                lag_resolver.subtract_working_duration(predecessor.finish, -relationship.lag)
            )
        return successor.start == required
    if relationship.type is RelationshipType.SS:
        required = _shift_working_date(predecessor.start, relationship.lag, lag_resolver)
        return successor.start == required
    if relationship.type is RelationshipType.FF:
        required = _shift_working_date(predecessor.finish, relationship.lag, lag_resolver)
        return successor.finish == required
    if relationship.type is RelationshipType.SF:
        required = _shift_working_date(predecessor.start, relationship.lag, lag_resolver)
        return successor.finish == required
    raise ValueError(f"unsupported relationship type: {relationship.type}")


def _longest_path_activity_ids(
    activities: Iterable[Activity],
    relationships: Iterable[Relationship],
    early_schedule: Mapping[str, ScheduledActivity],
    resolver: WorkingTimeResolver,
    relationship_lag_resolver=None,
) -> frozenset[str]:
    """Trace P6-style driving relationships from the latest early finishes."""
    activity_list = list(activities)
    activity_map = {activity.id: activity for activity in activity_list}
    incoming: dict[str, list[Relationship]] = {activity_id: [] for activity_id in activity_map}
    for relationship in relationships:
        if relationship.predecessor_id not in activity_map or relationship.successor_id not in activity_map:
            raise ValueError("relationship references an unknown activity")
        incoming[relationship.successor_id].append(relationship)

    latest_early_finish = max(item.finish for item in early_schedule.values())
    longest: set[str] = {
        activity_id
        for activity_id, scheduled in early_schedule.items()
        if scheduled.finish == latest_early_finish
    }

    stack = sorted(longest, reverse=True)
    while stack:
        successor_id = stack.pop()
        successor = early_schedule[successor_id]
        for relationship in sorted(
            incoming[successor_id],
            key=lambda item: (item.predecessor_id, item.successor_id, item.type.value, item.lag),
            reverse=True,
        ):
            predecessor_id = relationship.predecessor_id
            if predecessor_id in longest:
                continue
            predecessor = early_schedule[predecessor_id]
            if _relationship_is_driving(relationship, predecessor, successor, resolver, relationship_lag_resolver(relationship) if relationship_lag_resolver else None):
                longest.add(predecessor_id)
                stack.append(predecessor_id)
    return frozenset(longest)


def _relationship_free_float(
    relationship: Relationship,
    predecessor: ScheduledActivity,
    successor: ScheduledActivity,
    predecessor_activity: Activity,
    resolver: WorkingTimeResolver,
    relationship_lag_resolver: WorkingTimeResolver | None = None,
) -> int:
    delay = 0
    while delay < 10000:
        candidate_start = resolver.add_working_duration(predecessor.start, delay)
        candidate = ScheduledActivity(
            activity_id=predecessor.activity_id,
            start=candidate_start,
            finish=resolver.add_working_duration(candidate_start, predecessor_activity.duration),
            duration=predecessor_activity.duration,
        )
        if not _relationship_holds(relationship, candidate, successor, resolver, relationship_lag_resolver):
            return max(0, delay - 1)
        delay += 1
    return 10000


def _relationship_total_float(
    relationship: Relationship,
    predecessor: ScheduledActivity,
    successor_late: ScheduledActivity,
    predecessor_activity: Activity,
    resolver: WorkingTimeResolver,
    relationship_lag_resolver: WorkingTimeResolver | None = None,
) -> int:
    delay = 0
    while delay < 10000:
        candidate_start = resolver.add_working_duration(predecessor.start, delay)
        candidate = ScheduledActivity(
            activity_id=predecessor.activity_id,
            start=candidate_start,
            finish=resolver.add_working_duration(candidate_start, predecessor_activity.duration),
            duration=predecessor_activity.duration,
        )
        if not _relationship_holds(relationship, candidate, successor_late, resolver, relationship_lag_resolver):
            return max(0, delay - 1)
        delay += 1
    return 10000


def _choose_default_float_path_endpoint(
    activity_map: Mapping[str, Activity],
    relationships: Iterable[Relationship],
    early_schedule: Mapping[str, ScheduledActivity],
    late_schedule: Mapping[str, ScheduledActivity],
    resolver: WorkingTimeResolver,
    use_total_float: bool,
    calendar_provider: ActivityCalendarProvider | None = None,
    relationship_lag_resolver=None,
) -> str | None:
    incoming: dict[str, list[Relationship]] = {activity_id: [] for activity_id in activity_map}
    outgoing: dict[str, list[Relationship]] = {activity_id: [] for activity_id in activity_map}
    for relationship in relationships:
        incoming[relationship.successor_id].append(relationship)
        outgoing[relationship.predecessor_id].append(relationship)

    candidates: list[tuple[tuple[int, int, int, str], str]] = []
    for activity_id in sorted(activity_map):
        incoming_rels = incoming[activity_id]
        if use_total_float:
            if not incoming_rels:
                continue
            metric = min(
                _relationship_total_float(
                    relationship,
                    early_schedule[relationship.predecessor_id],
                    late_schedule[activity_id],
                    activity_map[relationship.predecessor_id],
                    calendar_provider.resolver_for(relationship.predecessor_id) if calendar_provider is not None else resolver,
                    relationship_lag_resolver(relationship) if relationship_lag_resolver is not None else None,
                )
                for relationship in incoming_rels
            )
        else:
            if outgoing[activity_id]:
                continue
            metric = min(
                (
                    _relationship_free_float(
                        relationship,
                        early_schedule[relationship.predecessor_id],
                        early_schedule[activity_id],
                        activity_map[relationship.predecessor_id],
                        calendar_provider.resolver_for(relationship.predecessor_id) if calendar_provider is not None else resolver,
                        relationship_lag_resolver(relationship) if relationship_lag_resolver is not None else None,
                    )
                    for relationship in incoming_rels
                ),
                default=0,
            )

        candidates.append(
            (
                (
                    metric,
                    -early_schedule[activity_id].finish.toordinal(),
                    early_schedule[activity_id].start.toordinal(),
                    activity_id,
                ),
                activity_id,
            )
        )
    return min(candidates)[1] if candidates else None

def _multiple_float_paths(
    activities: Iterable[Activity],
    relationships: Iterable[Relationship],
    early_schedule: Mapping[str, ScheduledActivity],
    late_schedule: Mapping[str, ScheduledActivity],
    resolver: WorkingTimeResolver,
    options: ScheduleOptions,
    calendar_provider: ActivityCalendarProvider | None = None,
    relationship_lag_resolver=None,
) -> tuple[MultipleFloatPath, ...]:
    if not options.multiple_float_paths_enabled or options.maximum_multiple_float_paths == 0:
        return ()

    activity_map = {activity.id: activity for activity in activities}
    relationship_list = list(relationships)
    if not activity_map:
        return ()

    incoming: dict[str, list[Relationship]] = {activity_id: [] for activity_id in activity_map}
    for relationship in relationship_list:
        if relationship.predecessor_id not in activity_map or relationship.successor_id not in activity_map:
            raise ValueError("relationship references an unknown activity")
        incoming[relationship.successor_id].append(relationship)

    remaining = set(activity_map)
    paths: list[MultipleFloatPath] = []
    explicit_endpoint = options.multiple_float_paths_ending_activity_object_id
    if explicit_endpoint is not None and explicit_endpoint not in activity_map:
        raise ValueError("multiple float paths ending activity does not exist")

    for path_number in range(1, options.maximum_multiple_float_paths + 1):
        if not remaining:
            break

        if path_number == 1 and explicit_endpoint is not None:
            endpoint = explicit_endpoint
        else:
            scoped = {activity_id: activity_map[activity_id] for activity_id in remaining}
            scoped_relationships = [
                relationship
                for relationship in relationship_list
                if relationship.predecessor_id in remaining
                and relationship.successor_id in remaining
            ]
            endpoint = _choose_default_float_path_endpoint(
                scoped,
                scoped_relationships,
                early_schedule,
                late_schedule,
                resolver,
                options.multiple_float_paths_use_total_float,
                calendar_provider=calendar_provider,
                relationship_lag_resolver=relationship_lag_resolver,
            ) or min(remaining)

        if endpoint not in remaining:
            candidates = sorted(
                relationship.predecessor_id
                for relationship in incoming[endpoint]
                if relationship.predecessor_id in remaining
            )
            if not candidates:
                break
            endpoint = candidates[0]

        path_rev: list[str] = [endpoint]
        remaining.remove(endpoint)
        current = endpoint

        while True:
            candidates = [
                relationship
                for relationship in incoming[current]
                if relationship.predecessor_id in remaining
            ]
            if not candidates:
                break

            successor = early_schedule[current]
            scored: list[tuple[tuple[int, int, int, int, int, str], Relationship]] = []
            for relationship in candidates:
                predecessor_id = relationship.predecessor_id
                predecessor = early_schedule[predecessor_id]
                if options.multiple_float_paths_use_total_float:
                    metric = _relationship_total_float(
                        relationship, predecessor, late_schedule[current],
                        activity_map[predecessor_id],
                        calendar_provider.resolver_for(predecessor_id) if calendar_provider is not None else resolver,
                        relationship_lag_resolver(relationship) if relationship_lag_resolver is not None else None,
                    )
                    driving_penalty = 0
                else:
                    metric = _relationship_free_float(
                        relationship, predecessor, successor,
                        activity_map[predecessor_id],
                        calendar_provider.resolver_for(predecessor_id) if calendar_provider is not None else resolver,
                        relationship_lag_resolver(relationship) if relationship_lag_resolver is not None else None,
                    )
                    driving_penalty = 0 if _relationship_is_driving(
                        relationship, predecessor, successor,
                        calendar_provider.resolver_for(predecessor_id) if calendar_provider is not None else resolver,
                        relationship_lag_resolver(relationship) if relationship_lag_resolver is not None else None,
                    ) else 1
                activity_float = _working_delay_between(
                    early_schedule[predecessor_id].start,
                    late_schedule[predecessor_id].start,
                    calendar_provider.resolver_for(predecessor_id) if calendar_provider is not None else resolver,
                )
                scored.append((
                    (
                        metric, driving_penalty, activity_float,
                        -predecessor.finish.toordinal(),
                        predecessor.start.toordinal(),
                        predecessor_id,
                    ),
                    relationship,
                ))

            _, chosen = min(scored)
            predecessor_id = chosen.predecessor_id
            path_rev.append(predecessor_id)
            remaining.remove(predecessor_id)
            current = predecessor_id

        paths.append(
            MultipleFloatPath(path_number=path_number, activity_ids=tuple(reversed(path_rev)))
        )

    return tuple(paths)


def calculate_floats(
    activities: Iterable[Activity],
    relationships: Iterable[Relationship],
    early_schedule: Mapping[str, ScheduledActivity],
    late_schedule: Mapping[str, ScheduledActivity],
    resolver: WorkingTimeResolver,
    options: ScheduleOptions | None = None,
    calendar_provider: ActivityCalendarProvider | None = None,
    relationship_lag_resolver=None,
) -> Mapping[str, FloatActivity]:
    """Calculate relationship-aware Total Float and Free Float."""
    selected_options = options or ScheduleOptions()
    longest_path_ids = (
        _longest_path_activity_ids(activities, relationships, early_schedule, resolver, relationship_lag_resolver)
        if selected_options.critical_activity_path_type is CriticalActivityPathType.LONGEST_PATH
        else frozenset()
    )

    activity_map = {activity.id: activity for activity in activities}
    outgoing: dict[str, list[Relationship]] = {activity_id: [] for activity_id in activity_map}
    for rel in relationships:
        outgoing[rel.predecessor_id].append(rel)

    result: dict[str, FloatActivity] = {}
    for activity_id in sorted(activity_map):
        early = early_schedule[activity_id]
        late = late_schedule[activity_id]
        activity_resolver = calendar_provider.resolver_for(activity_id) if calendar_provider is not None else resolver
        start_float = _working_delay_between(early.start, late.start, activity_resolver)
        finish_float = _working_delay_between(early.finish, late.finish, activity_resolver)
        # P6 can calculate total float from Start Float, Finish Float, or the
        # smaller of the two. Negative float remains a valid reportable value.
        if selected_options.compute_total_float_type is TotalFloatCalculationType.FINISH_FLOAT:
            total = finish_float
        elif selected_options.compute_total_float_type is TotalFloatCalculationType.SMALLER_FLOAT:
            total = min(start_float, finish_float)
        else:
            total = start_float
        free = _free_float(
            activity_map[activity_id], early, outgoing[activity_id], early_schedule, activity_resolver, relationship_lag_resolver
        )
        free = max(0, min(total, free))
        if selected_options.critical_activity_path_type is CriticalActivityPathType.LONGEST_PATH:
            critical = activity_id in longest_path_ids
        else:
            critical = (
                total <= selected_options.critical_activity_float_threshold
                or (
                    selected_options.make_open_ended_activities_critical
                    and not outgoing[activity_id]
                )
            )

        result[activity_id] = FloatActivity(
            activity_id=activity_id,
            early_start=early.start,
            early_finish=early.finish,
            late_start=late.start,
            late_finish=late.finish,
            total_float=total,
            free_float=free,
            critical=critical,
        )
    return result


def schedule(
    activities: Iterable[Activity],
    relationships: Iterable[Relationship],
    project_start: date,
    resolver: WorkingTimeResolver,
    project_finish: date | None = None,
    constraints: Iterable[ActivityConstraint] | None = None,
    options: ScheduleOptions | None = None,
    calculation_context: CalculationContext | None = None,
    calendar_provider: ActivityCalendarProvider | None = None,
    relationship_lag_resolver=None,
) -> ScheduleResult:
    """Run CPM passes and select either earliest or ALAP output."""
    selected_options = options or ScheduleOptions()
    if calculation_context is not None and calculation_context.project_version < 0:
        raise ValueError("invalid calculation context")
    activity_list = list(activities)
    relationship_list = list(relationships)
    constraint_list = list(constraints or ())
    early = forward_pass(
        activity_list,
        relationship_list,
        project_start,
        resolver,
        constraint_list,
        calculation_context,
        selected_options.start_to_start_lag_calculation_type,
        selected_options.data_date,
        calendar_provider=calendar_provider,
        relationship_lag_resolver=relationship_lag_resolver,
    )
    late = backward_pass(
        activity_list, relationship_list, early, project_finish, resolver, constraint_list,
        calendar_provider=calendar_provider,
        relationship_lag_resolver=relationship_lag_resolver,
    )
    floats = calculate_floats(
        activity_list,
        relationship_list,
        early,
        late,
        resolver,
        selected_options,
        calendar_provider=calendar_provider,
        relationship_lag_resolver=relationship_lag_resolver,
    )

    float_paths = _multiple_float_paths(
        activity_list, relationship_list, early, late, resolver, selected_options,
        calendar_provider=calendar_provider,
        relationship_lag_resolver=relationship_lag_resolver,
    )
    path_by_activity: dict[str, tuple[int, int]] = {}
    for path in float_paths:
        for order, activity_id in enumerate(path.activity_ids, start=1):
            path_by_activity.setdefault(activity_id, (path.path_number, order))

    if path_by_activity:
        floats = {
            activity_id: FloatActivity(
                activity_id=value.activity_id,
                early_start=value.early_start,
                early_finish=value.early_finish,
                late_start=value.late_start,
                late_finish=value.late_finish,
                total_float=value.total_float,
                free_float=value.free_float,
                critical=value.critical,
                float_path=path_by_activity.get(activity_id, (None, None))[0],
                float_path_order=path_by_activity.get(activity_id, (None, None))[1],
            )
            for activity_id, value in floats.items()
        }

    if project_finish is not None:
        effective_finish = resolver.normalize_finish(project_finish)
    else:
        finish_resolver = resolver
        if calendar_provider is not None:
            finish_activity_id = max(early, key=lambda activity_id: early[activity_id].finish)
            finish_resolver = calendar_provider.resolver_for(finish_activity_id)
        effective_finish = finish_resolver.normalize_finish(
            max(item.finish for item in early.values())
        )
    selected = late if selected_options.mode is ScheduleMode.ALAP else early

    return ScheduleResult(
        activities=selected,
        floats=floats,
        project_finish=effective_finish,
        early_activities=early,
        late_activities=late,
        mode=selected_options.mode,
        float_paths=float_paths,
    )
