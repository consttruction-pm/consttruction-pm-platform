from datetime import date
from decimal import Decimal

import pytest

from construction_pm.scheduling.resource_dependent import (
    ResourceDependentCalculationError,
    ResourceDependentDemandPeriod,
    ResourceDependentDriverFact,
    derive_resource_dependent_duration,
)


def driver(
    assignment_id: str,
    *,
    activity_id: str = "RD-1",
    resource_id: str | None = None,
    calendar_id: str = "RC-1",
    calendar_version: str = "v2",
    unit: str = "labor-unit",
    planned: str | None = "8",
    driving: bool | None = True,
    rate: str = "4",
    period: str = "day",
    hours: str = "8",
) -> ResourceDependentDriverFact:
    return ResourceDependentDriverFact(
        assignment_id=assignment_id,
        activity_id=activity_id,
        resource_id=resource_id or assignment_id,
        calendar_id=calendar_id,
        calendar_version=calendar_version,
        unit_of_measure=unit,
        planned_units=None if planned is None else Decimal(planned),
        is_driving=driving,
        units_per_time=None if rate is None else Decimal(rate),
        units_per_time_period=period,
        hours_per_units_time_period=None if hours is None else Decimal(hours),
    )


def derive(*assignments: ResourceDependentDriverFact):
    return derive_resource_dependent_duration(
        tenant_id="T-1",
        project_id="P-1",
        project_revision=7,
        activity_id="RD-1",
        assignments=tuple(assignments),
    )


def test_longest_driving_resource_controls_whole_working_day_duration():
    result = derive(
        driver("A-1", planned="8", rate="4"),
        driver("B-1", planned="9", rate="3"),
    )

    assert result.duration_working_days == 3
    assert result.calendar_id == "RC-1"
    assert result.calendar_version == "v2"
    assert result.driving_assignment_ids == ("A-1", "B-1")
    assert len(result.input_hash) == 64


def test_derivation_is_deterministic_independent_of_input_order():
    first = derive(driver("A-1", planned="8", rate="4"), driver("B-1", planned="9", rate="3"))
    second = derive(driver("B-1", planned="9", rate="3"), driver("A-1", planned="8", rate="4"))
    assert first == second


@pytest.mark.parametrize(
    ("facts", "code"),
    [
        ((), "RESOURCE_DEPENDENT_DRIVING_ASSIGNMENT_REQUIRED"),
        ((driver("A-1", driving=None),), "RESOURCE_DEPENDENT_DRIVING_FLAG_REQUIRED"),
        ((driver("A-1", driving=False),), "RESOURCE_DEPENDENT_DRIVING_ASSIGNMENT_REQUIRED"),
        ((driver("A-1", calendar_version=None),), "RESOURCE_DEPENDENT_DRIVER_CALENDAR_VERSION_REQUIRED"),
        ((driver("A-1", period="week"),), "RESOURCE_DEPENDENT_NONDAILY_RATE_UNSUPPORTED"),
        ((driver("A-1", planned="5", rate="2"),), "RESOURCE_DEPENDENT_FRACTIONAL_DURATION_UNSUPPORTED"),
    ],
)
def test_unsupported_or_ambiguous_driving_contract_fails_closed(facts, code):
    with pytest.raises(ResourceDependentCalculationError, match=code):
        derive(*facts)


def test_nondriving_assignments_never_contribute_to_activity_duration():
    driving_only = derive(driver("A-1", planned="8", rate="4"))
    mixed = derive(
        driver("A-1", planned="8", rate="4"),
        driver("A-2", driving=False, planned="100", rate="1"),
    )

    assert mixed.duration_working_days == 2
    assert mixed.duration_source == "driving"
    assert mixed.driving_assignment_ids == ("A-1",)
    # The nondriving fact still binds the immutable input, so the hash changes.
    assert mixed.input_hash != driving_only.input_hash


def test_all_nondriving_activity_uses_persisted_duration_without_inventing_driver():
    result = derive_resource_dependent_duration(
        tenant_id="T-1",
        project_id="P-1",
        project_revision=7,
        activity_id="RD-1",
        assignments=(driver("A-2", driving=False),),
        fallback_duration_working_days=5,
        fallback_calendar_id="ACT-CAL",
        fallback_calendar_version="v9",
    )

    assert result.duration_working_days == 5
    assert result.duration_source == "activity"
    assert result.driving_assignment_ids == ()
    assert result.calendar_id == "ACT-CAL"
    assert result.calendar_version == "v9"
    assert len(result.input_hash) == 64


