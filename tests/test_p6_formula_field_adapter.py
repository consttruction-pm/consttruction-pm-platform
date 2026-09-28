from datetime import date, datetime, timezone

import pytest

from construction_pm.p6_field_registry import P6FieldDefinition, P6FieldType
from construction_pm.p6_formula_engine import (
    FormulaDefinition,
    FormulaSchemaValue,
    FormulaType,
    FormulaTypeError,
    FormulaValue,
    compile_formula,
    evaluate_formula,
)
from construction_pm.p6_formula_field_adapter import (
    P6FormulaFieldAdapter,
    P6FormulaFieldTypeError,
)


def field(
    field_id: str,
    data_type: P6FieldType,
    unit: str | None = None,
) -> P6FieldDefinition:
    return P6FieldDefinition(
        field_id=field_id,
        subject_area="Test",
        p6_field=field_id,
        display_name=field_id,
        data_type=data_type,
        writable=True,
        computed=False,
        unit=unit,
    )


@pytest.mark.parametrize(
    ("p6_type", "expected"),
    [
        (P6FieldType.STRING, FormulaType.TEXT),
        (P6FieldType.DATE, FormulaType.DATE),
        (P6FieldType.DATETIME, FormulaType.DATETIME),
        (P6FieldType.DECIMAL, FormulaType.NUMBER),
        (P6FieldType.PERCENTAGE, FormulaType.NUMBER),
        (P6FieldType.INTEGER, FormulaType.NUMBER),
        (P6FieldType.DOUBLE, FormulaType.NUMBER),
        (P6FieldType.COST, FormulaType.NUMBER),
        (P6FieldType.BOOLEAN, FormulaType.BOOLEAN),
        (P6FieldType.ENUM, FormulaType.TEXT),
        (P6FieldType.OBJECT_ID, FormulaType.TEXT),
    ],
)
def test_p6_field_types_map_to_safe_formula_types(
    p6_type: P6FieldType, expected: FormulaType
) -> None:
    assert P6FormulaFieldAdapter.formula_type_for_p6(p6_type) is expected


@pytest.mark.parametrize(
    "p6_type",
    [
        P6FieldType.DURATION,
        P6FieldType.UNIT,
        P6FieldType.OBJECT_ID_ARRAY,
        P6FieldType.STRING_ARRAY,
        P6FieldType.COMPLEX,
        P6FieldType.SPREAD,
    ],
)
def test_unsupported_p6_types_fail_closed(p6_type: P6FieldType) -> None:
    with pytest.raises(
        P6FormulaFieldTypeError,
        match=f"UNSUPPORTED_P6_FORMULA_FIELD_TYPE:{p6_type.value}",
    ):
        P6FormulaFieldAdapter.formula_type_for_p6(p6_type)


def test_adapter_preserves_field_unit() -> None:
    schema = P6FormulaFieldAdapter.schema_for_field(
        field("cost", P6FieldType.COST, "USD")
    )
    assert schema.type is FormulaType.NUMBER
    assert schema.unit == "USD"


def test_date_fields_compare_as_typed_dates() -> None:
    schema = {
        "start": P6FormulaFieldAdapter.schema_for_field(
            field("start", P6FieldType.DATE)
        ),
        "finish": P6FormulaFieldAdapter.schema_for_field(
            field("finish", P6FieldType.DATE)
        ),
    }
    compiled = compile_formula(
        FormulaDefinition(
            "date.compare", "1.0", "[finish] >= [start]", FormulaType.BOOLEAN
        ),
        schema,
    )
    assert evaluate_formula(
        compiled,
        {
            "start": FormulaValue.date(date(2026, 9, 28)),
            "finish": FormulaValue.date(date(2026, 9, 29)),
        },
    ) == FormulaValue.boolean(True)


def test_datetime_values_require_timezone_and_compare_typed() -> None:
    schema = {
        "start": P6FormulaFieldAdapter.schema_for_field(
            field("start", P6FieldType.DATETIME)
        ),
        "finish": P6FormulaFieldAdapter.schema_for_field(
            field("finish", P6FieldType.DATETIME)
        ),
    }
    compiled = compile_formula(
        FormulaDefinition(
            "datetime.compare", "1.0", "[finish] > [start]", FormulaType.BOOLEAN
        ),
        schema,
    )
    start = datetime(2026, 9, 28, 8, 0, tzinfo=timezone.utc)
    finish = datetime(2026, 9, 28, 9, 0, tzinfo=timezone.utc)
    assert evaluate_formula(
        compiled,
        {
            "start": FormulaValue.datetime(start),
            "finish": FormulaValue.datetime(finish),
        },
    ) == FormulaValue.boolean(True)

    with pytest.raises(FormulaTypeError, match="TIMEZONE_AWARE_DATETIME_REQUIRED"):
        FormulaValue.datetime(datetime(2026, 9, 28, 8, 0))


def test_date_arithmetic_is_not_silently_allowed() -> None:
    schema = {"start": FormulaSchemaValue(FormulaType.DATE)}
    with pytest.raises(FormulaTypeError, match="NUMERIC_OPERANDS_REQUIRED"):
        compile_formula(
            FormulaDefinition("date.add", "1.0", "[start] + 1", FormulaType.DATE),
            schema,
        )
