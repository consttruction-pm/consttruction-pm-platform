from collections import defaultdict
from datetime import date
from decimal import Decimal

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.leveling_boundary import SchedulerLevelingInput
from construction_pm.scheduling.leveling_scheduler import schedule_with_resource_leveling
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.resource_leveling import (
    BackwardLevelingActivity,
    LevelingActivity,
    ResourceCapacity,
    ResourceDemand,
    ResourceLevelingOptions,
)


def test_linked_leveling_reconstructs_final_resource_demand_by_shifted_period() -> None:
    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    resolver = WorkingTimeResolver(
        WorkingCalendar(
            working_weekdays=frozenset({0, 1, 2, 3, 4}),
            holidays=frozenset(),
        )
    )
    demand_a = ResourceDemand("R1", day_one, Decimal("8"), "A")
    demand_b = ResourceDemand("R1", day_one, Decimal("8"), "B")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", day_one, day_one, 1, (demand_a,)),
            LevelingActivity("B", day_one, day_one, 1, (demand_b,)),
        ),
        backward_activities=(
            BackwardLevelingActivity(
                "A", day_one, day_one, day_two, day_two, (demand_a,)
            ),
            BackwardLevelingActivity(
                "B", day_one, day_one, day_two, day_two, (demand_b,)
            ),
        ),
        capacities=(
            ResourceCapacity("R1", day_one, Decimal("8")),
            ResourceCapacity("R1", day_two, Decimal("16")),
        ),
        options=ResourceLevelingOptions(
            preserve_scheduled_early_and_late_dates=True,
            level_all_resources=True,
        ),
    )

    result, forward, backward = schedule_with_resource_leveling(
        (Activity("A", 1), Activity("B", 1)),
        (Relationship("A", "B", RelationshipType.SS),),
        day_one,
        resolver,
        leveling_input,
    )

    assert len(forward) == 1
    assert backward == ()
    assert result.activities["A"].start == day_two
    assert result.activities["B"].start == day_two

    # Reconstruct demand from each demand's own period and the activity's
    # final CPM displacement. Do not assume every demand occurs only on the
    # activity start date: multi-period resource assignments must retain their
    # period offsets when leveling shifts an activity.
    final_demand_by_resource_period: dict[tuple[str, date], Decimal] = defaultdict(Decimal)
    for activity_input in leveling_input.forward_activities:
        final_start = result.activities[activity_input.activity_id].start
        displacement = resolver.working_days_between(activity_input.start, final_start)
        for demand in activity_input.resource_demands:
            final_period = resolver.add_working_duration(demand.period, displacement + 1)
            final_demand_by_resource_period[(demand.resource_id, final_period)] += demand.units

    capacity_by_resource_period = {
        (capacity.resource_id, capacity.period): capacity.units
        for capacity in leveling_input.capacities
    }
    assert dict(final_demand_by_resource_period) == {("R1", day_two): Decimal("16")}
    assert all(
        units <= capacity_by_resource_period.get(key, Decimal("0"))
        for key, units in final_demand_by_resource_period.items()
    )

