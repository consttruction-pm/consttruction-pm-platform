from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Final, Mapping


P6_CALENDAR_PERIOD_FIELDS: Final[Mapping[str, str]] = {
    "day": "HoursPerDay",
    "week": "HoursPerWeek",
    "month": "HoursPerMonth",
    "year": "HoursPerYear",
}


def _as_positive_decimal(value: Decimal | int | float | str, field_name: str) -> Decimal:
    try:
        decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be a finite positive number") from exc
    if not decimal_value.is_finite() or decimal_value <= 0:
        raise ValueError(f"{field_name} must be a finite positive number")
    return decimal_value


@dataclass(frozen=True)
class CalendarTimePeriodFactors:
    """P6 calendar conversion factors used to display time units and durations.

    These values are calendar metadata, not scheduling arithmetic. The
    authoritative Shared Scheduling Core continues to use its existing working
    day/time resolvers for CPM and duration calculations.
    """

    hours_per_day: Decimal = Decimal("8")
    hours_per_week: Decimal = Decimal("40")
    hours_per_month: Decimal = Decimal("160")
    hours_per_year: Decimal = Decimal("2080")

    def __post_init__(self) -> None:
        object.__setattr__(self, "hours_per_day", _as_positive_decimal(self.hours_per_day, "hours_per_day"))
        object.__setattr__(self, "hours_per_week", _as_positive_decimal(self.hours_per_week, "hours_per_week"))
        object.__setattr__(self, "hours_per_month", _as_positive_decimal(self.hours_per_month, "hours_per_month"))
        object.__setattr__(self, "hours_per_year", _as_positive_decimal(self.hours_per_year, "hours_per_year"))

    def value_for(self, period: str) -> Decimal:
        values = {
            "day": self.hours_per_day,
            "week": self.hours_per_week,
            "month": self.hours_per_month,
            "year": self.hours_per_year,
        }
        try:
            return values[period.strip().lower()]
        except KeyError as exc:
            raise ValueError(f"unsupported calendar time period: {period}") from exc

    def as_p6_fields(self) -> dict[str, Decimal]:
        return {
            "HoursPerDay": self.hours_per_day,
            "HoursPerWeek": self.hours_per_week,
            "HoursPerMonth": self.hours_per_month,
            "HoursPerYear": self.hours_per_year,
        }
