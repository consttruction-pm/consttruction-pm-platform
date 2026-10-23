from __future__ import annotations

"""Fresh persisted-record to immutable schedule-input composition boundary.

This module is deliberately an application adapter: all scheduling semantics
remain in the shared scheduling domain/core. Unsupported date/resource/calendar
semantics fail closed instead of being coerced or silently omitted.
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .activity_master_repository import ActivityMasterRepository
from .backend_p0.models import BackendScope
from .calendar_exception_repository import CalendarExceptionRepository
from .calendar_master_repository import (
    ActivityCalendarAssignmentMaster,
    CalendarMaster,
    CalendarMasterRepository,
    CalendarPersistenceError,
    RelationshipLagCalendarAssignmentMaster,
)
from .calendar_snapshot_repository import CalendarSnapshotRepository
from .calendar_work_hours_repository import CalendarWorkHourRepository
from .constraint_master_repository import ConstraintMasterRepository
from .relationship_master_repository import RelationshipMasterRepository
from .p6_resource_assignment_repository import (
    P6ResourceAssignmentPeriodRepository,
    P6ResourceAssignmentRepository,
)
from .p6_resource_rate_repository import (
    P6ResourceRatePersistenceError,
    P6ResourceRateRepository,
)
from .project_schedule_settings_repository import (
    ProjectScheduleSettings,
    ProjectScheduleSettingsPersistenceError,
    ProjectScheduleSettingsRepository,
)
from .scheduling.activity import Activity, ActivityType
from .scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from .scheduling.calendar_context import CalendarReference
from .scheduling.calendar_system import CalendarSystem
from .scheduling.constraints import ActivityConstraint
from .scheduling.relationships import Relationship
from .scheduling.resource_leveling import ResourceCapacity
from .scheduling.resource_leveling_input import (
    ResourceAssignmentLevelingRef,
    ResourceDemandInput,
    ResourceCapacityRate,
    ResourceLevelingFacts,
    ResourceLevelingFactsError,
)
from .p6_versioned_resource_calendar_resolver import (
    P6ResourceCalendarResolutionError,
    resolve_p6_resource_calendar,
)
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
        resource_rate_repository: P6ResourceRateRepository | None = None,
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
        self.resource_rate_repository = resource_rate_repository

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


    @staticmethod
    def _resource_leveling_requested(options: object) -> bool:
        return any((
            getattr(options, "level_all_resources"),
            getattr(options, "level_within_float"),
            getattr(options, "resource_list") is not None,
            getattr(options, "priority_list") is not None,
            getattr(options, "min_float_to_preserve") != 0,
            getattr(options, "over_allocation_percentage") != 0,
            getattr(options, "preserve_scheduled_early_and_late_dates"),
        ))

    @staticmethod
    def _profile_period_hours(rate: ResourceCapacityRate, calendar_snapshot: object) -> Decimal:
        """Verify the time-period factor against the exact declared P6 source."""
        if rate.time_period_source == "global":
            # Global time-period factors are persisted directly with the profile
            # contract and included in its profile hash; never infer defaults.
            return rate.hours_per_time_period

        raw_snapshot = getattr(calendar_snapshot, "snapshot", None)
        if not isinstance(raw_snapshot, dict):
            raise ScheduleInputCompositionError("RESOURCE_CALENDAR_SNAPSHOT_NOT_FOUND")
        factors = raw_snapshot.get("time_period_factors")
        if not isinstance(factors, dict):
            raise ScheduleInputCompositionError("RESOURCE_CALENDAR_TIME_PERIOD_FACTORS_REQUIRED")
        mapping = {
            "hour": Decimal("1"),
            "day": "hours_per_day",
            "week": "hours_per_week",
            "month": "hours_per_month",
            "year": "hours_per_year",
        }
        factor_key = mapping.get(rate.time_period_unit)
        if isinstance(factor_key, Decimal):
            expected = factor_key
        elif isinstance(factor_key, str):
            try:
                expected = Decimal(str(factors[factor_key]))
            except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                raise ScheduleInputCompositionError(
                    "RESOURCE_CALENDAR_TIME_PERIOD_FACTOR_MISSING"
                ) from exc
        else:
            raise ScheduleInputCompositionError("INVALID_RESOURCE_RATE_TIME_PERIOD_UNIT")
        if expected != rate.hours_per_time_period:
            raise ScheduleInputCompositionError("RESOURCE_RATE_CALENDAR_FACTOR_MISMATCH")
        return expected

    def _compose_resource_leveling_facts(
        self,
        scope: BackendScope,
        schedule_input: AuthoritativeScheduleInput,
        assignments: tuple,
        persisted_periods: tuple,
        *,
        calculation_timezone: str,
    ) -> ResourceLevelingFacts:
        """Compose hash-bound assignment demand and Max Units/Time capacity."""
        if self.calendar_exception_repository is None or self.calendar_work_hours_repository is None:
            raise ScheduleInputCompositionError("RESOURCE_CALENDAR_RESOLVER_NOT_CONFIGURED")
        if self.resource_rate_repository is None:
            raise ScheduleInputCompositionError("RESOURCE_MAX_UNITS_PER_TIME_REPOSITORY_NOT_CONFIGURED")
        if not isinstance(calculation_timezone, str) or not calculation_timezone.strip():
            raise ScheduleInputCompositionError("CALCULATION_TIMEZONE_REQUIRED")
        try:
            calculation_zone = ZoneInfo(calculation_timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ScheduleInputCompositionError("INVALID_CALCULATION_TIMEZONE") from exc
        if not assignments:
            raise ScheduleInputCompositionError("RESOURCE_LEVELING_ASSIGNMENTS_REQUIRED")
        if not persisted_periods:
            raise ScheduleInputCompositionError("RESOURCE_LEVELING_DEMAND_PERIODS_REQUIRED")

        try:
            persisted_rates = self.resource_rate_repository.list(scope)
        except (P6ResourceRatePersistenceError, TypeError, ValueError) as exc:
            raise ScheduleInputCompositionError(f"RESOURCE_RATE_READ_FAILED:{exc}") from exc

        activity_ids = {activity.id for activity in schedule_input.activities}
        activity_by_id = {activity.id: activity for activity in schedule_input.activities}
        assignment_by_id: dict[str, object] = {}
        resource_calendar_refs: dict[str, tuple[str, str]] = {}
        assignment_refs: list[ResourceAssignmentLevelingRef] = []
        resource_units: dict[str, str] = {}
        for assignment in sorted(assignments, key=lambda item: item.assignment_id):
            assignment.validate()
            if assignment.scope != scope:
                raise ScheduleInputCompositionError("RESOURCE_ASSIGNMENT_SCOPE_MISMATCH")
            if assignment.activity_id not in activity_ids:
                raise ScheduleInputCompositionError("RESOURCE_ASSIGNMENT_UNKNOWN_ACTIVITY")
            if activity_by_id[assignment.activity_id].activity_type is ActivityType.RESOURCE_DEPENDENT:
                # The driving flag is now persisted, but Resource Dependent
                # forward/backward date derivation and nondriving placement are
                # not yet implemented in the shared scheduler. Keep this guard
                # until those semantics and end-to-end regression tests exist;
                # a persisted flag alone is not sufficient to schedule safely.
                raise ScheduleInputCompositionError(
                    "RESOURCE_DEPENDENT_DRIVING_ASSIGNMENT_UNSUPPORTED"
                )
            if assignment.calendar_id is None or assignment.calendar_version is None:
                raise ScheduleInputCompositionError("MISSING_RESOURCE_CALENDAR_VERSION")
            if not isinstance(assignment.unit, str) or not assignment.unit.strip():
                raise ScheduleInputCompositionError("RESOURCE_ASSIGNMENT_UNIT_OF_MEASURE_REQUIRED")
            if assignment.assignment_id in assignment_by_id:
                raise ScheduleInputCompositionError("DUPLICATE_RESOURCE_ASSIGNMENT_ID")
            ref = (assignment.calendar_id, assignment.calendar_version)
            existing_ref = resource_calendar_refs.get(assignment.resource_id)
            if existing_ref is not None and existing_ref != ref:
                raise ScheduleInputCompositionError("AMBIGUOUS_RESOURCE_CALENDAR")
            resource_calendar_refs[assignment.resource_id] = ref
            old_unit = resource_units.get(assignment.resource_id)
            if old_unit is not None and old_unit != assignment.unit:
                raise ScheduleInputCompositionError("RESOURCE_ASSIGNMENT_UNIT_MISMATCH")
            resource_units[assignment.resource_id] = assignment.unit
            assignment_by_id[assignment.assignment_id] = assignment
            assignment_refs.append(ResourceAssignmentLevelingRef(
                assignment_id=assignment.assignment_id,
                activity_id=assignment.activity_id,
                resource_id=assignment.resource_id,
                calendar_id=assignment.calendar_id,
                calendar_version=assignment.calendar_version,
                unit_of_measure=assignment.unit,
                assigned_units=assignment.units,
                remaining_units=assignment.remaining_units,
                is_driving=assignment.is_driving,
                units_per_time=assignment.units_per_time,
                units_per_time_period=assignment.units_per_time_period,
                hours_per_units_time_period=assignment.hours_per_units_time_period,
            ))

        demands: list[ResourceDemandInput] = []
        seen_demand_keys: set[tuple[str, date]] = set()
        for period in sorted(persisted_periods, key=lambda item: (item.assignment_id, item.period_start)):
            period.validate()
            if period.scope != scope:
                raise ScheduleInputCompositionError("RESOURCE_PERIOD_SCOPE_MISMATCH")
            assignment = assignment_by_id.get(period.assignment_id)
            if assignment is None:
                raise ScheduleInputCompositionError("RESOURCE_PERIOD_ASSIGNMENT_NOT_FOUND")
            if (
                period.activity_id != assignment.activity_id
                or period.resource_id != assignment.resource_id
            ):
                raise ScheduleInputCompositionError("RESOURCE_PERIOD_ASSIGNMENT_MISMATCH")
            try:
                period_date = date.fromisoformat(period.period_start)
            except (TypeError, ValueError) as exc:
                raise ScheduleInputCompositionError("INVALID_RESOURCE_PERIOD_DATE") from exc
            demand_key = (period.assignment_id, period_date)
            if demand_key in seen_demand_keys:
                raise ScheduleInputCompositionError("DUPLICATE_RESOURCE_DEMAND_PERIOD")
            seen_demand_keys.add(demand_key)
            demands.append(ResourceDemandInput(
                assignment_id=period.assignment_id,
                activity_id=period.activity_id,
                resource_id=period.resource_id,
                period=period_date,
                units=period.units,
            ))

        rates_by_resource: dict[str, list[ResourceCapacityRate]] = {}
        seen_rate_keys: set[tuple[str, datetime, str]] = set()
        for rate in sorted(persisted_rates, key=lambda item: (item.resource_id, item.effective_from, item.shift_id)):
            rate.validate()
            rate_key = (rate.resource_id, rate.effective_from, rate.shift_id)
            if rate_key in seen_rate_keys:
                raise ScheduleInputCompositionError("DUPLICATE_RESOURCE_RATE")
            seen_rate_keys.add(rate_key)
            if rate.resource_id not in resource_calendar_refs:
                continue
            if rate.unit_of_measure != resource_units[rate.resource_id]:
                raise ScheduleInputCompositionError("RESOURCE_RATE_UNIT_MISMATCH")
            local_effective = rate.effective_from.astimezone(calculation_zone)
            if local_effective.time() != time.min:
                raise ScheduleInputCompositionError("RESOURCE_RATE_EFFECTIVE_TIME_NOT_REPRESENTABLE")
            rates_by_resource.setdefault(rate.resource_id, []).append(rate)

        for resource_id in resource_calendar_refs:
            resource_rates = rates_by_resource.get(resource_id, [])
            if not resource_rates:
                raise ScheduleInputCompositionError("RESOURCE_MAX_UNITS_PER_TIME_REQUIRED")
            # The v1 date-based resource capacity contract cannot model shift
            # calendars. Refuse ambiguous multi-shift rows rather than summing
            # overlapping shift capacities or selecting one without authority.
            if len({rate.shift_id for rate in resource_rates}) != 1:
                raise ScheduleInputCompositionError("RESOURCE_RATE_SHIFT_LEVELING_UNSUPPORTED")
            resource_rates.sort(key=lambda item: item.effective_from)

        # Build one immutable, finite calendar-hours envelope. It is not itself
        # resource capacity: P6 Max Units/Time is applied below for every date.
        anchors: list[date] = [schedule_input.project_start]
        if schedule_input.project_finish is not None:
            anchors.append(schedule_input.project_finish)
        anchors.extend(demand.period for demand in demands)
        anchors.extend(item.date for item in schedule_input.constraints)
        for activity in schedule_input.activities:
            for value in (
                activity.actual_start, activity.actual_finish, activity.remaining_start,
                activity.expected_finish, activity.planned_finish,
            ):
                if isinstance(value, date) and not isinstance(value, datetime):
                    anchors.append(value)
        horizon_start = min(anchors)
        horizon_seed_end = max(anchors)
        total_duration = sum(activity.duration for activity in schedule_input.activities)
        positive_lags = sum(max(0, relationship.lag) for relationship in schedule_input.relationships)
        safety_days = max(30, total_duration + positive_lags + (7 * len(schedule_input.activities)))
        horizon_end = horizon_seed_end + timedelta(days=safety_days)
        horizon_span = (horizon_end - horizon_start).days
        if horizon_span < 0 or horizon_span > 36500:
            raise ScheduleInputCompositionError("RESOURCE_LEVELING_CAPACITY_HORIZON_OUT_OF_RANGE")
        capacity_periods = tuple(
            horizon_start + timedelta(days=offset)
            for offset in range(horizon_span + 1)
        )

        resolved_calendars: dict[tuple[str, str], object] = {}
        calendar_snapshots: dict[tuple[str, str], object] = {}
        for calendar_ref in sorted(set(resource_calendar_refs.values())):
            try:
                master = self.calendar_repository.get(scope, calendar_ref[0], calendar_ref[1])
                if master is None or master.scope != scope:
                    raise ScheduleInputCompositionError("RESOURCE_CALENDAR_VERSION_NOT_FOUND")
                calendar_snapshot = self.calendar_snapshot_repository.get(master)
                if calendar_snapshot is None:
                    raise ScheduleInputCompositionError("RESOURCE_CALENDAR_SNAPSHOT_NOT_FOUND")
                resolved = resolve_p6_resource_calendar(
                    scope=scope,
                    calendar_id=calendar_ref[0],
                    calendar_version=calendar_ref[1],
                    periods=capacity_periods,
                    calendar_repository=self.calendar_repository,
                    snapshot_repository=self.calendar_snapshot_repository,
                    exception_repository=self.calendar_exception_repository,
                    work_hours_repository=self.calendar_work_hours_repository,
                )
                resolved_calendars[calendar_ref] = resolved
                calendar_snapshots[calendar_ref] = calendar_snapshot
            except ScheduleInputCompositionError:
                raise
            except (P6ResourceCalendarResolutionError, CalendarPersistenceError, TypeError, ValueError) as exc:
                raise ScheduleInputCompositionError(
                    f"RESOURCE_CALENDAR_RESOLUTION_FAILED:{exc}"
                ) from exc

        rates_snapshot = tuple(sorted(
            (rate for resource_rates in rates_by_resource.values() for rate in resource_rates),
            key=lambda item: (item.resource_id, item.effective_from, item.shift_id),
        ))
        capacities: list[ResourceCapacity] = []
        for resource_id, calendar_ref in sorted(resource_calendar_refs.items()):
            calendar = resolved_calendars[calendar_ref]
            calendar_snapshot = calendar_snapshots[calendar_ref]
            if calendar.canonical_snapshot_hash is None or not calendar.capacity_slices:
                raise ScheduleInputCompositionError("RESOURCE_CALENDAR_CAPACITY_NOT_HASH_BOUND")
            resource_rates = rates_by_resource[resource_id]
            factors_snapshot = self._profile_period_hours(
                resource_rates[0], calendar_snapshot
            )
            del factors_snapshot  # exact period factor is checked for each effective rate below
            capacity_hours_by_period = dict(calendar.capacity_slices)
            # Periods and rate rows are ordered. Advance one pointer instead
            # of rescanning every historical rate for every date (O(days*rates)
            # becomes O(days+rates) for long-horizon construction schedules).
            rate_index = 0
            selected_rate: ResourceCapacityRate | None = None
            for period in capacity_periods:
                local_boundary = datetime.combine(period, time.min, tzinfo=calculation_zone)
                while (
                    rate_index < len(resource_rates)
                    and resource_rates[rate_index].effective_from <= local_boundary
                ):
                    selected_rate = resource_rates[rate_index]
                    rate_index += 1
                if selected_rate is None:
                    raise ScheduleInputCompositionError("RESOURCE_MAX_UNITS_PER_TIME_NOT_EFFECTIVE")
                if selected_rate.time_period_source == "calendar":
                    self._profile_period_hours(selected_rate, calendar_snapshot)
                hours = capacity_hours_by_period.get(period)
                if hours is None:
                    raise ScheduleInputCompositionError("RESOURCE_CALENDAR_CAPACITY_PERIOD_MISSING")
                capacity_units = selected_rate.capacity_for_work_hours(hours)
                capacities.append(ResourceCapacity(
                    resource_id=resource_id,
                    period=period,
                    units=capacity_units,
                    calendar_id=calendar_ref[0],
                    calendar_version=calendar_ref[1],
                    calendar_snapshot_hash=calendar.canonical_snapshot_hash,
                    calendar_work_hours=hours,
                    resource_rate_hash=selected_rate.profile_hash,
                    resource_rate_effective_from=selected_rate.effective_from,
                ))

        facts = ResourceLevelingFacts(
            assignments=tuple(assignment_refs),
            demands=tuple(demands),
            capacities=tuple(capacities),
            resource_capacity_rates=rates_snapshot,
            capacity_horizon_start=horizon_start,
            capacity_horizon_end=horizon_end,
            calculation_timezone=calculation_timezone,
        )
        try:
            facts.validate(activity_ids=activity_ids)
        except ResourceLevelingFactsError as exc:
            raise ScheduleInputCompositionError(str(exc)) from exc
        return facts

    def compose(
        self,
        scope: BackendScope,
        *,
        snapshot_id: str,
        calculation_timezone: str | None = None,
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
        if relationship_lag_assignments:
            # P6 v26 exposes one schedule-wide "Calendar for scheduling
            # Relationship Lag" option. Per-relationship overrides are not
            # part of that P6 calculation profile; fail closed rather than
            # silently produce different dates under the P6 label.
            raise ScheduleInputCompositionError(
                "PER_RELATIONSHIP_LAG_CALENDAR_NOT_SUPPORTED_BY_P6_PROFILE"
            )
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
        leveling_requested = self._resource_leveling_requested(options)
        if leveling_requested and (
            options.include_external_res_ass
            or options.external_project_priority_limit > 0
        ):
            # Cross-project assignments and project leveling-priority ordering
            # are not in this project's immutable input pool yet. Never level
            # a single-project subset while the user requested external scope.
            raise ScheduleInputCompositionError("CROSS_PROJECT_RESOURCE_LEVELING_UNSUPPORTED")
        if leveling_requested and options.recalculate_resource_costs:
            # Current Schedule Query produces schedule dates/floats, not
            # authoritative re-costed resource assignment outputs.
            raise ScheduleInputCompositionError("RESOURCE_COST_RECALCULATION_AFTER_LEVELING_UNSUPPORTED")

        if not persisted_activities:
            raise ScheduleInputCompositionError("SCHEDULE_ACTIVITIES_EMPTY")
        if not leveling_requested and (resource_assignments or resource_periods):
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

        schedule_input = AuthoritativeScheduleInput(
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
            constraints=tuple(constraints),
            schedule_options=project_settings.schedule_options,
            project_start=project_settings.project_start,
            project_finish=project_settings.project_finish,
            project_leveling_priority=project_settings.project_leveling_priority,
        )
        if not leveling_requested:
            return schedule_input
        if not isinstance(calculation_timezone, str) or not calculation_timezone.strip():
            raise ScheduleInputCompositionError("CALCULATION_TIMEZONE_REQUIRED")
        resource_leveling_inputs = self._compose_resource_leveling_facts(
            scope,
            schedule_input,
            resource_assignments,
            resource_periods,
            calculation_timezone=calculation_timezone,
        )
        return AuthoritativeScheduleInput(
            snapshot_id=schedule_input.snapshot_id,
            tenant_id=schedule_input.tenant_id,
            project_id=schedule_input.project_id,
            project_revision=schedule_input.project_revision,
            mode=schedule_input.mode,
            project_calendar=schedule_input.project_calendar,
            activities=schedule_input.activities,
            relationships=schedule_input.relationships,
            activity_calendar_assignments=schedule_input.activity_calendar_assignments,
            constraints=schedule_input.constraints,
            schedule_options=schedule_input.schedule_options,
            project_start=schedule_input.project_start,
            project_finish=schedule_input.project_finish,
            project_leveling_priority=schedule_input.project_leveling_priority,
            resource_leveling_inputs=resource_leveling_inputs,
        )


__all__ = [
    "AuthoritativeScheduleInputComposer",
    "ScheduleInputCompositionError",
]
