from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from construction_pm.p6_interchange_values import (
    P6InterchangeTypedValue,
    P6InterchangeValueError,
)
from construction_pm.p6_user_defined_field_values_repository import P6DurationValue


@pytest.mark.parametrize(
    "typed",
    (
        P6InterchangeTypedValue("date", date(2026, 9, 28)),
        P6InterchangeTypedValue(
            "datetime", datetime(2026, 9, 28, 12, 30, tzinfo=timezone.utc)
        ),
        P6InterchangeTypedValue("decimal", Decimal("1234.500")),
        P6InterchangeTypedValue("duration", P6DurationValue(Decimal("7.25"), "hours")),
        P6InterchangeTypedValue("boolean", True),
        P6InterchangeTypedValue("enum", "TASK"),
        P6InterchangeTypedValue("integer", 42),
        P6InterchangeTypedValue("string", "A-10"),
        P6InterchangeTypedValue("string-array", ["Activity Code", "WBS"]),
        P6InterchangeTypedValue("object-id-array", ["obj-1", "obj-2"]),
        P6InterchangeTypedValue("decimal", Decimal("1250.00"), currency="USD"),
    ),
)
def test_json_round_trip_preserves_typed_value_and_semantics(typed) -> None:
    restored = P6InterchangeTypedValue.from_json(typed.to_json())

    assert restored.data_type == typed.data_type
    assert restored.value == typed.value
    assert restored.unit == typed.unit
    assert restored.currency == typed.currency


def test_duration_unit_is_explicit_and_cannot_drift() -> None:
    value = P6InterchangeTypedValue(
        "duration",
        P6DurationValue(Decimal("8"), "hours"),
        unit="days",
    )

    with pytest.raises(P6InterchangeValueError, match="DURATION_UNIT_MISMATCH"):
        value.to_payload()


def test_invalid_boolean_does_not_coerce_from_string() -> None:
    with pytest.raises(P6InterchangeValueError, match="INVALID_BOOLEAN_VALUE"):
        P6InterchangeTypedValue.from_payload(
            {"data_type": "boolean", "value": "true"}
        )


def test_invalid_decimal_fails_closed() -> None:
    with pytest.raises(P6InterchangeValueError, match="INVALID_DECIMAL_VALUE"):
        P6InterchangeTypedValue.from_payload(
            {"data_type": "decimal", "value": "not-a-number"}
        )


def test_unknown_type_is_rejected() -> None:
    with pytest.raises(P6InterchangeValueError, match="UNSUPPORTED_DATA_TYPE:binary"):
        P6InterchangeTypedValue("binary", b"raw").to_payload()



def test_from_payload_rejects_non_integer_numeric_values_without_truncation() -> None:
    with pytest.raises(P6InterchangeValueError, match="INVALID_INTEGER_VALUE"):
        P6InterchangeTypedValue.from_payload({"data_type": "integer", "value": 3.9})


@pytest.mark.parametrize("kind", ("enum", "string"))
def test_from_payload_rejects_non_string_values_without_coercion(kind: str) -> None:
    with pytest.raises(
        P6InterchangeValueError,
        match=f"INVALID_{kind.upper()}_VALUE",
    ):
        P6InterchangeTypedValue.from_payload(
            {"data_type": kind, "value": 123}
        )


@pytest.mark.parametrize("kind", ("string-array", "object-id-array"))
@pytest.mark.parametrize("raw", ("not-an-array", [1, "valid"], [None]))
def test_array_typed_values_reject_non_string_members(kind: str, raw) -> None:
    with pytest.raises(
        P6InterchangeValueError,
        match=f"INVALID_{kind.upper().replace('-', '_')}_VALUE",
    ):
        P6InterchangeTypedValue(kind, raw).to_payload()


@pytest.mark.parametrize("kind", ("string-array", "object-id-array"))
@pytest.mark.parametrize("raw", ("not-an-array", [1, "valid"], [None]))
def test_array_payloads_reject_non_string_members(kind: str, raw) -> None:
    with pytest.raises(
        P6InterchangeValueError,
        match=f"INVALID_{kind.upper().replace('-', '_')}_VALUE",
    ):
        P6InterchangeTypedValue.from_payload({"data_type": kind, "value": raw})
