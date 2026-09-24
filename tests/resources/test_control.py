from datetime import date
from decimal import Decimal

from construction_pm.resources.control import aggregate_assignments
from construction_pm.resources.models import CostBasis, Resource, ResourceAssignment, ResourceRate, ResourceType


def test_portfolio_control_aggregates_assignments():
    resource = Resource(
        "r1", "LAB-01", "Worker", ResourceType.LABOR, "hour",
        [ResourceRate(Decimal("10"), CostBasis.PER_UNIT, effective_from=date(2026, 1, 1))]
    )
    result = aggregate_assignments(
        {"r1": resource},
        [
            ResourceAssignment("A-1", "r1", Decimal("10"), Decimal("2")),
            ResourceAssignment("A-2", "r1", Decimal("5"), Decimal("1")),
        ],
        date(2026, 9, 24),
    )
    assert result.planned_units == Decimal("15")
    assert result.actual_units == Decimal("3")
    assert result.remaining_units == Decimal("12")
    assert result.planned_cost == Decimal("150.00")
    assert result.actual_cost == Decimal("30.00")
