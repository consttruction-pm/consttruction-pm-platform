from decimal import Decimal

import pytest

from construction_pm.p6_formula_dependency_graph import FormulaDependencyGraph
from construction_pm.p6_formula_engine import (
    FormulaDefinition,
    FormulaTypeError,
    FormulaSchemaValue,
    FormulaType,
    FormulaValue,
    compile_formula,
)
from construction_pm.p6_formula_recalculation import FormulaRecalculationEngine


def _formula(formula_id: str, expression: str):
    schema = {
        "A": FormulaSchemaValue(FormulaType.NUMBER),
        "B": FormulaSchemaValue(FormulaType.NUMBER),
        "C": FormulaSchemaValue(FormulaType.NUMBER),
        "raw": FormulaSchemaValue(FormulaType.NUMBER),
    }
    return compile_formula(
        FormulaDefinition(formula_id, "1.0", expression, FormulaType.NUMBER),
        schema,
    )


def test_chain_recalculates_in_dependency_order():
    formulas = {
        "C": _formula("C", "[B] * 2"),
        "B": _formula("B", "[A] + [raw]"),
        "A": _formula("A", "[raw] + 1"),
    }
    graph = FormulaDependencyGraph(formulas)

    result = FormulaRecalculationEngine().recalculate(
        graph,
        {"raw": FormulaValue.number(Decimal("3"))},
        {"A"},
    )

    assert result.plan.ordered_formula_ids == ("A", "B", "C")
    assert result.values["A"].value == Decimal("4")
    assert result.values["B"].value == Decimal("7")
    assert result.values["C"].value == Decimal("14")


def test_branching_recalculates_only_affected_closure():
    formulas = {
        "A": _formula("A", "[raw] + 1"),
        "B": _formula("B", "[A] + 1"),
        "C": _formula("C", "[A] + 2"),
        "D": _formula("D", "[B] + [C]"),
    }
    graph = FormulaDependencyGraph(formulas)

    result = FormulaRecalculationEngine().recalculate(
        graph,
        {"raw": FormulaValue.number(Decimal("5")), "unrelated": FormulaValue.text("keep")},
        {"A"},
    )

    assert result.plan.ordered_formula_ids == ("A", "B", "C", "D")
    assert result.values["A"].value == Decimal("6")
    assert result.values["B"].value == Decimal("7")
    assert result.values["C"].value == Decimal("8")
    assert result.values["D"].value == Decimal("15")
    assert "unrelated" not in result.values


def test_empty_change_set_is_a_noop():
    formulas = {"A": _formula("A", "[raw] + 1")}
    graph = FormulaDependencyGraph(formulas)

    result = FormulaRecalculationEngine().recalculate(
        graph,
        {"raw": FormulaValue.number(Decimal("5"))},
        set(),
    )

    assert result.plan.ordered_formula_ids == ()
    assert dict(result.values) == {}


def test_formula_runtime_error_does_not_return_partial_result():
    formulas = {
        "A": _formula("A", "[raw] + 1"),
        "B": _formula("B", "[A] + 1"),
    }
    graph = FormulaDependencyGraph(formulas)

    with pytest.raises(FormulaTypeError):
        FormulaRecalculationEngine().recalculate(
            graph,
            {"raw": FormulaValue.text("bad")},
            {"A"},
        )
