from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from construction_pm.scheduling.resource_dependent import (
    ResourceDependentDemandPeriod,
    ResourceDependentDriverFact,
)
from construction_pm.scheduling.resource_dependent_placement import (
    ASSIGNMENT_FAILED,
    ASSIGNMENT_FIXED_DRIVING,
    ASSIGNMENT_PLACED,
    PLACEMENT_COMPLETE,
    PLACEMENT_FAILED,
    ResourceDependentPlacementError,
    demands_at_final_schedule,
    place_resource_dependent_assignments,
)
from construction_pm.scheduling.resource_leveling import (
    LevelingActivity,
    LevelingPriority,
    ResourceCapacity,
    ResourceDemand,
    SortOrder,
)

HASH = "a" * 64


def fact(
    assignment_id: str,
    *,
    activity_id: str = "RD-1",
    resource_id: str | None = None,
    driving: bool,
    periods: tuple[tuple[str, str], ...],
    planned: str = "8",
    rate: str = "4",
    calendar_id: str = "RC-1",
    calendar_version: str = "v1",
) -> ResourceDependentDriverFact:
    return ResourceDependentDriverFact(
        assignment_id=assignment_id,
        activity_id=activity_id,
        resource_id=resource_id or assignment_id,
        calendar_id=calendar_id,
        calendar_version=calendar_version,
        unit_of_measure="labor-unit",
        planned_units=Decimal(planned),
        is_driving=driving,
        units_per_time=Decimal(rate),
        units_per_time_period="day",
        hours_per_units_time_period=Decimal("8"),
        demand_periods=tuple(
            ResourceDependentDemandPeriod(date.fromisoformat(day), Decimal(units))
            for day, units in periods
        ),
    )


def capacity(resource_id: str, days: tuple[str, ...], units: str = "8") -> tuple[ResourceCapacity, ...]:
    return tuple(
        ResourceCapacity(
            resource_id,
            date.fromisoformat(day),
            Decimal(units),
            "RC-1",
            "v1",
            HASH,
        )
        for day in days
    )


def capacity_values(
    resource_id: str,
    values: tuple[tuple[str, str], ...],
) -> tuple[ResourceCapacity, ...]:
    return tuple(
        ResourceCapacity(
            resource_id,
            date.fromisoformat(day),
            Decimal(units),
            "RC-1",
            "v1",
            HASH,
        )
        for day, units in values
    )


def activities(*, start: str = "2026-10-19", finish: str = "2026-10-21"):
    return {"RD-1": SimpleNamespace(start=date.fromisoformat(start), finish=date.fromisoformat(finish))}


def test_driving_and_nondriving_assignments_place_independently():
    facts = (
        fact(
            "AS-DRIVE",
            driving=True,
            periods=(("2026-10-19", "4"), ("2026-10-20", "4")),
        ),
        fact(
            "AS-FLEX",
            resource_id="R-FLEX",
            driving=False,
            periods=(("2026-10-19", "4"), ("2026-10-20", "4")),
        ),
    )
    capacities = capacity("AS-DRIVE", ("2026-10-19", "2026-10-20", "2026-10-21")) + capacity(
        "R-FLEX",
        ("2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22"),
    )
    committed = (ResourceDemand("R-FLEX", date(2026, 10, 19), Decimal("8"), "TD-1"),)

    result = place_resource_dependent_assignments(
        facts=facts,
        activities=activities(),
        capacities=capacities,
        committed_demands=committed,
    )

    assert result.status == PLACEMENT_COMPLETE
    by_id = {item.assignment_id: item for item in result.assignments}
    assert by_id["AS-DRIVE"].status == ASSIGNMENT_FIXED_DRIVING
    assert by_id["AS-DRIVE"].start == date(2026, 10, 19)
    assert by_id["AS-DRIVE"].finish == date(2026, 10, 20)
    assert [
        (item.source_period_start, item.period)
        for item in by_id["AS-DRIVE"].demand_periods
    ] == [
        (date(2026, 10, 19), date(2026, 10, 19)),
        (date(2026, 10, 20), date(2026, 10, 20)),
    ]
    assert by_id["AS-FLEX"].status == ASSIGNMENT_PLACED
    # The nondriving assignment starts after full Task Dependent load and never
    # changes the activity's authoritative dates.
    assert by_id["AS-FLEX"].start == date(2026, 10, 20)
    assert by_id["AS-FLEX"].finish == date(2026, 10, 21)
    assert by_id["AS-FLEX"].total_units == Decimal("8")
    assert [
        (item.source_period_start, item.period)
        for item in by_id["AS-FLEX"].demand_periods
    ] == [
        (date(2026, 10, 19), date(2026, 10, 20)),
        (date(2026, 10, 20), date(2026, 10, 21)),
    ]
    assert len(result.input_hash) == 64

    replay = place_resource_dependent_assignments(
        facts=tuple(reversed(facts)),
        activities=activities(),
        capacities=capacities,
        committed_demands=committed,
    )
    assert replay.to_payload() == result.to_payload()


