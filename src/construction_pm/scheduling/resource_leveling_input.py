from __future__ import annotations

"""Canonical, version-bound resource facts embedded in an authoritative schedule input.

This module is a domain contract only. It does not read persistence, resolve
calendars, or calculate scheduling dates.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .resource_leveling import ResourceCapacity


class ResourceLevelingFactsError(ValueError):
    """Raised when immutable resource facts are incomplete or inconsistent."""


@dataclass(frozen=True)
class ResourceAssignmentLevelingRef:
    """Minimum immutable assignment identity needed to interpret time-phased demand."""

    assignment_id: str
    activity_id: str
    resource_id: str
    calendar_id: str
    calendar_version: str
    unit_of_measure: str | None = None
    assigned_units: Decimal | None = None
    remaining_units: Decimal | None = None
    # Nullable for migrated legacy rows; never infer driving status.
    is_driving: bool | None = None
    # Assignment Units/Time is not the same as resource Max Units/Time.
    units_per_time: Decimal | None = None
    units_per_time_period: str | None = None
    hours_per_units_time_period: Decimal | None = None

    def validate(self) -> None:
        if self.is_driving is not None and not isinstance(self.is_driving, bool):
            raise ResourceLevelingFactsError("INVALID_ASSIGNMENT_DRIVING_FLAG")
        rate_fields = (
            self.units_per_time,
            self.units_per_time_period,
            self.hours_per_units_time_period,
        )
        if any(value is not None for value in rate_fields) and not all(
            value is not None for value in rate_fields
        ):
            raise ResourceLevelingFactsError("INCOMPLETE_ASSIGNMENT_UNITS_PER_TIME")
        if self.units_per_time is not None:
            if (
                not isinstance(self.units_per_time, Decimal)
                or not self.units_per_time.is_finite()
                or self.units_per_time <= 0
            ):
                raise ResourceLevelingFactsError("INVALID_ASSIGNMENT_UNITS_PER_TIME")
            if self.units_per_time_period not in {"hour", "day", "week", "month", "year"}:
                raise ResourceLevelingFactsError("INVALID_ASSIGNMENT_UNITS_PER_TIME_PERIOD")
            if (
                not isinstance(self.hours_per_units_time_period, Decimal)
                or not self.hours_per_units_time_period.is_finite()
                or self.hours_per_units_time_period <= 0
            ):
                raise ResourceLevelingFactsError("INVALID_ASSIGNMENT_UNITS_PER_TIME_CONVERSION")
        for value, code in (
            (self.assignment_id, "ASSIGNMENT_ID"),
            (self.activity_id, "ACTIVITY_ID"),
            (self.resource_id, "RESOURCE_ID"),
            (self.calendar_id, "CALENDAR_ID"),
            (self.calendar_version, "CALENDAR_VERSION"),
            (self.unit_of_measure, "UNIT_OF_MEASURE"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ResourceLevelingFactsError(f"INVALID_{code}")
        for value, code in (
            (self.assigned_units, "ASSIGNED_UNITS"),
            (self.remaining_units, "REMAINING_UNITS"),
        ):
            if value is not None and (
                not isinstance(value, Decimal) or not value.is_finite() or value < 0
            ):
                raise ResourceLevelingFactsError(f"INVALID_{code}")


@dataclass(frozen=True)
class ResourceDemandInput:
    """Time-phased units copied from one persisted assignment period."""

    assignment_id: str
    activity_id: str
    resource_id: str
    period: date
    units: Decimal

    def validate(self) -> None:
        for value, code in (
            (self.assignment_id, "ASSIGNMENT_ID"),
            (self.activity_id, "ACTIVITY_ID"),
            (self.resource_id, "RESOURCE_ID"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ResourceLevelingFactsError(f"INVALID_{code}")
        if not isinstance(self.period, date) or isinstance(self.period, datetime):
            raise ResourceLevelingFactsError("INVALID_DEMAND_PERIOD")
        if not isinstance(self.units, Decimal) or not self.units.is_finite() or self.units < 0:
            raise ResourceLevelingFactsError("INVALID_DEMAND_UNITS")


@dataclass(frozen=True)
class ResourceCapacityRate:
    """Effective-dated P6 ResourceRate Max Units/Time in explicit canonical units.

    `hours_per_time_period` is the exact conversion factor selected by the
    source time-period policy (calendar or global). It must not be inferred
    during calculation. Percentage limits require an explicit full-time base
    in the assignment's unit of measure.
    """

    resource_id: str
    effective_from: datetime
    max_units_per_time: Decimal
    time_period_unit: str
    hours_per_time_period: Decimal
    unit_of_measure: str
    time_period_source: str
    capacity_basis: str = "absolute"
    full_time_units_per_time_period: Decimal | None = None
    shift_id: str = "default"
    record_revision: int = 1

    def validate(self) -> None:
        if not isinstance(self.resource_id, str) or not self.resource_id.strip():
            raise ResourceLevelingFactsError("INVALID_RESOURCE_RATE_RESOURCE_ID")
        if (
            not isinstance(self.effective_from, datetime)
            or self.effective_from.tzinfo is None
            or self.effective_from.utcoffset() is None
        ):
            raise ResourceLevelingFactsError("INVALID_RESOURCE_RATE_EFFECTIVE_FROM")
        if (
            not isinstance(self.max_units_per_time, Decimal)
            or not self.max_units_per_time.is_finite()
            or self.max_units_per_time < 0
        ):
            raise ResourceLevelingFactsError("INVALID_RESOURCE_MAX_UNITS_PER_TIME")
        if self.time_period_unit not in {"hour", "day", "week", "month", "year"}:
            raise ResourceLevelingFactsError("INVALID_RESOURCE_RATE_TIME_PERIOD_UNIT")
        if (
            not isinstance(self.hours_per_time_period, Decimal)
            or not self.hours_per_time_period.is_finite()
            or self.hours_per_time_period <= 0
        ):
            raise ResourceLevelingFactsError("INVALID_RESOURCE_RATE_PERIOD_CONVERSION")
        if not isinstance(self.unit_of_measure, str) or not self.unit_of_measure.strip():
            raise ResourceLevelingFactsError("INVALID_RESOURCE_RATE_UNIT")
        if self.time_period_source not in {"calendar", "global"}:
            raise ResourceLevelingFactsError("INVALID_RESOURCE_RATE_PERIOD_SOURCE")
        if self.capacity_basis not in {"absolute", "percentage"}:
            raise ResourceLevelingFactsError("INVALID_RESOURCE_RATE_CAPACITY_BASIS")
        if self.capacity_basis == "percentage":
            if (
                not isinstance(self.full_time_units_per_time_period, Decimal)
                or not self.full_time_units_per_time_period.is_finite()
                or self.full_time_units_per_time_period <= 0
            ):
                raise ResourceLevelingFactsError("RESOURCE_RATE_PERCENTAGE_BASE_REQUIRED")
        elif self.full_time_units_per_time_period is not None:
            raise ResourceLevelingFactsError("UNEXPECTED_RESOURCE_RATE_PERCENTAGE_BASE")
        if not isinstance(self.shift_id, str) or not self.shift_id.strip():
            raise ResourceLevelingFactsError("INVALID_RESOURCE_RATE_SHIFT_ID")
        if (
            isinstance(self.record_revision, bool)
            or not isinstance(self.record_revision, int)
            or self.record_revision < 1
        ):
            raise ResourceLevelingFactsError("INVALID_RESOURCE_RATE_REVISION")

    def canonical_payload(self) -> dict[str, object]:
        return {
            "resource_id": self.resource_id,
            "effective_from": self.effective_from.astimezone(timezone.utc).isoformat(),
            "max_units_per_time": str(self.max_units_per_time),
            "time_period_unit": self.time_period_unit,
            "hours_per_time_period": str(self.hours_per_time_period),
            "unit_of_measure": self.unit_of_measure,
            "time_period_source": self.time_period_source,
            "capacity_basis": self.capacity_basis,
            "full_time_units_per_time_period": (
                None
                if self.full_time_units_per_time_period is None
                else str(self.full_time_units_per_time_period)
            ),
            "shift_id": self.shift_id,
            "record_revision": self.record_revision,
        }

    @property
    def profile_hash(self) -> str:
        payload = json.dumps(
            self.canonical_payload(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def capacity_for_work_hours(self, available_work_hours: Decimal) -> Decimal:
        if (
            not isinstance(available_work_hours, Decimal)
            or not available_work_hours.is_finite()
            or available_work_hours < 0
        ):
            raise ResourceLevelingFactsError("INVALID_RESOURCE_CALENDAR_WORK_HOURS")
        if self.capacity_basis == "absolute":
            return self.max_units_per_time * available_work_hours / self.hours_per_time_period
        assert self.full_time_units_per_time_period is not None
        return (
            self.max_units_per_time
            / Decimal("100")
            * self.full_time_units_per_time_period
            * available_work_hours
            / self.hours_per_time_period
        )


@dataclass(frozen=True)
class ResourceLevelingFacts:
    """Hash-bound raw demand and versioned capacity inputs for one schedule snapshot.

    `capacity_horizon_start/end` describe the finite capacity range committed
    to this snapshot. Evaluation may not extend it by querying mutable calendar
    repositories; missing capacity remains a validation failure.
    """

    assignments: tuple[ResourceAssignmentLevelingRef, ...]
    demands: tuple[ResourceDemandInput, ...]
    capacities: tuple[ResourceCapacity, ...]
    resource_capacity_rates: tuple[ResourceCapacityRate, ...]
    capacity_horizon_start: date
    capacity_horizon_end: date
    calculation_timezone: str
    schema_version: int = 2

    def validate(self, *, activity_ids: set[str]) -> None:
        if self.schema_version != 2:
            raise ResourceLevelingFactsError("UNSUPPORTED_RESOURCE_LEVELING_FACTS_VERSION")
        if not isinstance(self.assignments, tuple) or not self.assignments:
            raise ResourceLevelingFactsError("RESOURCE_ASSIGNMENTS_REQUIRED")
        if not isinstance(self.demands, tuple) or not self.demands:
            raise ResourceLevelingFactsError("RESOURCE_DEMAND_PERIODS_REQUIRED")
        if not isinstance(self.capacities, tuple) or not self.capacities:
            raise ResourceLevelingFactsError("RESOURCE_CAPACITY_SLICES_REQUIRED")
        if not isinstance(self.resource_capacity_rates, tuple) or not self.resource_capacity_rates:
            raise ResourceLevelingFactsError("RESOURCE_MAX_UNITS_PER_TIME_REQUIRED")
        if not isinstance(self.calculation_timezone, str) or not self.calculation_timezone.strip():
            raise ResourceLevelingFactsError("RESOURCE_LEVELING_TIMEZONE_REQUIRED")
        try:
            calculation_zone = ZoneInfo(self.calculation_timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ResourceLevelingFactsError("INVALID_RESOURCE_LEVELING_TIMEZONE") from exc
        for value in (self.capacity_horizon_start, self.capacity_horizon_end):
            if not isinstance(value, date) or isinstance(value, datetime):
                raise ResourceLevelingFactsError("INVALID_CAPACITY_HORIZON")
        if self.capacity_horizon_end < self.capacity_horizon_start:
            raise ResourceLevelingFactsError("INVALID_CAPACITY_HORIZON")

        assignment_by_id: dict[str, ResourceAssignmentLevelingRef] = {}
        resource_calendar: dict[str, tuple[str, str]] = {}
        for assignment in self.assignments:
            if not isinstance(assignment, ResourceAssignmentLevelingRef):
                raise ResourceLevelingFactsError("INVALID_RESOURCE_ASSIGNMENT")
            assignment.validate()
            if assignment.assignment_id in assignment_by_id:
                raise ResourceLevelingFactsError("DUPLICATE_RESOURCE_ASSIGNMENT_ID")
            if assignment.activity_id not in activity_ids:
                raise ResourceLevelingFactsError("RESOURCE_ASSIGNMENT_UNKNOWN_ACTIVITY")
            assignment_by_id[assignment.assignment_id] = assignment
            calendar_ref = (assignment.calendar_id, assignment.calendar_version)
            existing = resource_calendar.get(assignment.resource_id)
            if existing is not None and existing != calendar_ref:
                raise ResourceLevelingFactsError("AMBIGUOUS_RESOURCE_CALENDAR")
            resource_calendar[assignment.resource_id] = calendar_ref

        rates_by_resource: dict[str, list[ResourceCapacityRate]] = {}
        rate_keys: set[tuple[str, datetime, str]] = set()
        assignment_units: dict[str, str] = {}
        for assignment in assignment_by_id.values():
            assert assignment.unit_of_measure is not None
            existing_unit = assignment_units.get(assignment.resource_id)
            if existing_unit is not None and existing_unit != assignment.unit_of_measure:
                raise ResourceLevelingFactsError("RESOURCE_ASSIGNMENT_UNIT_MISMATCH")
            assignment_units[assignment.resource_id] = assignment.unit_of_measure
        for rate in self.resource_capacity_rates:
            if not isinstance(rate, ResourceCapacityRate):
                raise ResourceLevelingFactsError("INVALID_RESOURCE_CAPACITY_RATE")
            rate.validate()
            if rate.resource_id not in resource_calendar:
                raise ResourceLevelingFactsError("RESOURCE_RATE_FOR_UNASSIGNED_RESOURCE")
            if rate.unit_of_measure != assignment_units[rate.resource_id]:
                raise ResourceLevelingFactsError("RESOURCE_RATE_UNIT_MISMATCH")
            key = (rate.resource_id, rate.effective_from, rate.shift_id)
            if key in rate_keys:
                raise ResourceLevelingFactsError("DUPLICATE_RESOURCE_RATE")
            rate_keys.add(key)
            local_effective = rate.effective_from.astimezone(calculation_zone)
            if local_effective.time() != time.min:
                raise ResourceLevelingFactsError("RESOURCE_RATE_EFFECTIVE_TIME_NOT_REPRESENTABLE")
            rates_by_resource.setdefault(rate.resource_id, []).append(rate)
        for resource_id in resource_calendar:
            rows = rates_by_resource.get(resource_id, [])
            if not rows:
                raise ResourceLevelingFactsError("RESOURCE_MAX_UNITS_PER_TIME_REQUIRED")
            if len({row.shift_id for row in rows}) != 1 or any(
                row.shift_id != "default" for row in rows
            ):
                # There is no versioned shift definition/working-time resolver
                # in this date-based input schema. A single named shift is still
                # unsupported; it cannot safely inherit the generic calendar.
                raise ResourceLevelingFactsError("RESOURCE_RATE_SHIFT_LEVELING_UNSUPPORTED")
            rows.sort(key=lambda row: row.effective_from)

        demand_keys: set[tuple[str, date]] = set()
        for demand in self.demands:
            if not isinstance(demand, ResourceDemandInput):
                raise ResourceLevelingFactsError("INVALID_RESOURCE_DEMAND")
            demand.validate()
            assignment = assignment_by_id.get(demand.assignment_id)
            if assignment is None:
                raise ResourceLevelingFactsError("RESOURCE_DEMAND_ASSIGNMENT_NOT_FOUND")
            if (demand.activity_id, demand.resource_id) != (
                assignment.activity_id, assignment.resource_id
            ):
                raise ResourceLevelingFactsError("RESOURCE_DEMAND_ASSIGNMENT_MISMATCH")
            key = (demand.assignment_id, demand.period)
            if key in demand_keys:
                raise ResourceLevelingFactsError("DUPLICATE_RESOURCE_DEMAND_PERIOD")
            demand_keys.add(key)
            if not self.capacity_horizon_start <= demand.period <= self.capacity_horizon_end:
                raise ResourceLevelingFactsError("DEMAND_OUTSIDE_CAPACITY_HORIZON")

        capacity_by_key: dict[tuple[str, date], ResourceCapacity] = {}
        calendar_hash_by_resource: dict[str, tuple[str, str, str]] = {}
        for capacity in self.capacities:
            if not isinstance(capacity, ResourceCapacity):
                raise ResourceLevelingFactsError("INVALID_RESOURCE_CAPACITY")
            if not self.capacity_horizon_start <= capacity.period <= self.capacity_horizon_end:
                raise ResourceLevelingFactsError("CAPACITY_OUTSIDE_HORIZON")
            key = (capacity.resource_id, capacity.period)
            if key in capacity_by_key:
                raise ResourceLevelingFactsError("DUPLICATE_RESOURCE_CAPACITY_PERIOD")
            capacity_by_key[key] = capacity
            reference = resource_calendar.get(capacity.resource_id)
            if reference is None:
                raise ResourceLevelingFactsError("CAPACITY_FOR_UNASSIGNED_RESOURCE")
            if (capacity.calendar_id, capacity.calendar_version) != reference:
                raise ResourceLevelingFactsError("RESOURCE_CAPACITY_CALENDAR_MISMATCH")
            if capacity.calendar_snapshot_hash is None:
                raise ResourceLevelingFactsError("RESOURCE_CALENDAR_SNAPSHOT_HASH_REQUIRED")
            if capacity.calendar_work_hours is None:
                raise ResourceLevelingFactsError("RESOURCE_CALENDAR_WORK_HOURS_REQUIRED")
            if capacity.resource_rate_hash is None or capacity.resource_rate_effective_from is None:
                raise ResourceLevelingFactsError("RESOURCE_RATE_IDENTITY_REQUIRED")
            expected_rate = max(
                (
                    row
                    for row in rates_by_resource.get(capacity.resource_id, ())
                    if row.effective_from <= datetime.combine(
                        capacity.period, time.min, tzinfo=calculation_zone
                    )
                ),
                key=lambda row: row.effective_from,
                default=None,
            )
            if expected_rate is None:
                raise ResourceLevelingFactsError("RESOURCE_MAX_UNITS_PER_TIME_NOT_EFFECTIVE")
            if (
                capacity.resource_rate_hash != expected_rate.profile_hash
                or capacity.resource_rate_effective_from != expected_rate.effective_from
            ):
                raise ResourceLevelingFactsError("RESOURCE_RATE_CAPACITY_IDENTITY_MISMATCH")
            expected_capacity = expected_rate.capacity_for_work_hours(
                capacity.calendar_work_hours
            )
            if expected_capacity != capacity.units:
                raise ResourceLevelingFactsError("RESOURCE_CAPACITY_RATE_FORMULA_MISMATCH")
            identity = (
                capacity.calendar_id or "",
                capacity.calendar_version or "",
                capacity.calendar_snapshot_hash,
            )
            old_identity = calendar_hash_by_resource.get(capacity.resource_id)
            if old_identity is not None and old_identity != identity:
                raise ResourceLevelingFactsError("RESOURCE_CALENDAR_HASH_MISMATCH")
            calendar_hash_by_resource[capacity.resource_id] = identity

        horizon_day_count = (self.capacity_horizon_end - self.capacity_horizon_start).days + 1
        # Match the publication composer limit here too: persisted snapshots
        # are revalidated independently and must not request an unbounded loop.
        if horizon_day_count > 36501:
            raise ResourceLevelingFactsError("RESOURCE_LEVELING_CAPACITY_HORIZON_OUT_OF_RANGE")
        for resource_id in resource_calendar:
            if resource_id not in calendar_hash_by_resource:
                raise ResourceLevelingFactsError("RESOURCE_CALENDAR_CAPACITY_REQUIRED")
            first_day = date.fromordinal(self.capacity_horizon_start.toordinal())
            first_boundary = datetime.combine(first_day, time.min, tzinfo=calculation_zone)
            if not any(
                row.effective_from <= first_boundary
                for row in rates_by_resource.get(resource_id, ())
            ):
                raise ResourceLevelingFactsError("RESOURCE_MAX_UNITS_PER_TIME_NOT_EFFECTIVE")
            for offset in range(horizon_day_count):
                period = date.fromordinal(self.capacity_horizon_start.toordinal() + offset)
                if (resource_id, period) not in capacity_by_key:
                    raise ResourceLevelingFactsError("RESOURCE_CAPACITY_PERIOD_MISSING")
        for demand in self.demands:
            if (demand.resource_id, demand.period) not in capacity_by_key:
                raise ResourceLevelingFactsError("RESOURCE_CAPACITY_PERIOD_MISSING")
