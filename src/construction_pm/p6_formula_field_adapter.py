from __future__ import annotations

from dataclasses import dataclass

from .p6_field_registry import P6FieldDefinition, P6FieldType
from .p6_formula_engine import FormulaSchemaValue, FormulaType, FormulaTypeError


class P6FormulaFieldTypeError(FormulaTypeError):
    """Raised when a P6 field type has no safe formula representation yet."""


@dataclass(frozen=True)
class P6FormulaFieldAdapter:
    """Maps authoritative P6 field metadata to the Shared/Core formula schema."""

    @staticmethod
    def schema_for_field(field: P6FieldDefinition) -> FormulaSchemaValue:
        return FormulaSchemaValue(
            type=P6FormulaFieldAdapter.formula_type_for_p6(field.data_type),
            unit=field.unit,
        )

    @staticmethod
    def formula_type_for_p6(field_type: P6FieldType) -> FormulaType:
        mapping = {
            P6FieldType.STRING: FormulaType.TEXT,
            P6FieldType.DATE: FormulaType.DATE,
            P6FieldType.DATETIME: FormulaType.DATETIME,
            P6FieldType.DECIMAL: FormulaType.NUMBER,
            P6FieldType.PERCENTAGE: FormulaType.NUMBER,
            P6FieldType.BOOLEAN: FormulaType.BOOLEAN,
            P6FieldType.ENUM: FormulaType.TEXT,
            P6FieldType.INTEGER: FormulaType.NUMBER,
            P6FieldType.DOUBLE: FormulaType.NUMBER,
            P6FieldType.COST: FormulaType.NUMBER,
            P6FieldType.OBJECT_ID: FormulaType.TEXT,
        }
        try:
            return mapping[field_type]
        except KeyError as exc:
            raise P6FormulaFieldTypeError(
                f"UNSUPPORTED_P6_FORMULA_FIELD_TYPE:{field_type.value}"
            ) from exc


__all__ = ["P6FormulaFieldAdapter", "P6FormulaFieldTypeError"]
