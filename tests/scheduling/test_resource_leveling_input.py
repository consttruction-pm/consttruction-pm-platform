from datetime import date
from decimal import Decimal

import pytest

from construction_pm.scheduling.resource_leveling import ResourceCapacity
from construction_pm.scheduling.resource_leveling_input import (
    ResourceAssignmentLevelingRef,
    ResourceDemandInput,
    ResourceLevelingFacts,
    ResourceLevelingFactsError,
)


def _facts(*, capacities):
    assignment = ResourceAssignmentLevelingRef(
        assignment_id="ASSIGN-A",
        activity_id="A",
        resource_id="R1",
        calendar_id="RES-CAL-1",
        calendar_version="v1",
        assigned_units=Decimal("8"),
        remaining_units=Decimal("8"),
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
        capacity_horizon_start=date(2026, 10, 19),
        capacity_horizon_end=date(2026, 10, 20),
    )


def _capacity(day: date) -> ResourceCapacity:
    return ResourceCapacity(
        resource_id="R1",
        period=day,
        units=Decimal("8"),
        calendar_id="RES-CAL-1",
        calendar_version="v1",
        calendar_snapshot_hash="a" * 64,
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
    )
    facts = _facts(capacities=(
        _capacity(date(2026, 10, 19)),
        wrong_version,
    ))

    with pytest.raises(ResourceLevelingFactsError, match="RESOURCE_CAPACITY_CALENDAR_MISMATCH"):
        facts.validate(activity_ids={"A"})
