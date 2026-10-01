from __future__ import annotations

from datetime import date

from .constraints import ActivityConstraint, ConstraintType
from .resource_leveling import BackwardLevelingShift, LevelingShift


def forward_leveling_constraints(
    shifts: tuple[LevelingShift, ...] | list[LevelingShift],
) -> tuple[ActivityConstraint, ...]:
    """Translate accepted forward leveling movement into scheduler lower bounds.

    The scheduler remains responsible for applying relationships, calendars,
    constraints, and CPM. A leveling proposal never overwrites ScheduledActivity
    dates directly.
    """
    return tuple(
        ActivityConstraint(
            activity_id=shift.activity_id,
            type=ConstraintType.START_NO_EARLIER_THAN,
            date=shift.new_start,
        )
        for shift in sorted(shifts, key=lambda item: (item.activity_id, item.shift_working_days))
        if shift.shift_working_days > 0
    )


def backward_leveling_constraints(
    shifts: tuple[BackwardLevelingShift, ...] | list[BackwardLevelingShift],
) -> tuple[ActivityConstraint, ...]:
    """Translate accepted backward leveling movement into scheduler upper bounds."""
    return tuple(
        ActivityConstraint(
            activity_id=shift.activity_id,
            type=ConstraintType.START_NO_LATER_THAN,
            date=shift.new_start,
        )
        for shift in sorted(shifts, key=lambda item: (item.activity_id, item.shift_working_days))
        if shift.advanced_days > 0
    )


def merge_leveling_constraints(
    base_constraints: tuple[ActivityConstraint, ...] | list[ActivityConstraint],
    *,
    forward: tuple[LevelingShift, ...] | list[LevelingShift] = (),
    backward: tuple[BackwardLevelingShift, ...] | list[BackwardLevelingShift] = (),
) -> tuple[ActivityConstraint, ...]:
    """Compose scheduler-owned leveling bounds with existing project constraints."""
    return tuple(base_constraints) + forward_leveling_constraints(forward) + backward_leveling_constraints(backward)
