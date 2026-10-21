from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class ResourceCalendar:
    id: str
    working_weekdays: frozenset[int] = frozenset({0, 1, 2, 3, 4})
    daily_capacity: Decimal = Decimal("8")
    # Optional for compatibility with legacy callers; strict P6 resource
    # capacity resolution requires this to match the immutable assignment ref.
    calendar_version: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("resource calendar id must be non-empty")
        if self.calendar_version is not None and (
            not isinstance(self.calendar_version, str) or not self.calendar_version.strip()
        ):
            raise ValueError("resource calendar version must be non-empty when supplied")

    def is_working_day(self, value: date) -> bool:
        return value.weekday() in self.working_weekdays

    def capacity_on(self, value: date) -> Decimal:
        return self.daily_capacity if self.is_working_day(value) else Decimal("0")
