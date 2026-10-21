from datetime import date

import pytest
from construction_pm.scheduling.relationships import RelationshipType

from construction_pm.scheduling.constraints import ActivityConstraint, ConstraintType
from construction_pm.scheduling.leveling_scheduler import (
    _order_backward_leveling_candidates,
    backward_leveling_constraints,
    forward_leveling_constraints,
    merge_leveling_constraints,
)
from construction_pm.scheduling.resource_leveling import (
    BackwardLevelingActivity,
    BackwardLevelingShift,
    LevelingShift,
    ResourceDemand,
    ResourceCapacity,
    ResourceLevelingOptions,
)
from construction_pm.scheduling.leveling_boundary import SchedulerLevelingInput
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver


def test_backward_candidate_order_preserves_proposal_priority_for_equal_advances() -> None:
    """Equal-size moves retain the scheduler's P6-prioritized proposal order."""
    proposed = (
        BackwardLevelingShift(
            activity_id="B",
            shift_working_days=-1,
            new_start=date(2026, 10, 2),
            new_finish=date(2026, 10, 2),
            advanced_days=1,
        ),
        BackwardLevelingShift(
            activity_id="A",
            shift_working_days=-1,
            new_start=date(2026, 10, 2),
            new_finish=date(2026, 10, 2),
            advanced_days=1,
        ),
        BackwardLevelingShift(
            activity_id="B",
            shift_working_days=-2,
            new_start=date(2026, 10, 1),
            new_finish=date(2026, 10, 1),
            advanced_days=2,
        ),
    )

    ordered = _order_backward_leveling_candidates(proposed)

    assert [(item.activity_id, item.advanced_days) for item in ordered] == [
        ("B", 1),
        ("A", 1),
        ("B", 2),
    ]


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


def _resource_leveling_input(*, preserve: bool, capacity_day_two: str = "8") -> SchedulerLevelingInput:
    demands = (
        ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "A"),
        ResourceDemand("R1", date(2026, 10, 1), Decimal("8"), "B"),
    )
    forward = (
        LevelingActivity("A", date(2026, 10, 1), date(2026, 10, 1), 1, (demands[0],)),
        LevelingActivity("B", date(2026, 10, 1), date(2026, 10, 1), 1, (demands[1],)),
    )
    backward = (
        BackwardLevelingActivity("A", date(2026, 10, 1), date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 2), (demands[0],)),
        BackwardLevelingActivity("B", date(2026, 10, 1), date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 2), (demands[1],)),
    )
    capacities = (
        ResourceCapacity("R1", date(2026, 10, 1), Decimal("8")),
        ResourceCapacity("R1", date(2026, 10, 2), Decimal(capacity_day_two)),
    )
    return SchedulerLevelingInput(forward, backward, capacities, ResourceLevelingOptions(
        preserve_scheduled_early_and_late_dates=preserve, level_all_resources=True,
    ))


def _run_resource_leveling(preserve: bool):
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    return schedule_with_resource_leveling(
        (Activity("A", 1), Activity("B", 1)), (), date(2026, 10, 1), resolver,
        _resource_leveling_input(preserve=preserve), project_finish=date(2026, 10, 3),
    )


def test_resource_leveling_preserve_dates_runs_forward_only():
    result, forward, backward = _run_resource_leveling(True)
    assert len(forward) == 1
    assert backward == ()
    assert sorted(item.start for item in result.activities.values()) == [date(2026, 10, 1), date(2026, 10, 2)]


def test_resource_leveling_without_preserve_runs_backward_from_late_dates():
    result, forward, backward = _run_resource_leveling(False)
    assert len(forward) == 1
    assert len(backward) == 1
    assert backward[0].advanced_days == 1
    # The forward-shifted activity stays on day two; the backward pass moves
    # the other activity to day one instead of cancelling the forward shift.
    assert sorted(item.start for item in result.activities.values()) == [date(2026, 10, 1), date(2026, 10, 2)]


def test_backward_exact_constraints_pin_accepted_start() -> None:
    shifts = (
        BackwardLevelingShift(
            activity_id="A",
            shift_working_days=-2,
            new_start=date(2026, 10, 5),
            new_finish=date(2026, 10, 7),
            advanced_days=2,
        ),
    )

    from construction_pm.scheduling.leveling_scheduler import backward_leveling_exact_constraints

    assert backward_leveling_exact_constraints(shifts) == (
        ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, date(2026, 10, 5)),
        ActivityConstraint("A", ConstraintType.START_NO_LATER_THAN, date(2026, 10, 5)),
    )


def test_backward_exact_constraints_keep_existing_base_constraints_separate() -> None:
    base = (
        ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, date(2026, 10, 8)),
    )
    shifts = (
        BackwardLevelingShift(
            activity_id="A",
            shift_working_days=-1,
            new_start=date(2026, 10, 7),
            new_finish=date(2026, 10, 8),
            advanced_days=1,
        ),
    )

    from construction_pm.scheduling.leveling_scheduler import backward_leveling_exact_constraints

    assert base + backward_leveling_exact_constraints(shifts) == (
        ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, date(2026, 10, 8)),
        ActivityConstraint("A", ConstraintType.START_NO_EARLIER_THAN, date(2026, 10, 7)),
        ActivityConstraint("A", ConstraintType.START_NO_LATER_THAN, date(2026, 10, 7)),
    )

