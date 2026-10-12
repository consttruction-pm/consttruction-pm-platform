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


def _resource_leveling_input(*, preserve: bool) -> SchedulerLevelingInput:
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
        ResourceCapacity("R1", date(2026, 10, 2), Decimal("8")),
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
            min_float_to_preserve=1,
            preserve_scheduled_early_and_late_dates=True,
        ),
    )

    # Each activity has one day of total float in the leveling input. Preserving
    # one day leaves no movement allowance, so the engine must not shift either
    # activity merely to remove the resource overload.
    assert forward == ()
    assert backward == ()
    assert result.activities["A"].start == date(2026, 10, 1)
    assert result.activities["B"].start == date(2026, 10, 1)



def test_linked_resource_leveling_recalculates_relationships_and_cpm_output() -> None:
    from construction_pm.scheduling.relationships import Relationship, RelationshipType

    resolver = WorkingTimeResolver(WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset(),
    ))
    activities = (Activity("A", 1), Activity("B", 1))
    relationships = (Relationship("A", "B", RelationshipType.SS),)

    result, forward, backward = schedule_with_resource_leveling(
        activities,
        relationships,
        date(2026, 10, 1),
        resolver,
        _resource_leveling_input(preserve=True),
    )

    # Accepted leveling movement must flow back through the ordinary CPM scheduler.
    assert len(forward) == 1
    assert backward == ()
    assert result.activities["B"].start >= result.activities["A"].start
    assert result.project_finish == max(item.finish for item in result.activities.values())
    assert set(result.floats) == {"A", "B"}
    for activity_id, float_result in result.floats.items():
        early = result.early_activities[activity_id]
        late = result.late_activities[activity_id]
        assert float_result.early_start == early.start
        assert float_result.early_finish == early.finish
        assert float_result.late_start == late.start
        assert float_result.late_finish == late.finish


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
