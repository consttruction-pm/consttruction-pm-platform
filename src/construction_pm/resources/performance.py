from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .control import ResourcePortfolioControl, aggregate_assignments
from .models import Resource, ResourceAssignment


@dataclass(frozen=True)
class ResourcePerformanceBridge:
    planned_cost: Decimal
    actual_cost: Decimal
    remaining_cost: Decimal
    at_completion_cost: Decimal
    cost_variance_at_completion: Decimal
    planned_units: Decimal
    actual_units: Decimal
    remaining_units: Decimal


def build_resource_performance_bridge(
    resources: dict[str, Resource],
    assignments: list[ResourceAssignment],
    as_of,
) -> ResourcePerformanceBridge:
    control: ResourcePortfolioControl = aggregate_assignments(
        resources, assignments, as_of
    )
    at_completion = control.actual_cost + control.remaining_cost
    return ResourcePerformanceBridge(
        planned_cost=control.planned_cost,
        actual_cost=control.actual_cost,
        remaining_cost=control.remaining_cost,
        at_completion_cost=at_completion,
        cost_variance_at_completion=control.planned_cost - at_completion,
        planned_units=control.planned_units,
        actual_units=control.actual_units,
        remaining_units=control.remaining_units,
    )
