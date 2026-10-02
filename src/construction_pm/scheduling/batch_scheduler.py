from __future__ import annotations

"""Authoritative date-based multi-project scheduling orchestration."""

from dataclasses import dataclass
from typing import Mapping

from .authoritative_schedule import AuthoritativeScheduleInput, AuthoritativeScheduleMode
from .calendar_context import CalendarResolverRegistry
from .calendar_resolution import (
    resolve_authoritative_activity_calendars,
    resolve_relationship_lag_resolvers,
)
from .project_relationships import resolve_project_relationships
from .schedule import ScheduleResult, schedule
from .schedule_batch import AuthoritativeScheduleBatch


class MultiProjectSchedulingError(ValueError):
    """Raised when a batch capability cannot be executed safely."""


@dataclass(frozen=True)
class ScheduleBatchResult:
    """Deterministic per-project results from one authoritative batch."""

    results: Mapping[str, ScheduleResult]


def execute_authoritative_schedule_batch(
    batch: AuthoritativeScheduleBatch,
    calendar_registry: CalendarResolverRegistry,
) -> ScheduleBatchResult:
    """Execute the supported date-based portion of an authoritative batch.

    The batch owns cross-project float boundaries and project priorities.
    Existing CPM remains the only calculation engine. Capabilities that require
    a shared cross-project graph or authoritative resource-demand source fail
    explicitly instead of silently degrading to single-project behavior.
    """
    if not isinstance(batch, AuthoritativeScheduleBatch):
        raise MultiProjectSchedulingError("INVALID_SCHEDULE_BATCH")

    results: dict[str, ScheduleResult] = {}
    activity_project_ids = {
        activity.id: snapshot.project_id
        for snapshot in batch.snapshots
        for activity in snapshot.activities
    }

    for snapshot in batch.snapshots:
        if snapshot.mode is not AuthoritativeScheduleMode.DATE_BASED:
            raise MultiProjectSchedulingError("MULTI_PROJECT_TIME_AWARE_UNSUPPORTED")

        options = snapshot.schedule_options
        if options.include_external_res_ass:
            raise MultiProjectSchedulingError("EXTERNAL_RESOURCE_ASSIGNMENTS_REQUIRE_BATCH_RESOURCE_SOURCE")
        if any(
            (
                options.level_all_resources,
                options.level_within_float,
                options.min_float_to_preserve != 0,
                options.over_allocation_percentage != 0,
                options.resource_list is not None,
                options.priority_list is not None,
                options.preserve_scheduled_early_and_late_dates,
            )
        ):
            raise MultiProjectSchedulingError("RESOURCE_LEVELING_REQUIRES_BATCH_LEVELING_EXECUTOR")

        resolved_relationships = resolve_project_relationships(
            snapshot.relationships,
            activity_project_ids=activity_project_ids,
            scheduled_project_id=snapshot.project_id,
            ignore_other_project_relationships=options.ignore_other_project_relationships,
        )
        if not options.ignore_other_project_relationships:
            external = tuple(
                relationship
                for relationship in resolved_relationships
                if activity_project_ids[relationship.predecessor_id]
                != activity_project_ids[relationship.successor_id]
            )
            if external:
                raise MultiProjectSchedulingError(
                    "CROSS_PROJECT_RELATIONSHIPS_REQUIRE_SHARED_BATCH_GRAPH"
                )

        calendars = resolve_authoritative_activity_calendars(snapshot, calendar_registry)
        lag_resolvers = resolve_relationship_lag_resolvers(snapshot, calendar_registry)
        result = schedule(
            activities=snapshot.activities,
            relationships=resolved_relationships,
            project_start=snapshot.project_start,
            resolver=calendars.project,
            project_finish=snapshot.project_finish,
            constraints=snapshot.constraints,
            options=options,
            relationship_lag_resolvers=lag_resolvers,
            batch_scheduled_finish=batch.float_boundary.latest_finish,
            activity_resolvers=calendars.activities,
        )
        results[snapshot.project_id] = result

    return ScheduleBatchResult(results=results)
