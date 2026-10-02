from __future__ import annotations

"""Shared-Core boundary for safe multi-project P6 batch scheduling orchestration."""

from dataclasses import dataclass, replace
from typing import Iterable, Mapping

from .authoritative_schedule import AuthoritativeScheduleInput, AuthoritativeScheduleMode
from .constraints import ActivityConstraint, ConstraintType
from .external_resource_assignments import (
    ExternalResourceAssignment,
    select_batch_resource_assignments_for_scheduling,
)
from .project_relationships import resolve_project_relationships
from .resource_leveling import ResourceDemand
from .relationships import Relationship
from .schedule import ScheduleResult, schedule
from .schedule_batch import AuthoritativeScheduleBatch
from .schedule_options import ScheduleOptions
from .calendar_context import CalendarResolverRegistry


class BatchScheduleEvaluationError(ValueError):
    """Raised when a multi-project batch cannot be executed safely."""


@dataclass(frozen=True)
class BatchScheduleResult:
    """Deterministic result of authoritative multi-project batch execution."""

    project_results: Mapping[str, ScheduleResult]
    scoped_relationships: Mapping[str, tuple[Relationship, ...]]
    selected_resource_demands: Mapping[str, tuple[ResourceDemand, ...]]
    calculate_based_on_project_finish: bool


def _all_relationships(
    snapshots: tuple[AuthoritativeScheduleInput, ...],
    relationships: Iterable[Relationship] | None,
) -> tuple[Relationship, ...]:
    if relationships is not None:
        return tuple(relationships)
    merged: list[Relationship] = []
    seen: set[tuple[str, str, str, int]] = set()
    for snapshot in snapshots:
        for relationship in snapshot.relationships:
            key = (
                relationship.predecessor_id,
                relationship.successor_id,
                relationship.type.value,
                relationship.lag,
            )
            if key not in seen:
                seen.add(key)
                merged.append(relationship)
    return tuple(merged)


