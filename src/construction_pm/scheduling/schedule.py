from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Mapping

from .activity import Activity
from .calendar import WorkingTimeResolver
from .forward_pass import ScheduledActivity, _shift_working_date, _topological_order
from .relationships import Relationship, RelationshipType


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


def _latest_predecessor_start(
    relationship: Relationship,
    successor: ScheduledActivity,
    predecessor_duration: int,
    resolver: WorkingTimeResolver,
) -> date:
    """Invert one forward relationship constraint for the backward pass."""
    lag = relationship.lag

    if relationship.type is RelationshipType.FS:
        # predecessor finish + lag < successor start in our inclusive model.
        target_finish = (
            resolver.subtract_working_duration(successor.start, lag)
            if lag >= 0
            else resolver.add_working_duration(successor.start, -lag)
        )
        return resolver.subtract_working_duration(target_finish, predecessor_duration)

    if relationship.type is RelationshipType.SS:
        target_start = _shift_working_date(successor.start, -lag, resolver)
        return target_start

    if relationship.type is RelationshipType.FF:
        target_finish = _shift_working_date(successor.finish, -lag, resolver)
        return resolver.subtract_working_duration(target_finish, predecessor_duration)

    if relationship.type is RelationshipType.SF:
        target_start = _shift_working_date(successor.finish, -lag, resolver)
        return target_start

    raise ValueError(f"unsupported relationship type: {relationship.type}")


def backward_pass(
    activities: Iterable[Activity],
    relationships: Iterable[Relationship],
    forward: Mapping[str, ScheduledActivity],
    project_finish: date | None,
    resolver: WorkingTimeResolver,
) -> Mapping[str, ScheduledActivity]:
    """Calculate deterministic latest dates from the project finish.

    The supplied forward schedule is authoritative for early dates. Each
    activity's latest start is the most restrictive inverse relationship
    requirement among its successors.
    """
    activity_list = list(activities)
    activity_map = {activity.id: activity for activity in activity_list}
    relationship_list = list(relationships)

    if set(activity_map) != set(forward):
        raise ValueError("forward schedule must contain every activity")

    for rel in relationship_list:
        if rel.predecessor_id not in activity_map or rel.successor_id not in activity_map:
            raise ValueError("relationship references an unknown activity")

    finish = project_finish or max(item.finish for item in forward.values())
    outgoing: dict[str, list[Relationship]] = {activity_id: [] for activity_id in activity_map}
    for rel in relationship_list:
        outgoing[rel.predecessor_id].append(rel)

    order = _topological_order(activity_map, relationship_list)
    result: dict[str, ScheduledActivity] = {}

    for activity_id in reversed(order):
        activity = activity_map[activity_id]
        successors = outgoing[activity_id]
        if not successors:
            late_finish = resolver.normalize_finish(finish)
            late_start = resolver.subtract_working_duration(
                late_finish, activity.duration
            )
        else:
            candidates = [
                _latest_predecessor_start(
                    rel,
                    forward[rel.successor_id],
                    activity.duration,
                    resolver,
                )
                for rel in sorted(
                    successors,
                    key=lambda item: (
                        item.successor_id,
                        item.predecessor_id,
                        item.type.value,
                        item.lag,
                    ),
                )
            ]
            late_start = min(candidates)
            late_finish = resolver.add_working_duration(
                late_start, activity.duration
            )

        result[activity_id] = ScheduledActivity(
            activity_id=activity_id,
            start=late_start,
            finish=late_finish,
            duration=activity.duration,
        )

    return result


def _working_delay_between(
    early: date,
    delayed: date,
    resolver: WorkingTimeResolver,
) -> int:
    if delayed < early:
        return -_working_delay_between(delayed, early, resolver)
    return resolver.working_days_between(early, delayed)


def _relationship_holds(
    relationship: Relationship,
    predecessor: ScheduledActivity,
    successor: ScheduledActivity,
    resolver: WorkingTimeResolver,
) -> bool:
    lag = relationship.lag

    if relationship.type is RelationshipType.FS:
        required = (
            _shift_working_date(predecessor.finish, lag, resolver)
        )
        return successor.start > required

    if relationship.type is RelationshipType.SS:
        required = _shift_working_date(predecessor.start, lag, resolver)
        return successor.start >= required

    if relationship.type is RelationshipType.FF:
        required = _shift_working_date(predecessor.finish, lag, resolver)
        return successor.finish >= required

    if relationship.type is RelationshipType.SF:
        required = _shift_working_date(predecessor.start, lag, resolver)
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

    max_safe = 0
    for rel in successors:
        successor = early_schedule[rel.successor_id]
        delay = 0
        while delay < 10000:
            candidate_start = resolver.add_working_duration(early.start, delay)
            candidate = ScheduledActivity(
                activity_id=early.activity_id,
                start=candidate_start,
                finish=resolver.add_working_duration(
                    candidate_start, activity.duration
                ),
                duration=activity.duration,
            )
            if not _relationship_holds(rel, candidate, successor, resolver):
                break
            delay += 1
        max_safe = delay - 1 if max_safe == 0 else min(max_safe, delay - 1)
    return max(0, max_safe)


def calculate_floats(
    activities: Iterable[Activity],
    relationships: Iterable[Relationship],
    early_schedule: Mapping[str, ScheduledActivity],
    late_schedule: Mapping[str, ScheduledActivity],
    resolver: WorkingTimeResolver,
) -> Mapping[str, FloatActivity]:
    """Calculate Total Float, relationship-aware Free Float and criticality."""
    activity_map = {activity.id: activity for activity in activities}
    outgoing: dict[str, list[Relationship]] = {activity_id: [] for activity_id in activity_map}
    for rel in relationships:
        outgoing[rel.predecessor_id].append(rel)

    result: dict[str, FloatActivity] = {}
    for activity_id in sorted(activity_map):
        early = early_schedule[activity_id]
        late = late_schedule[activity_id]
        total = max(
            0,
            _working_delay_between(early.start, late.start, resolver),
        )
        free = _free_float(
            activity_map[activity_id],
            early,
            outgoing[activity_id],
            early_schedule,
            resolver,
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
) -> ScheduleResult:
    """Run forward pass, backward pass and float/critical-path analysis."""
    activity_list = list(activities)
    relationship_list = list(relationships)
    early = __import__(
        "construction_pm.scheduling.forward_pass",
        fromlist=["forward_pass"],
    ).forward_pass(activity_list, relationship_list, project_start, resolver)
    late = backward_pass(
        activity_list,
        relationship_list,
        early,
        project_finish,
        resolver,
    )
    floats = calculate_floats(
        activity_list, relationship_list, early, late, resolver
    )
    return ScheduleResult(
        activities=early,
        floats=floats,
        project_finish=project_finish or max(item.finish for item in early.values()),
    )