def test_schedule_options_map_all_authoritative_leveling_fields() -> None:
    from construction_pm.scheduling.leveling_boundary import (
        scheduler_leveling_input_from_options,
    )
    from construction_pm.scheduling.schedule_options import ScheduleOptions

    base = _resource_leveling_input(preserve=True)
    options = ScheduleOptions(
        level_all_resources=True,
        level_within_float=True,
        min_float_to_preserve=2,
        over_allocation_percentage=12.5,
        resource_list=("R1", "R2"),
        preserve_scheduled_early_and_late_dates=True,
    )

    mapped = scheduler_leveling_input_from_options(
        forward_activities=base.forward_activities,
        backward_activities=base.backward_activities,
        capacities=base.capacities,
        options=options,
    )

    assert mapped.options.level_all_resources is True
    assert mapped.options.level_within_float is True
    assert mapped.options.min_float_to_preserve == Decimal("2")
    assert mapped.options.over_allocation_percentage == Decimal("12.5")
    assert mapped.options.resource_ids == ("R1", "R2")
    assert mapped.options.preserve_scheduled_early_and_late_dates is True


def test_schedule_options_leveling_path_uses_typed_boundary() -> None:
    from construction_pm.scheduling.schedule_options import ScheduleOptions

    base = _resource_leveling_input(preserve=True)
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))

    result, forward, backward = schedule_with_resource_leveling(
        (Activity("A", 1), Activity("B", 1)), (), date(2026, 10, 1), resolver,
        base,
        project_finish=date(2026, 10, 3),
        options=ScheduleOptions(
            level_all_resources=True,
            level_within_float=True,
            min_float_to_preserve=0,
            resource_list=("R1",),
            preserve_scheduled_early_and_late_dates=True,
        ),
    )

    # The ScheduleOptions path reaches the authoritative leveling engine.
    # A real one-working-day offset resolves the overload in one shift.
    assert len(forward) == 1
    assert forward[0].activity_id == "A"
    assert forward[0].new_start == date(2026, 10, 2)
    assert backward == ()
    assert set(result.activities) == {"A", "B"}



def test_public_leveling_orchestration_preserves_configured_minimum_float() -> None:
    import pytest

    from construction_pm.scheduling.resource_leveling import ResourceLevelingError
    from construction_pm.scheduling.schedule_options import ScheduleOptions

    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    # Both activities demand 8 units on day one, but capacity is only 8.
    # Preserving one day of float leaves no legal shift, so the final-load guard
    # must reject this infeasible schedule instead of silently accepting overload.
    with pytest.raises(ResourceLevelingError, match="FINAL_RESOURCE_OVERALLOCATION"):
        schedule_with_resource_leveling(
            (Activity("A", 1), Activity("B", 1)),
            (),
            date(2026, 10, 1),
            resolver,
            _resource_leveling_input(preserve=True),
            project_finish=date(2026, 10, 3),
            options=ScheduleOptions(
                level_all_resources=True,
                level_within_float=True,
                min_float_to_preserve=1,
                preserve_scheduled_early_and_late_dates=True,
            ),
        )



def test_linked_resource_leveling_recalculates_relationships_and_cpm_output() -> None:
    from construction_pm.scheduling.relationships import Relationship, RelationshipType

    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    activities = (Activity("A", 1), Activity("B", 1))
    relationships = (Relationship("A", "B", RelationshipType.SS),)

    capacity_day_two = Decimal("16")
    leveling_input = _resource_leveling_input(
        preserve=True, capacity_day_two=str(capacity_day_two)
    )
    result, forward, backward = schedule_with_resource_leveling(
        activities,
        relationships,
        date(2026, 10, 1),
        resolver,
        leveling_input,
    )

    # Day one is overloaded (16 units against capacity 8); after the SS-linked
    # activities move together, day two explicitly has capacity for both (16).
    # Accepted leveling movement must flow back through the ordinary CPM scheduler.
    assert len(forward) == 1
    assert backward == ()
    # The accepted A shift must be propagated through the SS dependency by
    # the ordinary CPM scheduler, not merely reflected in leveling metadata.
    assert result.activities["A"].start == date(2026, 10, 2)
    assert result.activities["B"].start == date(2026, 10, 2)
    assert result.activities["A"].finish == date(2026, 10, 2)
    assert result.activities["B"].finish == date(2026, 10, 2)
    assert result.project_finish == date(2026, 10, 2)
    final_daily_demand_by_day = {
        day: sum(
            demand.units
            for activity_input in leveling_input.forward_activities
            for demand in activity_input.resource_demands
            if result.activities[activity_input.activity_id].start == day
        )
        for day in (date(2026, 10, 1), date(2026, 10, 2))
    }
    capacity_by_day = {
        capacity.period: capacity.units
        for capacity in leveling_input.capacities
        if capacity.resource_id == "R1"
    }
    assert final_daily_demand_by_day == {
        date(2026, 10, 1): Decimal("0"),
        date(2026, 10, 2): Decimal("16"),
    }
    assert all(
        final_daily_demand_by_day[day] <= capacity_by_day[day]
        for day in final_daily_demand_by_day
    )
    assert set(result.floats) == {"A", "B"}
    for activity_id, float_result in result.floats.items():
        early = result.early_activities[activity_id]
        late = result.late_activities[activity_id]
        assert float_result.early_start == early.start
        assert float_result.early_finish == early.finish
        assert float_result.late_start == late.start
        assert float_result.late_finish == late.finish
        assert float_result.total_float == 0
        assert early.start == date(2026, 10, 2)
        assert early.finish == date(2026, 10, 2)
        assert late.start == date(2026, 10, 2)
        assert late.finish == date(2026, 10, 2)


