from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum


class ResourceLevelingError(ValueError):
    """Raised when a resource-leveling contract is invalid."""


class SortOrder(str, Enum):
    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"


@dataclass(frozen=True)
class ResourceDemand:
    resource_id: str
    period: date
    units: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.resource_id, str) or not self.resource_id.strip():
            raise ResourceLevelingError("INVALID_RESOURCE_ID")
        if not isinstance(self.period, date):
            raise ResourceLevelingError("INVALID_PERIOD")
        if not isinstance(self.units, Decimal) or not self.units.is_finite() or self.units < 0:
            raise ResourceLevelingError("INVALID_DEMAND_UNITS")


@dataclass(frozen=True)
class ResourceCapacity:
    resource_id: str
    period: date
    units: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.resource_id, str) or not self.resource_id.strip():
            raise ResourceLevelingError("INVALID_RESOURCE_ID")
        if not isinstance(self.period, date):
            raise ResourceLevelingError("INVALID_PERIOD")
        if not isinstance(self.units, Decimal) or not self.units.is_finite() or self.units < 0:
            raise ResourceLevelingError("INVALID_CAPACITY_UNITS")


@dataclass(frozen=True)
class OverAllocation:
    resource_id: str
    period: date
    demand: Decimal
    base_capacity: Decimal
    effective_capacity: Decimal
    excess: Decimal


@dataclass(frozen=True)
class LevelingPriority:
    field_name: str
    sort_order: SortOrder

    def __post_init__(self) -> None:
        if not isinstance(self.field_name, str) or not self.field_name.strip():
            raise ResourceLevelingError("INVALID_PRIORITY_FIELD")
        if not isinstance(self.sort_order, SortOrder):
            raise ResourceLevelingError("INVALID_PRIORITY_SORT_ORDER")


@dataclass(frozen=True)
class ResourceLevelingOptions:
    level_all_resources: bool = False
    level_within_float: bool = False
    min_float_to_preserve: Decimal = Decimal("0")
    over_allocation_percentage: Decimal = Decimal("0")
    resource_ids: tuple[str, ...] = ()
    priorities: tuple[LevelingPriority, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.level_all_resources, bool):
            raise ResourceLevelingError("INVALID_LEVEL_ALL_RESOURCES")
        if not isinstance(self.level_within_float, bool):
            raise ResourceLevelingError("INVALID_LEVEL_WITHIN_FLOAT")
        if (
            not isinstance(self.min_float_to_preserve, Decimal)
            or not self.min_float_to_preserve.is_finite()
            or self.min_float_to_preserve < 0
        ):
            raise ResourceLevelingError("INVALID_MIN_FLOAT_TO_PRESERVE")
        if (
            not isinstance(self.over_allocation_percentage, Decimal)
            or not self.over_allocation_percentage.is_finite()
            or self.over_allocation_percentage < 0
            or self.over_allocation_percentage > 100
        ):
            raise ResourceLevelingError("INVALID_OVER_ALLOCATION_PERCENTAGE")
        if len(set(self.resource_ids)) != len(self.resource_ids):
            raise ResourceLevelingError("DUPLICATE_RESOURCE_ID")
        if any(not isinstance(resource_id, str) or not resource_id.strip() for resource_id in self.resource_ids):
            raise ResourceLevelingError("INVALID_RESOURCE_ID")


def detect_over_allocations(
    demands: tuple[ResourceDemand, ...] | list[ResourceDemand],
    capacities: tuple[ResourceCapacity, ...] | list[ResourceCapacity],
    *,
    over_allocation_percentage: Decimal = Decimal("0"),
) -> tuple[OverAllocation, ...]:
    if (
        not isinstance(over_allocation_percentage, Decimal)
        or not over_allocation_percentage.is_finite()
        or over_allocation_percentage < 0
        or over_allocation_percentage > 100
    ):
        raise ResourceLevelingError("INVALID_OVER_ALLOCATION_PERCENTAGE")

    demand_by_key: dict[tuple[str, date], Decimal] = {}
    capacity_by_key: dict[tuple[str, date], Decimal] = {}
    for item in demands:
        demand_by_key[(item.resource_id, item.period)] = (
            demand_by_key.get((item.resource_id, item.period), Decimal("0")) + item.units
        )
    for item in capacities:
        key = (item.resource_id, item.period)
        if key in capacity_by_key:
            raise ResourceLevelingError("DUPLICATE_RESOURCE_CAPACITY")
        capacity_by_key[key] = item.units

    result: list[OverAllocation] = []
    for resource_id, period in sorted(demand_by_key, key=lambda key: (key[1], key[0])):
        demand = demand_by_key[(resource_id, period)]
        base_capacity = capacity_by_key.get((resource_id, period), Decimal("0"))
        effective_capacity = base_capacity * (
            Decimal("1") + over_allocation_percentage / Decimal("100")
        )
        excess = demand - effective_capacity
        if excess > 0:
            result.append(
                OverAllocation(
                    resource_id=resource_id,
                    period=period,
                    demand=demand,
                    base_capacity=base_capacity,
                    effective_capacity=effective_capacity,
                    excess=excess,
                )
            )
    return tuple(result)