def test_nondriving_assignment_can_finish_after_activity_and_project_finish():
    result = place_resource_dependent_assignments(
        facts=(
            fact(
                "AS-FLEX",
                driving=False,
                periods=(("2026-10-19", "4"), ("2026-10-20", "4")),
            ),
        ),
        activities=activities(start="2026-10-19", finish="2026-10-19"),
        capacities=capacity(
            "AS-FLEX",
            ("2026-10-19", "2026-10-20", "2026-10-21"),
        ),
    )

    assert result.status == PLACEMENT_COMPLETE
    placed = result.assignments[0]
    assert placed.status == ASSIGNMENT_PLACED
    assert placed.start == date(2026, 10, 19)
    assert placed.finish == date(2026, 10, 20)
    assert placed.activity_finish == date(2026, 10, 19)
    assert [
        item.source_period_start for item in placed.demand_periods
    ] == [date(2026, 10, 19), date(2026, 10, 20)]


def test_nondriving_capacity_exhaustion_returns_assignment_diagnostic():
    result = place_resource_dependent_assignments(
        facts=(
            fact(
                "AS-FLEX",
                driving=False,
                periods=(("2026-10-19", "8"),),
                rate="8",
            ),
        ),
        activities=activities(),
        capacities=capacity(
            "AS-FLEX",
            ("2026-10-19", "2026-10-20", "2026-10-21"),
            units="4",
        ),
    )

    assert result.status == PLACEMENT_FAILED
    failed = result.assignments[0]
    assert failed.status == ASSIGNMENT_FAILED
    assert failed.diagnostic_code == "RESOURCE_DEPENDENT_NONDRIVING_CAPACITY_EXHAUSTED"
    assert failed.start is None and failed.finish is None
    assert result.failed_assignments == (failed,)


def test_zero_capacity_horizon_is_not_reported_as_placed():
    result = place_resource_dependent_assignments(
        facts=(
            fact(
                "AS-FLEX",
                driving=False,
                periods=(("2026-10-19", "8"),),
                rate="8",
            ),
        ),
        activities=activities(),
        capacities=capacity(
            "AS-FLEX",
            ("2026-10-19", "2026-10-20", "2026-10-21"),
            units="0",
        ),
    )

    assert result.status == PLACEMENT_FAILED
    assert result.assignments[0].diagnostic_code == "RESOURCE_DEPENDENT_CAPACITY_HORIZON_EXHAUSTED"


def test_demand_row_count_mismatch_returns_assignment_diagnostic():
    result = place_resource_dependent_assignments(
        facts=(
            fact(
                "AS-FLEX",
                driving=False,
                periods=(("2026-10-19", "4"),),
            ),
        ),
        activities=activities(),
        capacities=capacity("AS-FLEX", ("2026-10-19", "2026-10-20", "2026-10-21")),
    )

    assert result.status == PLACEMENT_FAILED
    failed = result.assignments[0]
    assert failed.status == ASSIGNMENT_FAILED
    assert failed.diagnostic_code == "RESOURCE_DEPENDENT_DEMAND_PERIOD_COUNT_MISMATCH"
    assert failed.start is None and failed.finish is None


