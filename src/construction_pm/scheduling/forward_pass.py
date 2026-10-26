from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Mapping, Sequence

from .activity import Activity
from .calculation_context import CalculationContext
from .calendar import WorkingTimeResolver
from .constraints import (
    ActivityConstraint,
    apply_earliest_constraint,
    validate_constraint_set,
    validate_upper_bound,
)
from .out_of_sequence import resolve_out_of_sequence_action
from .progress_state import ActivityProgressState, resolve_progress_state
from .relationships import Relationship, RelationshipType
from .schedule_options import OutOfSequenceScheduleType, StartToStartLagCalculationType


class SchedulingCycleError(ValueError):
    """Raised when the activity network contains a directed cycle."""


@dataclass(frozen=True)
class ScheduledActivity:
    activity_id: str
    start: date
    finish: date
    duration: int


def _shift_working_date(
    value: date, lag: int, resolver: WorkingTimeResolver
) -> date:
    if lag == 0:
        return resolver.normalize_start(value)
    if lag > 0:
        return resolver.add_working_duration(value, lag + 1)
    return resolver.subtract_working_duration(value, -lag + 1)


def _apply_lag_after(
    value: date, lag: int, resolver: WorkingTimeResolver
) -> date:
    """Place a successor event after/before an anchor using working-day lag."""
    if lag >= 0:
        return resolver.next_working_day(
            resolver.add_working_duration(value, lag + 1)
        )
    return resolver.previous_working_day(
        resolver.subtract_working_duration(value, -lag)
    )


def _successor_start(
    relationship: Relationship,
    predecessor: ScheduledActivity,
    successor_duration: int,
    resolver: WorkingTimeResolver,
    predecessor_activity: Activity | None = None,
    start_to_start_lag_calculation_type: StartToStartLagCalculationType = StartToStartLagCalculationType.EARLY_START,
    data_date: date | None = None,
    lag_resolver: WorkingTimeResolver | None = None,
    predecessor_resolver: WorkingTimeResolver | None = None,
    successor_resolver: WorkingTimeResolver | None = None,
) -> date:
    lag_resolver = lag_resolver or resolver
    if relationship.type is RelationshipType.SS:
        if predecessor_activity is not None and predecessor_activity.actual_start is not None:
            actual_start = predecessor_activity.actual_start
            if data_date is None:
                if actual_start > predecessor.start:
                    raise ValueError(
                        "data_date is required for an out-of-sequence start-to-start relationship"
                    )
                anchor = (
                    actual_start
                    if start_to_start_lag_calculation_type
                    is StartToStartLagCalculationType.ACTUAL_START
                    else predecessor.start
                )
                return _shift_working_date(anchor, relationship.lag, lag_resolver)
            if data_date < actual_start:
                raise ValueError(
                    "data_date must not precede actual_start for an out-of-sequence start-to-start relationship"
                )
            # Elapsed work since the actual start consumes the predecessor's
            # start-to-start lag; only the remaining lag constrains the
            # successor. This is the documented Actual Start behaviour.
            elapsed = (predecessor_resolver or resolver).working_days_between(
                actual_start, data_date
            )
            remaining_lag = max(0, relationship.lag - elapsed)
            anchor = (
                data_date
                if start_to_start_lag_calculation_type
                is StartToStartLagCalculationType.ACTUAL_START
                else predecessor.start
            )
            return _shift_working_date(anchor, remaining_lag, lag_resolver)

        return _shift_working_date(predecessor.start, relationship.lag, lag_resolver)

    if relationship.type is RelationshipType.FS:
        return _apply_lag_after(predecessor.finish, relationship.lag, lag_resolver)

    if relationship.type is RelationshipType.FF:
        target_finish = _shift_working_date(
            predecessor.finish, relationship.lag, lag_resolver
        )
        return (successor_resolver or resolver).subtract_working_duration(target_finish, successor_duration)

    if relationship.type is RelationshipType.SF:
        target_finish = _shift_working_date(
            predecessor.start, relationship.lag, lag_resolver
        )
        return (successor_resolver or resolver).subtract_working_duration(
            target_finish, successor_duration
        )

    raise ValueError(f"unsupported relationship type: {relationship.type}")


