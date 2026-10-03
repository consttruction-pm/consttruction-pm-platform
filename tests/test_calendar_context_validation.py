from datetime import datetime, timezone
from decimal import Decimal

import pytest

from construction_pm.scheduling.calendar_context import Continuous24HourResolver


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), Decimal("NaN"), Decimal("Infinity")])
def test_continuous_day_duration_rejects_non_finite(value):
    resolver = Continuous24HourResolver()
    with pytest.raises(ValueError, match="finite"):
        resolver.add_working_duration(datetime(2026, 1, 1, tzinfo=timezone.utc), value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), Decimal("NaN"), Decimal("Infinity")])
def test_continuous_day_subtraction_rejects_non_finite(value):
    resolver = Continuous24HourResolver()
    with pytest.raises(ValueError, match="finite"):
        resolver.subtract_working_duration(datetime(2026, 1, 2, tzinfo=timezone.utc), value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), Decimal("NaN"), Decimal("Infinity")])
def test_continuous_hour_duration_rejects_non_finite(value):
    resolver = Continuous24HourResolver()
    with pytest.raises(ValueError, match="finite"):
        resolver.add_working_hours(datetime(2026, 1, 1, tzinfo=timezone.utc), value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), Decimal("NaN"), Decimal("Infinity")])
def test_continuous_hour_subtraction_rejects_non_finite(value):
    resolver = Continuous24HourResolver()
    with pytest.raises(ValueError, match="finite"):
        resolver.subtract_working_hours(datetime(2026, 1, 2, tzinfo=timezone.utc), value)
