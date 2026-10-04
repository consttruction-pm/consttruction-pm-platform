from decimal import Decimal

import pytest

from construction_pm.p6_formula_engine import (
    FormulaDefinition,
    FormulaDependencyError,
    FormulaError,
    FormulaSchemaValue,
    FormulaSyntaxError,
    FormulaType,
    FormulaTypeError,
    FormulaValue,
    compile_formula,
    detect_formula_cycles,
    evaluate_formula,
    parse_formula,
)


SCHEMA = {
    "budget": FormulaSchemaValue(FormulaType.NUMBER, "USD"),
    "actual": FormulaSchemaValue(FormulaType.NUMBER, "USD"),
    "quantity": FormulaSchemaValue(FormulaType.NUMBER, "m3"),
    "unit_rate": FormulaSchemaValue(FormulaType.NUMBER, "USD/m3"),
    "is_approved": FormulaSchemaValue(FormulaType.BOOLEAN),
    "name": FormulaSchemaValue(FormulaType.TEXT),
}


def _compile(expression: str, result_type: FormulaType = FormulaType.NUMBER):
    return compile_formula(
        FormulaDefinition(
            formula_id="test.formula",
            version="1.0",
            expression=expression,
            result_type=result_type,
        ),
        SCHEMA,
    )


def test_parser_builds_dependencies_without_executing_code() -> None:
    compiled = _compile("[budget] - [actual]")

    assert compiled.dependencies == ("actual", "budget")
    assert compiled.inferred_type is FormulaType.NUMBER


def test_arithmetic_is_decimal_deterministic_and_typed() -> None:
    compiled = _compile("([budget] - [actual]) / 2")

    result = evaluate_formula(
        compiled,
        {
            "budget": FormulaValue.number(Decimal("1000.10"), "USD"),
            "actual": FormulaValue.number(Decimal("250.05"), "USD"),
        },
    )

    assert result == FormulaValue.number(Decimal("375.025"), "USD")


def test_if_and_logical_functions_are_supported() -> None:
    compiled = compile_formula(
        FormulaDefinition(
            formula_id="test.status",
            version="1.0",
            expression='IF([is_approved] AND TRUE, "Approved", "Pending")',
            result_type=FormulaType.TEXT,
        ),
        SCHEMA,
    )

    assert evaluate_formula(
        compiled,
        {"is_approved": FormulaValue.boolean(True)}
    ) == FormulaValue.text("Approved")


def test_if_is_lazy_for_unselected_branch_errors() -> None:
    compiled = _compile("IF(TRUE, 7, [budget] / 0)")
    assert evaluate_formula(
        compiled,
        {"budget": FormulaValue.number(10, "USD")},
    ) == FormulaValue.number(7)


def test_binary_and_or_short_circuit_decisive_left_operand() -> None:
    and_formula = compile_formula(
        FormulaDefinition("test.and_lazy", "1.0", "FALSE AND ([budget] / 0 > 1)", FormulaType.BOOLEAN),
        SCHEMA,
    )
    or_formula = compile_formula(
        FormulaDefinition("test.or_lazy", "1.0", "TRUE OR ([budget] / 0 > 1)", FormulaType.BOOLEAN),
        SCHEMA,
    )

    values = {"budget": FormulaValue.number(10, "USD")}
    assert evaluate_formula(and_formula, values) == FormulaValue.boolean(False)
    assert evaluate_formula(or_formula, values) == FormulaValue.boolean(True)


def test_function_and_or_short_circuit_decisive_operand() -> None:
    and_formula = compile_formula(
        FormulaDefinition(
            "test.and_function_lazy",
            "1.0",
            "AND(FALSE, [budget] / 0 > 1)",
            FormulaType.BOOLEAN,
        ),
        SCHEMA,
    )
    or_formula = compile_formula(
        FormulaDefinition(
            "test.or_function_lazy",
            "1.0",
            "OR(TRUE, [budget] / 0 > 1)",
            FormulaType.BOOLEAN,
        ),
        SCHEMA,
    )

    values = {"budget": FormulaValue.number(10, "USD")}
    assert evaluate_formula(and_formula, values) == FormulaValue.boolean(False)
    assert evaluate_formula(or_formula, values) == FormulaValue.boolean(True)


