from __future__ import annotations

"""Shared-Core boundary for safe multi-project P6 batch scheduling orchestration."""

from dataclasses import dataclass, replace
from typing import Iterable, Mapping

from .authoritative_schedule import (
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
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
    """Deterministic result of the currently supported multi-project boundary."""

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
    tenants = {snapshot.tenant_id for snapshot in batch.snapshots}
    if len(tenants) != 1:
        raise BatchScheduleEvaluationError("MULTI_PROJECT_CROSS_TENANT_NOT_SUPPORTED")
    for snapshot in batch.snapshots:
        if snapshot.schedule_options.calculate_float_based_on_finish_date != calculate_based_on_project_finish:
            raise BatchScheduleEvaluationError(
                "BATCH_FLOAT_OPTION_MISMATCH"
            )


def execute_authoritative_schedule_batch(
    snapshots: Iterable[AuthoritativeScheduleInput],
    calendar_registry: CalendarResolverRegistry,
    *,
    calculate_based_on_project_finish: bool,
    relationships: Iterable[Relationship] | None = None,
    external_resource_assignments: Iterable[ExternalResourceAssignment] = (),
) -> BatchScheduleResult:
    """Execute the supported P6 multi-project scheduling boundary.

    The function deliberately composes existing authoritative Shared-Core
    scheduling, relationship, float-boundary, and external-resource seams.
    Cross-project graph execution and multi-project resource leveling are
    rejected explicitly until their authoritative execution model exists.
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
        assignment.project_id not in known_projects for assignment in assignment_tuple
    ):
        raise BatchScheduleEvaluationError("UNKNOWN_EXTERNAL_ASSIGNMENT_PROJECT")

    project_results: dict[str, ScheduleResult] = {}
    scoped_relationships: dict[str, tuple[Relationship, ...]] = {}
    selected_resource_demands: dict[str, tuple[ResourceDemand, ...]] = {}

    for snapshot in batch.snapshots:
        options: ScheduleOptions = snapshot.schedule_options
        scoped = resolve_project_relationships(
            all_relationships,
            activity_project_ids=activity_projects,
            scheduled_project_id=snapshot.project_id,
            ignore_other_project_relationships=options.ignore_other_project_relationships,
        )
        scoped_relationships[snapshot.project_id] = scoped

        external_edges = tuple(
            relationship
            for relationship in scoped
            if activity_projects[relationship.predecessor_id] != snapshot.project_id
            or activity_projects[relationship.successor_id] != snapshot.project_id
        )
        if external_edges:
            raise BatchScheduleEvaluationError(
                "MULTI_PROJECT_RELATIONSHIP_EXECUTION_REQUIRED"
            )

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

        # These P6 multi-project/resource-selection flags have already been
        # consumed by this orchestrator. Do not pass them back to the
        # single-project CPM engine, which correctly rejects them as
        # unsupported standalone options.
        engine_options = replace(
            options,
            ignore_other_project_relationships=False,
            include_external_res_ass=False,
            external_project_priority_limit=0,
        )

        resolver = calendar_registry.resolve(snapshot.project_calendar)
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
