from __future__ import annotations

import json
from decimal import Decimal
from dataclasses import asdict
from datetime import date, datetime, time, timezone
from typing import Callable, Mapping, Protocol

from ..application.authorization import AuthorizationError
from ..application.project_lifecycle import ProjectLifecycleError, SessionError
from ..application.project_lifecycle_api import ProjectLifecycleAPI
from ..backend_p0.api import BackendP0API
from ..backend_p0.schedule_query import SCHEDULE_QUERY_VERSION, ScheduleQueryAPI
from ..control_intelligence.contracts import ControlScope
from ..control_intelligence.query import ScheduleQueryKind, ScheduleQueryRequest
from ..backend_p0.models import BackendScope
from ..calendar_master_repository import CalendarMasterRepository, SQLiteCalendarMasterRepository
from ..calendar_snapshot_repository import SQLiteCalendarSnapshotRepository
from ..p6_calendar_read_api import P6CalendarReadAPI
from ..p6_calendar_api import P6CalendarAPI, P6CalendarCreateRequest, P6_CALENDAR_API_VERSION
from ..calendar_exception_repository import CalendarException
from ..calendar_work_hours_repository import CalendarWorkHourRule
from ..scheduling.calendar_system import CalendarSystem
from ..p6_baseline_api import P6BaselineAPI, P6_BASELINE_API_VERSION
from ..p6_baseline_repository import P6Baseline
from ..dependency_graph_api import DependencyGraphAPI
from ..client_sync.api_endpoint import VersionedSyncEndpoint, VersionedSyncRevisionEndpoint
from ..p6_field_registry import (
    P6FieldDefinition,
    P6FieldType,
    P6_FIELD_REGISTRY_REFERENCE_PRODUCT,
    P6_FIELD_REGISTRY_REFERENCE_VERSION,
    P6_FIELD_REGISTRY_STATUS,
)
from ..p6_field_registry_api import P6FieldRegistryAPI, P6_FIELD_REGISTRY_API_VERSION
from ..p6_formula_authority_api import P6FormulaAuthorityAPI
from ..p6_financial_period_api import P6FinancialPeriodAPI, P6_FINANCIAL_PERIOD_API_VERSION
from ..p6_expense_api import P6ExpenseAPI, P6_EXPENSE_API_VERSION
from ..p6_activity_period_actual_api import P6ActivityPeriodActualAPI, P6_ACTIVITY_PERIOD_ACTUAL_API_VERSION
from ..p6_relationship_api import P6RelationshipAPI, P6_RELATIONSHIP_API_VERSION
from ..p6_role_api import P6RoleAPI, P6_ROLE_API_VERSION
from ..p6_expense_repository import P6Expense
from ..p6_financial_period_repository import P6FinancialPeriod
from ..p6_mapping_api import P6MappingAPI, P6_MAPPING_API_VERSION
from ..p6_interchange_api import P6InterchangeAPI, P6_INTERCHANGE_API_VERSION
from ..p6_resource_read_api import P6ResourceReadAPI, P6_RESOURCE_READ_API_VERSION
from ..p6_resource_write_api import P6ResourceWriteAPI, P6_RESOURCE_WRITE_API_VERSION
from ..p6_resource_assignment_repository import P6ResourceAssignmentPeriodValue
from ..p6_resource_spread_api import P6ResourceSpreadAPI, P6_RESOURCE_SPREAD_API_VERSION
from ..p6_resource_spread_repository import P6ResourceSpreadBucket
from ..p6_code_api import P6CodeAPI, P6_CODE_API_VERSION
from ..p6_code_repository import P6CodeDefinition, P6CodeValue
from ..p6_mapping_registry import P6MappingDefinition, P6MappingFormat, P6MappingStatus, PersistedP6Mapping
from ..p6_layout_definition_api import P6LayoutDefinitionAPI, P6_LAYOUT_DEFINITION_API_VERSION
from ..p6_layout_definition_repository import LayoutColumn, PersistedP6Layout
from ..p6_user_defined_fields_repository import P6UserDefinedFieldDefinition
from ..p6_user_defined_fields_repository import P6UserDefinedFieldDefinition


class Clock(Protocol):
    def now(self) -> datetime: ...


class UtcClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class ProjectLifecycleHttpRoutes:
    """Framework-neutral HTTP boundary between the Web client and application layer.

    The browser authenticates with an opaque session cookie. Tenant/user/project
    identity is never accepted from browser headers as authoritative identity.
    A concrete ASGI/WSGI adapter can translate its request/response objects to
    this small contract without adding business logic.
    """

    SESSION_COOKIE = "cp_session"

    def __init__(
        self,
        api: ProjectLifecycleAPI,
        clock: Clock | None = None,
        *,
        p6_field_registry_api: P6FieldRegistryAPI | None = None,
        p6_layout_definition_api: P6LayoutDefinitionAPI | None = None,
        p6_formula_authority_api: P6FormulaAuthorityAPI | None = None,
        p6_calendar_read_api: P6CalendarReadAPI | None = None,
        p6_calendar_api: P6CalendarAPI | None = None,
        p6_baseline_api: P6BaselineAPI | None = None,
        p6_financial_period_api: P6FinancialPeriodAPI | None = None,
        p6_expense_api: P6ExpenseAPI | None = None,
        p6_activity_period_actual_api: P6ActivityPeriodActualAPI | None = None,
        p6_relationship_api: P6RelationshipAPI | None = None,
        p6_role_api: P6RoleAPI | None = None,
        p6_mapping_api: P6MappingAPI | None = None,
        p6_interchange_api: P6InterchangeAPI | None = None,
        p6_resource_read_api: P6ResourceReadAPI | None = None,
        p6_resource_write_api: P6ResourceWriteAPI | None = None,
        p6_resource_spread_api: P6ResourceSpreadAPI | None = None,
        p6_code_api: P6CodeAPI | None = None,
        dependency_graph_api: DependencyGraphAPI | None = None,
        sync_endpoint_factory: Callable[[str, str], VersionedSyncEndpoint] | None = None,
        backend_p0_api: BackendP0API | None = None,
        schedule_query_api: ScheduleQueryAPI | None = None,
    ) -> None:
        self._api = api
        self._clock = clock or UtcClock()
        self._p6_field_registry_api = p6_field_registry_api
        self._p6_layout_definition_api = p6_layout_definition_api
        self._p6_formula_authority_api = p6_formula_authority_api
        self._p6_calendar_read_api = p6_calendar_read_api
        self._p6_calendar_api = p6_calendar_api
        self._p6_baseline_api = p6_baseline_api
        self._p6_financial_period_api = p6_financial_period_api
        self._p6_expense_api = p6_expense_api
        self._p6_activity_period_actual_api = p6_activity_period_actual_api
        self._p6_relationship_api = p6_relationship_api
        self._p6_role_api = p6_role_api
        self._p6_mapping_api = p6_mapping_api
        self._p6_interchange_api = p6_interchange_api
        self._p6_resource_read_api = p6_resource_read_api
        self._p6_resource_write_api = p6_resource_write_api
        self._p6_resource_spread_api = p6_resource_spread_api
        self._p6_code_api = p6_code_api
        self._dependency_graph_api = dependency_graph_api
        self._sync_endpoint_factory = sync_endpoint_factory
        self._backend_p0_api = backend_p0_api
        self._schedule_query_api = schedule_query_api

    def handle(
        self,
        method: str,
        path: str,
        *,
        cookies: Mapping[str, str] | None = None,
        body: bytes = b"",
        headers: Mapping[str, str] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        session_id = (cookies or {}).get(self.SESSION_COOKIE)
        request_headers = headers or {}
        if not session_id:
            return self._error(401, "SESSION_REQUIRED", "error.session.required")

        try:
            now = self._clock.now()
            if method == "GET" and path == "/api/session":
                response = self._api.get_session(session_id, now=now)
                return self._json(200, {
                    "session_id": response.session_id,
                    "user_id": response.user_id,
                    "tenant_id": response.tenant_id,
                    "roles": sorted(response.roles),
                    "expires_at": response.expires_at.isoformat(),
                })
            if method == "GET" and path == "/api/projects":
                response = self._api.list_projects(session_id, now=now)
                return self._json(200, {
                    "projects": [asdict(project) for project in response.projects]
                })
            if method == "GET" and path == "/api/v1/workspace/control-room/read":
                if self._backend_p0_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                tenant_id = request_headers.get("X-Tenant-Id")
                project_id = request_headers.get("X-Project-Id")
                revision_raw = request_headers.get("X-Project-Revision")
                if not tenant_id or not project_id or not revision_raw:
                    return self._error(400, "WORKSPACE_READ_REQUEST_INVALID", "error.request.invalid")
                try:
                    revision = int(revision_raw)
                except (TypeError, ValueError):
                    return self._error(400, "WORKSPACE_READ_REQUEST_INVALID", "error.request.invalid")
                if revision < 0 or str(revision) != revision_raw.strip():
                    return self._error(400, "WORKSPACE_READ_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                if tenant_id != context.tenant_id:
                    return self._error(403, "CROSS_SCOPE_ACCESS", "error.authorization.denied")
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                result = self._backend_p0_api.read_workspace_control_room(
                    tenant_id=context.tenant_id,
                    project_id=context.project_id,
                    revision=revision,
                    auth_context=auth,
                )
                if result is None:
                    return self._error(404, "WORKSPACE_READ_NOT_FOUND", "error.workspace_read.not_found")
                if not isinstance(result, dict):
                    return self._error(502, "INVALID_WORKSPACE_READ_RESPONSE", "error.workspace_read.invalid_payload")
                backend_error = result.get("error")
                if isinstance(backend_error, dict):
                    category = backend_error.get("category")
                    status = {"authorization": 403, "not_found": 404, "conflict": 409, "validation": 400}.get(category, 500)
                    return self._json(status, result)
                return self._json(200, result)
            if method == "POST" and path == "/api/v1/schedule/query":
                if self._schedule_query_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                try:
                    payload = json.loads(body.decode("utf-8") or "{}")
                except json.JSONDecodeError:
                    return self._error(400, "SCHEDULE_QUERY_REQUEST_INVALID", "error.request.invalid")
                if not isinstance(payload, dict):
                    return self._error(400, "SCHEDULE_QUERY_REQUEST_INVALID", "error.request.invalid")
                if payload.get("contract_version") != SCHEDULE_QUERY_VERSION:
                    return self._error(400, "SCHEDULE_QUERY_REQUEST_INVALID", "error.request.invalid")
                required = ("query_id", "scope", "requested_by", "query_text", "kind", "language")
                if any(key not in payload for key in required):
                    return self._error(400, "SCHEDULE_QUERY_REQUEST_INVALID", "error.request.invalid")
                raw_scope = payload.get("scope")
                if not isinstance(raw_scope, dict):
                    return self._error(400, "SCHEDULE_QUERY_REQUEST_INVALID", "error.request.invalid")
                requested_project_id = raw_scope.get("project_id")
                if not isinstance(requested_project_id, str) or not requested_project_id.strip():
                    return self._error(400, "SCHEDULE_QUERY_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, requested_project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                if raw_scope.get("tenant_id") != context.tenant_id or raw_scope.get("project_id") != context.project_id or raw_scope.get("project_revision") != context.revision:
                    return self._error(403, "CROSS_SCOPE_ACCESS", "error.authorization.denied")
                if payload.get("requested_by") != session.user_id:
                    return self._error(403, "REQUESTED_BY_MISMATCH", "error.authorization.denied")
                if not isinstance(payload.get("query_id"), str) or not payload["query_id"].strip():
                    return self._error(400, "SCHEDULE_QUERY_REQUEST_INVALID", "error.request.invalid")
                if not isinstance(payload.get("query_text"), str) or not payload["query_text"].strip():
                    return self._error(400, "SCHEDULE_QUERY_REQUEST_INVALID", "error.request.invalid")
                if not isinstance(payload.get("language"), str) or not payload["language"].strip():
                    return self._error(400, "SCHEDULE_QUERY_REQUEST_INVALID", "error.request.invalid")
                try:
                    kind = ScheduleQueryKind(payload["kind"])
                    constraints = payload.get("constraints", {})
                    if not isinstance(constraints, dict):
                        return self._error(400, "SCHEDULE_QUERY_REQUEST_INVALID", "error.request.invalid")
                    request = ScheduleQueryRequest(
                        query_id=payload["query_id"],
                        scope=ControlScope(context.tenant_id, context.project_id, context.revision),
                        requested_by=session.user_id,
                        query_text=payload["query_text"],
                        kind=kind,
                        language=payload["language"],
                        constraints=constraints,
                    )
                except (TypeError, ValueError):
                    return self._error(400, "SCHEDULE_QUERY_REQUEST_INVALID", "error.request.invalid")
                result = self._schedule_query_api.execute(request, auth_context=auth)
                if not isinstance(result, dict):
                    return self._error(502, "INVALID_SCHEDULE_QUERY_RESPONSE", "error.schedule_query.invalid_payload")
                backend_error = result.get("error")
                if isinstance(backend_error, dict):
                    category = backend_error.get("category")
                    status = {"authorization": 403, "not_found": 404, "conflict": 409, "validation": 400}.get(category, 500)
                    return self._json(status, result)
                if result.get("contract_version") != "schedule-query-result.v1":
                    return self._error(502, "INVALID_SCHEDULE_QUERY_RESPONSE", "error.schedule_query.invalid_payload")
                return self._json(200, result)
            if method == "POST" and path == "/api/v1/sync/mutations":
                if self._sync_endpoint_factory is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                try:
                    payload = json.loads(body.decode("utf-8") or "{}")
                except json.JSONDecodeError:
                    return self._error(400, "SYNC_REQUEST_INVALID", "error.request.invalid")
                if not isinstance(payload, dict):
                    return self._error(400, "SYNC_REQUEST_INVALID", "error.request.invalid")
                required = ("project_id", "mutation_id", "tenant_id", "expected_revision", "operation", "idempotency_key")
                if any(key not in payload for key in required):
                    return self._error(400, "SYNC_REQUEST_INVALID", "error.request.invalid")
                if not all(isinstance(payload.get(key), str) and payload.get(key) for key in ("project_id", "mutation_id", "tenant_id", "operation", "idempotency_key")):
                    return self._error(400, "SYNC_REQUEST_INVALID", "error.request.invalid")
                if not isinstance(payload.get("expected_revision"), int) or isinstance(payload.get("expected_revision"), bool):
                    return self._error(400, "SYNC_REQUEST_INVALID", "error.request.invalid")
                if not isinstance(payload.get("payload", {}), dict):
                    return self._error(400, "SYNC_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, payload["project_id"], now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                idempotency_key = request_headers.get("Idempotency-Key")
                if not isinstance(idempotency_key, str) or not idempotency_key.strip():
                    return self._error(400, "SYNC_REQUEST_INVALID", "error.request.invalid")
                try:
                    result = self._sync_endpoint_factory(context.tenant_id, context.project_id).post(
                        payload,
                        {
                            "Idempotency-Key": idempotency_key,
                            "X-Tenant-Id": context.tenant_id,
                            "X-Project-Id": context.project_id,
                            "X-Project-Revision": str(context.revision),
                        },
                    )
                except (KeyError, TypeError, ValueError):
                    return self._error(400, "SYNC_REQUEST_INVALID", "error.request.invalid")
                return self._json(200, result)
            if method == "GET" and path.startswith("/api/v1/sync/revision/"):
                if self._sync_endpoint_factory is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/v1/sync/revision/"):].rstrip("/")
                if not project_id or "/" in project_id:
                    return self._error(400, "SYNC_REVISION_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                endpoint = VersionedSyncRevisionEndpoint(
                    context.tenant_id,
                    context.project_id,
                    lambda _tenant, _project: context.revision,
                )
                return self._json(200, endpoint.get({
                    "X-Tenant-Id": context.tenant_id,
                    "X-Project-Id": context.project_id,
                }))
            if path.startswith("/api/projects/") and "/p6/calendars" in path and self._p6_calendar_api is not None:
                calendar_base = "/p6/calendars"
                prefix, suffix = path.split(calendar_base, 1)
                project_id = prefix[len("/api/projects/"):]
                if not project_id:
                    return self._error(400, "P6_CALENDAR_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                scope = BackendScope(context.tenant_id, context.project_id, context.revision)
                try:
                    payload = json.loads(body.decode("utf-8") or "{}")
                    if not isinstance(payload, dict):
                        raise ValueError("invalid payload")
                    parts = suffix.strip("/").split("/") if suffix.strip("/") else []
                    if method == "POST" and not parts:
                        request = P6CalendarCreateRequest(
                            contract_version=payload.get("contract_version", P6_CALENDAR_API_VERSION),
                            calendar_id=str(payload.get("calendar_id", "")),
                            calendar_version=str(payload.get("calendar_version", "")),
                            calendar_type=str(payload.get("calendar_type", "")),
                            kind=str(payload.get("kind", "")),
                            name=str(payload.get("name", "")),
                            expected_revision=payload.get("expected_revision"),
                            base_calendar_id=payload.get("base_calendar_id"),
                            base_calendar_version=payload.get("base_calendar_version"),
                        )
                        return self._json(200, self._p6_calendar_api.create(scope, request, auth_context=auth))
                    if len(parts) == 2 and method in {"PATCH", "DELETE"}:
                        calendar_id, calendar_version = parts
                        if method == "DELETE":
                            expected_revision = payload.get("expected_revision")
                            if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
                                raise ValueError("expected_revision required")
                            result = self._p6_calendar_api.delete(scope, calendar_id, calendar_version, expected_revision=expected_revision, auth_context=auth)
                            return self._json(200, {"contract_version": P6_CALENDAR_API_VERSION, "deleted": result})
                        request = P6CalendarCreateRequest(
                            contract_version=payload.get("contract_version", P6_CALENDAR_API_VERSION),
                            calendar_id=calendar_id,
                            calendar_version=calendar_version,
                            calendar_type=str(payload.get("calendar_type", "")),
                            kind=str(payload.get("kind", "")),
                            name=str(payload.get("name", "")),
                            expected_revision=payload.get("expected_revision"),
                            base_calendar_id=payload.get("base_calendar_id"),
                            base_calendar_version=payload.get("base_calendar_version"),
                        )
                        return self._json(200, self._p6_calendar_api.update(scope, request, auth_context=auth))
                    if len(parts) == 3 and parts[2] in {"copy", "replace"} and method == "POST":
                        calendar_id, calendar_version, operation = parts
                        if operation == "copy":
                            return self._json(200, self._p6_calendar_api.copy(
                                scope, calendar_id, calendar_version,
                                str(payload.get("target_calendar_id", "")), str(payload.get("target_calendar_version", "")),
                                auth_context=auth,
                            ))
                        return self._json(200, self._p6_calendar_api.replace(
                            scope, str(payload.get("target_calendar_id", "")), str(payload.get("target_calendar_version", "")),
                            calendar_id, calendar_version, auth_context=auth,
                        ))
                    if len(parts) == 3 and parts[2] in {"exceptions", "work-hours"}:
                        calendar_id, calendar_version, resource = parts
                        if method == "GET":
                            if resource == "exceptions":
                                return self._json(200, {"contract_version": P6_CALENDAR_API_VERSION, "exceptions": list(self._p6_calendar_api.list_exceptions(scope, calendar_id, calendar_version, auth_context=auth))})
                            kind = str(payload.get("kind", "")) if payload else ""
                            if not kind:
                                raise ValueError("kind required")
                            return self._json(200, {"contract_version": P6_CALENDAR_API_VERSION, "work_hours": list(self._p6_calendar_api.list_work_hours(scope, calendar_id, calendar_version, kind, auth_context=auth))})
                        if method == "POST" and resource == "exceptions":
                            raw_intervals = payload.get("intervals", [])
                            if not isinstance(raw_intervals, list): raise ValueError("invalid intervals")
                            intervals = tuple((time.fromisoformat(str(item[0])), time.fromisoformat(str(item[1]))) for item in raw_intervals if isinstance(item, (list, tuple)) and len(item) == 2)
                            if len(intervals) != len(raw_intervals): raise ValueError("invalid intervals")
                            exception = CalendarException(
                                scope, calendar_id, calendar_version, date.fromisoformat(str(payload.get("date", ""))),
                                str(payload.get("mode", "")), payload.get("total_work_hours"), intervals,
                                CalendarSystem(str(payload.get("system", CalendarSystem.GREGORIAN.value))),
                            )
                            return self._json(200, self._p6_calendar_api.save_exception(exception, auth_context=auth))
                        if method == "POST" and resource == "work-hours":
                            raw_intervals = payload.get("intervals", [])
                            if not isinstance(raw_intervals, list): raise ValueError("invalid intervals")
                            intervals = tuple((str(item[0]), str(item[1])) for item in raw_intervals if isinstance(item, (list, tuple)) and len(item) == 2)
                            if len(intervals) != len(raw_intervals): raise ValueError("invalid intervals")
                            rule = CalendarWorkHourRule(
                                scope, calendar_id, calendar_version, str(payload.get("kind", "")),
                                payload.get("weekday"), payload.get("is_working_day"),
                                None if payload.get("total_work_hours") is None else Decimal(str(payload.get("total_work_hours"))), intervals,
                            )
                            return self._json(200, self._p6_calendar_api.save_work_hours(rule, auth_context=auth))
                except (TypeError, ValueError, ArithmeticError):
                    return self._error(400, "P6_CALENDAR_REQUEST_INVALID", "error.request.invalid")
            if method == "GET" and path.startswith("/api/projects/") and path.endswith("/p6/calendars"):
                if self._p6_calendar_read_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/p6/calendars")].rstrip("/")
                if not project_id:
                    return self._error(400, "P6_CALENDAR_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                result = self._p6_calendar_read_api.list_calendars(
                    BackendScope(context.tenant_id, context.project_id, context.revision),
                    auth_context=auth,
                )
                return self._json(200, result)
            if method == "GET" and path.startswith("/api/projects/") and "/p6/calendars/" in path and path.endswith("/snapshot"):
                if self._p6_calendar_read_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, suffix = path.split("/p6/calendars/", 1)
                project_id = prefix[len("/api/projects/"):]
                parts = suffix[:-len("/snapshot")].rstrip("/").split("/")
                if not project_id or len(parts) != 2 or not all(parts):
                    return self._error(400, "P6_CALENDAR_REQUEST_INVALID", "error.request.invalid")
                calendar_id, calendar_version = parts
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                result = self._p6_calendar_read_api.get_snapshot(
                    BackendScope(context.tenant_id, context.project_id, context.revision),
                    calendar_id,
                    calendar_version,
                    auth_context=auth,
                )
                if result is None:
                    return self._error(404, "P6_CALENDAR_NOT_FOUND", "error.p6.calendar.not_found")
                return self._json(200, result)
            if method == "GET" and path.startswith("/api/projects/") and path.endswith("/p6/mappings"):
                if self._p6_mapping_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/p6/mappings")].rstrip("/")
                if not project_id:
                    return self._error(400, "P6_MAPPING_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                result = self._p6_mapping_api.list(
                    BackendScope(context.tenant_id, context.project_id, context.revision),
                    auth_context=auth,
                )
                return self._json(200, {
                    "contract_version": P6_MAPPING_API_VERSION,
                    "mappings": list(result),
                })
            if method == "GET" and path.startswith("/api/projects/") and "/p6/mappings/" in path:
                if self._p6_mapping_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, mapping_id = path.split("/p6/mappings/", 1)
                project_id = prefix[len("/api/projects/"):]
                if not project_id or not mapping_id or "/" in mapping_id:
                    return self._error(400, "P6_MAPPING_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                result = self._p6_mapping_api.get(
                    BackendScope(context.tenant_id, context.project_id, context.revision),
                    mapping_id,
                    auth_context=auth,
                )
                if result is None:
                    return self._error(404, "P6_MAPPING_NOT_FOUND", "error.p6.mapping.not_found")
                return self._json(200, result)
            if method == "POST" and path.startswith("/api/projects/") and path.endswith("/p6/mappings"):
                if self._p6_mapping_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/p6/mappings")].rstrip("/")
                if not project_id:
                    return self._error(400, "P6_MAPPING_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                try:
                    payload = json.loads(body.decode("utf-8") or "{}")
                    if not isinstance(payload, dict):
                        raise ValueError
                    record = PersistedP6Mapping(
                        scope=BackendScope(context.tenant_id, context.project_id, context.revision),
                        definition=P6MappingDefinition(
                            mapping_id=payload.get("mapping_id", ""),
                            registry_version=payload.get("registry_version", "p6-field-registry.v1"),
                            format=P6MappingFormat(payload.get("format", "")),
                            subject_area=payload.get("subject_area", ""),
                            source_field=payload.get("source_field", ""),
                            canonical_field=payload.get("canonical_field", ""),
                            status=P6MappingStatus(payload.get("status", "SUPPORTED")),
                            source_type=payload.get("source_type"),
                            canonical_type=payload.get("canonical_type"),
                            unit=payload.get("unit"),
                            notes=payload.get("notes"),
                        ),
                    )
                    result = self._p6_mapping_api.create(record, auth_context=auth)
                except (TypeError, ValueError):
                    return self._error(400, "P6_MAPPING_REQUEST_INVALID", "error.request.invalid")
                return self._json(200, result)
            if method == "POST" and path.startswith("/api/projects/") and "/p6/interchange/" in path and path.endswith("/import"):
                if self._p6_interchange_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, format_path = path.split("/p6/interchange/", 1)
                if not prefix.startswith("/api/projects/") or not format_path.endswith("/import"):
                    return self._error(400, "P6_INTERCHANGE_REQUEST_INVALID", "error.request.invalid")
                project_id = prefix[len("/api/projects/"):]
                format_value = format_path[:-len("/import")].strip("/")
                try:
                    format = P6MappingFormat(format_value)
                    context = self._api.open_project(session_id, project_id, now=now).context
                    auth = context.authorization_context(self._api.get_session(session_id, now=now).roles)
                    result = self._p6_interchange_api.import_document(
                        scope=BackendScope(context.tenant_id, context.project_id, context.revision),
                        format=format,
                        payload=body,
                        auth_context=auth,
                    )
                    return self._json(200, result)
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    return self._error(400, str(exc), "error.request.invalid")
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                except ValueError as exc:
                    return self._error(400, str(exc), "error.request.invalid")

            if method == "POST" and path.startswith("/api/projects/") and "/p6/interchange/" in path and path.endswith("/export"):
                if self._p6_interchange_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, format_path = path.split("/p6/interchange/", 1)
                project_id = prefix[len("/api/projects/"):]
                format_value = format_path[:-len("/export")].strip("/")
                try:
                    payload = json.loads(body.decode("utf-8") or "{}")
                    if not isinstance(payload, dict) or not isinstance(payload.get("values"), list):
                        return self._error(400, "P6_INTERCHANGE_REQUEST_INVALID", "error.request.invalid")
                    format = P6MappingFormat(format_value)
                    context = self._api.open_project(session_id, project_id, now=now).context
                    auth = context.authorization_context(self._api.get_session(session_id, now=now).roles)
                    result = self._p6_interchange_api.export_document(
                        scope=BackendScope(context.tenant_id, context.project_id, context.revision),
                        format=format,
                        values=tuple(item for item in payload["values"] if isinstance(item, dict)),
                        extensions=payload.get("extensions"),
                        auth_context=auth,
                    )
                    return self._json(200, result)
                except json.JSONDecodeError:
                    return self._error(400, "P6_INTERCHANGE_REQUEST_INVALID", "error.request.invalid")
                except (ValueError, AuthorizationError) as exc:
                    return self._error(400 if not isinstance(exc, AuthorizationError) else 403, str(exc), "error.request.invalid" if not isinstance(exc, AuthorizationError) else "error.authorization.denied")

            if method == "GET" and path.startswith("/api/projects/") and "/dependencies/" in path:
                if self._dependency_graph_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, resource_id = path.split("/dependencies/", 1)
                project_id = prefix[len("/api/projects/"):]
                if not project_id or not resource_id or "/" in resource_id:
                    return self._error(400, "DEPENDENCY_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                result = self._dependency_graph_api.get(
                    tenant_id=context.tenant_id,
                    project_id=context.project_id,
                    resource_id=resource_id,
                    auth_context=auth,
                )
                if result is None:
                    return self._error(404, "DEPENDENCY_NOT_FOUND", "error.dependency.not_found")
                return self._json(200, result)
            if method == "GET" and path.startswith("/api/projects/") and path.endswith("/p6/financial-periods"):
                if self._p6_financial_period_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/p6/financial-periods")].rstrip("/")
                if not project_id:
                    return self._error(400, "P6_FINANCIAL_PERIOD_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                result = self._p6_financial_period_api.list(
                    BackendScope(context.tenant_id, context.project_id, context.revision),
                    auth_context=auth,
                )
                return self._json(200, {
                    "contract_version": P6_FINANCIAL_PERIOD_API_VERSION,
                    "financial_periods": list(result),
                })
            if method == "GET" and path.startswith("/api/projects/") and "/p6/financial-periods/" in path:
                if self._p6_financial_period_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, period_id = path.split("/p6/financial-periods/", 1)
                project_id = prefix[len("/api/projects/"):]
                if not project_id or not period_id or "/" in period_id:
                    return self._error(400, "P6_FINANCIAL_PERIOD_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                result = self._p6_financial_period_api.get(
                    BackendScope(context.tenant_id, context.project_id, context.revision),
                    period_id,
                    auth_context=auth,
                )
                if result is None:
                    return self._error(404, "P6_FINANCIAL_PERIOD_NOT_FOUND", "error.p6.financial_period.not_found")
                return self._json(200, result)
            if method == "POST" and path.startswith("/api/projects/") and path.endswith("/p6/financial-periods"):
                if self._p6_financial_period_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/p6/financial-periods")].rstrip("/")
                if not project_id:
                    return self._error(400, "P6_FINANCIAL_PERIOD_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                try:
                    payload = json.loads(body.decode("utf-8") or "{}")
                except json.JSONDecodeError:
                    return self._error(400, "P6_FINANCIAL_PERIOD_REQUEST_INVALID", "error.request.invalid")
                if not isinstance(payload, dict):
                    return self._error(400, "P6_FINANCIAL_PERIOD_REQUEST_INVALID", "error.request.invalid")
                period = P6FinancialPeriod(
                    scope=BackendScope(context.tenant_id, context.project_id, context.revision),
                    period_id=payload.get("period_id", ""),
                    name=payload.get("name", ""),
                    start_date=payload.get("start_date", ""),
                    end_date=payload.get("end_date", ""),
                    status=payload.get("status", "OPEN"),
                )
                try:
                    result = self._p6_financial_period_api.create(period, auth_context=auth)
                except (TypeError, ValueError):
                    return self._error(400, "P6_FINANCIAL_PERIOD_REQUEST_INVALID", "error.request.invalid")
                return self._json(200, result)
            if path.startswith("/api/projects/") and "/p6/roles" in path and self._p6_role_api is not None:
                prefix = "/p6/roles"
                project_id = path[len("/api/projects/"):].split(prefix, 1)[0].rstrip("/")
                suffix = path[len("/api/projects/") + len(project_id) + len(prefix):]
                if not project_id:
                    return self._error(400, "P6_ROLE_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                scope = BackendScope(context.tenant_id, context.project_id, context.revision)
                try:
                    parts = suffix.strip("/").split("/") if suffix.strip("/") else []
                    payload = json.loads(body.decode("utf-8") or "{}") if body else {}
                    if not isinstance(payload, dict):
                        raise ValueError("invalid payload")
                    if method == "GET" and not parts:
                        result = self._p6_role_api.list(context.tenant_id, context.project_id, context.revision, auth_context=auth)
                        return self._json(200, {"contract_version": P6_ROLE_API_VERSION, "roles": list(result)})
                    if method == "GET" and len(parts) == 1 and parts[0]:
                        result = self._p6_role_api.get(context.tenant_id, context.project_id, context.revision, parts[0], auth_context=auth)
                        if result is None:
                            return self._error(404, "P6_ROLE_NOT_FOUND", "error.p6.role.not_found")
                        return self._json(200, result)
                    if method == "POST" and not parts:
                        from ..p6_role_repository import P6Role
                        role = P6Role(
                            scope.tenant_id, scope.project_id, scope.project_revision,
                            payload.get("role_id", ""), payload.get("name", ""), payload.get("description")
                        )
                        return self._json(200, self._p6_role_api.create(role, auth_context=auth))
                    if method == "PATCH" and len(parts) == 1 and parts[0]:
                        from ..p6_role_repository import P6Role
                        expected_revision = payload.get("expected_revision")
                        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
                            raise ValueError("expected_revision required")
                        role = P6Role(
                            scope.tenant_id, scope.project_id, scope.project_revision,
                            parts[0], payload.get("name", ""), payload.get("description"),
                            expected_revision
                        )
                        return self._json(200, self._p6_role_api.update(role, expected_revision=expected_revision, auth_context=auth))
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                except (TypeError, ValueError, ArithmeticError, KeyError):
                    return self._error(400, "P6_ROLE_REQUEST_INVALID", "error.request.invalid")
            if path.startswith("/api/projects/") and "/p6/relationships" in path and self._p6_relationship_api is not None:
                prefix = "/p6/relationships"
                project_id = path[len("/api/projects/"):].split(prefix, 1)[0].rstrip("/")
                suffix = path[len("/api/projects/") + len(project_id) + len(prefix):]
                if not project_id:
                    return self._error(400, "P6_RELATIONSHIP_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                scope = BackendScope(context.tenant_id, context.project_id, context.revision)
                try:
                    parts = suffix.strip("/").split("/") if suffix.strip("/") else []
                    payload = json.loads(body.decode("utf-8") or "{}") if body else {}
                    if not isinstance(payload, dict):
                        raise ValueError("invalid payload")
                    if method == "GET" and not parts:
                        result = self._p6_relationship_api.list(scope, auth_context=auth)
                        return self._json(200, {"contract_version": P6_RELATIONSHIP_API_VERSION, "relationships": list(result)})
                    if method == "GET" and len(parts) == 1 and parts[0]:
                        result = self._p6_relationship_api.get(scope, parts[0], auth_context=auth)
                        if result is None:
                            return self._error(404, "P6_RELATIONSHIP_NOT_FOUND", "error.p6.relationship.not_found")
                        return self._json(200, result)
                    if method == "POST" and not parts:
                        from ..relationship_master_repository import RelationshipMaster
                        from ..scheduling.relationships import RelationshipType
                        from ..scheduling.time_duration import DurationUnit
                        relationship = RelationshipMaster(
                            scope=scope,
                            relationship_id=payload.get("relationship_id", ""),
                            predecessor_id=payload.get("predecessor_id", ""),
                            successor_id=payload.get("successor_id", ""),
                            relationship_type=RelationshipType(payload.get("relationship_type", "FS")),
                            lag_value=Decimal(str(payload.get("lag_value", "0"))),
                            lag_unit=DurationUnit(payload.get("lag_unit", DurationUnit.WORKING_DAY.value)),
                        )
                        expected_revision = payload.get("expected_revision")
                        if expected_revision is not None and (isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 0):
                            raise ValueError("invalid expected_revision")
                        return self._json(200, self._p6_relationship_api.create(relationship, expected_revision=expected_revision, auth_context=auth))
                    if method == "PATCH" and len(parts) == 1 and parts[0]:
                        from ..relationship_master_repository import RelationshipMaster
                        from ..scheduling.relationships import RelationshipType
                        from ..scheduling.time_duration import DurationUnit
                        expected_revision = payload.get("expected_revision")
                        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
                            raise ValueError("expected_revision required")
                        relationship = RelationshipMaster(
                            scope=scope,
                            relationship_id=parts[0],
                            predecessor_id=payload.get("predecessor_id", ""),
                            successor_id=payload.get("successor_id", ""),
                            relationship_type=RelationshipType(payload.get("relationship_type", "FS")),
                            lag_value=Decimal(str(payload.get("lag_value", "0"))),
                            lag_unit=DurationUnit(payload.get("lag_unit", DurationUnit.WORKING_DAY.value)),
                            record_revision=expected_revision,
                        )
                        return self._json(200, self._p6_relationship_api.update(relationship, expected_revision=expected_revision, auth_context=auth))
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                except (TypeError, ValueError, ArithmeticError):
                    return self._error(400, "P6_RELATIONSHIP_REQUEST_INVALID", "error.request.invalid")
            if path.startswith("/api/projects/") and "/p6/expenses" in path and self._p6_expense_api is not None:
                prefix = "/p6/expenses"
                project_id = path[len("/api/projects/"):].split(prefix, 1)[0].rstrip("/")
                suffix = path[len("/api/projects/") + len(project_id) + len(prefix):]
                if not project_id:
                    return self._error(400, "P6_EXPENSE_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                scope = BackendScope(context.tenant_id, context.project_id, context.revision)
                try:
                    payload = json.loads(body.decode("utf-8") or "{}")
                    if not isinstance(payload, dict):
                        raise ValueError("invalid payload")
                    expense_id = suffix.strip("/")
                    if method == "GET" and not expense_id:
                        result = self._p6_expense_api.list(
                            scope,
                            activity_id=payload.get("activity_id"),
                            wbs_id=payload.get("wbs_id"),
                            auth_context=auth,
                        )
                        return self._json(200, {
                            "contract_version": P6_EXPENSE_API_VERSION,
                            "expenses": list(result),
                        })
                    if method == "GET" and expense_id and "/" not in expense_id:
                        result = self._p6_expense_api.get(scope, expense_id, auth_context=auth)
                        if result is None:
                            return self._error(404, "P6_EXPENSE_NOT_FOUND", "error.p6.expense.not_found")
                        return self._json(200, result)
                    if method == "POST" and not expense_id:
                        expense = P6Expense(
                            scope=scope,
                            expense_id=payload.get("expense_id", ""),
                            name=payload.get("name", ""),
                            category=payload.get("category", ""),
                            activity_id=payload.get("activity_id"),
                            wbs_id=payload.get("wbs_id"),
                            expense_date=payload.get("expense_date"),
                            planned_cost=None if payload.get("planned_cost") is None else Decimal(str(payload.get("planned_cost"))),
                            actual_cost=None if payload.get("actual_cost") is None else Decimal(str(payload.get("actual_cost"))),
                            remaining_cost=None if payload.get("remaining_cost") is None else Decimal(str(payload.get("remaining_cost"))),
                            currency=payload.get("currency"),
                            note=payload.get("note"),
                        )
                        return self._json(200, self._p6_expense_api.create(expense, auth_context=auth))
                except (TypeError, ValueError, ArithmeticError):
                    return self._error(400, "P6_EXPENSE_REQUEST_INVALID", "error.request.invalid")
            if path.startswith("/api/projects/") and "/p6/activity-period-actuals" in path and self._p6_activity_period_actual_api is not None:
                prefix = "/p6/activity-period-actuals"
                project_id = path[len("/api/projects/"):].split(prefix, 1)[0].rstrip("/")
                suffix = path[len("/api/projects/") + len(project_id) + len(prefix):]
                if not project_id:
                    return self._error(400, "P6_ACTIVITY_PERIOD_ACTUAL_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                scope = BackendScope(context.tenant_id, context.project_id, context.revision)
                try:
                    parts = suffix.strip("/").split("/") if suffix.strip("/") else []
                    payload = json.loads(body.decode("utf-8") or "{}") if body else {}
                    if not isinstance(payload, dict):
                        raise ValueError("invalid payload")
                    if method == "GET" and not parts:
                        result = self._p6_activity_period_actual_api.list(
                            scope,
                            activity_id=payload.get("activity_id"),
                            period_id=payload.get("period_id"),
                            auth_context=auth,
                        )
                        return self._json(200, {
                            "contract_version": P6_ACTIVITY_PERIOD_ACTUAL_API_VERSION,
                            "activity_period_actuals": list(result),
                        })
                    if method == "GET" and len(parts) == 1 and parts[0]:
                        result = self._p6_activity_period_actual_api.get(scope, parts[0], auth_context=auth)
                        if result is None:
                            return self._error(404, "P6_ACTIVITY_PERIOD_ACTUAL_NOT_FOUND", "error.p6.activity_period_actual.not_found")
                        return self._json(200, result)
                    if method == "POST" and not parts:
                        from ..p6_activity_period_actual_repository import P6ActivityPeriodActual
                        actual = P6ActivityPeriodActual(
                            scope=scope,
                            actual_id=payload.get("actual_id", ""),
                            activity_id=payload.get("activity_id", ""),
                            period_id=payload.get("period_id", ""),
                            actual_units=None if payload.get("actual_units") is None else Decimal(str(payload.get("actual_units"))),
                            actual_cost=None if payload.get("actual_cost") is None else Decimal(str(payload.get("actual_cost"))),
                            unit=payload.get("unit"),
                            currency=payload.get("currency"),
                            note=payload.get("note"),
                        )
                        return self._json(200, self._p6_activity_period_actual_api.create(actual, auth_context=auth))
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                except (TypeError, ValueError, ArithmeticError):
                    return self._error(400, "P6_ACTIVITY_PERIOD_ACTUAL_REQUEST_INVALID", "error.request.invalid")
            if method == "GET" and path.startswith("/api/projects/") and path.endswith("/p6/resource-assignments"):
                if self._p6_resource_read_api is None: return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/p6/resource-assignments")].rstrip("/")
                if not project_id: return self._error(400, "P6_RESOURCE_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now); auth = context.authorization_context(session.roles)
                result = self._p6_resource_read_api.list_assignments(BackendScope(context.tenant_id, context.project_id, context.revision), auth_context=auth)
                return self._json(200, {"contract_version": P6_RESOURCE_READ_API_VERSION, "assignments": list(result)})
            if method == "GET" and path.startswith("/api/projects/") and "/p6/resource-assignments/" in path:
                if self._p6_resource_read_api is None: return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, assignment_id = path.split("/p6/resource-assignments/", 1); project_id = prefix[len("/api/projects/"):]; assignment_id = assignment_id.rstrip("/")
                if not project_id or not assignment_id or "/" in assignment_id: return self._error(400, "P6_RESOURCE_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now); auth = context.authorization_context(session.roles)
                result = self._p6_resource_read_api.get_assignment(BackendScope(context.tenant_id, context.project_id, context.revision), assignment_id, auth_context=auth)
                if result is None: return self._error(404, "P6_RESOURCE_ASSIGNMENT_NOT_FOUND", "error.p6.resource_assignment.not_found")
                return self._json(200, result)
            if method == "GET" and path.startswith("/api/projects/") and path.endswith("/p6/resource-assignment-periods"):
                if self._p6_resource_read_api is None: return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/p6/resource-assignment-periods")].rstrip("/")
                if not project_id: return self._error(400, "P6_RESOURCE_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now); auth = context.authorization_context(session.roles)
                result = self._p6_resource_read_api.list_assignment_periods(BackendScope(context.tenant_id, context.project_id, context.revision), auth_context=auth)
                return self._json(200, {"contract_version": P6_RESOURCE_READ_API_VERSION, "periods": list(result)})
            if method == "GET" and path.startswith("/api/projects/") and "/p6/resource-assignment-periods/" in path:
                if self._p6_resource_read_api is None: return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, suffix = path.split("/p6/resource-assignment-periods/", 1); project_id = prefix[len("/api/projects/"):]; parts = suffix.rstrip("/").split("/")
                if not project_id or len(parts) != 2 or not all(parts): return self._error(400, "P6_RESOURCE_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now); auth = context.authorization_context(session.roles)
                result = self._p6_resource_read_api.get_assignment_period(BackendScope(context.tenant_id, context.project_id, context.revision), parts[0], parts[1], auth_context=auth)
                if result is None: return self._error(404, "P6_RESOURCE_ASSIGNMENT_PERIOD_NOT_FOUND", "error.p6.resource_assignment_period.not_found")
                return self._json(200, result)
            if method == "POST" and path.startswith("/api/projects/") and path.endswith("/p6/resource-assignment-periods"):
                if self._p6_resource_write_api is None: return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/p6/resource-assignment-periods")].rstrip("/")
                if not project_id: return self._error(400, "P6_RESOURCE_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now); auth = context.authorization_context(session.roles)
                try:
                    payload = json.loads(body.decode("utf-8") or "{}")
                    if not isinstance(payload, dict): raise ValueError("invalid payload")
                    value = P6ResourceAssignmentPeriodValue(scope=BackendScope(context.tenant_id, context.project_id, context.revision), assignment_id=str(payload.get("assignment_id","")), activity_id=str(payload.get("activity_id","")), resource_id=str(payload.get("resource_id","")), period_start=str(payload.get("period_start","")), units=Decimal(str(payload.get("units",""))), cost=Decimal(str(payload.get("cost",""))))
                    result = self._p6_resource_write_api.save_assignment_period(value, auth_context=auth)
                except (TypeError, ValueError, ArithmeticError): return self._error(400, "P6_RESOURCE_REQUEST_INVALID", "error.request.invalid")
                return self._json(200, result)
            if method == "GET" and path.startswith("/api/projects/") and path.endswith("/p6/resource-spreads"):
                if self._p6_resource_spread_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/p6/resource-spreads")].rstrip("/")
                if not project_id:
                    return self._error(400, "P6_RESOURCE_SPREAD_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                result = self._p6_resource_spread_api.list(
                    BackendScope(context.tenant_id, context.project_id, context.revision),
                    auth_context=auth,
                )
                return self._json(200, {
                    "contract_version": P6_RESOURCE_SPREAD_API_VERSION,
                    "buckets": result,
                })
            if method == "GET" and path.startswith("/api/projects/") and "/p6/resource-spreads/" in path:
                if self._p6_resource_spread_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, suffix = path.split("/p6/resource-spreads/", 1)
                project_id = prefix[len("/api/projects/"):]
                parts = suffix.rstrip("/").split("/")
                if not project_id or len(parts) != 2 or not all(parts):
                    return self._error(400, "P6_RESOURCE_SPREAD_REQUEST_INVALID", "error.request.invalid")
                spread_id, period_id = parts
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                result = self._p6_resource_spread_api.get(
                    BackendScope(context.tenant_id, context.project_id, context.revision),
                    spread_id,
                    period_id,
                    auth_context=auth,
                )
                if result is None:
                    return self._error(404, "P6_RESOURCE_SPREAD_NOT_FOUND", "error.p6.resource_spread.not_found")
                return self._json(200, result)
            if method == "POST" and path.startswith("/api/projects/") and path.endswith("/p6/resource-spreads"):
                if self._p6_resource_spread_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/p6/resource-spreads")].rstrip("/")
                if not project_id:
                    return self._error(400, "P6_RESOURCE_SPREAD_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                try:
                    payload = json.loads(body.decode("utf-8") or "{}")
                except json.JSONDecodeError:
                    return self._error(400, "P6_RESOURCE_SPREAD_REQUEST_INVALID", "error.request.invalid")
                if not isinstance(payload, dict):
                    return self._error(400, "P6_RESOURCE_SPREAD_REQUEST_INVALID", "error.request.invalid")
                try:
                    bucket = P6ResourceSpreadBucket(
                        scope=BackendScope(context.tenant_id, context.project_id, context.revision),
                        spread_id=payload.get("spread_id", ""),
                        resource_id=payload.get("resource_id", ""),
                        period_id=payload.get("period_id", ""),
                        period_start=payload.get("period_start", ""),
                        period_end=payload.get("period_end", ""),
                        spread_type=payload.get("spread_type", ""),
                        metric=payload.get("metric", ""),
                        value=__import__("decimal", fromlist=["Decimal"]).Decimal(str(payload.get("value", ""))),
                        unit=payload.get("unit"),
                        currency=payload.get("currency"),
                    )
                    result = self._p6_resource_spread_api.save(bucket, auth_context=auth)
                except (TypeError, ValueError, ArithmeticError):
                    return self._error(400, "P6_RESOURCE_SPREAD_REQUEST_INVALID", "error.request.invalid")
                return self._json(200, result)
            if method == "GET" and path.startswith("/api/projects/") and path.endswith("/p6/baselines"):
                if self._p6_baseline_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/p6/baselines")].rstrip("/")
                if not project_id:
                    return self._error(400, "P6_BASELINE_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                result = self._p6_baseline_api.list(
                    BackendScope(context.tenant_id, context.project_id, context.revision),
                    auth_context=auth,
                )
                return self._json(200, {
                    "contract_version": P6_BASELINE_API_VERSION,
                    "baselines": list(result),
                })
            if method == "GET" and path.startswith("/api/projects/") and "/p6/baselines/" in path:
                if self._p6_baseline_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, baseline_id = path.split("/p6/baselines/", 1)
                project_id = prefix[len("/api/projects/"):]
                if not project_id or not baseline_id or "/" in baseline_id:
                    return self._error(400, "P6_BASELINE_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                result = self._p6_baseline_api.get(
                    BackendScope(context.tenant_id, context.project_id, context.revision),
                    baseline_id,
                    auth_context=auth,
                )
                if result is None:
                    return self._error(404, "P6_BASELINE_NOT_FOUND", "error.p6.baseline.not_found")
                return self._json(200, result)
            if method == "POST" and path.startswith("/api/projects/") and path.endswith("/p6/baselines"):
                if self._p6_baseline_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/p6/baselines")].rstrip("/")
                if not project_id:
                    return self._error(400, "P6_BASELINE_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                try:
                    payload = json.loads(body.decode("utf-8") or "{}")
                except json.JSONDecodeError:
                    return self._error(400, "P6_BASELINE_REQUEST_INVALID", "error.request.invalid")
                if not isinstance(payload, dict):
                    return self._error(400, "P6_BASELINE_REQUEST_INVALID", "error.request.invalid")
                baseline = P6Baseline(
                    scope=BackendScope(context.tenant_id, context.project_id, context.revision),
                    baseline_id=payload.get("baseline_id", ""),
                    name=payload.get("name", ""),
                    baseline_type=payload.get("baseline_type", ""),
                    source_revision=payload.get("source_revision", -1),
                    created_at=payload.get("created_at", ""),
                    notes=payload.get("notes"),
                )
                try:
                    result = self._p6_baseline_api.create(baseline, auth_context=auth)
                except (TypeError, ValueError):
                    return self._error(400, "P6_BASELINE_REQUEST_INVALID", "error.request.invalid")
                return self._json(200, result)
            if method == "POST" and path.startswith("/api/projects/") and "/p6/fields/" in path:
                if self._p6_field_registry_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, registry_version = path.split("/p6/fields/", 1)
                project_id = prefix[len("/api/projects/"):]
                if not project_id or not registry_version or "/" in registry_version:
                    return self._error(400, "P6_FIELD_REGISTRY_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                payload = json.loads(body.decode("utf-8") or "{}")
                if not isinstance(payload, dict):
                    return self._error(400, "P6_FIELD_REQUEST_INVALID", "error.request.invalid")
                field = P6FieldDefinition(
                    field_id=str(payload.get("field_id", "")),
                    subject_area=str(payload.get("subject_area", "")),
                    p6_field=str(payload.get("p6_field", "")),
                    display_name=str(payload.get("display_name", "")),
                    data_type=P6FieldType(str(payload.get("data_type", ""))),
                    writable=bool(payload.get("writable", False)),
                    computed=bool(payload.get("computed", False)),
                    unit=payload.get("unit"),
                    source=payload.get("source", P6_FIELD_REGISTRY_REFERENCE_PRODUCT),
                    reference_url=payload.get("reference_url", P6FieldDefinition.reference_url),
                    read_only=payload.get("read_only"),
                    filterable=payload.get("filterable"),
                    orderable=payload.get("orderable"),
                    nullable=payload.get("nullable"),
                    disposition=payload.get("disposition", P6_FIELD_REGISTRY_STATUS),
                )
                result = self._p6_field_registry_api.save_field(
                    BackendScope(context.tenant_id, context.project_id, context.revision),
                    registry_version,
                    field,
                    auth_context=auth,
                )
                return self._json(200, {"contract_version": P6_FIELD_REGISTRY_API_VERSION, **result["field"]})

            if method == "GET" and path.startswith("/api/projects/") and "/p6/fields/" in path:
                if self._p6_field_registry_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, registry_version = path.split("/p6/fields/", 1)
                project_id = prefix[len("/api/projects/"):]
                if not project_id or not registry_version or "/" in registry_version:
                    return self._error(400, "P6_FIELD_REGISTRY_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                fields = self._p6_field_registry_api.list_fields(
                    BackendScope(context.tenant_id, context.project_id, context.revision),
                    registry_version,
                    "Activity",
                    auth_context=auth,
                )
                return self._json(200, {
                    "contract_version": P6_FIELD_REGISTRY_API_VERSION,
                    "registry_version": registry_version,
                    "reference_product": P6_FIELD_REGISTRY_REFERENCE_PRODUCT,
                    "reference_version": P6_FIELD_REGISTRY_REFERENCE_VERSION,
                    "status": P6_FIELD_REGISTRY_STATUS,
                    "fields": [item["field"] for item in fields],
                })
            if method == "POST" and path.startswith("/api/projects/") and "/p6/udfs/" in path:
                if self._p6_field_registry_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, registry_version = path.split("/p6/udfs/", 1)
                project_id = prefix[len("/api/projects/"):]
                if not project_id or not registry_version or "/" in registry_version:
                    return self._error(400, "P6_UDF_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                payload = json.loads(body.decode("utf-8") or "{}")
                if not isinstance(payload, dict):
                    return self._error(400, "P6_UDF_REQUEST_INVALID", "error.request.invalid")
                try:
                    definition = P6UserDefinedFieldDefinition(
                        scope=BackendScope(context.tenant_id, context.project_id, context.revision),
                        registry_version=registry_version,
                        udf_id=str(payload.get("udf_id", "")),
                        subject_area=str(payload.get("subject_area", "")),
                        display_name=str(payload.get("display_name", "")),
                        data_type=P6FieldType(str(payload.get("data_type", ""))),
                        writable=bool(payload.get("writable", False)),
                        nullable=bool(payload.get("nullable", False)),
                        unit=payload.get("unit"),
                        allowed_values=tuple(payload.get("allowed_values", ())),
                    )
                except (TypeError, ValueError):
                    return self._error(400, "P6_UDF_REQUEST_INVALID", "error.request.invalid")
                result = self._p6_field_registry_api.save_udf(definition, auth_context=auth)
                return self._json(200, {"contract_version": P6_FIELD_REGISTRY_API_VERSION, **result["udf"]})

            if method == "GET" and path.startswith("/api/projects/") and "/p6/udfs/" in path:
                if self._p6_field_registry_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, registry_version = path.split("/p6/udfs/", 1)
                project_id = prefix[len("/api/projects/"):]
                if not project_id or not registry_version or "/" in registry_version:
                    return self._error(400, "P6_UDF_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                udfs = self._p6_field_registry_api.list_udfs(
                    BackendScope(context.tenant_id, context.project_id, context.revision),
                    registry_version,
                    "Activity",
                    auth_context=auth,
                )
                return self._json(200, {
                    "contract_version": P6_FIELD_REGISTRY_API_VERSION,
                    "registry_version": registry_version,
                    "udfs": [item["udf"] for item in udfs],
                })
            if method == "POST" and path.startswith("/api/projects/") and "/p6/formulas/" in path:
                if self._p6_formula_authority_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, registry_version = path.split("/p6/formulas/", 1)
                project_id = prefix[len("/api/projects/"):]
                if not project_id or not registry_version or "/" in registry_version:
                    return self._error(400, "P6_FORMULA_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                payload = json.loads(body.decode("utf-8") or "{}")
                if not isinstance(payload, dict) or not isinstance(payload.get("expression"), str):
                    return self._error(400, "P6_FORMULA_REQUEST_INVALID", "error.request.invalid")
                context_field_id = payload.get("context_field_id")
                if context_field_id is not None and not isinstance(context_field_id, str):
                    return self._error(400, "P6_FORMULA_REQUEST_INVALID", "error.request.invalid")
                result = self._p6_formula_authority_api.validate(
                    BackendScope(context.tenant_id, context.project_id, context.revision),
                    registry_version,
                    payload["expression"],
                    auth_context=auth,
                    context_field_id=context_field_id,
                )
                return self._json(200, result)
            if method == "POST" and path.startswith("/api/projects/") and "/p6/layouts/" in path:
                if self._p6_layout_definition_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, layout_path = path.split("/p6/layouts/", 1)
                project_id = prefix[len("/api/projects/"):]
                parts = layout_path.split("/", 1)
                if not project_id or len(parts) != 2 or not all(parts):
                    return self._error(400, "P6_LAYOUT_REQUEST_INVALID", "error.request.invalid")
                layout_scope, view_id = parts
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                payload = json.loads(body.decode("utf-8") or "{}")
                if not isinstance(payload, dict):
                    return self._error(400, "INVALID_LAYOUT_REQUEST", "error.request.invalid")
                revision = int(payload.get("revision", 0))
                raw_columns = payload.get("columns", [])
                if not isinstance(raw_columns, list):
                    return self._error(400, "INVALID_LAYOUT_COLUMNS", "error.request.invalid")
                columns = tuple(LayoutColumn(**item) for item in raw_columns)
                metadata = payload.get("metadata", {})
                if not isinstance(metadata, dict):
                    return self._error(400, "INVALID_LAYOUT_METADATA", "error.request.invalid")
                layout = PersistedP6Layout(
                    BackendScope(context.tenant_id, context.project_id, context.revision),
                    layout_scope,
                    view_id,
                    revision,
                    columns,
                    metadata,
                )
                result = self._p6_layout_definition_api.save(layout, auth_context=auth)
                return self._json(200, {"contract_version": P6_LAYOUT_DEFINITION_API_VERSION, **result["layout"]})
            if method == "GET" and path.startswith("/api/projects/") and "/p6/layouts/" in path:
                if self._p6_layout_definition_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, layout_path = path.split("/p6/layouts/", 1)
                project_id = prefix[len("/api/projects/"):]
                parts = layout_path.split("/", 1)
                if not project_id or len(parts) != 2 or not all(parts):
                    return self._error(400, "P6_LAYOUT_REQUEST_INVALID", "error.request.invalid")
                layout_scope, view_id = parts
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                result = self._p6_layout_definition_api.get(
                    BackendScope(context.tenant_id, context.project_id, context.revision),
                    layout_scope,
                    view_id,
                    auth_context=auth,
                )
                if result is None:
                    return self._error(404, "P6_LAYOUT_NOT_FOUND", "error.p6.layout.not_found")
                return self._json(200, {"contract_version": P6_LAYOUT_DEFINITION_API_VERSION, **result["layout"]})
            if method == "GET" and path.startswith("/api/projects/") and path.endswith("/p6/codes"):
                if self._p6_code_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/p6/codes")].rstrip("/")
                if not project_id:
                    return self._error(400, "P6_CODE_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED": return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                result = self._p6_code_api.list(BackendScope(context.tenant_id, context.project_id, context.revision), auth_context=auth)
                return self._json(200, {"contract_version": P6_CODE_API_VERSION, "codes": list(result)})
            if method == "GET" and path.startswith("/api/projects/") and "/p6/codes/" in path:
                if self._p6_code_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, code_id = path.split("/p6/codes/", 1)
                project_id = prefix[len("/api/projects/"):]
                if not project_id or not code_id or "/" in code_id:
                    return self._error(400, "P6_CODE_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED": return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                result = self._p6_code_api.get(BackendScope(context.tenant_id, context.project_id, context.revision), code_id, auth_context=auth)
                if result is None: return self._error(404, "P6_CODE_NOT_FOUND", "error.p6.code.not_found")
                return self._json(200, result)
            if method == "POST" and path.startswith("/api/projects/") and path.endswith("/p6/codes"):
                if self._p6_code_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/p6/codes")].rstrip("/")
                if not project_id: return self._error(400, "P6_CODE_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED": return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                try:
                    payload = json.loads(body.decode("utf-8") or "{}")
                    if not isinstance(payload, dict): raise ValueError
                    raw_values = payload.get("values", [])
                    if not isinstance(raw_values, list): raise ValueError
                    values = tuple(P6CodeValue(value_id=item.get("value_id", ""), value=item.get("value", ""), description=item.get("description")) for item in raw_values if isinstance(item, dict))
                    if len(values) != len(raw_values): raise ValueError
                    definition = P6CodeDefinition(BackendScope(context.tenant_id, context.project_id, context.revision), payload.get("code_id", ""), payload.get("name", ""), payload.get("subject_area", ""), payload.get("scope_kind", ""), payload.get("scope_key", ""), values)
                    result = self._p6_code_api.create(definition, auth_context=auth)
                except (TypeError, ValueError): return self._error(400, "P6_CODE_REQUEST_INVALID", "error.request.invalid")
                return self._json(200, result)
            if method == "POST" and path.startswith("/api/projects/") and path.endswith("/open"):
                project_id = path[len("/api/projects/"):-len("/open")]
                if not project_id:
                    return self._error(400, "PROJECT_ID_REQUIRED", "error.project.id_required")
                response = self._api.open_project(session_id, project_id, now=now)
                return self._json(200, {"context": asdict(response.context)})
            if method == "POST" and path == "/api/projects":
                payload = json.loads(body.decode("utf-8") or "{}")
                response = self._api.create_project(
                    session_id,
                    str(payload.get("project_id", "")),
                    str(payload.get("name", "")),
                    now=now,
                )
                return self._json(201, {"context": asdict(response.context)})
            return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
        except SessionError as exc:
            return self._error(401, str(exc), "error.session.invalid")
        except AuthorizationError as exc:
            return self._error(403, str(exc), "error.authorization.denied")
        except ProjectLifecycleError as exc:
            return self._error(400, str(exc), "error.project.lifecycle")
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self._error(400, str(exc) or "INVALID_REQUEST", "error.request.invalid")

    @staticmethod
    def _json(status: int, payload: object) -> tuple[int, dict[str, str], bytes]:
        return (
            status,
            {"Content-Type": "application/json; charset=utf-8"},
            json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8"),
        )

    @classmethod
    def _error(
        cls, status: int, code: str, message_key: str
    ) -> tuple[int, dict[str, str], bytes]:
        return cls._json(status, {
            "code": code,
            "retryable": status >= 500,
            "message_key": message_key,
            "available_actions": ["retry"] if status >= 500 else [],
        })
