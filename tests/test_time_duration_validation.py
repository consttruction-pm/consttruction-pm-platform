import pytest
from decimal import Decimal

from construction_pm.scheduling.time_duration import DurationUnit, LagQuantity, TimeQuantity


@pytest.mark.parametrize("factory", [TimeQuantity.working_days, TimeQuantity.working_hours])
def test_time_quantity_rejects_non_finite(factory):
    with pytest.raises(ValueError, match="finite"):
        factory(Decimal("NaN"))
    with pytest.raises(ValueError, match="finite"):
        factory(Decimal("Infinity"))


@pytest.mark.parametrize("factory", [LagQuantity.working_days, LagQuantity.working_hours])
def test_lag_quantity_rejects_non_finite(factory):
    with pytest.raises(ValueError, match="finite"):
        factory(Decimal("NaN"))
    with pytest.raises(ValueError, match="finite"):
        factory(Decimal("-Infinity"))


def test_time_quantity_requires_duration_unit():
    with pytest.raises(TypeError):
        TimeQuantity(Decimal("1"), "working-day")


def test_lag_quantity_requires_duration_unit():
    with pytest.raises(TypeError):
        LagQuantity(Decimal("1"), "working-day")


def test_lag_quantity_preserves_negative_finite_value():
    item = LagQuantity(Decimal("-1.5"), DurationUnit.WORKING_DAY)
    assert item.value == Decimal("-1.5")
