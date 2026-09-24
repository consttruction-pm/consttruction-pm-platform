from datetime import date
from decimal import Decimal
from construction_pm.resources.histogram import build_resource_histogram
from construction_pm.resources.models import ResourcePeriodValue

def test_histogram_groups_by_resource_and_day():
    values = [
        ResourcePeriodValue("r1", date(2026, 9, 21), Decimal("3"), Decimal("30")),
        ResourcePeriodValue("r1", date(2026, 9, 21), Decimal("2"), Decimal("20")),
        ResourcePeriodValue("r2", date(2026, 9, 21), Decimal("4"), Decimal("40")),
    ]
    result = build_resource_histogram(values)
    assert result["r1"][date(2026, 9, 21)] == Decimal("5")
    assert result["r2"][date(2026, 9, 21)] == Decimal("4")
