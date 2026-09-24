from decimal import Decimal

import pytest

from construction_pm.scheduling.time_duration import DurationUnit, LagQuantity, TimeQuantity


def test_working_day_quantity_is_explicit_and_decimal_safe():
    quantity = TimeQuantity.working_days("2.5")
    assert quantity.value == Decimal("2.5")
    assert quantity.unit is DurationUnit.WORKING_DAY


def test_working_hour_quantity_is_explicit():
    quantity = TimeQuantity.working_hours(7.5)
    assert quantity.value == Decimal("7.5")
    assert quantity.unit is DurationUnit.WORKING_HOUR


def test_duration_quantity_rejects_negative_values():
    with pytest.raises(ValueError):
        TimeQuantity.working_hours(-1)


def test_lag_preserves_negative_lead_without_calendar_conversion():
    lag = LagQuantity.working_hours("-2.5")
    assert lag.value == Decimal("-2.5")
    assert lag.unit is DurationUnit.WORKING_HOUR


def test_lag_zero_is_valid():
    assert LagQuantity.working_days(0).value == Decimal("0")
