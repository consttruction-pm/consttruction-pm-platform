from datetime import date
from decimal import Decimal

import pytest

from construction_pm.scheduling.leveling_boundary import (
    scheduler_leveling_input_from_options,
)
from construction_pm.scheduling.resource_leveling import (
    BackwardLevelingActivity,
    LevelingActivity,
    ResourceCapacity,
    ResourceDemand,
    ResourceLevelingError,
)
from construction_pm.scheduling.resource_leveling import SortOrder
from construction_pm.scheduling.schedule_options import (
    PriorityListItem,
    PrioritySortOrder,
    ScheduleOptions,
)


def _slices():
    demand = ResourceDemand("R1", date(2026, 10, 5), Decimal("1"), "A1")
    forward = (
        LevelingActivity(
            activity_id="A1",
            start=date(2026, 10, 5),
            finish=date(2026, 10, 5),
            total_float=2,
            resource_demands=(demand,),
        ),
    )
    backward = (
        BackwardLevelingActivity(
            activity_id="A1",
            early_start=date(2026, 10, 5),
            early_finish=date(2026, 10, 5),
            late_start=date(2026, 10, 7),
            late_finish=date(2026, 10, 7),
            resource_demands=(demand,),
        ),
    )
    capacities = (
        ResourceCapacity("R1", date(2026, 10, 5), Decimal("1")),
    )
    return forward, backward, capacities


def test_scheduler_leveling_boundary_maps_p6_options_without_calculating_dates():
    forward, backward, capacities = _slices()
    options = ScheduleOptions(
        level_all_resources=True,
        level_within_float=True,
        min_float_to_preserve=1,
        over_allocation_percentage=25,
        preserve_scheduled_early_and_late_dates=False,
    )

    boundary = scheduler_leveling_input_from_options(
        forward_activities=forward,
        backward_activities=backward,
        capacities=capacities,
        options=options,
    )

    assert boundary.options.level_all_resources is True
    assert boundary.options.level_within_float is True
    assert boundary.options.min_float_to_preserve == Decimal("1")
    assert boundary.options.over_allocation_percentage == Decimal("25")
    assert boundary.options.preserve_scheduled_early_and_late_dates is False
    assert boundary.forward_activities[0].start == date(2026, 10, 5)
    assert boundary.backward_activities[0].late_start == date(2026, 10, 7)


def test_scheduler_leveling_boundary_rejects_mismatched_activity_sets():
    forward, backward, capacities = _slices()
    mismatched = (
        BackwardLevelingActivity(
            activity_id="A2",
            early_start=date(2026, 10, 5),
            early_finish=date(2026, 10, 5),
            late_start=date(2026, 10, 7),
            late_finish=date(2026, 10, 7),
        ),
    )

    with pytest.raises(ValueError, match="activity sets must match"):
        scheduler_leveling_input_from_options(
            forward_activities=forward,
            backward_activities=mismatched,
            capacities=capacities,
            options=ScheduleOptions(),
        )


def test_leveling_activity_rejects_unknown_demand_activity():
    bad = ResourceDemand("R1", date(2026, 10, 5), Decimal("1"), "UNKNOWN")
    with pytest.raises(ResourceLevelingError, match="DEMAND_ACTIVITY_MISMATCH"):
        LevelingActivity(
            activity_id="A1",
            start=date(2026, 10, 5),
            finish=date(2026, 10, 5),
            total_float=2,
            resource_demands=(bad,),
        )


def test_scheduler_leveling_boundary_maps_ordered_priority_list():
    forward, backward, capacities = _slices()
    options = ScheduleOptions(
        priority_list=(
            PriorityListItem("total_float", PrioritySortOrder.ASCENDING),
            PriorityListItem("activity_priority", PrioritySortOrder.DESCENDING),
            PriorityListItem("activity_id", PrioritySortOrder.ASCENDING),
        ),
    )

    boundary = scheduler_leveling_input_from_options(
        forward_activities=forward,
        backward_activities=backward,
        capacities=capacities,
        options=options,
    )

    assert [(item.field_name, item.sort_order) for item in boundary.options.priorities] == [
        ("total_float", SortOrder.ASCENDING),
        ("activity_priority", SortOrder.DESCENDING),
        ("activity_id", SortOrder.ASCENDING),
    ]


def test_scheduler_leveling_boundary_rejects_unsupported_priority_field():
    forward, backward, capacities = _slices()
    options = ScheduleOptions(
        priority_list=(PriorityListItem("resource_id", PrioritySortOrder.ASCENDING),),
    )

    with pytest.raises(ResourceLevelingError, match="UNSUPPORTED_LEVELING_PRIORITY"):
        scheduler_leveling_input_from_options(
            forward_activities=forward,
            backward_activities=backward,
            capacities=capacities,
            options=options,
        )
