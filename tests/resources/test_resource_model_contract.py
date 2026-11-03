from __future__ import annotations

from datetime import date
from decimal import Decimal

from construction_pm.resources.models import CostBasis, Resource, ResourceRate, ResourceType


def test_resource_normalizes_legacy_rate_lists_to_an_immutable_tuple():
    rate = ResourceRate(rate=Decimal("12.50"), basis=CostBasis.PER_HOUR)
    resource = Resource(
        id="R-1",
        code="LAB-01",
        name="Labor",
        resource_type=ResourceType.LABOR,
        unit="hour",
        rates=[rate],
    )

    assert resource.rates == (rate,)
    assert isinstance(resource.rates, tuple)
    assert resource.rate_on(date.today()) is rate


def test_resource_without_rates_uses_the_same_empty_value_after_round_trip():
    tuple_resource = Resource(
        id="R-2",
        code="MAT-01",
        name="Material",
        resource_type=ResourceType.MATERIAL,
        unit="ton",
        rates=(),
    )
    list_resource = Resource(
        id="R-2",
        code="MAT-01",
        name="Material",
        resource_type=ResourceType.MATERIAL,
        unit="ton",
        rates=[],
    )

    assert tuple_resource == list_resource
    assert tuple_resource.rates == ()
