from __future__ import annotations

"""Versioned Shared Core adapters for persisted project-domain Application APIs.

These adapters contain DTO decoding only. Validation, authorization, persistence
and domain semantics remain in the existing typed APIs and Shared Core.
"""

from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from construction_pm.application.authorization import AuthorizationContext, Permission
from construction_pm.activity_master_repository import ActivityMaster
from construction_pm.backend_p0.models import BackendScope
from construction_pm.constraint_master_repository import ConstraintMaster
from construction_pm.p6_baseline_repository import P6Baseline
from construction_pm.p6_cost_account_repository import P6CostAccount
from construction_pm.p6_expense_repository import P6Expense
from construction_pm.p6_activity_master_api import P6ActivityMasterAPI, P6_ACTIVITY_MASTER_API_VERSION
from construction_pm.p6_constraint_api import P6ConstraintAPI, P6_CONSTRAINT_API_VERSION
from construction_pm.p6_relationship_api import P6RelationshipAPI, P6_RELATIONSHIP_API_VERSION
from construction_pm.p6_wbs_master_api import P6WBSMasterAPI, P6_WBS_MASTER_API_VERSION
from construction_pm.relationship_master_repository import RelationshipMaster
from construction_pm.scheduling.activity import (
    ActivityLevelingPriority,
    ActivityStatus,
    ActivityStatusCode,
    ActivityType,
    PercentCompleteType,
)
from construction_pm.scheduling.constraints import ConstraintType
from construction_pm.scheduling.time_duration import DurationUnit
from construction_pm.scheduling.relationships import RelationshipType
from construction_pm.shared_core_runtime import SharedCoreOperation
from construction_pm.calendar_exception_repository import CalendarException
from construction_pm.calendar_work_hours_repository import CalendarWorkHourRule
from construction_pm.scheduling.calendar_system import CalendarSystem, JalaliDate
from construction_pm.p6_calendar_api import P6CalendarAPI, P6CalendarCreateRequest, P6_CALENDAR_API_VERSION
from construction_pm.p6_calendar_read_api import P6CalendarReadAPI
from construction_pm.p6_baseline_api import P6BaselineAPI, P6_BASELINE_API_VERSION
from construction_pm.p6_cost_account_api import P6CostAccountAPI, P6_COST_ACCOUNT_API_VERSION
from construction_pm.p6_expense_api import P6ExpenseAPI, P6_EXPENSE_API_VERSION
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignment,
    P6ResourceAssignmentPeriodValue,
)
from construction_pm.p6_resource_read_api import P6ResourceReadAPI, P6_RESOURCE_READ_API_VERSION
from construction_pm.p6_resource_write_api import P6ResourceWriteAPI, P6_RESOURCE_WRITE_API_VERSION
from construction_pm.p6_resource_spread_api import P6ResourceSpreadAPI, P6_RESOURCE_SPREAD_API_VERSION
from construction_pm.p6_resource_spread_repository import P6ResourceSpreadBucket
from construction_pm.p6_resource_capacity_read_api import (
    P6ResourceCapacityReadAPI,
    P6_RESOURCE_CAPACITY_READ_API_VERSION,
)
from construction_pm.p6_resource_capacity_write_api import (
    P6ResourceCapacityWriteAPI,
    P6_RESOURCE_CAPACITY_WRITE_API_VERSION,
)
from construction_pm.resources.max_units_time import ResourceCapacityBasis
from construction_pm.resources.api import ResourceAPI
from construction_pm.resources.models import (
    CostBasis,
    Resource,
    ResourceRate,
    ResourceType,
)
from construction_pm.p6_schedule_snapshot_publication_api import (
    P6ScheduleSnapshotPublicationAPI,
    P6_SCHEDULE_SNAPSHOT_API_VERSION,
    P6_PROJECT_SCHEDULE_SETTINGS_API_VERSION,
)
from construction_pm.wbs_master_repository import WBSMaster, WBSParentKind


