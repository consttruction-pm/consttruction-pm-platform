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



class SecondaryConstraintError(ValueError):
    """Raised when P6 secondary constraint semantics cannot be represented."""


class SecondaryConstraintType(str, Enum):
    """Oracle P6 Activity.SecondaryConstraintType wire values."""

    START_ON = "Start On"
    START_ON_OR_BEFORE = "Start On or Before"
    START_ON_OR_AFTER = "Start On or After"
    FINISH_ON = "Finish On"
    FINISH_ON_OR_BEFORE = "Finish On or Before"
    FINISH_ON_OR_AFTER = "Finish On or After"
    AS_LATE_AS_POSSIBLE = "As Late As Possible"
    MANDATORY_START = "Mandatory Start"
    MANDATORY_FINISH = "Mandatory Finish"


_SECONDARY_EXECUTABLE_TYPES = frozenset(
    {
        SecondaryConstraintType.START_ON_OR_BEFORE,
        SecondaryConstraintType.START_ON_OR_AFTER,
        SecondaryConstraintType.FINISH_ON_OR_BEFORE,
        SecondaryConstraintType.FINISH_ON_OR_AFTER,
    }
)


@dataclass(frozen=True)
class ActivitySecondaryConstraint:
    activity_id: str
    type: SecondaryConstraintType
    date: date

    def __post_init__(self) -> None:
        if not self.activity_id:
            raise ValueError("activity_id is required")
        if not isinstance(self.type, SecondaryConstraintType):
            raise TypeError("type must be a SecondaryConstraintType")

    def to_activity_constraint(self) -> ActivityConstraint:
        try:
            mapped_type = {
                SecondaryConstraintType.START_ON_OR_BEFORE: ConstraintType.START_NO_LATER_THAN,
                SecondaryConstraintType.START_ON_OR_AFTER: ConstraintType.START_NO_EARLIER_THAN,
                SecondaryConstraintType.FINISH_ON_OR_BEFORE: ConstraintType.FINISH_NO_LATER_THAN,
                SecondaryConstraintType.FINISH_ON_OR_AFTER: ConstraintType.FINISH_NO_EARLIER_THAN,
            }[self.type]
        except KeyError as exc:
            raise SecondaryConstraintError(
                f"{self.type.value!r} is documented by P6 but is not an executable "
                "secondary constraint value in P6 EPPM REST Release 26"
            ) from exc
        return ActivityConstraint(self.activity_id, mapped_type, self.date)


def resolve_secondary_constraint(
    *,
    primary: ActivityConstraint | None,
    secondary: ActivitySecondaryConstraint | None,
) -> ActivityConstraint | None:
    if secondary is None:
        return None
    if primary is None:
        raise SecondaryConstraintError(
            f"secondary constraint for {secondary.activity_id} requires a primary constraint"
        )
    if secondary.type not in _SECONDARY_EXECUTABLE_TYPES:
        raise SecondaryConstraintError(
            f"{secondary.type.value!r} is not permitted as a secondary constraint "
            "in P6 EPPM REST Release 26"
        )
    if primary.activity_id != secondary.activity_id:
        raise SecondaryConstraintError(
            "primary and secondary constraints must target the same activity"
        )
    return secondary.to_activity_constraint()


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

    # P6 semantics: Start/Finish No Earlier Than are early-date constraints.
    # They affect the forward pass and reduce float; they do not move late dates.
    if constraint.type is ConstraintType.START_NO_EARLIER_THAN:
        return late_start

    if constraint.type is ConstraintType.FINISH_NO_EARLIER_THAN:
        return late_start

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


def validate_late_constraint_window(
    constraint: ActivityConstraint,
    start: date,
    finish: date,
    resolver: WorkingTimeResolver,
) -> None:
    """Validate only constraints that govern P6 late dates.

    Start/Finish No Earlier Than are early-date constraints in P6 and therefore
    must not reject a late date that precedes the early-date constraint target.
    Start/Finish No Later Than and Mandatory constraints remain applicable.
    """
    target = _target(constraint, resolver)

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
