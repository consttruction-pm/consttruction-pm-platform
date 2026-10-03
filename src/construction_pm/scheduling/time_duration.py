from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class DurationUnit(str, Enum):
    """Explicit duration/lag unit contract for the time-aware scheduling path."""

    WORKING_DAY = "working-day"
    WORKING_HOUR = "working-hour"


@dataclass(frozen=True)
class TimeQuantity:
    """Portable, explicit duration quantity.

    Decimal is used so working-hour values remain calculation-safe and are not
    silently coerced to binary floating-point values.
    """

    value: Decimal
    unit: DurationUnit

    def __post_init__(self) -> None:
        if not isinstance(self.unit, DurationUnit):
            raise TypeError("unit must be a DurationUnit")
        try:
            value = Decimal(str(self.value))
        except Exception as exc:
            raise TypeError("value must be a decimal-compatible quantity") from exc
        if not value.is_finite():
            raise ValueError("quantity must be finite")
        if value < 0:
            raise ValueError("quantity must be non-negative")
        object.__setattr__(self, "value", value)

    @classmethod
    def working_days(cls, value: Decimal | int | float) -> "TimeQuantity":
        return cls(Decimal(str(value)), DurationUnit.WORKING_DAY)

    @classmethod
    def working_hours(cls, value: Decimal | int | float) -> "TimeQuantity":
        return cls(Decimal(str(value)), DurationUnit.WORKING_HOUR)


@dataclass(frozen=True)
class LagQuantity:
    """Explicit relationship-lag contract.

    Sign is preserved because negative lag is a supported lead/overlap
    capability. Zero is valid. Unit conversion is intentionally not performed
    here because conversion requires the authoritative calendar resolver.
    """

    value: Decimal
    unit: DurationUnit

    def __post_init__(self) -> None:
        if not isinstance(self.unit, DurationUnit):
            raise TypeError("unit must be a DurationUnit")
        try:
            value = Decimal(str(self.value))
        except Exception as exc:
            raise TypeError("value must be a decimal-compatible lag") from exc
        if not value.is_finite():
            raise ValueError("lag must be finite")
        object.__setattr__(self, "value", value)

    @classmethod
    def working_days(cls, value: Decimal | int | float) -> "LagQuantity":
        return cls(Decimal(str(value)), DurationUnit.WORKING_DAY)

    @classmethod
    def working_hours(cls, value: Decimal | int | float) -> "LagQuantity":
        return cls(Decimal(str(value)), DurationUnit.WORKING_HOUR)
