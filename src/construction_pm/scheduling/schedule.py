from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Iterable, Mapping

from .activity import Activity
from .calculation_context import CalculationContext
from .calendar import WorkingTimeResolver
from .constraints import (
    ActivityConstraint,
    apply_latest_constraint,
    validate_constraint_set,
    validate_late_constraint_window,
)
from .forward_pass import ScheduledActivity, _shift_working_date, _successor_start, _topological_order, forward_pass
from .relationships import Relationship, RelationshipType


class ScheduleMode(str, Enum):
    EARLIEST = "EARLIEST"
    ALAP = "ALAP"


class TotalFloatCalculationType(str, Enum):
    START_FLOAT = "START_FLOAT"
    FINISH_FLOAT = "FINISH_FLOAT"
    SMALLER_FLOAT = "SMALLER_FLOAT"


class CriticalActivityPathType(str, Enum):
    CRITICAL_FLOAT = "CRITICAL_FLOAT"
    LONGEST_PATH = "LONGEST_PATH"


@dataclass(frozen=True)
class ScheduleOptions:
    """Shared scheduling options with P6-compatible semantics.

    Only options with implemented semantics are applied by this slice.
    Unimplemented P6 options remain explicit in the P6 registry and must not
    be silently ignored by the scheduler.
    """

    mode: ScheduleMode = ScheduleMode.EARLIEST
    compute_total_float_type: TotalFloatCalculationType = (
        TotalFloatCalculationType.START_FLOAT
    )
    critical_activity_float_threshold: int = 0
    critical_activity_path_type: CriticalActivityPathType = (
        CriticalActivityPathType.CRITICAL_FLOAT
    )
    make_open_ended_activities_critical: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.mode, ScheduleMode):
            raise ValueError("mode must be a ScheduleMode")
        if not isinstance(self.compute_total_float_type, TotalFloatCalculationType):
            raise ValueError(
                "compute_total_float_type must be a TotalFloatCalculationType"
            )
        if not isinstance(self.critical_activity_path_type, CriticalActivityPathType):
            raise ValueError(
                "critical_activity_path_type must be a CriticalActivityPathType"
            )
        if isinstance(self.critical_activity_float_threshold, bool):
            raise ValueError("critical_activity_float_threshold must be an integer")
        if not isinstance(self.critical_activity_float_threshold, int):
            raise ValueError("critical_activity_float_threshold must be an integer")
        if self.critical_activity_float_threshold < 0:
            raise ValueError("critical_activity_float_threshold must be non-negative")


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


@dataclass(frozen=True)
class ScheduleResult:
    activities: Mapping[str, ScheduledActivity]
    floats: Mapping[str, FloatActivity]
    project_finish: date
    early_activities: Mapping[str, ScheduledActivity] | None = None
    late_activities: Mapping[str, ScheduledActivity] | None = None
    mode: ScheduleMode = ScheduleMode.EARLIEST


def _inverse_event_shift(successor_event: date, lag: int, resolver: WorkingTimeResolver) -> date:
    if lag >= 0:
        return resolver.previous_working_day(
            resolver.subtract_working_duration(successor_event, lag + 1)
        )
    return resolver.next_working_day(
        resolver.add_working_duration(successor_event, -lag)
    )


def _inverse_start_shift(successor_start: date, lag: int, resolver: WorkingTimeResolver) -> date:
    if lag >= 0:
        return resolver.subtract_working_duration(successor_start, lag + 1)
    return resolver.add_working_duration(successor_start, -lag + 1)


def _latest_predecessor_start(
    relationship: Relationship,
    successor: ScheduledActivity,
    predecessor_duration: int,
    resolver: WorkingTimeResolver,
) -> date:
    if relationship.type is RelationshipType.FS:
        predecessor_finish = _inverse_event_shift(successor.start, relationship.lag, resolver)
        return resolver.subtract_working_duration(predecessor_finish, predecessor_duration)

    if relationship.type is RelationshipType.SS:
        return _inverse_start_shift(successor.start, relationship.lag, resolver)

    if relationship.type is RelationshipType.FF:
        predecessor_finish = _inverse_event_shift(successor.finish, relationship.lag, resolver)
        return resolver.subtract_working_duration(predecessor_finish, predecessor_duration)

    if relationship.type is RelationshipType.SF:
        return _inverse_event_shift(successor.finish, relationship.lag, resolver)

    raise ValueError(f"unsupported relationship type: {relationship.type}")


