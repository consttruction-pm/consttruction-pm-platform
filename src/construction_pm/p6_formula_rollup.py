from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from .p6_formula_engine import CompiledFormula, FormulaType, FormulaTypeError, FormulaValue, evaluate_formula


class FormulaRollupFunction(str, Enum):
    SUM = "SUM"
    MIN = "MIN"
    MAX = "MAX"


@dataclass(frozen=True)
class FormulaRollupResult:
    """Deterministic rollup result for one summary scope."""

    function: FormulaRollupFunction
    value: FormulaValue


class FormulaRollupEngine:
    """Aggregate Shared Core formula results for summary/WBS/project scopes.

    Scope membership and hierarchy traversal belong to the domain/application
    layer. This engine only evaluates the compiled formula for each supplied
    child row and aggregates the typed results deterministically.
    """

    def aggregate(
        self,
        function: FormulaRollupFunction,
        values: Mapping[str, FormulaValue],
    ) -> FormulaRollupResult:
        if function not in {
            FormulaRollupFunction.SUM,
            FormulaRollupFunction.MIN,
            FormulaRollupFunction.MAX,
        }:
            raise FormulaTypeError(f"UNSUPPORTED_ROLLUP_FUNCTION:{function}")

        present = [
            value for _, value in sorted(values.items())
            if value.type is not FormulaType.NULL
        ]
        if any(value.type is not FormulaType.NUMBER for value in present):
            raise FormulaTypeError("ROLLUP_VALUES_MUST_BE_NUMERIC")
        normalized = [
            FormulaValue.number(value.value, value.unit)
            for value in present
        ]
        if not normalized:
            return FormulaRollupResult(function, FormulaValue.null())

        first_unit = normalized[0].unit
        if any(value.unit != first_unit for value in normalized[1:]):
            raise FormulaTypeError("INCOMPATIBLE_UNITS")

        if function is FormulaRollupFunction.SUM:
            total = sum((value.value for value in normalized))
            result = FormulaValue.number(total, first_unit)
        elif function is FormulaRollupFunction.MIN:
            result = min(normalized, key=lambda value: value.value)
        else:
            result = max(normalized, key=lambda value: value.value)

        return FormulaRollupResult(function, result)

    def rollup(
        self,
        compiled_formula: CompiledFormula,
        child_values: Mapping[str, Mapping[str, FormulaValue]],
        function: FormulaRollupFunction,
    ) -> FormulaRollupResult:
        if compiled_formula.definition.result_type is not FormulaType.NUMBER:
            raise FormulaTypeError("ROLLUP_REQUIRES_NUMERIC_FORMULA")

        evaluated = {
            child_id: evaluate_formula(compiled_formula, values)
            for child_id, values in sorted(child_values.items())
        }
        return self.aggregate(function, evaluated)


__all__ = ["FormulaRollupEngine", "FormulaRollupFunction", "FormulaRollupResult"]
