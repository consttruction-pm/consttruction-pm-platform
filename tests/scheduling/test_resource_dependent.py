from dataclasses import replace
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
    actual: str | None = None,
    remaining: str | None = None,
    calendar_hours_per_day: str | None = None,
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
        actual_units=None if actual is None else Decimal(actual),
        remaining_units=None if remaining is None else Decimal(remaining),
        calendar_hours_per_day=(
            None if calendar_hours_per_day is None else Decimal(calendar_hours_per_day)
        ),
    )


def derive(*assignments: ResourceDependentDriverFact):
    return derive_resource_dependent_duration(
        tenant_id="T-1",
        project_id="P-1",
        project_revision=7,
        activity_id="RD-1",
        assignments=tuple(assignments),
    )


def with_periods(
    fact: ResourceDependentDriverFact,
    periods: tuple[tuple[str, str], ...],
) -> ResourceDependentDriverFact:
    return ResourceDependentDriverFact(
        **{
            **fact.__dict__,
            "demand_periods": tuple(
                ResourceDependentDemandPeriod(date.fromisoformat(day), Decimal(units))
                for day, units in periods
            ),
        }
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
    ("planned", "rate", "period", "hours", "calendar_hours", "expected_days"),
    [
        # 100 units at 20/week with a 40-hour week and an 8-hour day = 25 days.
        ("100", "20", "week", "40", "8", 25),
        # 20 units at 0.5/hour with a 1-hour period and 8-hour day = 5 days.
        ("20", "0.5", "hour", "1", "8", 5),
        # A 160-hour month with an 8-hour day and 50 units at 10/month = 100 days.
        ("50", "10", "month", "160", "8", 100),
        # A 10-hour resource day changes the conversion of a weekly rate.
        ("100", "20", "week", "50", "10", 25),
    ],
)
def test_non_daily_rate_converts_through_bound_calendar_hours(
    planned, rate, period, hours, calendar_hours, expected_days
):
    result = derive(
        driver(
            "A-1",
            planned=planned,
            rate=rate,
            period=period,
            hours=hours,
            calendar_hours_per_day=calendar_hours,
        )
    )
    assert result.duration_working_days == expected_days
    assert result.exact_duration_working_days == Decimal(expected_days)


def test_fractional_rate_with_whole_day_result_is_supported():
    result = derive(driver("A-1", planned="5", rate="2.5"))
    assert result.duration_working_days == 2
    # The legacy daily contract has no fractional remainder to bind.
    assert result.exact_duration_working_days is None


def test_weekly_rate_without_calendar_hours_fails_closed():
    with pytest.raises(
        ResourceDependentCalculationError,
        match="RESOURCE_DEPENDENT_CALENDAR_HOURS_PER_DAY_REQUIRED",
    ):
        derive(driver("A-1", planned="100", rate="20", period="week", hours="40"))


