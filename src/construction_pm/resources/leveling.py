from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .calendar import ResourceCalendar


@dataclass(frozen=True)
class ResourceLoad:
    resource_id: str
    period_start: date
    units: Decimal


@dataclass(frozen=True)
class Overload:
    resource_id: str
    period_start: date
    loaded_units: Decimal
    capacity_units: Decimal
    excess_units: Decimal
    utilization_percent: Decimal


def detect_overloads(
    calendar_by_resource: dict[str, ResourceCalendar],
    loads: list[ResourceLoad],
) -> list[Overload]:
    result: list[Overload] = []
    for load in loads:
        calendar = calendar_by_resource[load.resource_id]
        capacity = calendar.capacity_on(load.period_start)
        if load.units > capacity:
            utilization = (
                Decimal("0")
                if capacity == 0
                else (load.units / capacity * Decimal("100"))
            )
            result.append(
                Overload(
                    resource_id=load.resource_id,
                    period_start=load.period_start,
                    loaded_units=load.units,
                    capacity_units=capacity,
                    excess_units=load.units - capacity,
                    utilization_percent=utilization,
                )
            )
    return result


def available_capacity(
    calendar: ResourceCalendar,
    period_start: date,
    loaded_units: Decimal,
) -> Decimal:
    return max(Decimal("0"), calendar.capacity_on(period_start) - loaded_units)
