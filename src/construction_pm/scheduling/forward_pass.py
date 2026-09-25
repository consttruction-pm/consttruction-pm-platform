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
from .relationships import Relationship, RelationshipType


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
) -> date:
    if relationship.type is RelationshipType.SS:
        return _shift_working_date(predecessor.start, relationship.lag, resolver)

    if relationship.type is RelationshipType.FS:
        return _apply_lag_after(predecessor.finish, relationship.lag, resolver)

    if relationship.type is RelationshipType.FF:
        target_finish = _shift_working_date(predecessor.finish, relationship.lag, resolver)
        return resolver.subtract_working_duration(target_finish, successor_duration)

    if relationship.type is RelationshipType.SF:
        target_finish = _shift_working_date(predecessor.start, relationship.lag, resolver)
        return resolver.subtract_working_duration(target_finish, successor_duration)

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


def forward_pass(
    activities: Iterable[Activity],
    relationships: Iterable[Relationship],
    project_start: date,
    resolver: WorkingTimeResolver,
    constraints: Sequence[ActivityConstraint] | None = None,
    calculation_context: CalculationContext | None = None,
) -> Mapping[str, ScheduledActivity]:
    """Deterministic earliest-start pass with foundational date constraints.

    When supplied, ``calculation_context`` is validated at the Shared Core
    boundary. The context is metadata/identity only and never changes dates.
    """
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
        validate_constraint_set(
            activity_constraints, activity_map[activity_id].duration, resolver
        )

    incoming: dict[str, list[Relationship]] = {activity_id: [] for activity_id in activity_map}
    for rel in relationship_list:
        incoming[rel.successor_id].append(rel)

    order = _topological_order(activity_map, relationship_list)
    result: dict[str, ScheduledActivity] = {}

    for activity_id in order:
        activity = activity_map[activity_id]
        if not incoming[activity_id]:
            start = resolver.normalize_start(project_start)
        else:
            start = max(
                _successor_start(rel, result[rel.predecessor_id], activity.duration, resolver)
                for rel in sorted(
                    incoming[activity_id],
                    key=lambda item: (
                        item.predecessor_id, item.successor_id, item.type.value, item.lag
                    ),
                )
            )

        for constraint in sorted(
            constraint_map[activity_id], key=lambda item: (item.type.value, item.date)
        ):
            start = apply_earliest_constraint(constraint, start, activity.duration, resolver)

        finish = resolver.add_working_duration(start, activity.duration)

        for constraint in sorted(
            constraint_map[activity_id], key=lambda item: (item.type.value, item.date)
        ):
            validate_upper_bound(constraint, start, finish, resolver)

        result[activity_id] = ScheduledActivity(
            activity_id=activity_id, start=start, finish=finish, duration=activity.duration
        )

    return result