def backward_pass(
    activities: Iterable[Activity],
    relationships: Iterable[Relationship],
    forward: Mapping[str, ScheduledActivity],
    project_finish: date | None,
    resolver: WorkingTimeResolver,
    constraints: Iterable[ActivityConstraint] | None = None,
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
            activity_constraints, activity_map[activity_id].duration, resolver
        )

    for rel in relationship_list:
        if rel.predecessor_id not in activity_map or rel.successor_id not in activity_map:
            raise ValueError("relationship references an unknown activity")

    early_project_finish = max(item.finish for item in forward.values())
    finish = resolver.normalize_finish(project_finish or early_project_finish)

    outgoing: dict[str, list[Relationship]] = {activity_id: [] for activity_id in activity_map}
    for rel in relationship_list:
        outgoing[rel.predecessor_id].append(rel)

    order = _topological_order(activity_map, relationship_list)
    result: dict[str, ScheduledActivity] = {}

    for activity_id in reversed(order):
        activity = activity_map[activity_id]
        successors = outgoing[activity_id]

        if not successors:
            late_finish = finish
            late_start = resolver.subtract_working_duration(late_finish, activity.duration)
        else:
            late_start = min(
                _latest_predecessor_start(
                    rel, result[rel.successor_id], activity.duration, resolver
                )
                for rel in sorted(
                    successors,
                    key=lambda item: (
                        item.successor_id, item.predecessor_id, item.type.value, item.lag
                    ),
                )
            )
            latest_by_project_finish = resolver.subtract_working_duration(
                finish, activity.duration
            )
            late_start = min(late_start, latest_by_project_finish)
            late_finish = resolver.add_working_duration(late_start, activity.duration)

        for constraint in sorted(
            constraint_map[activity_id], key=lambda item: (item.type.value, item.date)
        ):
            late_start = apply_latest_constraint(
                constraint, late_start, activity.duration, resolver
            )
            late_finish = resolver.add_working_duration(late_start, activity.duration)

        if late_finish > finish:
            raise ValueError(f"backward schedule exceeds project finish for {activity_id}")

        for constraint in sorted(
            constraint_map[activity_id], key=lambda item: (item.type.value, item.date)
        ):
            validate_late_constraint_window(constraint, late_start, late_finish, resolver)

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
        if not _relationship_holds(relationship, result[relationship.predecessor_id], result[relationship.successor_id], resolver):
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
) -> bool:
    if relationship.type is RelationshipType.FS:
        required = (
            resolver.next_working_day(
                resolver.add_working_duration(predecessor.finish, relationship.lag + 1)
            )
            if relationship.lag >= 0
            else resolver.previous_working_day(
                resolver.subtract_working_duration(predecessor.finish, -relationship.lag)
            )
        )
        return successor.start >= required

    if relationship.type is RelationshipType.SS:
        required = _shift_working_date(predecessor.start, relationship.lag, resolver)
        return successor.start >= required

    if relationship.type is RelationshipType.FF:
        required = _shift_working_date(predecessor.finish, relationship.lag, resolver)
        return successor.finish >= required

    if relationship.type is RelationshipType.SF:
        required = _shift_working_date(predecessor.start, relationship.lag, resolver)
        return successor.finish >= required

    raise ValueError(f"unsupported relationship type: {relationship.type}")


def _free_float(
    activity: Activity,
    early: ScheduledActivity,
    successors: list[Relationship],
    early_schedule: Mapping[str, ScheduledActivity],
    resolver: WorkingTimeResolver,
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
            if not _relationship_holds(rel, candidate, successor, resolver):
                break
            delay += 1
        limits.append(delay - 1)
    return max(0, min(limits))


def calculate_floats(
    activities: Iterable[Activity],
    relationships: Iterable[Relationship],
    early_schedule: Mapping[str, ScheduledActivity],
    late_schedule: Mapping[str, ScheduledActivity],
    resolver: WorkingTimeResolver,
    options: ScheduleOptions | None = None,
) -> Mapping[str, FloatActivity]:
    """Calculate relationship-aware Total Float and Free Float."""
    selected_options = options or ScheduleOptions()
    if selected_options.critical_activity_path_type is CriticalActivityPathType.LONGEST_PATH:
        raise NotImplementedError(
            "LONGEST_PATH criticality is registered but not yet implemented by this scheduler slice"
        )

    activity_map = {activity.id: activity for activity in activities}
    outgoing: dict[str, list[Relationship]] = {activity_id: [] for activity_id in activity_map}
    for rel in relationships:
        outgoing[rel.predecessor_id].append(rel)

    result: dict[str, FloatActivity] = {}
    for activity_id in sorted(activity_map):
        early = early_schedule[activity_id]
        late = late_schedule[activity_id]
        start_float = _working_delay_between(early.start, late.start, resolver)
        finish_float = _working_delay_between(early.finish, late.finish, resolver)
        # P6 can calculate total float from Start Float, Finish Float, or the
        # smaller of the two. Negative float remains a valid reportable value.
        if selected_options.compute_total_float_type is TotalFloatCalculationType.FINISH_FLOAT:
            total = finish_float
        elif selected_options.compute_total_float_type is TotalFloatCalculationType.SMALLER_FLOAT:
            total = min(start_float, finish_float)
        else:
            total = start_float
        free = _free_float(
            activity_map[activity_id], early, outgoing[activity_id], early_schedule, resolver
        )
        free = max(0, min(total, free))
        result[activity_id] = FloatActivity(
            activity_id=activity_id,
            early_start=early.start,
            early_finish=early.finish,
            late_start=late.start,
            late_finish=late.finish,
            total_float=total,
            free_float=free,
            critical=(
                total <= selected_options.critical_activity_float_threshold
                or (
                    selected_options.make_open_ended_activities_critical
                    and not outgoing[activity_id]
                )
            ),
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
) -> ScheduleResult:
    """Run CPM passes and select either earliest or ALAP output."""
    selected_options = options or ScheduleOptions()
    if calculation_context is not None and calculation_context.project_version < 0:
        raise ValueError("invalid calculation context")
    activity_list = list(activities)
    relationship_list = list(relationships)
    constraint_list = list(constraints or ())
    early = forward_pass(
        activity_list, relationship_list, project_start, resolver, constraint_list, calculation_context
    )
    late = backward_pass(
        activity_list, relationship_list, early, project_finish, resolver, constraint_list
    )
    floats = calculate_floats(
        activity_list,
        relationship_list,
        early,
        late,
        resolver,
        selected_options,
    )

    effective_finish = resolver.normalize_finish(
        project_finish or max(item.finish for item in early.values())
    )
    selected = late if selected_options.mode is ScheduleMode.ALAP else early

    return ScheduleResult(
        activities=selected,
        floats=floats,
        project_finish=effective_finish,
        early_activities=early,
        late_activities=late,
        mode=selected_options.mode,
    )
