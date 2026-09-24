from datetime import date
from decimal import Decimal

from construction_pm.resources.calendar import ResourceCalendar


def test_resource_calendar_capacity():
    calendar = ResourceCalendar("rc-1", frozenset({0, 1, 2, 3, 4}), Decimal("8"))
    assert calendar.capacity_on(date(2026, 9, 21)) == Decimal("8")
    assert calendar.capacity_on(date(2026, 9, 20)) == Decimal("0")
