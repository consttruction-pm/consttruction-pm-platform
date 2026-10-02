from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class PercentCompleteType(str, Enum):
    DURATION = "DURATION"
    UNITS = "UNITS"
    PHYSICAL = "PHYSICAL"
    SCOPE = "SCOPE"


class ActivityStatusCode(str, Enum):
    """P6 Activity.StatusCode semantic values."""

    PLANNED = "Planned"
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    WHAT_IF = "What-If"
    REQUESTED = "Requested"
    TEMPLATE = "Template"

    @classmethod
    def from_p6_value(cls, value: str) -> "ActivityStatusCode":
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(
                f"unsupported P6 Activity.StatusCode value: {value!r}"
            ) from exc


@dataclass(frozen=True)
class Activity:
    """Portable scheduling activity used by the Shared Scheduling Core."""

    id: str
    duration: int
    actual_start: date | None = None
    actual_finish: date | None = None
    remaining_duration: int | None = None
    remaining_start: date | None = None
    percent_complete: float | None = None
    percent_complete_type: PercentCompleteType = PercentCompleteType.DURATION
    expected_finish: date | None = None
    status_code: ActivityStatusCode = ActivityStatusCode.PLANNED

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("activity id is required")
        if not isinstance(self.duration, int):
            raise TypeError("duration must be an integer working-day value")
        if self.duration < 0:
            raise ValueError("duration must be non-negative")
        if self.actual_start is not None and not isinstance(self.actual_start, date):
            raise TypeError("actual_start must be a date or None")
        if self.actual_finish is not None and not isinstance(self.actual_finish, date):
            raise TypeError("actual_finish must be a date or None")
        if self.actual_start is None and self.actual_finish is not None:
            raise ValueError("actual_finish requires actual_start")
        if self.actual_start is not None and self.actual_finish is not None and self.actual_finish < self.actual_start:
            raise ValueError("actual_finish must not precede actual_start")
        if self.remaining_duration is not None:
            if not isinstance(self.remaining_duration, int):
                raise TypeError("remaining_duration must be an integer working-day value or None")
            if self.remaining_duration < 0:
                raise ValueError("remaining_duration must be non-negative")
            if self.actual_finish is not None and self.remaining_duration != 0:
                raise ValueError("completed activities must have zero remaining_duration")
        if self.remaining_start is not None and not isinstance(self.remaining_start, date):
            raise TypeError("remaining_start must be a date or None")
        if self.actual_finish is not None and self.remaining_start is not None:
            raise ValueError("completed activities cannot have a remaining_start")
        if self.percent_complete is not None:
            if not isinstance(self.percent_complete, (int, float)):
                raise TypeError("percent_complete must be numeric or None")
            if not 0 <= self.percent_complete <= 100:
                raise ValueError("percent_complete must be between 0 and 100")
        if not isinstance(self.percent_complete_type, PercentCompleteType):
            raise TypeError("percent_complete_type must be a PercentCompleteType")
        if not isinstance(self.status_code, ActivityStatusCode):
            raise TypeError("status_code must be an ActivityStatusCode")
        if self.expected_finish is not None and not isinstance(self.expected_finish, date):
            raise TypeError("expected_finish must be a date or None")
        if self.actual_start is not None and self.expected_finish is not None and self.expected_finish < self.actual_start:
            raise ValueError("expected_finish must not precede actual_start")
        if self.actual_finish is not None and self.percent_complete not in (None, 100):
            raise ValueError("completed activities must have 100 percent_complete")