def test_final_resource_validation_shifts_demands_by_signed_working_days():
    from types import SimpleNamespace

    import pytest

    from construction_pm.scheduling.leveling_scheduler import _validate_final_resource_load
    from construction_pm.scheduling.resource_leveling import ResourceLevelingError

    thursday = date(2026, 10, 1)
    friday = date(2026, 10, 2)
    monday = date(2026, 10, 5)
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    demand = ResourceDemand("R1", thursday, Decimal("8"), "A")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(LevelingActivity("A", thursday, thursday, 1, (demand,)),),
        backward_activities=(
            BackwardLevelingActivity("A", thursday, thursday, thursday, thursday, (demand,)),
        ),
        capacities=(
            ResourceCapacity("R1", thursday, Decimal("8")),
            ResourceCapacity("R1", friday, Decimal("0")),
        ),
        options=ResourceLevelingOptions(level_all_resources=True),
    )

    # Thursday -> Friday must shift the demand to Friday (not leave it on Thursday).
    with pytest.raises(ResourceLevelingError, match="FINAL_RESOURCE_OVERALLOCATION"):
        _validate_final_resource_load(
            result=SimpleNamespace(activities={"A": SimpleNamespace(start=friday)}),
            leveling_input=leveling_input,
            resolver=resolver,
        )

    # A backward move from Monday to Friday must be supported and shift Monday's
    # demand back to Friday rather than raising from a reversed date interval.
    monday_demand = ResourceDemand("R1", monday, Decimal("8"), "A")
    backward_input = SchedulerLevelingInput(
        forward_activities=(LevelingActivity("A", monday, monday, 1, (monday_demand,)),),
        # SchedulerLevelingInput requires identical forward/backward activity
        # sets, even when this focused validation case only exercises a backward
        # final-date displacement.
        backward_activities=(
            BackwardLevelingActivity(
                "A", monday, monday, monday, monday, (monday_demand,)
            ),
        ),
        capacities=(
            ResourceCapacity("R1", friday, Decimal("0")),
            ResourceCapacity("R1", monday, Decimal("8")),
        ),
        options=ResourceLevelingOptions(level_all_resources=True),
    )
    with pytest.raises(ResourceLevelingError, match="FINAL_RESOURCE_OVERALLOCATION"):
        _validate_final_resource_load(
            result=SimpleNamespace(activities={"A": SimpleNamespace(start=friday)}),
            leveling_input=backward_input,
            resolver=resolver,
        )


def test_linked_leveling_rejects_overallocation_reintroduced_by_cpm_relationships():
    import pytest

    from construction_pm.scheduling.relationships import Relationship, RelationshipType
    from construction_pm.scheduling.resource_leveling import ResourceLevelingError
    from construction_pm.scheduling.schedule_options import ScheduleOptions

    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    demand_a = ResourceDemand("R1", day_one, Decimal("8"), "A")
    demand_b = ResourceDemand("R1", day_one, Decimal("8"), "B")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", day_one, day_one, 1, (demand_a,)),
            LevelingActivity("B", day_one, day_one, 1, (demand_b,)),
        ),
        backward_activities=(
            BackwardLevelingActivity("A", day_one, day_one, day_two, day_two, (demand_a,)),
            BackwardLevelingActivity("B", day_one, day_one, day_two, day_two, (demand_b,)),
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

    with pytest.raises(ResourceLevelingError, match="FINAL_RESOURCE_OVERALLOCATION"):
        schedule_with_resource_leveling(
            (Activity("A", 1), Activity("B", 1)),
            (Relationship("A", "B", RelationshipType.SS),),
            day_one,
            resolver,
            leveling_input,
            options=ScheduleOptions(
                level_all_resources=True,
                level_within_float=True,
                preserve_scheduled_early_and_late_dates=True,
            ),
        )


def test_public_leveling_orchestration_rejects_unknown_selected_resource() -> None:
    import pytest

    from construction_pm.scheduling.resource_leveling import ResourceLevelingError
    from construction_pm.scheduling.schedule_options import ScheduleOptions

    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))

    with pytest.raises(ResourceLevelingError, match="UNKNOWN_RESOURCE"):
        schedule_with_resource_leveling(
            (Activity("A", 1), Activity("B", 1)),
            (),
            date(2026, 10, 1),
            resolver,
            _resource_leveling_input(preserve=True),
            options=ScheduleOptions(
                level_all_resources=False,
                resource_list=("UNKNOWN",),
                preserve_scheduled_early_and_late_dates=True,
            ),
        )


def test_public_forward_leveling_within_float_moves_by_one_working_day() -> None:
    from construction_pm.scheduling.schedule_options import ScheduleOptions

    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    result, forward, backward = schedule_with_resource_leveling(
        (Activity("A", 1), Activity("B", 1)),
        (),
        date(2026, 10, 1),
        resolver,
        _resource_leveling_input(preserve=True),
        project_finish=date(2026, 10, 3),
        options=ScheduleOptions(
            level_all_resources=True,
            level_within_float=True,
            preserve_scheduled_early_and_late_dates=True,
        ),
    )

    assert [shift.activity_id for shift in forward] == ["A"]
    assert forward[0].shift_working_days == 1
    assert backward == ()
    assert result.activities["A"].start == date(2026, 10, 2)
    assert result.activities["B"].start == date(2026, 10, 1)