def _topological_order(
    activity_ids: Iterable[str], relationships: Iterable[Relationship],
) -> list[str]:
    ids = sorted(activity_ids)
    predecessor_count = {activity_id: 0 for activity_id in ids}
    successors: dict[str, list[str]] = {activity_id: [] for activity_id in ids}
    for rel in relationships:
        predecessor_count[rel.successor_id] += 1
        successors[rel.predecessor_id].append(rel.successor_id)
    ready = sorted(
        activity_id for activity_id, count in predecessor_count.items() if count == 0
    )
    order: list[str] = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for successor_id in sorted(successors[current]):
            predecessor_count[successor_id] -= 1
            if predecessor_count[successor_id] == 0:
                ready.append(successor_id)
                ready.sort()
    if len(order) != len(ids):
        raise SchedulingCycleError("activity network contains a cycle")
    return order


def _apply_expected_finish_target(
    start: date,
    activity: Activity,
    resolver: WorkingTimeResolver,
    use_expected_finish_dates: bool,
    scheduled_duration: int,
) -> date:
    """Apply the P6 expected-finish scheduling target without moving before logic."""
    if not use_expected_finish_dates or activity.expected_finish is None:
        return start

    expected_start = resolver.subtract_working_duration(
        resolver.normalize_finish(activity.expected_finish),
        scheduled_duration,
    )
    return max(start, expected_start)


