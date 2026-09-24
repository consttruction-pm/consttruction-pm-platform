from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Iterable, Mapping

from .activity import Activity
from .calendar import WorkingTimeResolver
from .constraints import (
    ActivityConstraint,
    apply_latest_constraint,
    validate_constraint_set,
    validate_constraint_window,
)
from .forward_pass import ScheduledActivity, _shift_working_date, _topological_order, forward_pass
from .relationships import Relationship, RelationshipType


class ScheduleMode(str, Enum):
    EARLIEST = "EARLIEST"
    ALAP = "ALAP"


@dataclass(frozen=True)
class ScheduleOptions:
    """Explicit scheduling-output options."""

    mode: ScheduleMode = ScheduleMode.EARLIEST

    def __post_init__(self) -> None:
        if not isinstance(self.mode, ScheduleMode):
            raise ValueError("mode must be a ScheduleMode")


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
            resolver.subtract_working_duration(successor_event, lag)
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
    if finish < early_project_finish:
        raise ValueError("project finish cannot be earlier than the early project finish")

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
            late_finish = resolver.add_working_duration(late_start, activity.duration)

        for constraint in sorted(
            constraint_map[activity_id], key=lambda item: (item.type.value, item.date)
        ):
            late_start = apply_latest_constraint(
                constraint, late_start, activity.duration, resolver
            )
            late_finish = resolver.add_working_duration(late_start, activity.duration)

        for constraint in sorted(
            constraint_map[activity_id], key=lambda item: (item.type.value, item.date)
        ):
            validate_constraint_window(constraint, late_start, late_finish, resolver)

        result[activity_id] = ScheduledActivity(
            activity_id=activity_id,
            start=late_start,
            finish=late_finish,
            duration=activity.duration,
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
                resolver.add_working_duration(predecessor.finish, relationship.lag)
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
        required = (
            resolver.next_working_day(
                resolver.add_working_duration(predecessor.start, relationship.lag)
            )
            if relationship.lag >= 0
            else resolver.previous_working_day(
                resolver.subtract_working_duration(predecessor.start, -relationship.lag)
            )
        )
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
) -> Mapping[str, FloatActivity]:
    """Calculate relationship-aware Total Float and Free Float."""
    activity_map = {activity.id: activity for activity in activities}
    outgoing: dict[str, list[Relationship]] = {activity_id: [] for activity_id in activity_map}
    for rel in relationships:
        outgoing[rel.predecessor_id].append(rel)

    result: dict[str, FloatActivity] = {}
    for activity_id in sorted(activity_map):
        early = early_schedule[activity_id]
        late = late_schedule[activity_id]
        total = max(0, _working_delay_between(early.start, late.start, resolver))
        free = _free_float(
            activity_map[activity_id], early, outgoing[activity_id], early_schedule, resolver
        )
        result[activity_id] = FloatActivity(
            activity_id=activity_id,
            early_start=early.start,
            early_finish=early.finish,
            late_start=late.start,
            late_finish=late.finish,
            total_float=total,
            free_float=min(total, free),
            critical=total == 0,
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
) -> ScheduleResult:
    """Run CPM passes and select either earliest or ALAP output."""
    selected_options = options or ScheduleOptions()
    activity_list = list(activities)
    relationship_list = list(relationships)
    constraint_list = list(constraints or ())
    early = forward_pass(
        activity_list, relationship_list, project_start, resolver, constraint_list
    )
    late = backward_pass(
        activity_list, relationship_list, early, project_finish, resolver, constraint_list
    )
    floats = calculate_floats(activity_list, relationship_list, early, late, resolver)

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