def test_public_leveling_priority_changes_deterministic_shift_order() -> None:
    from construction_pm.scheduling.schedule_options import (
        PriorityListItem,
        PrioritySortOrder,
        ScheduleOptions,
    )

    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    base = _resource_leveling_input(preserve=True)

    prioritized, prioritized_forward, prioritized_backward = schedule_with_resource_leveling(
        (Activity("A", 1), Activity("B", 1)),
        (),
        date(2026, 10, 1),
        resolver,
        base,
        project_finish=date(2026, 10, 3),
        options=ScheduleOptions(
            level_all_resources=True,
            level_within_float=True,
            priority_list=(
                PriorityListItem("activity_id", PrioritySortOrder.DESCENDING),
            ),
            preserve_scheduled_early_and_late_dates=True,
        ),
    )
    defaulted, default_forward, default_backward = schedule_with_resource_leveling(
        (Activity("A", 1), Activity("B", 1)),
        (),
        date(2026, 10, 1),
        resolver,
        base,
        project_finish=date(2026, 10, 3),
        options=ScheduleOptions(
            level_all_resources=True,
            level_within_float=True,
            preserve_scheduled_early_and_late_dates=True,
        ),
    )

    # One shift removes the day-one overload; priority chooses which activity moves.
    assert [shift.activity_id for shift in prioritized_forward] == ["B"]
    assert [shift.activity_id for shift in default_forward] == ["A"]
    assert prioritized_backward == ()
    assert default_backward == ()
    assert prioritized.activities["A"].start == date(2026, 10, 1)
    assert prioritized.activities["B"].start == date(2026, 10, 2)
    assert defaulted.activities["A"].start == date(2026, 10, 2)
    assert defaulted.activities["B"].start == date(2026, 10, 1)


def test_public_leveling_orchestration_applies_overallocation_tolerance() -> None:
    from construction_pm.scheduling.schedule_options import ScheduleOptions

    day_one = date(2026, 10, 1)
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    demand = ResourceDemand("R1", day_one, Decimal("105"), "A")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", day_one, day_one, 0, (demand,)),
        ),
        backward_activities=(
            BackwardLevelingActivity("A", day_one, day_one, day_one, day_one, (demand,)),
        ),
        capacities=(ResourceCapacity("R1", day_one, Decimal("100")),),
        options=ResourceLevelingOptions(
            preserve_scheduled_early_and_late_dates=True,
            level_all_resources=True,
        ),
    )

    result, forward, backward = schedule_with_resource_leveling(
        (Activity("A", 1),),
        (),
        day_one,
        resolver,
        leveling_input,
        project_finish=date(2026, 10, 2),
        options=ScheduleOptions(
            level_all_resources=True,
            level_within_float=True,
            over_allocation_percentage=5.0,
            preserve_scheduled_early_and_late_dates=True,
        ),
    )

    # A 5% tolerance raises the effective capacity from 100 to 105. This
    # public-path assertion catches a mapping/orchestration regression that
    # silently drops ScheduleOptions.over_allocation_percentage.
    assert forward == ()
    assert backward == ()
    assert result.activities["A"].start == day_one


def test_public_leveling_selected_resource_scope_keeps_other_activities_unchanged() -> None:
    from construction_pm.scheduling.schedule_options import ScheduleOptions

    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    r1_a = ResourceDemand("R1", day_one, Decimal("8"), "A")
    r1_b = ResourceDemand("R1", day_one, Decimal("8"), "B")
    r2_c = ResourceDemand("R2", day_one, Decimal("8"), "C")
    r2_d = ResourceDemand("R2", day_one, Decimal("8"), "D")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", day_one, day_one, 1, (r1_a,)),
            LevelingActivity("B", day_one, day_one, 1, (r1_b,)),
            LevelingActivity("C", day_one, day_one, 1, (r2_c,)),
            LevelingActivity("D", day_one, day_one, 1, (r2_d,)),
        ),
        backward_activities=(
            BackwardLevelingActivity("A", day_one, day_one, day_two, day_two, (r1_a,)),
            BackwardLevelingActivity("B", day_one, day_one, day_two, day_two, (r1_b,)),
            BackwardLevelingActivity("C", day_one, day_one, day_two, day_two, (r2_c,)),
            BackwardLevelingActivity("D", day_one, day_one, day_two, day_two, (r2_d,)),
        ),
        capacities=(
            ResourceCapacity("R1", day_one, Decimal("8")),
            ResourceCapacity("R1", day_two, Decimal("8")),
            ResourceCapacity("R2", day_one, Decimal("8")),
            ResourceCapacity("R2", day_two, Decimal("8")),
        ),
        options=ResourceLevelingOptions(
            preserve_scheduled_early_and_late_dates=True,
            level_all_resources=False,
            resource_ids=("R1",),
        ),
    )

    result, forward, backward = schedule_with_resource_leveling(
        (Activity("A", 1), Activity("B", 1), Activity("C", 1), Activity("D", 1)),
        (),
        day_one,
        resolver,
        leveling_input,
        project_finish=date(2026, 10, 3),
        options=ScheduleOptions(
            level_all_resources=False,
            level_within_float=True,
            resource_list=("R1",),
            preserve_scheduled_early_and_late_dates=True,
        ),
    )

    assert len(forward) == 1
    assert forward[0].activity_id in {"A", "B"}
    assert backward == ()
    assert {activity_id: result.activities[activity_id].start for activity_id in ("C", "D")} == {
        "C": day_one,
        "D": day_one,
    }
    assert {activity_id: result.activities[activity_id].start for activity_id in ("A", "B")} in (
        {"A": day_one, "B": day_two},
        {"A": day_two, "B": day_one},
    )


