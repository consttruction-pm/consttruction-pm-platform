from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .p6_formula_dependency_graph import FormulaDependencyGraph, FormulaRecalculationPlan
from .p6_formula_engine import FormulaValue, evaluate_formula


@dataclass(frozen=True)
class FormulaRecalculationResult:
    """Deterministic results for one formula recalculation transaction."""

    plan: FormulaRecalculationPlan
    values: Mapping[str, FormulaValue]

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))


class FormulaRecalculationEngine:
    """Evaluate affected compiled formulas in dependency-safe order.

    The engine owns orchestration only. Formula parsing, type checking, units,
    null semantics, dependency discovery and expression evaluation remain in
    the Shared Formula Core.
    """

    def recalculate(
        self,
        graph: FormulaDependencyGraph,
        values: Mapping[str, FormulaValue],
        changed_formula_ids: set[str] | frozenset[str],
    ) -> FormulaRecalculationResult:
        plan = graph.recalculation_plan(changed_formula_ids)
        working_values = dict(values)

        for formula_id in plan.ordered_formula_ids:
            compiled = graph.formula_of(formula_id)
            working_values[formula_id] = evaluate_formula(compiled, working_values)

        result_values = {
            formula_id: working_values[formula_id]
            for formula_id in plan.ordered_formula_ids
        }
        return FormulaRecalculationResult(plan=plan, values=result_values)

    def recalculate_changes(
        self,
        graph: FormulaDependencyGraph,
        values: Mapping[str, FormulaValue],
        changed_ids: set[str] | frozenset[str],
    ) -> FormulaRecalculationResult:
        plan = graph.recalculation_plan_for_changes(changed_ids)
        if not plan.ordered_formula_ids:
            return FormulaRecalculationResult(
                plan=plan,
                values={},
            )

        working_values = dict(values)
        for formula_id in plan.ordered_formula_ids:
            compiled = graph.formula_of(formula_id)
            working_values[formula_id] = evaluate_formula(compiled, working_values)

        return FormulaRecalculationResult(
            plan=plan,
            values={
                formula_id: working_values[formula_id]
                for formula_id in plan.ordered_formula_ids
            },
        )


__all__ = ["FormulaRecalculationEngine", "FormulaRecalculationResult"]