def test_all_nondriving_requires_authoritative_activity_duration_and_calendar():
    with pytest.raises(ResourceDependentCalculationError, match="RESOURCE_DEPENDENT_DRIVING_ASSIGNMENT_REQUIRED"):
        derive(driver("A-2", driving=False))

    with pytest.raises(ResourceDependentCalculationError, match="RESOURCE_DEPENDENT_ACTIVITY_CALENDAR_REQUIRED"):
        derive_resource_dependent_duration(
            tenant_id="T-1",
            project_id="P-1",
            project_revision=7,
            activity_id="RD-1",
            assignments=(driver("A-2", driving=False),),
            fallback_duration_working_days=5,
            fallback_calendar_version="v9",
        )

    with pytest.raises(ResourceDependentCalculationError, match="RESOURCE_DEPENDENT_ACTIVITY_CALENDAR_VERSION_REQUIRED"):
        derive_resource_dependent_duration(
            tenant_id="T-1",
            project_id="P-1",
            project_revision=7,
            activity_id="RD-1",
            assignments=(driver("A-2", driving=False),),
            fallback_duration_working_days=5,
            fallback_calendar_id="ACT-CAL",
        )


def test_all_nondriving_still_requires_versioned_resource_calendar_for_placement():
    with pytest.raises(ResourceDependentCalculationError, match="RESOURCE_DEPENDENT_NONDRIVING_CALENDAR_VERSION_REQUIRED"):
        derive_resource_dependent_duration(
            tenant_id="T-1",
            project_id="P-1",
            project_revision=7,
            activity_id="RD-1",
            assignments=(driver("A-2", driving=False, calendar_version=None),),
            fallback_duration_working_days=5,
            fallback_calendar_id="ACT-CAL",
            fallback_calendar_version="v9",
        )


def test_demand_periods_are_part_of_the_canonical_hash_and_order_independent():
    first = driver(
        "A-1",
        planned="8",
        rate="4",
    )
    period = ResourceDependentDemandPeriod(date(2026, 10, 19), Decimal("8"))
    other_period = ResourceDependentDemandPeriod(date(2026, 10, 20), Decimal("4"))
    with_periods = ResourceDependentDriverFact(
        **{**first.__dict__, "demand_periods": (other_period, period)}
    )
    reordered = ResourceDependentDriverFact(
        **{**first.__dict__, "demand_periods": (period, other_period)}
    )
    without_periods = derive(first)

    assert derive(with_periods) == derive(reordered)
    assert derive(with_periods).input_hash != without_periods.input_hash


def test_invalid_demand_periods_fail_closed():
    first = driver("A-1", planned="8", rate="4")
    duplicate = ResourceDependentDriverFact(
        **{
            **first.__dict__,
            "demand_periods": (
                ResourceDependentDemandPeriod(date(2026, 10, 19), Decimal("1")),
                ResourceDependentDemandPeriod(date(2026, 10, 19), Decimal("2")),
            ),
        }
    )
    with pytest.raises(ResourceDependentCalculationError, match="DUPLICATE_RESOURCE_DEPENDENT_DEMAND_PERIOD"):
        derive(duplicate)

    negative = ResourceDependentDriverFact(
        **{
            **first.__dict__,
            "demand_periods": (
                ResourceDependentDemandPeriod(date(2026, 10, 19), Decimal("-1")),
            ),
        }
    )
    with pytest.raises(ResourceDependentCalculationError, match="INVALID_RESOURCE_DEPENDENT_DEMAND_UNITS"):
        derive(negative)


def test_driving_assignments_must_share_exact_calendar_version_and_unit():
    with pytest.raises(ResourceDependentCalculationError, match="RESOURCE_DEPENDENT_DRIVING_CALENDAR_MISMATCH"):
        derive(driver("A-1"), driver("A-2", calendar_version="v3"))

    with pytest.raises(ResourceDependentCalculationError, match="RESOURCE_DEPENDENT_DRIVING_UNIT_MISMATCH"):
        derive(driver("A-1"), driver("A-2", unit="equipment-day"))
