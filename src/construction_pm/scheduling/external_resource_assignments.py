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
    calculations. This boundary filters the authoritative assignment source.

    ResourceDemand currently identifies resources by bare resource_id. Until
    project identity is carried through the full leveling pipeline, selected
    assignments with the same resource_id from different projects are rejected
    rather than silently conflated or resolved using another project's calendar.
    """
    if not isinstance(scheduled_project_id, str) or not scheduled_project_id.strip():
        raise ResourceLevelingError("INVALID_SCHEDULED_PROJECT_ID")
    if not isinstance(include_external_res_ass, bool):
        raise ResourceLevelingError("INVALID_INCLUDE_EXTERNAL_RES_ASS")
    # Materialize once because callers may supply a generator. If there are no
    # assignments, the external-resource options are not evaluated: an empty
    # assignment set cannot affect the schedule and the P6 default sentinel
    # (priority limit 0) must not turn a no-op into a runtime failure.
    assignment_list = tuple(assignments)
    if not assignment_list:
        return ()

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

    selected_assignments: list[ExternalResourceAssignment] = []
    for assignment in assignment_list:
        if not isinstance(assignment, ExternalResourceAssignment):
            raise ResourceLevelingError("INVALID_EXTERNAL_RESOURCE_ASSIGNMENT")
        if assignment.project_id != scheduled_project_id:
            if not include_external_res_ass:
                continue
            if assignment.project_id not in priorities:
                raise ResourceLevelingError("MISSING_PROJECT_LEVELING_PRIORITY")
            if priorities[assignment.project_id] > external_project_priority_limit:
                continue
        selected_assignments.append(assignment)

    project_by_resource: dict[str, str] = {}
    for assignment in selected_assignments:
        previous_project = project_by_resource.get(assignment.resource_id)
        if previous_project is not None and previous_project != assignment.project_id:
            raise ResourceLevelingError(
                f"CROSS_PROJECT_RESOURCE_ID_COLLISION:{assignment.resource_id}"
            )
        project_by_resource[assignment.resource_id] = assignment.project_id

    return tuple(assignment.to_demand() for assignment in selected_assignments)


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
