from datetime import date
from decimal import Decimal

from construction_pm.scheduling.activity import Activity, ActivityLevelingPriority
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

    # ScheduleResult does not expose a resource-demand ledger. Reproject each
    # activity's typed input assignments by the final scheduled start offset,
    # then aggregate the resulting demand periods against the capacity fixture.
    final_demand_by_day = {day_one: Decimal("0"), day_two: Decimal("0")}
    for activity in leveling_input.forward_activities:
        final_start = result.activities[activity.activity_id].start
        # These fixture demands are single-period assignments on day one.
        # Project them to the final scheduled start directly; the resolver's
        # working_days_between uses exclusive interval semantics for this pair.
        for demand in activity.resource_demands:
            final_period = day_two if final_start == day_two else day_one
            if demand.resource_id == "R1" and final_period in final_demand_by_day:
                final_demand_by_day[final_period] += demand.units
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


def test_public_backward_leveling_moves_linked_activities_without_breaking_ss() -> None:
    from construction_pm.scheduling.relationships import Relationship, RelationshipType

    day_one = date(2026, 10, 1)  # Thursday
    day_two = date(2026, 10, 2)  # Friday
    day_three = date(2026, 10, 5)  # Monday: working day, not Saturday
    demands = (
        ResourceDemand("R1", day_one, Decimal("8"), "A"),
        ResourceDemand("R1", day_one, Decimal("8"), "B"),
    )
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", day_one, day_one, 1, (demands[0],), activity_priority=1),
            LevelingActivity("B", day_one, day_one, 1, (demands[1],), activity_priority=0),
        ),
        backward_activities=(
            BackwardLevelingActivity("A", day_one, day_one, day_three, day_three, (demands[0],), activity_priority=1),
            BackwardLevelingActivity("B", day_one, day_one, day_three, day_three, (demands[1],), activity_priority=0),
        ),
        capacities=(
            ResourceCapacity("R1", day_one, Decimal("16")),
            ResourceCapacity("R1", day_two, Decimal("8")),
        ),
        options=ResourceLevelingOptions(
            preserve_scheduled_early_and_late_dates=False,
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
        project_finish=day_three,
        options=ScheduleOptions(
            level_all_resources=True,
            preserve_scheduled_early_and_late_dates=False,
            priority_list=(PriorityListItem("activity_priority", PrioritySortOrder.ASCENDING),),
        ),
    )

    # Both demands are initially on day one. The valid Monday project finish
    # creates a real late window; the backward proposal advances B's late start
    # to Friday. The final CPM reschedule keeps A on Thursday and B on Friday;
    # this respects SS because B does not start before A.
    assert forward == ()
    assert len(backward) == 1
    assert backward[0].activity_id == "B"
    assert backward[0].advanced_days == 1
    assert backward[0].new_start == day_two
    assert result.activities["A"].start == day_one
    assert result.activities["B"].start == day_two
    assert result.project_finish == day_three

def test_public_leveling_uses_distinct_planned_finish_priority_from_activity():
    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    day_three = date(2026, 10, 5)
    demands = (
        ResourceDemand("R1", day_one, Decimal("8"), "A"),
        ResourceDemand("R1", day_one, Decimal("8"), "B"),
    )
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", day_one, day_one, 2, (demands[0],)),
            LevelingActivity("B", day_one, day_one, 2, (demands[1],)),
        ),
        backward_activities=(
            BackwardLevelingActivity("A", day_one, day_one, day_three, day_three, (demands[0],)),
            BackwardLevelingActivity("B", day_one, day_one, day_three, day_three, (demands[1],)),
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
        (
            Activity("A", 1, planned_finish=day_three),
            Activity("B", 1, planned_finish=day_two),
        ),
        (),
        day_one,
        resolver,
        leveling_input,
        project_finish=day_three,
        options=ScheduleOptions(
            level_all_resources=True,
            level_within_float=True,
            preserve_scheduled_early_and_late_dates=True,
            priority_list=(
                PriorityListItem("planned_finish", PrioritySortOrder.ASCENDING),
            ),
        ),
    )

    assert [shift.activity_id for shift in forward] == ["A"]
    assert backward == ()
    assert result.activities["A"].start == day_two

