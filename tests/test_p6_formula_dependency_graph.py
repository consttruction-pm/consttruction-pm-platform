from decimal import Decimal

import pytest

from construction_pm.p6_formula_dependency_graph import FormulaDependencyGraph
from construction_pm.p6_formula_engine import (
    FormulaDefinition,
    FormulaDependencyError,
    FormulaSchemaValue,
    FormulaType,
    compile_formula,
)


def _formula(formula_id: str, expression: str):
    schema = {
        "A": FormulaSchemaValue(FormulaType.NUMBER),
        "B": FormulaSchemaValue(FormulaType.NUMBER),
        "C": FormulaSchemaValue(FormulaType.NUMBER),
        "raw": FormulaSchemaValue(FormulaType.NUMBER),
        "other": FormulaSchemaValue(FormulaType.NUMBER),
    }
    return compile_formula(
        FormulaDefinition(formula_id, "1", expression, FormulaType.NUMBER),
        schema,
    )


def test_chain_has_deterministic_topological_recalculation_order():
    formulas = {
        "C": _formula("C", "[B] + 1"),
        "B": _formula("B", "[A] + 1"),
        "A": _formula("A", "1"),
    }

    graph = FormulaDependencyGraph(formulas)

    assert graph.recalculation_plan({"A"}).ordered_formula_ids == ("A", "B", "C")
    assert graph.transitive_dependents({"A"}) == ("B", "C")


def test_branching_dependencies_are_all_invalidated():
    formulas = {
        "A": _formula("A", "1"),
        "B": _formula("B", "[A] + 1"),
        "C": _formula("C", "[A] + 2"),
        "D": _formula("D", "[B] + [C]"),
    }

    graph = FormulaDependencyGraph(formulas)

    assert graph.dependents_of("A") == ("B", "C")
    assert graph.transitive_dependents({"A"}) == ("B", "C", "D")
    assert graph.recalculation_plan({"A"}).ordered_formula_ids == ("A", "B", "C", "D")


def test_unrelated_formulas_are_not_recalculated():
    formulas = {
        "A": _formula("A", "1"),
        "B": _formula("B", "[A] + 1"),
        "X": _formula("X", "10"),
    }

    graph = FormulaDependencyGraph(formulas)

    assert graph.affected_formulas({"A"}) == ("A", "B")
    assert graph.recalculation_plan({"A"}).ordered_formula_ids == ("A", "B")


def test_cycle_is_rejected_with_a_trace():
    formulas = {
        "A": _formula("A", "[B] + 1"),
        "B": _formula("B", "[A] + 1"),
    }

    with pytest.raises(FormulaDependencyError, match=r"CIRCULAR_DEPENDENCY:A -> B -> A"):
        FormulaDependencyGraph(formulas)


def test_missing_requested_formula_is_rejected():
    graph = FormulaDependencyGraph({"A": _formula("A", "1")})

    with pytest.raises(FormulaDependencyError, match="FORMULA_NOT_FOUND:X"):
        graph.recalculation_plan({"X"})


def test_external_field_dependencies_do_not_become_formula_edges():
    graph = FormulaDependencyGraph({"A": _formula("A", "[C] + 1")})

    assert graph.dependencies_of("A") == ()
    assert graph.dependents_of("A") == ()


def test_recalculation_order_is_stable_for_multiple_ready_nodes():
    formulas = {
        "Z": _formula("Z", "[A] + 1"),
        "Y": _formula("Y", "[A] + 2"),
        "A": _formula("A", "1"),
    }

    graph = FormulaDependencyGraph(formulas)

    assert graph.recalculation_plan({"A"}).ordered_formula_ids == ("A", "Y", "Z")


def test_external_field_change_invalidates_direct_and_transitive_dependents():
    formulas = {
        "A": _formula("A", "[raw] + 1"),
        "B": _formula("B", "[A] + 1"),
        "C": _formula("C", "[B] + 1"),
        "D": _formula("D", "[other] + 1"),
    }
    graph = FormulaDependencyGraph(formulas)

    assert graph.dependents_of_change("raw") == ("A",)
    assert graph.affected_formulas_for_changes({"raw"}) == ("A", "B", "C")
    assert graph.affected_formulas_for_changes({"missing"}) == ()
