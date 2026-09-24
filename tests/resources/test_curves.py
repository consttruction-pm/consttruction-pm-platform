from datetime import date
from decimal import Decimal
from construction_pm.resources.curves import build_resource_curve, build_cumulative_cost_curve
from construction_pm.resources.models import ResourcePeriodValue

def test_resource_curve_is_time_sorted():
    values = [
        ResourcePeriodValue("r1", date(2026, 9, 22), Decimal("2"), Decimal("20")),
        ResourcePeriodValue("r1", date(2026, 9, 21), Decimal("3"), Decimal("30")),
    ]
    result = build_resource_curve(values)
    assert list(result) == [date(2026, 9, 21), date(2026, 9, 22)]
    assert result[date(2026, 9, 21)] == (Decimal("3"), Decimal("30"))

def test_cumulative_cost_curve():
    values = [
        ResourcePeriodValue("r1", date(2026, 9, 21), Decimal("3"), Decimal("30")),
        ResourcePeriodValue("r1", date(2026, 9, 22), Decimal("2"), Decimal("20")),
    ]
    assert build_cumulative_cost_curve(values)[date(2026, 9, 22)] == Decimal("50")
