from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from .calendar import WorkingTimeResolver


class ConstraintType(str, Enum):
    START_NO_EARLIER_THAN = "START_NO_EARLIER_THAN"
    START_NO_LATER_THAN = "START_NO_LATER_THAN"
    FINISH_NO_EARLIER_THAN = "FINISH_NO_EARLIER_THAN"
    FINISH_NO_LATER_THAN = "FINISH_NO_LATER_THAN"
    MANDATORY_START = "MANDATORY_START"
    MANDATORY_FINISH = "MANDATORY_FINISH"


@dataclass(frozen=True)
class ActivityConstraint:
    activity_id: str
    type: ConstraintType
    date: date

    def __post_init__(self) -> None:
        if not self.activity_id:
            raise ValueError("activity_id is required")


class ConstraintViolation(ValueError):
    """Raised when a mandatory or upper-bound constraint cannot be satisfied."""


def apply_earliest_constraint(
    constraint: ActivityConstraint,
    start: date,
    duration: int,
    resolver: WorkingTimeResolver,
) -> date:
    target = resolver.normalize_start(constraint.date)

    if constraint.type is ConstraintType.START_NO_EARLIER_THAN:
        return max(start, target)

    if constraint.type is ConstraintType.FINISH_NO_EARLIER_THAN:
        required_start = resolver.subtract_working_duration(target, duration)
        return max(start, required_start)

    if constraint.type is ConstraintType.MANDATORY_START:
        if start > target:
            raise ConstraintViolation(
                f"mandatory start for {constraint.activity_id} is earlier than predecessor logic"
            )
        return target

    if constraint.type is ConstraintType.MANDATORY_FINISH:
        required_start = resolver.subtract_working_duration(target, duration)
        if start > required_start:
            raise ConstraintViolation(
                f"mandatory finish for {constraint.activity_id} cannot be satisfied"
            )
        return required_start

    return start


def validate_upper_bound(
    constraint: ActivityConstraint,
    start: date,
    finish: date,
    resolver: WorkingTimeResolver,
) -> None:
    target = resolver.normalize_start(constraint.date)

    if constraint.type is ConstraintType.START_NO_LATER_THAN and start > target:
        raise ConstraintViolation(
            f"start no later than constraint violated for {constraint.activity_id}"
        )

    if constraint.type is ConstraintType.FINISH_NO_LATER_THAN and finish > target:
        raise ConstraintViolation(
            f"finish no later than constraint violated for {constraint.activity_id}"
        )

    if constraint.type is ConstraintType.MANDATORY_START and start != target:
        raise ConstraintViolation(
            f"mandatory start constraint violated for {constraint.activity_id}"
        )

    if constraint.type is ConstraintType.MANDATORY_FINISH and finish != target:
        raise ConstraintViolation(
            f"mandatory finish constraint violated for {constraint.activity_id}"
        )
