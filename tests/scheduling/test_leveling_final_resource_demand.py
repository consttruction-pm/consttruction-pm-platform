from collections import defaultdict
from datetime import date
from decimal import Decimal

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.leveling_boundary import SchedulerLevelingInput
from construction_pm.scheduling.leveling_scheduler import schedule_with_resource_leveling
from construction_pm.scheduling.relationships import Relationship, RelationshipType
from construction_pm.scheduling.resource_leveling import (
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
        backward_activities=(),
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
            final_period = resolver.add_working_duration(demand.period, displacement)
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
