from __future__ import annotations

"""Materialize immutable schedule snapshots into Shared Scheduling Core models."""

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from .schedule_input_snapshot_repository import ScheduleInputSnapshot
from .scheduling.activity import (
    Activity,
    ActivityLevelingPriority,
    ActivityStatus,
    ActivityType,
    ActivityStatusCode,
    PercentCompleteType,
)
from .scheduling.authoritative_schedule import (
    ActivityCalendarAssignment,
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from .scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
    RelationshipLagCalendar,
    SchedulingCalendarContext,
)
from .scheduling.constraints import ActivityConstraint, ConstraintType
from .scheduling.calendar_system import CalendarSystem
from .scheduling.relationships import Relationship, RelationshipType
from .scheduling.resource_leveling import ResourceCapacity
from .scheduling.resource_leveling_input import (
    ResourceAssignmentLevelingRef,
    ResourceCapacityRate,
    ResourceDemandInput,
    ResourceLevelingFacts,
    ResourceLevelingFactsError,
)
from .scheduling.schedule import (
    CriticalActivityPathType,
    ScheduleMode,
    ScheduleOptions,
    TotalFloatCalculationType,
)
from .scheduling.schedule_options import (
    OutOfSequenceScheduleType,
    PriorityListItem,
    PrioritySortOrder,
    StartToStartLagCalculationType,
)
from .scheduling.time_constraints import TimeActivityConstraint, TimeConstraintType
from .scheduling.time_duration import DurationUnit, LagQuantity, TimeQuantity
from .scheduling.time_forward_pass import TimeActivity, TimeRelationship


class SnapshotMaterializationError(ValueError):
    """Raised when an immutable snapshot cannot be safely materialized."""


@dataclass(frozen=True)
class MaterializedScheduleInput:
    """Calculation-ready schedule input plus the resolver registry it references."""

    schedule_input: AuthoritativeScheduleInput
    calendar_registry: CalendarResolverRegistry


def materialize_schedule_snapshot(
    snapshot: ScheduleInputSnapshot,
    calendar_registry: CalendarResolverRegistry,
) -> MaterializedScheduleInput:
    _validate_snapshot_integrity(snapshot)
    try:
        payload = json.loads(snapshot.canonical_payload)
    except json.JSONDecodeError as exc:
        raise SnapshotMaterializationError("INVALID_SNAPSHOT_JSON") from exc
    if not isinstance(payload, dict):
        raise SnapshotMaterializationError("INVALID_SNAPSHOT_PAYLOAD")
    if payload.get("relationship_lag_calendar_assignments"):
        # Older/nonstandard snapshots may carry per-relationship overrides.
        # P6 only defines a schedule-wide relationship-lag calendar option;
        # never ignore persisted nonstandard data and silently change dates.
        raise SnapshotMaterializationError(
            "PER_RELATIONSHIP_LAG_CALENDAR_NOT_SUPPORTED_BY_P6_PROFILE"
        )

    if payload.get("snapshot_id") != snapshot.snapshot_id:
        raise SnapshotMaterializationError("SNAPSHOT_ID_MISMATCH")
    if payload.get("tenant_id") != snapshot.scope.tenant_id or payload.get("project_id") != snapshot.scope.project_id:
        raise SnapshotMaterializationError("SNAPSHOT_SCOPE_MISMATCH")
    project_revision = payload.get("project_revision")
    if isinstance(project_revision, bool) or not isinstance(project_revision, int):
        raise SnapshotMaterializationError("INVALID_PROJECT_REVISION")
    if project_revision != snapshot.scope.project_revision:
        raise SnapshotMaterializationError("SNAPSHOT_REVISION_MISMATCH")

    try:
        result = _materialize_payload(payload, snapshot, calendar_registry)
    except SnapshotMaterializationError:
        raise
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise SnapshotMaterializationError("SNAPSHOT_MATERIALIZATION_FAILED") from exc
    return MaterializedScheduleInput(result, calendar_registry)


def _validate_snapshot_integrity(snapshot: ScheduleInputSnapshot) -> None:
    snapshot.validate()
    actual = hashlib.sha256(snapshot.canonical_payload.encode("utf-8")).hexdigest()
    if actual != snapshot.snapshot_hash:
        raise SnapshotMaterializationError("SNAPSHOT_HASH_MISMATCH")


