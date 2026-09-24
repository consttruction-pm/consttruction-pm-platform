from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Activity:
    """Portable scheduling activity used by the Shared Scheduling Core."""

    id: str
    duration: int

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("activity id is required")
        if not isinstance(self.duration, int):
            raise TypeError("duration must be an integer working-day value")
        if self.duration < 0:
            raise ValueError("duration must be non-negative")
