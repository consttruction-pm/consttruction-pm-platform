from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum


class ResourceType(str, Enum):
    LABOR = "labor"
    MACHINERY = "machinery"
    MATERIAL = "material"
    OTHER = "other"


class CostBasis(str, Enum):
    PER_UNIT = "per_unit"
    PER_HOUR = "per_hour"
    PER_DAY = "per_day"
    LUMP_SUM = "lump_sum"


@dataclass(frozen=True)
class ResourceRate:
    rate: Decimal
    basis: CostBasis
    currency: str = "USD"
    effective_from: date | None = None
    effective_to: date | None = None
    version: int = 1

    def is_effective_on(self, as_of: date) -> bool:
        return (
            (self.effective_from is None or as_of >= self.effective_from)
            and (self.effective_to is None or as_of <= self.effective_to)
        )


@dataclass
class Resource:
    """Resource master data with rates stored as a stable immutable value sequence.

    Callers may pass any iterable (including legacy lists); normalize it at the
    domain boundary so repository round-trips and equality do not depend on the
    container chosen by an API or persistence adapter.
    """

    id: str
    code: str
    name: str
    resource_type: ResourceType
    unit: str
    rates: tuple[ResourceRate, ...] = ()
    calendar_id: str | None = None
    active: bool = True

    def __post_init__(self) -> None:
        self.rates = tuple(self.rates)

    def rate_on(self, as_of: date) -> ResourceRate:
        candidates = [r for r in self.rates if r.is_effective_on(as_of)]
        if not candidates:
            raise ValueError(f"No effective rate for resource {self.code} on {as_of}")
        return max(candidates, key=lambda r: r.version)


@dataclass(frozen=True)
class ResourceAssignment:
    activity_id: str
    resource_id: str
    planned_units: Decimal
    actual_units: Decimal = Decimal("0")
    remaining_units: Decimal | None = None
    planned_cost: Decimal | None = None
    actual_cost: Decimal | None = None
    remaining_cost: Decimal | None = None

    def normalized_remaining_units(self) -> Decimal:
        return (
            self.remaining_units
            if self.remaining_units is not None
            else max(Decimal("0"), self.planned_units - self.actual_units)
        )


@dataclass(frozen=True)
class ResourcePeriodValue:
    resource_id: str
    period_start: date
    units: Decimal
    cost: Decimal


@dataclass(frozen=True)
class ResourceControlResult:
    planned_units: Decimal
    actual_units: Decimal
    remaining_units: Decimal
    planned_cost: Decimal
    actual_cost: Decimal
    remaining_cost: Decimal
    unit_variance: Decimal
    cost_variance: Decimal
    utilization_percent: Decimal
