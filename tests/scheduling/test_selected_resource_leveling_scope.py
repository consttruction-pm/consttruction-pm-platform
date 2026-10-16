from datetime import date
from decimal import Decimal

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.leveling_boundary import SchedulerLevelingInput
from construction_pm.scheduling.leveling_scheduler import schedule_with_resource_leveling
from construction_pm.scheduling.resource_leveling import (
    BackwardLevelingActivity,
    LevelingActivity,
    ResourceCapacity,
    ResourceDemand,
    ResourceLevelingOptions,
)
from construction_pm.scheduling.schedule_options import ScheduleOptions


def test_public_resource_list_limits_which_resource_overloads_trigger_leveling() -> None:
    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    demands = (
        ResourceDemand("R1", day_one, Decimal("8"), "A"),
        ResourceDemand("R1", day_one, Decimal("8"), "B"),
        ResourceDemand("R2", day_one, Decimal("8"), "C"),
        ResourceDemand("R2", day_one, Decimal("8"), "D"),
    )
    forward = (
        LevelingActivity("A", day_one, day_one, 1, (demands[0],)),
        LevelingActivity("B", day_one, day_one, 1, (demands[1],)),
        LevelingActivity("C", day_one, day_one, 1, (demands[2],)),
        LevelingActivity("D", day_one, day_one, 1, (demands[3],)),
    )
    backward = (
        BackwardLevelingActivity("A", day_one, day_one, day_two, day_two, (demands[0],)),
        BackwardLevelingActivity("B", day_one, day_one, day_two, day_two, (demands[1],)),
        BackwardLevelingActivity("C", day_one, day_one, day_two, day_two, (demands[2],)),
        BackwardLevelingActivity("D", day_one, day_one, day_two, day_two, (demands[3],)),
    )
    capacities = (
        ResourceCapacity("R1", day_one, Decimal("8")),
        ResourceCapacity("R1", day_two, Decimal("8")),
        ResourceCapacity("R2", day_one, Decimal("8")),
        ResourceCapacity("R2", day_two, Decimal("8")),
    )
    leveling_input = SchedulerLevelingInput(
        forward,
        backward,
        capacities,
        ResourceLevelingOptions(
            preserve_scheduled_early_and_late_dates=True,
            level_all_resources=False,
            level_within_float=True,
            resource_ids=("R1",),
        ),
    )
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))

    result, forward_shifts, backward_shifts = schedule_with_resource_leveling(
        (Activity("A", 1), Activity("B", 1), Activity("C", 1), Activity("D", 1)),
        (),
        day_one,
        resolver,
        leveling_input,
        project_finish=date(2026, 10, 3),
        options=ScheduleOptions(
            level_all_resources=False,
            resource_list=("R1",),
            level_within_float=True,
            preserve_scheduled_early_and_late_dates=True,
        ),
    )

    assert [shift.activity_id for shift in forward_shifts] == ["A"]
    assert backward_shifts == ()
    assert result.activities["A"].start == day_two
    assert result.activities["B"].start == day_one
    # R2 is overloaded too, but it is not selected and must not trigger shifts.
    assert result.activities["C"].start == day_one
    assert result.activities["D"].start == day_one