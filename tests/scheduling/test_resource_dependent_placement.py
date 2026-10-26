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
from construction_pm.scheduling.resource_leveling import ResourceCapacity, ResourceDemand

HASH = "a" * 64


def fact(
    assignment_id: str,
    *,
    resource_id: str | None = None,
    driving: bool,
    periods: tuple[tuple[str, str], ...],
    calendar_id: str = "RC-1",
    calendar_version: str = "v1",
) -> ResourceDependentDriverFact:
    return ResourceDependentDriverFact(
        assignment_id=assignment_id,
        activity_id="RD-1",
        resource_id=resource_id or assignment_id,
        calendar_id=calendar_id,
        calendar_version=calendar_version,
        unit_of_measure="labor-unit",
        planned_units=Decimal("8"),
        is_driving=driving,
        units_per_time=Decimal("4"),
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


def activities(*, start: str = "2026-10-19", finish: str = "2026-10-21"):
    return {"RD-1": SimpleNamespace(start=date.fromisoformat(start), finish=date.fromisoformat(finish))}


def test_driving_and_nondriving_assignments_place_independently():
    facts = (
        fact("AS-DRIVE", driving=True, periods=(("2026-10-19", "4"),)),
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
    assert by_id["AS-FLEX"].status == ASSIGNMENT_PLACED
    # The nondriving assignment starts after full Task Dependent load and never
    # changes the activity's authoritative dates.
    assert by_id["AS-FLEX"].start == date(2026, 10, 20)
    assert by_id["AS-FLEX"].finish == date(2026, 10, 21)
    assert by_id["AS-FLEX"].total_units == Decimal("8")
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
                periods=(("2026-10-19", "8"), ("2026-10-20", "8")),
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


def test_nondriving_capacity_exhaustion_returns_assignment_diagnostic():
    result = place_resource_dependent_assignments(
        facts=(
            fact(
                "AS-FLEX",
                driving=False,
                periods=(("2026-10-19", "8"),),
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
    from construction_pm.scheduling.resource_leveling import LevelingActivity

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
