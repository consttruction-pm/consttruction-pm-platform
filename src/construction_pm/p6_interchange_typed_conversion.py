from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from .p6_field_registry import P6FieldDefinition, P6FieldType
from .p6_interchange_values import P6InterchangeTypedValue
from .p6_user_defined_field_values_repository import P6DurationValue
from .p6_mapping_registry import P6MappingFormat
from .scheduling.activity import ActivityStatus, ActivityType

class P6InterchangeTypedConversionError(ValueError):
    """Raised when an interchange value cannot be converted to the canonical field type."""

def typed_value_for_field(field: P6FieldDefinition, raw: Any) -> P6InterchangeTypedValue:
    kind = field.data_type
    try:
        if kind is P6FieldType.DATE:
            value = raw if isinstance(raw, date) and not isinstance(raw, datetime) else date.fromisoformat(str(raw))
            return P6InterchangeTypedValue("date", value, unit=field.unit)
        if kind is P6FieldType.DATETIME:
            if isinstance(raw, datetime):
                value = raw
            else:
                text = str(raw)
                if len(text) == 10:
                    value = datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
                else:
                    value = datetime.fromisoformat(text)
            if value.tzinfo is None or value.utcoffset() is None:
                value = value.replace(tzinfo=timezone.utc)
            return P6InterchangeTypedValue("datetime", value, unit=field.unit)
        if kind in {P6FieldType.DECIMAL, P6FieldType.DOUBLE, P6FieldType.COST, P6FieldType.PERCENTAGE, P6FieldType.UNIT}:
            value = raw if isinstance(raw, Decimal) else Decimal(str(raw))
            if not value.is_finite():
                raise ValueError("finite decimal required")
            return P6InterchangeTypedValue("decimal", value, unit=field.unit)
        if kind is P6FieldType.DURATION:
            if isinstance(raw, P6DurationValue): value = raw
            elif isinstance(raw, dict) and {"value", "unit"} <= set(raw): value = P6DurationValue(Decimal(str(raw["value"])), str(raw["unit"]))
            else: raise ValueError("duration object with value and unit required")
            return P6InterchangeTypedValue("duration", value, unit=value.unit)
        if kind is P6FieldType.BOOLEAN:
            if not isinstance(raw, bool): raise ValueError("boolean required")
            return P6InterchangeTypedValue("boolean", raw)
        if kind is P6FieldType.INTEGER:
            # File codecs commonly provide numbers as strings. Accept only finite,
            # mathematically integral values; never truncate a fractional value.
            if isinstance(raw, bool):
                raise ValueError("boolean is not integer")
            numeric = raw if isinstance(raw, Decimal) else Decimal(str(raw))
            if not numeric.is_finite() or numeric != numeric.to_integral_value():
                raise ValueError("integer value required")
            return P6InterchangeTypedValue("integer", int(numeric))
        if kind is P6FieldType.ENUM: return P6InterchangeTypedValue("enum", str(raw))
        if kind in {P6FieldType.STRING, P6FieldType.OBJECT_ID}: return P6InterchangeTypedValue("string", str(raw))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise P6InterchangeTypedConversionError(f"INVALID_CANONICAL_VALUE:{field.field_id}:{field.data_type.value}") from exc
    raise P6InterchangeTypedConversionError(f"UNSUPPORTED_CANONICAL_FIELD_TYPE:{field.field_id}:{kind.value}")



_XER_ACTIVITY_STATUS_FROM_WIRE = {
    "TK_NotStart": ActivityStatus.NOT_STARTED.value,
    "TK_Active": ActivityStatus.IN_PROGRESS.value,
    "TK_Complete": ActivityStatus.COMPLETED.value,
}
_XER_ACTIVITY_TYPE_FROM_WIRE = {
    "TT_Task": ActivityType.TASK_DEPENDENT.value,
    "TT_Rsrc": ActivityType.RESOURCE_DEPENDENT.value,
    "TT_LOE": ActivityType.LEVEL_OF_EFFORT.value,
    "TT_Mile": ActivityType.START_MILESTONE.value,
    "TT_FinMile": ActivityType.FINISH_MILESTONE.value,
    "TT_WBS": ActivityType.WBS_SUMMARY.value,
}


def typed_value_for_mapping(field: P6FieldDefinition, raw: Any, *, format: P6MappingFormat, source_field: str) -> P6InterchangeTypedValue:
    """Decode format-specific enum tokens, then validate the canonical field type."""
    if format is P6MappingFormat.XER_PROJECT:
        if source_field == "status_code" and field.field_id == "activity.status":
            try:
                raw = _XER_ACTIVITY_STATUS_FROM_WIRE[str(raw)]
            except KeyError as exc:
                raise P6InterchangeTypedConversionError(
                    f"UNSUPPORTED_XER_ACTIVITY_STATUS:{raw}"
                ) from exc
        elif source_field == "task_type" and field.field_id == "activity.type":
            try:
                raw = _XER_ACTIVITY_TYPE_FROM_WIRE[str(raw)]
            except KeyError as exc:
                raise P6InterchangeTypedConversionError(
                    f"UNSUPPORTED_XER_ACTIVITY_TYPE:{raw}"
                ) from exc
    return typed_value_for_field(field, raw)


def source_value_for_mapping(field: P6FieldDefinition, canonical: Any, *, format: P6MappingFormat, source_field: str) -> Any:
    """Encode canonical values using the external tokens for the mapped field."""
    value = typed_value_for_field(field, canonical).value
    if format is P6MappingFormat.XER_PROJECT:
        if source_field == "status_code" and field.field_id == "activity.status":
            reverse = {canonical_value: wire for wire, canonical_value in _XER_ACTIVITY_STATUS_FROM_WIRE.items()}
            try:
                return reverse[str(value)]
            except KeyError as exc:
                raise P6InterchangeTypedConversionError(
                    f"UNSUPPORTED_CANONICAL_XER_ACTIVITY_STATUS:{value}"
                ) from exc
        if source_field == "task_type" and field.field_id == "activity.type":
            reverse = {canonical_value: wire for wire, canonical_value in _XER_ACTIVITY_TYPE_FROM_WIRE.items()}
            try:
                return reverse[str(value)]
            except KeyError as exc:
                raise P6InterchangeTypedConversionError(
                    f"UNSUPPORTED_CANONICAL_XER_ACTIVITY_TYPE:{value}"
                ) from exc
    return value


__all__ = ["P6InterchangeTypedConversionError", "typed_value_for_field", "typed_value_for_mapping", "source_value_for_mapping"]
