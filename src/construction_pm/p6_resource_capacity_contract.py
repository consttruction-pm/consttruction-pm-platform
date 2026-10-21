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
    """Scope-preserving API contract for scheduler ResourceCapacity input.

    Capacity is sourced only from the authoritative ResourceCalendar model.
    AssignmentPeriod/ResourceSpreadBucket values are never interpreted as
    capacity by this contract.
    """

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
    calendars: Mapping[object, ResourceCalendar],
    periods: Sequence[date],
    *,
    require_calendar_versions: bool = False,
) -> tuple[P6ResourceCapacitySlice, ...]:
    """Build authoritative capacity slices from resource calendar capacity.

    A resource's calendar reference is taken from its persisted assignment
    calendar_id. Missing or conflicting calendar references are rejected
    rather than guessed. The resulting slices are deterministic and retain
    Decimal precision and tenant/project/revision scope.
    """

    scope.validate()
    requested_periods = tuple(sorted(set(periods)))
    if any(not isinstance(period, date) for period in requested_periods):
        raise ResourceCapacityContractError("INVALID_PERIOD")

    if not isinstance(require_calendar_versions, bool):
        raise ResourceCapacityContractError("INVALID_REQUIRE_CALENDAR_VERSIONS")
    calendar_by_resource: dict[str, tuple[str, str | None]] = {}
    for assignment in assignments:
        assignment.validate()
        if assignment.scope != scope:
            raise ResourceCapacityContractError("CROSS_SCOPE_CAPACITY")
        if assignment.calendar_id is None:
            raise ResourceCapacityContractError("MISSING_RESOURCE_CALENDAR")
        calendar_version = assignment.calendar_version
        if require_calendar_versions and (calendar_version is None or not calendar_version.strip()):
            raise ResourceCapacityContractError("MISSING_RESOURCE_CALENDAR_VERSION")
        existing = calendar_by_resource.get(assignment.resource_id)
        reference = (assignment.calendar_id, calendar_version)
        if existing is not None and existing != reference:
            raise ResourceCapacityContractError("AMBIGUOUS_RESOURCE_CALENDAR")
        calendar_by_resource[assignment.resource_id] = reference

    result: list[P6ResourceCapacitySlice] = []
    for resource_id, (calendar_id, calendar_version) in sorted(calendar_by_resource.items()):
        calendar = None
        if calendar_version is not None:
            calendar = calendars.get((calendar_id, calendar_version))
        if calendar is None and not require_calendar_versions:
            # Legacy callers remain supported, but strict callers never resolve
            # by calendar ID alone because that could select the wrong version.
            calendar = calendars.get(calendar_id)
        if calendar is None:
            code = "RESOURCE_CALENDAR_VERSION_NOT_FOUND" if require_calendar_versions else "RESOURCE_CALENDAR_NOT_FOUND"
            raise ResourceCapacityContractError(code)
        if calendar.id != calendar_id:
            raise ResourceCapacityContractError("RESOURCE_CALENDAR_IDENTITY_MISMATCH")
        if require_calendar_versions and calendar.calendar_version != calendar_version:
            raise ResourceCapacityContractError("RESOURCE_CALENDAR_OBJECT_VERSION_MISMATCH")
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