def test_zero_unit_demand_row_is_not_silently_interpreted_as_duration():
    result = place_resource_dependent_assignments(
        facts=(
            fact(
                "AS-FLEX",
                driving=False,
                periods=(("2026-10-19", "8"), ("2026-10-20", "0")),
            ),
        ),
        activities=activities(),
        capacities=capacity("AS-FLEX", ("2026-10-19", "2026-10-20", "2026-10-21")),
    )

    assert result.status == PLACEMENT_FAILED
    assert (
        result.assignments[0].diagnostic_code
        == "RESOURCE_DEPENDENT_ZERO_DEMAND_PERIOD_UNSUPPORTED"
    )


def test_source_period_gap_on_a_working_day_is_not_recompressed():
    result = place_resource_dependent_assignments(
        facts=(
            fact(
                "AS-FLEX",
                driving=False,
                # Oct 20 is a positive-capacity working day but has no persisted
                # demand row. Treating the rows as consecutive would silently
                # place the Oct 21 units on Oct 20.
                periods=(("2026-10-19", "4"), ("2026-10-21", "4")),
            ),
        ),
        activities=activities(),
        capacities=capacity("AS-FLEX", ("2026-10-19", "2026-10-20", "2026-10-21")),
    )

    assert result.status == PLACEMENT_FAILED
    assert (
        result.assignments[0].diagnostic_code
        == "RESOURCE_DEPENDENT_SOURCE_PERIOD_GAP"
    )
    assert result.assignments[0].start is None


def test_source_period_missing_from_capacity_ledger_is_explicit():
    result = place_resource_dependent_assignments(
        facts=(
            fact(
                "AS-FLEX",
                driving=False,
                periods=(("2026-10-19", "4"), ("2026-10-20", "4")),
            ),
        ),
        activities=activities(),
        capacities=capacity_values(
            "AS-FLEX",
            (("2026-10-19", "8"), ("2026-10-21", "8")),
        ),
    )

    assert result.status == PLACEMENT_FAILED
    assert (
        result.assignments[0].diagnostic_code
        == "RESOURCE_DEPENDENT_SOURCE_PERIOD_CAPACITY_NOT_FOUND:2026-10-20"
    )


def test_weekend_gap_between_source_periods_is_preserved():
    result = place_resource_dependent_assignments(
        facts=(
            fact(
                "AS-DRIVE",
                driving=True,
                periods=(("2026-10-23", "4"), ("2026-10-26", "4")),
            ),
        ),
        activities=activities(start="2026-10-23", finish="2026-10-26"),
        capacities=capacity_values(
            "AS-DRIVE",
            (
                ("2026-10-23", "8"),
                ("2026-10-24", "0"),
                ("2026-10-25", "0"),
                ("2026-10-26", "8"),
            ),
        ),
    )

    assert result.status == PLACEMENT_COMPLETE
    placed = result.assignments[0]
    assert placed.status == ASSIGNMENT_FIXED_DRIVING
    assert placed.start == date(2026, 10, 23)
    assert placed.finish == date(2026, 10, 26)
    assert [
        (item.source_period_start, item.period)
        for item in placed.demand_periods
    ] == [
        (date(2026, 10, 23), date(2026, 10, 23)),
        (date(2026, 10, 26), date(2026, 10, 26)),
    ]


def test_variable_capacity_selects_a_later_fitting_window():
    result = place_resource_dependent_assignments(
        facts=(
            fact(
                "AS-FLEX",
                driving=False,
                periods=(
                    ("2026-10-19", "4"),
                    ("2026-10-20", "4"),
                    ("2026-10-21", "4"),
                ),
                planned="12",
            ),
        ),
        activities=activities(),
        capacities=capacity_values(
            "AS-FLEX",
            (
                ("2026-10-19", "2"),
                ("2026-10-20", "2"),
                ("2026-10-21", "4"),
                ("2026-10-22", "4"),
                ("2026-10-23", "8"),
            ),
        ),
    )

    assert result.status == PLACEMENT_COMPLETE
    placed = result.assignments[0]
    assert placed.status == ASSIGNMENT_PLACED
    assert placed.start == date(2026, 10, 21)
    assert placed.finish == date(2026, 10, 23)
    assert [
        item.period for item in placed.demand_periods
    ] == [date(2026, 10, 21), date(2026, 10, 22), date(2026, 10, 23)]
    assert [
        item.source_period_start for item in placed.demand_periods
    ] == [date(2026, 10, 19), date(2026, 10, 20), date(2026, 10, 21)]


