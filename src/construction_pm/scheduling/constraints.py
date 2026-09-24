from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Iterable

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
    """Raised when constraints cannot be satisfied simultaneously."""


def _target(constraint: ActivityConstraint, resolver: WorkingTimeResolver) -> date:
    return resolver.normalize_start(constraint.date)


def validate_constraint_set(
    constraints: Iterable[ActivityConstraint],
    duration: int,
    resolver: WorkingTimeResolver,
) -> None:
    """Reject internally contradictory constraints before scheduling.

    This validation is deterministic and activity-local. Relationship-driven
    conflicts are still validated by the forward/backward passes.
    """
    items = sorted(
        constraints,
        key=lambda item: (item.activity_id, item.type.value, item.date),
    )
    by_activity: dict[str, list[ActivityConstraint]] = {}
    for item in items:
        by_activity.setdefault(item.activity_id, []).append(item)

    for activity_id, activity_constraints in by_activity.items():
        start_lower: date | None = None
        start_upper: date | None = None
        finish_lower: date | None = None
        finish_upper: date | None = None
        mandatory_start: date | None = None
        mandatory_finish: date | None = None

        for constraint in activity_constraints:
            target = _target(constraint, resolver)
            if constraint.type is ConstraintType.START_NO_EARLIER_THAN:
                start_lower = max(start_lower, target) if start_lower else target
            elif constraint.type is ConstraintType.START_NO_LATER_THAN:
                start_upper = min(start_upper, target) if start_upper else target
            elif constraint.type is ConstraintType.FINISH_NO_EARLIER_THAN:
                finish_lower = max(finish_lower, target) if finish_lower else target
            elif constraint.type is ConstraintType.FINISH_NO_LATER_THAN:
                finish_upper = min(finish_upper, target) if finish_upper else target
            elif constraint.type is ConstraintType.MANDATORY_START:
                if mandatory_start is not None and mandatory_start != target:
                    raise ConstraintViolation(
                        f"conflicting mandatory starts for {activity_id}"
                    )
                mandatory_start = target
            elif constraint.type is ConstraintType.MANDATORY_FINISH:
                if mandatory_finish is not None and mandatory_finish != target:
                    raise ConstraintViolation(
                        f"conflicting mandatory finishes for {activity_id}"
                    )
                mandatory_finish = target

        if start_lower and start_upper and start_lower > start_upper:
            raise ConstraintViolation(
                f"start constraint window is empty for {activity_id}"
            )
        if finish_lower and finish_upper and finish_lower > finish_upper:
            raise ConstraintViolation(
                f"finish constraint window is empty for {activity_id}"
            )

        if mandatory_start is not None:
            if start_lower and mandatory_start < start_lower:
                raise ConstraintViolation(f"mandatory start conflicts for {activity_id}")
            if start_upper and mandatory_start > start_upper:
                raise ConstraintViolation(f"mandatory start conflicts for {activity_id}")
            mandatory_finish_from_start = resolver.add_working_duration(
                mandatory_start, duration
            )
            if finish_lower and mandatory_finish_from_start < finish_lower:
                raise ConstraintViolation(f"mandatory start conflicts with finish constraint for {activity_id}")
            if finish_upper and mandatory_finish_from_start > finish_upper:
                raise ConstraintViolation(f"mandatory start conflicts with finish constraint for {activity_id}")
            if mandatory_finish is not None and mandatory_finish_from_start != mandatory_finish:
                raise ConstraintViolation(f"mandatory start and finish conflict for {activity_id}")

        if mandatory_finish is not None:
            mandatory_start_from_finish = resolver.subtract_working_duration(
                mandatory_finish, duration
            )
            if start_lower and mandatory_start_from_finish < start_lower:
                raise ConstraintViolation(f"mandatory finish conflicts with start constraint for {activity_id}")
            if start_upper and mandatory_start_from_finish > start_upper:
                raise ConstraintViolation(f"mandatory finish conflicts with start constraint for {activity_id}")

        if start_lower and finish_upper:
            earliest_finish = resolver.add_working_duration(start_lower, duration)
            if earliest_finish > finish_upper:
                raise ConstraintViolation(
                    f"start/finish constraint window is empty for {activity_id}"
                )

        if finish_lower and start_upper:
            latest_finish = resolver.add_working_duration(start_upper, duration)
            if latest_finish < finish_lower:
                raise ConstraintViolation(
                    f"start/finish constraint window is empty for {activity_id}"
                )


def apply_earliest_constraint(
    constraint: ActivityConstraint,
    start: date,
    duration: int,
    resolver: WorkingTimeResolver,
) -> date:
    target = _target(constraint, resolver)

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


def apply_latest_constraint(
    constraint: ActivityConstraint,
    late_start: date,
    duration: int,
    resolver: WorkingTimeResolver,
) -> date:
    target = _target(constraint, resolver)

    if constraint.type is ConstraintType.START_NO_LATER_THAN:
        return min(late_start, target)

    if constraint.type is ConstraintType.FINISH_NO_LATER_THAN:
        latest_start = resolver.subtract_working_duration(target, duration)
        return min(late_start, latest_start)

    if constraint.type is ConstraintType.MANDATORY_START:
        if late_start < target:
            raise ConstraintViolation(
                f"mandatory start for {constraint.activity_id} conflicts with successor/project finish logic"
            )
        return target

    if constraint.type is ConstraintType.MANDATORY_FINISH:
        latest_start = resolver.subtract_working_duration(target, duration)
        if late_start < latest_start:
            raise ConstraintViolation(
                f"mandatory finish for {constraint.activity_id} conflicts with successor/project finish logic"
            )
        return latest_start

    return late_start


def validate_upper_bound(
    constraint: ActivityConstraint,
    start: date,
    finish: date,
    resolver: WorkingTimeResolver,
) -> None:
    """Validate constraints that impose an upper bound during the forward pass."""
    target = _target(constraint, resolver)

    if constraint.type is ConstraintType.START_NO_LATER_THAN and start > target:
        raise ConstraintViolation(
            f"start no later than constraint violated for {constraint.activity_id}"
        )

    if constraint.type is ConstraintType.FINISH_NO_LATER_THAN and finish > target:
        raise ConstraintViolation(
            f"finish no later than constraint violated for {constraint.activity_id}"
        )


def validate_constraint_window(
    constraint: ActivityConstraint,
    start: date,
    finish: date,
    resolver: WorkingTimeResolver,
) -> None:
    target = _target(constraint, resolver)

    if constraint.type is ConstraintType.START_NO_EARLIER_THAN and start < target:
        raise ConstraintViolation(
            f"start no earlier than constraint violated for {constraint.activity_id}"
        )

    if constraint.type is ConstraintType.START_NO_LATER_THAN and start > target:
        raise ConstraintViolation(
            f"start no later than constraint violated for {constraint.activity_id}"
        )

    if constraint.type is ConstraintType.FINISH_NO_EARLIER_THAN and finish < target:
        raise ConstraintViolation(
            f"finish no earlier than constraint violated for {constraint.activity_id}"
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
