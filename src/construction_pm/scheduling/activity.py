from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Activity:
    """Portable scheduling activity used by the Shared Scheduling Core."""

    id: str
    duration: int
    actual_start: date | None = None
    expected_finish: date | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("activity id is required")
        if not isinstance(self.duration, int):
            raise TypeError("duration must be an integer working-day value")
        if self.duration < 0:
            raise ValueError("duration must be non-negative")
        if self.actual_start is not None and not isinstance(self.actual_start, date):
            raise TypeError("actual_start must be a date or None")
        if self.expected_finish is not None and not isinstance(self.expected_finish, date):
            raise TypeError("expected_finish must be a date or None")
        if self.actual_start is not None and self.expected_finish is not None and self.expected_finish < self.actual_start:
            raise ValueError("expected_finish must not precede actual_start")
