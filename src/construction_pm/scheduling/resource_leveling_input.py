from __future__ import annotations

"""Canonical, version-bound resource facts embedded in an authoritative schedule input.

This module is a domain contract only. It does not read persistence, resolve
calendars, or calculate scheduling dates.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

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
    assigned_units: Decimal | None = None
    remaining_units: Decimal | None = None

    def validate(self) -> None:
        for value, code in (
            (self.assignment_id, "ASSIGNMENT_ID"),
            (self.activity_id, "ACTIVITY_ID"),
            (self.resource_id, "RESOURCE_ID"),
            (self.calendar_id, "CALENDAR_ID"),
            (self.calendar_version, "CALENDAR_VERSION"),
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
class ResourceLevelingFacts:
    """Hash-bound raw demand and versioned capacity inputs for one schedule snapshot.

    `capacity_horizon_start/end` describe the finite capacity range committed
    to this snapshot. Evaluation may not extend it by querying mutable calendar
    repositories; missing capacity remains a validation failure.
    """

    assignments: tuple[ResourceAssignmentLevelingRef, ...]
    demands: tuple[ResourceDemandInput, ...]
    capacities: tuple[ResourceCapacity, ...]
    capacity_horizon_start: date
    capacity_horizon_end: date
    schema_version: int = 1

    def validate(self, *, activity_ids: set[str]) -> None:
        if self.schema_version != 1:
            raise ResourceLevelingFactsError("UNSUPPORTED_RESOURCE_LEVELING_FACTS_VERSION")
        if not isinstance(self.assignments, tuple) or not self.assignments:
            raise ResourceLevelingFactsError("RESOURCE_ASSIGNMENTS_REQUIRED")
        if not isinstance(self.demands, tuple) or not self.demands:
            raise ResourceLevelingFactsError("RESOURCE_DEMAND_PERIODS_REQUIRED")
        if not isinstance(self.capacities, tuple) or not self.capacities:
            raise ResourceLevelingFactsError("RESOURCE_CAPACITY_SLICES_REQUIRED")
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
            for offset in range(horizon_day_count):
                period = date.fromordinal(self.capacity_horizon_start.toordinal() + offset)
                if (resource_id, period) not in capacity_by_key:
                    raise ResourceLevelingFactsError("RESOURCE_CAPACITY_PERIOD_MISSING")
        for demand in self.demands:
            if (demand.resource_id, demand.period) not in capacity_by_key:
                raise ResourceLevelingFactsError("RESOURCE_CAPACITY_PERIOD_MISSING")
