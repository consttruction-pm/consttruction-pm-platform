from __future__ import annotations

"""Fresh persisted-record to immutable schedule-input composition boundary.

This module is deliberately an application adapter: all scheduling semantics
remain in the shared scheduling domain/core. Unsupported date/resource/calendar
semantics fail closed instead of being coerced or silently omitted.
"""

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
from .project_schedule_settings_repository import (
    ProjectScheduleSettings,
    ProjectScheduleSettingsPersistenceError,
    ProjectScheduleSettingsRepository,
)
from .scheduling.activity import Activity, ActivityStatus, ActivityType
from .scheduling.resource_dependent import (
    ResourceDependentCalculationError,
    ResourceDependentDriverFact,
    ResourceDependentDuration,
    derive_resource_dependent_duration,
)
from .scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
    RelationshipLagCalendarAssignment,
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
        # Resource leveling is bound by the authoritative Schedule Query's
        # hash-bound companion input. Do not reject valid persisted options here;
        # the query resolver will read exact-version resource/calendar facts and
        # fail closed if those facts are unavailable.
        options = project_settings.schedule_options

        if not persisted_activities:
            raise ScheduleInputCompositionError("SCHEDULE_ACTIVITIES_EMPTY")
        activity_ids = {item.activity_id for item in persisted_activities}
        if len(activity_ids) != len(persisted_activities):
            raise ScheduleInputCompositionError("DUPLICATE_PERSISTED_ACTIVITY_ID")

        # Resource assignments and period values remain in their own immutable,
        # revision-scoped repositories and are bound by the leveler's companion
        # input/hash. Validate the cross-record references here so the snapshot
        # publisher cannot silently bless orphaned or mis-scoped resource data.
        assignments_by_id = {}
        for assignment in resource_assignments:
            if assignment.scope != scope:
                raise ScheduleInputCompositionError(
                    f"RESOURCE_ASSIGNMENT_SCOPE_MISMATCH:{assignment.assignment_id}"
                )
            try:
                assignment.validate()
            except (TypeError, ValueError) as exc:
                raise ScheduleInputCompositionError(
                    f"INVALID_RESOURCE_ASSIGNMENT:{assignment.assignment_id}:{exc}"
                ) from exc
            if assignment.assignment_id in assignments_by_id:
                raise ScheduleInputCompositionError("DUPLICATE_PERSISTED_RESOURCE_ASSIGNMENT_ID")
            if assignment.activity_id not in activity_ids:
                raise ScheduleInputCompositionError(
                    f"RESOURCE_ASSIGNMENT_UNKNOWN_ACTIVITY:{assignment.assignment_id}:{assignment.activity_id}"
                )
            assignments_by_id[assignment.assignment_id] = assignment

        seen_resource_periods = set()
        for period in resource_periods:
            if period.scope != scope:
                raise ScheduleInputCompositionError(
                    f"RESOURCE_PERIOD_SCOPE_MISMATCH:{period.assignment_id}:{period.period_start}"
                )
            try:
                period.validate()
            except (TypeError, ValueError) as exc:
                raise ScheduleInputCompositionError(
                    f"INVALID_RESOURCE_PERIOD:{period.assignment_id}:{period.period_start}:{exc}"
                ) from exc
            assignment = assignments_by_id.get(period.assignment_id)
            if assignment is None:
                raise ScheduleInputCompositionError(
                    f"RESOURCE_PERIOD_ASSIGNMENT_NOT_FOUND:{period.assignment_id}"
                )
            if (
                period.activity_id != assignment.activity_id
                or period.resource_id != assignment.resource_id
            ):
                raise ScheduleInputCompositionError(
                    f"RESOURCE_PERIOD_ASSIGNMENT_MISMATCH:{period.assignment_id}:{period.period_start}"
                )
            try:
                date.fromisoformat(period.period_start)
            except (TypeError, ValueError) as exc:
                raise ScheduleInputCompositionError(
                    f"INVALID_RESOURCE_PERIOD_START:{period.assignment_id}:{period.period_start}"
                ) from exc
            period_key = (period.assignment_id, period.period_start)
            if period_key in seen_resource_periods:
                raise ScheduleInputCompositionError("DUPLICATE_PERSISTED_RESOURCE_PERIOD")
            seen_resource_periods.add(period_key)

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
        resource_dependent_durations: dict[str, ResourceDependentDuration] = {}
        resource_dependent_assignment_facts: list[ResourceDependentDriverFact] = []
        assignments_by_activity: dict[str, list[object]] = {}
        for assignment in assignments_by_id.values():
            assignments_by_activity.setdefault(assignment.activity_id, []).append(assignment)

        for item in sorted(persisted_activities, key=lambda value: value.activity_id):
            if item.scope != scope:
                raise ScheduleInputCompositionError(f"ACTIVITY_SCOPE_MISMATCH:{item.activity_id}")
            if item.duration_unit is not DurationUnit.WORKING_DAY:
                raise ScheduleInputCompositionError(
                    f"UNSUPPORTED_DURATION_UNIT:{item.activity_id}:{item.duration_unit.value}"
                )

            raw_activity_type = getattr(item.activity_type, "value", item.activity_type)
            resource_dependent = raw_activity_type == ActivityType.RESOURCE_DEPENDENT.value
            derived = None
            if resource_dependent:
                raw_status = getattr(item.status, "value", item.status)
                if (
                    raw_status != ActivityStatus.NOT_STARTED.value
                    or item.actual_start is not None
                    or item.actual_finish is not None
                ):
                    raise ScheduleInputCompositionError(
                        f"RESOURCE_DEPENDENT_IN_PROGRESS_DERIVATION_UNSUPPORTED:{item.activity_id}"
                    )
                raw_assignments = assignments_by_activity.get(item.activity_id, [])
                facts = tuple(
                    ResourceDependentDriverFact(
                        assignment_id=assignment.assignment_id,
                        activity_id=assignment.activity_id,
                        resource_id=assignment.resource_id,
                        calendar_id=assignment.calendar_id,
                        calendar_version=assignment.calendar_version,
                        unit_of_measure=assignment.unit,
                        planned_units=assignment.units,
                        is_driving=assignment.is_driving,
                        units_per_time=assignment.units_per_time,
                        units_per_time_period=assignment.units_per_time_period,
                        hours_per_units_time_period=assignment.hours_per_units_time_period,
                    )
                    for assignment in raw_assignments
                )
                resource_dependent_assignment_facts.extend(facts)
                try:
                    derived = derive_resource_dependent_duration(
                        tenant_id=scope.tenant_id,
                        project_id=scope.project_id,
                        project_revision=scope.project_revision,
                        activity_id=item.activity_id,
                        assignments=facts,
                    )
                except ResourceDependentCalculationError as exc:
                    raise ScheduleInputCompositionError(
                        f"{exc}:{item.activity_id}"
                    ) from exc
                resource_dependent_durations[item.activity_id] = derived
                value = Decimal(derived.duration_working_days)
            else:
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
                        resource_dependent_input_hash=None if derived is None else derived.input_hash,
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

        # Resource Dependent activities follow their driving resource calendar,
        # pinned to the exact master version used to derive the duration.
        for activity_id, derived in resource_dependent_durations.items():
            reference = self._load_calendar_reference(
                scope, derived.calendar_id, derived.calendar_version,
                expected_kind="working-day",
            )
            known_calendar_assignments[activity_id] = ActivityCalendarAssignment(
                activity_id, reference
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
            resource_dependent_assignment_facts=tuple(
                sorted(resource_dependent_assignment_facts, key=lambda fact: fact.assignment_id)
            ),
        )


__all__ = [
    "AuthoritativeScheduleInputComposer",
    "ScheduleInputCompositionError",
]
