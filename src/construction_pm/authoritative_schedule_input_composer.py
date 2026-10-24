from __future__ import annotations

"""Fresh persisted-record to immutable schedule-input composition boundary.

This module is deliberately an application adapter: all scheduling semantics
remain in the shared scheduling domain/core. Unsupported date/resource/calendar
semantics fail closed instead of being coerced or silently omitted.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
import hashlib
import json
from typing import Protocol

from .activity_master_repository import ActivityMasterRepository
from .backend_p0.models import BackendScope
from .calendar_master_repository import (
    ActivityCalendarAssignmentMaster,
    CalendarMaster,
    CalendarMasterRepository,
    CalendarPersistenceError,
    RelationshipLagCalendarAssignmentMaster,
)
from .calendar_snapshot_repository import CalendarSnapshotRepository
from .calendar_exception_repository import CalendarExceptionRepository
from .calendar_work_hours_repository import CalendarWorkHourRepository
from .p6_versioned_resource_calendar_resolver import resolve_p6_resource_calendar
from .p6_resource_capacity_contract import build_resource_capacity_slices
from .resources.calendar import ResourceCalendar
from .constraint_master_repository import ConstraintMasterRepository
from .relationship_master_repository import RelationshipMasterRepository
from .p6_resource_assignment_repository import (
    P6ResourceAssignment,
    P6ResourceAssignmentPeriodValue,
    P6ResourceAssignmentPeriodRepository,
    P6ResourceAssignmentRepository,
)
from .project_schedule_settings_repository import (
    ProjectScheduleSettings,
    ProjectScheduleSettingsPersistenceError,
    ProjectScheduleSettingsRepository,
)
from .scheduling.activity import Activity
from .scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
    RelationshipLagCalendarAssignment,
    ResourceLevelingDemandSnapshot,
    ResourceLevelingCapacitySnapshot,
    ResourceLevelingInputSnapshot,
)
from .scheduling.calendar_context import CalendarReference
from .scheduling.calendar_system import CalendarSystem
from .scheduling.constraints import ActivityConstraint
from .scheduling.relationships import Relationship
from .scheduling.time_duration import DurationUnit


class ScheduleInputCompositionError(ValueError):
    """Raised when persisted project records cannot safely form a schedule input."""


class ActivityCalendarAssignments(Protocol):
    def list_activities(self, scope: BackendScope) -> tuple[ActivityCalendarAssignmentMaster, ...]: ...
    def list_relationship_lag(self, scope: BackendScope) -> tuple[RelationshipLagCalendarAssignmentMaster, ...]: ...


class AuthoritativeScheduleInputComposer:
    """Build an immutable scheduler input from fresh, scope-bound repository reads."""

    def __init__(
        self,
        *,
        activity_repository: ActivityMasterRepository,
        relationship_repository: RelationshipMasterRepository,
        constraint_repository: ConstraintMasterRepository,
        calendar_repository: CalendarMasterRepository,
        calendar_assignment_repository: ActivityCalendarAssignments,
        calendar_snapshot_repository: CalendarSnapshotRepository,
        resource_assignment_repository: P6ResourceAssignmentRepository,
        resource_period_repository: P6ResourceAssignmentPeriodRepository,
        project_schedule_settings_repository: ProjectScheduleSettingsRepository,
        calendar_exception_repository: CalendarExceptionRepository | None = None,
        calendar_work_hours_repository: CalendarWorkHourRepository | None = None,
    ) -> None:
        self.activity_repository = activity_repository
        self.relationship_repository = relationship_repository
        self.constraint_repository = constraint_repository
        self.calendar_repository = calendar_repository
        self.calendar_assignment_repository = calendar_assignment_repository
        self.calendar_snapshot_repository = calendar_snapshot_repository
        self.resource_assignment_repository = resource_assignment_repository
        self.resource_period_repository = resource_period_repository
        self.project_schedule_settings_repository = project_schedule_settings_repository
        self.calendar_exception_repository = calendar_exception_repository
        self.calendar_work_hours_repository = calendar_work_hours_repository

    @staticmethod
    def _date_value(value: date | datetime | None, *, field_name: str, activity_id: str) -> date | None:
        if value is None:
            return None
        if not isinstance(value, date) or isinstance(value, datetime):
            raise ScheduleInputCompositionError(
                f"DATE_BASED_DATETIME_PRECISION_UNSUPPORTED:{activity_id}:{field_name}"
            )
        return value

    @staticmethod
    def _calendar_reference(calendar: CalendarMaster, snapshot: object) -> CalendarReference:
        if calendar.base_calendar_id is not None or calendar.base_calendar_version is not None:
            raise ScheduleInputCompositionError(
                f"CALENDAR_INHERITANCE_NOT_BOUND_TO_SNAPSHOT:{calendar.calendar_id}@{calendar.calendar_version}"
            )
        snapshot_data = getattr(snapshot, "snapshot", None)
        if not isinstance(snapshot_data, dict):
            raise ScheduleInputCompositionError("CALENDAR_SNAPSHOT_NOT_FOUND_OR_INVALID")
        if getattr(snapshot, "kind", None) != calendar.kind:
            raise ScheduleInputCompositionError("CALENDAR_SNAPSHOT_KIND_MISMATCH")
        raw_system = snapshot_data.get("system")
        if not isinstance(raw_system, str):
            raise ScheduleInputCompositionError("CALENDAR_SYSTEM_MISSING_FROM_SNAPSHOT")
        try:
            system = CalendarSystem(raw_system)
            return CalendarReference(
                calendar_id=calendar.calendar_id,
                calendar_version=calendar.calendar_version,
                kind=calendar.kind,
                system=system,
            )
        except (TypeError, ValueError) as exc:
            raise ScheduleInputCompositionError("INVALID_CALENDAR_REFERENCE") from exc

    def _load_calendar_reference(
        self,
        scope: BackendScope,
        calendar_id: str,
        calendar_version: str,
        *,
        expected_kind: str = "working-day",
    ) -> CalendarReference:
        try:
            calendar = self.calendar_repository.get(scope, calendar_id, calendar_version)
        except CalendarPersistenceError as exc:
            raise ScheduleInputCompositionError(str(exc)) from exc
        if calendar is None:
            raise ScheduleInputCompositionError(
                f"CALENDAR_VERSION_NOT_FOUND:{calendar_id}@{calendar_version}"
            )
        if calendar.scope != scope:
            raise ScheduleInputCompositionError("CALENDAR_SCOPE_MISMATCH")
        if calendar.kind != expected_kind:
            raise ScheduleInputCompositionError(
                f"CALENDAR_KIND_MISMATCH:{calendar_id}@{calendar_version}"
            )
        try:
            snapshot = self.calendar_snapshot_repository.get(calendar)
        except CalendarPersistenceError as exc:
            raise ScheduleInputCompositionError(str(exc)) from exc
        if snapshot is None:
            raise ScheduleInputCompositionError(
                f"CALENDAR_SNAPSHOT_NOT_FOUND:{calendar_id}@{calendar_version}"
            )
        if snapshot.scope != scope or snapshot.calendar_id != calendar.calendar_id or snapshot.calendar_version != calendar.calendar_version:
            raise ScheduleInputCompositionError("CALENDAR_SNAPSHOT_IDENTITY_MISMATCH")
        return self._calendar_reference(calendar, snapshot)

    def _compose_resource_leveling_input(
        self,
        scope: BackendScope,
        project_settings: ProjectScheduleSettings,
        persisted_activities: tuple[object, ...],
        assignments: tuple[P6ResourceAssignment, ...],
        period_values: tuple[P6ResourceAssignmentPeriodValue, ...],
        activity_ids: set[str],
    ) -> ResourceLevelingInputSnapshot:
        """Bind exact resource demand and versioned calendar capacity into the snapshot.

        The forecast window is deliberately finite: project_start through the
        furthest explicitly persisted project finish, activity finish, or
        time-phased resource period. The evaluator will never level outside this
        window; impossible loads fail final allocation validation rather than
        receiving guessed/default capacity.
        """
        if not assignments:
            raise ScheduleInputCompositionError("RESOURCE_LEVELING_ASSIGNMENTS_REQUIRED")
        if not period_values:
            raise ScheduleInputCompositionError("RESOURCE_LEVELING_PERIODS_REQUIRED")
        if (
            self.calendar_exception_repository is None
            or self.calendar_work_hours_repository is None
        ):
            raise ScheduleInputCompositionError("RESOURCE_LEVELING_CALENDAR_REPOSITORIES_REQUIRED")

        assignments_by_id: dict[str, P6ResourceAssignment] = {}
        for assignment in assignments:
            try:
                assignment.validate()
            except (TypeError, ValueError, ArithmeticError) as exc:
                raise ScheduleInputCompositionError("INVALID_RESOURCE_LEVELING_ASSIGNMENT") from exc
            if assignment.scope != scope:
                raise ScheduleInputCompositionError("RESOURCE_LEVELING_ASSIGNMENT_SCOPE_MISMATCH")
            if assignment.assignment_id in assignments_by_id:
                raise ScheduleInputCompositionError("DUPLICATE_RESOURCE_LEVELING_ASSIGNMENT")
            if assignment.activity_id not in activity_ids:
                raise ScheduleInputCompositionError("RESOURCE_LEVELING_ASSIGNMENT_UNKNOWN_ACTIVITY")
            if not assignment.calendar_id or not assignment.calendar_version:
                raise ScheduleInputCompositionError("RESOURCE_LEVELING_ASSIGNMENT_CALENDAR_VERSION_REQUIRED")
            assignments_by_id[assignment.assignment_id] = assignment

        periods_by_assignment: dict[str, list[P6ResourceAssignmentPeriodValue]] = {}
        demand_dates: set[date] = set()
        for period_value in period_values:
            try:
                period_value.validate()
            except (TypeError, ValueError, ArithmeticError) as exc:
                raise ScheduleInputCompositionError("INVALID_RESOURCE_LEVELING_PERIOD") from exc
            if period_value.scope != scope:
                raise ScheduleInputCompositionError("RESOURCE_LEVELING_PERIOD_SCOPE_MISMATCH")
            assignment = assignments_by_id.get(period_value.assignment_id)
            if assignment is None:
                raise ScheduleInputCompositionError("RESOURCE_LEVELING_PERIOD_ASSIGNMENT_NOT_FOUND")
            if (
                period_value.activity_id != assignment.activity_id
                or period_value.resource_id != assignment.resource_id
            ):
                raise ScheduleInputCompositionError("RESOURCE_LEVELING_PERIOD_ASSIGNMENT_MISMATCH")
            if period_value.units < 0:
                raise ScheduleInputCompositionError("NEGATIVE_RESOURCE_LEVELING_DEMAND")
            try:
                period_date = date.fromisoformat(period_value.period_start)
            except ValueError as exc:
                raise ScheduleInputCompositionError("INVALID_RESOURCE_LEVELING_PERIOD_DATE") from exc
            if period_date.isoformat() != period_value.period_start:
                raise ScheduleInputCompositionError("NON_CANONICAL_RESOURCE_LEVELING_PERIOD_DATE")
            demand_dates.add(period_date)
            periods_by_assignment.setdefault(period_value.assignment_id, []).append(period_value)

        # The resource-calendar resolver's full output hash includes the exact
        # calendar master, base chain, canonical calendar snapshot, work-hour
        # declarations and exceptions for every required date.
        schedule_finish_candidates: list[date] = list(demand_dates)
        if project_settings.project_finish is not None:
            schedule_finish_candidates.append(project_settings.project_finish)
        for item in persisted_activities:
            for value in (item.expected_finish, item.planned_finish, item.actual_finish):
                if value is not None:
                    if not isinstance(value, date) or isinstance(value, datetime):
                        raise ScheduleInputCompositionError("RESOURCE_LEVELING_FINISH_DATE_MUST_BE_DATE")
                    schedule_finish_candidates.append(value)
        start_candidates = [project_settings.project_start, *demand_dates]
        for item in persisted_activities:
            if item.actual_start is not None:
                if not isinstance(item.actual_start, date) or isinstance(item.actual_start, datetime):
                    raise ScheduleInputCompositionError("RESOURCE_LEVELING_START_DATE_MUST_BE_DATE")
                start_candidates.append(item.actual_start)
        window_start = min(start_candidates)
        window_end = max(schedule_finish_candidates)
        if window_end < window_start:
            raise ScheduleInputCompositionError("INVALID_RESOURCE_LEVELING_CAPACITY_HORIZON")
        horizon_days = (window_end - window_start).days
        # Prevent accidental unbounded allocation of calendar-capacity rows.
        # The cap is an explicit fail-closed boundary, not a substituted default
        # capacity or a change to any CPM/leveling priority calculation.
        if horizon_days > 10000:
            raise ScheduleInputCompositionError("RESOURCE_LEVELING_CAPACITY_HORIZON_TOO_LARGE")
        capacity_periods = tuple(
            window_start + timedelta(days=offset)
            for offset in range(horizon_days + 1)
        )

        calendars: dict[tuple[str, str], ResourceCalendar] = {}
        calendar_references = sorted({
            (assignment.calendar_id, assignment.calendar_version)
            for assignment in assignments.values()
            if assignment.resource_id in {p.resource_id for p in period_values}
        })
        try:
            for calendar_id, calendar_version in calendar_references:
                assert calendar_id is not None and calendar_version is not None
                calendars[(calendar_id, calendar_version)] = resolve_p6_resource_calendar(
                    scope=scope,
                    calendar_id=calendar_id,
                    calendar_version=calendar_version,
                    periods=capacity_periods,
                    calendar_repository=self.calendar_repository,
                    snapshot_repository=self.calendar_snapshot_repository,
                    exception_repository=self.calendar_exception_repository,
                    work_hours_repository=self.calendar_work_hours_repository,
                )
            capacity_slices = build_resource_capacity_slices(
                scope,
                assignments,
                calendars,
                capacity_periods,
                require_calendar_versions=True,
            )
        except (TypeError, ValueError, ArithmeticError) as exc:
            if isinstance(exc, ScheduleInputCompositionError):
                raise
            raise ScheduleInputCompositionError(
                f"RESOURCE_LEVELING_CAPACITY_RESOLUTION_FAILED:{exc}"
            ) from exc

        demands: list[ResourceLevelingDemandSnapshot] = []
        for period_value in sorted(
            period_values,
            key=lambda item: (item.assignment_id, item.period_start),
        ):
            assignment = assignments_by_id[period_value.assignment_id]
            assert assignment.calendar_id is not None and assignment.calendar_version is not None
            demands.append(ResourceLevelingDemandSnapshot(
                assignment_id=period_value.assignment_id,
                activity_id=period_value.activity_id,
                resource_id=period_value.resource_id,
                period=date.fromisoformat(period_value.period_start),
                units=period_value.units,
                calendar_id=assignment.calendar_id,
                calendar_version=assignment.calendar_version,
            ))

        capacities = tuple(ResourceLevelingCapacitySnapshot(
            resource_id=item.resource_id,
            period=item.period,
            units=item.units,
            calendar_id=item.calendar_id,
            calendar_version=item.calendar_version or "",
            calendar_snapshot_hash=item.calendar_snapshot_hash or "",
        ) for item in capacity_slices)
        source_payload = {
            "scope": {
                "tenant_id": scope.tenant_id,
                "project_id": scope.project_id,
                "project_revision": scope.project_revision,
            },
            "assignments": [{
                "assignment_id": item.assignment_id,
                "activity_id": item.activity_id,
                "resource_id": item.resource_id,
                "calendar_id": item.calendar_id,
                "calendar_version": item.calendar_version,
                "units": None if item.units is None else str(item.units),
                "actual_units": None if item.actual_units is None else str(item.actual_units),
                "remaining_units": None if item.remaining_units is None else str(item.remaining_units),
                "periods": [{
                    "period_start": row.period_start,
                    "units": str(row.units),
                    "cost": str(row.cost),
                } for row in sorted(periods_by_assignment.get(item.assignment_id, ()), key=lambda row: row.period_start)],
            } for item in sorted(assignments, key=lambda item: item.assignment_id)],
            "calendar_hashes": [{
                "calendar_id": calendar_id,
                "calendar_version": calendar_version,
                "snapshot_hash": calendars[(calendar_id, calendar_version)].canonical_snapshot_hash,
            } for calendar_id, calendar_version in calendar_references],
        }
        source_hash = hashlib.sha256(
            json.dumps(source_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return ResourceLevelingInputSnapshot(
            schema_version="resource-leveling-input.v1",
            source_data_hash=source_hash,
            demands=tuple(demands),
            capacities=capacities,
            max_shift_working_days=horizon_days,
        )

    def compose(
        self,
        scope: BackendScope,
        *,
        snapshot_id: str,
    ) -> AuthoritativeScheduleInput:
        scope.validate()
        if not isinstance(snapshot_id, str) or not snapshot_id.strip():
            raise ScheduleInputCompositionError("SNAPSHOT_ID_REQUIRED")
        try:
            # Fresh reads intentionally occur at the application boundary.
            # The core receives only the immutable result below.
            persisted_activities = self.activity_repository.list(scope)
            persisted_relationships = self.relationship_repository.list(scope)
            persisted_constraints = self.constraint_repository.list(scope)
            activity_calendar_assignments = self.calendar_assignment_repository.list_activities(scope)
            relationship_lag_assignments = self.calendar_assignment_repository.list_relationship_lag(scope)
            resource_assignments = self.resource_assignment_repository.list(scope)
            resource_periods = self.resource_period_repository.list(scope)
            project_settings = self.project_schedule_settings_repository.get(scope)
        except (ProjectScheduleSettingsPersistenceError, CalendarPersistenceError) as exc:
            raise ScheduleInputCompositionError(str(exc)) from exc
        except (TypeError, ValueError) as exc:
            if isinstance(exc, ScheduleInputCompositionError):
                raise
            raise ScheduleInputCompositionError(f"PERSISTED_INPUT_READ_FAILED:{exc}") from exc

        if project_settings is None:
            raise ScheduleInputCompositionError("PROJECT_SCHEDULE_SETTINGS_NOT_FOUND")
        if project_settings.scope != scope:
            raise ScheduleInputCompositionError("PROJECT_SCHEDULE_SETTINGS_SCOPE_MISMATCH")
        try:
            project_settings.validate()
        except ProjectScheduleSettingsPersistenceError as exc:
            raise ScheduleInputCompositionError(str(exc)) from exc
        if project_settings.mode is not AuthoritativeScheduleMode.DATE_BASED:
            raise ScheduleInputCompositionError("TIME_AWARE_ACTIVITY_MASTER_MAPPING_NOT_IMPLEMENTED")
        if project_settings.schedule_options.data_date is not None and (
            not isinstance(project_settings.schedule_options.data_date, date)
            or isinstance(project_settings.schedule_options.data_date, datetime)
        ):
            raise ScheduleInputCompositionError("DATE_BASED_DATA_DATE_MUST_BE_DATE")
        options = project_settings.schedule_options
        leveling_requested = any((
            options.level_all_resources,
            options.level_within_float,
            options.resource_list is not None,
            options.priority_list is not None,
            options.min_float_to_preserve != 0,
            options.over_allocation_percentage != 0,
            options.preserve_scheduled_early_and_late_dates,
        ))

        if not persisted_activities:
            raise ScheduleInputCompositionError("SCHEDULE_ACTIVITIES_EMPTY")
        if not leveling_requested and (resource_assignments or resource_periods):
            # Resource data must not disappear silently from a plain schedule
            # snapshot. The separate Activity Master -> schedule resource binding
            # remains a distinct governed path; do not infer it here.
            raise ScheduleInputCompositionError("RESOURCE_ASSIGNMENTS_NOT_BOUND_TO_SNAPSHOT")
        activity_ids = {item.activity_id for item in persisted_activities}
        if len(activity_ids) != len(persisted_activities):
            raise ScheduleInputCompositionError("DUPLICATE_PERSISTED_ACTIVITY_ID")

        configured_calendar = project_settings.project_calendar
        project_calendar = self._load_calendar_reference(
            scope,
            configured_calendar.calendar_id,
            configured_calendar.calendar_version,
            expected_kind=configured_calendar.kind,
        )
        if project_calendar != configured_calendar:
            raise ScheduleInputCompositionError("PROJECT_CALENDAR_REFERENCE_MISMATCH")

        activities: list[Activity] = []
        for item in sorted(persisted_activities, key=lambda value: value.activity_id):
            if item.scope != scope:
                raise ScheduleInputCompositionError(f"ACTIVITY_SCOPE_MISMATCH:{item.activity_id}")
            if item.duration_unit is not DurationUnit.WORKING_DAY:
                raise ScheduleInputCompositionError(
                    f"UNSUPPORTED_DURATION_UNIT:{item.activity_id}:{item.duration_unit.value}"
                )
            value = item.duration_value
            if not isinstance(value, Decimal) or not value.is_finite() or value != value.to_integral_value():
                raise ScheduleInputCompositionError(f"NON_INTEGRAL_WORKING_DAY_DURATION:{item.activity_id}")
            try:
                activities.append(
                    Activity(
                        id=item.activity_id,
                        duration=int(value),
                        actual_start=self._date_value(item.actual_start, field_name="actual_start", activity_id=item.activity_id),
                        actual_finish=self._date_value(item.actual_finish, field_name="actual_finish", activity_id=item.activity_id),
                        remaining_duration=item.remaining_duration,
                        remaining_start=self._date_value(item.remaining_start, field_name="remaining_start", activity_id=item.activity_id),
                        percent_complete=item.percent_complete,
                        percent_complete_type=item.percent_complete_type,
                        expected_finish=self._date_value(item.expected_finish, field_name="expected_finish", activity_id=item.activity_id),
                        status=item.status,
                        activity_type=item.activity_type,
                        status_code=item.status_code,
                        name=item.name,
                        original_duration=item.original_duration,
                        planned_finish=self._date_value(item.planned_finish, field_name="planned_finish", activity_id=item.activity_id),
                        leveling_priority=item.leveling_priority,
                    )
                )
            except (TypeError, ValueError, ArithmeticError) as exc:
                raise ScheduleInputCompositionError(
                    f"INVALID_PERSISTED_ACTIVITY:{item.activity_id}:{exc}"
                ) from exc

        relationship_records_by_id = {
            item.relationship_id: item for item in persisted_relationships
        }
        if len(relationship_records_by_id) != len(persisted_relationships):
            raise ScheduleInputCompositionError("DUPLICATE_PERSISTED_RELATIONSHIP_ID")

        relationships: list[Relationship] = []
        for item in sorted(persisted_relationships, key=lambda value: value.relationship_id):
            if item.scope != scope:
                raise ScheduleInputCompositionError(
                    f"RELATIONSHIP_SCOPE_MISMATCH:{item.relationship_id}"
                )
            if item.lag_unit is not DurationUnit.WORKING_DAY:
                raise ScheduleInputCompositionError(
                    f"UNSUPPORTED_RELATIONSHIP_LAG_UNIT:{item.relationship_id}:{item.lag_unit.value}"
                )
            lag = item.lag_value
            if not isinstance(lag, Decimal) or not lag.is_finite() or lag != lag.to_integral_value():
                raise ScheduleInputCompositionError(
                    f"NON_INTEGRAL_WORKING_DAY_LAG:{item.relationship_id}"
                )
            try:
                relationships.append(
                    Relationship(
                        predecessor_id=item.predecessor_id,
                        successor_id=item.successor_id,
                        type=item.relationship_type,
                        lag=int(lag),
                    )
                )
            except (TypeError, ValueError) as exc:
                raise ScheduleInputCompositionError(
                    f"INVALID_PERSISTED_RELATIONSHIP:{item.relationship_id}:{exc}"
                ) from exc

        constraints: list[ActivityConstraint] = []
        for item in sorted(persisted_constraints, key=lambda value: value.constraint_id):
            if item.scope != scope:
                raise ScheduleInputCompositionError(f"CONSTRAINT_SCOPE_MISMATCH:{item.constraint_id}")
            if not isinstance(item.constraint_date, date) or isinstance(item.constraint_date, datetime):
                raise ScheduleInputCompositionError(
                    f"CONSTRAINT_DATE_PRECISION_UNSUPPORTED:{item.constraint_id}"
                )
            try:
                constraints.append(item.to_domain())
            except (TypeError, ValueError) as exc:
                raise ScheduleInputCompositionError(
                    f"INVALID_PERSISTED_CONSTRAINT:{item.constraint_id}:{exc}"
                ) from exc

        known_calendar_assignments: dict[str, ActivityCalendarAssignment] = {}
        for assignment in activity_calendar_assignments:
            if assignment.scope != scope:
                raise ScheduleInputCompositionError(
                    f"ACTIVITY_CALENDAR_ASSIGNMENT_SCOPE_MISMATCH:{assignment.activity_id}"
                )
            if assignment.activity_id not in activity_ids:
                raise ScheduleInputCompositionError(
                    f"ACTIVITY_CALENDAR_ASSIGNMENT_UNKNOWN_ACTIVITY:{assignment.activity_id}"
                )
            if assignment.activity_id in known_calendar_assignments:
                raise ScheduleInputCompositionError(
                    f"DUPLICATE_ACTIVITY_CALENDAR_ASSIGNMENT:{assignment.activity_id}"
                )
            reference = self._load_calendar_reference(
                scope, assignment.calendar_id, assignment.calendar_version,
            )
            if reference == project_calendar:
                # Explicitly preserve an explicit assignment even if it is the project calendar.
                known_calendar_assignments[assignment.activity_id] = ActivityCalendarAssignment(
                    assignment.activity_id, reference
                )
            else:
                known_calendar_assignments[assignment.activity_id] = ActivityCalendarAssignment(
                    assignment.activity_id, reference
                )

        relationship_lag_calendar_items: list[RelationshipLagCalendarAssignment] = []
        for assignment in sorted(
            relationship_lag_assignments, key=lambda item: item.relationship_id
        ):
            assignment.validate()
            if assignment.scope != scope:
                raise ScheduleInputCompositionError(
                    f"RELATIONSHIP_LAG_ASSIGNMENT_SCOPE_MISMATCH:{assignment.relationship_id}"
                )
            relationship = relationship_records_by_id.get(assignment.relationship_id)
            if relationship is None:
                raise ScheduleInputCompositionError(
                    f"RELATIONSHIP_LAG_ASSIGNMENT_UNKNOWN_RELATIONSHIP:{assignment.relationship_id}"
                )
            lag_calendar = None
            if assignment.calendar_id is not None:
                if assignment.calendar_version is None:
                    raise ScheduleInputCompositionError(
                        f"RELATIONSHIP_LAG_CALENDAR_VERSION_REQUIRED:{assignment.relationship_id}"
                    )
                lag_calendar = self._load_calendar_reference(
                    scope,
                    assignment.calendar_id,
                    assignment.calendar_version,
                    expected_kind=(
                        "working-day"
                        if project_settings.mode is AuthoritativeScheduleMode.DATE_BASED
                        else "working-time"
                    ),
                )
            try:
                relationship_lag_calendar_items.append(
                    RelationshipLagCalendarAssignment(
                        relationship_id=assignment.relationship_id,
                        predecessor_id=relationship.predecessor_id,
                        successor_id=relationship.successor_id,
                        option=assignment.option,
                        calendar=lag_calendar,
                    )
                )
            except (TypeError, ValueError) as exc:
                raise ScheduleInputCompositionError(
                    f"INVALID_RELATIONSHIP_LAG_ASSIGNMENT:{assignment.relationship_id}:{exc}"
                ) from exc

        resource_leveling_input = None
        if leveling_requested:
            resource_leveling_input = self._compose_resource_leveling_input(
                scope,
                project_settings,
                persisted_activities,
                resource_assignments,
                resource_periods,
                activity_ids,
            )

        return AuthoritativeScheduleInput(
            snapshot_id=snapshot_id,
            tenant_id=scope.tenant_id,
            project_id=scope.project_id,
            project_revision=scope.project_revision,
            mode=project_settings.mode,
            project_calendar=project_calendar,
            activities=tuple(activities),
            relationships=tuple(relationships),
            activity_calendar_assignments=tuple(
                known_calendar_assignments[key] for key in sorted(known_calendar_assignments)
            ),
            relationship_lag_calendar_assignments=tuple(relationship_lag_calendar_items),
            constraints=tuple(constraints),
            schedule_options=project_settings.schedule_options,
            project_start=project_settings.project_start,
            project_finish=project_settings.project_finish,
            project_leveling_priority=project_settings.project_leveling_priority,
            resource_leveling_input=resource_leveling_input,
        )


__all__ = [
    "AuthoritativeScheduleInputComposer",
    "ScheduleInputCompositionError",
]
