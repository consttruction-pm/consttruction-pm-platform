from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from .models import ResourcePeriodValue


def build_resource_curve(values: list[ResourcePeriodValue]) -> dict[date, tuple[Decimal, Decimal]]:
    totals = defaultdict(lambda: [Decimal("0"), Decimal("0")])
    for value in values:
        totals[value.period_start][0] += value.units
        totals[value.period_start][1] += value.cost
    return {period: (data[0], data[1]) for period, data in sorted(totals.items())}
