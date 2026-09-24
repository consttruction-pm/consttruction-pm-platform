from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

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


def successor_earliest_start(
    relationship: Relationship,
    predecessor_start,
    predecessor_finish,
    duration: int,
    resolver: WorkingTimeResolver,
):
    """Calculate the earliest successor start imposed by one relationship.

    Lag is expressed in working days. This function is intentionally pure and
    framework-independent so the same rule can execute on Web, Desktop and
    approved Mobile offline workflows.
    """
    lagged_finish = resolver.add_working_duration(predecessor_finish, relationship.lag) if relationship.lag >= 0 else resolver.subtract_working_duration(predecessor_finish, -relationship.lag)
    lagged_start = resolver.add_working_duration(predecessor_start, relationship.lag) if relationship.lag >= 0 else resolver.subtract_working_duration(predecessor_start, -relationship.lag)

    if relationship.type is RelationshipType.FS:
        return resolver.next_working_day(lagged_finish)
    if relationship.type is RelationshipType.SS:
        return lagged_start
    if relationship.type is RelationshipType.FF:
        target_finish = lagged_finish
        return resolver.subtract_working_duration(target_finish, duration)
    if relationship.type is RelationshipType.SF:
        target_finish = lagged_start
        return resolver.subtract_working_duration(target_finish, duration)
    raise ValueError(f"unsupported relationship type: {relationship.type}")