def test_null_propagates_in_arithmetic_and_comparisons() -> None:
    compiled = _compile("[budget] - [actual]")

    assert evaluate_formula(
        compiled,
        {"budget": FormulaValue.number(100, "USD"), "actual": FormulaValue.null()},
    ) == FormulaValue.null()

    comparison = compile_formula(
        FormulaDefinition(
            formula_id="test.compare",
            version="1.0",
            expression="[budget] > [actual]",
            result_type=FormulaType.BOOLEAN,
        ),
        SCHEMA,
    )
    assert evaluate_formula(
        comparison,
        {"budget": FormulaValue.number(100, "USD"), "actual": FormulaValue.null()},
    ) == FormulaValue.null()


def test_incompatible_units_are_rejected_during_type_check() -> None:
    with pytest.raises(FormulaTypeError, match="INCOMPATIBLE_UNITS"):
        _compile("[budget] + [quantity]")


def test_missing_field_is_rejected_before_evaluation() -> None:
    with pytest.raises(FormulaDependencyError, match="FIELD_NOT_FOUND:missing"):
        _compile("[missing] + 1")


def test_if_branches_must_have_compatible_types() -> None:
    with pytest.raises(FormulaTypeError, match="IF_BRANCH_TYPES_MUST_MATCH"):
        compile_formula(
            FormulaDefinition(
                formula_id="test.bad_if",
                version="1.0",
                expression='IF(TRUE, [budget], "text")',
                result_type=FormulaType.NUMBER,
            ),
            SCHEMA,
        )


def test_round_uses_decimal_half_up_semantics() -> None:
    compiled = _compile("ROUND([actual], 2)")

    result = evaluate_formula(
        compiled,
        {"actual": FormulaValue.number(Decimal("1.235"), "USD")},
    )

    assert result == FormulaValue.number(Decimal("1.24"), "USD")


def test_division_by_zero_is_explicit() -> None:
    compiled = _compile("[budget] / 0")
    with pytest.raises(FormulaError, match="DIVISION_BY_ZERO"):
        evaluate_formula(compiled, {"budget": FormulaValue.number(10, "USD")})


def test_syntax_rejects_unterminated_field_and_bare_identifiers() -> None:
    with pytest.raises(FormulaSyntaxError, match="UNTERMINATED_FIELD_REFERENCE"):
        parse_formula("[budget")

    with pytest.raises(FormulaSyntaxError, match="BARE_IDENTIFIER_NOT_ALLOWED"):
        parse_formula("budget + 1")


def test_coalesce_short_circuits_unselected_error() -> None:
    compiled = _compile("COALESCE([budget], [budget] / 0)")
    assert evaluate_formula(
        compiled,
        {"budget": FormulaValue.number(5, "USD")},
    ) == FormulaValue.number(5, "USD")


def test_coalesce_and_aggregate_functions_handle_nulls() -> None:
    coalesce = compile_formula(
        FormulaDefinition(
            formula_id="test.coalesce",
            version="1.0",
            expression='COALESCE(NULL, [budget])',
            result_type=FormulaType.NUMBER,
        ),
        SCHEMA,
    )
    assert evaluate_formula(
        coalesce, {"budget": FormulaValue.number(5, "USD")}
    ) == FormulaValue.number(5, "USD")

    total = _compile("SUM(NULL, [budget], [actual])")
    assert evaluate_formula(
        total,
        {
            "budget": FormulaValue.number(5, "USD"),
            "actual": FormulaValue.number(3, "USD"),
        },
    ) == FormulaValue.number(8, "USD")


