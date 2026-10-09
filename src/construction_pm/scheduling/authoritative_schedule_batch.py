from __future__ import annotations

"""Authoritative multi-project scheduling orchestration boundary."""

from dataclasses import dataclass, replace
from typing import Iterable, Mapping

from .activity_calendar_context import ActivityCalendarContext
from .authoritative_schedule import AuthoritativeScheduleInput, AuthoritativeScheduleMode
from .calendar import WorkingTimeResolver
from .calendar_context import CalendarResolverRegistry
from .resource_calendar_context import ResourceCalendarContext, ResourceCalendarContextError
from .external_resource_assignments import (
    ExternalResourceAssignment,
    select_batch_resource_assignments_for_scheduling,
)
from .project_relationships import resolve_project_relationships
from .schedule import ScheduleResult, schedule
from .leveling_boundary import SchedulerLevelingInput
from .leveling_scheduler import schedule_with_resource_leveling
from .resource_leveling import BackwardLevelingActivity, LevelingActivity, ResourceDemand
from .schedule_batch import AuthoritativeScheduleBatch


_BATCH_ROUTING_OPTION_FIELDS = frozenset({
    "ignore_other_project_relationships",
    "include_external_res_ass",
    "external_project_priority_limit",
    "calculate_float_based_on_finish_date",
    "level_all_resources",
    "level_within_float",
    "min_float_to_preserve",
    "over_allocation_percentage",
    "resource_list",
    "priority_list",
})


