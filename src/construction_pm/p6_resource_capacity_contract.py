from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping, Sequence

from .backend_p0.models import BackendScope
from .p6_resource_assignment_repository import P6ResourceAssignment
from .resources.calendar import ResourceCalendar


class ResourceCapacityContractError(ValueError):
    """Raised when an authoritative resource-capacity input cannot be resolved."""


@dataclass(frozen=True)
class P6ResourceCapacitySlice:
    """Scope-preserving API contract for scheduler ResourceCapacity input."""

    scope: BackendScope
    resource_id: str
    period: date
    units: Decimal
    calendar_id: str
    calendar_version: str | None = None

    def validate(self) -> None:
        self.scope.validate()
        if not isinstance(self.resource_id, str) or not self.resource_id.strip():
            raise ResourceCapacityContractError("INVALID_RESOURCE_ID")
        if not isinstance(self.period, date):
            raise ResourceCapacityContractError("INVALID_PERIOD")
        if not isinstance(self.units, Decimal) or not self.units.is_finite() or self.units < 0:
            raise ResourceCapacityContractError("INVALID_CAPACITY_UNITS")
        if not isinstance(self.calendar_id, str) or not self.calendar_id.strip():
            raise ResourceCapacityContractError("INVALID_CALENDAR_ID")
        if self.calendar_version is not None and (
            not isinstance(self.calendar_version, str) or not self.calendar_version.strip()
        ):
            raise ResourceCapacityContractError("INVALID_CALENDAR_VERSION")


def build_resource_capacity_slices(
    scope: BackendScope,
    assignments: Sequence[P6ResourceAssignment],
    calendars: Mapping[str | tuple[str, str], ResourceCalendar],
    periods: Sequence[date],
) -> tuple[P6ResourceCapacitySlice, ...]:
    """Resolve pinned calendars by the exact (calendar_id, calendar_version) key.

    Unversioned legacy assignments continue to use the calendar_id key.
    Version-pinned assignments never fall back to an unversioned calendar.
    """

    scope.validate()
    requested_periods = tuple(sorted(set(periods)))
    if any(not isinstance(period, date) for period in requested_periods):
        raise ResourceCapacityContractError("INVALID_PERIOD")

    calendar_by_resource: dict[str, tuple[str, str | None]] = {}
    for assignment in assignments:
        assignment.validate()
        if assignment.scope != scope:
            raise ResourceCapacityContractError("CROSS_SCOPE_CAPACITY")
        if assignment.calendar_id is None:
            raise ResourceCapacityContractError("MISSING_RESOURCE_CALENDAR")
        reference = (assignment.calendar_id, assignment.calendar_version)
        existing = calendar_by_resource.get(assignment.resource_id)
        if existing is not None and existing != reference:
            raise ResourceCapacityContractError("AMBIGUOUS_RESOURCE_CALENDAR")
        calendar_by_resource[assignment.resource_id] = reference

    result: list[P6ResourceCapacitySlice] = []
    for resource_id, (calendar_id, calendar_version) in sorted(calendar_by_resource.items()):
        if calendar_version is None:
            calendar = calendars.get(calendar_id)
            if calendar is not None and calendar.calendar_version is not None:
                raise ResourceCapacityContractError("RESOURCE_CALENDAR_VERSION_MISMATCH")
        else:
            calendar = calendars.get((calendar_id, calendar_version))
            if calendar is None:
                raise ResourceCapacityContractError("RESOURCE_CALENDAR_VERSION_NOT_FOUND")
            if calendar.id != calendar_id or calendar.calendar_version != calendar_version:
                raise ResourceCapacityContractError("RESOURCE_CALENDAR_VERSION_MISMATCH")
        if calendar is None:
            raise ResourceCapacityContractError("RESOURCE_CALENDAR_NOT_FOUND")
        for period in requested_periods:
            item = P6ResourceCapacitySlice(
                scope=scope,
                resource_id=resource_id,
                period=period,
                units=calendar.capacity_on(period),
                calendar_id=calendar_id,
                calendar_version=calendar_version,
            )
            item.validate()
            result.append(item)
    return tuple(result)


__all__ = ["P6ResourceCapacitySlice", "ResourceCapacityContractError", "build_resource_capacity_slices"]
