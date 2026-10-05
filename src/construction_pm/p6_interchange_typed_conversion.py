from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from .p6_field_registry import P6FieldDefinition, P6FieldType
from .p6_interchange_values import P6InterchangeTypedValue
from .p6_user_defined_field_values_repository import P6DurationValue

class P6InterchangeTypedConversionError(ValueError):
    """Raised when an interchange value cannot be converted to the canonical field type."""

def typed_value_for_field(field: P6FieldDefinition, raw: Any) -> P6InterchangeTypedValue:
    kind = field.data_type
    try:
        if kind is P6FieldType.DATE:
            value = raw if isinstance(raw, date) and not isinstance(raw, datetime) else date.fromisoformat(str(raw))
            return P6InterchangeTypedValue("date", value, unit=field.unit)
        if kind is P6FieldType.DATETIME:
            if isinstance(raw, datetime): value = raw
            else:
                text = str(raw)
                value = datetime.fromisoformat(text).replace(tzinfo=timezone.utc) if len(text) == 10 else datetime.fromisoformat(text)
            if value.tzinfo is None or value.utcoffset() is None: value = value.replace(tzinfo=timezone.utc)
            return P6InterchangeTypedValue("datetime", value, unit=field.unit)
        if kind in {P6FieldType.DECIMAL, P6FieldType.DOUBLE, P6FieldType.COST, P6FieldType.PERCENTAGE, P6FieldType.UNIT}:
            value = raw if isinstance(raw, Decimal) else Decimal(str(raw))
            return P6InterchangeTypedValue("decimal", value, unit=field.unit)
        if kind is P6FieldType.DURATION:
            if isinstance(raw, P6DurationValue): value = raw
            elif isinstance(raw, dict) and {"value","unit"} <= set(raw): value = P6DurationValue(Decimal(str(raw["value"])), str(raw["unit"]))
            else: raise ValueError("duration object with value and unit required")
            return P6InterchangeTypedValue("duration", value, unit=value.unit)
        if kind is P6FieldType.BOOLEAN:
            if not isinstance(raw, bool): raise ValueError("boolean required")
            return P6InterchangeTypedValue("boolean", raw)
        if kind is P6FieldType.INTEGER: return P6InterchangeTypedValue("integer", raw if isinstance(raw,int) and not isinstance(raw,bool) else int(raw))
        if kind is P6FieldType.ENUM: return P6InterchangeTypedValue("enum", str(raw))
        if kind in {P6FieldType.STRING, P6FieldType.OBJECT_ID}: return P6InterchangeTypedValue("string", str(raw))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise P6InterchangeTypedConversionError(f"INVALID_CANONICAL_VALUE:{field.field_id}:{field.data_type.value}") from exc
    raise P6InterchangeTypedConversionError(f"UNSUPPORTED_CANONICAL_FIELD_TYPE:{field.field_id}:{kind.value}")

__all__=["P6InterchangeTypedConversionError","typed_value_for_field"]