def _activity_project_ids(
    snapshots: tuple[AuthoritativeScheduleInput, ...],
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for snapshot in snapshots:
        for activity in snapshot.activities:
            owner = mapping.get(activity.id)
            if owner is not None and owner != snapshot.project_id:
                raise BatchScheduleEvaluationError(
                    "DUPLICATE_ACTIVITY_ID_ACROSS_PROJECTS"
                )
            mapping[activity.id] = snapshot.project_id
    return mapping


def _validate_batch_inputs(
    batch: AuthoritativeScheduleBatch,
    calculate_based_on_project_finish: bool,
) -> None:
    if not isinstance(calculate_based_on_project_finish, bool):
        raise BatchScheduleEvaluationError(
            "INVALID_CALCULATE_FLOAT_BASED_ON_FINISH_DATE"
        )
    if any(
        snapshot.mode is not AuthoritativeScheduleMode.DATE_BASED
        for snapshot in batch.snapshots
    ):
        raise BatchScheduleEvaluationError("MULTI_PROJECT_TIME_AWARE_NOT_SUPPORTED")
    snapshot_ids = [snapshot.snapshot_id for snapshot in batch.snapshots]
    if len(snapshot_ids) != len(set(snapshot_ids)):
        raise BatchScheduleEvaluationError("DUPLICATE_SNAPSHOT_ID")
    tenants = {snapshot.tenant_id for snapshot in batch.snapshots}
    if len(tenants) != 1:
        raise BatchScheduleEvaluationError("MULTI_PROJECT_CROSS_TENANT_NOT_SUPPORTED")
    for snapshot in batch.snapshots:
        if snapshot.schedule_options.calculate_float_based_on_finish_date != calculate_based_on_project_finish:
            raise BatchScheduleEvaluationError("BATCH_FLOAT_OPTION_MISMATCH")

    relationship_modes = {
        snapshot.schedule_options.ignore_other_project_relationships
        for snapshot in batch.snapshots
    }
    if len(relationship_modes) > 1:
        raise BatchScheduleEvaluationError("BATCH_RELATIONSHIP_OPTION_MISMATCH")


def _project_constraints(
    snapshots: tuple[AuthoritativeScheduleInput, ...],
) -> tuple[ActivityConstraint, ...]:
    """Anchor each project's activities at or after its authoritative start."""
    result: list[ActivityConstraint] = []
    for snapshot in snapshots:
        for activity in snapshot.activities:
            result.append(
                ActivityConstraint(
                    activity.id,
                    ConstraintType.START_NO_EARLIER_THAN,
                    snapshot.project_start,
                )
            )
    return tuple(result)


def _global_relationships(
    relationships: tuple[Relationship, ...],
    activity_projects: Mapping[str, str],
) -> tuple[Relationship, ...]:
    """Return relationships executable by the single shared CPM graph."""
    result: list[Relationship] = []
    for relationship in relationships:
        if (
            relationship.predecessor_id not in activity_projects
            or relationship.successor_id not in activity_projects
        ):
            raise BatchScheduleEvaluationError("RELATIONSHIP_REFERENCES_UNKNOWN_ACTIVITY")
        result.append(relationship)
    return tuple(result)


def execute_authoritative_schedule_batch(
    snapshots: Iterable[AuthoritativeScheduleInput],
    calendar_registry: CalendarResolverRegistry,
    *,
    calculate_based_on_project_finish: bool,
    relationships: Iterable[Relationship] | None = None,
    external_resource_assignments: Iterable[ExternalResourceAssignment] = (),
) -> BatchScheduleResult:
    """Execute the authoritative P6 multi-project DATE_BASED batch.

    Local-only batches retain the existing per-project scheduler path. When
    cross-project relationships are enabled, all selected activities and
    relationships are sent through one existing CPM graph so the relationship
    is executable rather than merely filtered. No second CPM implementation is
    introduced.
    """

    snapshot_tuple = tuple(snapshots)
    batch = AuthoritativeScheduleBatch.from_snapshots(
        snapshot_tuple,
        calculate_based_on_project_finish=calculate_based_on_project_finish,
    )
    _validate_batch_inputs(batch, calculate_based_on_project_finish)

    all_relationships = _all_relationships(batch.snapshots, relationships)
    activity_projects = _activity_project_ids(batch.snapshots)
    assignment_tuple = tuple(external_resource_assignments)
    known_projects = {snapshot.project_id for snapshot in batch.snapshots}
    if any(
        assignment.project_id not in known_projects
        for assignment in assignment_tuple
    ):
        raise BatchScheduleEvaluationError("UNKNOWN_EXTERNAL_ASSIGNMENT_PROJECT")

    project_results: dict[str, ScheduleResult] = {}
    scoped_relationships: dict[str, tuple[Relationship, ...]] = {}
    selected_resource_demands: dict[str, tuple[ResourceDemand, ...]] = {}

    options_by_project = {
        snapshot.project_id: snapshot.schedule_options for snapshot in batch.snapshots
    }
    for snapshot in batch.snapshots:
        options = snapshot.schedule_options
        scoped = resolve_project_relationships(
            all_relationships,
            activity_project_ids=activity_projects,
            scheduled_project_id=snapshot.project_id,
            ignore_other_project_relationships=options.ignore_other_project_relationships,
        )
        scoped_relationships[snapshot.project_id] = scoped

        selected_resource_demands[snapshot.project_id] = tuple(
            select_batch_resource_assignments_for_scheduling(
                batch,
                assignment_tuple,
                scheduled_project_id=snapshot.project_id,
                options=options,
            )
            if options.include_external_res_ass
            else (
                assignment.to_demand()
                for assignment in assignment_tuple
                if assignment.project_id == snapshot.project_id
            )
        )

        if any(
            getattr(options, name)
            for name in (
                "level_all_resources",
                "level_within_float",
                "min_float_to_preserve",
                "over_allocation_percentage",
                "resource_list",
                "priority_list",
            )
        ):
            raise BatchScheduleEvaluationError(
                "MULTI_PROJECT_RESOURCE_LEVELING_EXECUTION_REQUIRED"
            )
        if options.preserve_scheduled_early_and_late_dates:
            raise BatchScheduleEvaluationError(
                "MULTI_PROJECT_SCHEDULE_OPTION_EXECUTION_REQUIRED"
            )

    # These fields have already been consumed by the batch boundary.
    engine_options = replace(
        batch.snapshots[0].schedule_options,
        ignore_other_project_relationships=False,
        include_external_res_ass=False,
        external_project_priority_limit=0,
    )

    has_external_relationship = any(
        activity_projects[relationship.predecessor_id]
        != activity_projects[relationship.successor_id]
        for relationship in all_relationships
    )
    include_external_relationships = not batch.snapshots[0].schedule_options.ignore_other_project_relationships

    if has_external_relationship and include_external_relationships:
        if calculate_based_on_project_finish:
            raise BatchScheduleEvaluationError(
                "MULTI_PROJECT_LOCAL_FLOAT_WITH_CROSS_PROJECT_RELATIONSHIPS_REQUIRED"
            )
        calendars = {snapshot.project_calendar for snapshot in batch.snapshots}
        if len(calendars) != 1:
            raise BatchScheduleEvaluationError(
                "MULTI_PROJECT_CALENDAR_EXECUTION_REQUIRED"
            )
        resolver = calendar_registry.resolve(batch.snapshots[0].project_calendar)
        activities = tuple(
            activity
            for snapshot in batch.snapshots
            for activity in snapshot.activities
        )
        constraints = tuple(
            constraint
            for snapshot in batch.snapshots
            for constraint in snapshot.constraints
        ) + _project_constraints(batch.snapshots)
        global_result = schedule(
            activities=activities,
            relationships=_global_relationships(all_relationships, activity_projects),
            project_start=min(snapshot.project_start for snapshot in batch.snapshots),
            resolver=resolver,
            project_finish=None,
            constraints=constraints,
            options=engine_options,
            batch_scheduled_finish=max(
                snapshot.project_finish
                or snapshot.project_start
                for snapshot in batch.snapshots
            ),
        )
        for snapshot in batch.snapshots:
            owned = {activity.id for activity in snapshot.activities}
            project_results[snapshot.project_id] = replace(
                global_result,
                activities={
                    activity_id: value
                    for activity_id, value in global_result.activities.items()
                    if activity_id in owned
                },
                early_activities={
                    activity_id: value
                    for activity_id, value in (global_result.early_activities or {}).items()
                    if activity_id in owned
                },
                late_activities={
                    activity_id: value
                    for activity_id, value in (global_result.late_activities or {}).items()
                    if activity_id in owned
                },
                floats={
                    activity_id: value
                    for activity_id, value in global_result.floats.items()
                    if activity_id in owned
                },
                project_finish=snapshot.project_finish
                or global_result.project_finish,
            )
    else:
        for snapshot in batch.snapshots:
            resolver = calendar_registry.resolve(snapshot.project_calendar)
            options = options_by_project[snapshot.project_id]
            scoped = scoped_relationships[snapshot.project_id]
            engine_options = replace(
                options,
                ignore_other_project_relationships=False,
                include_external_res_ass=False,
                external_project_priority_limit=0,
            )
            project_results[snapshot.project_id] = schedule(
                activities=snapshot.activities,
                relationships=tuple(scoped),
                project_start=snapshot.project_start,
                resolver=resolver,
                project_finish=snapshot.project_finish,
                constraints=snapshot.constraints,
                options=engine_options,
                batch_scheduled_finish=batch.finish_boundary_for(snapshot.project_id),
            )

    return BatchScheduleResult(
        project_results=project_results,
        scoped_relationships=scoped_relationships,
        selected_resource_demands=selected_resource_demands,
        calculate_based_on_project_finish=calculate_based_on_project_finish,
    )