def test_formula_cycle_detection_is_deterministic() -> None:
    schema = {
        "a": FormulaSchemaValue(FormulaType.NUMBER),
        "b": FormulaSchemaValue(FormulaType.NUMBER),
    }
    a = compile_formula(
        FormulaDefinition("a", "1.0", "[b] + 1", FormulaType.NUMBER),
        schema,
    )
    b = compile_formula(
        FormulaDefinition("b", "1.0", "[a] + 1", FormulaType.NUMBER),
        schema,
    )

    with pytest.raises(FormulaDependencyError, match="CIRCULAR_DEPENDENCY:a -> b -> a"):
        detect_formula_cycles({"a": a, "b": b})


def test_result_type_mismatch_is_rejected_at_compile_boundary() -> None:
    with pytest.raises(FormulaTypeError, match="RESULT_TYPE_MISMATCH"):
        _compile("[budget]", FormulaType.TEXT)


def test_unsupported_function_fails_closed() -> None:
    with pytest.raises(FormulaTypeError, match="UNSUPPORTED_FUNCTION:HACK"):
        _compile("HACK([budget])")


def test_parser_supports_precedence() -> None:
    compiled = _compile("[budget] + 2 * 3")

    assert evaluate_formula(
        compiled,
        {"budget": FormulaValue.number(4, "USD")},
    ) == FormulaValue.number(10, "USD")



def test_multiplication_composes_units_and_produces_total_cost() -> None:
    compiled = _compile("[quantity] * [unit_rate]")

    result = evaluate_formula(
        compiled,
        {
            "quantity": FormulaValue.number(Decimal("2.5"), "m3"),
            "unit_rate": FormulaValue.number(Decimal("120"), "USD/m3"),
        },
    )

    assert result == FormulaValue.number(Decimal("300"), "USD")


def test_division_composes_units_and_supports_inverse_units() -> None:
    compiled = _compile("[budget] / [quantity]")

    assert evaluate_formula(
        compiled,
        {
            "budget": FormulaValue.number(Decimal("300"), "USD"),
            "quantity": FormulaValue.number(Decimal("2"), "m3"),
        },
    ) == FormulaValue.number(Decimal("150"), "USD/m3")

    inverse = _compile("1 / [quantity]")
    assert evaluate_formula(
        inverse,
        {"quantity": FormulaValue.number(Decimal("2"), "m3")},
    ) == FormulaValue.number(Decimal("0.5"), "1/m3")


def test_unit_normalization_is_deterministic() -> None:
    assert FormulaValue.number(1, "m3*USD").unit == "USD*m3"
    assert FormulaValue.number(1, "USD/m3").unit == "USD/m3"
    assert FormulaValue.number(1, "USD*USD/USD").unit == "USD"


def test_power_requires_integer_unitless_exponent_and_composes_units() -> None:
    compiled = _compile("[quantity] ^ 2")

    assert evaluate_formula(
        compiled, {"quantity": FormulaValue.number(2, "m3")}
    ) == FormulaValue.number(4, "m3^2")

    with pytest.raises(FormulaTypeError, match="POWER_EXPONENT_MUST_BE_INTEGER"):
        _compile("[quantity] ^ 0.5")

    negative = _compile("[quantity] ^ -2")
    assert evaluate_formula(
        negative, {"quantity": FormulaValue.number(2, "m3")}
    ) == FormulaValue.number(Decimal("0.25"), "1/m3^2")

    with pytest.raises(FormulaTypeError, match="POWER_EXPONENT_MUST_BE_UNITLESS"):
        _compile("[quantity] ^ [unit_rate]")

    dynamic_schema = {
        "quantity": FormulaSchemaValue(FormulaType.NUMBER, "m3"),
        "exponent": FormulaSchemaValue(FormulaType.NUMBER),
    }
    with pytest.raises(FormulaTypeError, match="POWER_UNIT_EXPONENT_MUST_BE_LITERAL"):
        compile_formula(
            FormulaDefinition("dynamic.power", "1.0", "[quantity] ^ [exponent]", FormulaType.NUMBER),
            dynamic_schema,
        )


def test_invalid_unit_syntax_fails_closed() -> None:
    with pytest.raises(FormulaTypeError, match="INVALID_UNIT"):
        FormulaValue.number(1, "USD//m3")
