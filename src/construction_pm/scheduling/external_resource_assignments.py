from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from .resource_leveling import ResourceDemand, ResourceLevelingError


@dataclass(frozen=True)
class ExternalResourceAssignment:
    """Authoritative resource-assignment slice from a scheduling batch project."""

    project_id: str
    resource_id: str
    period: date
    units: Decimal
    activity_id: str | None = None

    def to_demand(self) -> ResourceDemand:
        return ResourceDemand(
            self.resource_id, self.period, self.units, self.activity_id
        )


def select_resource_assignments_for_scheduling(
    assignments: Iterable[ExternalResourceAssignment],
    *,
    scheduled_project_id: str,
    include_external_res_ass: bool,
) -> tuple[ResourceDemand, ...]:
    """Resolve resource demand for a project scheduling batch.

    P6's IncludeExternalResAss option controls whether assignments from
    projects other than the project being scheduled participate in resource
    calculations. This boundary filters the authoritative assignment source;
    it never invents external demand or changes CPM calculations.
    """
    if not isinstance(scheduled_project_id, str) or not scheduled_project_id.strip():
        raise ResourceLevelingError("INVALID_SCHEDULED_PROJECT_ID")
    if not isinstance(include_external_res_ass, bool):
        raise ResourceLevelingError("INVALID_INCLUDE_EXTERNAL_RES_ASS")

    selected: list[ResourceDemand] = []
    for assignment in assignments:
        if not isinstance(assignment, ExternalResourceAssignment):
            raise ResourceLevelingError("INVALID_EXTERNAL_RESOURCE_ASSIGNMENT")
        if assignment.project_id != scheduled_project_id and not include_external_res_ass:
            continue
        selected.append(assignment.to_demand())
    return tuple(selected)