def test_nondriving_without_demand_periods_is_not_silently_dropped():
    result = place_resource_dependent_assignments(
        facts=(fact("AS-FLEX", driving=False, periods=()),),
        activities=activities(),
        capacities=capacity("AS-FLEX", ("2026-10-19",)),
    )

    assert result.status == PLACEMENT_FAILED
    assert (
        result.assignments[0].diagnostic_code
        == "RESOURCE_DEPENDENT_ASSIGNMENT_PERIODS_REQUIRED"
    )


def test_driving_demand_must_fit_at_the_authoritative_activity_start():
    result = place_resource_dependent_assignments(
        facts=(
            fact(
                "AS-DRIVE",
                driving=True,
                periods=(("2026-10-19", "8"),),
                rate="8",
            ),
        ),
        activities=activities(),
        capacities=capacity(
            "AS-DRIVE",
            ("2026-10-19", "2026-10-20", "2026-10-21"),
            units="4",
        ),
    )

    assert result.status == PLACEMENT_FAILED
    assert result.assignments[0].diagnostic_code == "RESOURCE_DEPENDENT_DRIVING_CAPACITY_EXCEEDED"
    assert result.assignments[0].status == ASSIGNMENT_FAILED


def test_driving_capacity_must_exist_at_activity_start_not_a_later_date():
    result = place_resource_dependent_assignments(
        facts=(
            fact(
                "AS-DRIVE",
                driving=True,
                periods=(("2026-10-19", "4"),),
                planned="4",
            ),
        ),
        activities=activities(),
        capacities=capacity(
            "AS-DRIVE",
            ("2026-10-20", "2026-10-21"),
        ),
    )

    assert result.status == PLACEMENT_FAILED
    assert (
        result.assignments[0].diagnostic_code
        == "RESOURCE_DEPENDENT_DRIVING_CAPACITY_NOT_AT_ACTIVITY_START"
    )


def test_capacity_calendar_mismatch_is_an_assignment_diagnostic():
    result = place_resource_dependent_assignments(
        facts=(
            fact(
                "AS-FLEX",
                driving=False,
                periods=(("2026-10-19", "1"),),
                planned="1",
                rate="1",
                calendar_version="v2",
            ),
        ),
        activities=activities(),
        capacities=capacity("AS-FLEX", ("2026-10-19",)),
    )

    assert result.status == PLACEMENT_FAILED
    assert (
        result.assignments[0].diagnostic_code
        == "RESOURCE_DEPENDENT_RESOURCE_CALENDAR_MISMATCH"
    )


def test_committed_demand_overlap_is_rejected_instead_of_double_counted():
    with pytest.raises(
        ResourceDependentPlacementError,
        match="RESOURCE_DEPENDENT_COMMITTED_DEMAND_OVERLAP",
    ):
        place_resource_dependent_assignments(
            facts=(
                fact(
                    "AS-FLEX",
                    driving=False,
                    periods=(("2026-10-19", "1"),),
                    planned="1",
                    rate="1",
                ),
            ),
            activities=activities(),
            capacities=capacity("AS-FLEX", ("2026-10-19",)),
            committed_demands=(
                ResourceDemand(
                    "AS-FLEX",
                    date(2026, 10, 19),
                    Decimal("1"),
                    "RD-1",
                    assignment_id="AS-FLEX",
                ),
            ),
        )


def test_demands_at_final_schedule_shifts_and_preserves_assignment_identity():
    forward = (
        LevelingActivity(
            "RD-1",
            date(2026, 10, 19),
            date(2026, 10, 21),
            0,
            (
                ResourceDemand(
                    "R-1",
                    date(2026, 10, 19),
                    Decimal("4"),
                    "RD-1",
                    assignment_id="AS-1",
                    is_driving=True,
                ),
            ),
        ),
    )

    class Resolver:
        def working_days_between(self, start, finish):
            return (finish - start).days

        def add_working_duration(self, value, count):
            return date.fromordinal(value.toordinal() + count - 1)

        def subtract_working_duration(self, value, count):
            return date.fromordinal(value.toordinal() - count + 1)

    shifted = demands_at_final_schedule(
        forward_activities=forward,
        final_activities={
            "RD-1": SimpleNamespace(start=date(2026, 10, 21), finish=date(2026, 10, 23))
        },
        resolver=Resolver(),
    )

    assert shifted == (
        ResourceDemand(
            "R-1",
            date(2026, 10, 21),
            Decimal("4"),
            "RD-1",
            assignment_id="AS-1",
            is_driving=True,
        ),
    )


