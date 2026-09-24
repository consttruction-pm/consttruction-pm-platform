from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .calendar import WorkingTimeResolver


class RelationshipType(str, Enum):
    FS = "FS"
    SS = "SS"
    FF = "FF"
    SF = "SF"


@dataclass(frozen=True)
class Relationship:
    predecessor_id: str
    successor_id: str
    type: RelationshipType = RelationshipType.FS
    lag: int = 0

    def __post_init__(self) -> None:
        if not self.predecessor_id or not self.successor_id:
            raise ValueError("relationship endpoints are required")
        if self.predecessor_id == self.successor_id:
            raise ValueError("self relationships are not allowed")
        if not isinstance(self.lag, int):
            raise TypeError("lag must be an integer working-day value")


def _shift_event(
    value,
    lag: int,
    resolver: WorkingTimeResolver,
) -> object:
    if lag >= 0:
        return resolver.next_working_day(
            resolver.add_working_duration(value, lag)
        )
    return resolver.previous_working_day(
        resolver.subtract_working_duration(value, -lag)
    )


def successor_earliest_start(
    relationship: Relationship,
    predecessor_start,
    predecessor_finish,
    duration: int,
    resolver: WorkingTimeResolver,
):
    """Calculate the earliest successor start imposed by one relationship.

    Lag is expressed in working days and uses the same event-boundary
    semantics as the Forward Pass.
    """
    if relationship.type is RelationshipType.SS:
        if relationship.lag >= 0:
            return resolver.add_working_duration(
                predecessor_start, relationship.lag + 1
            )
        return resolver.subtract_working_duration(
            predecessor_start, -relationship.lag + 1
        )

    if relationship.type is RelationshipType.FS:
        return _shift_event(predecessor_finish, relationship.lag, resolver)

    if relationship.type is RelationshipType.FF:
        target_finish = _shift_event(predecessor_finish, relationship.lag, resolver)
        return resolver.subtract_working_duration(target_finish, duration)

    if relationship.type is RelationshipType.SF:
        target_finish = _shift_event(predecessor_start, relationship.lag, resolver)
        return resolver.subtract_working_duration(target_finish, duration)

    raise ValueError(f"unsupported relationship type: {relationship.type}")
