from decimal import Decimal

import pytest

from construction_pm.scheduling.earned_value import (
    ETC_PF_CPI,
    ETC_PF_CPI_SPI,
    ETC_PF_ONE,
    ETC_REMAINING_COST,
    ETC_USER_PF,
    EarnedValueError,
    EarnedValueInput,
    calculate_earned_value,
)


def measure(**overrides):
    values = {
        "planned_value": "100",
        "earned_value": "90",
        "actual_cost": "110",
        "budget_at_completion": "150",
        "remaining_cost": "40",
        "etc_method": ETC_REMAINING_COST,
    }
    values.update(overrides)
    return EarnedValueInput(**values)


def test_variances_and_indices_follow_the_documented_identities():
    result = calculate_earned_value(measure())

    assert result.cost_variance == Decimal("-20")
    assert result.schedule_variance == Decimal("-10")
    assert result.cost_performance_index == Decimal("90") / Decimal("110")
    assert result.schedule_performance_index == Decimal("0.9")
    assert result.estimate_to_complete == Decimal("40")
    assert result.estimate_at_completion == Decimal("150")
    assert result.variance_at_completion == Decimal("0")


def test_zero_actual_cost_leaves_cpi_undefined_instead_of_one():
    result = calculate_earned_value(measure(actual_cost="0"))

    assert result.cost_performance_index is None
    assert result.cost_variance == Decimal("90")
    assert "cost_performance_index" in result.canonical_snapshot()
    assert result.canonical_snapshot()["cost_performance_index"] is None


def test_zero_planned_value_leaves_spi_undefined_instead_of_one():
    result = calculate_earned_value(measure(planned_value="0", earned_value="0"))

    assert result.schedule_performance_index is None
    assert result.schedule_variance == Decimal("0")


def test_remaining_cost_estimator_works_without_bac_and_omits_vac():
    result = calculate_earned_value(
        measure(budget_at_completion=None, remaining_cost="25")
    )

    assert result.estimate_to_complete == Decimal("25")
    assert result.estimate_at_completion == Decimal("135")
    assert result.variance_at_completion is None


def test_pf_one_estimator_uses_the_remaining_budget():
    result = calculate_earned_value(measure(etc_method=ETC_PF_ONE))

    assert result.performance_factor == Decimal("1")
    assert result.estimate_to_complete == Decimal("60")
    assert result.estimate_at_completion == Decimal("170")
    assert result.variance_at_completion == Decimal("-20")


def test_pf_inverse_cpi_estimator():
    # CPI = 90 / 120 = 0.75; ETC = 60 / 0.75 = 80.
    result = calculate_earned_value(
        measure(actual_cost="120", etc_method=ETC_PF_CPI)
    )

    assert result.cost_performance_index == Decimal("0.75")
    assert result.performance_factor == Decimal("1") / Decimal("0.75")
    assert result.estimate_to_complete == Decimal("80")
    assert result.estimate_at_completion == Decimal("200")
    assert result.variance_at_completion == Decimal("-50")


def test_pf_inverse_cpi_times_spi_estimator():
    # CPI = 0.75 and SPI = 0.75, so PF = 1 / 0.5625.
    result = calculate_earned_value(
        measure(
            actual_cost="120",
            planned_value="120",
            etc_method=ETC_PF_CPI_SPI,
        )
    )

    assert result.cost_performance_index == Decimal("0.75")
    assert result.schedule_performance_index == Decimal("0.75")
    expected_etc = Decimal("60") / (Decimal("0.75") * Decimal("0.75"))
    assert result.estimate_to_complete == expected_etc
    assert result.estimate_at_completion == Decimal("120") + expected_etc
    assert result.variance_at_completion == Decimal("150") - (
        Decimal("120") + expected_etc
    )


def test_user_defined_performance_factor():
    result = calculate_earned_value(
        measure(
            etc_method=ETC_USER_PF,
            performance_factor="1.5",
        )
    )

    assert result.performance_factor == Decimal("1.5")
    assert result.estimate_to_complete == Decimal("90")
    assert result.estimate_at_completion == Decimal("200")
    assert result.variance_at_completion == Decimal("-50")


def test_canonical_snapshot_is_all_strings_and_none():
    snapshot = calculate_earned_value(measure()).canonical_snapshot()

    numeric_keys = {
        "planned_value",
        "earned_value",
        "actual_cost",
        "cost_variance",
        "schedule_variance",
        "cost_performance_index",
        "schedule_performance_index",
        "budget_at_completion",
        "estimate_to_complete",
        "estimate_at_completion",
        "variance_at_completion",
        "performance_factor",
    }
    for key in numeric_keys:
        assert isinstance(snapshot[key], (str, type(None)))
    assert snapshot["etc_method"] == ETC_REMAINING_COST


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"remaining_cost": None}, "EARNED_VALUE_REMAINING_COST_REQUIRED"),
        (
            {"etc_method": ETC_PF_ONE, "budget_at_completion": None},
            "EARNED_VALUE_BUDGET_AT_COMPLETION_REQUIRED",
        ),
        (
            {"etc_method": ETC_PF_CPI, "actual_cost": "0"},
            "EARNED_VALUE_COST_INDEX_UNAVAILABLE",
        ),
        (
            {
                "etc_method": ETC_PF_CPI_SPI,
                "planned_value": "0",
                "earned_value": "50",
            },
            "EARNED_VALUE_SCHEDULE_INDEX_UNAVAILABLE",
        ),
        (
            {"etc_method": ETC_USER_PF, "performance_factor": None},
            "EARNED_VALUE_PERFORMANCE_FACTOR_REQUIRED",
        ),
        (
            {"etc_method": ETC_USER_PF, "performance_factor": "0"},
            "EARNED_VALUE_PERFORMANCE_FACTOR_INVALID",
        ),
        (
            {"etc_method": ETC_PF_CPI, "earned_value": "160"},
            "EARNED_VALUE_REMAINING_BUDGET_NEGATIVE",
        ),
        ({"planned_value": "-1"}, "EARNED_VALUE_PLANNED_VALUE_INVALID"),
        ({"earned_value": "NaN"}, "EARNED_VALUE_EARNED_VALUE_INVALID"),
        ({"actual_cost": "Infinity"}, "EARNED_VALUE_ACTUAL_COST_INVALID"),
        (
            {"budget_at_completion": "-5"},
            "EARNED_VALUE_BUDGET_AT_COMPLETION_INVALID",
        ),
        ({"remaining_cost": "-5"}, "EARNED_VALUE_REMAINING_COST_INVALID"),
        ({"etc_method": "WEIGHTED_CURVE"}, "EARNED_VALUE_ETC_METHOD_UNSUPPORTED"),
    ],
)
def test_invalid_inputs_and_unsupported_estimators_fail_closed(overrides, code):
    with pytest.raises(EarnedValueError, match=code):
        calculate_earned_value(measure(**overrides))


@pytest.mark.parametrize(
    "constructed",
    [
        lambda: EarnedValueInput(
            planned_value="100", earned_value="90", actual_cost="110",
            remaining_cost="40", etc_method="MANUAL_BUCKETS",
        ),
        lambda: EarnedValueInput(
            planned_value="100", earned_value="90", actual_cost="110",
            remaining_cost="40", budget_at_completion=False,
        ),
    ],
)
def test_construction_rejects_invalid_contract_values(constructed):
    with pytest.raises(EarnedValueError):
        constructed()


def test_non_earned_value_input_fails_closed():
    with pytest.raises(EarnedValueError, match="EARNED_VALUE_INPUT_REQUIRED"):
        calculate_earned_value({"planned_value": "100"})
