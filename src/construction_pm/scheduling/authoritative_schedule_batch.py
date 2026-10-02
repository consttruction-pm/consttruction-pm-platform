from __future__ import annotations

"""Authoritative multi-project scheduling orchestration boundary."""

from dataclasses import dataclass, replace
from typing import Iterable, Mapping

from .authoritative_schedule import AuthoritativeScheduleInput
from .calendar import WorkingTimeResolver
from .external_resource_assignments import (
    ExternalResourceAssignment,
    select_batch_resource_assignments_for_scheduling,
)
from .project_relationships import resolve_project_relationships
from .schedule import ScheduleResult, schedule
from .schedule_batch import AuthoritativeScheduleBatch


class UnsupportedMultiProjectSchedulingError(ValueError):
    """Raised when a multi-project capability cannot be safely executed."""


@dataclass(frozen=True)
class AuthoritativeProjectScheduleExecution:
    """Immutable result for one project inside an authoritative batch."""

    project_id: str
    snapshot_id: str
    result: ScheduleResult
    resource_demands: tuple = ()


@dataclass(frozen=True)
class AuthoritativeScheduleBatchExecution:
    """Immutable authoritative execution result for a scheduling batch."""

    batch: AuthoritativeScheduleBatch
    projects: tuple[AuthoritativeProjectScheduleExecution, ...]

    def project(self, project_id: str) -> AuthoritativeProjectScheduleExecution:
        for execution in self.projects:
            if execution.project_id == project_id:
                return execution
        raise ValueError(f"unknown schedule batch project: {project_id}")


def execute_authoritative_schedule_batch(
    snapshots: Iterable[AuthoritativeScheduleInput],
    *,
    resolvers: Mapping[str, WorkingTimeResolver],
    external_relationships: Iterable = (),
    activity_project_ids: Mapping[str, str] | None = None,
    resource_assignments: Iterable[ExternalResourceAssignment] = (),
) -> AuthoritativeScheduleBatchExecution:
    """Execute the safe multi-project P6 scheduling boundary.

    Each project's own activity graph is scheduled by the existing authoritative
    schedule() implementation. Multi-project-only relationship and resource
    options are resolved at this boundary rather than being reimplemented in CPM.

    Cross-project graph execution remains explicitly unsupported: when
    ignore_other_project_relationships is false, an external relationship
    touching the scheduled project raises instead of silently dropping the edge.
    When it is true, those external edges are intentionally excluded.
    """
    snapshot_list = tuple(snapshots)
    if not snapshot_list:
        raise ValueError('at least one schedule snapshot is required')
    if not isinstance(resolvers, Mapping):
        raise TypeError('resolvers must be a mapping')

    batch = AuthoritativeScheduleBatch.from_snapshots(
        snapshot_list,
        calculate_based_on_project_finish=all(
            snapshot.schedule_options.calculate_float_based_on_finish_date
            for snapshot in snapshot_list
        ),
    )

    all_activity_projects = dict(activity_project_ids or {})
    for snapshot in snapshot_list:
        for activity in snapshot.activities:
            existing = all_activity_projects.get(activity.id)
            if existing is not None and existing != snapshot.project_id:
                raise ValueError(f'activity belongs to multiple projects: {activity.id}')
            all_activity_projects[activity.id] = snapshot.project_id

    external_relationship_list = tuple(external_relationships)
    executions: list[AuthoritativeProjectScheduleExecution] = []

    for snapshot in snapshot_list:
        resolver = resolvers.get(snapshot.project_id)
        if resolver is None:
            raise KeyError(
                f'calendar resolver not registered for project: {snapshot.project_id}'
            )

        options = snapshot.schedule_options
        scoped_relationships = resolve_project_relationships(
            external_relationship_list,
            activity_project_ids=all_activity_projects,
            scheduled_project_id=snapshot.project_id,
            ignore_other_project_relationships=options.ignore_other_project_relationships,
        )
        if scoped_relationships:
            raise UnsupportedMultiProjectSchedulingError(
                'cross-project relationship execution is not implemented: '
                f'project={snapshot.project_id}'
            )

        resource_demands = ()
        if options.include_external_res_ass:
            resource_demands = select_batch_resource_assignments_for_scheduling(
                batch,
                resource_assignments,
                scheduled_project_id=snapshot.project_id,
                options=options,
            )

        project_options = replace(
            options,
            ignore_other_project_relationships=False,
            include_external_res_ass=False,
            external_project_priority_limit=0,
        )
        batch_finish = batch.finish_boundary_for(snapshot.project_id)
        result = schedule(
            snapshot.activities,
            snapshot.relationships,
            snapshot.project_start,
            resolver,
            project_finish=snapshot.project_finish,
            constraints=snapshot.constraints,
            options=project_options,
            batch_scheduled_finish=batch_finish,
        )
        executions.append(
            AuthoritativeProjectScheduleExecution(
                project_id=snapshot.project_id,
                snapshot_id=snapshot.snapshot_id,
                result=result,
                resource_demands=tuple(resource_demands),
            )
        )

    return AuthoritativeScheduleBatchExecution(batch=batch, projects=tuple(executions))
