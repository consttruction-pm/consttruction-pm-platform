from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Mapping

from .activity import Activity
from .calendar import WorkingTimeResolver
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


def _successor_start(
    relationship: Relationship,
    predecessor: ScheduledActivity,
    successor_duration: int,
    resolver: WorkingTimeResolver,
) -> date:
    lag = relationship.lag

    if relationship.type is RelationshipType.SS:
        return _shift_working_date(predecessor.start, lag, resolver)

    if relationship.type is RelationshipType.FS:
        if lag >= 0:
            target = resolver.add_working_duration(predecessor.finish, lag)
        else:
            target = resolver.subtract_working_duration(predecessor.finish, -lag)
        return resolver.next_working_day(target)

    if relationship.type is RelationshipType.FF:
        finish = _shift_working_date(predecessor.finish, lag, resolver)
        return resolver.subtract_working_duration(finish, successor_duration)

    if relationship.type is RelationshipType.SF:
        finish = _shift_working_date(predecessor.start, lag, resolver)
        return resolver.subtract_working_duration(finish, successor_duration)

    raise ValueError(f"unsupported relationship type: {relationship.type}")


def _topological_order(
    activity_ids: Iterable[str],
    relationships: Iterable[Relationship],
) -> list[str]:
    ids = sorted(activity_ids)
    predecessor_count = {activity_id: 0 for activity_id in ids}
    successors: dict[str, list[str]] = {activity_id: [] for activity_id in ids}

    for rel in relationships:
        predecessor_count[rel.successor_id] += 1
        successors[rel.predecessor_id].append(rel.successor_id)

    ready = sorted(
        activity_id
        for activity_id, count in predecessor_count.items()
        if count == 0
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
) -> Mapping[str, ScheduledActivity]:
    """Run a deterministic earliest-start forward pass over an activity network.

    All predecessors are evaluated; the latest relationship-imposed start wins.
    The result is independent of input collection order. Cycles are rejected.
    """

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

    incoming: dict[str, list[Relationship]] = {
        activity_id: [] for activity_id in activity_map
    }
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
                _successor_start(
                    rel,
                    result[rel.predecessor_id],
                    activity.duration,
                    resolver,
                )
                for rel in sorted(
                    incoming[activity_id],
                    key=lambda item: (
                        item.predecessor_id,
                        item.successor_id,
                        item.type.value,
                        item.lag,
                    ),
                )
            )

        finish = resolver.add_working_duration(start, activity.duration)
        result[activity_id] = ScheduledActivity(
            activity_id=activity_id,
            start=start,
            finish=finish,
            duration=activity.duration,
        )

    return result
