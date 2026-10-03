from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .p6_user_defined_field_values_repository import P6DurationValue


class P6InterchangeValueError(ValueError):
    """Raised when a typed interchange value is not losslessly representable."""


@dataclass(frozen=True)
class P6InterchangeTypedValue:
    data_type: str
    value: Any
    unit: str | None = None
    currency: str | None = None

    def validate(self) -> None:
        if not isinstance(self.data_type, str) or not self.data_type.strip():
            raise P6InterchangeValueError("INVALID_DATA_TYPE")
        if self.unit is not None and (not isinstance(self.unit, str) or not self.unit.strip()):
            raise P6InterchangeValueError("INVALID_UNIT")
        if self.currency is not None and (
            not isinstance(self.currency, str) or not self.currency.strip()
        ):
            raise P6InterchangeValueError("INVALID_CURRENCY")

        kind = self.data_type
        if kind == "date":
            if not isinstance(self.value, date) or isinstance(self.value, datetime):
                raise P6InterchangeValueError("INVALID_DATE_VALUE")
        elif kind == "datetime":
            if (
                not isinstance(self.value, datetime)
                or self.value.tzinfo is None
                or self.value.utcoffset() is None
            ):
                raise P6InterchangeValueError("INVALID_DATETIME_VALUE")
        elif kind == "decimal":
            if not isinstance(self.value, Decimal) or not self.value.is_finite():
                raise P6InterchangeValueError("INVALID_DECIMAL_VALUE")
        elif kind == "duration":
            if not isinstance(self.value, P6DurationValue):
                raise P6InterchangeValueError("INVALID_DURATION_VALUE")
            self.value.validate()
            if self.unit is not None and self.unit != self.value.unit:
                raise P6InterchangeValueError("DURATION_UNIT_MISMATCH")
        elif kind == "boolean":
            if not isinstance(self.value, bool):
                raise P6InterchangeValueError("INVALID_BOOLEAN_VALUE")
        elif kind == "enum":
            if not isinstance(self.value, str) or not self.value.strip():
                raise P6InterchangeValueError("INVALID_ENUM_VALUE")
        elif kind == "integer":
            if not isinstance(self.value, int) or isinstance(self.value, bool):
                raise P6InterchangeValueError("INVALID_INTEGER_VALUE")
        elif kind == "string":
            if not isinstance(self.value, str):
                raise P6InterchangeValueError("INVALID_STRING_VALUE")
        else:
            raise P6InterchangeValueError(f"UNSUPPORTED_DATA_TYPE:{kind}")

    def to_payload(self) -> dict[str, Any]:
        self.validate()
        value: Any
        if self.data_type == "date":
            value = self.value.isoformat()
        elif self.data_type == "datetime":
            value = self.value.isoformat()
        elif self.data_type == "decimal":
            value = str(self.value)
        elif self.data_type == "duration":
            value = {"value": str(self.value.value), "unit": self.value.unit}
        else:
            value = self.value
        return {
            "data_type": self.data_type,
            "value": value,
            "unit": self.unit,
            "currency": self.currency,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_payload(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "P6InterchangeTypedValue":
        if not isinstance(payload, Mapping):
            raise P6InterchangeValueError("INVALID_PAYLOAD")
        kind = payload.get("data_type")
        unit = payload.get("unit")
        currency = payload.get("currency")
        raw = payload.get("value")
        if not isinstance(kind, str):
            raise P6InterchangeValueError("INVALID_DATA_TYPE")

        try:
            if kind == "date":
                value = date.fromisoformat(str(raw))
            elif kind == "datetime":
                value = datetime.fromisoformat(str(raw))
            elif kind == "decimal":
                value = Decimal(str(raw))
            elif kind == "duration":
                if not isinstance(raw, Mapping):
                    raise ValueError("duration object required")
                value = P6DurationValue(
                    Decimal(str(raw["value"])),
                    str(raw["unit"]),
                )
            elif kind == "boolean":
                if not isinstance(raw, bool):
                    raise ValueError("boolean required")
                value = raw
            elif kind == "integer":
                if isinstance(raw, bool) or not isinstance(raw, int):
                    raise ValueError("integer required")
                value = raw
            elif kind in {"enum", "string"}:
                value = str(raw)
            else:
                raise P6InterchangeValueError(f"UNSUPPORTED_DATA_TYPE:{kind}")
        except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
            raise P6InterchangeValueError(f"INVALID_{kind.upper()}_VALUE") from exc

        result = cls(kind, value, unit, currency)
        result.validate()
        return result

    @classmethod
    def from_json(cls, payload: str) -> "P6InterchangeTypedValue":
        try:
            raw = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise P6InterchangeValueError("INVALID_JSON") from exc
        return cls.from_payload(raw)


__all__ = ["P6InterchangeTypedValue", "P6InterchangeValueError"]