def _two_activity_priority_activities(
    *,
    priority_a: int = 3,
    priority_b: int = 3,
) -> dict[str, LevelingActivity]:
    return {
        "A-TASK": LevelingActivity(
            "A-TASK",
            date(2026, 10, 19),
            date(2026, 10, 19),
            10,
            activity_priority=priority_a,
        ),
        "B-TASK": LevelingActivity(
            "B-TASK",
            date(2026, 10, 19),
            date(2026, 10, 19),
            10,
            activity_priority=priority_b,
        ),
    }


def _two_activity_dates() -> dict[str, SimpleNamespace]:
    return {
        activity_id: SimpleNamespace(
            start=date(2026, 10, 19),
            finish=date(2026, 10, 19),
        )
        for activity_id in ("A-TASK", "B-TASK")
    }


def _competing_nondriving_facts() -> tuple[ResourceDependentDriverFact, ...]:
    return tuple(
        fact(
            f"AS-{activity_id[0]}",
            activity_id=activity_id,
            resource_id="R-SHARED",
            driving=False,
            periods=(("2026-10-19", "8"),),
            planned="8",
            rate="8",
        )
        for activity_id in ("A-TASK", "B-TASK")
    )


def test_competing_nondriving_assignments_follow_p6_default_activity_id_order():
    facts = _competing_nondriving_facts()
    kwargs = {
        "activities": _two_activity_dates(),
        "capacities": capacity("R-SHARED", ("2026-10-19", "2026-10-20"), units="8"),
        "priority_activities": _two_activity_priority_activities(),
    }

    result = place_resource_dependent_assignments(facts=facts, **kwargs)

    assert result.status == PLACEMENT_COMPLETE
    by_id = {item.assignment_id: item for item in result.assignments}
    # P6 with no priority list sorts by Activity ID and levels the lower ID
    # first. The first-leveled activity therefore receives the later window.
    assert by_id["AS-A"].start == date(2026, 10, 20)
    assert by_id["AS-B"].start == date(2026, 10, 19)
    assert by_id["AS-A"].activity_priority_rank == 1
    assert by_id["AS-B"].activity_priority_rank == 2
    assert result.priorities == ()
    assert result.to_payload()["priority_fields"] == []

    replay = place_resource_dependent_assignments(
        facts=tuple(reversed(facts)),
        **kwargs,
    )
    assert replay.to_payload() == result.to_payload()


@pytest.mark.parametrize(
    ("sort_order", "delayed_assignment_id"),
    [
        (SortOrder.ASCENDING, "AS-A"),
        (SortOrder.DESCENDING, "AS-B"),
    ],
)
def test_competing_nondriving_assignments_follow_configured_activity_priority(
    sort_order,
    delayed_assignment_id,
):
    priorities = (LevelingPriority("activity_priority", sort_order),)
    result = place_resource_dependent_assignments(
        facts=_competing_nondriving_facts(),
        activities=_two_activity_dates(),
        capacities=capacity("R-SHARED", ("2026-10-19", "2026-10-20"), units="8"),
        # A is the lowest priority level and B the top level.
        priority_activities=_two_activity_priority_activities(
            priority_a=1,
            priority_b=5,
        ),
        priorities=priorities,
    )

    by_id = {item.assignment_id: item for item in result.assignments}
    delayed = by_id[delayed_assignment_id]
    earlier = by_id["AS-B" if delayed_assignment_id == "AS-A" else "AS-A"]
    assert delayed.start == date(2026, 10, 20)
    assert earlier.start == date(2026, 10, 19)
    assert delayed.activity_priority_rank == 1
    assert earlier.activity_priority_rank == 2
    assert result.to_payload()["priority_fields"] == [
        {"field_name": "activity_priority", "sort_order": sort_order.value}
    ]


