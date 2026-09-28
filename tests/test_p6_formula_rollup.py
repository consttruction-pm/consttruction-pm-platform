from decimal import Decimal

import pytest

from construction_pm.p6_formula_engine import (
    FormulaDefinition,
    FormulaSchemaValue,
    FormulaType,
    FormulaTypeError,
    FormulaValue,
    compile_formula,
)
from construction_pm.p6_formula_rollup import FormulaRollupEngine, FormulaRollupFunction


def _compiled_formula(expression: str = "[qty] * [rate]"):
    schema = {
        "qty": FormulaSchemaValue(FormulaType.NUMBER, unit="m3"),
        "rate": FormulaSchemaValue(FormulaType.NUMBER),
    }
    return compile_formula(
        FormulaDefinition("activity.total", "1.0", expression, FormulaType.NUMBER),
        schema,
    )


def test_sum_rollup_is_deterministic_and_preserves_unit():
    result = FormulaRollupEngine().aggregate(
        FormulaRollupFunction.SUM,
        {
            "activity-b": FormulaValue.number(Decimal("2"), "m3"),
            "activity-a": FormulaValue.number(Decimal("3"), "m3"),
        },
    )

    assert result.value == FormulaValue.number(Decimal("5"), "m3")


def test_null_children_are_ignored_consistently_with_formula_sum():
    result = FormulaRollupEngine().aggregate(
        FormulaRollupFunction.SUM,
        {
            "activity-a": FormulaValue.null(),
            "activity-b": FormulaValue.number(Decimal("4"), "m3"),
        },
    )

    assert result.value == FormulaValue.number(Decimal("4"), "m3")


@pytest.mark.parametrize(
    ("function", "expected"),
    [
        (FormulaRollupFunction.MIN, Decimal("2")),
        (FormulaRollupFunction.MAX, Decimal("7")),
    ],
)
def test_min_max_rollups_are_typed_and_deterministic(function, expected):
    result = FormulaRollupEngine().aggregate(
        function,
        {
            "b": FormulaValue.number(Decimal("7"), "m3"),
            "a": FormulaValue.number(Decimal("2"), "m3"),
        },
    )

    assert result.value == FormulaValue.number(expected, "m3")


def test_empty_rollup_is_null():
    result = FormulaRollupEngine().aggregate(FormulaRollupFunction.SUM, {})

    assert result.value == FormulaValue.null()


def test_incompatible_units_are_rejected():
    with pytest.raises(FormulaTypeError, match="INCOMPATIBLE_UNITS"):
        FormulaRollupEngine().aggregate(
            FormulaRollupFunction.SUM,
            {
                "a": FormulaValue.number(Decimal("1"), "m3"),
                "b": FormulaValue.number(Decimal("2"), "day"),
            },
        )


def test_non_number_values_are_rejected():
    with pytest.raises(FormulaTypeError, match="ROLLUP_VALUES_MUST_BE_NUMERIC"):
        FormulaRollupEngine().aggregate(
            FormulaRollupFunction.SUM,
            {
                "a": FormulaValue.text("not-number"),
            },
        )


def test_compiled_formula_is_evaluated_for_each_child_before_rollup():
    formula = _compiled_formula()

    result = FormulaRollupEngine().rollup(
        formula,
        {
            "activity-b": {
                "qty": FormulaValue.number(Decimal("3"), "m3"),
                "rate": FormulaValue.number(Decimal("2")),
            },
            "activity-a": {
                "qty": FormulaValue.number(Decimal("4"), "m3"),
                "rate": FormulaValue.number(Decimal("2")),
            },
        },
        FormulaRollupFunction.SUM,
    )

    assert result.value == FormulaValue.number(Decimal("14"), "m3")


def test_non_numeric_formula_cannot_be_rolled_up():
    schema = {"name": FormulaSchemaValue(FormulaType.TEXT)}
    formula = compile_formula(
        FormulaDefinition("activity.name", "1.0", "[name]", FormulaType.TEXT),
        schema,
    )

    with pytest.raises(FormulaTypeError, match="ROLLUP_REQUIRES_NUMERIC_FORMULA"):
        FormulaRollupEngine().rollup(formula, {}, FormulaRollupFunction.SUM)