def test_linked_leveling_preserves_offsets_for_multi_period_resource_demand() -> None:
    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    day_three = date(2026, 10, 5)
    resolver = WorkingTimeResolver(
        WorkingCalendar(
            working_weekdays=frozenset({0, 1, 2, 3, 4}),
            holidays=frozenset(),
        )
    )
    demands_a = (
        ResourceDemand("R1", day_one, Decimal("8"), "A"),
        ResourceDemand("R1", day_two, Decimal("8"), "A"),
    )
    demands_b = (
        ResourceDemand("R1", day_one, Decimal("8"), "B"),
        ResourceDemand("R1", day_two, Decimal("8"), "B"),
    )
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", day_one, day_two, 2, demands_a),
            LevelingActivity("B", day_one, day_two, 2, demands_b),
        ),
        backward_activities=(
            BackwardLevelingActivity("A", day_one, day_two, day_two, day_three, demands_a),
            BackwardLevelingActivity("B", day_one, day_two, day_two, day_three, demands_b),
        ),
        capacities=(
            ResourceCapacity("R1", day_one, Decimal("8")),
            ResourceCapacity("R1", day_two, Decimal("16")),
            ResourceCapacity("R1", day_three, Decimal("16")),
        ),
        options=ResourceLevelingOptions(
            preserve_scheduled_early_and_late_dates=True,
            level_all_resources=True,
        ),
    )

    result, forward, backward = schedule_with_resource_leveling(
        (Activity("A", 2), Activity("B", 2)),
        (Relationship("A", "B", RelationshipType.SS),),
        day_one,
        resolver,
        leveling_input,
    )

    assert len(forward) == 1
    assert backward == ()
    assert result.activities["A"].start == day_two
    assert result.activities["B"].start == day_two

    # Each activity has demand in two distinct periods. Moving its start by
    # one working day must move both demand periods by one working day while
    # retaining the one-period offset between them.
    final_demand_by_resource_period: dict[tuple[str, date], Decimal] = defaultdict(Decimal)
    for activity_input in leveling_input.forward_activities:
        final_start = result.activities[activity_input.activity_id].start
        displacement = resolver.working_days_between(activity_input.start, final_start)
        for demand in activity_input.resource_demands:
            final_period = resolver.add_working_duration(demand.period, displacement + 1)
            final_demand_by_resource_period[(demand.resource_id, final_period)] += demand.units

    capacity_by_resource_period = {
        (capacity.resource_id, capacity.period): capacity.units
        for capacity in leveling_input.capacities
    }
    assert dict(final_demand_by_resource_period) == {
        ("R1", day_two): Decimal("16"),
        ("R1", day_three): Decimal("16"),
    }
    assert all(
        units <= capacity_by_resource_period.get(key, Decimal("0"))
        for key, units in final_demand_by_resource_period.items()
    )

def test_leveling_rejects_activity_missing_from_scheduler_input():
    import pytest

    from construction_pm.scheduling.resource_leveling import ResourceLevelingError

    day = date(2026, 10, 1)
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    demand = ResourceDemand("R1", day, Decimal("1"), "MISSING")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(LevelingActivity("MISSING", day, day, 0, (demand,)),),
        backward_activities=(BackwardLevelingActivity(
            "MISSING", day, day, day, day, (demand,),
        ),),
        capacities=(ResourceCapacity("R1", day, Decimal("1")),),
        options=ResourceLevelingOptions(level_all_resources=True),
    )
    with pytest.raises(ResourceLevelingError, match="LEVELING_ACTIVITY_NOT_IN_SCHEDULE:MISSING"):
        schedule_with_resource_leveling(
            (Activity("A", 1),), (), day, resolver, leveling_input,
        )


def test_leveling_rejects_duplicate_scheduler_activity_ids():
    import pytest

    from construction_pm.scheduling.resource_leveling import ResourceLevelingError

    day = date(2026, 10, 1)
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    leveling_input = SchedulerLevelingInput(
        forward_activities=(LevelingActivity("A", day, day, 0),),
        backward_activities=(BackwardLevelingActivity("A", day, day, day, day),),
        capacities=(),
        options=ResourceLevelingOptions(),
    )
    with pytest.raises(ResourceLevelingError, match="DUPLICATE_SCHEDULE_ACTIVITY_ID"):
        schedule_with_resource_leveling(
            (Activity("A", 1), Activity("A", 2)), (), day, resolver, leveling_input,
        )


def test_leveling_rejects_empty_scheduler_activity_set():
    import pytest

    from construction_pm.scheduling.resource_leveling import ResourceLevelingError

    day = date(2026, 10, 1)
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    leveling_input = SchedulerLevelingInput(
        forward_activities=(),
        backward_activities=(),
        capacities=(),
        options=ResourceLevelingOptions(),
    )
    with pytest.raises(ResourceLevelingError, match="SCHEDULE_ACTIVITIES_EMPTY"):
        schedule_with_resource_leveling((), (), day, resolver, leveling_input)
