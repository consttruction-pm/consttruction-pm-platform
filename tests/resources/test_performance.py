from datetime import date
from decimal import Decimal

from construction_pm.resources.models import CostBasis, Resource, ResourceAssignment, ResourceRate, ResourceType
from construction_pm.resources.performance import build_resource_performance_bridge


def test_resource_performance_bridge():
    resource = Resource(
        "r1", "LAB-01", "Worker", ResourceType.LABOR, "hour",
        [ResourceRate(Decimal("10"), CostBasis.PER_UNIT, effective_from=date(2026, 1, 1))]
    )
    result = build_resource_performance_bridge(
        {"r1": resource},
        [ResourceAssignment("A-1", "r1", Decimal("10"), Decimal("4"))],
        date(2026, 9, 24),
    )
    assert result.at_completion_cost == Decimal("100.00")
    assert result.cost_variance_at_completion == Decimal("0.00")
