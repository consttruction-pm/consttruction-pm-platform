from datetime import date
from decimal import Decimal

import pytest

from construction_pm.resources.calculator import calculate_assignment_control, calculate_cost
from construction_pm.resources.models import (
    CostBasis,
    Resource,
    ResourceAssignment,
    ResourceRate,
    ResourceType,
)


@pytest.fixture
def labor() -> Resource:
    return Resource(
        id="r1",
        code="LAB-01",
        name="Electrician",
        resource_type=ResourceType.LABOR,
        unit="hour",
        rates=[
            ResourceRate(
                rate=Decimal("25.00"),
                basis=CostBasis.PER_HOUR,
                currency="USD",
                effective_from=date(2026, 1, 1),
                version=1,
            )
        ],
    )


def test_cost_uses_effective_rate(labor: Resource):
    assert calculate_cost(labor, Decimal("8"), date(2026, 9, 24)) == Decimal("200.00")


def test_remaining_units_default_to_plan_minus_actual(labor: Resource):
    assignment = ResourceAssignment(
        activity_id="A-1",
        resource_id="r1",
        planned_units=Decimal("10"),
        actual_units=Decimal("4"),
    )
    result = calculate_assignment_control(labor, assignment, date(2026, 9, 24))
    assert result.remaining_units == Decimal("6")
    assert result.actual_cost == Decimal("100.00")
    assert result.remaining_cost == Decimal("150.00")


def test_explicit_remaining_is_preserved(labor: Resource):
    assignment = ResourceAssignment(
        activity_id="A-1",
        resource_id="r1",
        planned_units=Decimal("10"),
        actual_units=Decimal("4"),
        remaining_units=Decimal("8"),
    )
    result = calculate_assignment_control(labor, assignment, date(2026, 9, 24))
    assert result.remaining_units == Decimal("8")
    assert result.unit_variance == Decimal("2")


def test_no_effective_rate_fails():
    resource = Resource(
        id="r2",
        code="MAT-01",
        name="Brick",
        resource_type=ResourceType.MATERIAL,
        unit="m3",
        rates=[],
    )
    with pytest.raises(ValueError, match="No effective rate"):
        calculate_cost(resource, Decimal("1"), date(2026, 9, 24))
