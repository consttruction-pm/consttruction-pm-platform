from __future__ import annotations
from collections import defaultdict
from datetime import date
from decimal import Decimal
from .models import ResourcePeriodValue

def build_resource_histogram(values: list[ResourcePeriodValue]) -> dict[str, dict[date, Decimal]]:
    result: dict[str, dict[date, Decimal]] = defaultdict(dict)
    totals: dict[tuple[str, date], Decimal] = defaultdict(lambda: Decimal("0"))
    for value in values:
        totals[(value.resource_id, value.period_start)] += value.units
    for (resource_id, period), units in sorted(totals.items(), key=lambda item: (item[0][0], item[0][1])):
        result[resource_id][period] = units
    return dict(result)
