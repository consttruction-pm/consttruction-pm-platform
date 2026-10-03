from datetime import date
from decimal import Decimal

import pytest

from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), Decimal("NaN"), Decimal("Infinity")])
def test_working_calendar_add_rejects_non_finite_duration(value):
    resolver = WorkingTimeResolver(WorkingCalendar())
    with pytest.raises(ValueError, match="finite"):
        resolver.add_working_duration(date(2026, 1, 5), value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), Decimal("NaN"), Decimal("Infinity")])
def test_working_calendar_subtract_rejects_non_finite_duration(value):
    resolver = WorkingTimeResolver(WorkingCalendar())
    with pytest.raises(ValueError, match="finite"):
        resolver.subtract_working_duration(date(2026, 1, 6), value)
