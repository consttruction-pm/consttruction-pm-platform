from dataclasses import asdict
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from construction_pm.scheduling.resource_leveling import ResourceCapacity
from construction_pm.scheduling.resource_leveling_input import (
    ResourceAssignmentLevelingRef,
    ResourceCapacityRate,
    ResourceDemandInput,
    ResourceLevelingFacts,
    ResourceLevelingFactsError,
)


def _facts(
    *, capacities, is_driving=None, units_per_time=None,
    units_per_time_period=None, hours_per_units_time_period=None,
):
    assignment = ResourceAssignmentLevelingRef(
        assignment_id="ASSIGN-A",
        activity_id="A",
        resource_id="R1",
        calendar_id="RES-CAL-1",
        calendar_version="v1",
        unit_of_measure="h",
        assigned_units=Decimal("8"),
        remaining_units=Decimal("8"),
        is_driving=is_driving,
        units_per_time=units_per_time,
        units_per_time_period=units_per_time_period,
        hours_per_units_time_period=hours_per_units_time_period,
    )
    return ResourceLevelingFacts(
        assignments=(assignment,),
        demands=(
            ResourceDemandInput(
                assignment_id="ASSIGN-A",
                activity_id="A",
                resource_id="R1",
                period=date(2026, 10, 19),
                units=Decimal("8"),
            ),
        ),
        capacities=tuple(capacities),
        resource_capacity_rates=(_rate(),),
        capacity_horizon_start=date(2026, 10, 19),
        capacity_horizon_end=date(2026, 10, 20),
        calculation_timezone="UTC",
    )


def _rate() -> ResourceCapacityRate:
    return ResourceCapacityRate(
        resource_id="R1",
        effective_from=datetime(2026, 10, 18, tzinfo=timezone.utc),
        max_units_per_time=Decimal("8"),
        time_period_unit="day",
        hours_per_time_period=Decimal("8"),
        unit_of_measure="h",
        time_period_source="global",
    )


def _capacity(day: date, *, calendar_version: str = "v1", units: str = "8") -> ResourceCapacity:
    rate = _rate()
    return ResourceCapacity(
        resource_id="R1",
        period=day,
        units=Decimal(units),
        calendar_id="RES-CAL-1",
        calendar_version=calendar_version,
        calendar_snapshot_hash="a" * 64,
        calendar_work_hours=Decimal("8"),
        resource_rate_hash=rate.profile_hash,
        resource_rate_effective_from=rate.effective_from,
    )


def test_resource_leveling_facts_accept_complete_versioned_capacity_horizon():
    facts = _facts(capacities=(
        _capacity(date(2026, 10, 19)),
        _capacity(date(2026, 10, 20)),
    ))

    facts.validate(activity_ids={"A"})


def test_resource_leveling_facts_reject_missing_capacity_inside_horizon():
    facts = _facts(capacities=(_capacity(date(2026, 10, 19)),))

    with pytest.raises(ResourceLevelingFactsError, match="RESOURCE_CAPACITY_PERIOD_MISSING"):
        facts.validate(activity_ids={"A"})


def test_resource_leveling_facts_reject_capacity_from_wrong_calendar_version():
    wrong_version = ResourceCapacity(
        resource_id="R1",
        period=date(2026, 10, 20),
        units=Decimal("8"),
        calendar_id="RES-CAL-1",
        calendar_version="v2",
        calendar_snapshot_hash="b" * 64,
        calendar_work_hours=Decimal("8"),
        resource_rate_hash=_rate().profile_hash,
        resource_rate_effective_from=_rate().effective_from,
    )
    facts = _facts(capacities=(
        _capacity(date(2026, 10, 19)),
        wrong_version,
    ))

    with pytest.raises(ResourceLevelingFactsError, match="RESOURCE_CAPACITY_CALENDAR_MISMATCH"):
        facts.validate(activity_ids={"A"})


def test_resource_leveling_facts_reject_unbounded_capacity_horizon():
    assignment = ResourceAssignmentLevelingRef(
        assignment_id="ASSIGN-A",
        activity_id="A",
        resource_id="R1",
        calendar_id="RES-CAL-1",
        calendar_version="v1",
        unit_of_measure="h",
        assigned_units=Decimal("8"),
        remaining_units=Decimal("8"),
    )
    start = date(2026, 10, 19)
    end = date.fromordinal(start.toordinal() + 36501)
    facts = ResourceLevelingFacts(
        assignments=(assignment,),
        demands=(
            ResourceDemandInput(
                assignment_id="ASSIGN-A",
                activity_id="A",
                resource_id="R1",
                period=start,
                units=Decimal("8"),
            ),
        ),
        capacities=(_capacity(start),),
        resource_capacity_rates=(_rate(),),
        capacity_horizon_start=start,
        capacity_horizon_end=end,
        calculation_timezone="UTC",
    )

    with pytest.raises(
        ResourceLevelingFactsError,
        match="RESOURCE_LEVELING_CAPACITY_HORIZON_OUT_OF_RANGE",
    ):
        facts.validate(activity_ids={"A"})



@pytest.mark.parametrize("is_driving", [True, False])
def test_resource_leveling_facts_preserve_explicit_assignment_driving_status(is_driving):
    facts = _facts(
        capacities=(
            _capacity(date(2026, 10, 19)),
            _capacity(date(2026, 10, 20)),
        ),
        is_driving=is_driving,
    )

    facts.validate(activity_ids={"A"})

    assert facts.assignments[0].is_driving is is_driving


def test_resource_leveling_facts_reject_non_boolean_assignment_driving_status():
    facts = _facts(
        capacities=(
            _capacity(date(2026, 10, 19)),
            _capacity(date(2026, 10, 20)),
        ),
        is_driving="true",
    )

    with pytest.raises(
        ResourceLevelingFactsError,
        match="INVALID_ASSIGNMENT_DRIVING_FLAG",
    ):
        facts.validate(activity_ids={"A"})



def test_resource_leveling_facts_preserve_assignment_units_per_time():
    facts = _facts(
        capacities=(
            _capacity(date(2026, 10, 19)),
            _capacity(date(2026, 10, 20)),
        ),
        is_driving=True,
        units_per_time=Decimal("2.5"),
        units_per_time_period="day",
        hours_per_units_time_period=Decimal("8"),
    )

    facts.validate(activity_ids={"A"})

    assignment = facts.assignments[0]
    assert assignment.is_driving is True
    assert assignment.units_per_time == Decimal("2.5")
    assert assignment.units_per_time_period == "day"
    assert assignment.hours_per_units_time_period == Decimal("8")
    payload = asdict(assignment)
    assert payload["units_per_time"] == Decimal("2.5")
    assert payload["units_per_time_period"] == "day"
    assert payload["hours_per_units_time_period"] == Decimal("8")


@pytest.mark.parametrize(
    "kwargs, error",
    [
        (
            {"units_per_time": Decimal("2")},
            "INCOMPLETE_ASSIGNMENT_UNITS_PER_TIME",
        ),
        (
            {"units_per_time": Decimal("2"), "units_per_time_period": "decade",
             "hours_per_units_time_period": Decimal("8")},
            "INVALID_ASSIGNMENT_UNITS_PER_TIME_PERIOD",
        ),
    ],
)
def test_resource_leveling_facts_reject_incomplete_assignment_units_per_time(kwargs, error):
    facts = _facts(
        capacities=(
            _capacity(date(2026, 10, 19)),
            _capacity(date(2026, 10, 20)),
        ),
        **kwargs,
    )
    with pytest.raises(ResourceLevelingFactsError, match=error):
        facts.validate(activity_ids={"A"})
