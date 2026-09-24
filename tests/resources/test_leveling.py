from datetime import date
from decimal import Decimal

from construction_pm.resources.calendar import ResourceCalendar
from construction_pm.resources.leveling import ResourceLoad, available_capacity, detect_overloads


def test_detect_overload():
    calendar = ResourceCalendar("rc", frozenset({0, 1, 2, 3, 4}), Decimal("8"))
    loads = [ResourceLoad("r1", date(2026, 9, 21), Decimal("10"))]
    result = detect_overloads({"r1": calendar}, loads)
    assert len(result) == 1
    assert result[0].excess_units == Decimal("2")
    assert result[0].utilization_percent == Decimal("125")


def test_no_overload_on_weekend_with_zero_capacity():
    calendar = ResourceCalendar("rc", frozenset({0, 1, 2, 3, 4}), Decimal("8"))
    loads = [ResourceLoad("r1", date(2026, 9, 20), Decimal("0"))]
    assert detect_overloads({"r1": calendar}, loads) == []


def test_available_capacity():
    calendar = ResourceCalendar("rc", frozenset({0, 1, 2, 3, 4}), Decimal("8"))
    assert available_capacity(calendar, date(2026, 9, 21), Decimal("3")) == Decimal("5")
