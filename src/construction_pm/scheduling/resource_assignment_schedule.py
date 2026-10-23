from __future__ import annotations

"""Immutable result contract for resource-dependent assignment date derivation.

The contract is intentionally separate from persistence and calculation. It
makes assignment-level dates and unresolved placement explicit so callers
cannot silently substitute activity dates for resource dates.
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class AssignmentPlacementStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    DELAYED_FOR_CAPACITY = "DELAYED_FOR_CAPACITY"
    UNSCHEDULED = "UNSCHEDULED"


@dataclass(frozen=True)
class ResourceAssignmentScheduleResult:
    """Calculated date window for one assignment, bound to an input snapshot."""

    snapshot_hash: str
    assignment_id: str
    activity_id: str
    resource_id: str
    is_driving: bool
    early_start: date | None
    early_finish: date | None
    late_start: date | None
    late_finish: date | None
    status: AssignmentPlacementStatus
    diagnostic_code: str | None = None

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.snapshot_hash, "snapshot_hash"),
            (self.assignment_id, "assignment_id"),
            (self.activity_id, "activity_id"),
            (self.resource_id, "resource_id"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if not isinstance(self.is_driving, bool):
            raise TypeError("is_driving must be an explicit boolean")
        if not isinstance(self.status, AssignmentPlacementStatus):
            raise TypeError("status must be an AssignmentPlacementStatus")
        dates = (self.early_start, self.early_finish, self.late_start, self.late_finish)
        if any(
            value is not None and (not isinstance(value, date) or isinstance(value, datetime))
            for value in dates
        ):
            raise TypeError("assignment schedule dates must be date-only values or None")
        if self.status is AssignmentPlacementStatus.UNSCHEDULED:
            if any(value is not None for value in dates):
                raise ValueError("unscheduled assignments must not expose calculated dates")
            if not self.diagnostic_code:
                raise ValueError("unscheduled assignments require a diagnostic_code")
        else:
            if self.early_start is None or self.early_finish is None:
                raise ValueError("scheduled assignments require early dates")
            if self.late_start is None or self.late_finish is None:
                raise ValueError("scheduled assignments require late dates")
            if self.early_finish < self.early_start or self.late_finish < self.late_start:
                raise ValueError("assignment finish dates must not precede start dates")
            if self.status is AssignmentPlacementStatus.DELAYED_FOR_CAPACITY and not self.diagnostic_code:
                raise ValueError("capacity-delayed assignments require a diagnostic_code")
            if self.status is AssignmentPlacementStatus.SCHEDULED and self.diagnostic_code is not None:
                raise ValueError("scheduled assignments must not carry a failure diagnostic")
