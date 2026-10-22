from __future__ import annotations

"""Fresh persisted-record to immutable schedule-input composition boundary.

This module is deliberately an application adapter: all scheduling semantics
remain in the shared scheduling domain/core. Unsupported date/resource/calendar
semantics fail closed instead of being coerced or silently omitted.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
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
from .constraint_master_repository import ConstraintMasterRepository
from .relationship_master_repository import RelationshipMasterRepository
from .p6_resource_assignment_repository import (
    P6ResourceAssignmentPeriodRepository,
    P6ResourceAssignmentRepository,
)
from .scheduling.activity import Activity
from .scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from .scheduling.calendar_context import CalendarReference
from .scheduling.calendar_system import CalendarSystem
from .scheduling.constraints import ActivityConstraint
from .scheduling.relationships import Relationship
from .scheduling.schedule_options import ScheduleOptions
from .scheduling.time_duration import DurationUnit


class ScheduleInputCompositionError(ValueError):
    """Raised when persisted project records cannot safely form a schedule input."""


@dataclass(frozen=True)
class ScheduleInputDefinition:
    """Explicit schedule settings required to compose one DATE_BASED schedule.

    These are project schedule settings supplied by the trusted application
    boundary; the composer does not guess project dates, calendars, units or
    option values when persistence has not yet modeled them.
    """

    project_calendar_id: str
    project_calendar_version: str
    project_start: date
    schedule_options: ScheduleOptions
    project_finish: date | None = None
    mode: AuthoritativeScheduleMode = AuthoritativeScheduleMode.DATE_BASED
    project_leveling_priority: int = 10

    def validate(self) -> None:
        if not isinstance(self.project_calendar_id, str) or not self.project_calendar_id.strip():
            raise ScheduleInputCompositionError("PROJECT_CALENDAR_ID_REQUIRED")
        if not isinstance(self.project_calendar_version, str) or not self.project_calendar_version.strip():
            raise ScheduleInputCompositionError("PROJECT_CALENDAR_VERSION_REQUIRED")
        if not isinstance(self.mode, AuthoritativeScheduleMode):
            raise ScheduleInputCompositionError("INVALID_SCHEDULE_MODE")
        if self.mode is not AuthoritativeScheduleMode.DATE_BASED:
            raise ScheduleInputCompositionError("TIME_AWARE_ACTIVITY_MASTER_MAPPING_NOT_IMPLEMENTED")
        if not isinstance(self.project_start, date) or isinstance(self.project_start, datetime):
            raise ScheduleInputCompositionError("DATE_BASED_PROJECT_START_MUST_BE_DATE")
        if self.project_finish is not None and (
            not isinstance(self.project_finish, date) or isinstance(self.project_finish, datetime)
        ):
            raise ScheduleInputCompositionError("DATE_BASED_PROJECT_FINISH_MUST_BE_DATE")
        if not isinstance(self.schedule_options, ScheduleOptions):
            raise ScheduleInputCompositionError("TYPED_SCHEDULE_OPTIONS_REQUIRED")
        if isinstance(self.project_leveling_priority, bool) or not isinstance(self.project_leveling_priority, int) or not 1 <= self.project_leveling_priority <= 100:
            raise ScheduleInputCompositionError("INVALID_PROJECT_LEVELING_PRIORITY")
        if self.schedule_options.data_date is not None and (
            not isinstance(self.schedule_options.data_date, date)
            or isinstance(self.schedule_options.data_date, datetime)
        ):
            raise ScheduleInputCompositionError("DATE_BASED_DATA_DATE_MUST_BE_DATE")

        options = self.schedule_options
        if any((
            options.level_all_resources,
            options.level_within_float,
            options.resource_list is not None,
            options.priority_list is not None,
            options.min_float_to_preserve != 0,
            options.over_allocation_percentage != 0,
            options.preserve_scheduled_early_and_late_dates,
        )):
            raise ScheduleInputCompositionError("RESOURCE_LEVELING_REQUIRES_HASH_BOUND_INPUT")


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
    ) -> None:
        self.activity_repository = activity_repository
        self.relationship_repository = relationship_repository
        self.constraint_repository = constraint_repository
        self.calendar_repository = calendar_repository
        self.calendar_assignment_repository = calendar_assignment_repository
        self.calendar_snapshot_repository = calendar_snapshot_repository
        self.resource_assignment_repository = resource_assignment_repository
        self.resource_period_repository = resource_period_repository

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
        if snapshot_data.get("kind") != calendar.kind:
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

    def compose(
        self,
        scope: BackendScope,
        *,
        snapshot_id: str,
        definition: ScheduleInputDefinition,
    ) -> AuthoritativeScheduleInput:
        scope.validate()
        if not isinstance(snapshot_id, str) or not snapshot_id.strip():
            raise ScheduleInputCompositionError("SNAPSHOT_ID_REQUIRED")
        definition.validate()
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
        except (TypeError, ValueError) as exc:
            if isinstance(exc, ScheduleInputCompositionError):
                raise
            raise ScheduleInputCompositionError(f"PERSISTED_INPUT_READ_FAILED:{exc}") from exc

        if not persisted_activities:
            raise ScheduleInputCompositionError("SCHEDULE_ACTIVITIES_EMPTY")
        if resource_assignments or resource_periods:
            raise ScheduleInputCompositionError("RESOURCE_ASSIGNMENTS_NOT_BOUND_TO_SNAPSHOT")
        if relationship_lag_assignments:
            raise ScheduleInputCompositionError("RELATIONSHIP_LAG_CALENDAR_ASSIGNMENTS_NOT_BOUND_TO_SNAPSHOT")

        activity_ids = {item.activity_id for item in persisted_activities}
        if len(activity_ids) != len(persisted_activities):
            raise ScheduleInputCompositionError("DUPLICATE_PERSISTED_ACTIVITY_ID")

        project_calendar = self._load_calendar_reference(
            scope,
            definition.project_calendar_id,
            definition.project_calendar_version,
        )

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

        return AuthoritativeScheduleInput(
            snapshot_id=snapshot_id,
            tenant_id=scope.tenant_id,
            project_id=scope.project_id,
            project_revision=scope.project_revision,
            mode=definition.mode,
            project_calendar=project_calendar,
            activities=tuple(activities),
            relationships=tuple(relationships),
            activity_calendar_assignments=tuple(
                known_calendar_assignments[key] for key in sorted(known_calendar_assignments)
            ),
            constraints=tuple(constraints),
            schedule_options=definition.schedule_options,
            project_start=definition.project_start,
            project_finish=definition.project_finish,
            project_leveling_priority=definition.project_leveling_priority,
        )


__all__ = [
    "AuthoritativeScheduleInputComposer",
    "ScheduleInputCompositionError",
    "ScheduleInputDefinition",
]
