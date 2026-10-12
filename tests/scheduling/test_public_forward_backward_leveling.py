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
from construction_pm.scheduling.schedule_options import (
    PriorityListItem,
    PrioritySortOrder,
    ScheduleOptions,
)


def test_public_options_run_forward_and_backward_leveling_then_recalculate_cpm() -> None:
    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    demands = (
        ResourceDemand("R1", day_one, Decimal("8"), "A"),
        ResourceDemand("R1", day_one, Decimal("8"), "B"),
    )
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", day_one, day_one, 1, (demands[0],), activity_priority=0),
            LevelingActivity("B", day_one, day_one, 1, (demands[1],), activity_priority=1),
        ),
        backward_activities=(
            BackwardLevelingActivity("A", day_one, day_one, day_two, day_two, (demands[0],), activity_priority=1),
            BackwardLevelingActivity("B", day_one, day_one, day_two, day_two, (demands[1],), activity_priority=0),
        ),
        capacities=(
            ResourceCapacity("R1", day_one, Decimal("8")),
            ResourceCapacity("R1", day_two, Decimal("8")),
        ),
        options=ResourceLevelingOptions(
            preserve_scheduled_early_and_late_dates=True,
            level_all_resources=True,
        ),
    )
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))

    result, forward, backward = schedule_with_resource_leveling(
        (Activity("A", 1), Activity("B", 1)),
        (),
        day_one,
        resolver,
        leveling_input,
        project_finish=date(2026, 10, 3),
        options=ScheduleOptions(
            level_all_resources=True,
            preserve_scheduled_early_and_late_dates=False,
            priority_list=(PriorityListItem("activity_priority", PrioritySortOrder.ASCENDING),),
        ),
    )

    # The forward pass prioritizes A; the backward pass prioritizes B. This
    # exercises both public passes without letting the backward pass cancel
    # the same activity's forward shift.
    assert len(forward) == 1
    assert forward[0].activity_id == "A"
    assert len(backward) == 1
    assert backward[0].activity_id == "B"
    assert backward[0].advanced_days == 1
    assert {key: value.start for key, value in result.activities.items()} == {
        "A": day_two,
        "B": day_one,
    }
    assert result.project_finish == day_two
    final_demand_by_day = {
        day: sum(
            demand.units
            for activity_id, demand in (("A", demands[0]), ("B", demands[1]))
            if result.activities[activity_id].start == day
        )
        for day in (day_one, day_two)
    }
    capacity_by_day = {day_one: Decimal("8"), day_two: Decimal("8")}
    assert final_demand_by_day == {
        day_one: Decimal("8"),
        day_two: Decimal("8"),
    }
    assert all(final_demand_by_day[day] <= capacity_by_day[day] for day in capacity_by_day)
    assert set(result.floats) == {"A", "B"}
    for activity_id, float_result in result.floats.items():
        assert float_result.early_start == result.early_activities[activity_id].start
        assert float_result.early_finish == result.early_activities[activity_id].finish
        assert float_result.late_start == result.late_activities[activity_id].start
        assert float_result.late_finish == result.late_activities[activity_id].finish



def test_public_forward_backward_leveling_recalculates_linked_cpm_and_capacity() -> None:
    from construction_pm.scheduling.relationships import Relationship, RelationshipType

    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    demands = (
        ResourceDemand("R1", day_one, Decimal("8"), "A"),
        ResourceDemand("R1", day_one, Decimal("8"), "B"),
    )
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", day_one, day_one, 1, (demands[0],), activity_priority=0),
            LevelingActivity("B", day_one, day_one, 1, (demands[1],), activity_priority=1),
        ),
        backward_activities=(
            BackwardLevelingActivity("A", day_one, day_one, day_two, day_two, (demands[0],), activity_priority=1),
            BackwardLevelingActivity("B", day_one, day_one, day_two, day_two, (demands[1],), activity_priority=0),
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
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))

    result, forward, backward = schedule_with_resource_leveling(
        (Activity("A", 1), Activity("B", 1)),
        (Relationship("A", "B", RelationshipType.SS),),
        day_one,
        resolver,
        leveling_input,
        project_finish=date(2026, 10, 3),
        options=ScheduleOptions(
            level_all_resources=True,
            preserve_scheduled_early_and_late_dates=False,
            priority_list=(PriorityListItem("activity_priority", PrioritySortOrder.ASCENDING),),
        ),
    )

    # The forward pass shifts A; linked CPM then moves B to day two via SS.
    # The backward pass must honor those recalculated early dates rather than
    # proposing a move that violates the relationship. Day two is sized for both.
    assert [shift.activity_id for shift in forward] == ["A"]
    # The backward pass runs against the relationship-constrained intermediate
    # schedule. It must not propose moving B ahead of A's SS-constrained start.
    assert backward == ()
    assert result.activities["A"].start == day_two
    assert result.activities["B"].start == day_two
    assert result.activities["A"].finish == day_two
    assert result.activities["B"].finish == day_two
    assert result.project_finish == day_two

    final_demand_by_day = {
        day: sum(
            demand.units
            for activity_id, demand in (("A", demands[0]), ("B", demands[1]))
            if result.activities[activity_id].start == day
        )
        for day in (day_one, day_two)
    }
    capacity_by_day = {day_one: Decimal("8"), day_two: Decimal("16")}
    assert final_demand_by_day == {
        day_one: Decimal("0"),
        day_two: Decimal("16"),
    }
    assert all(final_demand_by_day[day] <= capacity_by_day[day] for day in capacity_by_day)
    assert set(result.floats) == {"A", "B"}
    for activity_id, float_result in result.floats.items():
        assert float_result.early_start == result.early_activities[activity_id].start
        assert float_result.early_finish == result.early_activities[activity_id].finish
        assert float_result.late_start == result.late_activities[activity_id].start
        assert float_result.late_finish == result.late_activities[activity_id].finish
        assert float_result.total_float == 0
        assert float_result.critical is True
