from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class PercentCompleteType(str, Enum):
    DURATION = "DURATION"
    UNITS = "UNITS"
    PHYSICAL = "PHYSICAL"
    SCOPE = "SCOPE"


class ActivityStatus(str, Enum):
    """P6 Activity.Status semantic values."""

    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"

    @classmethod
    def from_p6_value(cls, value: str) -> "ActivityStatus":
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"unsupported P6 Activity.Status value: {value!r}") from exc


class ActivityType(str, Enum):
    """P6 Activity.Type semantic values."""

    TASK_DEPENDENT = "Task Dependent"
    RESOURCE_DEPENDENT = "Resource Dependent"
    LEVEL_OF_EFFORT = "Level of Effort"
    START_MILESTONE = "Start Milestone"
    FINISH_MILESTONE = "Finish Milestone"
    WBS_SUMMARY = "WBS Summary"

    @classmethod
    def from_p6_value(cls, value: str) -> "ActivityType":
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"unsupported P6 Activity.Type value: {value!r}") from exc


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
    status: ActivityStatus = ActivityStatus.NOT_STARTED
    activity_type: ActivityType = ActivityType.TASK_DEPENDENT
    status_code: ActivityStatusCode = ActivityStatusCode.PLANNED

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("activity id must be a non-empty string")
        if isinstance(self.duration, bool) or not isinstance(self.duration, int):
            raise TypeError("duration must be an integer working-day value")
        if self.duration < 0:
            raise ValueError("duration must be non-negative")
        if self.actual_start is not None and (not isinstance(self.actual_start, date) or isinstance(self.actual_start, datetime)):
            raise TypeError("actual_start must be a date or None")
        if self.actual_finish is not None and (not isinstance(self.actual_finish, date) or isinstance(self.actual_finish, datetime)):
            raise TypeError("actual_finish must be a date or None")
        if self.actual_start is None and self.actual_finish is not None:
            raise ValueError("actual_finish requires actual_start")
        if self.actual_start is not None and self.actual_finish is not None and self.actual_finish < self.actual_start:
            raise ValueError("actual_finish must not precede actual_start")
        if self.remaining_duration is not None:
            if isinstance(self.remaining_duration, bool) or not isinstance(self.remaining_duration, int):
                raise TypeError("remaining_duration must be an integer working-day value or None")
            if self.remaining_duration < 0:
                raise ValueError("remaining_duration must be non-negative")
            if self.actual_finish is not None and self.remaining_duration != 0:
                raise ValueError("completed activities must have zero remaining_duration")
        if self.remaining_start is not None and (not isinstance(self.remaining_start, date) or isinstance(self.remaining_start, datetime)):
            raise TypeError("remaining_start must be a date or None")
        if self.actual_finish is not None and self.remaining_start is not None:
            raise ValueError("completed activities cannot have a remaining_start")
        if self.percent_complete is not None:
            if isinstance(self.percent_complete, bool) or not isinstance(self.percent_complete, (int, float)):
                raise TypeError("percent_complete must be numeric or None")
            if not 0 <= self.percent_complete <= 100:
                raise ValueError("percent_complete must be between 0 and 100")
        if not isinstance(self.percent_complete_type, PercentCompleteType):
            raise TypeError("percent_complete_type must be a PercentCompleteType")
        if not isinstance(self.status, ActivityStatus):
            raise TypeError("status must be an ActivityStatus")
        if not isinstance(self.activity_type, ActivityType):
            raise TypeError("activity_type must be an ActivityType")
        if not isinstance(self.status_code, ActivityStatusCode):
            raise TypeError("status_code must be an ActivityStatusCode")
        if self.expected_finish is not None and (not isinstance(self.expected_finish, date) or isinstance(self.expected_finish, datetime)):
            raise TypeError("expected_finish must be a date or None")
        if self.actual_start is not None and self.expected_finish is not None and self.expected_finish < self.actual_start:
            raise ValueError("expected_finish must not precede actual_start")
        if self.actual_finish is not None and self.percent_complete not in (None, 100):
            raise ValueError("completed activities must have 100 percent_complete")
