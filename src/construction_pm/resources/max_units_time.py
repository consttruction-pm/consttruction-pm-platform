"""Typed, effective-dated resource capacity (Max Units/Time).

This module models the resource ceiling. It is deliberately separate from
``P6ResourceAssignment.units_per_time`` and from calendar working capacity:

* ``units_per_time`` on an assignment is *demand* for one activity.
* ``ResourceCalendar.capacity_slices`` is the working-time capacity model used
  by the scheduler.
* ``ResourceMaxUnitsTime`` is the resource's registered ceiling over an
  effective interval, with an explicit unit basis, conversion factor and
  immutable content identity.

No caller may infer a ceiling from assignment demand or a calendar default.
Missing or ambiguous capacity raises instead of returning an assumed value.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum


class ResourceCapacityError(ValueError):
    """Raised when a resource-capacity definition is invalid or unresolvable."""


class ResourceCapacityBasis(str, Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


def _decimal_token(value: Decimal) -> str:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ResourceCapacityError("INVALID_CAPACITY_DECIMAL")
    normalized = value.normalize()
    # Decimal("8.0").normalize() is Decimal("8"); Decimal("0").normalize() is
    # Decimal("0"). Formatting with "f" avoids scientific notation in hashes.
    return format(normalized, "f") if normalized != 0 else "0"


def _identity_payload(
    *,
    resource_id: str,
    max_units: Decimal,
    unit_basis: ResourceCapacityBasis,
    hours_per_time_period: Decimal,
    effective_from: date,
    effective_to: date | None,
    source: str,
) -> str:
    return json.dumps(
        {
            "resource_id": resource_id,
            "max_units": _decimal_token(max_units),
            "unit_basis": unit_basis.value,
            "hours_per_time_period": _decimal_token(hours_per_time_period),
            "effective_from": effective_from.isoformat(),
            "effective_to": None if effective_to is None else effective_to.isoformat(),
            "source": source,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def compute_capacity_identity(
    *,
    resource_id: str,
    max_units: Decimal,
    unit_basis: ResourceCapacityBasis,
    hours_per_time_period: Decimal,
    effective_from: date,
    effective_to: date | None,
    source: str,
) -> str:
    payload = _identity_payload(
        resource_id=resource_id,
        max_units=max_units,
        unit_basis=unit_basis,
        hours_per_time_period=hours_per_time_period,
        effective_from=effective_from,
        effective_to=effective_to,
        source=source,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ResourceMaxUnitsTime:
    """One immutable effective-dated resource ceiling segment.

    ``max_units`` is expressed per ``unit_basis`` (for example ``8`` units per
    ``day``). ``hours_per_time_period`` is the explicit conversion factor for
    that basis (for example ``8`` hours per working day). Conversion to another
    basis is only possible when the caller supplies that basis' hours-per-period;
    the model never assumes 24-hour days or 5-day weeks.
    """

    resource_id: str
    max_units: Decimal
    unit_basis: ResourceCapacityBasis
    hours_per_time_period: Decimal
    effective_from: date
    effective_to: date | None
    source: str
    identity: str

    def __post_init__(self) -> None:
        if not isinstance(self.resource_id, str) or not self.resource_id.strip():
            raise ResourceCapacityError("INVALID_RESOURCE_ID")
        if (
            not isinstance(self.max_units, Decimal)
            or not self.max_units.is_finite()
            or self.max_units <= 0
        ):
            raise ResourceCapacityError("INVALID_MAX_UNITS")
        if not isinstance(self.unit_basis, ResourceCapacityBasis):
            raise ResourceCapacityError("INVALID_CAPACITY_BASIS")
        if (
            not isinstance(self.hours_per_time_period, Decimal)
            or not self.hours_per_time_period.is_finite()
            or self.hours_per_time_period <= 0
        ):
            raise ResourceCapacityError("INVALID_HOURS_PER_TIME_PERIOD")
        if not isinstance(self.effective_from, date):
            raise ResourceCapacityError("INVALID_EFFECTIVE_FROM")
        if self.effective_to is not None:
            if not isinstance(self.effective_to, date):
                raise ResourceCapacityError("INVALID_EFFECTIVE_TO")
            if self.effective_to < self.effective_from:
                raise ResourceCapacityError("INVALID_EFFECTIVE_INTERVAL")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ResourceCapacityError("INVALID_CAPACITY_SOURCE")
        expected = compute_capacity_identity(
            resource_id=self.resource_id,
            max_units=self.max_units,
            unit_basis=self.unit_basis,
            hours_per_time_period=self.hours_per_time_period,
            effective_from=self.effective_from,
            effective_to=self.effective_to,
            source=self.source,
        )
        if self.identity != expected:
            raise ResourceCapacityError("CAPACITY_IDENTITY_MISMATCH")

    @classmethod
    def create(
        cls,
        *,
        resource_id: str,
        max_units: Decimal,
        unit_basis: ResourceCapacityBasis,
        hours_per_time_period: Decimal,
        effective_from: date,
        effective_to: date | None,
        source: str,
    ) -> "ResourceMaxUnitsTime":
        identity = compute_capacity_identity(
            resource_id=resource_id,
            max_units=max_units,
            unit_basis=unit_basis,
            hours_per_time_period=hours_per_time_period,
            effective_from=effective_from,
            effective_to=effective_to,
            source=source,
        )
        return cls(
            resource_id=resource_id,
            max_units=max_units,
            unit_basis=unit_basis,
            hours_per_time_period=hours_per_time_period,
            effective_from=effective_from,
            effective_to=effective_to,
            source=source,
            identity=identity,
        )

    @property
    def units_per_hour(self) -> Decimal:
        return self.max_units / self.hours_per_time_period

    def is_effective_on(self, value: date) -> bool:
        if not isinstance(value, date):
            raise ResourceCapacityError("INVALID_EFFECTIVE_DATE")
        return value >= self.effective_from and (
            self.effective_to is None or value <= self.effective_to
        )

    def convert_to(
        self,
        *,
        basis: ResourceCapacityBasis,
        hours_per_time_period: Decimal,
    ) -> Decimal:
        """Convert the ceiling to another basis using an explicit factor.

        The conversion is ``units/hour x hours-per-target-period``. The caller
        must supply the target period's hours; the model does not assume a
        calendar, a 24-hour day or a five-day week.
        """

        if not isinstance(basis, ResourceCapacityBasis):
            raise ResourceCapacityError("INVALID_CAPACITY_BASIS")
        if (
            not isinstance(hours_per_time_period, Decimal)
            or not hours_per_time_period.is_finite()
            or hours_per_time_period <= 0
        ):
            raise ResourceCapacityError("INVALID_HOURS_PER_TIME_PERIOD")
        return self.units_per_hour * hours_per_time_period


@dataclass(frozen=True)
class ResourceMaxUnitsTimeProfile:
    """Validated, non-overlapping effective-dated ceiling segments."""

    resource_id: str
    segments: tuple[ResourceMaxUnitsTime, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.resource_id, str) or not self.resource_id.strip():
            raise ResourceCapacityError("INVALID_RESOURCE_ID")
        if not isinstance(self.segments, tuple):
            raise ResourceCapacityError("INVALID_CAPACITY_SEGMENTS")
        ordered = tuple(sorted(self.segments, key=lambda item: item.effective_from))
        for segment in ordered:
            if segment.resource_id != self.resource_id:
                raise ResourceCapacityError("CAPACITY_RESOURCE_MISMATCH")
        previous: ResourceMaxUnitsTime | None = None
        for segment in ordered:
            if previous is not None:
                if previous.effective_to is None:
                    raise ResourceCapacityError("CAPACITY_SEGMENTS_OVERLAP")
                if segment.effective_from <= previous.effective_to:
                    raise ResourceCapacityError("CAPACITY_SEGMENTS_OVERLAP")
            previous = segment
        object.__setattr__(self, "segments", ordered)

    def segment_on(self, value: date) -> ResourceMaxUnitsTime:
        if not isinstance(value, date):
            raise ResourceCapacityError("INVALID_EFFECTIVE_DATE")
        matches = tuple(segment for segment in self.segments if segment.is_effective_on(value))
        if not matches:
            raise ResourceCapacityError("CAPACITY_SEGMENT_NOT_EFFECTIVE")
        if len(matches) > 1:
            raise ResourceCapacityError("CAPACITY_SEGMENTS_OVERLAP")
        return matches[0]

    def capacity_on(
        self,
        value: date,
        *,
        basis: ResourceCapacityBasis | None = None,
        hours_per_time_period: Decimal | None = None,
    ) -> Decimal:
        segment = self.segment_on(value)
        if basis is None and hours_per_time_period is None:
            return segment.max_units
        if basis is None or hours_per_time_period is None:
            raise ResourceCapacityError("CAPACITY_CONVERSION_INCOMPLETE")
        return segment.convert_to(
            basis=basis,
            hours_per_time_period=hours_per_time_period,
        )


__all__ = [
    "ResourceCapacityBasis",
    "ResourceCapacityError",
    "ResourceMaxUnitsTime",
    "ResourceMaxUnitsTimeProfile",
    "compute_capacity_identity",
]