def _required(payload: dict[str, Any], key: str) -> Any:
    if key not in payload:
        raise SnapshotMaterializationError(f"MISSING_SNAPSHOT_FIELD:{key}")
    return payload[key]


def _required_string(payload: dict[str, Any], key: str, error_code: str | None = None) -> str:
    value = _required(payload, key)
    if not isinstance(value, str) or not value.strip():
        raise SnapshotMaterializationError(error_code or f"INVALID_SNAPSHOT_FIELD:{key}")
    return value

def _calendar(value: Any) -> CalendarReference:
    if not isinstance(value, dict):
        raise SnapshotMaterializationError("INVALID_CALENDAR_REFERENCE")
    raw_system = value.get("system", CalendarSystem.GREGORIAN.value)
    if not isinstance(raw_system, str):
        raise SnapshotMaterializationError("INVALID_CALENDAR_SYSTEM")
    try:
        system = CalendarSystem(raw_system)
    except ValueError as exc:
        raise SnapshotMaterializationError("INVALID_CALENDAR_SYSTEM") from exc
    raw_kind = value.get("kind", "working-day")
    if not isinstance(raw_kind, str):
        raise SnapshotMaterializationError("INVALID_CALENDAR_REFERENCE")
    return CalendarReference(
        _required_string(value, "calendar_id", "INVALID_CALENDAR_REFERENCE"),
        _required_string(value, "calendar_version", "INVALID_CALENDAR_REFERENCE"),
        raw_kind,
        system,
    )