def test_public_leveling_allows_one_day_move_at_minimum_float_boundary() -> None:
    from dataclasses import replace

    from construction_pm.scheduling.schedule_options import ScheduleOptions

    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    day_three = date(2026, 10, 5)
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    base = _resource_leveling_input(preserve=True)
    leveling_input = SchedulerLevelingInput(
        forward_activities=tuple(
            # Deliberately stale input values must be replaced by the CPM result.
            replace(activity, total_float=99) for activity in base.forward_activities
        ),
        backward_activities=tuple(
            replace(activity, late_start=day_three, late_finish=day_three)
            for activity in base.backward_activities
        ),
        capacities=base.capacities,
        options=base.options,
    )

    result, forward, backward = schedule_with_resource_leveling(
        (Activity("A", 1), Activity("B", 1)),
        (),
        day_one,
        resolver,
        leveling_input,
        # Thursday -> Monday produces two working-day units of total float.
        project_finish=day_three,
        options=ScheduleOptions(
            level_all_resources=True,
            level_within_float=True,
            min_float_to_preserve=1,
            preserve_scheduled_early_and_late_dates=True,
        ),
    )

    # Fresh CPM float is two working days, despite the deliberately stale 99.
    # Preserving one day of float therefore allows exactly one working-day move.
    assert len(forward) == 1
    assert forward[0].shift_working_days == 1
    assert forward[0].consumed_float == 1
    assert forward[0].remaining_float == 1
    assert forward[0].new_start == day_two
    assert backward == ()
    assert sorted(activity.start for activity in result.activities.values()) == [
        day_one,
        day_two,
    ]

def test_public_backward_leveling_applies_overallocation_tolerance() -> None:
    from construction_pm.scheduling.schedule_options import ScheduleOptions

    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    forward_demand = ResourceDemand("R1", day_one, Decimal("105"), "A")
    backward_demand = ResourceDemand("R1", day_two, Decimal("105"), "A")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", day_one, day_one, 1, (forward_demand,)),
        ),
        backward_activities=(
            BackwardLevelingActivity(
                "A", day_one, day_one, day_two, day_two, (backward_demand,),
            ),
        ),
        capacities=(
            ResourceCapacity("R1", day_one, Decimal("100")),
            ResourceCapacity("R1", day_two, Decimal("100")),
        ),
        options=ResourceLevelingOptions(
            preserve_scheduled_early_and_late_dates=False,
            level_all_resources=True,
        ),
    )

    result, forward, backward = schedule_with_resource_leveling(
        (Activity("A", 1),),
        (),
        day_one,
        resolver,
        leveling_input,
        project_finish=day_two,
        options=ScheduleOptions(
            level_all_resources=True,
            level_within_float=True,
            over_allocation_percentage=5.0,
            preserve_scheduled_early_and_late_dates=False,
        ),
    )

    # The 5% tolerance makes 105 units acceptable against capacity 100 in
    # both passes. Without propagation to the backward proposer, A would be
    # advanced from day two to day one to "resolve" a tolerated overload.
    assert forward == ()
    assert backward == ()
    assert result.activities["A"].start == day_one


def test_final_resource_validation_rejects_missing_scheduled_activity_with_demands():
    from types import SimpleNamespace

    import pytest

    from construction_pm.scheduling.leveling_scheduler import _validate_final_resource_load
    from construction_pm.scheduling.resource_leveling import ResourceLevelingError

    day = date(2026, 10, 1)
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    demand = ResourceDemand("R1", day, Decimal("8"), "A")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(LevelingActivity("A", day, day, 1, (demand,)),),
        backward_activities=(
            BackwardLevelingActivity("A", day, day, day, day, (demand,)),
        ),
        capacities=(ResourceCapacity("R1", day, Decimal("8")),),
        options=ResourceLevelingOptions(level_all_resources=True),
    )

    with pytest.raises(ResourceLevelingError, match="FINAL_SCHEDULE_MISSING_ACTIVITY:A"):
        _validate_final_resource_load(
            result=SimpleNamespace(activities={}),
            leveling_input=leveling_input,
            resolver=resolver,
        )


def test_backward_activity_builder_shifts_resource_demands_inclusive_of_one_day():
    from types import SimpleNamespace

    from construction_pm.scheduling.leveling_scheduler import _backward_activities_from_intermediate

    day_one = date(2026, 10, 1)
    day_two = date(2026, 10, 2)
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    demand = ResourceDemand("R1", day_one, Decimal("8"), "A")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", day_one, day_one, 2, (demand,)),
        ),
        backward_activities=(
            BackwardLevelingActivity("A", day_one, day_one, day_two, day_two, (demand,)),
        ),
        capacities=(ResourceCapacity("R1", day_one, Decimal("8")),),
        options=ResourceLevelingOptions(level_all_resources=True),
    )

    built = _backward_activities_from_intermediate(
        leveling_input,
        early_schedule={"A": SimpleNamespace(start=day_one, finish=day_one)},
        late_schedule={"A": SimpleNamespace(start=day_two, finish=day_two)},
        resolver=resolver,
    )

    assert len(built) == 1
    assert built[0].resource_demands[0].period == day_two



def test_backward_activity_builder_shifts_demands_across_weekend():
    from types import SimpleNamespace

    from construction_pm.scheduling.leveling_scheduler import _backward_activities_from_intermediate

    thursday = date(2026, 10, 1)
    monday = date(2026, 10, 5)
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    demand = ResourceDemand("R1", thursday, Decimal("8"), "A")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", thursday, thursday, 3, (demand,)),
        ),
        backward_activities=(
            BackwardLevelingActivity("A", thursday, thursday, monday, monday, (demand,)),
        ),
        capacities=(ResourceCapacity("R1", monday, Decimal("8")),),
        options=ResourceLevelingOptions(level_all_resources=True),
    )

    built = _backward_activities_from_intermediate(
        leveling_input,
        early_schedule={"A": SimpleNamespace(start=thursday, finish=thursday)},
        late_schedule={"A": SimpleNamespace(start=monday, finish=monday)},
        resolver=resolver,
    )

    assert built[0].resource_demands[0].period == monday


