"""P0-E: the leveling orchestrator must never recompute an identical CPM pass.

Every CPM call inside ``schedule_with_resource_leveling`` uses the same
activities, relationships, calendars, options, lag resolvers and calculation
context; only the ordered constraint tuple differs. These tests pin both the
number of CPM passes and the fact that reuse returns the same authoritative
result as a fresh calculation for the same final constraint set.
"""

import importlib
from datetime import date
from decimal import Decimal

from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.leveling_boundary import SchedulerLevelingInput
from construction_pm.scheduling.leveling_scheduler import (
    backward_leveling_exact_constraints,
    forward_leveling_constraints,
    schedule_with_resource_leveling,
)
from construction_pm.scheduling.resource_leveling import (
    BackwardLevelingActivity,
    LevelingActivity,
    ResourceCapacity,
    ResourceDemand,
    ResourceLevelingOptions,
)
from construction_pm.scheduling.schedule import schedule

schedule_module = importlib.import_module("construction_pm.scheduling.schedule")
from construction_pm.scheduling.schedule_options import (
    PriorityListItem,
    PrioritySortOrder,
    ScheduleOptions,
)

DAY_ONE = date(2026, 10, 1)  # Thursday
DAY_TWO = date(2026, 10, 2)  # Friday
DAY_THREE = date(2026, 10, 5)  # Monday


def _resolver() -> WorkingTimeResolver:
    return WorkingTimeResolver(
        WorkingCalendar(working_weekdays=frozenset({0, 1, 2, 3, 4}), holidays=frozenset())
    )


def _count_cpm_passes(monkeypatch) -> list[tuple]:
    calls: list[tuple] = []
    real_schedule = schedule_module.schedule

    def counting(activities, relationships, project_start, resolver, **kwargs):
        calls.append(tuple(kwargs.get("constraints") or ()))
        return real_schedule(activities, relationships, project_start, resolver, **kwargs)

    monkeypatch.setattr(schedule_module, "schedule", counting)
    return calls


def _backward_scenario():
    """Two linked activities where one backward move is accepted."""
    demands = (
        ResourceDemand("R1", DAY_ONE, Decimal("8"), "A"),
        ResourceDemand("R1", DAY_ONE, Decimal("8"), "B"),
    )
    leveling_input = SchedulerLevelingInput(
        forward_activities=(
            LevelingActivity("A", DAY_ONE, DAY_ONE, 1, (demands[0],), activity_priority=1),
            LevelingActivity("B", DAY_ONE, DAY_ONE, 1, (demands[1],), activity_priority=0),
        ),
        backward_activities=(
            BackwardLevelingActivity("A", DAY_ONE, DAY_ONE, DAY_THREE, DAY_THREE, (demands[0],), activity_priority=1),
            BackwardLevelingActivity("B", DAY_ONE, DAY_ONE, DAY_THREE, DAY_THREE, (demands[1],), activity_priority=0),
        ),
        capacities=(
            ResourceCapacity("R1", DAY_ONE, Decimal("16")),
            ResourceCapacity("R1", DAY_TWO, Decimal("8")),
        ),
        options=ResourceLevelingOptions(
            preserve_scheduled_early_and_late_dates=False,
            level_all_resources=True,
        ),
    )
    from construction_pm.scheduling.relationships import Relationship, RelationshipType

    return {
        "activities": (Activity("A", 1), Activity("B", 1)),
        "relationships": (Relationship("A", "B", RelationshipType.SS),),
        "leveling_input": leveling_input,
    }


def _forward_only_scenario(size: int = 12):
    from construction_pm.scheduling.benchmark_fixtures import (
        leveling_orchestration_case,
    )

    return leveling_orchestration_case(size)


def test_backward_acceptance_does_not_repeat_the_closing_cpm_pass(monkeypatch) -> None:
    scenario = _backward_scenario()
    calls = _count_cpm_passes(monkeypatch)

    result, forward, backward = schedule_with_resource_leveling(
        scenario["activities"],
        scenario["relationships"],
        DAY_ONE,
        _resolver(),
        scenario["leveling_input"],
        project_finish=DAY_THREE,
        options=ScheduleOptions(
            level_all_resources=True,
            preserve_scheduled_early_and_late_dates=False,
            priority_list=(PriorityListItem("activity_priority", PrioritySortOrder.ASCENDING),),
        ),
    )

    assert forward == ()
    assert [(shift.activity_id, shift.advanced_days) for shift in backward] == [("B", 1)]
    # Reference engine: initial, intermediate, two candidate trials and a
    # closing pass over the winning candidate's constraint set. The closing
    # pass is an exact duplicate, so it must not run again.
    assert len(calls) == 3
    assert calls.count(calls[-1]) == 1
    assert callable(schedule_module.schedule)
    # The published result is still the authoritative CPM result for the final
    # constraint set, not a stale intermediate.
    assert result.activities["A"].start == DAY_ONE
    assert result.activities["B"].start == DAY_TWO


