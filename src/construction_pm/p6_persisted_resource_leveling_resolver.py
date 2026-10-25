from __future__ import annotations

"""Build an authorized, version-bound resource-leveling input from persisted facts.

The resolver is intended to be injected into the production Schedule Query
composition. It reads only the exact tenant/project/revision selected by the
immutable schedule snapshot, resolves calendar ID+version pairs, and returns
an immutable Shared-Core input whose source and content hashes are checked
before evaluation.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Callable, Protocol

from .application.authorization import AuthorizationContext
from .backend_p0.models import BackendScope
from .calendar_exception_repository import CalendarExceptionRepository
from .calendar_master_repository import CalendarMasterRepository
from .calendar_snapshot_repository import CalendarSnapshotRepository
from .calendar_work_hours_repository import CalendarWorkHourRepository
from .p6_resource_leveling_read_adapter import (
    P6ResourceLevelingReadAdapterError,
    _assignment_from_dto,
    _period_from_dto,
    build_scheduler_leveling_input,
)
from .p6_resource_read_api import P6ResourceReadAPI
from .p6_versioned_resource_calendar_resolver import resolve_p6_resource_calendar
from .schedule_evaluator import resolve_relationship_lag_resolvers
from .schedule_input_snapshot_repository import ScheduleInputSnapshot
from .schedule_snapshot_materializer import materialize_schedule_snapshot
from .scheduling.activity import ActivityLevelingPriority, ActivityType
from .scheduling.resource_dependent import (
    ResourceDependentCalculationError,
    ResourceDependentDriverFact,
    derive_resource_dependent_duration,
)
from .scheduling.calendar import WorkingTimeResolver
from .scheduling.calendar_context import CalendarResolverRegistry
from .scheduling.calculation_context import CalculationContext
from .scheduling.leveling_boundary import SchedulerLevelingInput
from .scheduling.leveling_scheduler import _schedule_options_without_leveling
from .scheduling.resource_leveling import (
    BackwardLevelingActivity,
    LevelingActivity,
    ResourceLevelingOptions,
)
from .scheduling.schedule import schedule


class PersistedResourceLevelingResolverError(ValueError):
    """Persisted resource/calendar facts cannot be bound to this schedule."""


class _ResourceReadAPI(Protocol):
    def list_assignments(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict, ...]: ...

    def list_assignment_periods(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict, ...]: ...


@dataclass(frozen=True)
class _CapturedResourceReadAPI:
    """Keep the exactly-authorized reads stable across adapter composition."""

    scope: BackendScope
    assignments: tuple[dict, ...]
    periods: tuple[dict, ...]

    def _validate(self, scope: BackendScope, auth_context: AuthorizationContext) -> None:
        if scope != self.scope:
            raise PersistedResourceLevelingResolverError("RESOURCE_READ_SCOPE_CHANGED")
        if (
            auth_context.tenant_id != scope.tenant_id
            or auth_context.project_id != scope.project_id
        ):
            raise PersistedResourceLevelingResolverError("RESOURCE_READ_AUTH_SCOPE_MISMATCH")

    def list_assignments(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict, ...]:
        self._validate(scope, auth_context)
        return self.assignments

    def list_assignment_periods(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict, ...]:
        self._validate(scope, auth_context)
        return self.periods


# The canonical activity-leveling priority is deliberately mapped rather than
# inferred from localized labels or activity IDs.
_ACTIVITY_PRIORITY = {
    # The core sorts this numeric value in the configured direction. A lower
    # value therefore represents the lower-priority enum: ascending puts
    # Lowest/Low ahead of Top/High; descending reverses this order.
    ActivityLevelingPriority.LOWEST: 1,
    ActivityLevelingPriority.LOW: 2,
    ActivityLevelingPriority.NORMAL: 3,
    ActivityLevelingPriority.HIGH: 4,
    ActivityLevelingPriority.TOP: 5,
}


def _validate_context(
    snapshot: ScheduleInputSnapshot,
    context: CalculationContext,
    auth_context: AuthorizationContext,
) -> BackendScope:
    scope = snapshot.scope
    if (
        context.input_snapshot_id != snapshot.snapshot_id
        or context.project_id != scope.project_id
        or context.project_version != scope.project_revision
        or (context.tenant_id is not None and context.tenant_id != scope.tenant_id)
    ):
        raise PersistedResourceLevelingResolverError("RESOURCE_INPUT_CALCULATION_SCOPE_MISMATCH")
    if (
        auth_context.tenant_id != scope.tenant_id
        or auth_context.project_id != scope.project_id
    ):
        raise PersistedResourceLevelingResolverError("RESOURCE_INPUT_AUTHORIZATION_SCOPE_MISMATCH")
    return BackendScope(scope.tenant_id, scope.project_id, scope.project_revision)


def _date_range(first: date, last: date) -> tuple[date, ...]:
    if last < first:
        raise PersistedResourceLevelingResolverError("INVALID_RESOURCE_CAPACITY_HORIZON")
    # The exact calendar resolver calculates nonworking days as zero capacity,
    # so every civil date in the movement horizon must be present.
    count = (last - first).days
    return tuple(first + timedelta(days=offset) for offset in range(count + 1))


def _activity_shift_bound(materialized, initial_schedule) -> int:
    source = materialized.schedule_input
    # All-leveling can move activities beyond float; total activity duration and
    # positive relationship lags bound a serialized local-project solution.
    total_duration = 0
    for activity in source.activities:
        values = (
            getattr(activity, "duration", 0),
            getattr(activity, "original_duration", None) or 0,
            getattr(activity, "remaining_duration", None) or 0,
        )
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values):
            raise PersistedResourceLevelingResolverError("UNSUPPORTED_RESOURCE_DURATION_BOUND")
        total_duration += max(values)
    total_lag = 0
    for relationship in source.relationships:
        lag = getattr(relationship, "lag", 0)
        if isinstance(lag, bool) or not isinstance(lag, int):
            raise PersistedResourceLevelingResolverError("UNSUPPORTED_RESOURCE_LAG_BOUND")
        total_lag += max(0, lag)
    float_bound = max(
        (max(0, getattr(value, "total_float", 0)) for value in initial_schedule.floats.values()),
        default=0,
    )
    # Shared Core caps forward resource movement at 10,000 working days. The
    # extra two working days cover the scheduler's event/date boundary mapping.
    return min(10_000, max(1, total_duration + total_lag, float_bound) + 2)


def build_persisted_resource_leveling_input_resolver(
    *,
    resource_read_api: P6ResourceReadAPI,
    calendar_master_repository: CalendarMasterRepository,
    calendar_snapshot_repository: CalendarSnapshotRepository,
    calendar_exception_repository: CalendarExceptionRepository,
    calendar_work_hours_repository: CalendarWorkHourRepository,
) -> Callable[
    [ScheduleInputSnapshot, CalculationContext, CalendarResolverRegistry, AuthorizationContext],
    SchedulerLevelingInput | None,
]:
    """Compose real persisted resource and versioned-calendar repositories.

    Inject the returned callable into build_project_lifecycle_wsgi_app. The
    resolver is invoked only for a snapshot whose date-based options actually
    request resource leveling.
    """

    def resolve(
        snapshot: ScheduleInputSnapshot,
        calculation_context: CalculationContext,
        calendar_registry: CalendarResolverRegistry,
        auth_context: AuthorizationContext,
    ) -> SchedulerLevelingInput:
        scope = _validate_context(snapshot, calculation_context, auth_context)
        materialized = materialize_schedule_snapshot(snapshot, calendar_registry)
        source = materialized.schedule_input
        if source.mode.value != "DATE_BASED":
            raise PersistedResourceLevelingResolverError("RESOURCE_LEVELING_REQUIRES_DATE_BASED_SCHEDULE")
        if not isinstance(source.project_start, date) or isinstance(source.project_start, datetime):
            raise PersistedResourceLevelingResolverError("INVALID_RESOURCE_PROJECT_START")

        project_resolver = materialized.calendar_registry.resolve(source.project_calendar)
        if not isinstance(project_resolver, WorkingTimeResolver):
            raise PersistedResourceLevelingResolverError("DATE_BASED_PROJECT_CALENDAR_REQUIRED")
        relationship_lag_resolvers = resolve_relationship_lag_resolvers(
            source, materialized.calendar_registry
        )
        activity_resolvers = {
            assignment.activity_id: materialized.calendar_registry.resolve(assignment.calendar)
            for assignment in source.activity_calendar_assignments
        }
        if any(not isinstance(value, WorkingTimeResolver) for value in activity_resolvers.values()):
            raise PersistedResourceLevelingResolverError("DATE_BASED_ACTIVITY_CALENDAR_REQUIRED")

        # Get the same Shared-Core CPM intermediate dates/float used to seed
        # leveler candidates; only resource-leveling options are suppressed.
        initial = schedule(
            activities=source.activities,
            relationships=source.relationships,
            project_start=source.project_start,
            resolver=project_resolver,
            project_finish=source.project_finish,
            constraints=source.constraints,
            options=_schedule_options_without_leveling(source.schedule_options),
            calculation_context=calculation_context,
            relationship_lag_resolvers=relationship_lag_resolvers,
            activity_resolvers=activity_resolvers,
        )

        forward: list[LevelingActivity] = []
        backward: list[BackwardLevelingActivity] = []
        source_activities = {activity.id: activity for activity in source.activities}
        for activity_id in sorted(source_activities):
            activity = source_activities[activity_id]
            early = (initial.early_activities or initial.activities).get(activity_id)
            late = (initial.late_activities or initial.activities).get(activity_id)
            floats = initial.floats.get(activity_id)
            if early is None or late is None or floats is None:
                raise PersistedResourceLevelingResolverError(
                    f"CPM_LEVELING_ACTIVITY_MISSING:{activity_id}"
                )
            priority = _ACTIVITY_PRIORITY.get(activity.leveling_priority)
            if priority is None:
                raise PersistedResourceLevelingResolverError(
                    f"UNSUPPORTED_ACTIVITY_LEVELING_PRIORITY:{activity_id}"
                )
            forward.append(LevelingActivity(
                activity_id=activity_id,
                start=early.start,
                finish=early.finish,
                total_float=floats.total_float,
                resource_demands=(),
                activity_priority=priority,
                free_float=floats.free_float,
                late_start=late.start,
                late_finish=late.finish,
            ))
            # Negative-float snapshots can report late dates before early dates.
            # The leveling proposal window is clamped to the computed early dates;
            # the authoritative CPM result and its negative float remain intact.
            late_start = max(late.start, early.start)
            late_finish = max(late.finish, early.finish)
            backward.append(BackwardLevelingActivity(
                activity_id=activity_id,
                early_start=early.start,
                early_finish=early.finish,
                late_start=late_start,
                late_finish=late_finish,
                resource_demands=(),
                activity_priority=priority,
                total_float=floats.total_float,
                free_float=floats.free_float,
            ))

        # Snapshot assignment/period DTOs once through the authorized read API.
        assignments_dto = resource_read_api.list_assignments(scope, auth_context=auth_context)
        periods_dto = resource_read_api.list_assignment_periods(scope, auth_context=auth_context)
        typed_assignments: dict[str, dict] = {}
        for item in assignments_dto:
            assignment = _assignment_from_dto(scope, item)
            assignment_id = assignment.get("assignment_id")
            if not isinstance(assignment_id, str) or not assignment_id.strip():
                raise PersistedResourceLevelingResolverError("INVALID_ASSIGNMENT_ID")
            if assignment_id in typed_assignments:
                raise PersistedResourceLevelingResolverError("DUPLICATE_ASSIGNMENT_ID")
            calendar_id = assignment.get("calendar_id")
            calendar_version = assignment.get("calendar_version")
            if not isinstance(calendar_id, str) or not calendar_id.strip():
                raise PersistedResourceLevelingResolverError("MISSING_RESOURCE_CALENDAR")
            if not isinstance(calendar_version, str) or not calendar_version.strip():
                raise PersistedResourceLevelingResolverError("MISSING_RESOURCE_CALENDAR_VERSION")
            if assignment.get("activity_id") not in source_activities:
                raise PersistedResourceLevelingResolverError(
                    f"RESOURCE_ASSIGNMENT_ACTIVITY_NOT_IN_SNAPSHOT:{assignment.get('activity_id')}"
                )
            typed_assignments[assignment_id] = assignment

        # Resource Dependent duration is derived when the immutable schedule
        # input is composed. Verify the same driving facts are still persisted
        # before allowing this query to replay that derived duration.
        activity_calendar_assignments = {
            item.activity_id: item.calendar for item in source.activity_calendar_assignments
        }
        for activity in source.activities:
            raw_activity_type = getattr(activity.activity_type, "value", activity.activity_type)
            if raw_activity_type != ActivityType.RESOURCE_DEPENDENT.value:
                continue
            if not isinstance(activity.resource_dependent_input_hash, str):
                raise PersistedResourceLevelingResolverError(
                    f"RESOURCE_DEPENDENT_INPUT_HASH_REQUIRED:{activity.id}"
                )
            assignment_rows = tuple(
                value for value in typed_assignments.values()
                if value.get("activity_id") == activity.id
            )
            facts = tuple(
                ResourceDependentDriverFact(
                    assignment_id=str(value.get("assignment_id", "")),
                    activity_id=str(value.get("activity_id", "")),
                    resource_id=str(value.get("resource_id", "")),
                    calendar_id=value.get("calendar_id"),
                    calendar_version=value.get("calendar_version"),
                    unit_of_measure=value.get("unit"),
                    planned_units=value.get("units"),
                    is_driving=value.get("is_driving"),
                    units_per_time=value.get("units_per_time"),
                    units_per_time_period=value.get("units_per_time_period"),
                    hours_per_units_time_period=value.get("hours_per_units_time_period"),
                )
                for value in assignment_rows
            )
            try:
                derivation = derive_resource_dependent_duration(
                    tenant_id=scope.tenant_id,
                    project_id=scope.project_id,
                    project_revision=scope.project_revision,
                    activity_id=activity.id,
                    assignments=facts,
                )
            except ResourceDependentCalculationError as exc:
                raise PersistedResourceLevelingResolverError(
                    f"{exc}:{activity.id}"
                ) from exc
            if (
                derivation.input_hash != activity.resource_dependent_input_hash
                or derivation.duration_working_days != activity.duration
            ):
                raise PersistedResourceLevelingResolverError(
                    f"RESOURCE_DEPENDENT_SOURCE_CHANGED:{activity.id}"
                )
            calendar_ref = activity_calendar_assignments.get(activity.id)
            if (
                calendar_ref is None
                or calendar_ref.calendar_id != derivation.calendar_id
                or calendar_ref.calendar_version != derivation.calendar_version
            ):
                raise PersistedResourceLevelingResolverError(
                    f"RESOURCE_DEPENDENT_CALENDAR_BINDING_MISMATCH:{activity.id}"
                )

        period_dates_by_activity: dict[str, list[date]] = {}
        for item in periods_dto:
            period = _period_from_dto(scope, item)
            assignment_id = period.get("assignment_id")
            assignment = typed_assignments.get(assignment_id)
            if assignment is None:
                raise PersistedResourceLevelingResolverError("RESOURCE_PERIOD_ASSIGNMENT_NOT_FOUND")
            activity_id = period.get("activity_id")
            if activity_id != assignment.get("activity_id") or period.get("resource_id") != assignment.get("resource_id"):
                raise PersistedResourceLevelingResolverError("RESOURCE_PERIOD_ASSIGNMENT_MISMATCH")
            raw_date = period.get("period_start")
            if not isinstance(raw_date, str):
                raise PersistedResourceLevelingResolverError("INVALID_RESOURCE_PERIOD_START")
            try:
                period_date = date.fromisoformat(raw_date)
            except ValueError as exc:
                raise PersistedResourceLevelingResolverError("INVALID_RESOURCE_PERIOD_START") from exc
            period_dates_by_activity.setdefault(str(activity_id), []).append(period_date)

        if typed_assignments and not periods_dto:
            raise PersistedResourceLevelingResolverError("RESOURCE_ASSIGNMENT_PERIODS_REQUIRED")

        cached_api = _CapturedResourceReadAPI(
            scope=scope,
            assignments=tuple(assignments_dto),
            periods=tuple(periods_dto),
        )
        calendars: dict[tuple[str, str], object] = {}
        capacity_periods: tuple[date, ...] = ()
        if typed_assignments:
            shift_bound = _activity_shift_bound(materialized, initial)
            range_starts: list[date] = []
            range_ends: list[date] = []
            for activity_id, demand_periods in period_dates_by_activity.items():
                activity_resolver = activity_resolvers.get(activity_id, project_resolver)
                if not isinstance(activity_resolver, WorkingTimeResolver):
                    raise PersistedResourceLevelingResolverError("INVALID_ACTIVITY_CALENDAR_RESOLVER")
                for period_date in demand_periods:
                    # Compute an exact working-calendar movement envelope first;
                    # then resolve resource capacity for every civil date in it.
                    range_starts.append(activity_resolver.subtract_working_duration(period_date, shift_bound))
                    range_ends.append(activity_resolver.add_working_duration(period_date, shift_bound))
            if not range_starts or not range_ends:
                raise PersistedResourceLevelingResolverError("RESOURCE_ASSIGNMENT_PERIODS_REQUIRED")
            capacity_periods = _date_range(min(range_starts), max(range_ends))
            calendar_pairs = sorted({
                (str(value["calendar_id"]), str(value["calendar_version"]))
                for value in typed_assignments.values()
            })
            for calendar_id, calendar_version in calendar_pairs:
                calendars[(calendar_id, calendar_version)] = resolve_p6_resource_calendar(
                    scope=scope,
                    calendar_id=calendar_id,
                    calendar_version=calendar_version,
                    periods=capacity_periods,
                    calendar_repository=calendar_master_repository,
                    snapshot_repository=calendar_snapshot_repository,
                    exception_repository=calendar_exception_repository,
                    work_hours_repository=calendar_work_hours_repository,
                )

        return build_scheduler_leveling_input(
            read_api=cached_api,  # exactly the already-authorized read captured above
            scope=scope,
            auth_context=auth_context,
            forward_activities=tuple(forward),
            backward_activities=tuple(backward),
            calendars=calendars,  # strict (calendar ID, version) keys only
            periods=capacity_periods,
            options=ResourceLevelingOptions(),
            require_calendar_versions=True,
            source_snapshot_id=snapshot.snapshot_id,
            source_snapshot_hash=snapshot.snapshot_hash,
            source_calculation_identity=calculation_context.calculation_identity,
        )

    return resolve


__all__ = [
    "PersistedResourceLevelingResolverError",
    "build_persisted_resource_leveling_input_resolver",
]