def _mapping(value: object, code: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(code)
    return value


def _fields(
    value: object,
    *,
    required: set[str],
    allowed: set[str],
    code: str,
) -> Mapping[str, object]:
    data = _mapping(value, code)
    if set(data) - allowed or not required.issubset(data):
        raise ValueError(code)
    return data


def _record_revision(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("EXPECTED_REVISION_REQUIRED")
    return value


def _decimal(value: object, code: str) -> Decimal:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(code) from exc
    if not parsed.is_finite():
        raise ValueError(code)
    return parsed


def _date_or_datetime(value: object, code: str) -> date | datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    try:
        if "T" in value or " " in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(code) from exc


def _scope(actor: AuthorizationContext, revision: int) -> BackendScope:
    return BackendScope(actor.tenant_id, actor.project_id, revision)


def _record_result(value: object) -> dict[str, object]:
    return {"item": value}


def _list_result(value: object) -> dict[str, object]:
    if not isinstance(value, (tuple, list)):
        raise ValueError("INVALID_APPLICATION_LIST_RESPONSE")
    return {"items": list(value), "count": len(value)}


def _resource_error(value: object) -> None:
    if isinstance(value, Mapping) and isinstance(value.get("error"), Mapping):
        error = value["error"]
        code = error.get("code")
        if not isinstance(code, str) or not code.strip():
            code = "RESOURCE_MASTER_OPERATION_FAILED"
        raise ValueError(code)


def _resource_items(value: object) -> tuple[object, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError("INVALID_RESOURCE_MASTER_LIST_RESPONSE")
    for item in value:
        _resource_error(item)
    return tuple(value)

def build_project_domain_operations(
    *,
    activity_api: P6ActivityMasterAPI | None = None,
    wbs_api: P6WBSMasterAPI | None = None,
    relationship_api: P6RelationshipAPI | None = None,
    constraint_api: P6ConstraintAPI | None = None,
    calendar_api: P6CalendarAPI | None = None,
    calendar_read_api: P6CalendarReadAPI | None = None,
    schedule_snapshot_api: P6ScheduleSnapshotPublicationAPI | None = None,
    baseline_api: P6BaselineAPI | None = None,
    cost_account_api: P6CostAccountAPI | None = None,
    expense_api: P6ExpenseAPI | None = None,
    resource_read_api: P6ResourceReadAPI | None = None,
    resource_write_api: P6ResourceWriteAPI | None = None,
    resource_spread_api: P6ResourceSpreadAPI | None = None,
    resource_capacity_read_api: P6ResourceCapacityReadAPI | None = None,
    resource_capacity_write_api: P6ResourceCapacityWriteAPI | None = None,
    resource_master_api_factory: Callable[[AuthorizationContext], ResourceAPI] | None = None,
) -> dict[str, SharedCoreOperation]:
    """Build the same allow-listed CRUD ABI over server or local typed APIs."""
    operations: dict[str, SharedCoreOperation] = {}

    if wbs_api is not None:
        def wbs_list(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _list_result(wbs_api.list(_scope(actor, revision), auth_context=actor))

        def wbs_get(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                wbs_api.get(_scope(actor, revision), str(payload["wbs_id"]), auth_context=actor)
            )

        def wbs_item(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> WBSMaster:
            raw = _fields(
                payload["wbs"],
                required={"wbs_id", "parent_kind", "code", "name", "sequence_number"},
                allowed={"wbs_id", "parent_kind", "parent_wbs_id", "code", "name", "sequence_number"},
                code="INVALID_WBS_PAYLOAD",
            )
            return WBSMaster(
                scope=_scope(actor, revision),
                wbs_id=raw["wbs_id"],
                parent_kind=WBSParentKind(raw["parent_kind"]),
                parent_wbs_id=raw.get("parent_wbs_id"),
                code=raw["code"],
                name=raw["name"],
                sequence_number=raw["sequence_number"],
            )

        def wbs_create(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(wbs_api.create(wbs_item(payload, actor, revision), auth_context=actor))

        def wbs_update(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                wbs_api.update(
                    wbs_item(payload, actor, revision),
                    expected_revision=_record_revision(payload["expected_revision"]),
                    auth_context=actor,
                )
            )

        def wbs_delete(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                wbs_api.delete(
                    _scope(actor, revision),
                    str(payload["wbs_id"]),
                    expected_revision=_record_revision(payload["expected_revision"]),
                    auth_context=actor,
                )
            )

        for name, version, permission, required, allowed, handler in (
            ("wbs.list", P6_WBS_MASTER_API_VERSION, Permission.PROJECT_READ, set(), set(), wbs_list),
            ("wbs.get", P6_WBS_MASTER_API_VERSION, Permission.PROJECT_READ, {"wbs_id"}, {"wbs_id"}, wbs_get),
            ("wbs.create", P6_WBS_MASTER_API_VERSION, Permission.PROJECT_WRITE, {"wbs"}, {"wbs"}, wbs_create),
            ("wbs.update", P6_WBS_MASTER_API_VERSION, Permission.PROJECT_WRITE, {"wbs", "expected_revision"}, {"wbs", "expected_revision"}, wbs_update),
            ("wbs.delete", P6_WBS_MASTER_API_VERSION, Permission.PROJECT_WRITE, {"wbs_id", "expected_revision"}, {"wbs_id", "expected_revision"}, wbs_delete),
        ):
            operations[name] = SharedCoreOperation(
                contract_version=version,
                permission=permission,
                required_fields=frozenset(required),
                allowed_fields=frozenset(allowed),
                handler=handler,
                mutates=permission is Permission.PROJECT_WRITE,
            )

    if activity_api is not None:
        activity_fields = {
            "activity_id", "name", "duration_value", "duration_unit", "actual_start",
            "expected_finish", "actual_finish", "remaining_duration", "remaining_start",
            "percent_complete", "percent_complete_type", "planned_finish", "leveling_priority",
            "original_duration", "activity_type", "status", "status_code", "wbs_id",
        }

        def activity_item(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> ActivityMaster:
            raw = _fields(
                payload["activity"],
                required={"activity_id", "duration_value", "duration_unit"},
                allowed=activity_fields,
                code="INVALID_ACTIVITY_PAYLOAD",
            )
            percent = raw.get("percent_complete")
            if percent is not None and (
                isinstance(percent, bool) or not isinstance(percent, (int, float))
            ):
                raise ValueError("INVALID_PERCENT_COMPLETE")
            remaining = raw.get("remaining_duration")
            original = raw.get("original_duration")
            for number, code in ((remaining, "INVALID_REMAINING_DURATION"), (original, "INVALID_ORIGINAL_DURATION")):
                if number is not None and (
                    isinstance(number, bool) or not isinstance(number, int) or number < 0
                ):
                    raise ValueError(code)
            return ActivityMaster(
                scope=_scope(actor, revision),
                activity_id=raw["activity_id"],
                duration_value=_decimal(raw["duration_value"], "INVALID_DURATION_VALUE"),
                duration_unit=DurationUnit(raw["duration_unit"]),
                actual_start=_date_or_datetime(raw.get("actual_start"), "INVALID_ACTUAL_START"),
                expected_finish=_date_or_datetime(raw.get("expected_finish"), "INVALID_EXPECTED_FINISH"),
                actual_finish=_date_or_datetime(raw.get("actual_finish"), "INVALID_ACTUAL_FINISH"),
                remaining_duration=remaining,
                remaining_start=_date_or_datetime(raw.get("remaining_start"), "INVALID_REMAINING_START"),
                percent_complete=percent,
                percent_complete_type=PercentCompleteType(raw.get("percent_complete_type", PercentCompleteType.DURATION.value)),
                planned_finish=_date_or_datetime(raw.get("planned_finish"), "INVALID_PLANNED_FINISH"),
                leveling_priority=ActivityLevelingPriority(raw.get("leveling_priority", ActivityLevelingPriority.NORMAL.value)),
                original_duration=original,
                name=raw.get("name", ""),
                activity_type=ActivityType(raw.get("activity_type", ActivityType.TASK_DEPENDENT.value)),
                status=ActivityStatus(raw.get("status", ActivityStatus.NOT_STARTED.value)),
                status_code=ActivityStatusCode(raw.get("status_code", ActivityStatusCode.PLANNED.value)),
                wbs_id=raw.get("wbs_id"),
            )

        def activity_list(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _list_result(activity_api.list(_scope(actor, revision), auth_context=actor))

        def activity_get(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                activity_api.get(_scope(actor, revision), str(payload["activity_id"]), auth_context=actor)
            )

        def activity_create(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(activity_api.create(activity_item(payload, actor, revision), auth_context=actor))

        def activity_update(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                activity_api.update(
                    activity_item(payload, actor, revision),
                    expected_revision=_record_revision(payload["expected_revision"]),
                    auth_context=actor,
                )
            )

        for name, permission, required, allowed, handler in (
            ("activity.list", Permission.PROJECT_READ, set(), set(), activity_list),
            ("activity.get", Permission.PROJECT_READ, {"activity_id"}, {"activity_id"}, activity_get),
            ("activity.create", Permission.PROJECT_WRITE, {"activity"}, {"activity"}, activity_create),
            ("activity.update", Permission.PROJECT_WRITE, {"activity", "expected_revision"}, {"activity", "expected_revision"}, activity_update),
        ):
            operations[name] = SharedCoreOperation(
                contract_version=P6_ACTIVITY_MASTER_API_VERSION,
                permission=permission,
                required_fields=frozenset(required),
                allowed_fields=frozenset(allowed),
                handler=handler,
                mutates=permission is Permission.PROJECT_WRITE,
            )

    if relationship_api is not None:
        def relationship_item(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> RelationshipMaster:
            raw = _fields(
                payload["relationship"],
                required={"relationship_id", "predecessor_id", "successor_id"},
                allowed={"relationship_id", "predecessor_id", "successor_id", "relationship_type", "lag_value", "lag_unit"},
                code="INVALID_RELATIONSHIP_PAYLOAD",
            )
            return RelationshipMaster(
                scope=_scope(actor, revision),
                relationship_id=raw["relationship_id"],
                predecessor_id=raw["predecessor_id"],
                successor_id=raw["successor_id"],
                relationship_type=RelationshipType(raw.get("relationship_type", RelationshipType.FS.value)),
                lag_value=_decimal(raw.get("lag_value", "0"), "INVALID_LAG_VALUE"),
                lag_unit=DurationUnit(raw.get("lag_unit", DurationUnit.WORKING_DAY.value)),
            )

        def relationship_list(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _list_result(relationship_api.list(_scope(actor, revision), auth_context=actor))

        def relationship_get(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                relationship_api.get(_scope(actor, revision), str(payload["relationship_id"]), auth_context=actor)
            )

        def relationship_create(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(relationship_api.create(relationship_item(payload, actor, revision), auth_context=actor))

        def relationship_update(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                relationship_api.update(
                    relationship_item(payload, actor, revision),
                    expected_revision=_record_revision(payload["expected_revision"]),
                    auth_context=actor,
                )
            )

        def relationship_delete(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                relationship_api.delete(
                    _scope(actor, revision),
                    str(payload["relationship_id"]),
                    expected_revision=_record_revision(payload["expected_revision"]),
                    auth_context=actor,
                )
            )

        for name, permission, required, allowed, handler in (
            ("relationship.list", Permission.PROJECT_READ, set(), set(), relationship_list),
            ("relationship.get", Permission.PROJECT_READ, {"relationship_id"}, {"relationship_id"}, relationship_get),
            ("relationship.create", Permission.PROJECT_WRITE, {"relationship"}, {"relationship"}, relationship_create),
            ("relationship.update", Permission.PROJECT_WRITE, {"relationship", "expected_revision"}, {"relationship", "expected_revision"}, relationship_update),
            ("relationship.delete", Permission.PROJECT_WRITE, {"relationship_id", "expected_revision"}, {"relationship_id", "expected_revision"}, relationship_delete),
        ):
            operations[name] = SharedCoreOperation(
                contract_version=P6_RELATIONSHIP_API_VERSION,
                permission=permission,
                required_fields=frozenset(required),
                allowed_fields=frozenset(allowed),
                handler=handler,
                mutates=permission is Permission.PROJECT_WRITE,
            )

    if constraint_api is not None:
        def constraint_item(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> ConstraintMaster:
            raw = _fields(
                payload["constraint"],
                required={"constraint_id", "activity_id", "constraint_type", "constraint_date"},
                allowed={"constraint_id", "activity_id", "constraint_type", "constraint_date"},
                code="INVALID_CONSTRAINT_PAYLOAD",
            )
            raw_date = raw["constraint_date"]
            if not isinstance(raw_date, str):
                raise ValueError("INVALID_CONSTRAINT_DATE")
            try:
                constraint_date = date.fromisoformat(raw_date)
            except ValueError as exc:
                raise ValueError("INVALID_CONSTRAINT_DATE") from exc
            return ConstraintMaster(
                scope=_scope(actor, revision),
                constraint_id=raw["constraint_id"],
                activity_id=raw["activity_id"],
                constraint_type=ConstraintType(raw["constraint_type"]),
                constraint_date=constraint_date,
            )

        def constraint_list(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _list_result(constraint_api.list(_scope(actor, revision), auth_context=actor))

        def constraint_get(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                constraint_api.get(_scope(actor, revision), str(payload["constraint_id"]), auth_context=actor)
            )

        def constraint_create(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(constraint_api.create(constraint_item(payload, actor, revision), auth_context=actor))

        def constraint_update(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                constraint_api.update(
                    constraint_item(payload, actor, revision),
                    expected_revision=_record_revision(payload["expected_revision"]),
                    auth_context=actor,
                )
            )

        for name, permission, required, allowed, handler in (
            ("constraint.list", Permission.PROJECT_READ, set(), set(), constraint_list),
            ("constraint.get", Permission.PROJECT_READ, {"constraint_id"}, {"constraint_id"}, constraint_get),
            ("constraint.create", Permission.PROJECT_WRITE, {"constraint"}, {"constraint"}, constraint_create),
            ("constraint.update", Permission.PROJECT_WRITE, {"constraint", "expected_revision"}, {"constraint", "expected_revision"}, constraint_update),
        ):
            operations[name] = SharedCoreOperation(
                contract_version=P6_CONSTRAINT_API_VERSION,
                permission=permission,
                required_fields=frozenset(required),
                allowed_fields=frozenset(allowed),
                handler=handler,
                mutates=permission is Permission.PROJECT_WRITE,
            )


    if calendar_api is not None:
        def calendar_list(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return calendar_api.list(_scope(actor, revision), auth_context=actor)

        def calendar_get(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                calendar_api.get(
                    _scope(actor, revision),
                    str(payload["calendar_id"]),
                    str(payload["calendar_version"]),
                    auth_context=actor,
                )
            )

        def calendar_create_or_update_request(payload: Mapping[str, object]) -> P6CalendarCreateRequest:
            raw = _fields(
                payload["calendar"],
                required={"calendar_id", "calendar_version", "calendar_type", "kind", "name"},
                allowed={
                    "calendar_id", "calendar_version", "calendar_type", "kind", "name",
                    "base_calendar_id", "base_calendar_version", "expected_revision",
                },
                code="INVALID_CALENDAR_PAYLOAD",
            )
            expected = raw.get("expected_revision")
            if expected is not None and (
                isinstance(expected, bool) or not isinstance(expected, int) or expected < 0
            ):
                raise ValueError("INVALID_EXPECTED_REVISION")
            return P6CalendarCreateRequest(
                contract_version=P6_CALENDAR_API_VERSION,
                calendar_id=raw["calendar_id"],
                calendar_version=raw["calendar_version"],
                calendar_type=raw["calendar_type"],
                kind=raw["kind"],
                name=raw["name"],
                expected_revision=expected,
                base_calendar_id=raw.get("base_calendar_id"),
                base_calendar_version=raw.get("base_calendar_version"),
            )

        def calendar_create(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                calendar_api.create(
                    _scope(actor, revision),
                    calendar_create_or_update_request(payload),
                    auth_context=actor,
                )
            )

        def calendar_update(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                calendar_api.update(
                    _scope(actor, revision),
                    calendar_create_or_update_request(payload),
                    auth_context=actor,
                )
            )

        def calendar_delete(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result({
                "deleted": calendar_api.delete(
                    _scope(actor, revision),
                    str(payload["calendar_id"]),
                    str(payload["calendar_version"]),
                    expected_revision=_record_revision(payload["expected_revision"]),
                    auth_context=actor,
                )
            })

        for name, permission, required, allowed, handler in (
            ("calendar.list", Permission.PROJECT_READ, set(), set(), calendar_list),
            ("calendar.get", Permission.PROJECT_READ, {"calendar_id", "calendar_version"}, {"calendar_id", "calendar_version"}, calendar_get),
            ("calendar.create", Permission.PROJECT_WRITE, {"calendar"}, {"calendar"}, calendar_create),
            ("calendar.update", Permission.PROJECT_WRITE, {"calendar"}, {"calendar"}, calendar_update),
            ("calendar.delete", Permission.PROJECT_WRITE, {"calendar_id", "calendar_version", "expected_revision"}, {"calendar_id", "calendar_version", "expected_revision"}, calendar_delete),
        ):
            operations[name] = SharedCoreOperation(
                contract_version=P6_CALENDAR_API_VERSION,
                permission=permission,
                required_fields=frozenset(required),
                allowed_fields=frozenset(allowed),
                handler=handler,
                mutates=permission is Permission.PROJECT_WRITE,
            )


        def calendar_copy(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            raw = _fields(
                payload["copy"],
                required={
                    "source_calendar_id", "source_calendar_version",
                    "target_calendar_id", "target_calendar_version",
                },
                allowed={
                    "source_calendar_id", "source_calendar_version",
                    "target_calendar_id", "target_calendar_version",
                },
                code="INVALID_CALENDAR_COPY_PAYLOAD",
            )
            return _record_result(
                calendar_api.copy(
                    _scope(actor, revision),
                    str(raw["source_calendar_id"]),
                    str(raw["source_calendar_version"]),
                    str(raw["target_calendar_id"]),
                    str(raw["target_calendar_version"]),
                    auth_context=actor,
                )
            )

        def calendar_replace(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            raw = _fields(
                payload["replace"],
                required={
                    "target_calendar_id", "target_calendar_version",
                    "source_calendar_id", "source_calendar_version",
                },
                allowed={
                    "target_calendar_id", "target_calendar_version",
                    "source_calendar_id", "source_calendar_version",
                },
                code="INVALID_CALENDAR_REPLACE_PAYLOAD",
            )
            return _record_result(
                calendar_api.replace(
                    _scope(actor, revision),
                    str(raw["target_calendar_id"]),
                    str(raw["target_calendar_version"]),
                    str(raw["source_calendar_id"]),
                    str(raw["source_calendar_version"]),
                    auth_context=actor,
                )
            )

        def calendar_exception_save(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            raw = _fields(
                payload["exception"],
                required={"calendar_id", "calendar_version", "exception_date", "mode"},
                allowed={
                    "calendar_id", "calendar_version", "exception_date", "mode",
                    "system", "total_work_hours", "intervals",
                },
                code="INVALID_CALENDAR_EXCEPTION_PAYLOAD",
            )
            raw_date = raw["exception_date"]
            if not isinstance(raw_date, str):
                raise ValueError("INVALID_EXCEPTION_DATE")
            try:
                system = CalendarSystem(raw.get("system", CalendarSystem.GREGORIAN.value))
                if system is CalendarSystem.JALALI:
                    parts = raw_date.replace("/", "-").split("-")
                    if len(parts) != 3:
                        raise ValueError("INVALID_EXCEPTION_DATE")
                    exception_date: date | JalaliDate = JalaliDate(*(int(part) for part in parts))
                else:
                    exception_date = date.fromisoformat(raw_date)
            except (TypeError, ValueError) as exc:
                raise ValueError("INVALID_EXCEPTION_DATE") from exc
            raw_intervals = raw.get("intervals", [])
            if not isinstance(raw_intervals, list):
                raise ValueError("INVALID_EXCEPTION_INTERVALS")
            intervals: list[tuple[time, time]] = []
            for pair in raw_intervals:
                if (
                    not isinstance(pair, list) or len(pair) != 2
                    or any(not isinstance(item, str) for item in pair)
                ):
                    raise ValueError("INVALID_EXCEPTION_INTERVALS")
                try:
                    intervals.append((time.fromisoformat(pair[0]), time.fromisoformat(pair[1])))
                except ValueError as exc:
                    raise ValueError("INVALID_EXCEPTION_INTERVALS") from exc
            total = raw.get("total_work_hours")
            exception = CalendarException(
                scope=_scope(actor, revision),
                calendar_id=raw["calendar_id"],
                calendar_version=raw["calendar_version"],
                exception_date=exception_date,
                mode=raw["mode"],
                total_work_hours=None if total is None else _decimal(total, "INVALID_EXCEPTION_TOTAL_WORK_HOURS"),
                intervals=tuple(intervals),
                system=system,
            )
            return _record_result(calendar_api.save_exception(exception, auth_context=actor))

        for name, required, allowed, handler in (
            ("calendar.copy", {"copy"}, {"copy"}, calendar_copy),
            ("calendar.replace", {"replace"}, {"replace"}, calendar_replace),
            ("calendar.exception.save", {"exception"}, {"exception"}, calendar_exception_save),
        ):
            operations[name] = SharedCoreOperation(
                contract_version=P6_CALENDAR_API_VERSION,
                permission=Permission.PROJECT_WRITE,
                required_fields=frozenset(required),
                allowed_fields=frozenset(allowed),
                handler=handler,
                mutates=True,
            )

        def calendar_exception_list(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _list_result(
                calendar_api.list_exceptions(
                    _scope(actor, revision),
                    str(payload["calendar_id"]),
                    str(payload["calendar_version"]),
                    auth_context=actor,
                )
            )

        operations["calendar.exception_list"] = SharedCoreOperation(
            contract_version=P6_CALENDAR_API_VERSION,
            permission=Permission.PROJECT_READ,
            required_fields=frozenset({"calendar_id", "calendar_version"}),
            allowed_fields=frozenset({"calendar_id", "calendar_version"}),
            handler=calendar_exception_list,
        )

        def calendar_work_hours_list(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            kind = payload["kind"]
            if not isinstance(kind, str):
                raise ValueError("INVALID_WORK_HOUR_KIND")
            return _list_result(
                calendar_api.list_work_hours(
                    _scope(actor, revision),
                    str(payload["calendar_id"]),
                    str(payload["calendar_version"]),
                    kind,
                    auth_context=actor,
                )
            )

        def calendar_work_hours_save(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            raw = _fields(
                payload["rule"],
                required={"calendar_id", "calendar_version", "kind"},
                allowed={
                    "calendar_id", "calendar_version", "kind", "weekday",
                    "is_working_day", "total_work_hours", "intervals",
                },
                code="INVALID_WORK_HOUR_PAYLOAD",
            )
            raw_intervals = raw.get("intervals", [])
            if not isinstance(raw_intervals, list):
                raise ValueError("INVALID_WORK_HOUR_INTERVALS")
            intervals: list[tuple[str, str]] = []
            for pair in raw_intervals:
                if (
                    not isinstance(pair, list)
                    or len(pair) != 2
                    or any(not isinstance(item, str) for item in pair)
                ):
                    raise ValueError("INVALID_WORK_HOUR_INTERVALS")
                intervals.append((pair[0], pair[1]))
            total = raw.get("total_work_hours")
            return _record_result(
                calendar_api.save_work_hours(
                    CalendarWorkHourRule(
                        scope=_scope(actor, revision),
                        calendar_id=raw["calendar_id"],
                        calendar_version=raw["calendar_version"],
                        kind=raw["kind"],
                        weekday=raw.get("weekday"),
                        is_working_day=raw.get("is_working_day"),
                        total_work_hours=None if total is None else _decimal(total, "INVALID_TOTAL_WORK_HOURS"),
                        intervals=tuple(intervals),
                    ),
                    auth_context=actor,
                )
            )

        operations["calendar.work_hours.list"] = SharedCoreOperation(
            contract_version=P6_CALENDAR_API_VERSION,
            permission=Permission.PROJECT_READ,
            required_fields=frozenset({"calendar_id", "calendar_version", "kind"}),
            allowed_fields=frozenset({"calendar_id", "calendar_version", "kind"}),
            handler=calendar_work_hours_list,
        )
        operations["calendar.work_hours.save"] = SharedCoreOperation(
            contract_version=P6_CALENDAR_API_VERSION,
            permission=Permission.PROJECT_WRITE,
            required_fields=frozenset({"rule"}),
            allowed_fields=frozenset({"rule"}),
            handler=calendar_work_hours_save,
            mutates=True,
        )

    if calendar_read_api is not None:
        from construction_pm.p6_calendar_read_api import P6_CALENDAR_READ_API_VERSION

        def calendar_snapshot_get(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                calendar_read_api.get_snapshot(
                    _scope(actor, revision),
                    str(payload["calendar_id"]),
                    str(payload["calendar_version"]),
                    auth_context=actor,
                )
            )

        operations["calendar.snapshot_get"] = SharedCoreOperation(
            contract_version=P6_CALENDAR_READ_API_VERSION,
            permission=Permission.PROJECT_READ,
            required_fields=frozenset({"calendar_id", "calendar_version"}),
            allowed_fields=frozenset({"calendar_id", "calendar_version"}),
            handler=calendar_snapshot_get,
        )


    if schedule_snapshot_api is not None:
        def schedule_settings_get(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                schedule_snapshot_api.get_settings(
                    _scope(actor, revision),
                    auth_context=actor,
                )
            )

        def schedule_publish(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            timezone_name = payload["timezone_name"]
            if not isinstance(timezone_name, str) or not timezone_name.strip():
                raise ValueError("TIMEZONE_REQUIRED")
            request_id = payload.get("request_id")
            idempotency_key = payload.get("idempotency_key")
            if request_id is not None and not isinstance(request_id, str):
                raise ValueError("INVALID_REQUEST_ID")
            if idempotency_key is not None and not isinstance(idempotency_key, str):
                raise ValueError("INVALID_IDEMPOTENCY_KEY")
            return _record_result(
                schedule_snapshot_api.publish(
                    _scope(actor, revision),
                    timezone_name=timezone_name,
                    auth_context=actor,
                    request_id=request_id,
                    idempotency_key=idempotency_key,
                )
            )

        operations["schedule.settings.get"] = SharedCoreOperation(
            contract_version=P6_PROJECT_SCHEDULE_SETTINGS_API_VERSION,
            permission=Permission.PROJECT_SCHEDULE,
            required_fields=frozenset(),
            allowed_fields=frozenset(),
            handler=schedule_settings_get,
        )
        operations["schedule.publish"] = SharedCoreOperation(
            contract_version=P6_SCHEDULE_SNAPSHOT_API_VERSION,
            permission=Permission.PROJECT_SCHEDULE,
            required_fields=frozenset({"timezone_name"}),
            allowed_fields=frozenset({"timezone_name", "request_id", "idempotency_key"}),
            handler=schedule_publish,
            mutates=True,
        )


    if baseline_api is not None:
        def baseline_list(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _list_result(baseline_api.list(_scope(actor, revision), auth_context=actor))

        def baseline_get(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                baseline_api.get(_scope(actor, revision), str(payload["baseline_id"]), auth_context=actor)
            )

        def baseline_create(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            raw = _fields(
                payload["baseline"],
                required={"baseline_id", "name", "baseline_type", "source_revision", "created_at"},
                allowed={"baseline_id", "name", "baseline_type", "source_revision", "created_at", "notes"},
                code="INVALID_BASELINE_PAYLOAD",
            )
            source_revision = raw["source_revision"]
            if isinstance(source_revision, bool) or not isinstance(source_revision, int) or source_revision < 0:
                raise ValueError("INVALID_SOURCE_REVISION")
            return _record_result(
                baseline_api.create(
                    P6Baseline(
                        scope=_scope(actor, revision),
                        baseline_id=raw["baseline_id"],
                        name=raw["name"],
                        baseline_type=raw["baseline_type"],
                        source_revision=source_revision,
                        created_at=raw["created_at"],
                        notes=raw.get("notes"),
                    ),
                    auth_context=actor,
                )
            )

        for name, permission, required, allowed, handler in (
            ("baseline.list", Permission.PROJECT_READ, set(), set(), baseline_list),
            ("baseline.get", Permission.PROJECT_READ, {"baseline_id"}, {"baseline_id"}, baseline_get),
            ("baseline.create", Permission.PROJECT_WRITE, {"baseline"}, {"baseline"}, baseline_create),
        ):
            operations[name] = SharedCoreOperation(
                contract_version=P6_BASELINE_API_VERSION,
                permission=permission,
                required_fields=frozenset(required),
                allowed_fields=frozenset(allowed),
                handler=handler,
                mutates=permission is Permission.PROJECT_WRITE,
            )

    if cost_account_api is not None:
        def cost_account_list(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _list_result(cost_account_api.list(_scope(actor, revision), auth_context=actor))

        def cost_account_get(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                cost_account_api.get(_scope(actor, revision), str(payload["account_id"]), auth_context=actor)
            )

        def cost_account_create(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            raw = _fields(
                payload["cost_account"],
                required={"account_id", "name"},
                allowed={"account_id", "name", "parent_account_id", "description"},
                code="INVALID_COST_ACCOUNT_PAYLOAD",
            )
            return _record_result(
                cost_account_api.create(
                    P6CostAccount(
                        scope=_scope(actor, revision),
                        account_id=raw["account_id"],
                        name=raw["name"],
                        parent_account_id=raw.get("parent_account_id"),
                        description=raw.get("description"),
                    ),
                    auth_context=actor,
                )
            )

        for name, permission, required, allowed, handler in (
            ("cost_account.list", Permission.PROJECT_READ, set(), set(), cost_account_list),
            ("cost_account.get", Permission.PROJECT_READ, {"account_id"}, {"account_id"}, cost_account_get),
            ("cost_account.create", Permission.PROJECT_WRITE, {"cost_account"}, {"cost_account"}, cost_account_create),
        ):
            operations[name] = SharedCoreOperation(
                contract_version=P6_COST_ACCOUNT_API_VERSION,
                permission=permission,
                required_fields=frozenset(required),
                allowed_fields=frozenset(allowed),
                handler=handler,
                mutates=permission is Permission.PROJECT_WRITE,
            )

    if expense_api is not None:
        def expense_list(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            activity_id = payload.get("activity_id")
            wbs_id = payload.get("wbs_id")
            if activity_id is not None and not isinstance(activity_id, str):
                raise ValueError("INVALID_ACTIVITY_ID")
            if wbs_id is not None and not isinstance(wbs_id, str):
                raise ValueError("INVALID_WBS_ID")
            return _list_result(
                expense_api.list(
                    _scope(actor, revision),
                    activity_id=activity_id,
                    wbs_id=wbs_id,
                    auth_context=actor,
                )
            )

        def expense_get(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                expense_api.get(_scope(actor, revision), str(payload["expense_id"]), auth_context=actor)
            )

        def expense_create(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            raw = _fields(
                payload["expense"],
                required={"expense_id", "name", "category"},
                allowed={
                    "expense_id", "name", "category", "activity_id", "wbs_id",
                    "expense_date", "planned_cost", "actual_cost", "remaining_cost",
                    "currency", "note",
                },
                code="INVALID_EXPENSE_PAYLOAD",
            )
            return _record_result(
                expense_api.create(
                    P6Expense(
                        scope=_scope(actor, revision),
                        expense_id=raw["expense_id"],
                        name=raw["name"],
                        category=raw["category"],
                        activity_id=raw.get("activity_id"),
                        wbs_id=raw.get("wbs_id"),
                        expense_date=raw.get("expense_date"),
                        planned_cost=None if raw.get("planned_cost") is None else _decimal(raw["planned_cost"], "INVALID_PLANNED_COST"),
                        actual_cost=None if raw.get("actual_cost") is None else _decimal(raw["actual_cost"], "INVALID_ACTUAL_COST"),
                        remaining_cost=None if raw.get("remaining_cost") is None else _decimal(raw["remaining_cost"], "INVALID_REMAINING_COST"),
                        currency=raw.get("currency"),
                        note=raw.get("note"),
                    ),
                    auth_context=actor,
                )
            )

        for name, permission, required, allowed, handler in (
            ("expense.list", Permission.PROJECT_READ, set(), {"activity_id", "wbs_id"}, expense_list),
            ("expense.get", Permission.PROJECT_READ, {"expense_id"}, {"expense_id"}, expense_get),
            ("expense.create", Permission.PROJECT_WRITE, {"expense"}, {"expense"}, expense_create),
        ):
            operations[name] = SharedCoreOperation(
                contract_version=P6_EXPENSE_API_VERSION,
                permission=permission,
                required_fields=frozenset(required),
                allowed_fields=frozenset(allowed),
                handler=handler,
                mutates=permission is Permission.PROJECT_WRITE,
            )



    if resource_master_api_factory is not None:
        from datetime import date as _date

        def resource_master_list(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            api = resource_master_api_factory(actor)
            return _list_result(_resource_items(api.list_resources()))

        def resource_master_get(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            api = resource_master_api_factory(actor)
            result = api.get_resource(str(payload["resource_id"]))
            _resource_error(result)
            return _record_result(result)

        def resource_master_save(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            raw = _fields(
                payload["resource"],
                required={"id", "code", "name", "type", "unit"},
                allowed={"id", "code", "name", "type", "unit", "calendar_id", "active", "rates"},
                code="INVALID_RESOURCE_MASTER_PAYLOAD",
            )
            active = raw.get("active", True)
            if not isinstance(active, bool):
                raise ValueError("INVALID_RESOURCE_ACTIVE_FLAG")
            raw_rates = raw.get("rates", [])
            if not isinstance(raw_rates, list):
                raise ValueError("INVALID_RESOURCE_RATES")
            rates: list[ResourceRate] = []
            for raw_rate in raw_rates:
                rate = _fields(
                    raw_rate,
                    required={"rate", "basis"},
                    allowed={"rate", "basis", "currency", "effective_from", "effective_to", "version"},
                    code="INVALID_RESOURCE_RATE",
                )
                effective_from = rate.get("effective_from")
                effective_to = rate.get("effective_to")
                try:
                    start_date = None if effective_from is None else _date.fromisoformat(str(effective_from))
                    end_date = None if effective_to is None else _date.fromisoformat(str(effective_to))
                except ValueError as exc:
                    raise ValueError("INVALID_RESOURCE_RATE_DATE") from exc
                version = rate.get("version", 1)
                if isinstance(version, bool) or not isinstance(version, int) or version < 1:
                    raise ValueError("INVALID_RESOURCE_RATE_VERSION")
                rates.append(
                    ResourceRate(
                        rate=_decimal(rate["rate"], "INVALID_RESOURCE_RATE_VALUE"),
                        basis=CostBasis(rate["basis"]),
                        currency=rate.get("currency", "USD"),
                        effective_from=start_date,
                        effective_to=end_date,
                        version=version,
                    )
                )
            resource = Resource(
                id=raw["id"],
                code=raw["code"],
                name=raw["name"],
                resource_type=ResourceType(raw["type"]),
                unit=raw["unit"],
                calendar_id=raw.get("calendar_id"),
                active=active,
                rates=tuple(rates),
            )
            expected = payload.get("expected_revision")
            if expected is not None and (
                isinstance(expected, bool) or not isinstance(expected, int) or expected < 1
            ):
                raise ValueError("INVALID_RESOURCE_EXPECTED_REVISION")
            idempotency_key = payload.get("idempotency_key")
            if idempotency_key is not None and (
                not isinstance(idempotency_key, str) or not idempotency_key.strip()
            ):
                raise ValueError("INVALID_RESOURCE_IDEMPOTENCY_KEY")
            result = resource_master_api_factory(actor).create_resource(
                resource,
                expected_revision=expected,
                idempotency_key=idempotency_key,
            )
            if isinstance(result, Mapping) and isinstance(result.get("error"), Mapping):
                error = result["error"]
                code = error.get("code")
                raise ValueError(code if isinstance(code, str) else "RESOURCE_MASTER_OPERATION_FAILED")
            return _record_result(result)

        for name, required, allowed, handler in (
            ("resource.master.list", set(), set(), resource_master_list),
            ("resource.master.get", {"resource_id"}, {"resource_id"}, resource_master_get),
            ("resource.master.save", {"resource"}, {"resource", "expected_revision", "idempotency_key"}, resource_master_save),
        ):
            operations[name] = SharedCoreOperation(
                contract_version="resource.v1",
                permission=Permission.PROJECT_READ if name != "resource.master.save" else Permission.PROJECT_WRITE,
                required_fields=frozenset(required),
                allowed_fields=frozenset(allowed),
                handler=handler,
                mutates=name == "resource.master.save",
            )

    if resource_read_api is not None:
        def assignment_list(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            activity_id = payload.get("activity_id")
            resource_id = payload.get("resource_id")
            if activity_id is not None and not isinstance(activity_id, str):
                raise ValueError("INVALID_ACTIVITY_ID")
            if resource_id is not None and not isinstance(resource_id, str):
                raise ValueError("INVALID_RESOURCE_ID")
            return _list_result(
                resource_read_api.list_assignments(
                    _scope(actor, revision),
                    activity_id=activity_id,
                    resource_id=resource_id,
                    auth_context=actor,
                )
            )

        def assignment_get(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                resource_read_api.get_assignment(
                    _scope(actor, revision),
                    str(payload["assignment_id"]),
                    auth_context=actor,
                )
            )

        def assignment_period_list(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            assignment_id = payload.get("assignment_id")
            if assignment_id is not None and not isinstance(assignment_id, str):
                raise ValueError("INVALID_ASSIGNMENT_ID")
            return _list_result(
                resource_read_api.list_assignment_periods(
                    _scope(actor, revision),
                    assignment_id=assignment_id,
                    auth_context=actor,
                )
            )

        def assignment_period_get(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                resource_read_api.get_assignment_period(
                    _scope(actor, revision),
                    str(payload["assignment_id"]),
                    str(payload["period_start"]),
                    auth_context=actor,
                )
            )

        for name, required, allowed, handler in (
            ("resource_assignment.list", set(), {"activity_id", "resource_id"}, assignment_list),
            ("resource_assignment.get", {"assignment_id"}, {"assignment_id"}, assignment_get),
            ("resource_assignment_period.list", set(), {"assignment_id"}, assignment_period_list),
            ("resource_assignment_period.get", {"assignment_id", "period_start"}, {"assignment_id", "period_start"}, assignment_period_get),
        ):
            operations[name] = SharedCoreOperation(
                contract_version=P6_RESOURCE_READ_API_VERSION,
                permission=Permission.PROJECT_READ,
                required_fields=frozenset(required),
                allowed_fields=frozenset(allowed),
                handler=handler,
            )

    def require_registered_resource(actor: AuthorizationContext, resource_id: object) -> None:
        if resource_master_api_factory is None:
            raise ValueError("RESOURCE_MASTER_CONTEXT_REQUIRED")
        if not isinstance(resource_id, str) or not resource_id.strip():
            raise ValueError("INVALID_RESOURCE_ID")
        result = resource_master_api_factory(actor).get_resource(resource_id)
        _resource_error(result)
        if result is None:
            raise ValueError("RESOURCE_NOT_FOUND")

    if resource_write_api is not None:
        def assignment_create(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            raw = _fields(
                payload["assignment"],
                required={"assignment_id", "activity_id", "resource_id"},
                allowed={
                    "assignment_id", "activity_id", "resource_id", "role_id",
                    "units", "actual_units", "remaining_units", "planned_cost",
                    "actual_cost", "remaining_cost", "unit", "currency",
                    "calendar_id", "calendar_version", "note", "is_driving",
                    "units_per_time", "units_per_time_period", "hours_per_units_time_period",
                },
                code="INVALID_RESOURCE_ASSIGNMENT_PAYLOAD",
            )
            decimal_names = (
                "units", "actual_units", "remaining_units", "planned_cost",
                "actual_cost", "remaining_cost", "units_per_time",
                "hours_per_units_time_period",
            )
            require_registered_resource(actor, raw["resource_id"])
            values = {
                name: None if raw.get(name) is None else _decimal(raw[name], f"INVALID_{name.upper()}")
                for name in decimal_names
            }
            is_driving = raw.get("is_driving")
            if is_driving is not None and not isinstance(is_driving, bool):
                raise ValueError("INVALID_IS_DRIVING")
            assignment = P6ResourceAssignment(
                scope=_scope(actor, revision),
                assignment_id=raw["assignment_id"],
                activity_id=raw["activity_id"],
                resource_id=raw["resource_id"],
                role_id=raw.get("role_id"),
                units=values["units"],
                actual_units=values["actual_units"],
                remaining_units=values["remaining_units"],
                planned_cost=values["planned_cost"],
                actual_cost=values["actual_cost"],
                remaining_cost=values["remaining_cost"],
                unit=raw.get("unit"),
                currency=raw.get("currency"),
                calendar_id=raw.get("calendar_id"),
                note=raw.get("note"),
                calendar_version=raw.get("calendar_version"),
                is_driving=is_driving,
                units_per_time=values["units_per_time"],
                units_per_time_period=raw.get("units_per_time_period"),
                hours_per_units_time_period=values["hours_per_units_time_period"],
            )
            return _record_result(resource_write_api.save_assignment(assignment, auth_context=actor))

        def assignment_period_create(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            raw = _fields(
                payload["period"],
                required={"assignment_id", "activity_id", "resource_id", "period_start", "units", "cost"},
                allowed={"assignment_id", "activity_id", "resource_id", "period_start", "units", "cost"},
                code="INVALID_RESOURCE_ASSIGNMENT_PERIOD_PAYLOAD",
            )
            require_registered_resource(actor, raw["resource_id"])
            value = P6ResourceAssignmentPeriodValue(
                scope=_scope(actor, revision),
                assignment_id=raw["assignment_id"],
                activity_id=raw["activity_id"],
                resource_id=raw["resource_id"],
                period_start=raw["period_start"],
                units=_decimal(raw["units"], "INVALID_UNITS"),
                cost=_decimal(raw["cost"], "INVALID_COST"),
            )
            return _record_result(
                resource_write_api.save_assignment_period(value, auth_context=actor)
            )

        operations["resource_assignment.create"] = SharedCoreOperation(
            contract_version=P6_RESOURCE_WRITE_API_VERSION,
            permission=Permission.PROJECT_WRITE,
            required_fields=frozenset({"assignment"}),
            allowed_fields=frozenset({"assignment"}),
            handler=assignment_create,
            mutates=True,
        )
        operations["resource_assignment_period.create"] = SharedCoreOperation(
            contract_version=P6_RESOURCE_WRITE_API_VERSION,
            permission=Permission.PROJECT_WRITE,
            required_fields=frozenset({"period"}),
            allowed_fields=frozenset({"period"}),
            handler=assignment_period_create,
            mutates=True,
        )

    if resource_spread_api is not None:
        def spread_list(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            spread_id = payload.get("spread_id")
            if spread_id is not None and not isinstance(spread_id, str):
                raise ValueError("INVALID_SPREAD_ID")
            return _list_result(
                resource_spread_api.list(
                    _scope(actor, revision),
                    spread_id=spread_id,
                    auth_context=actor,
                )
            )

        def spread_get(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                resource_spread_api.get(
                    _scope(actor, revision),
                    str(payload["spread_id"]),
                    str(payload["period_id"]),
                    auth_context=actor,
                )
            )

        def spread_save(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            raw = _fields(
                payload["spread"],
                required={
                    "spread_id", "resource_id", "period_id", "period_start",
                    "period_end", "spread_type", "metric", "value",
                },
                allowed={
                    "spread_id", "resource_id", "period_id", "period_start",
                    "period_end", "spread_type", "metric", "value", "unit", "currency",
                },
                code="INVALID_RESOURCE_SPREAD_PAYLOAD",
            )
            return _record_result(
                resource_spread_api.save(
                    P6ResourceSpreadBucket(
                        scope=_scope(actor, revision),
                        spread_id=raw["spread_id"],
                        resource_id=raw["resource_id"],
                        period_id=raw["period_id"],
                        period_start=raw["period_start"],
                        period_end=raw["period_end"],
                        spread_type=raw["spread_type"],
                        metric=raw["metric"],
                        value=_decimal(raw["value"], "INVALID_SPREAD_VALUE"),
                        unit=raw.get("unit"),
                        currency=raw.get("currency"),
                    ),
                    auth_context=actor,
                )
            )

        for name, required, allowed, handler in (
            ("resource_spread.list", set(), {"spread_id"}, spread_list),
            ("resource_spread.get", {"spread_id", "period_id"}, {"spread_id", "period_id"}, spread_get),
        ):
            operations[name] = SharedCoreOperation(
                contract_version=P6_RESOURCE_SPREAD_API_VERSION,
                permission=Permission.PROJECT_READ,
                required_fields=frozenset(required),
                allowed_fields=frozenset(allowed),
                handler=handler,
            )
        operations["resource_spread.save"] = SharedCoreOperation(
            contract_version=P6_RESOURCE_SPREAD_API_VERSION,
            permission=Permission.PROJECT_WRITE,
            required_fields=frozenset({"spread"}),
            allowed_fields=frozenset({"spread"}),
            handler=spread_save,
            mutates=True,
        )

    if resource_capacity_read_api is not None:
        from datetime import date as _date

        def capacity_list(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            resource_id = payload.get("resource_id")
            if resource_id is not None and not isinstance(resource_id, str):
                raise ValueError("INVALID_RESOURCE_ID")
            return _list_result(
                resource_capacity_read_api.list_segments(
                    _scope(actor, revision), resource_id, auth_context=actor
                )
            )

        def capacity_profile(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            return _record_result(
                resource_capacity_read_api.get_profile(
                    _scope(actor, revision),
                    str(payload["resource_id"]),
                    auth_context=actor,
                )
            )

        def capacity_on(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            raw_date = payload["period"]
            if not isinstance(raw_date, str):
                raise ValueError("INVALID_CAPACITY_PERIOD")
            try:
                period = _date.fromisoformat(raw_date)
            except ValueError as exc:
                raise ValueError("INVALID_CAPACITY_PERIOD") from exc
            basis_raw = payload.get("basis")
            try:
                basis = None if basis_raw is None else ResourceCapacityBasis(basis_raw)
            except ValueError as exc:
                raise ValueError("INVALID_CAPACITY_BASIS") from exc
            hours_raw = payload.get("hours_per_time_period")
            return _record_result(
                resource_capacity_read_api.capacity_on(
                    _scope(actor, revision),
                    str(payload["resource_id"]),
                    period,
                    basis=basis,
                    hours_per_time_period=None if hours_raw is None else _decimal(hours_raw, "INVALID_HOURS_PER_TIME_PERIOD"),
                    auth_context=actor,
                )
            )

        for name, required, allowed, handler in (
            ("resource_capacity.list", set(), {"resource_id"}, capacity_list),
            ("resource_capacity.profile", {"resource_id"}, {"resource_id"}, capacity_profile),
            ("resource_capacity.on", {"resource_id", "period"}, {"resource_id", "period", "basis", "hours_per_time_period"}, capacity_on),
        ):
            operations[name] = SharedCoreOperation(
                contract_version=P6_RESOURCE_CAPACITY_READ_API_VERSION,
                permission=Permission.PROJECT_READ,
                required_fields=frozenset(required),
                allowed_fields=frozenset(allowed),
                handler=handler,
            )

    if resource_capacity_write_api is not None:
        def capacity_save(payload: Mapping[str, object], actor: AuthorizationContext, revision: int) -> object:
            raw = _fields(
                payload["capacity"],
                required={
                    "resource_id", "max_units", "unit_basis", "hours_per_time_period",
                    "effective_from", "expected_revision", "close_open_segment",
                },
                allowed={
                    "resource_id", "max_units", "unit_basis", "hours_per_time_period",
                    "effective_from", "effective_to", "expected_revision", "close_open_segment",
                },
                code="INVALID_RESOURCE_CAPACITY_PAYLOAD",
            )
            return _record_result(
                resource_capacity_write_api.save_effective_change(
                    _scope(actor, revision),
                    resource_id=raw["resource_id"],
                    max_units=raw["max_units"],
                    unit_basis=raw["unit_basis"],
                    hours_per_time_period=raw["hours_per_time_period"],
                    effective_from=raw["effective_from"],
                    effective_to=raw.get("effective_to"),
                    expected_revision=raw["expected_revision"],
                    close_open_segment=raw["close_open_segment"],
                    auth_context=actor,
                )
            )

        operations["resource_capacity.save"] = SharedCoreOperation(
            contract_version=P6_RESOURCE_CAPACITY_WRITE_API_VERSION,
            permission=Permission.PROJECT_WRITE,
            required_fields=frozenset({"capacity"}),
            allowed_fields=frozenset({"capacity"}),
            handler=capacity_save,
            mutates=True,
        )

    return operations


__all__ = ["build_project_domain_operations"]
