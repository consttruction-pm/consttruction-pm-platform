from __future__ import annotations

"""Versioned Shared Core adapters for persisted project-domain Application APIs.

These adapters contain DTO decoding only. Validation, authorization, persistence
and domain semantics remain in the existing typed APIs and Shared Core.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from construction_pm.application.authorization import AuthorizationContext, Permission
from construction_pm.activity_master_repository import ActivityMaster
from construction_pm.backend_p0.models import BackendScope
from construction_pm.constraint_master_repository import ConstraintMaster
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
from construction_pm.calendar_work_hours_repository import CalendarWorkHourRule
from construction_pm.p6_calendar_api import P6CalendarAPI, P6CalendarCreateRequest, P6_CALENDAR_API_VERSION
from construction_pm.p6_calendar_read_api import P6CalendarReadAPI
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


def build_project_domain_operations(
    *,
    activity_api: P6ActivityMasterAPI | None = None,
    wbs_api: P6WBSMasterAPI | None = None,
    relationship_api: P6RelationshipAPI | None = None,
    constraint_api: P6ConstraintAPI | None = None,
    calendar_api: P6CalendarAPI | None = None,
    calendar_read_api: P6CalendarReadAPI | None = None,
    schedule_snapshot_api: P6ScheduleSnapshotPublicationAPI | None = None,
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
        )

    return operations


__all__ = ["build_project_domain_operations"]