def forward_pass(
    activities: Iterable[Activity],
    relationships: Iterable[Relationship],
    project_start: date,
    resolver: WorkingTimeResolver,
    constraints: Sequence[ActivityConstraint] | None = None,
    calculation_context: CalculationContext | None = None,
    start_to_start_lag_calculation_type: StartToStartLagCalculationType = StartToStartLagCalculationType.EARLY_START,
    data_date: date | None = None,
    relationship_lag_resolvers: Mapping[tuple[str, str], WorkingTimeResolver] | None = None,
    use_expected_finish_dates: bool = False,
    out_of_sequence_schedule_type: OutOfSequenceScheduleType = OutOfSequenceScheduleType.RETAINED_LOGIC,
    activity_resolvers: Mapping[str, WorkingTimeResolver] | None = None,
) -> Mapping[str, ScheduledActivity]:
    """Deterministic earliest-start pass with P6 date options."""
    if calculation_context is not None:
        if calculation_context.project_version < 0:
            raise ValueError("invalid calculation context")

    activity_list = list(activities)
    activity_map = {activity.id: activity for activity in activity_list}
    if len(activity_map) != len(activity_list):
        raise ValueError("activity ids must be unique")
    if not activity_map:
        return {}

    relationship_list = list(relationships)
    for rel in relationship_list:
        if rel.predecessor_id not in activity_map or rel.successor_id not in activity_map:
            raise ValueError("relationship references an unknown activity")

    constraint_map: dict[str, list[ActivityConstraint]] = {
        activity_id: [] for activity_id in activity_map
    }
    all_constraints = list(constraints or ())
    for constraint in all_constraints:
        if constraint.activity_id not in activity_map:
            raise ValueError("constraint references an unknown activity")
        constraint_map[constraint.activity_id].append(constraint)

    for activity_id, activity_constraints in constraint_map.items():
        activity = activity_map[activity_id]
        activity_resolver = (activity_resolvers or {}).get(activity_id, resolver)
        # Validate each constraint set against the duration the activity is
        # actually scheduled with: completed work occupies no remaining
        # duration, and in-progress work occupies its remaining duration. The
        # backward pass uses the same scheduled duration, so both passes must
        # accept and reject the same constraint windows.
        progress = resolve_progress_state(
            activity, resolver=activity_resolver, data_date=data_date
        )
        if progress.state is ActivityProgressState.COMPLETE:
            constraint_duration = 0
        elif progress.state is ActivityProgressState.NOT_STARTED:
            constraint_duration = activity.duration
        else:
            constraint_duration = progress.remaining.remaining_duration
        validate_constraint_set(
            activity_constraints, constraint_duration, activity_resolver
        )

    incoming: dict[str, list[Relationship]] = {
        activity_id: [] for activity_id in activity_map
    }
    for rel in relationship_list:
        incoming[rel.successor_id].append(rel)

    order = _topological_order(activity_map, relationship_list)
    result: dict[str, ScheduledActivity] = {}

    for activity_id in order:
        activity = activity_map[activity_id]
        activity_resolver = (activity_resolvers or {}).get(activity_id, resolver)
        progress = resolve_progress_state(
            activity, resolver=activity_resolver, data_date=data_date
        )

        # Actual dates are recorded facts: completed work keeps its actual
        # start/finish in every out-of-sequence mode. Only remaining work is
        # placed by the selected scheduling method.
        if (
            progress.state is ActivityProgressState.COMPLETE
            and activity.actual_start is not None
        ):
            if data_date is not None and data_date < activity.actual_start:
                raise ValueError("data_date must not precede actual_start for progressed activity")
            start = activity_resolver.normalize_start(activity.actual_start)
            finish = (
                activity_resolver.normalize_finish(activity.actual_finish)
                if activity.actual_finish is not None
                else start
            )
            scheduled_duration = 0
            for constraint in sorted(
                constraint_map[activity_id], key=lambda item: (item.type.value, item.date)
            ):
                validate_upper_bound(constraint, start, finish, activity_resolver)
            result[activity_id] = ScheduledActivity(
                activity_id=activity_id, start=start, finish=finish, duration=0
            )
            continue

        if progress.state is ActivityProgressState.NOT_STARTED:
            scheduled_duration = activity.duration
        else:
            scheduled_duration = progress.remaining.remaining_duration

        if not incoming[activity_id]:
            logic_start = activity_resolver.normalize_start(project_start)
        else:
            start_requirements = [
                _successor_start(
                    rel,
                    result[rel.predecessor_id],
                    scheduled_duration,
                    resolver,
                    activity_map[rel.predecessor_id],
                    start_to_start_lag_calculation_type,
                    data_date,
                    (relationship_lag_resolvers or {}).get(
                        (rel.predecessor_id, rel.successor_id)
                    ),
                    (activity_resolvers or {}).get(rel.predecessor_id, resolver),
                    activity_resolver,
                )
                for rel in sorted(
                    incoming[activity_id],
                    key=lambda item: (
                        item.predecessor_id, item.successor_id,
                        item.type.value, item.lag
                    ),
                )
            ]
            logic_start = activity_resolver.normalize_start(max(start_requirements))

        if progress.state is ActivityProgressState.IN_PROGRESS:
            actual_start = activity_resolver.normalize_start(activity.actual_start)
            if data_date is not None and data_date < activity.actual_start:
                raise ValueError("data_date must not precede actual_start for progressed activity")
            if actual_start < logic_start:
                if data_date is None:
                    raise ValueError("data_date is required for out-of-sequence progress")
                # Classify explicitly so an unsupported mode or inconsistent
                # boundary fails here rather than producing a silent schedule.
                resolve_out_of_sequence_action(
                    activity,
                    relationship_required_start=logic_start,
                    data_date=data_date,
                    mode=out_of_sequence_schedule_type,
                )
            remaining_start = progress.remaining.remaining_start or activity.actual_start
            progress_boundary = activity_resolver.normalize_start(remaining_start)

            if out_of_sequence_schedule_type is OutOfSequenceScheduleType.PROGRESS_OVERRIDE:
                # Progressed work proceeds from its progress boundary; unfinished
                # predecessor logic no longer holds it back.
                start = max(actual_start, progress_boundary)
            elif out_of_sequence_schedule_type is OutOfSequenceScheduleType.ACTUAL_DATES:
                # The forward pass is anchored on the recorded actual start.
                start = actual_start
            else:
                # Retained Logic keeps remaining work subject to both the
                # selected progress boundary and unfinished predecessor logic.
                start = max(logic_start, progress_boundary)
        else:
            start = logic_start

        for constraint in sorted(
            constraint_map[activity_id], key=lambda item: (item.type.value, item.date)
        ):
            start = apply_earliest_constraint(
                constraint, start, scheduled_duration, activity_resolver
            )

        start = _apply_expected_finish_target(
            start,
            activity,
            activity_resolver,
            use_expected_finish_dates,
            scheduled_duration,
        )
        finish = activity_resolver.add_working_duration(start, scheduled_duration)

        for constraint in sorted(
            constraint_map[activity_id], key=lambda item: (item.type.value, item.date)
        ):
            validate_upper_bound(constraint, start, finish, activity_resolver)

        result[activity_id] = ScheduledActivity(
            activity_id=activity_id, start=start, finish=finish, duration=scheduled_duration
        )

    return result
