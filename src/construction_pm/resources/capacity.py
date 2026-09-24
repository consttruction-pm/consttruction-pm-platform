from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from .calendar import ResourceCalendar


def capacity_between(calendar: ResourceCalendar, start: date, finish: date) -> Decimal:
    if finish < start:
        raise ValueError("finish must not be before start")
    total = Decimal("0")
    current = start
    while current <= finish:
        total += calendar.capacity_on(current)
        current += timedelta(days=1)
    return total


def max_units_for_period(calendar: ResourceCalendar, start: date, finish: date, utilization: Decimal = Decimal("1")) -> Decimal:
    if utilization < Decimal("0") or utilization > Decimal("1"):
        raise ValueError("utilization must be between 0 and 1")
    return capacity_between(calendar, start, finish) * utilization