def _decimal(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise SnapshotMaterializationError("INVALID_DECIMAL") from exc
    if not result.is_finite():
        raise SnapshotMaterializationError("INVALID_DECIMAL")
    return result


def _date(value: Any) -> date:
    if not isinstance(value, str):
        raise SnapshotMaterializationError("INVALID_DATE")
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise SnapshotMaterializationError("INVALID_DATE") from exc
    return result


def _resource_leveling_facts(
    raw: Any,
    *,
    activity_ids: set[str],
) -> ResourceLevelingFacts | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise SnapshotMaterializationError("INVALID_RESOURCE_LEVELING_INPUTS")
    try:
        assignments_payload = _required(raw, "assignments")
        demands_payload = _required(raw, "demands")
        capacities_payload = _required(raw, "capacities")
        rates_payload = _required(raw, "resource_capacity_rates")
        if not all(isinstance(items, list) for items in (
            assignments_payload, demands_payload, capacities_payload, rates_payload
        )):
            raise SnapshotMaterializationError("INVALID_RESOURCE_LEVELING_INPUTS")
        assignments = tuple(
            ResourceAssignmentLevelingRef(
                assignment_id=_required_string(item, "assignment_id"),
                activity_id=_required_string(item, "activity_id"),
                resource_id=_required_string(item, "resource_id"),
                calendar_id=_required_string(item, "calendar_id"),
                calendar_version=_required_string(item, "calendar_version"),
                unit_of_measure=_required_string(item, "unit_of_measure"),
                assigned_units=(
                    _decimal(item["assigned_units"])
                    if item.get("assigned_units") is not None else None
                ),
                remaining_units=(
                    _decimal(item["remaining_units"])
                    if item.get("remaining_units") is not None else None
                ),
            )
            for item in assignments_payload
            if isinstance(item, dict)
        )
        if len(assignments) != len(assignments_payload):
            raise SnapshotMaterializationError("INVALID_RESOURCE_ASSIGNMENT")
        demands = tuple(
            ResourceDemandInput(
                assignment_id=_required_string(item, "assignment_id"),
                activity_id=_required_string(item, "activity_id"),
                resource_id=_required_string(item, "resource_id"),
                period=_date(_required(item, "period")),
                units=_decimal(_required(item, "units")),
            )
            for item in demands_payload
            if isinstance(item, dict)
        )
        if len(demands) != len(demands_payload):
            raise SnapshotMaterializationError("INVALID_RESOURCE_DEMAND")
        capacities = tuple(
            ResourceCapacity(
                resource_id=_required_string(item, "resource_id"),
                period=_date(_required(item, "period")),
                units=_decimal(_required(item, "units")),
                calendar_id=_required_string(item, "calendar_id"),
                calendar_version=_required_string(item, "calendar_version"),
                calendar_snapshot_hash=_required_string(item, "calendar_snapshot_hash"),
                calendar_work_hours=_decimal(_required(item, "calendar_work_hours")),
                resource_rate_hash=_required_string(item, "resource_rate_hash"),
                resource_rate_effective_from=_datetime(_required(item, "resource_rate_effective_from")),
            )
            for item in capacities_payload
            if isinstance(item, dict)
        )
        if len(capacities) != len(capacities_payload):
            raise SnapshotMaterializationError("INVALID_RESOURCE_CAPACITY")
        rates = tuple(
            ResourceCapacityRate(
                resource_id=_required_string(item, "resource_id"),
                effective_from=_datetime(_required(item, "effective_from")),
                max_units_per_time=_decimal(_required(item, "max_units_per_time")),
                time_period_unit=_required_string(item, "time_period_unit"),
                hours_per_time_period=_decimal(_required(item, "hours_per_time_period")),
                unit_of_measure=_required_string(item, "unit_of_measure"),
                time_period_source=_required_string(item, "time_period_source"),
                capacity_basis=_required_string(item, "capacity_basis"),
                full_time_units_per_time_period=(
                    _decimal(item["full_time_units_per_time_period"])
                    if item.get("full_time_units_per_time_period") is not None else None
                ),
                shift_id=_required_string(item, "shift_id"),
                record_revision=_strict_integer(item.get("record_revision"), "INVALID_RESOURCE_RATE_REVISION"),
            )
            for item in rates_payload
            if isinstance(item, dict)
        )
        if len(rates) != len(rates_payload):
            raise SnapshotMaterializationError("INVALID_RESOURCE_CAPACITY_RATE")
        facts = ResourceLevelingFacts(
            assignments=assignments,
            demands=demands,
            capacities=capacities,
            resource_capacity_rates=rates,
            capacity_horizon_start=_date(_required(raw, "capacity_horizon_start")),
            capacity_horizon_end=_date(_required(raw, "capacity_horizon_end")),
            calculation_timezone=_required_string(raw, "calculation_timezone"),
            schema_version=_strict_integer(raw.get("schema_version", 1), "INVALID_RESOURCE_LEVELING_SCHEMA_VERSION"),
        )
        facts.validate(activity_ids=activity_ids)
        return facts
    except SnapshotMaterializationError:
        raise
    except ResourceLevelingFactsError as exc:
        raise SnapshotMaterializationError(str(exc)) from exc
    except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
        raise SnapshotMaterializationError("INVALID_RESOURCE_LEVELING_INPUTS") from exc


def _datetime(value: Any) -> datetime:
    if not isinstance(value, str):
        raise SnapshotMaterializationError("INVALID_DATETIME")
    try:
        result = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SnapshotMaterializationError("INVALID_DATETIME") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise SnapshotMaterializationError("DATETIME_MUST_BE_TIMEZONE_AWARE")
    return result


def _duration_unit(value: Any) -> DurationUnit:
    if not isinstance(value, str):
        raise SnapshotMaterializationError("INVALID_DURATION_UNIT")
    try:
        return DurationUnit(value)
    except ValueError as exc:
        raise SnapshotMaterializationError("INVALID_DURATION_UNIT") from exc


def _finite_float(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SnapshotMaterializationError(f"INVALID_SCHEDULE_OPTION:{field_name}")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise SnapshotMaterializationError(f"INVALID_SCHEDULE_OPTION:{field_name}") from exc
    if not result == result or result in (float("inf"), float("-inf")):
        raise SnapshotMaterializationError(f"INVALID_SCHEDULE_OPTION:{field_name}")
    return result


def _strict_integer(value: Any, error_code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SnapshotMaterializationError(error_code)
    return value


def _finite_percent_complete(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SnapshotMaterializationError("INVALID_ACTIVITY_PERCENT_COMPLETE")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise SnapshotMaterializationError("INVALID_ACTIVITY_PERCENT_COMPLETE") from exc
    if not result == result or result in (float("inf"), float("-inf")):
        raise SnapshotMaterializationError("INVALID_ACTIVITY_PERCENT_COMPLETE")
    if not 0 <= result <= 100:
        raise SnapshotMaterializationError("INVALID_ACTIVITY_PERCENT_COMPLETE")
    return result


def _resource_list(raw: Any) -> tuple[str, ...] | None:
    """Decode canonical resource-ID arrays while accepting legacy comma strings.

    Legacy strings are converted only at this interchange boundary. New
    snapshots serialize the domain tuple as a JSON array and never split IDs
    that legitimately contain commas.
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        if not raw.strip():
            raise SnapshotMaterializationError("INVALID_SCHEDULE_OPTION:resource_list")
        items = [item.strip() for item in raw.split(",")]
        if any(not item for item in items):
            raise SnapshotMaterializationError("INVALID_SCHEDULE_OPTION:resource_list")
        raw = items
    if not isinstance(raw, list) or not raw:
        raise SnapshotMaterializationError("INVALID_SCHEDULE_OPTION:resource_list")
    if any(not isinstance(item, str) or not item.strip() or item != item.strip() for item in raw):
        raise SnapshotMaterializationError("INVALID_SCHEDULE_OPTION:resource_list")
    items = tuple(raw)
    if len(set(items)) != len(items):
        raise SnapshotMaterializationError("INVALID_SCHEDULE_OPTION:resource_list")
    return items


def parse_schedule_options_payload(value: Any) -> ScheduleOptions:
    """Parse explicit JSON ScheduleOptions using the canonical snapshot contract."""
    return _schedule_options(value)


def _schedule_options(value: Any) -> ScheduleOptions:
    if not isinstance(value, dict):
        raise SnapshotMaterializationError("INVALID_SCHEDULE_OPTIONS")

    def _bool(name: str, default: bool = False) -> bool:
        raw = value.get(name, default)
        if not isinstance(raw, bool):
            raise SnapshotMaterializationError(f"INVALID_SCHEDULE_OPTION:{name}")
        return raw

    def _int(name: str, default: int) -> int:
        raw = value.get(name, default)
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise SnapshotMaterializationError(f"INVALID_SCHEDULE_OPTION:{name}")
        return raw

    def _priority_sort_order(item: dict[str, Any]) -> PrioritySortOrder:
        raw = item.get("sort_order", PrioritySortOrder.ASCENDING.value)
        if not isinstance(raw, str):
            raise SnapshotMaterializationError("INVALID_SCHEDULE_OPTION:priority_list")
        try:
            return PrioritySortOrder(raw)
        except ValueError as exc:
            raise SnapshotMaterializationError(
                "INVALID_SCHEDULE_OPTION:priority_list"
            ) from exc

    try:
        priority_payload = value.get("priority_list")
        if priority_payload is None:
            priority_list = None
        else:
            if not isinstance(priority_payload, list) or not priority_payload:
                raise SnapshotMaterializationError("INVALID_SCHEDULE_OPTION:priority_list")
            priority_list = tuple(
                PriorityListItem(
                    field_name=_required_string(
                        item, "field_name", "INVALID_SCHEDULE_OPTION:priority_list"
                    ),
                    sort_order=_priority_sort_order(item),
                )
                for item in priority_payload
                if isinstance(item, dict)
            )
            if len(priority_list) != len(priority_payload):
                raise SnapshotMaterializationError("INVALID_SCHEDULE_OPTION:priority_list")

        raw_mode = value.get("mode", ScheduleMode.EARLIEST.value)
        if not isinstance(raw_mode, str):
            raise SnapshotMaterializationError("INVALID_SCHEDULE_OPTION:mode")
        return ScheduleOptions(
            mode=ScheduleMode(raw_mode),
            compute_total_float_type=TotalFloatCalculationType(
                _required_string(
                    value,
                    "compute_total_float_type",
                    "INVALID_SCHEDULE_OPTION:compute_total_float_type",
                )
                if "compute_total_float_type" in value
                else TotalFloatCalculationType.START_FLOAT.value
            ),
            critical_activity_float_threshold=_finite_float(value.get("critical_activity_float_threshold", 0), "critical_activity_float_threshold"),
            critical_activity_path_type=CriticalActivityPathType(
                _required_string(
                    value,
                    "critical_activity_path_type",
                    "INVALID_SCHEDULE_OPTION:critical_activity_path_type",
                )
                if "critical_activity_path_type" in value
                else CriticalActivityPathType.CRITICAL_FLOAT.value
            ),
            make_open_ended_activities_critical=_bool("make_open_ended_activities_critical"),
            multiple_float_paths_enabled=_bool("multiple_float_paths_enabled"),
            maximum_multiple_float_paths=_int("maximum_multiple_float_paths", 0),
            multiple_float_paths_ending_activity_object_id=value.get(
                "multiple_float_paths_ending_activity_object_id"
            ),
            multiple_float_paths_ending_activity_short_name=value.get(
                "multiple_float_paths_ending_activity_short_name"
            ),
            multiple_float_paths_use_total_float=_bool("multiple_float_paths_use_total_float", True),
            min_float_to_preserve=_int("min_float_to_preserve", 0),
            out_of_sequence_schedule_type=OutOfSequenceScheduleType(
                _required_string(
                    value,
                    "out_of_sequence_schedule_type",
                    "INVALID_SCHEDULE_OPTION:out_of_sequence_schedule_type",
                )
                if "out_of_sequence_schedule_type" in value
                else OutOfSequenceScheduleType.RETAINED_LOGIC.value
            ),
            start_to_start_lag_calculation_type=StartToStartLagCalculationType(
                _required_string(
                    value,
                    "start_to_start_lag_calculation_type",
                    "INVALID_SCHEDULE_OPTION:start_to_start_lag_calculation_type",
                )
                if "start_to_start_lag_calculation_type" in value
                else StartToStartLagCalculationType.EARLY_START.value
            ),
            relationship_lag_calendar=RelationshipLagCalendar(
                _required_string(
                    value,
                    "relationship_lag_calendar",
                    "INVALID_SCHEDULE_OPTION:relationship_lag_calendar",
                )
                if "relationship_lag_calendar" in value
                else RelationshipLagCalendar.PROJECT_DEFAULT.value
            ),
            use_expected_finish_dates=_bool("use_expected_finish_dates"),
            recalculate_resource_costs=_bool("recalculate_resource_costs"),
            calculate_float_based_on_finish_date=_bool("calculate_float_based_on_finish_date"),
            ignore_other_project_relationships=_bool("ignore_other_project_relationships"),
            include_external_res_ass=_bool("include_external_res_ass"),
            level_all_resources=_bool("level_all_resources"),
            level_within_float=_bool("level_within_float"),
            over_allocation_percentage=_finite_float(value.get("over_allocation_percentage", 0.0), "over_allocation_percentage"),
            resource_list=_resource_list(value.get("resource_list")),
            priority_list=priority_list,
            external_project_priority_limit=_int("external_project_priority_limit", 0),
            preserve_scheduled_early_and_late_dates=_bool("preserve_scheduled_early_and_late_dates"),
            data_date=_date(value["data_date"]) if value.get("data_date") is not None else None,
        )
    except SnapshotMaterializationError:
        raise
    except (TypeError, ValueError) as exc:
        raise SnapshotMaterializationError("INVALID_SCHEDULE_OPTIONS") from exc

def _materialize_payload(
    payload: dict[str, Any],
    snapshot: ScheduleInputSnapshot,
    registry: CalendarResolverRegistry,
) -> AuthoritativeScheduleInput:
    mode = AuthoritativeScheduleMode(
        _required_string(payload, "mode", "INVALID_SNAPSHOT_FIELD:mode")
    )
    project_calendar = _calendar(_required(payload, "project_calendar"))
    assignments_payload = _required(payload, "activity_calendar_assignments")
    assignment_refs: dict[str, CalendarReference] = {}
    for item in assignments_payload:
        if not isinstance(item, dict):
            raise SnapshotMaterializationError("INVALID_ACTIVITY_CALENDAR_ASSIGNMENT")
        activity_id = _required_string(item, "activity_id", "INVALID_ACTIVITY_CALENDAR_ASSIGNMENT")
        if activity_id in assignment_refs:
            raise SnapshotMaterializationError("DUPLICATE_ACTIVITY_CALENDAR_ASSIGNMENT")
        assignment_refs[activity_id] = _calendar(_required(item, "calendar"))

    activities: list[Activity | TimeActivity] = []
    for item in _required(payload, "activities"):
        if not isinstance(item, dict):
            raise SnapshotMaterializationError("INVALID_ACTIVITY")
        activity_id = _required_string(item, "id", "INVALID_ACTIVITY")
        duration_payload = item.get("duration", 0)
        if mode is AuthoritativeScheduleMode.DATE_BASED:
            if isinstance(duration_payload, bool) or not isinstance(duration_payload, int):
                raise SnapshotMaterializationError("INVALID_ACTIVITY_DURATION")
            unit = _duration_unit(item.get("duration_unit", "working-day"))
            if unit is not DurationUnit.WORKING_DAY:
                raise SnapshotMaterializationError("DATE_BASED_DURATION_MUST_BE_WORKING_DAYS")
            duration_value = Decimal(duration_payload)
        elif isinstance(duration_payload, dict):
            duration_value = _decimal(_required(duration_payload, "value"))
            unit = _duration_unit(_required(duration_payload, "unit"))
        else:
            unit = _duration_unit(item.get("duration_unit", "working-day"))
            duration_value = _decimal(duration_payload)
        actual = item.get("actual_start")
        if mode is AuthoritativeScheduleMode.DATE_BASED:
            if unit is not DurationUnit.WORKING_DAY:
                raise SnapshotMaterializationError("DATE_BASED_DURATION_MUST_BE_WORKING_DAYS")
            try:
                status = ActivityStatus(
                    item.get("status", ActivityStatus.NOT_STARTED.value)
                    if isinstance(item.get("status", ActivityStatus.NOT_STARTED.value), str)
                    else (_ for _ in ()).throw(SnapshotMaterializationError("INVALID_ACTIVITY_ENUM"))
                )
                activity_type = ActivityType(
                    item.get("activity_type", ActivityType.TASK_DEPENDENT.value)
                    if isinstance(item.get("activity_type", ActivityType.TASK_DEPENDENT.value), str)
                    else (_ for _ in ()).throw(SnapshotMaterializationError("INVALID_ACTIVITY_ENUM"))
                )
                status_code = ActivityStatusCode(
                    item.get("status_code", ActivityStatusCode.PLANNED.value)
                    if isinstance(item.get("status_code", ActivityStatusCode.PLANNED.value), str)
                    else (_ for _ in ()).throw(SnapshotMaterializationError("INVALID_ACTIVITY_ENUM"))
                )
                percent_complete_type = PercentCompleteType(
                    item.get("percent_complete_type", PercentCompleteType.DURATION.value)
                    if isinstance(item.get("percent_complete_type", PercentCompleteType.DURATION.value), str)
                    else (_ for _ in ()).throw(SnapshotMaterializationError("INVALID_ACTIVITY_ENUM"))
                )
            except ValueError as exc:
                raise SnapshotMaterializationError("INVALID_ACTIVITY_ENUM") from exc

            raw_name = item.get("name", "")
            if not isinstance(raw_name, str):
                raise SnapshotMaterializationError("INVALID_ACTIVITY_NAME")
            raw_original_duration = item.get("original_duration")
            original_duration = (
                _strict_integer(raw_original_duration, "INVALID_ACTIVITY_ORIGINAL_DURATION")
                if raw_original_duration is not None
                else None
            )
            if original_duration is not None and original_duration < 0:
                raise SnapshotMaterializationError("INVALID_ACTIVITY_ORIGINAL_DURATION")
            raw_planned_finish = item.get("planned_finish")
            planned_finish = _date(raw_planned_finish) if raw_planned_finish is not None else None
            raw_leveling_priority = item.get(
                "leveling_priority", ActivityLevelingPriority.NORMAL.value
            )
            if not isinstance(raw_leveling_priority, str):
                raise SnapshotMaterializationError("INVALID_ACTIVITY_LEVELING_PRIORITY")
            try:
                leveling_priority = ActivityLevelingPriority(raw_leveling_priority)
            except ValueError as exc:
                raise SnapshotMaterializationError(
                    "INVALID_ACTIVITY_LEVELING_PRIORITY"
                ) from exc

            activities.append(
                Activity(
                    activity_id,
                    int(duration_value),
                    _date(actual) if actual is not None else None,
                    _date(item["actual_finish"]) if item.get("actual_finish") is not None else None,
                    _strict_integer(item["remaining_duration"], "INVALID_ACTIVITY_REMAINING_DURATION") if item.get("remaining_duration") is not None else None,
                    _date(item["remaining_start"]) if item.get("remaining_start") is not None else None,
                    _finite_percent_complete(item["percent_complete"]) if item.get("percent_complete") is not None else None,
                    percent_complete_type,
                    _date(item["expected_finish"]) if item.get("expected_finish") is not None else None,
                    status,
                    activity_type,
                    status_code,
                    raw_name,
                    original_duration,
                    planned_finish,
                    leveling_priority,
                )
            )
        else:
            if unit is not DurationUnit.WORKING_HOUR:
                raise SnapshotMaterializationError("TIME_AWARE_DURATION_MUST_BE_WORKING_HOURS")
            stored_context = item.get("calendar_context")
            if stored_context is not None and not isinstance(stored_context, dict):
                raise SnapshotMaterializationError("INVALID_ACTIVITY_CALENDAR_CONTEXT")
            activity_ref = assignment_refs.get(activity_id, project_calendar)
            if isinstance(stored_context, dict) and stored_context.get("activity") is not None:
                stored_activity_ref = _calendar(stored_context["activity"])
                if activity_id in assignment_refs and stored_activity_ref != activity_ref:
                    raise SnapshotMaterializationError(
                        "CONFLICTING_ACTIVITY_CALENDAR_ASSIGNMENT"
                    )
                activity_ref = stored_activity_ref
            context = SchedulingCalendarContext(
                project=project_calendar,
                activity=activity_ref,
                relationship_lag=(
                    _calendar(stored_context["relationship_lag"])
                    if isinstance(stored_context, dict) and stored_context.get("relationship_lag") is not None
                    else None
                ),
            )
            activities.append(
                TimeActivity(
                    activity_id,
                    TimeQuantity(duration_value, unit),
                    context,
                    _datetime(actual) if actual is not None else None,
                )
            )

    relationships: list[Relationship | TimeRelationship] = []
    for item in _required(payload, "relationships"):
        if not isinstance(item, dict):
            raise SnapshotMaterializationError("INVALID_RELATIONSHIP")
        try:
            raw_type = item.get("type", RelationshipType.FS.value)
            if not isinstance(raw_type, str):
                raise SnapshotMaterializationError("INVALID_RELATIONSHIP")
            rel_type = RelationshipType(raw_type)
        except ValueError as exc:
            raise SnapshotMaterializationError("INVALID_RELATIONSHIP") from exc
        lag_payload = item.get("lag", 0)
        if mode is AuthoritativeScheduleMode.DATE_BASED:
            if isinstance(lag_payload, bool) or not isinstance(lag_payload, int):
                raise SnapshotMaterializationError("INVALID_RELATIONSHIP_LAG")
            unit = _duration_unit(item.get("lag_unit", "working-day"))
            if unit is not DurationUnit.WORKING_DAY:
                raise SnapshotMaterializationError("DATE_BASED_LAG_MUST_BE_WORKING_DAYS")
            lag_value = Decimal(lag_payload)
        elif isinstance(lag_payload, dict):
            lag_value = _decimal(_required(lag_payload, "value"))
            unit = _duration_unit(_required(lag_payload, "unit"))
        else:
            unit = _duration_unit(item.get("lag_unit", "working-day"))
            lag_value = _decimal(lag_payload)
        predecessor_id = _required_string(item, "predecessor_id", "INVALID_RELATIONSHIP")
        successor_id = _required_string(item, "successor_id", "INVALID_RELATIONSHIP")
        if mode is AuthoritativeScheduleMode.DATE_BASED:
            if unit is not DurationUnit.WORKING_DAY:
                raise SnapshotMaterializationError("DATE_BASED_LAG_MUST_BE_WORKING_DAYS")
            if lag_value != lag_value.to_integral_value():
                raise SnapshotMaterializationError("INVALID_RELATIONSHIP_LAG")
            relationships.append(
                Relationship(predecessor_id, successor_id, rel_type, int(lag_value))
            )
        else:
            relationships.append(
                TimeRelationship(
                    predecessor_id,
                    successor_id,
                    rel_type,
                    LagQuantity(lag_value, unit),
                )
            )

    if mode is AuthoritativeScheduleMode.DATE_BASED:
        constraint_items = _required(payload, "constraints")
        constraints_list: list[ActivityConstraint] = []
        for item in constraint_items:
            if not isinstance(item, dict):
                raise SnapshotMaterializationError("INVALID_CONSTRAINT")
            try:
                raw_type = _required(item, "type")
                if not isinstance(raw_type, str):
                    raise SnapshotMaterializationError("INVALID_CONSTRAINT")
                constraint_type = ConstraintType(raw_type)
            except ValueError as exc:
                raise SnapshotMaterializationError("INVALID_CONSTRAINT") from exc
            constraints_list.append(
                ActivityConstraint(
                    _required_string(item, "activity_id", "INVALID_CONSTRAINT"),
                    constraint_type,
                    _date(_required(item, "date")),
                )
            )
        constraints = tuple(constraints_list)
    else:
        constraint_items = _required(payload, "constraints")
        constraints_list: list[TimeActivityConstraint] = []
        for item in constraint_items:
            if not isinstance(item, dict):
                raise SnapshotMaterializationError("INVALID_CONSTRAINT")
            try:
                raw_type = _required(item, "type")
                if not isinstance(raw_type, str):
                    raise SnapshotMaterializationError("INVALID_CONSTRAINT")
                constraint_type = TimeConstraintType(raw_type)
            except ValueError as exc:
                raise SnapshotMaterializationError("INVALID_CONSTRAINT") from exc
            constraints_list.append(
                TimeActivityConstraint(
                    _required_string(item, "activity_id", "INVALID_CONSTRAINT"),
                    constraint_type,
                    _datetime(_required(item, "target")),
                )
            )
        constraints = tuple(constraints_list)

    relationships_tuple = tuple(relationships)
    activities_tuple = tuple(activities)
    assignments = tuple(
        ActivityCalendarAssignment(activity_id, reference)
        for activity_id, reference in sorted(assignment_refs.items())
    )
    project_start_value = _required(payload, "project_start")
    project_finish_value = payload.get("project_finish")
    raw_project_leveling_priority = payload.get("project_leveling_priority", 10)
    if (isinstance(raw_project_leveling_priority, bool) or not isinstance(raw_project_leveling_priority, int) or not 1 <= raw_project_leveling_priority <= 100):
        raise SnapshotMaterializationError("INVALID_PROJECT_LEVELING_PRIORITY")
    resource_leveling_inputs = _resource_leveling_facts(
        payload.get("resource_leveling_inputs"),
        activity_ids={activity.id for activity in activities_tuple},
    )
    return AuthoritativeScheduleInput(
        snapshot_id=snapshot.snapshot_id,
        tenant_id=snapshot.scope.tenant_id,
        project_id=snapshot.scope.project_id,
        project_revision=snapshot.scope.project_revision,
        mode=mode,
        project_calendar=project_calendar,
        activities=activities_tuple,
        relationships=relationships_tuple,
        activity_calendar_assignments=assignments,
        constraints=constraints,
        schedule_options=_schedule_options(_required(payload, "schedule_options")),
        project_start=(
            _datetime(project_start_value)
            if mode is AuthoritativeScheduleMode.TIME_AWARE
            else _date(project_start_value)
        ),
        project_finish=(
            _datetime(project_finish_value)
            if project_finish_value is not None and mode is AuthoritativeScheduleMode.TIME_AWARE
            else _date(project_finish_value)
            if project_finish_value is not None
            else None
        ),
        project_leveling_priority=raw_project_leveling_priority,
        resource_leveling_inputs=resource_leveling_inputs,
    )