@pytest.mark.parametrize(
    ("facts", "code"),
    [
        ((), "RESOURCE_DEPENDENT_DRIVING_ASSIGNMENT_REQUIRED"),
        ((driver("A-1", driving=None),), "RESOURCE_DEPENDENT_DRIVING_FLAG_REQUIRED"),
        ((driver("A-1", driving=False),), "RESOURCE_DEPENDENT_DRIVING_ASSIGNMENT_REQUIRED"),
        ((driver("A-1", calendar_version=None),), "RESOURCE_DEPENDENT_DRIVER_CALENDAR_VERSION_REQUIRED"),
        ((driver("A-1", period="week"),), "RESOURCE_DEPENDENT_CALENDAR_HOURS_PER_DAY_REQUIRED"),
        ((driver("A-1", period="fortnight"),), "RESOURCE_DEPENDENT_RATE_PERIOD_UNSUPPORTED"),
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


def test_demand_distribution_reconciles_planned_units_rate_and_row_count():
    valid = with_periods(
        driver("A-1", planned="8", rate="4"),
        (("2026-10-19", "4"), ("2026-10-20", "4")),
    )
    assert derive(valid).duration_working_days == 2

    cases = (
        (
            with_periods(
                driver("A-1", planned="8", rate="4"),
                (("2026-10-19", "4"), ("2026-10-20", "3")),
            ),
            "RESOURCE_DEPENDENT_DEMAND_UNITS_MISMATCH",
        ),
        (
            with_periods(
                driver("A-1", planned="8", rate="4"),
                (("2026-10-19", "8"),),
            ),
            "RESOURCE_DEPENDENT_DEMAND_PERIOD_COUNT_MISMATCH",
        ),
        (
            with_periods(
                driver("A-1", planned="8", rate="4"),
                (("2026-10-19", "8"), ("2026-10-20", "0")),
            ),
            "RESOURCE_DEPENDENT_ZERO_DEMAND_PERIOD_UNSUPPORTED",
        ),
        (
            with_periods(
                driver("A-1", planned="8", rate=None),
                (("2026-10-19", "4"), ("2026-10-20", "4")),
            ),
            "RESOURCE_DEPENDENT_UNITS_PER_TIME_REQUIRED",
        ),
        (
            with_periods(
                driver("A-1", planned="9", rate="4"),
                (("2026-10-19", "5"), ("2026-10-20", "4")),
            ),
            # 9 units at 4/day is 2.25 exact days, so a date-based schedule
            # occupies three working days; two demand rows are ambiguous.
            "RESOURCE_DEPENDENT_DEMAND_PERIOD_COUNT_MISMATCH",
        ),
    )
    for fact, code in cases:
        with pytest.raises(ResourceDependentCalculationError, match=code):
            derive(fact)

    fractional = with_periods(
        driver("A-1", planned="9", rate="4"),
        (("2026-10-19", "4"), ("2026-10-20", "4"), ("2026-10-21", "1")),
    )
    result = derive(fractional)
    assert result.duration_working_days == 3
    assert result.exact_duration_working_days == Decimal("2.25")


def test_nondriving_demand_distribution_is_validated_independently_of_activity_duration():
    valid = with_periods(
        driver("A-2", driving=False, planned="8", rate="4"),
        (("2026-10-19", "4"), ("2026-10-20", "4")),
    )
    result = derive_resource_dependent_duration(
        tenant_id="T-1",
        project_id="P-1",
        project_revision=7,
        activity_id="RD-1",
        assignments=(valid,),
        fallback_duration_working_days=5,
        fallback_calendar_id="ACT-CAL",
        fallback_calendar_version="v9",
    )
    # The assignment spans two demand days while the activity keeps its own
    # authoritative five-day duration.
    assert result.duration_working_days == 5
    assert result.duration_source == "activity"

    invalid = with_periods(
        driver("A-2", driving=False, planned="8", rate="4"),
        (("2026-10-19", "8"),),
    )
    with pytest.raises(
        ResourceDependentCalculationError,
        match="RESOURCE_DEPENDENT_DEMAND_PERIOD_COUNT_MISMATCH",
    ):
        derive_resource_dependent_duration(
            tenant_id="T-1",
            project_id="P-1",
            project_revision=7,
            activity_id="RD-1",
            assignments=(invalid,),
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
    period = ResourceDependentDemandPeriod(date(2026, 10, 19), Decimal("4"))
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


def test_longest_driving_assignment_selects_its_own_calendar():
    result = derive(
        driver("A-1", planned="8", rate="4", calendar_id="RC-1"),
        driver("A-2", planned="9", rate="3", calendar_id="RC-2", calendar_version="v7"),
    )

    assert result.duration_working_days == 3
    assert (result.calendar_id, result.calendar_version) == ("RC-2", "v7")
    assert result.driving_assignment_ids == ("A-1", "A-2")


def test_driving_calendar_selection_is_independent_of_input_order():
    facts = (
        driver("A-1", planned="8", rate="4", calendar_id="RC-1"),
        driver("A-2", planned="9", rate="3", calendar_id="RC-2", calendar_version="v7"),
    )
    first = derive(*facts)
    second = derive(*reversed(facts))
    assert first == second


def test_equal_duration_tie_between_different_calendars_fails_closed():
    with pytest.raises(
        ResourceDependentCalculationError,
        match="RESOURCE_DEPENDENT_DRIVING_CALENDAR_TIE",
    ):
        derive(
            driver("A-1", planned="8", rate="4", calendar_id="RC-1"),
            driver("A-2", planned="6", rate="3", calendar_id="RC-2", calendar_version="v7"),
        )


def test_equal_duration_tie_on_one_calendar_is_deterministic():
    result = derive(
        driver("A-1", planned="8", rate="4", calendar_id="RC-1"),
        driver("A-2", planned="6", rate="3", calendar_id="RC-1"),
    )

    assert result.duration_working_days == 2
    assert (result.calendar_id, result.calendar_version) == ("RC-1", "v2")


def test_driving_assignments_may_use_different_units_of_measure():
    result = derive(
        driver("A-1", planned="8", rate="4", unit="labor-unit"),
        driver("A-2", planned="9", rate="3", unit="equipment-day"),
    )

    assert result.duration_working_days == 3
    assert result.calendar_id == "RC-1"


@pytest.mark.parametrize(
    ("fact", "code"),
    [
        (
            driver("A-2", calendar_version=None),
            "RESOURCE_DEPENDENT_DRIVER_CALENDAR_VERSION_REQUIRED",
        ),
        (
            driver("A-2", calendar_id=None),
            "RESOURCE_DEPENDENT_DRIVER_CALENDAR_REQUIRED",
        ),
        (
            driver("A-2", unit=None),
            "RESOURCE_DEPENDENT_UNIT_OF_MEASURE_REQUIRED",
        ),
    ],
)
def test_each_driving_assignment_requires_its_own_identity(fact, code):
    with pytest.raises(ResourceDependentCalculationError, match=code):
        derive(driver("A-1"), fact)

def test_duplicate_assignment_ids_fail_closed():
    with pytest.raises(
        ResourceDependentCalculationError,
        match="DUPLICATE_RESOURCE_DEPENDENT_ASSIGNMENT_ID",
    ):
        derive(driver("A-1"), driver("A-1", planned="12"))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("assignment_id", None),
        ("assignment_id", 17),
        ("resource_id", None),
        ("resource_id", ""),
    ],
)
def test_malformed_assignment_identifiers_fail_with_domain_error(field, value):
    fact = replace(driver("A-1"), **{field: value})
    with pytest.raises(
        ResourceDependentCalculationError,
        match="RESOURCE_DEPENDENT_ASSIGNMENT_ID_REQUIRED",
    ):
        derive(fact)


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"tenant_id": ""}, "RESOURCE_DEPENDENT_TENANT_ID_REQUIRED"),
        ({"project_id": " "}, "RESOURCE_DEPENDENT_PROJECT_ID_REQUIRED"),
        ({"project_revision": -1}, "RESOURCE_DEPENDENT_PROJECT_REVISION_INVALID"),
        ({"project_revision": True}, "RESOURCE_DEPENDENT_PROJECT_REVISION_INVALID"),
    ],
)
def test_identity_and_revision_inputs_are_validated(overrides, code):
    kwargs = {
        "tenant_id": "T-1",
        "project_id": "P-1",
        "project_revision": 7,
        "activity_id": "RD-1",
        "assignments": (driver("A-1"),),
    }
    kwargs.update(overrides)
    with pytest.raises(ResourceDependentCalculationError, match=code):
        derive_resource_dependent_duration(**kwargs)


