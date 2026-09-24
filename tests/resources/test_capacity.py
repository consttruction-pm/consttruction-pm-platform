from datetime import date
from decimal import Decimal

import pytest

from construction_pm.resources.calendar import ResourceCalendar
from construction_pm.resources.capacity import capacity_between, max_units_for_period


def test_capacity_excludes_nonworking_days():
    calendar = ResourceCalendar("rc", frozenset({0, 1, 2, 3, 4}), Decimal("8"))
    assert capacity_between(calendar, date(2026, 9, 18), date(2026, 9, 20)) == Decimal("8")


def test_capacity_utilization():
    calendar = ResourceCalendar("rc", frozenset({0, 1, 2, 3, 4}), Decimal("8"))
    assert max_units_for_period(calendar, date(2026, 9, 21), date(2026, 9, 25), Decimal("0.5")) == Decimal("20")


def test_invalid_utilization():
    calendar = ResourceCalendar("rc")
    with pytest.raises(ValueError):
        max_units_for_period(calendar, date(2026, 9, 21), date(2026, 9, 21), Decimal("1.1"))