def test_nondriving_priority_direction_matches_shared_core_forward_leveling():
    from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
    from construction_pm.scheduling.resource_leveling import (
        propose_forward_leveling_within_float,
    )

    priorities = (LevelingPriority("activity_priority", SortOrder.ASCENDING),)
    forward = tuple(
        LevelingActivity(
            activity.activity_id,
            activity.start,
            activity.finish,
            activity.total_float,
            activity_priority=activity.activity_priority,
            resource_demands=(
                ResourceDemand(
                    "R-SHARED",
                    date(2026, 10, 19),
                    Decimal("8"),
                    activity.activity_id,
                    assignment_id=f"AS-{activity.activity_id[0]}",
                ),
            ),
        )
        for activity in _two_activity_priority_activities(
            priority_a=1,
            priority_b=5,
        ).values()
    )
    shifts = propose_forward_leveling_within_float(
        forward,
        capacity("R-SHARED", ("2026-10-19", "2026-10-20"), units="8"),
        resolver=WorkingTimeResolver(WorkingCalendar()),
        priorities=priorities,
        level_all_resources=True,
    )

    result = place_resource_dependent_assignments(
        facts=_competing_nondriving_facts(),
        activities=_two_activity_dates(),
        capacities=capacity("R-SHARED", ("2026-10-19", "2026-10-20"), units="8"),
        priority_activities=_two_activity_priority_activities(
            priority_a=1,
            priority_b=5,
        ),
        priorities=priorities,
    )

    by_id = {item.assignment_id: item for item in result.assignments}
    # The Shared Core levels A-TASK (lower priority, ascending) first. The
    # independent assignment placement delays the same activity by one day.
    assert [(shift.activity_id, shift.shift_working_days) for shift in shifts] == [
        ("A-TASK", 1)
    ]
    assert by_id["AS-A"].start == date(2026, 10, 20)
    assert by_id["AS-B"].start == date(2026, 10, 19)


def test_configured_priority_order_is_bound_to_the_placement_input_hash():
    kwargs = {
        "facts": _competing_nondriving_facts(),
        "activities": _two_activity_dates(),
        "capacities": capacity("R-SHARED", ("2026-10-19", "2026-10-20"), units="8"),
        "priority_activities": _two_activity_priority_activities(
            priority_a=1,
            priority_b=5,
        ),
    }
    ascending = place_resource_dependent_assignments(
        priorities=(LevelingPriority("activity_priority", SortOrder.ASCENDING),),
        **kwargs,
    )
    descending = place_resource_dependent_assignments(
        priorities=(LevelingPriority("activity_priority", SortOrder.DESCENDING),),
        **kwargs,
    )

    assert ascending.input_hash != descending.input_hash
    assert {
        item.assignment_id: item.activity_priority_rank for item in ascending.assignments
    } == {"AS-A": 1, "AS-B": 2}
    assert {
        item.assignment_id: item.activity_priority_rank for item in descending.assignments
    } == {"AS-B": 1, "AS-A": 2}


def test_priority_context_is_required_for_configured_priorities():
    with pytest.raises(
        ResourceDependentPlacementError,
        match="RESOURCE_DEPENDENT_PRIORITY_CONTEXT_REQUIRED",
    ):
        place_resource_dependent_assignments(
            facts=_competing_nondriving_facts(),
            activities=_two_activity_dates(),
            capacities=capacity("R-SHARED", ("2026-10-19", "2026-10-20"), units="8"),
            priorities=(LevelingPriority("activity_priority", SortOrder.ASCENDING),),
        )


def test_missing_priority_activity_fails_closed():
    priority_activities = _two_activity_priority_activities()
    del priority_activities["B-TASK"]

    with pytest.raises(
        ResourceDependentPlacementError,
        match="RESOURCE_DEPENDENT_PRIORITY_ACTIVITY_MISSING:B-TASK",
    ):
        place_resource_dependent_assignments(
            facts=_competing_nondriving_facts(),
            activities=_two_activity_dates(),
            capacities=capacity("R-SHARED", ("2026-10-19", "2026-10-20"), units="8"),
            priority_activities=priority_activities,
        )