def test_in_progress_activity_derives_remaining_duration_from_remaining_units():
    fact = with_periods(
        driver("A-1", planned="20", rate="5", actual="15", remaining="5"),
        (("2026-10-26", "5"),),
    )

    result = derive(fact)

    assert result.duration_working_days == 4
    assert result.remaining_duration_working_days == 1
    assert result.duration_source == "driving"


def test_in_progress_longest_remaining_driver_selects_activity_calendar():
    # A has the longer planned duration (20/4 = 5 days) but only one day of
    # remaining work; B still needs four days. The remaining-work schedule is
    # governed by B and therefore by B's own versioned calendar.
    result = derive(
        with_periods(
            driver(
                "A-1", planned="20", rate="4", actual="16", remaining="4",
                calendar_id="RC-1",
            ),
            (("2026-11-02", "4"),),
        ),
        with_periods(
            driver(
                "B-1", planned="24", rate="4", actual="8", remaining="16",
                calendar_id="RC-2", calendar_version="v7",
            ),
            (("2026-11-02", "4"), ("2026-11-03", "4"), ("2026-11-04", "4"), ("2026-11-05", "4")),
        ),
    )

    assert result.duration_working_days == 6
    assert result.remaining_duration_working_days == 4
    assert (result.calendar_id, result.calendar_version) == ("RC-2", "v7")


def test_in_progress_equal_remaining_duration_between_calendars_fails_closed():
    with pytest.raises(
        ResourceDependentCalculationError,
        match="RESOURCE_DEPENDENT_PROGRESS_DRIVING_CALENDAR_TIE",
    ):
        derive(
            with_periods(
                driver(
                    "A-1", planned="20", rate="4", actual="16", remaining="4",
                    calendar_id="RC-1",
                ),
                (("2026-11-02", "4"),),
            ),
            with_periods(
                driver(
                    "B-1", planned="20", rate="4", actual="16", remaining="4",
                    calendar_id="RC-2", calendar_version="v7",
                ),
                (("2026-11-02", "4"),),
            ),
        )


def test_in_progress_progress_units_must_reconcile_planned_units():
    with pytest.raises(
        ResourceDependentCalculationError,
        match="RESOURCE_DEPENDENT_PROGRESS_UNITS_MISMATCH",
    ):
        derive(driver("A-1", planned="20", rate="4", actual="10", remaining="6"))