def _validate_shared_graph_schedule_options(snapshot_list: tuple) -> None:
    """Reject order-dependent options before one global graph uses a single option set.

    Batch-routing and resource-selection fields are resolved per project or by
    explicit guards at this orchestration boundary. All remaining ScheduleOptions
    fields must match because the shared graph is evaluated once.
    """
    if len(snapshot_list) < 2:
        return
    first = snapshot_list[0].schedule_options
    mismatches = sorted(
        name
        for name in first.__dataclass_fields__
        if name not in _BATCH_ROUTING_OPTION_FIELDS
        and any(
            getattr(snapshot.schedule_options, name) != getattr(first, name)
            for snapshot in snapshot_list[1:]
        )
    )
    if mismatches:
        raise UnsupportedMultiProjectSchedulingError(
            "MULTI_PROJECT_SCHEDULE_OPTIONS_MISMATCH:" + ",".join(mismatches)
        )


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
    leveling_input: SchedulerLevelingInput | None = None,
    calendar_registry: CalendarResolverRegistry | None = None,
) -> AuthoritativeScheduleBatchExecution:
    """Execute the safe multi-project P6 scheduling boundary.

    Each project's own activity graph is scheduled by the existing authoritative
    schedule() implementation. Multi-project-only relationship and resource
    options are resolved at this boundary rather than being reimplemented in CPM.

    Cross-project relationships are executed through one shared authoritative
    schedule() graph when the option requires them; ignored external edges are
    intentionally excluded. Activity calendars are resolved once at this
    orchestration boundary when a registry is supplied.
    """
    snapshot_list = tuple(snapshots)
    if not snapshot_list:
        raise ValueError('at least one schedule snapshot is required')
    if not isinstance(resolvers, Mapping):
        raise TypeError('resolvers must be a mapping')

    snapshot_ids = [snapshot.snapshot_id for snapshot in snapshot_list]
    if len(snapshot_ids) != len(set(snapshot_ids)):
        raise UnsupportedMultiProjectSchedulingError("DUPLICATE_SNAPSHOT_ID")

    tenants = {snapshot.tenant_id for snapshot in snapshot_list}
    if len(tenants) != 1:
        raise UnsupportedMultiProjectSchedulingError("MULTI_PROJECT_CROSS_TENANT_NOT_SUPPORTED")

    if any(snapshot.mode is not AuthoritativeScheduleMode.DATE_BASED for snapshot in snapshot_list):
        raise UnsupportedMultiProjectSchedulingError("MULTI_PROJECT_TIME_AWARE_NOT_SUPPORTED")

    float_basis = {
        snapshot.schedule_options.calculate_float_based_on_finish_date
        for snapshot in snapshot_list
    }
    if len(float_basis) > 1:
        raise UnsupportedMultiProjectSchedulingError(
            'mixed calculate_float_based_on_finish_date settings are not supported '
            'within one authoritative scheduling batch'
        )

    batch = AuthoritativeScheduleBatch.from_snapshots(
        snapshot_list,
        calculate_based_on_project_finish=float_basis.pop(),
    )

    all_activity_projects = dict(activity_project_ids or {})
    for snapshot in snapshot_list:
        for activity in snapshot.activities:
            existing = all_activity_projects.get(activity.id)
            if existing is not None and existing != snapshot.project_id:
                raise ValueError(f'activity belongs to multiple projects: {activity.id}')
            all_activity_projects[activity.id] = snapshot.project_id

    external_relationship_list = tuple(external_relationships)
    resource_assignment_list = tuple(resource_assignments)
    activity_calendar_resolvers = None
    if calendar_registry is not None:
        activity_calendar_context = ActivityCalendarContext.from_snapshots(
            snapshot_list, calendar_registry
        )
        activity_calendar_resolvers = activity_calendar_context.as_mapping()
        if leveling_input is not None:
            activity_calendars = {
                resolver.calendar for resolver in activity_calendar_resolvers.values()
            }
            if len(activity_calendars) > 1:
                raise UnsupportedMultiProjectSchedulingError(
                    "MULTI_PROJECT_RESOURCE_LEVELING_ACTIVITY_CALENDARS_NOT_SUPPORTED"
                )
    resource_calendar_resolvers: dict[str, WorkingTimeResolver] | None = None
    if calendar_registry is not None and leveling_input is not None:
        try:
            resource_context = ResourceCalendarContext.from_snapshots(
                snapshot_list, calendar_registry
            )
        except ResourceCalendarContextError as exc:
            raise UnsupportedMultiProjectSchedulingError(
                "RESOURCE_CALENDAR_CONTEXT_INVALID"
            ) from exc

        resolved_by_resource: dict[str, WorkingTimeResolver] = {}
        reference_by_resource: dict[str, object] = {}

        def register_resource_calendar(project_id: str, resource_id: str) -> None:
            try:
                reference = resource_context.reference_for_resource(project_id, resource_id)
                resource_resolver = resource_context.for_resource(project_id, resource_id)
            except ResourceCalendarContextError as exc:
                raise UnsupportedMultiProjectSchedulingError(
                    "RESOURCE_CALENDAR_CONTEXT_UNRESOLVED"
                ) from exc
            previous = reference_by_resource.get(resource_id)
            if previous is not None and previous != reference:
                raise UnsupportedMultiProjectSchedulingError(
                    "RESOURCE_CALENDAR_ASSIGNMENT_MISMATCH:" + resource_id
                )
            reference_by_resource[resource_id] = reference
            resolved_by_resource[resource_id] = resource_resolver

        for snapshot in snapshot_list:
            for assignment in snapshot.resource_calendar_assignments:
                register_resource_calendar(snapshot.project_id, assignment.resource_id)
        for assignment in resource_assignment_list:
            register_resource_calendar(assignment.project_id, assignment.resource_id)

        explicit_resource_ids = {
            assignment.resource_id
            for snapshot in snapshot_list
            for assignment in snapshot.resource_calendar_assignments
        }
        explicit_resource_ids.update(
            assignment.resource_id for assignment in resource_assignment_list
        )
        for activity in (*leveling_input.forward_activities, *leveling_input.backward_activities):
            owning_project = all_activity_projects.get(activity.activity_id)
            for demand in activity.resource_demands:
                # A persisted resource assignment identifies the resource's owner
                # project and remains authoritative even when the demand is consumed
                # by an activity in another project.
                if demand.resource_id in explicit_resource_ids:
                    continue
                if owning_project is not None:
                    register_resource_calendar(owning_project, demand.resource_id)
                elif len(snapshot_list) == 1:
                    register_resource_calendar(snapshot_list[0].project_id, demand.resource_id)
                else:
                    raise UnsupportedMultiProjectSchedulingError(
                        "RESOURCE_CALENDAR_CONTEXT_AMBIGUOUS:" + demand.resource_id
                    )
        resource_calendar_resolvers = resolved_by_resource

    executions: list[AuthoritativeProjectScheduleExecution] = []

    has_leveling_options = any(
        snapshot.schedule_options.level_all_resources
        or snapshot.schedule_options.level_within_float
        or snapshot.schedule_options.resource_list
        or snapshot.schedule_options.priority_list
        or snapshot.schedule_options.min_float_to_preserve
        or snapshot.schedule_options.over_allocation_percentage
        for snapshot in snapshot_list
    )
    if has_leveling_options and len(snapshot_list) > 1 and leveling_input is None:
        raise UnsupportedMultiProjectSchedulingError(
            "MULTI_PROJECT_RESOURCE_LEVELING_INPUT_REQUIRED"
        )

    relationship_settings = {
        snapshot.schedule_options.ignore_other_project_relationships
        for snapshot in snapshot_list
    }
    if len(snapshot_list) > 1 and external_relationship_list and len(relationship_settings) > 1:
        raise UnsupportedMultiProjectSchedulingError(
            "MULTI_PROJECT_RELATIONSHIP_OPTION_MISMATCH"
        )

    include_external_relationships = any(
        not snapshot.schedule_options.ignore_other_project_relationships
        for snapshot in snapshot_list
    )
    shared_relationships = (
        external_relationship_list if include_external_relationships else ()
    )

    if len(snapshot_list) > 1 and (shared_relationships or leveling_input is not None):
        _validate_shared_graph_schedule_options(snapshot_list)
        first_resolver = resolvers.get(snapshot_list[0].project_id)
        if first_resolver is None:
            raise KeyError(
                f"calendar resolver not registered for project: {snapshot_list[0].project_id}"
            )
        if calendar_registry is None and any(
            resolvers.get(snapshot.project_id) is None
            or resolvers[snapshot.project_id].calendar != first_resolver.calendar
            for snapshot in snapshot_list
        ):
            raise UnsupportedMultiProjectSchedulingError(
                "MULTI_PROJECT_CALENDAR_EXECUTION_REQUIRED"
            )

        if any(
            snapshot.schedule_options.calculate_float_based_on_finish_date
            for snapshot in snapshot_list
        ):
            raise UnsupportedMultiProjectSchedulingError(
                "MULTI_PROJECT_LOCAL_FLOAT_WITH_SHARED_BATCH_GRAPH_REQUIRED"
            )

        resolver = first_resolver
        global_activities = tuple(
            activity for snapshot in snapshot_list for activity in snapshot.activities
        )
        global_relationships = tuple(
            relationship
            for snapshot in snapshot_list
            for relationship in snapshot.relationships
        ) + tuple(shared_relationships)
        global_constraints = tuple(
            constraint
            for snapshot in snapshot_list
            for constraint in snapshot.constraints
        )
        batch_finish = max(
            snapshot.project_finish
            for snapshot in snapshot_list
            if snapshot.project_finish is not None
        )
        selected_by_project: dict[str, tuple[ResourceDemand, ...]] = {}
        for snapshot in snapshot_list:
            selected_by_project[snapshot.project_id] = (
                select_batch_resource_assignments_for_scheduling(
                    batch,
                    resource_assignment_list,
                    scheduled_project_id=snapshot.project_id,
                    options=snapshot.schedule_options,
                )
                if snapshot.schedule_options.include_external_res_ass
                else ()
            )

        if leveling_input is not None:
            activity_ids = {activity.id for activity in global_activities}
            forward_ids = {
                activity.activity_id for activity in leveling_input.forward_activities
            }
            backward_ids = {
                activity.activity_id for activity in leveling_input.backward_activities
            }
            if forward_ids != activity_ids or backward_ids != activity_ids:
                raise UnsupportedMultiProjectSchedulingError(
                    "MULTI_PROJECT_LEVELING_ACTIVITY_SET_MISMATCH"
                )
            if any(
                snapshot.schedule_options != snapshot_list[0].schedule_options
                for snapshot in snapshot_list[1:]
            ):
                raise UnsupportedMultiProjectSchedulingError(
                    "MULTI_PROJECT_LEVELING_OPTIONS_MUST_MATCH"
                )

            initial_options = replace(
                snapshot_list[0].schedule_options,
                ignore_other_project_relationships=False,
                include_external_res_ass=False,
                external_project_priority_limit=0,
                calculate_float_based_on_finish_date=False,
                level_all_resources=False,
                level_within_float=False,
                resource_list=None,
                priority_list=None,
                min_float_to_preserve=0,
                over_allocation_percentage=0,
                preserve_scheduled_early_and_late_dates=False,
            )
            initial = schedule(
                global_activities,
                global_relationships,
                min(snapshot.project_start for snapshot in snapshot_list),
                resolver,
                project_finish=batch_finish,
                constraints=global_constraints,
                options=initial_options,
                batch_scheduled_finish=batch_finish,
                activity_resolvers=activity_calendar_resolvers,
            )

            selected_demands = tuple(
                demand
                for demands in selected_by_project.values()
                for demand in demands
            )
            def demands_for(activity_id: str, existing: Iterable[ResourceDemand]) -> tuple[ResourceDemand, ...]:
                merged = tuple(existing) + tuple(
                    demand for demand in selected_demands
                    if demand.activity_id == activity_id
                )
                return tuple(
                    sorted(
                        {
                            (d.resource_id, d.period, d.units, d.activity_id): d
                            for d in merged
                        }.values(),
                        key=lambda d: (d.period, d.resource_id, d.activity_id or ""),
                    )
                )

            rebased_forward = tuple(
                replace(
                    activity,
                    start=initial.activities[activity.activity_id].start,
                    finish=initial.activities[activity.activity_id].finish,
                    total_float=initial.floats[activity.activity_id].total_float,
                    resource_demands=demands_for(
                        activity.activity_id, activity.resource_demands
                    ),
                )
                for activity in sorted(
                    leveling_input.forward_activities,
                    key=lambda item: item.activity_id,
                )
            )
            early = initial.early_activities or initial.activities
            late = initial.late_activities or initial.activities
            rebased_backward = tuple(
                replace(
                    activity,
                    early_start=early[activity.activity_id].start,
                    early_finish=early[activity.activity_id].finish,
                    late_start=late[activity.activity_id].start,
                    late_finish=late[activity.activity_id].finish,
                    resource_demands=demands_for(
                        activity.activity_id, activity.resource_demands
                    ),
                )
                for activity in sorted(
                    leveling_input.backward_activities,
                    key=lambda item: item.activity_id,
                )
            )
            merged_input = SchedulerLevelingInput(
                forward_activities=rebased_forward,
                backward_activities=rebased_backward,
                capacities=leveling_input.capacities,
                options=leveling_input.options,
            )
            final_result, _, _ = schedule_with_resource_leveling(
                global_activities,
                global_relationships,
                min(snapshot.project_start for snapshot in snapshot_list),
                resolver,
                merged_input,
                project_finish=batch_finish,
                constraints=global_constraints,
                options=snapshot_list[0].schedule_options,
                batch_scheduled_finish=batch_finish,
                resource_calendar_resolvers=resource_calendar_resolvers,
            )
            for snapshot in snapshot_list:
                owned_ids = {activity.id for activity in snapshot.activities}
                project_activities = {
                    key: value
                    for key, value in final_result.activities.items()
                    if key in owned_ids
                }
                project_floats = {
                    key: value
                    for key, value in final_result.floats.items()
                    if key in owned_ids
                }
                executions.append(
                    AuthoritativeProjectScheduleExecution(
                        project_id=snapshot.project_id,
                        snapshot_id=snapshot.snapshot_id,
                        result=replace(
                            final_result,
                            activities=project_activities,
                            early_activities={
                                key: value
                                for key, value in (final_result.early_activities or {}).items()
                                if key in owned_ids
                            },
                            late_activities={
                                key: value
                                for key, value in (final_result.late_activities or {}).items()
                                if key in owned_ids
                            },
                            floats=project_floats,
                            project_finish=max(
                                item.finish for item in project_activities.values()
                            ),
                        ),
                        resource_demands=selected_by_project[snapshot.project_id],
                    )
                )
            return AuthoritativeScheduleBatchExecution(
                batch=batch, projects=tuple(executions)
            )

        project_options = replace(
            snapshot_list[0].schedule_options,
            ignore_other_project_relationships=False,
            include_external_res_ass=False,
            external_project_priority_limit=0,
            calculate_float_based_on_finish_date=False,
        )
        global_result = schedule(
            global_activities,
            global_relationships,
            min(snapshot.project_start for snapshot in snapshot_list),
            resolver,
            project_finish=batch_finish,
            constraints=global_constraints,
            options=project_options,
            batch_scheduled_finish=batch_finish,
            activity_resolvers=activity_calendar_resolvers,
        )
        for snapshot in snapshot_list:
            owned_ids = {activity.id for activity in snapshot.activities}
            project_activities = {
                key: value
                for key, value in global_result.activities.items()
                if key in owned_ids
            }
            project_floats = {
                key: value
                for key, value in global_result.floats.items()
                if key in owned_ids
            }
            executions.append(
                AuthoritativeProjectScheduleExecution(
                    project_id=snapshot.project_id,
                    snapshot_id=snapshot.snapshot_id,
                    result=replace(
                        global_result,
                        activities=project_activities,
                        early_activities={
                            key: value
                            for key, value in (global_result.early_activities or {}).items()
                            if key in owned_ids
                        },
                        late_activities={
                            key: value
                            for key, value in (global_result.late_activities or {}).items()
                            if key in owned_ids
                        },
                        floats=project_floats,
                        project_finish=max(
                            item.finish for item in project_activities.values()
                        ),
                    ),
                )
            )
        return AuthoritativeScheduleBatchExecution(
            batch=batch, projects=tuple(executions)
        )

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
                resource_assignment_list,
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
            activity_resolvers=activity_calendar_resolvers,
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