def test_backward_activity_builder_shifts_resource_demands_across_holiday():
    from types import SimpleNamespace

    from construction_pm.scheduling.leveling_scheduler import _backward_activities_from_intermediate

    thursday = date(2026, 10, 1)
    monday = date(2026, 10, 5)
    friday_holiday = date(2026, 10, 2)
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}),
        holidays=frozenset({friday_holiday}),
    ))
    demand = ResourceDemand("R1", thursday, Decimal("8"), "A")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", thursday, thursday, 2, (demand,)),
        ),
        backward_activities=(
            BackwardLevelingActivity("A", thursday, thursday, monday, monday, (demand,)),
        ),
        capacities=(ResourceCapacity("R1", monday, Decimal("8")),),
        options=ResourceLevelingOptions(level_all_resources=True),
    )

    built = _backward_activities_from_intermediate(
        leveling_input,
        early_schedule={"A": SimpleNamespace(start=thursday, finish=thursday)},
        late_schedule={"A": SimpleNamespace(start=monday, finish=monday)},
        resolver=resolver,
    )

    assert built[0].resource_demands[0].period == monday


def test_final_resource_validation_shifts_backward_demands_across_holiday_and_weekend():
    from types import SimpleNamespace

    import pytest

    from construction_pm.scheduling.leveling_scheduler import _validate_final_resource_load
    from construction_pm.scheduling.resource_leveling import ResourceLevelingError

    thursday = date(2026, 10, 1)
    friday_holiday = date(2026, 10, 2)
    monday = date(2026, 10, 5)
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}),
        holidays=frozenset({friday_holiday}),
    ))
    demand = ResourceDemand("R1", monday, Decimal("8"), "A")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(LevelingActivity("A", monday, monday, 1, (demand,)),),
        backward_activities=(
            BackwardLevelingActivity("A", monday, monday, monday, monday, (demand,)),
        ),
        capacities=(
            ResourceCapacity("R1", thursday, Decimal("0")),
            ResourceCapacity("R1", monday, Decimal("8")),
        ),
        options=ResourceLevelingOptions(level_all_resources=True),
    )

    # Monday -> Thursday is one working-day displacement because Friday is
    # a holiday and the weekend is non-working; the demand must land Thursday.
    with pytest.raises(ResourceLevelingError, match="FINAL_RESOURCE_OVERALLOCATION"):
        _validate_final_resource_load(
            result=SimpleNamespace(activities={"A": SimpleNamespace(start=thursday)}),
            leveling_input=leveling_input,
            resolver=resolver,
        )

def test_backward_leveling_never_overrides_user_start_lower_bound() -> None:
    """A backward candidate earlier than a user constraint must be rejected."""
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    required_start = date(2026, 10, 2)

    result, _forward, backward = schedule_with_resource_leveling(
        (Activity("A", 1), Activity("B", 1)),
        (),
        date(2026, 10, 1),
        resolver,
        _resource_leveling_input(preserve=False),
        project_finish=date(2026, 10, 3),
        constraints=(
            ActivityConstraint(
                "A", ConstraintType.START_NO_EARLIER_THAN, required_start,
            ),
        ),
    )

    assert result.activities["A"].start >= required_start
    assert result.activities["A"].start != result.activities["B"].start
    # No accepted backward move may place A before the user-specified bound.
    assert all(
        shift.activity_id != "A" or shift.new_start >= required_start
        for shift in backward
    )

@pytest.mark.parametrize(
    ("relationship_type", "lag"),
    [
        (RelationshipType.FS, 0),
        (RelationshipType.FS, 1),
        (RelationshipType.FS, -1),
        (RelationshipType.SS, 0),
        (RelationshipType.SS, 1),
        (RelationshipType.SS, -1),
        (RelationshipType.FF, 0),
        (RelationshipType.FF, 1),
        (RelationshipType.FF, -1),
        (RelationshipType.SF, 0),
        (RelationshipType.SF, 1),
        (RelationshipType.SF, -1),
    ],
)
def test_leveling_recalculation_preserves_all_relationship_types_and_signed_lags(
    relationship_type, lag
):
    from construction_pm.scheduling.relationships import Relationship, RelationshipType
    from construction_pm.scheduling.schedule import _relationship_holds

    first_day = date(2026, 10, 1)
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    demand_a = ResourceDemand("R1", first_day, Decimal("8"), "A")
    demand_b = ResourceDemand("R1", first_day, Decimal("8"), "B")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", first_day, first_day, 10, (demand_a,)),
            LevelingActivity("B", first_day, first_day, 10, (demand_b,)),
        ),
        backward_activities=(
            BackwardLevelingActivity(
                "A", first_day, first_day, date(2026, 10, 10), date(2026, 10, 10), (demand_a,)
            ),
            BackwardLevelingActivity(
                "B", first_day, first_day, date(2026, 10, 10), date(2026, 10, 10), (demand_b,)
            ),
        ),
        capacities=tuple(
            # One activity at a time on every date forces real resource
            # contention, including the backward-leveling recalculation path.
            ResourceCapacity("R1", date(2026, 10, day), Decimal("8"))
            for day in range(1, 12)
        ),
        options=ResourceLevelingOptions(
            preserve_scheduled_early_and_late_dates=False,
            level_all_resources=True,
        ),
    )
    relationship = Relationship("A", "B", relationship_type, lag=lag)

    result, _forward, _backward = schedule_with_resource_leveling(
        (Activity("A", 1), Activity("B", 1)),
        (relationship,),
        first_day,
        resolver,
        leveling_input,
        project_finish=date(2026, 10, 15),
    )

    predecessor = result.activities["A"]
    successor = result.activities["B"]
    assert _relationship_holds(relationship, predecessor, successor, resolver, resolver), (
        f"{relationship_type.value} lag={lag} violated after leveling: "
        f"predecessor={predecessor}, successor={successor}"
    )
    final_demand_by_day = {
        day: sum(
            Decimal("8")
            for activity in (predecessor, successor)
            if activity.start == day
        )
        for day in (date(2026, 10, day) for day in range(1, 12))
    }
    capacity_by_day = {
        capacity.period: capacity.units
        for capacity in leveling_input.capacities
        if capacity.resource_id == "R1"
    }
    assert all(
        final_demand_by_day[day] <= capacity_by_day[day]
        for day in final_demand_by_day
    )
    assert set(result.floats) == {"A", "B"}