@pytest.mark.parametrize(
    ("actual", "remaining", "code"),
    [
        (None, "4", "RESOURCE_DEPENDENT_PROGRESS_ACTUAL_UNITS_REQUIRED"),
        ("16", None, "RESOURCE_DEPENDENT_PROGRESS_REMAINING_UNITS_REQUIRED"),
        ("-4", "24", "RESOURCE_DEPENDENT_PROGRESS_ACTUAL_UNITS_REQUIRED"),
    ],
)
def test_in_progress_requires_reconciled_actual_and_remaining_units(
    actual, remaining, code
):
    with pytest.raises(ResourceDependentCalculationError, match=code):
        derive(
            driver(
                "A-1", planned="20", rate="4", actual=actual, remaining=remaining
            )
        )


def test_in_progress_fractional_remaining_duration_uses_whole_day_span():
    # 3 remaining units at 5/day is 0.6 day: the remaining work occupies one
    # whole working day, while the exact decimal value stays auditable.
    result = derive(
        with_periods(
            driver(
                "A-1", planned="20", rate="5", actual="17", remaining="3"
            ),
            (("2026-10-19", "3"),),
        )
    )
    assert result.duration_working_days == 4
    assert result.remaining_duration_working_days == 1
    assert result.exact_remaining_duration_working_days == Decimal("0.6")


def test_in_progress_every_driving_assignment_requires_progress_units():
    with pytest.raises(
        ResourceDependentCalculationError,
        match="RESOURCE_DEPENDENT_PROGRESS_ASSIGNMENT_UNITS_REQUIRED:B-1",
    ):
        derive(
            with_periods(
                driver("A-1", planned="20", rate="4", actual="16", remaining="4"),
                (("2026-11-02", "4"),),
            ),
            driver("B-1", planned="20", rate="4"),
        )


def test_in_progress_every_nondriving_assignment_also_requires_progress_units():
    # Progress is activity-level: a nondriving assignment whose rows are
    # remaining demand must declare Actual/Remaining Units too, otherwise the
    # placement could misread remaining rows as planned demand.
    with pytest.raises(
        ResourceDependentCalculationError,
        match="RESOURCE_DEPENDENT_PROGRESS_ASSIGNMENT_UNITS_REQUIRED:B-1",
    ):
        derive(
            with_periods(
                driver("A-1", planned="20", rate="4", actual="16", remaining="4"),
                (("2026-11-02", "4"),),
            ),
            with_periods(
                driver("B-1", planned="8", rate="4", driving=False),
                (("2026-11-02", "4"), ("2026-11-03", "4")),
            ),
        )


def test_in_progress_demand_rows_reconcile_remaining_not_planned_units():
    valid = with_periods(
        driver("A-1", planned="20", rate="4", actual="16", remaining="4"),
        (("2026-11-02", "4"),),
    )
    assert derive(valid).remaining_duration_working_days == 1

    with pytest.raises(
        ResourceDependentCalculationError,
        match="RESOURCE_DEPENDENT_DEMAND_PERIOD_COUNT_MISMATCH",
    ):
        derive(
            with_periods(
                driver("A-1", planned="20", rate="4", actual="16", remaining="4"),
                (
                    ("2026-10-26", "4"),
                    ("2026-10-27", "4"),
                    ("2026-10-28", "4"),
                    ("2026-10-29", "4"),
                    ("2026-10-30", "4"),
                ),
            )
        )


def test_in_progress_hash_binds_actual_and_remaining_units():
    base = with_periods(
        driver("A-1", planned="20", rate="4", actual="16", remaining="4"),
        (("2026-11-02", "4"),),
    )
    other = with_periods(
        driver("A-1", planned="20", rate="4", actual="12", remaining="8"),
        (("2026-11-02", "4"), ("2026-11-03", "4")),
    )
    assert derive(base).input_hash != derive(other).input_hash

    not_started = with_periods(
        driver("A-1", planned="20", rate="4"),
        (
            ("2026-10-26", "4"),
            ("2026-10-27", "4"),
            ("2026-10-28", "4"),
            ("2026-10-29", "4"),
            ("2026-10-30", "4"),
        ),
    )
    assert derive(not_started).remaining_duration_working_days is None


def test_absent_progress_fields_keep_the_not_started_hash_reproducible():
    fact = with_periods(
        driver("A-1", planned="8", rate="4"),
        (("2026-10-19", "4"), ("2026-10-20", "4")),
    )
    explicit_none = ResourceDependentDriverFact(
        **{**fact.__dict__, "actual_units": None, "remaining_units": None}
    )

    assert derive(fact).input_hash == derive(explicit_none).input_hash
    assert "actual_units" not in fact.canonical_payload()
