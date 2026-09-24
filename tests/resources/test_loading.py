from datetime import date
from decimal import Decimal

from construction_pm.resources.loading import aggregate_loading, spread_units
from construction_pm.resources.models import (
    CostBasis,
    Resource,
    ResourceAssignment,
    ResourceRate,
    ResourceType,
)


def test_spread_units_preserves_total():
    resource = Resource(
        id="r1",
        code="LAB-01",
        name="Worker",
        resource_type=ResourceType.LABOR,
        unit="hour",
        rates=[
            ResourceRate(
                rate=Decimal("10"),
                basis=CostBasis.PER_UNIT,
                effective_from=date(2026, 1, 1),
            )
        ],
    )
    assignment = ResourceAssignment(
        activity_id="A-1",
        resource_id="r1",
        planned_units=Decimal("10"),
    )

    values = spread_units(
        resource, assignment, date(2026, 9, 1), date(2026, 9, 3), date(2026, 9, 24)
    )

    assert [v.units for v in values] == [
        Decimal("3.333333333333333333333333333"),
        Decimal("3.333333333333333333333333333"),
        Decimal("3.333333333333333333333333334"),
    ]
    assert sum(v.units for v in values) == Decimal("10")


def test_aggregate_loading_combines_same_resource_period():
    values = [
        # Deliberately same resource/date: aggregation must be deterministic.
        # Costs are already calculated by the domain layer.
        __import__("construction_pm.resources.models", fromlist=["ResourcePeriodValue"]).ResourcePeriodValue(
            "r1", date(2026, 9, 1), Decimal("2"), Decimal("20")
        ),
        __import__("construction_pm.resources.models", fromlist=["ResourcePeriodValue"]).ResourcePeriodValue(
            "r1", date(2026, 9, 1), Decimal("3"), Decimal("30")
        ),
    ]
    result = aggregate_loading(values)
    assert result[("r1", date(2026, 9, 1))].units == Decimal("5")
    assert result[("r1", date(2026, 9, 1))].cost == Decimal("50")
