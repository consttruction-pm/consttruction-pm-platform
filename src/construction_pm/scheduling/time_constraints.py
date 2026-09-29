from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .calendar_context import CalendarResolverRegistry
from .time_calendar import TimeAwareWorkingTimeResolver
from .time_unit_resolver import resolve_calendar_aware
from .time_duration import DurationUnit, TimeQuantity


class TimeConstraintType(str, Enum):
    START_NO_EARLIER_THAN = "START_NO_EARLIER_THAN"
    START_NO_LATER_THAN = "START_NO_LATER_THAN"
    FINISH_NO_EARLIER_THAN = "FINISH_NO_EARLIER_THAN"
    FINISH_NO_LATER_THAN = "FINISH_NO_LATER_THAN"
    MANDATORY_START = "MANDATORY_START"
    MANDATORY_FINISH = "MANDATORY_FINISH"


@dataclass(frozen=True)
class TimeActivityConstraint:
    activity_id: str
    type: TimeConstraintType
    target: datetime

    def __post_init__(self) -> None:
        if not self.activity_id:
            raise ValueError("activity_id is required")


class TimeConstraintViolation(ValueError):
    """Raised when time-aware activity constraints cannot be satisfied."""


def _resolver(activity, registry: CalendarResolverRegistry) -> TimeAwareWorkingTimeResolver:
    return resolve_calendar_aware(registry, activity.calendar_context.effective_activity())


def apply_time_earliest_constraints(
    activity,
    start: datetime,
    duration: TimeQuantity,
    constraints: list[TimeActivityConstraint],
    registry: CalendarResolverRegistry,
) -> datetime:
    resolver = _resolver(activity, registry)
    result = start
    for item in sorted(constraints, key=lambda x: (x.type.value, x.target)):
        if item.activity_id != activity.id:
            continue
        target = resolver.normalize_start(item.target)
        if item.type is TimeConstraintType.START_NO_EARLIER_THAN:
            result = max(result, target)
        elif item.type is TimeConstraintType.FINISH_NO_EARLIER_THAN:
            result = max(result, resolver.subtract_duration(target, duration))
        elif item.type is TimeConstraintType.MANDATORY_START:
            if result > target:
                raise TimeConstraintViolation(f"mandatory start conflicts for {activity.id}")
            result = target
        elif item.type is TimeConstraintType.MANDATORY_FINISH:
            required = resolver.subtract_duration(target, duration)
            if result > required:
                raise TimeConstraintViolation(f"mandatory finish conflicts for {activity.id}")
            result = required
    return result


def validate_time_early_window(
    activity,
    start: datetime,
    finish: datetime,
    constraints: list[TimeActivityConstraint],
    registry: CalendarResolverRegistry,
) -> None:
    resolver = _resolver(activity, registry)
    for item in constraints:
        if item.activity_id != activity.id:
            continue
        target = resolver.normalize_start(item.target)
        if item.type is TimeConstraintType.START_NO_LATER_THAN and start > target:
            raise TimeConstraintViolation(f"start no later than violated for {activity.id}")
        if item.type is TimeConstraintType.FINISH_NO_LATER_THAN and finish > target:
            raise TimeConstraintViolation(f"finish no later than violated for {activity.id}")
        if item.type is TimeConstraintType.MANDATORY_START and start != target:
            raise TimeConstraintViolation(f"mandatory start violated for {activity.id}")
        if item.type is TimeConstraintType.MANDATORY_FINISH and finish != target:
            raise TimeConstraintViolation(f"mandatory finish violated for {activity.id}")


def apply_time_latest_constraints(
    activity,
    late_start: datetime,
    duration: TimeQuantity,
    constraints: list[TimeActivityConstraint],
    registry: CalendarResolverRegistry,
) -> datetime:
    resolver = _resolver(activity, registry)
    result = late_start
    for item in sorted(constraints, key=lambda x: (x.type.value, x.target)):
        if item.activity_id != activity.id:
            continue
        target = resolver.normalize_start(item.target)
        if item.type in {
            TimeConstraintType.START_NO_EARLIER_THAN,
            TimeConstraintType.FINISH_NO_EARLIER_THAN,
        }:
            continue
        if item.type is TimeConstraintType.START_NO_LATER_THAN:
            result = min(result, target)
        elif item.type is TimeConstraintType.FINISH_NO_LATER_THAN:
            result = min(result, resolver.subtract_duration(target, duration))
        elif item.type is TimeConstraintType.MANDATORY_START:
            if result < target:
                raise TimeConstraintViolation(f"mandatory start conflicts for {activity.id}")
            result = target
        elif item.type is TimeConstraintType.MANDATORY_FINISH:
            required = _subtract_duration(target, duration, resolver)
            if result < required:
                raise TimeConstraintViolation(f"mandatory finish conflicts for {activity.id}")
            result = required
    return result


def validate_time_late_window(
    activity,
    start: datetime,
    finish: datetime,
    constraints: list[TimeActivityConstraint],
    registry: CalendarResolverRegistry,
) -> None:
    resolver = _resolver(activity, registry)
    for item in constraints:
        if item.activity_id != activity.id:
            continue
        target = resolver.normalize_start(item.target)
        if item.type is TimeConstraintType.START_NO_LATER_THAN and start > target:
            raise TimeConstraintViolation(f"late start no later than violated for {activity.id}")
        if item.type is TimeConstraintType.FINISH_NO_LATER_THAN and finish > target:
            raise TimeConstraintViolation(f"late finish no later than violated for {activity.id}")
        if item.type is TimeConstraintType.MANDATORY_START and start != target:
            raise TimeConstraintViolation(f"late mandatory start violated for {activity.id}")
        if item.type is TimeConstraintType.MANDATORY_FINISH and finish != target:
            raise TimeConstraintViolation(f"late mandatory finish violated for {activity.id}")