def test_backward_activity_builder_carries_authoritative_cpm_floats():
    from types import SimpleNamespace
    from construction_pm.scheduling.leveling_scheduler import _backward_activities_from_intermediate

    day_one, day_two = date(2026, 10, 1), date(2026, 10, 2)
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    demand = ResourceDemand("R1", day_one, Decimal("8"), "A")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(LevelingActivity("A", day_one, day_one, 2, (demand,)),),
        backward_activities=(BackwardLevelingActivity("A", day_one, day_one, day_two, day_two, (demand,)),),
        capacities=(ResourceCapacity("R1", day_one, Decimal("8")),),
        options=ResourceLevelingOptions(level_all_resources=True),
    )
    built = _backward_activities_from_intermediate(
        leveling_input,
        early_schedule={"A": SimpleNamespace(start=day_one, finish=day_one)},
        late_schedule={"A": SimpleNamespace(start=day_two, finish=day_two)},
        float_schedule={"A": SimpleNamespace(total_float=3, free_float=1)},
        resolver=resolver,
    )
    assert built[0].total_float == 3
    assert built[0].free_float == 1

def test_resource_leveling_preserves_activity_specific_calendars() -> None:
    """Every CPM pass in resource leveling must use the activity calendar map."""
    from construction_pm.scheduling.activity import Activity
    from construction_pm.scheduling.resource_leveling import LevelingActivity
    from construction_pm.scheduling.leveling_scheduler import schedule_with_resource_leveling
    from construction_pm.scheduling.schedule_options import ScheduleOptions

    start = date(2026, 10, 1)  # Thursday
    finish = date(2026, 10, 5)  # Monday
    project_resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    activity_resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3}), holidays=frozenset(),
    ))
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", start, start, 0, ()),
            LevelingActivity("B", start, finish, 0, ()),
        ),
        backward_activities=(
            BackwardLevelingActivity("A", start, start, finish, finish, ()),
            BackwardLevelingActivity("B", start, finish, finish, finish, ()),
        ),
        capacities=(),
        options=ResourceLevelingOptions(
            preserve_scheduled_early_and_late_dates=True,
            level_all_resources=False,
        ),
    )

    result, _, backward = schedule_with_resource_leveling(
        (Activity("A", 1), Activity("B", 2)),
        (),
        start,
        project_resolver,
        leveling_input,
        project_finish=finish,
        options=ScheduleOptions(preserve_scheduled_early_and_late_dates=True),
        activity_resolvers={"B": activity_resolver},
    )

    assert backward == ()
    assert result.activities["A"].finish == start
    # Friday is non-working for B, so its two-day activity ends on Monday.
    assert result.activities["B"].finish == finish


def test_backward_demand_translation_uses_activity_calendar() -> None:
    from decimal import Decimal
    from types import SimpleNamespace
    from construction_pm.scheduling.leveling_scheduler import _backward_activities_from_intermediate
    from construction_pm.scheduling.resource_leveling import LevelingActivity

    thursday = date(2026, 10, 1)
    monday = date(2026, 10, 5)
    project_resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    activity_resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3}), holidays=frozenset(),
    ))
    demand = ResourceDemand("R1", thursday, Decimal("8"), "B")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("B", thursday, thursday, 1, (demand,)),
        ),
        backward_activities=(
            BackwardLevelingActivity("B", thursday, thursday, monday, monday, (demand,)),
        ),
        capacities=(),
        options=ResourceLevelingOptions(preserve_scheduled_early_and_late_dates=False),
    )

    result = _backward_activities_from_intermediate(
        leveling_input,
        early_schedule={"B": SimpleNamespace(start=thursday, finish=thursday)},
        late_schedule={"B": SimpleNamespace(start=monday, finish=monday)},
        resolver=project_resolver,
        activity_resolvers={"B": activity_resolver},
    )

    # Friday is non-working for B. Its demand therefore shifts to Monday,
    # not Friday as it would under the project calendar.
    assert result[0].resource_demands[0].period == monday