def test_backward_scenario_result_matches_a_fresh_cpm_pass(monkeypatch) -> None:
    scenario = _backward_scenario()
    resolver = _resolver()
    options = ScheduleOptions(
        level_all_resources=True,
        preserve_scheduled_early_and_late_dates=False,
        priority_list=(PriorityListItem("activity_priority", PrioritySortOrder.ASCENDING),),
    )
    result, forward, backward = schedule_with_resource_leveling(
        scenario["activities"],
        scenario["relationships"],
        DAY_ONE,
        resolver,
        scenario["leveling_input"],
        project_finish=DAY_THREE,
        options=options,
    )

    retained_forward = tuple(
        shift for shift in forward if shift.activity_id not in {item.activity_id for item in backward}
    )
    final_constraints = (
        forward_leveling_constraints(retained_forward)
        + backward_leveling_exact_constraints(backward)
    )
    fresh = schedule(
        scenario["activities"],
        scenario["relationships"],
        DAY_ONE,
        resolver,
        project_finish=DAY_THREE,
        constraints=final_constraints,
        options=ScheduleOptions(),
    )

    assert {key: (value.start, value.finish) for key, value in result.activities.items()} == {
        key: (value.start, value.finish) for key, value in fresh.activities.items()
    }
    assert result.project_finish == fresh.project_finish
    assert {
        key: (value.total_float, value.free_float) for key, value in result.floats.items()
    } == {key: (value.total_float, value.free_float) for key, value in fresh.floats.items()}


def test_forward_only_orchestration_skips_the_duplicate_intermediate_and_final_passes(
    monkeypatch,
) -> None:
    fixture = _forward_only_scenario()
    calls = _count_cpm_passes(monkeypatch)

    result, forward, backward = schedule_with_resource_leveling(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        fixture.resolver,
        fixture.leveling_input,
        project_finish=fixture.project_finish,
        options=fixture.options,
    )

    assert forward
    assert backward == ()
    # Initial pass plus the single pass over the forward constraints; the
    # closing pass is identical to that intermediate pass and is reused.
    assert len(calls) == 2
    assert calls[0] == ()
    assert calls[0] != calls[1]
    assert result.project_finish == fixture.project_finish


def test_orchestration_without_any_shift_runs_a_single_cpm_pass(monkeypatch) -> None:
    demand = ResourceDemand("R1", DAY_ONE, Decimal("8"), "A")
    leveling_input = SchedulerLevelingInput(
        forward_activities=(LevelingActivity("A", DAY_ONE, DAY_ONE, 5, (demand,)),),
        backward_activities=(
            BackwardLevelingActivity("A", DAY_ONE, DAY_ONE, DAY_THREE, DAY_THREE, (demand,)),
        ),
        capacities=(
            ResourceCapacity("R1", DAY_ONE, Decimal("8")),
            ResourceCapacity("R1", DAY_TWO, Decimal("8")),
        ),
        options=ResourceLevelingOptions(
            preserve_scheduled_early_and_late_dates=True,
            level_all_resources=True,
        ),
    )
    calls = _count_cpm_passes(monkeypatch)

    result, forward, backward = schedule_with_resource_leveling(
        (Activity("A", 1),),
        (),
        DAY_ONE,
        _resolver(),
        leveling_input,
        project_finish=DAY_THREE,
        options=ScheduleOptions(
            level_all_resources=True,
            preserve_scheduled_early_and_late_dates=True,
        ),
    )

    assert forward == ()
    assert backward == ()
    assert calls == [()]
    assert result.activities["A"].start == DAY_ONE


def test_final_resource_validation_still_runs_after_reuse(monkeypatch) -> None:
    from construction_pm.scheduling import leveling_scheduler

    fixture = _forward_only_scenario(8)
    validations: list[object] = []
    original = leveling_scheduler._validate_final_resource_load

    def recording(**kwargs):
        validations.append(kwargs["result"])
        return original(**kwargs)

    monkeypatch.setattr(leveling_scheduler, "_validate_final_resource_load", recording)

    result, _forward, _backward = schedule_with_resource_leveling(
        fixture.activities,
        fixture.relationships,
        fixture.project_start,
        fixture.resolver,
        fixture.leveling_input,
        project_finish=fixture.project_finish,
        options=fixture.options,
    )

    # Candidate checks (none here, because there are no backward proposals) plus
    # exactly one final validation of the returned result.
    assert validations
    assert validations[-1] is result
