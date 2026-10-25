from decimal import Decimal

import pytest

from construction_pm.scheduling.resource_dependent import (
    ResourceDependentCalculationError,
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


def test_nondriving_assignment_does_not_determine_activity_duration():
    result = derive(
        driver("A-1", planned="8", rate="4", driving=True),
        driver("A-2", planned="100", rate="1", driving=False),
    )

    # Activity duration follows the driving assignment only; the nondriving
    # assignment is retained in the input hash for its separate placement path.
    assert result.duration_working_days == 2
    assert result.driving_assignment_ids == ("A-1",)
    assert len(result.input_hash) == 64


@pytest.mark.parametrize("driving", [1, 0, "true", "false"])
def test_driving_flag_requires_an_actual_boolean(driving):
    with pytest.raises(
        ResourceDependentCalculationError,
        match="INVALID_RESOURCE_DEPENDENT_DRIVING_FLAG",
    ):
        derive(driver("A-1", driving=driving))


def test_duplicate_assignment_ids_are_rejected_before_duration_derivation():
    with pytest.raises(
        ResourceDependentCalculationError,
        match="DUPLICATE_RESOURCE_DEPENDENT_ASSIGNMENT_ID",
    ):
        derive(driver("A-1"), driver("A-1", resource_id="R-2"))


def test_non_string_assignment_id_is_rejected_before_sorting():
    from dataclasses import replace

    with pytest.raises(
        ResourceDependentCalculationError,
        match="RESOURCE_DEPENDENT_ASSIGNMENT_ID_REQUIRED",
    ):
        derive(replace(driver("A-1"), assignment_id=1), driver("A-2"))


@pytest.mark.parametrize(
    ("assignment_id", "resource_id"),
    [(" A-1", "R-1"), ("A-1", " R-1"), ("A-1 ", "R-1"), ("A-1", "R-1 ")],
)
def test_noncanonical_assignment_and_resource_ids_are_rejected(assignment_id, resource_id):
    with pytest.raises(
        ResourceDependentCalculationError,
        match="RESOURCE_DEPENDENT_ASSIGNMENT_ID_REQUIRED",
    ):
        derive(driver(assignment_id, resource_id=resource_id))


def test_driving_assignments_must_share_exact_calendar_version_and_unit():
    with pytest.raises(ResourceDependentCalculationError, match="RESOURCE_DEPENDENT_DRIVING_CALENDAR_MISMATCH"):
        derive(driver("A-1"), driver("A-2", calendar_version="v3"))

    with pytest.raises(ResourceDependentCalculationError, match="RESOURCE_DEPENDENT_DRIVING_UNIT_MISMATCH"):
        derive(driver("A-1"), driver("A-2", unit="equipment-day"))
