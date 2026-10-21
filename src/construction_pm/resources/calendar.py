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
    canonical_snapshot_hash: str | None = None
    capacity_slices: tuple[tuple[date, Decimal], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("resource calendar id must be non-empty")
        if self.calendar_version is not None and (
            not isinstance(self.calendar_version, str) or not self.calendar_version.strip()
        ):
            raise ValueError("resource calendar version must be non-empty when supplied")
        if self.canonical_snapshot_hash is not None and (
            not isinstance(self.canonical_snapshot_hash, str)
            or len(self.canonical_snapshot_hash) != 64
            or any(c not in "0123456789abcdef" for c in self.canonical_snapshot_hash)
        ):
            raise ValueError("canonical snapshot hash must be a lowercase SHA-256 hex digest")
        if not isinstance(self.capacity_slices, tuple):
            raise ValueError("capacity_slices must be a tuple")
        seen: set[date] = set()
        normalized: list[tuple[date, Decimal]] = []
        for item in self.capacity_slices:
            if not isinstance(item, tuple) or len(item) != 2:
                raise ValueError("each capacity slice must be (date, Decimal)")
            period, units = item
            if not isinstance(period, date):
                raise ValueError("capacity slice period must be a date")
            if period in seen:
                raise ValueError("duplicate capacity slice period")
            if not isinstance(units, Decimal) or not units.is_finite() or units < 0:
                raise ValueError("capacity slice units must be a finite non-negative Decimal")
            seen.add(period)
            normalized.append((period, units))
        object.__setattr__(self, "capacity_slices", tuple(sorted(normalized, key=lambda x: x[0])))

    def is_working_day(self, value: date) -> bool:
        return value.weekday() in self.working_weekdays

    def capacity_on(self, value: date) -> Decimal:
        if self.capacity_slices:
            for period, units in self.capacity_slices:
                if period == value:
                    return units
            raise ValueError("RESOURCE_CALENDAR_CAPACITY_PERIOD_NOT_RESOLVED")
        return self.daily_capacity if self.is_working_day(value) else Decimal("0")