def test_forward_activity_builder_rebases_all_values_from_fresh_cpm():
    from types import SimpleNamespace
    from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
    from construction_pm.scheduling.leveling_scheduler import (
        _forward_activities_with_authoritative_floats,
    )
    from construction_pm.scheduling.resource_leveling import LevelingActivity

    day_one = date(2026, 10, 1)  # Thursday
    day_two = date(2026, 10, 2)  # Friday
    day_three = date(2026, 10, 5)  # Monday
    day_five = date(2026, 10, 7)  # Wednesday
    demand_a = ResourceDemand("R1", day_one, Decimal("8"), "A")
    demand_b = ResourceDemand("R1", day_one, Decimal("8"), "B")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            # These deliberately stale dates/floats must not survive CPM refresh.
            LevelingActivity("A", day_one, day_one, 99, (demand_a,), free_float=99),
            LevelingActivity("B", day_one, day_one, 99, (demand_b,), free_float=99),
        ),
        backward_activities=(
            BackwardLevelingActivity(
                "A", day_one, day_one, day_three, day_three, (demand_a,)
            ),
            BackwardLevelingActivity(
                "B", day_one, day_one, day_five, day_five, (demand_b,)
            ),
        ),
        capacities=(),
        options=ResourceLevelingOptions(level_all_resources=True),
    )
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))

    built = _forward_activities_with_authoritative_floats(
        leveling_input,
        resolver=resolver,
        initial_schedule=SimpleNamespace(
            early_activities={
                "A": SimpleNamespace(start=day_two, finish=day_two),
                "B": SimpleNamespace(start=day_three, finish=day_three),
            },
            floats={
                "A": SimpleNamespace(total_float=1, free_float=0),
                "B": SimpleNamespace(total_float=4, free_float=2),
            },
            late_activities={
                "A": SimpleNamespace(start=day_three, finish=day_three),
                "B": SimpleNamespace(start=day_five, finish=day_five),
            },
        ),
    )

    assert [(activity.start, activity.finish) for activity in built] == [
        (day_two, day_two), (day_three, day_three)
    ]
    assert [activity.total_float for activity in built] == [1, 4]
    assert [activity.free_float for activity in built] == [0, 2]
    assert [activity.late_start for activity in built] == [day_three, day_five]
    assert [activity.late_finish for activity in built] == [day_three, day_five]
    # Resource demand must follow the same CPM/calendar shift as the activity.
    assert [activity.resource_demands[0].period for activity in built] == [
        day_two, day_three
    ]

def test_public_leveling_rebases_resource_periods_to_fresh_cpm_dates():
    from construction_pm.scheduling.activity import Activity
    from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
    from construction_pm.scheduling.leveling_scheduler import schedule_with_resource_leveling
    from construction_pm.scheduling.relationships import Relationship, RelationshipType
    from construction_pm.scheduling.schedule_options import ScheduleOptions

    thursday = date(2026, 10, 1)
    friday = date(2026, 10, 2)
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    demand_a = ResourceDemand("R1", thursday, Decimal("1"), "A")
    # Deliberately stale request period: a fresh SS +1 CPM pass starts B Friday.
    demand_b = ResourceDemand("R1", thursday, Decimal("1"), "B")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", thursday, thursday, 9, (demand_a,)),
            LevelingActivity("B", thursday, thursday, 9, (demand_b,)),
        ),
        backward_activities=(
            BackwardLevelingActivity(
                "A", thursday, thursday, friday, friday, (demand_a,)
            ),
            BackwardLevelingActivity(
                "B", thursday, thursday, friday, friday, (demand_b,)
            ),
        ),
        capacities=(
            ResourceCapacity("R1", thursday, Decimal("1")),
            ResourceCapacity("R1", friday, Decimal("1")),
        ),
        options=ResourceLevelingOptions(
            preserve_scheduled_early_and_late_dates=True,
            level_all_resources=True,
        ),
    )

    result, forward, backward = schedule_with_resource_leveling(
        (Activity("A", 1), Activity("B", 1)),
        (Relationship("A", "B", RelationshipType.SS, lag=1),),
        thursday,
        resolver,
        leveling_input,
        project_finish=friday,
        options=ScheduleOptions(
            level_all_resources=True,
            preserve_scheduled_early_and_late_dates=True,
        ),
    )

    assert forward == ()
    assert backward == ()
    assert result.activities["A"].start == thursday
    assert result.activities["B"].start == friday
    # Stale periods must be rebased with CPM dates before leveling, not counted
    # as a false Thursday overload and then unnecessarily delayed.
    assert result.project_finish == friday


def test_infeasible_resource_window_fails_closed() -> None:
    """Do not report success when no CPM-feasible period has resource capacity."""
    import pytest

    from construction_pm.scheduling.resource_leveling import ResourceLevelingError
    from construction_pm.scheduling.schedule_options import ScheduleOptions

    day = date(2026, 10, 1)
    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    demand = ResourceDemand("R1", day, Decimal("8"), "A")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(LevelingActivity("A", day, day, 0, (demand,)),),
        backward_activities=(
            BackwardLevelingActivity("A", day, day, day, day, (demand,)),
        ),
        capacities=(ResourceCapacity("R1", day, Decimal("0")),),
        options=ResourceLevelingOptions(
            preserve_scheduled_early_and_late_dates=False,
            level_all_resources=True,
            level_within_float=True,
        ),
    )

    with pytest.raises(ResourceLevelingError, match="FINAL_RESOURCE_OVERALLOCATION"):
        schedule_with_resource_leveling(
            (Activity("A", 1),),
            (),
            day,
            resolver,
            leveling_input,
            project_finish=day,
            options=ScheduleOptions(
                level_all_resources=True,
                level_within_float=True,
                preserve_scheduled_early_and_late_dates=False,
            ),
        )

@pytest.mark.parametrize(
    "field_name",
    [
        "activity_id",
        "activity_priority",
        "early_start",
        "early_finish",
        "late_start",
        "late_finish",
        "free_float",
        "total_float",
    ],
)
def test_public_leveling_priority_boundary_accepts_supported_p6_fields(field_name):
    from construction_pm.scheduling.leveling_boundary import _map_priority_list
    from construction_pm.scheduling.schedule_options import (
        PriorityListItem,
        PrioritySortOrder,
        ScheduleOptions,
    )

    mapped = _map_priority_list(ScheduleOptions(
        priority_list=(PriorityListItem(field_name, PrioritySortOrder.ASCENDING),)
    ))

    assert len(mapped) == 1
    assert mapped[0].field_name == field_name

