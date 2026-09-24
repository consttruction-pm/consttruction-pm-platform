from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from .models import Resource, ResourceAssignment, ResourcePeriodValue
from .calculator import calculate_cost


def spread_units(
    resource: Resource,
    assignment: ResourceAssignment,
    start: date,
    finish: date,
    as_of: date,
) -> list[ResourcePeriodValue]:
    if finish < start:
        raise ValueError("finish must not be before start")

    days = (finish - start).days + 1
    total = assignment.planned_units
    daily = total / Decimal(days)
    result: list[ResourcePeriodValue] = []

    for index in range(days):
        period = start + timedelta(days=index)
        units = daily if index < days - 1 else total - daily * Decimal(days - 1)
        result.append(
            ResourcePeriodValue(
                resource_id=assignment.resource_id,
                period_start=period,
                units=units,
                cost=calculate_cost(resource, units, as_of),
            )
        )
    return result


def aggregate_loading(
    values: list[ResourcePeriodValue],
) -> dict[tuple[str, date], ResourcePeriodValue]:
    totals: dict[tuple[str, date], list[Decimal]] = defaultdict(
        lambda: [Decimal("0"), Decimal("0")]
    )
    for value in values:
        key = (value.resource_id, value.period_start)
        totals[key][0] += value.units
        totals[key][1] += value.cost

    return {
        key: ResourcePeriodValue(
            resource_id=key[0],
            period_start=key[1],
            units=amounts[0],
            cost=amounts[1],
        )
        for key, amounts in totals.items()
    }
