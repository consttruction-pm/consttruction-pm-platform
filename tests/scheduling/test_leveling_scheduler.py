from datetime import date

from construction_pm.scheduling.constraints import ActivityConstraint, ConstraintType
from construction_pm.scheduling.leveling_scheduler import (
    backward_leveling_constraints,
    forward_leveling_constraints,
    merge_leveling_constraints,
)
from construction_pm.scheduling.resource_leveling import (
    BackwardLevelingShift,
    LevelingShift,
)


def test_forward_leveling_becomes_start_lower_bound() -> None:
    shifts = (
        LevelingShift(
            activity_id="A",
            shift_working_days=2,
            new_start=date(2026, 10, 5),
            new_finish=date(2026, 10, 7),
            consumed_float=2,
            remaining_float=3,
        ),
    )

    assert forward_leveling_constraints(shifts) == (
        ActivityConstraint(
            activity_id="A",
            type=ConstraintType.START_NO_EARLIER_THAN,
            date=date(2026, 10, 5),
        ),
    )


def test_backward_leveling_becomes_start_upper_bound() -> None:
    shifts = (
        BackwardLevelingShift(
            activity_id="A",
            shift_working_days=-2,
            new_start=date(2026, 10, 5),
            new_finish=date(2026, 10, 7),
            advanced_days=2,
        ),
    )

    assert backward_leveling_constraints(shifts) == (
        ActivityConstraint(
            activity_id="A",
            type=ConstraintType.START_NO_LATER_THAN,
            date=date(2026, 10, 5),
        ),
    )


def test_zero_movement_does_not_create_leveling_constraint() -> None:
    forward = (
        LevelingShift(
            activity_id="A",
            shift_working_days=0,
            new_start=date(2026, 10, 1),
            new_finish=date(2026, 10, 3),
            consumed_float=0,
            remaining_float=3,
        ),
    )
    backward = (
        BackwardLevelingShift(
            activity_id="B",
            shift_working_days=0,
            new_start=date(2026, 10, 8),
            new_finish=date(2026, 10, 10),
            advanced_days=0,
        ),
    )
    base = (
        ActivityConstraint(
            activity_id="C",
            type=ConstraintType.START_NO_EARLIER_THAN,
            date=date(2026, 10, 2),
        ),
    )

    assert forward_leveling_constraints(forward) == ()
    assert backward_leveling_constraints(backward) == ()
    assert merge_leveling_constraints(base, forward=forward, backward=backward) == base
