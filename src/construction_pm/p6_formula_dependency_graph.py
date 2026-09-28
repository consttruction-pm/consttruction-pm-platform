from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .p6_formula_engine import CompiledFormula, FormulaDependencyError


@dataclass(frozen=True)
class FormulaRecalculationPlan:
    """Deterministic evaluation order for the affected formula set."""

    ordered_formula_ids: tuple[str, ...]


class FormulaDependencyGraph:
    """Immutable dependency graph for deterministic formula invalidation/recalculation.

    A dependency name that is also a formula id is treated as a formula edge.
    Other dependency names remain external field dependencies and do not become
    graph nodes. This keeps the graph independent from persistence and runtime
    field storage.
    """

    def __init__(self, formulas: Mapping[str, CompiledFormula]) -> None:
        self._formulas = dict(formulas)
        self._validate_ids()
        self._edges = {
            formula_id: tuple(
                dependency
                for dependency in sorted(formula.dependencies)
                if dependency in self._formulas
            )
            for formula_id, formula in sorted(self._formulas.items())
        }
        dependency_map: dict[str, set[str]] = {}
        for formula_id, formula in sorted(self._formulas.items()):
            for dependency in formula.dependencies:
                dependency_map.setdefault(dependency, set()).add(formula_id)
        self._dependents_index = {
            dependency: tuple(sorted(formula_ids))
            for dependency, formula_ids in sorted(dependency_map.items())
        }
        self._validate_cycles()

    @property
    def formula_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._formulas))

    def dependencies_of(self, formula_id: str) -> tuple[str, ...]:
        self._require_formula(formula_id)
        return self._edges[formula_id]

    def formula_of(self, formula_id: str) -> CompiledFormula:
        self._require_formula(formula_id)
        return self._formulas[formula_id]

    def dependents_of(self, formula_id: str) -> tuple[str, ...]:
        self._require_formula(formula_id)
        return self._dependents_index.get(formula_id, ())

    def dependents_of_change(self, dependency_id: str) -> tuple[str, ...]:
        if not dependency_id or not dependency_id.strip():
            raise FormulaDependencyError("INVALID_DEPENDENCY_ID")
        return self._dependents_index.get(dependency_id, ())

    def transitive_dependents(self, formula_ids: set[str] | frozenset[str]) -> tuple[str, ...]:
        self._validate_formula_ids(formula_ids)
        affected: set[str] = set()
        pending = sorted(formula_ids)

        while pending:
            current = pending.pop(0)
            for dependent in self.dependents_of(current):
                if dependent not in affected and dependent not in formula_ids:
                    affected.add(dependent)
                    pending.append(dependent)
            pending.sort()

        return tuple(sorted(affected))

    def affected_formulas(self, changed_formula_ids: set[str] | frozenset[str]) -> tuple[str, ...]:
        self._validate_formula_ids(changed_formula_ids)
        return tuple(sorted(set(changed_formula_ids) | set(self.transitive_dependents(changed_formula_ids))))

    def affected_formulas_for_changes(self, changed_ids: set[str] | frozenset[str]) -> tuple[str, ...]:
        if not changed_ids:
            return ()
        affected: set[str] = set()
        for changed_id in sorted(changed_ids):
            if changed_id in self._formulas:
                affected.add(changed_id)
            affected.update(self.dependents_of_change(changed_id))

        queue = sorted(affected)
        while queue:
            current = queue.pop(0)
            for dependent in self.dependents_of_change(current):
                if dependent not in affected:
                    affected.add(dependent)
                    queue.append(dependent)
            queue.sort()
        return tuple(sorted(affected))

    def recalculation_plan(self, changed_formula_ids: set[str] | frozenset[str]) -> FormulaRecalculationPlan:
        self._validate_formula_ids(changed_formula_ids)
        return self._recalculation_plan_for_affected(
            set(self.affected_formulas(changed_formula_ids))
        )

    def recalculation_plan_for_changes(
        self,
        changed_ids: set[str] | frozenset[str],
    ) -> FormulaRecalculationPlan:
        affected = set(self.affected_formulas_for_changes(changed_ids))
        return self._recalculation_plan_for_affected(affected)

    def _recalculation_plan_for_affected(
        self,
        affected: set[str],
    ) -> FormulaRecalculationPlan:
        indegree = {
            formula_id: sum(
                1
                for dependency in self._edges[formula_id]
                if dependency in affected
            )
            for formula_id in affected
        }
        ready = sorted(
            formula_id
            for formula_id, degree in indegree.items()
            if degree == 0
        )
        ordered: list[str] = []

        while ready:
            current = ready.pop(0)
            ordered.append(current)
            for dependent in self.dependents_of(current):
                if dependent not in affected:
                    continue
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    ready.append(dependent)
                    ready.sort()

        if len(ordered) != len(affected):
            raise FormulaDependencyError("CIRCULAR_DEPENDENCY")
        return FormulaRecalculationPlan(tuple(ordered))

    def _validate_ids(self) -> None:
        for formula_id in self._formulas:
            if not formula_id or not formula_id.strip():
                raise FormulaDependencyError("INVALID_FORMULA_ID")

    def _require_formula(self, formula_id: str) -> None:
        if formula_id not in self._formulas:
            raise FormulaDependencyError(f"FORMULA_NOT_FOUND:{formula_id}")

    def _validate_formula_ids(self, formula_ids: set[str] | frozenset[str]) -> None:
        for formula_id in formula_ids:
            self._require_formula(formula_id)

    def _validate_cycles(self) -> None:
        state: dict[str, int] = {}
        stack: list[str] = []

        def visit(formula_id: str) -> None:
            status = state.get(formula_id, 0)
            if status == 1:
                start = stack.index(formula_id)
                cycle = " -> ".join(stack[start:] + [formula_id])
                raise FormulaDependencyError(f"CIRCULAR_DEPENDENCY:{cycle}")
            if status == 2:
                return

            state[formula_id] = 1
            stack.append(formula_id)
            for dependency in self._edges[formula_id]:
                visit(dependency)
            stack.pop()
            state[formula_id] = 2

        for formula_id in sorted(self._formulas):
            visit(formula_id)


__all__ = ["FormulaDependencyGraph", "FormulaRecalculationPlan"]
