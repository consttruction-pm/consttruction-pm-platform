from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .calculator import calculate_assignment_control
from .models import Resource, ResourceAssignment


@dataclass(frozen=True)
class ResourcePortfolioControl:
    planned_units: Decimal
    actual_units: Decimal
    remaining_units: Decimal
    planned_cost: Decimal
    actual_cost: Decimal
    remaining_cost: Decimal
    unit_variance: Decimal
    cost_variance: Decimal


def aggregate_assignments(
    resources: dict[str, Resource],
    assignments: list[ResourceAssignment],
    as_of,
) -> ResourcePortfolioControl:
    totals = [Decimal("0")] * 8
    for assignment in assignments:
        resource = resources[assignment.resource_id]
        result = calculate_assignment_control(resource, assignment, as_of)
        values = (
            result.planned_units,
            result.actual_units,
            result.remaining_units,
            result.planned_cost,
            result.actual_cost,
            result.remaining_cost,
            result.unit_variance,
            result.cost_variance,
        )
        totals = [left + right for left, right in zip(totals, values)]

    return ResourcePortfolioControl(*totals)