def test_public_leveling_does_not_infer_planned_finish_after_activity_started():
    import pytest

    from construction_pm.scheduling.activity import ActivityStatus
    from construction_pm.scheduling.resource_leveling import ResourceLevelingError

    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    day_three = date(2026, 10, 5)
    demands = (
        ResourceDemand("R1", day_one, Decimal("8"), "A"),
        ResourceDemand("R1", day_one, Decimal("8"), "B"),
    )
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", day_one, day_one, 2, (demands[0],)),
            LevelingActivity("B", day_one, day_one, 2, (demands[1],)),
        ),
        backward_activities=(
            BackwardLevelingActivity("A", day_one, day_one, day_three, day_three, (demands[0],)),
            BackwardLevelingActivity("B", day_one, day_one, day_three, day_three, (demands[1],)),
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

    with pytest.raises(ResourceLevelingError, match="MISSING_LEVELING_PRIORITY_VALUE"):
        schedule_with_resource_leveling(
            (
                Activity("A", 1, actual_start=day_one, status=ActivityStatus.IN_PROGRESS),
                Activity("B", 1, planned_finish=day_two),
            ),
            (),
            day_one,
            resolver,
            leveling_input,
            project_finish=day_three,
            options=ScheduleOptions(
                level_all_resources=True,
                level_within_float=True,
                preserve_scheduled_early_and_late_dates=True,
                priority_list=(
                    PriorityListItem("planned_finish", PrioritySortOrder.ASCENDING),
                ),
            ),
        )

def test_public_backward_ss_conflict_rolls_back_incompatible_candidate(monkeypatch):
    import construction_pm.scheduling.leveling_scheduler as leveling_scheduler_module
    from construction_pm.scheduling.relationships import Relationship, RelationshipType
    from construction_pm.scheduling.resource_leveling import BackwardLevelingShift

    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    day_three = date(2026, 10, 5)
    demands = (
        ResourceDemand("R1", day_one, Decimal("8"), "A"),
        ResourceDemand("R1", day_one, Decimal("8"), "B"),
    )
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", day_one, day_one, 2, (demands[0],)),
            LevelingActivity("B", day_one, day_one, 2, (demands[1],)),
        ),
        backward_activities=(
            BackwardLevelingActivity("A", day_one, day_one, day_three, day_three, (demands[0],)),
            BackwardLevelingActivity("B", day_one, day_one, day_three, day_three, (demands[1],)),
        ),
        capacities=(
            ResourceCapacity("R1", day_one, Decimal("16")),
            ResourceCapacity("R1", day_two, Decimal("16")),
            ResourceCapacity("R1", day_three, Decimal("0")),
        ),
        options=ResourceLevelingOptions(
            preserve_scheduled_early_and_late_dates=False,
            level_all_resources=True,
        ),
    )
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))

    # The deepest B move would pin B to Thursday while the SS predecessor A is
    # pinned to Friday. The public scheduler must reject that candidate, reduce
    # B's advance limit to the previous feasible step and recalculate CPM.
    proposals = (
        BackwardLevelingShift("A", -1, day_two, day_two, 1),
        BackwardLevelingShift("B", -1, day_two, day_two, 1),
        BackwardLevelingShift("B", -2, day_one, day_one, 2),
    )
    monkeypatch.setattr(
        leveling_scheduler_module,
        "propose_backward_leveling",
        lambda *args, **kwargs: proposals,
    )

    result, forward, backward = schedule_with_resource_leveling(
        (Activity("A", 1), Activity("B", 1)),
        (Relationship("A", "B", RelationshipType.SS),),
        day_one,
        resolver,
        leveling_input,
        project_finish=day_three,
        options=ScheduleOptions(
            level_all_resources=True,
            preserve_scheduled_early_and_late_dates=False,
        ),
    )

    assert forward == ()
    assert {shift.activity_id: shift.advanced_days for shift in backward} == {
        "A": 1,
        "B": 1,
    }
    assert result.activities["A"].start == day_two
    assert result.activities["B"].start == day_two
    assert result.activities["B"].start >= result.activities["A"].start

    # The public scheduler's final capacity gate has passed. Also verify the
    # resulting demand ledger explicitly against the same capacity window.
    from construction_pm.scheduling.leveling_scheduler import _shifted_final_resource_demands

    final_demands = _shifted_final_resource_demands(
        result=result,
        leveling_input=leveling_input,
        resolver=resolver,
    )
    assert all(demand.period == day_two for demand in final_demands)
    assert sum((demand.units for demand in final_demands), Decimal("0")) <= Decimal("16")

def test_public_leveling_maps_activity_leveling_priority_from_activity():
    assert Activity("DEFAULT", 1).leveling_priority is ActivityLevelingPriority.NORMAL
    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    day_three = date(2026, 10, 5)
    demand_top = ResourceDemand("R1", day_one, Decimal("8"), "TOP")
    demand_lowest = ResourceDemand("R1", day_one, Decimal("8"), "LOWEST")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("TOP", day_one, day_one, 2, (demand_top,)),
            LevelingActivity("LOWEST", day_one, day_one, 2, (demand_lowest,)),
        ),
        backward_activities=(
            BackwardLevelingActivity("TOP", day_one, day_one, day_three, day_three, (demand_top,)),
            BackwardLevelingActivity("LOWEST", day_one, day_one, day_three, day_three, (demand_lowest,)),
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
        (
            Activity("TOP", 1, leveling_priority=ActivityLevelingPriority.TOP),
            Activity("LOWEST", 1, leveling_priority=ActivityLevelingPriority.LOWEST),
        ),
        (),
        day_one,
        resolver,
        leveling_input,
        project_finish=day_three,
        options=ScheduleOptions(
            level_all_resources=True,
            level_within_float=True,
            preserve_scheduled_early_and_late_dates=True,
            priority_list=(
                PriorityListItem("activity_leveling_priority", PrioritySortOrder.ASCENDING),
            ),
        ),
    )
    assert [shift.activity_id for shift in forward] == ["LOWEST"]
    assert backward == ()
    assert result.activities["TOP"].start == day_one
    assert result.activities["LOWEST"].start == day_two

