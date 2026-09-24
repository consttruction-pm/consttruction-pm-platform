from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .models import CostBasis, Resource, ResourceAssignment, ResourceControlResult

CENT = Decimal("0.01")
ZERO = Decimal("0")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_cost(
    resource: Resource,
    units: Decimal,
    as_of,
    *,
    hours_per_day: Decimal = Decimal("8"),
) -> Decimal:
    rate = resource.rate_on(as_of)
    if rate.basis == CostBasis.PER_UNIT:
        return money(units * rate.rate)
    if rate.basis == CostBasis.PER_HOUR:
        return money(units * rate.rate)
    if rate.basis == CostBasis.PER_DAY:
        return money(units * rate.rate)
    if rate.basis == CostBasis.LUMP_SUM:
        return money(rate.rate if units > ZERO else ZERO)
    raise ValueError(f"Unsupported cost basis: {rate.basis}")


def calculate_assignment_control(
    resource: Resource,
    assignment: ResourceAssignment,
    as_of,
) -> ResourceControlResult:
    planned_units = assignment.planned_units
    actual_units = assignment.actual_units
    remaining_units = assignment.normalized_remaining_units()

    planned_cost = (
        assignment.planned_cost
        if assignment.planned_cost is not None
        else calculate_cost(resource, planned_units, as_of)
    )
    actual_cost = (
        assignment.actual_cost
        if assignment.actual_cost is not None
        else calculate_cost(resource, actual_units, as_of)
    )
    remaining_cost = (
        assignment.remaining_cost
        if assignment.remaining_cost is not None
        else calculate_cost(resource, remaining_units, as_of)
    )

    unit_variance = actual_units + remaining_units - planned_units
    cost_variance = actual_cost + remaining_cost - planned_cost
    utilization = (
        ZERO
        if planned_units == ZERO
        else (actual_units / planned_units * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    )

    return ResourceControlResult(
        planned_units=planned_units,
        actual_units=actual_units,
        remaining_units=remaining_units,
        planned_cost=money(planned_cost),
        actual_cost=money(actual_cost),
        remaining_cost=money(remaining_cost),
        unit_variance=unit_variance,
        cost_variance=money(cost_variance),
        utilization_percent=utilization,
    )
