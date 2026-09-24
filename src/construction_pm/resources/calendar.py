from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class ResourceCalendar:
    id: str
    working_weekdays: frozenset[int] = frozenset({0, 1, 2, 3, 4})
    daily_capacity: Decimal = Decimal("8")

    def is_working_day(self, value: date) -> bool:
        return value.weekday() in self.working_weekdays

    def capacity_on(self, value: date) -> Decimal:
        return self.daily_capacity if self.is_working_day(value) else Decimal("0")
