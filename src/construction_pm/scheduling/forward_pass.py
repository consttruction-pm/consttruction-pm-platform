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
    if lag >= 0:
        return resolver.add_working_duration(value, lag + 1) if lag else resolver.normalize_start(value)
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
            return resolver.next_working_day(target)
        target = resolver.subtract_working_duration(predecessor.finish, -lag)
        return resolver.next_working_day(target)

    if relationship.type is RelationshipType.FF:
        finish = _shift_working_date(predecessor.finish, lag, resolver)
        return resolver.subtract_working_duration(finish, max(successor_duration - 1, 0))

    if relationship.type is RelationshipType.SF:
        finish = _shift_working_date(predecessor.start, lag, resolver)
        return resolver.subtract_working_duration(finish, max(successor_duration - 1, 0))

    raise ValueError(f"unsupported relationship type: {relationship.type}")


def forward_pass(
    activities: Iterable[Activity],
    relationships: Iterable[Relationship],
    project_start: date,
    resolver: WorkingTimeResolver,
) -> Mapping[str, ScheduledActivity]:
    """Run a deterministic earliest-start forward pass over an activity network.

    The result is independent of input collection order. All predecessors of an
    activity are evaluated and the most restrictive (latest) relationship
    requirement determines its earliest start. Cycles are rejected explicitly.
    """

    activity_map = {activity.id: activity for activity in activities}
    if len(activity_map) == 0:
        return {}

    if any(activity.id != key for key, activity in activity_map.items()):
        raise ValueError("activity ids must be stable")

    relationship_list = list(relationships)
    for rel in relationship_list:
        if rel.predecessor_id not in activity_map or rel.successor_id not in activity_map:
            raise ValueError("relationship references an unknown activity")

    incoming: dict[str, list[Relationship]] = {activity_id: [] for activity_id in activity_map}
    outgoing_count: dict[str, int] = {activity_id: 0 for activity_id in activity_map}
    for rel in relationship_list:
        incoming[rel.successor_id].append(rel)
        outgoing_count[rel.predecessor_id] += 1

    ready = sorted(
        activity_id for activity_id, count in outgoing_count.items()
        if count == 0
    )
    order: list[str] = []
    remaining_outgoing = dict(outgoing_count)
    successors: dict[str, list[str]] = {activity_id: [] for activity_id in activity_map}
    for rel in relationship_list:
        successors[rel.predecessor_id].append(rel.successor_id)

    while ready:
        current = ready.pop(0)
        order.append(current)
        for successor_id in sorted(successors[current]):
            remaining_outgoing[successor_id] -= 1
            if remaining_outgoing[successor_id] == 0:
                ready.append(successor_id)
                ready.sort()

    if len(order) != len(activity_map):
        raise SchedulingCycleError("activity network contains a cycle")

    # Reverse the dependency-first order above: incoming edges are what must be
    # resolved first. The construction above counts outgoing edges, so roots
    # are actually sinks; use a standard Kahn pass on predecessor counts.
    predecessor_count = {activity_id: len(incoming[activity_id]) for activity_id in activity_map}
    ready = sorted(
        activity_id for activity_id, count in predecessor_count.items()
        if count == 0
    )
    order = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for successor_id in sorted(successors[current]):
            predecessor_count[successor_id] -= 1
            if predecessor_count[successor_id] == 0:
                ready.append(successor_id)
                ready.sort()

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
