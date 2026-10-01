from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Iterable, Mapping

if TYPE_CHECKING:
    from .schedule_batch import AuthoritativeScheduleBatch
    from .schedule_options import ScheduleOptions

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
    project_leveling_priorities: Mapping[str, int] | None = None,
    external_project_priority_limit: int = 100,
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
    if isinstance(external_project_priority_limit, bool) or not isinstance(external_project_priority_limit, int):
        raise ResourceLevelingError("INVALID_EXTERNAL_PROJECT_PRIORITY_LIMIT")
    if not 1 <= external_project_priority_limit <= 100:
        raise ResourceLevelingError("INVALID_EXTERNAL_PROJECT_PRIORITY_LIMIT")
    priorities = project_leveling_priorities or {}
    for project_id, priority in priorities.items():
        if not isinstance(project_id, str) or not project_id.strip():
            raise ResourceLevelingError("INVALID_PROJECT_LEVELING_PRIORITY")
        if isinstance(priority, bool) or not isinstance(priority, int) or not 1 <= priority <= 100:
            raise ResourceLevelingError("INVALID_PROJECT_LEVELING_PRIORITY")

    selected: list[ResourceDemand] = []
    for assignment in assignments:
        if not isinstance(assignment, ExternalResourceAssignment):
            raise ResourceLevelingError("INVALID_EXTERNAL_RESOURCE_ASSIGNMENT")
        if assignment.project_id != scheduled_project_id:
            if not include_external_res_ass:
                continue
            if assignment.project_id not in priorities:
                raise ResourceLevelingError("MISSING_PROJECT_LEVELING_PRIORITY")
            if priorities[assignment.project_id] > external_project_priority_limit:
                continue
        selected.append(assignment.to_demand())
    return tuple(selected)



def select_batch_resource_assignments_for_scheduling(
    batch: "AuthoritativeScheduleBatch",
    assignments: Iterable[ExternalResourceAssignment],
    *,
    scheduled_project_id: str,
    options: "ScheduleOptions",
) -> tuple[ResourceDemand, ...]:
    """Apply authoritative batch priorities and ScheduleOptions to leveling demand.

    This is the scheduler orchestration seam: ScheduleOptions owns the
    include/limit decision, while AuthoritativeScheduleBatch owns the project
    priority values. No caller supplies a second project-priority source.
    """
    from .schedule_options import ScheduleOptions

    if not isinstance(options, ScheduleOptions):
        raise ResourceLevelingError("INVALID_SCHEDULE_OPTIONS")
    return select_resource_assignments_for_scheduling(
        assignments,
        scheduled_project_id=scheduled_project_id,
        include_external_res_ass=options.include_external_res_ass,
        project_leveling_priorities=batch.leveling_priorities(),
        external_project_priority_limit=options.external_project_priority_limit,
    )
