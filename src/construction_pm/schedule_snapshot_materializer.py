from __future__ import annotations

"""Materialize immutable schedule snapshots into Shared Scheduling Core models."""

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from .schedule_input_snapshot_repository import ScheduleInputSnapshot
from .scheduling.activity import Activity
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

    if payload.get("snapshot_id") != snapshot.snapshot_id:
        raise SnapshotMaterializationError("SNAPSHOT_ID_MISMATCH")
    if payload.get("tenant_id") != snapshot.scope.tenant_id or payload.get("project_id") != snapshot.scope.project_id:
        raise SnapshotMaterializationError("SNAPSHOT_SCOPE_MISMATCH")
    if payload.get("project_revision") != snapshot.scope.project_revision:
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


def _calendar(value: Any) -> CalendarReference:
    if not isinstance(value, dict):
        raise SnapshotMaterializationError("INVALID_CALENDAR_REFERENCE")
    try:
        system = CalendarSystem(str(value.get("system", CalendarSystem.GREGORIAN.value)))
    except ValueError as exc:
        raise SnapshotMaterializationError("INVALID_CALENDAR_SYSTEM") from exc
    return CalendarReference(
        str(_required(value, "calendar_id")),
        str(_required(value, "calendar_version")),
        str(value.get("kind", "working-day")),
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
    result = date.fromisoformat(value)
    return result


def _datetime(value: Any) -> datetime:
    if not isinstance(value, str):
        raise SnapshotMaterializationError("INVALID_DATETIME")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise SnapshotMaterializationError("DATETIME_MUST_BE_TIMEZONE_AWARE")
    return result


def _duration_unit(value: Any) -> DurationUnit:
    try:
        return DurationUnit(str(value))
    except ValueError as exc:
        raise SnapshotMaterializationError("INVALID_DURATION_UNIT") from exc


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

    try:
        priority_payload = value.get("priority_list")
        if priority_payload is None:
            priority_list = None
        else:
            if not isinstance(priority_payload, list) or not priority_payload:
                raise SnapshotMaterializationError("INVALID_SCHEDULE_OPTION:priority_list")
            priority_list = tuple(
                PriorityListItem(
                    field_name=str(_required(item, "field_name")),
                    sort_order=PrioritySortOrder(
                        str(item.get("sort_order", PrioritySortOrder.ASCENDING.value))
                    ),
                )
                for item in priority_payload
                if isinstance(item, dict)
            )
            if len(priority_list) != len(priority_payload):
                raise SnapshotMaterializationError("INVALID_SCHEDULE_OPTION:priority_list")

        return ScheduleOptions(
            mode=ScheduleMode(str(value.get("mode", ScheduleMode.EARLIEST.value))),
            compute_total_float_type=TotalFloatCalculationType(
                str(value.get("compute_total_float_type", TotalFloatCalculationType.START_FLOAT.value))
            ),
            critical_activity_float_threshold=float(value.get("critical_activity_float_threshold", 0)),
            critical_activity_path_type=CriticalActivityPathType(
                str(value.get("critical_activity_path_type", CriticalActivityPathType.CRITICAL_FLOAT.value))
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
                str(value.get("out_of_sequence_schedule_type", OutOfSequenceScheduleType.RETAINED_LOGIC.value))
            ),
            start_to_start_lag_calculation_type=StartToStartLagCalculationType(
                str(value.get(
                    "start_to_start_lag_calculation_type",
                    StartToStartLagCalculationType.EARLY_START.value,
                ))
            ),
            relationship_lag_calendar=RelationshipLagCalendar(
                str(value.get(
                    "relationship_lag_calendar",
                    RelationshipLagCalendar.PROJECT_DEFAULT.value,
                ))
            ),
            use_expected_finish_dates=_bool("use_expected_finish_dates"),
            calculate_float_based_on_finish_date=_bool("calculate_float_based_on_finish_date"),
            ignore_other_project_relationships=_bool("ignore_other_project_relationships"),
            include_external_res_ass=_bool("include_external_res_ass"),
            level_all_resources=_bool("level_all_resources"),
            level_within_float=_bool("level_within_float"),
            over_allocation_percentage=float(value.get("over_allocation_percentage", 0.0)),
            resource_list=value.get("resource_list"),
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
    mode = AuthoritativeScheduleMode(str(_required(payload, "mode")))
    project_calendar = _calendar(_required(payload, "project_calendar"))
    assignments_payload = _required(payload, "activity_calendar_assignments")
    assignment_refs: dict[str, CalendarReference] = {}
    for item in assignments_payload:
        if not isinstance(item, dict):
            raise SnapshotMaterializationError("INVALID_ACTIVITY_CALENDAR_ASSIGNMENT")
        activity_id = str(_required(item, "activity_id"))
        assignment_refs[activity_id] = _calendar(_required(item, "calendar"))

    activities: list[Activity | TimeActivity] = []
    for item in _required(payload, "activities"):
        if not isinstance(item, dict):
            raise SnapshotMaterializationError("INVALID_ACTIVITY")
        activity_id = str(_required(item, "id"))
        duration_payload = item.get("duration", 0)
        if isinstance(duration_payload, dict):
            duration_value = _decimal(_required(duration_payload, "value"))
            unit = _duration_unit(_required(duration_payload, "unit"))
        else:
            unit = _duration_unit(item.get("duration_unit", "working-day"))
            duration_value = _decimal(duration_payload)
        actual = item.get("actual_start")
        if mode is AuthoritativeScheduleMode.DATE_BASED:
            if unit is not DurationUnit.WORKING_DAY or duration_value != duration_value.to_integral_value():
                raise SnapshotMaterializationError("DATE_BASED_DURATION_MUST_BE_WORKING_DAYS")
            activities.append(
                Activity(activity_id, int(duration_value), _date(actual) if actual is not None else None)
            )
        else:
            if unit is not DurationUnit.WORKING_HOUR:
                raise SnapshotMaterializationError("TIME_AWARE_DURATION_MUST_BE_WORKING_HOURS")
            stored_context = item.get("calendar_context")
            if stored_context is not None and not isinstance(stored_context, dict):
                raise SnapshotMaterializationError("INVALID_ACTIVITY_CALENDAR_CONTEXT")
            activity_ref = assignment_refs.get(activity_id, project_calendar)
            if isinstance(stored_context, dict) and stored_context.get("activity") is not None:
                activity_ref = _calendar(stored_context["activity"])
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
        rel_type = RelationshipType(str(item.get("type", RelationshipType.FS.value)))
        lag_payload = item.get("lag", 0)
        if isinstance(lag_payload, dict):
            lag_value = _decimal(_required(lag_payload, "value"))
            unit = _duration_unit(_required(lag_payload, "unit"))
        else:
            unit = _duration_unit(item.get("lag_unit", "working-day"))
            lag_value = _decimal(lag_payload)
        predecessor_id = str(_required(item, "predecessor_id"))
        successor_id = str(_required(item, "successor_id"))
        if mode is AuthoritativeScheduleMode.DATE_BASED:
            if unit is not DurationUnit.WORKING_DAY or lag_value != lag_value.to_integral_value():
                raise SnapshotMaterializationError("DATE_BASED_LAG_MUST_BE_WORKING_DAYS")
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
        constraints = tuple(
            ActivityConstraint(
                str(_required(item, "activity_id")),
                ConstraintType(str(_required(item, "type"))),
                _date(_required(item, "date")),
            )
            for item in _required(payload, "constraints")
        )
    else:
        constraints = tuple(
            TimeActivityConstraint(
                str(_required(item, "activity_id")),
                TimeConstraintType(str(_required(item, "type"))),
                _datetime(_required(item, "target")),
            )
            for item in _required(payload, "constraints")
        )

    relationships_tuple = tuple(relationships)
    activities_tuple = tuple(activities)
    assignments = tuple(
        ActivityCalendarAssignment(activity_id, reference)
        for activity_id, reference in sorted(assignment_refs.items())
    )

    project_start_value = _required(payload, "project_start")
    project_finish_value = payload.get("project_finish")
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
        project_leveling_priority=payload.get("project_leveling_priority", 10),
    )
