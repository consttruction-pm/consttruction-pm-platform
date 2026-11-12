from __future__ import annotations

import json
from decimal import Decimal
from urllib.parse import parse_qs, unquote, urlsplit
from dataclasses import asdict, fields as dataclass_fields
from datetime import date, datetime, time, timezone
from typing import Callable, Mapping, Protocol

from ..application.authorization import AuthorizationContext, AuthorizationError, Permission
from ..change_claim_api import (
    ChangeClaimAPI, ChangeClaimCreateRequest, ChangeClaimReadRequest,
    P0_CHANGE_CLAIM_API_VERSION,
)
from ..change_claims import ChangeClaimStatus, ChangeClaimType
from ..application.project_lifecycle import ProjectLifecycleError, SessionError
from ..application.project_lifecycle_api import ProjectLifecycleAPI
from ..ai_action_runtime import AIActionRuntime, AIActionRuntimeContext, AIActionRuntimeError
from ..ai_assistant_orchestration import (
    AIAssistantProviderError,
    AIAssistantTurnOrchestrator,
    is_valid_language_tag,
)
from ..backend_p0.api import BackendP0API
from ..backend_p0.errors import BackendApplicationError
from ..backend_p0.workspace_read import WorkspaceControlRoomReadService
from ..backend_p0.schedule_query import SCHEDULE_QUERY_VERSION, ScheduleQueryAPI
from ..scheduling_code_reference_api import build_scheduling_code_reference_payload
from ..control_intelligence.contracts import ControlScope
from ..control_intelligence.query import ScheduleQueryKind, ScheduleQueryRequest
from ..backend_p0.models import BackendScope
from ..calendar_master_repository import CalendarMasterRepository, SQLiteCalendarMasterRepository
from ..calendar_snapshot_repository import SQLiteCalendarSnapshotRepository
from ..p6_calendar_read_api import P6CalendarReadAPI
from ..p6_calendar_api import P6CalendarAPI, P6CalendarCreateRequest, P6_CALENDAR_API_VERSION
from ..calendar_exception_repository import CalendarException
from ..calendar_work_hours_repository import CalendarWorkHourRule
from ..scheduling.calendar_system import CalendarSystem, JalaliDate
from ..scheduling.evm_source import (
    EarnedValuePVBucket,
    EarnedValuePVCurve,
    EarnedValuePVCurvePoint,
    EarnedValueSourceError,
    EarnedValueTechniqueOverride,
    EarnedValueWBSMilestone,
)
from ..scheduling.activity import (
    ActivityLevelingPriority as P6ActivityLevelingPriority,
    ActivityStatus as P6ActivityStatus,
    ActivityStatusCode as P6ActivityStatusCode,
    ActivityType as P6ActivityType,
    PercentCompleteType as P6ActivityPercentCompleteType,
)
from ..scheduling.time_duration import DurationUnit as P6ActivityDurationUnit
from ..p6_baseline_api import P6BaselineAPI, P6_BASELINE_API_VERSION
from ..p6_baseline_update import (
    BASELINE_UPDATE_FIELDS,
    P6BaselineUpdateError,
    P6BaselineUpdateSelection,
)
from ..p6_baseline_update_api import (
    P6_BASELINE_UPDATE_API_VERSION,
    P6BaselineUpdateAPI,
)
from ..p6_baseline_repository import P6Baseline
from ..p6_baseline_activity_repository import P6BaselineActivityPersistenceError
from ..p6_baseline_repository import P6BaselinePersistenceError
from ..p6_baseline_assignment import P6BaselineAssignmentError
from ..p6_baseline_assignment_api import (
    P6_BASELINE_ASSIGNMENT_API_VERSION,
    P6BaselineAssignmentAPI,
)
from ..p6_baseline_conversion import P6BaselineConversionError
from ..p6_baseline_conversion_api import (
    P6_BASELINE_CONVERSION_API_VERSION,
    P6BaselineConversionAPI,
)
from ..p6_current_activity_value_repository import (
    P6CurrentActivityPersistenceError,
)
from ..p6_earned_value_read_model import (
    P6_EARNED_VALUE_READ_MODEL_VERSION,
    P6EarnedValueReadModelError,
    P6EarnedValueSettings,
)
from ..p6_earned_value_read_model_api import P6EarnedValueReadModelAPI
from ..p6_activity_period_actual_repository import (
    P6ActivityPeriodActualPersistenceError,
)
from ..p6_expense_repository import P6ExpensePersistenceError
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
from ..p6_formula_column import (
    P6_FORMULA_COLUMN_API_VERSION,
    P6FormulaColumnAPI,
    P6FormulaColumnError,
)
from ..p6_financial_period_api import P6FinancialPeriodAPI, P6_FINANCIAL_PERIOD_API_VERSION
from ..p6_expense_api import P6ExpenseAPI, P6_EXPENSE_API_VERSION
from ..p6_cost_account_api import P6CostAccountAPI, P6_COST_ACCOUNT_API_VERSION
from ..p6_cost_account_repository import P6CostAccount
from ..p6_activity_period_actual_api import P6ActivityPeriodActualAPI, P6_ACTIVITY_PERIOD_ACTUAL_API_VERSION
from ..p6_relationship_api import P6RelationshipAPI, P6_RELATIONSHIP_API_VERSION
from ..p6_activity_master_api import P6ActivityMasterAPI, P6_ACTIVITY_MASTER_API_VERSION
from ..p6_wbs_master_api import P6WBSMasterAPI, P6_WBS_MASTER_API_VERSION
from ..wbs_master_repository import WBSMaster, WBSParentKind, WBSPersistenceError
from ..activity_master_repository import ActivityMaster, ActivityPersistenceError
from ..authoritative_schedule_input_composer import (
    ScheduleInputCompositionError,
)
from ..p6_schedule_snapshot_publication_api import (
    P6_PROJECT_SCHEDULE_SETTINGS_API_VERSION,
    P6_SCHEDULE_SNAPSHOT_API_VERSION,
    P6ScheduleSnapshotPublicationAPI,
)
from ..schedule_snapshot_publisher import ScheduleSnapshotPublicationError
from ..schedule_snapshot_materializer import parse_schedule_options_payload
from ..project_schedule_settings_repository import (
    ProjectScheduleSettings,
    ProjectScheduleSettingsPersistenceError,
)
from ..scheduling.calendar_context import CalendarReference
from ..scheduling.schedule_options import ScheduleOptions
from ..scheduling.authoritative_schedule import AuthoritativeScheduleMode
from ..relationship_master_repository import RelationshipPersistenceError
from ..p6_role_api import P6RoleAPI, P6_ROLE_API_VERSION
from ..p6_role_details_api import P6RoleDetailsAPI
from ..p6_resource_master_api import P6ResourceAPI, P6_RESOURCE_API_VERSION
from ..p6_expense_repository import P6Expense
from ..p6_financial_period_repository import P6FinancialPeriod
from ..p6_mapping_api import P6MappingAPI, P6_MAPPING_API_VERSION
from ..p6_interchange_api import P6InterchangeAPI, P6_INTERCHANGE_API_VERSION
from .form_builder_routes import FormBuilderHttpRoutes, ORGANIZATION_ROUTE
from ..p6_resource_read_api import P6ResourceReadAPI, P6_RESOURCE_READ_API_VERSION
from ..p6_resource_capacity_read_api import (
    P6ResourceCapacityReadAPI,
    P6_RESOURCE_CAPACITY_READ_API_VERSION,
)
from ..p6_resource_capacity_write_api import (
    P6ResourceCapacityWriteAPI,
    P6_RESOURCE_CAPACITY_WRITE_API_VERSION,
)
from ..p6_resource_rate_read_api import (
    P6ResourceRateReadAPI,
    P6_RESOURCE_RATE_READ_API_VERSION,
)
from ..p6_resource_rate_write_api import (
    P6ResourceRateWriteAPI,
    P6_RESOURCE_RATE_WRITE_API_VERSION,
)
from ..resources.max_units_time import ResourceCapacityBasis
from ..p6_resource_write_api import P6ResourceWriteAPI, P6_RESOURCE_WRITE_API_VERSION
from ..p6_resource_assignment_repository import (
    P6ResourceAssignment,
    P6ResourceAssignmentPeriodValue,
    P6ResourceAssignmentPersistenceError,
)
from ..p6_resource_spread_api import P6ResourceSpreadAPI, P6_RESOURCE_SPREAD_API_VERSION
from ..p6_resource_spread_repository import P6ResourceSpreadBucket
from ..p6_code_api import P6CodeAPI, P6_CODE_API_VERSION
from ..p6_code_repository import P6CodeDefinition, P6CodeValue
from ..p6_mapping_registry import P6MappingDefinition, P6MappingFormat, P6MappingStatus, PersistedP6Mapping
from ..p6_layout_definition_api import P6LayoutDefinitionAPI, P6_LAYOUT_DEFINITION_API_VERSION
from ..p6_layout_definition_repository import (
    PersistedP6Layout,
    P6LayoutPersistenceError,
    layout_column_from_mapping,
)
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
        p6_formula_column_api: P6FormulaColumnAPI | None = None,
        p6_calendar_read_api: P6CalendarReadAPI | None = None,
        p6_calendar_api: P6CalendarAPI | None = None,
        p6_baseline_api: P6BaselineAPI | None = None,
        p6_baseline_update_api: P6BaselineUpdateAPI | None = None,
        p6_baseline_assignment_api: P6BaselineAssignmentAPI | None = None,
        p6_baseline_conversion_api: P6BaselineConversionAPI | None = None,
        p6_earned_value_read_api: P6EarnedValueReadModelAPI | None = None,
        change_claim_api: ChangeClaimAPI | None = None,
        p6_financial_period_api: P6FinancialPeriodAPI | None = None,
        p6_expense_api: P6ExpenseAPI | None = None,
        p6_cost_account_api: P6CostAccountAPI | None = None,
        p6_activity_period_actual_api: P6ActivityPeriodActualAPI | None = None,
        p6_activity_master_api: P6ActivityMasterAPI | None = None,
        p6_wbs_master_api: P6WBSMasterAPI | None = None,
        p6_schedule_snapshot_api: P6ScheduleSnapshotPublicationAPI | None = None,
        p6_relationship_api: P6RelationshipAPI | None = None,
        p6_role_api: P6RoleAPI | None = None,
        p6_role_details_api: P6RoleDetailsAPI | None = None,
        p6_resource_api: P6ResourceAPI | None = None,
        p6_mapping_api: P6MappingAPI | None = None,
        p6_interchange_api: P6InterchangeAPI | None = None,
        p6_resource_read_api: P6ResourceReadAPI | None = None,
        p6_resource_capacity_read_api: P6ResourceCapacityReadAPI | None = None,
        p6_resource_capacity_write_api: P6ResourceCapacityWriteAPI | None = None,
        p6_resource_rate_read_api: P6ResourceRateReadAPI | None = None,
        p6_resource_rate_write_api: P6ResourceRateWriteAPI | None = None,
        p6_resource_write_api: P6ResourceWriteAPI | None = None,
        p6_resource_spread_api: P6ResourceSpreadAPI | None = None,
        p6_code_api: P6CodeAPI | None = None,
        dependency_graph_api: DependencyGraphAPI | None = None,
        sync_endpoint_factory: Callable[[str, str], VersionedSyncEndpoint] | None = None,
        backend_p0_api: BackendP0API | None = None,
        workspace_read_v2_service: WorkspaceControlRoomReadService | None = None,
        schedule_query_api: ScheduleQueryAPI | None = None,
        ai_action_runtime: AIActionRuntime | None = None,
        ai_assistant_orchestrator: AIAssistantTurnOrchestrator | None = None,
        form_builder_api: object | None = None,
    ) -> None:
        self._api = api
        self._clock = clock or UtcClock()
        self._p6_field_registry_api = p6_field_registry_api
        self._p6_layout_definition_api = p6_layout_definition_api
        self._p6_formula_authority_api = p6_formula_authority_api
        self._p6_formula_column_api = p6_formula_column_api
        self._p6_calendar_read_api = p6_calendar_read_api
        self._p6_calendar_api = p6_calendar_api
        self._p6_baseline_api = p6_baseline_api
        self._p6_baseline_update_api = p6_baseline_update_api
        self._p6_baseline_assignment_api = p6_baseline_assignment_api
        self._p6_baseline_conversion_api = p6_baseline_conversion_api
        self._p6_earned_value_read_api = p6_earned_value_read_api
        self._change_claim_api = change_claim_api
        self._p6_financial_period_api = p6_financial_period_api
        self._p6_expense_api = p6_expense_api
        self._p6_cost_account_api = p6_cost_account_api
        self._p6_activity_period_actual_api = p6_activity_period_actual_api
        self._p6_activity_master_api = p6_activity_master_api
        self._p6_wbs_master_api = p6_wbs_master_api
        self._p6_schedule_snapshot_api = p6_schedule_snapshot_api
        self._p6_relationship_api = p6_relationship_api
        self._p6_role_api = p6_role_api
        self._p6_role_details_api = p6_role_details_api
        self._p6_resource_api = p6_resource_api
        self._p6_mapping_api = p6_mapping_api
        self._p6_interchange_api = p6_interchange_api
        self._p6_resource_read_api = p6_resource_read_api
        self._p6_resource_capacity_read_api = p6_resource_capacity_read_api
        self._p6_resource_capacity_write_api = p6_resource_capacity_write_api
        self._p6_resource_rate_read_api = p6_resource_rate_read_api
        self._p6_resource_rate_write_api = p6_resource_rate_write_api
        self._p6_resource_write_api = p6_resource_write_api
        self._p6_resource_spread_api = p6_resource_spread_api
        self._p6_code_api = p6_code_api
        self._dependency_graph_api = dependency_graph_api
        self._sync_endpoint_factory = sync_endpoint_factory
        self._backend_p0_api = backend_p0_api
        self._workspace_read_v2_service = workspace_read_v2_service
        self._schedule_query_api = schedule_query_api
        self._ai_action_runtime = ai_action_runtime
        self._ai_assistant_orchestrator = ai_assistant_orchestrator
        self._form_builder_routes = (
            FormBuilderHttpRoutes(form_builder_api)  # type: ignore[arg-type]
            if form_builder_api is not None
            else None
        )

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
            if self._form_builder_routes is not None:
                form_path = urlsplit(path).path
                if form_path.startswith(ORGANIZATION_ROUTE) or (
                    form_path.startswith("/api/projects/") and "/forms" in form_path
                ):
                    return self._handle_form_route(
                        method, path, session_id=session_id, now=now, body=body, headers=request_headers
                    )
            baseline_update_response = self._handle_baseline_update_route(
                method, path, session_id=session_id, now=now, body=body
            )
            if baseline_update_response is not None:
                return baseline_update_response
            baseline_role_response = self._handle_baseline_role_route(
                method, path, session_id=session_id, now=now, body=body
            )
            if baseline_role_response is not None:
                return baseline_role_response
            earned_value_response = self._handle_earned_value_route(
                method, path, session_id=session_id, now=now, body=body
            )
            if earned_value_response is not None:
                return earned_value_response
            if method == "GET" and path == "/api/v1/schedule/code-reference":
                # The catalogue contains no project records, but a valid active session is required.
                self._api.get_session(session_id, now=now)
                return self._json(200, build_scheduling_code_reference_payload())
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
            if method == "GET" and path.startswith("/api/projects/") and path.count("/") == 3:
                project_id = path[len("/api/projects/"):]
                if not project_id:
                    return self._error(400, "PROJECT_ID_REQUIRED", "error.project.id_required")
                project = self._api.get_project(session_id, project_id, now=now)
                return self._json(200, {"project": asdict(project)})
            if method == "GET" and path in (
                "/api/v1/workspace/control-room/read",
                "/api/v2/workspace/control-room/read",
            ):
                is_v2_workspace_read = path == "/api/v2/workspace/control-room/read"
                if is_v2_workspace_read and self._workspace_read_v2_service is None:
                    return self._error(404, "WORKSPACE_READ_NOT_CONFIGURED", "error.route.not_found")
                if not is_v2_workspace_read and self._backend_p0_api is None:
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
                if revision != context.revision and is_v2_workspace_read:
                    # The v2 scope must match the authoritative project revision;
                    # a stale client never reads a different revision.
                    return self._error(
                        409,
                        "STALE_WORKSPACE_READ_SCOPE",
                        "error.workspace_read.stale_scope",
                    )
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                if is_v2_workspace_read:
                    try:
                        result = self._workspace_read_v2_service.read(
                            BackendScope(context.tenant_id, context.project_id, revision),
                            auth_context=auth,
                        )
                    except BackendApplicationError as exc:
                        result = exc.to_dto()
                else:
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
                    context = self._api.authorize_project(
                        session_id, payload["project_id"], Permission.PROJECT_WRITE, now=now
                    ).context
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
                            system=payload.get("system"),
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
                            # A GET cannot carry a JSON body, so listing without a
                            # kind returns every stored work-hour contract; the
                            # client groups the flat rows by their kind field.
                            kind = str(payload.get("kind", "")) if payload else ""
                            kinds = (kind,) if kind else (
                                "standard_work_week", "standard_detailed_work_hours",
                                "detailed_work_hours", "total_work_hours",
                            )
                            rules = [
                                rule
                                for current in kinds
                                for rule in self._p6_calendar_api.list_work_hours(scope, calendar_id, calendar_version, current, auth_context=auth)
                            ]
                            return self._json(200, {"contract_version": P6_CALENDAR_API_VERSION, "work_hours": rules})
                        if method == "POST" and resource == "exceptions":
                            raw_intervals = payload.get("intervals", [])
                            if not isinstance(raw_intervals, list): raise ValueError("invalid intervals")
                            intervals = tuple((time.fromisoformat(str(item[0])), time.fromisoformat(str(item[1]))) for item in raw_intervals if isinstance(item, (list, tuple)) and len(item) == 2)
                            if len(intervals) != len(raw_intervals): raise ValueError("invalid intervals")
                            calendar_system = CalendarSystem(str(payload.get("system", CalendarSystem.GREGORIAN.value)))
                            raw_date = str(payload.get("date", ""))
                            if calendar_system is CalendarSystem.JALALI:
                                date_parts = raw_date.split("-")
                                if len(date_parts) != 3 or any(not part.isdigit() for part in date_parts):
                                    raise ValueError("invalid Jalali date")
                                exception_date = JalaliDate(*(int(part) for part in date_parts))
                            else:
                                exception_date = date.fromisoformat(raw_date)
                            exception = CalendarException(
                                scope, calendar_id, calendar_version, exception_date,
                                str(payload.get("mode", "")), payload.get("total_work_hours"), intervals,
                                calendar_system,
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
                            if payload.get("replace") is True:
                                expected_revision = payload.get("expected_revision")
                                if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
                                    raise ValueError("expected_revision required")
                                return self._json(200, self._p6_calendar_api.replace_work_hours(
                                    rule, expected_revision=expected_revision, auth_context=auth
                                ))
                            return self._json(200, self._p6_calendar_api.save_work_hours(rule, auth_context=auth))
                    if len(parts) == 4 and parts[2] == "exceptions" and method in {"DELETE", "PUT"}:
                        calendar_id, calendar_version, _, raw_date = parts
                        exception_date = date.fromisoformat(unquote(raw_date))
                        if method == "DELETE":
                            deleted = self._p6_calendar_api.delete_exception(
                                scope, calendar_id, calendar_version, exception_date, auth_context=auth
                            )
                            return self._json(200, {"contract_version": P6_CALENDAR_API_VERSION, "deleted": deleted})
                        expected_revision = payload.get("expected_revision")
                        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
                            raise ValueError("expected_revision required")
                        raw_intervals = payload.get("intervals", [])
                        if not isinstance(raw_intervals, list):
                            raise ValueError("invalid intervals")
                        intervals = tuple(
                            (time.fromisoformat(str(item[0])), time.fromisoformat(str(item[1])))
                            for item in raw_intervals
                            if isinstance(item, (list, tuple)) and len(item) == 2
                        )
                        if len(intervals) != len(raw_intervals):
                            raise ValueError("invalid intervals")
                        return self._json(200, self._p6_calendar_api.revise_exception(
                            scope, calendar_id, calendar_version, exception_date,
                            mode=str(payload.get("mode", "")),
                            total_work_hours=payload.get("total_work_hours"),
                            intervals=intervals,
                            expected_revision=expected_revision,
                            auth_context=auth,
                        ))
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
                    parts = [unquote(part) for part in suffix.strip("/").split("/") if part]
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
                        parent = payload.get("parent_role_id")
                        if parent is not None and not isinstance(parent, str):
                            raise ValueError("INVALID_ROLE_PARENT")
                        calculate = payload.get("calculate_costs_from_units", True)
                        if not isinstance(calculate, bool):
                            raise ValueError("INVALID_ROLE_COST_FLAG")
                        role = P6Role(
                            scope.tenant_id, scope.project_id, scope.project_revision,
                            payload.get("role_id", ""), payload.get("name", ""),
                            payload.get("description"), 0, parent, calculate,
                        )
                        return self._json(200, self._p6_role_api.create(role, auth_context=auth))
                    if method == "PATCH" and len(parts) == 1 and parts[0]:
                        from ..p6_role_repository import P6Role
                        expected_revision = payload.get("expected_revision")
                        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
                            raise ValueError("expected_revision required")
                        parent = payload.get("parent_role_id")
                        if parent is not None and not isinstance(parent, str):
                            raise ValueError("INVALID_ROLE_PARENT")
                        calculate = payload.get("calculate_costs_from_units", True)
                        if not isinstance(calculate, bool):
                            raise ValueError("INVALID_ROLE_COST_FLAG")
                        role = P6Role(
                            scope.tenant_id, scope.project_id, scope.project_revision,
                            parts[0], payload.get("name", ""), payload.get("description"),
                            expected_revision, parent, calculate,
                        )
                        return self._json(200, self._p6_role_api.update(role, expected_revision=expected_revision, auth_context=auth))
                    if len(parts) >= 2 and parts[1] in {"rates", "limits", "resources"}:
                        if self._p6_role_details_api is None:
                            return self._error(503, "P6_ROLE_DETAILS_UNAVAILABLE", "error.request.invalid")
                        details = self._p6_role_details_api
                        role_id = parts[0]
                        kind = parts[1]
                        if kind == "rates":
                            if method == "GET" and len(parts) == 2:
                                return self._json(200, details.list_rates(
                                    context.tenant_id, context.project_id, context.revision,
                                    role_id, auth_context=auth,
                                ))
                            if method == "POST" and len(parts) == 2:
                                return self._json(200, details.save_rate(
                                    context.tenant_id, context.project_id, context.revision,
                                    role_id,
                                    effective_from=payload.get("effective_from"),
                                    rate_type=payload.get("rate_type"),
                                    rate=payload.get("rate"),
                                    unit=payload.get("unit"),
                                    currency=payload.get("currency"),
                                    expected_revision=None,
                                    auth_context=auth,
                                ))
                            if method == "PATCH" and len(parts) == 3:
                                return self._json(200, details.save_rate(
                                    context.tenant_id, context.project_id, context.revision,
                                    role_id,
                                    effective_from=parts[2],
                                    rate_type=payload.get("rate_type"),
                                    rate=payload.get("rate"),
                                    unit=payload.get("unit"),
                                    currency=payload.get("currency"),
                                    expected_revision=payload.get("expected_revision"),
                                    auth_context=auth,
                                ))
                        if kind == "limits":
                            if method == "GET" and len(parts) == 2:
                                return self._json(200, details.list_limits(
                                    context.tenant_id, context.project_id, context.revision,
                                    role_id, auth_context=auth,
                                ))
                            if method == "POST" and len(parts) == 2:
                                return self._json(200, details.save_limit(
                                    context.tenant_id, context.project_id, context.revision,
                                    role_id,
                                    effective_from=payload.get("effective_from"),
                                    max_units=payload.get("max_units"),
                                    unit_basis=payload.get("unit_basis"),
                                    expected_revision=None,
                                    auth_context=auth,
                                ))
                            if method == "PATCH" and len(parts) == 3:
                                return self._json(200, details.save_limit(
                                    context.tenant_id, context.project_id, context.revision,
                                    role_id,
                                    effective_from=parts[2],
                                    max_units=payload.get("max_units"),
                                    unit_basis=payload.get("unit_basis"),
                                    expected_revision=payload.get("expected_revision"),
                                    auth_context=auth,
                                ))
                        if kind == "resources":
                            if method == "GET" and len(parts) == 2:
                                return self._json(200, details.list_role_resources(
                                    context.tenant_id, context.project_id, context.revision,
                                    role_id, auth_context=auth,
                                ))
                            if method == "POST" and len(parts) == 2:
                                return self._json(200, details.save_role_resource(
                                    context.tenant_id, context.project_id, context.revision,
                                    role_id,
                                    resource_id=payload.get("resource_id"),
                                    proficiency=payload.get("proficiency"),
                                    is_primary=payload.get("is_primary", False),
                                    expected_revision=None,
                                    auth_context=auth,
                                ))
                            if method == "PATCH" and len(parts) == 3:
                                return self._json(200, details.save_role_resource(
                                    context.tenant_id, context.project_id, context.revision,
                                    role_id,
                                    resource_id=parts[2],
                                    proficiency=payload.get("proficiency"),
                                    is_primary=payload.get("is_primary", False),
                                    expected_revision=payload.get("expected_revision"),
                                    auth_context=auth,
                                ))
                            if method == "DELETE" and len(parts) == 3:
                                return self._json(200, details.remove_role_resource(
                                    context.tenant_id, context.project_id, context.revision,
                                    role_id, parts[2],
                                    expected_revision=payload.get("expected_revision"),
                                    auth_context=auth,
                                ))
                    raise ValueError("P6_ROLE_ROUTE_INVALID")
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                except (TypeError, ValueError, ArithmeticError, KeyError) as exc:
                    code = str(exc)
                    if code in {
                        "REVISION_CONFLICT",
                        "ROLE_ALREADY_EXISTS",
                        "ROLE_PARENT_NOT_FOUND",
                        "ROLE_HIERARCHY_CYCLE",
                        "ROLE_RATE_ALREADY_EXISTS",
                        "ROLE_RATE_LIMIT_EXCEEDED",
                        "ROLE_LIMIT_ALREADY_EXISTS",
                        "ROLE_RESOURCE_ALREADY_ASSIGNED",
                    }:
                        return self._error(409, code, "error.p6.role.conflict")
                    if code in {"ROLE_NOT_FOUND", "ROLE_RESOURCE_NOT_FOUND"}:
                        return self._error(404, code, "error.p6.role.not_found")
                    return self._error(
                        400,
                        code if code.startswith(("INVALID_", "ROLE_")) else "P6_ROLE_REQUEST_INVALID",
                        "error.request.invalid",
                    )
            if path.startswith("/api/projects/") and "/p6/resources" in path and self._p6_resource_api is not None:
                prefix = "/p6/resources"
                project_id = path[len("/api/projects/"):].split(prefix, 1)[0].rstrip("/")
                suffix = path[len("/api/projects/") + len(project_id) + len(prefix):]
                if not project_id:
                    return self._error(400, "P6_RESOURCE_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                try:
                    parts = suffix.strip("/").split("/") if suffix.strip("/") else []
                    payload = json.loads(body.decode("utf-8") or "{}") if body else {}
                    if not isinstance(payload, dict):
                        raise ValueError("invalid payload")
                    if method == "GET" and not parts:
                        result = self._p6_resource_api.list(
                            context.tenant_id, context.project_id, context.revision,
                            auth_context=auth,
                        )
                        return self._json(200, {
                            "contract_version": P6_RESOURCE_API_VERSION,
                            "resources": list(result),
                        })
                    if method == "GET" and len(parts) == 1 and parts[0]:
                        result = self._p6_resource_api.get(
                            context.tenant_id, context.project_id, context.revision,
                            parts[0], auth_context=auth,
                        )
                        if result is None:
                            return self._error(404, "P6_RESOURCE_NOT_FOUND", "error.p6.resource.not_found")
                        return self._json(200, result)
                    from ..p6_resource_master_repository import P6Resource
                    if method == "POST" and not parts:
                        resource = P6Resource(
                            context.tenant_id, context.project_id, context.revision,
                            payload.get("resource_id", ""), payload.get("name", ""),
                            payload.get("resource_type", "labor"),
                            payload.get("parent_resource_id"),
                            payload.get("calendar_id"),
                            None if payload.get("default_units_per_time") is None else str(payload.get("default_units_per_time")),
                            payload.get("unit_of_measure"), payload.get("email"),
                            payload.get("is_active", True),
                        )
                        return self._json(200, self._p6_resource_api.create(resource, auth_context=auth))
                    if method == "PATCH" and len(parts) == 1 and parts[0]:
                        expected_revision = payload.get("expected_revision")
                        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
                            raise ValueError("expected_revision required")
                        resource = P6Resource(
                            context.tenant_id, context.project_id, context.revision,
                            parts[0], payload.get("name", ""),
                            payload.get("resource_type", "labor"),
                            payload.get("parent_resource_id"),
                            payload.get("calendar_id"),
                            None if payload.get("default_units_per_time") is None else str(payload.get("default_units_per_time")),
                            payload.get("unit_of_measure"), payload.get("email"),
                            payload.get("is_active", True),
                        )
                        return self._json(200, self._p6_resource_api.update(
                            resource, expected_revision=expected_revision, auth_context=auth,
                        ))
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                except ValueError as exc:
                    code = str(exc)
                    if code == "REVISION_CONFLICT":
                        return self._error(409, code, "error.p6.resource.conflict")
                    if code in {
                        "RESOURCE_HIERARCHY_CYCLE",
                        "RESOURCE_PARENT_NOT_FOUND",
                        "RESOURCE_ALREADY_EXISTS",
                    }:
                        return self._error(409, code, "error.p6.resource.conflict")
                    if code == "RESOURCE_CALENDAR_NOT_FOUND":
                        return self._error(
                            409, code, "error.p6.resource.calendar_not_found"
                        )
                    return self._error(400, code if code.startswith(("INVALID_", "RESOURCE_")) else "P6_RESOURCE_REQUEST_INVALID", "error.request.invalid")
            if path.startswith("/api/projects/") and "/p6/cost-accounts" in path and self._p6_cost_account_api is not None:
                prefix = "/p6/cost-accounts"
                project_id = path[len("/api/projects/"):].split(prefix, 1)[0].rstrip("/")
                suffix = path[len("/api/projects/") + len(project_id) + len(prefix):]
                if not project_id:
                    return self._error(400, "P6_COST_ACCOUNT_REQUEST_INVALID", "error.request.invalid")
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
                        result = self._p6_cost_account_api.list(scope, auth_context=auth)
                        return self._json(200, {
                            "contract_version": P6_COST_ACCOUNT_API_VERSION,
                            "cost_accounts": list(result),
                        })
                    if method == "GET" and len(parts) == 1 and parts[0]:
                        result = self._p6_cost_account_api.get(scope, parts[0], auth_context=auth)
                        if result is None:
                            return self._error(404, "P6_COST_ACCOUNT_NOT_FOUND", "error.p6.cost_account.not_found")
                        return self._json(200, result)
                    if method == "POST" and not parts:
                        account = P6CostAccount(
                            scope=scope,
                            account_id=payload.get("account_id", ""),
                            name=payload.get("name", ""),
                            parent_account_id=payload.get("parent_account_id"),
                            description=payload.get("description"),
                        )
                        return self._json(200, self._p6_cost_account_api.create(account, auth_context=auth))
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                except (TypeError, ValueError, KeyError):
                    return self._error(400, "P6_COST_ACCOUNT_REQUEST_INVALID", "error.request.invalid")
            if path.startswith("/api/projects/") and "/p6/schedule/settings" in path and self._p6_schedule_snapshot_api is not None:
                prefix = "/p6/schedule/settings"
                project_id = path[len("/api/projects/"):].split(prefix, 1)[0].rstrip("/")
                suffix = path[len("/api/projects/") + len(project_id) + len(prefix):]
                if not project_id:
                    return self._error(400, "P6_PROJECT_SCHEDULE_SETTINGS_REQUEST_INVALID", "error.request.invalid")
                if suffix.strip("/"):
                    return self._error(405, "P6_PROJECT_SCHEDULE_SETTINGS_METHOD_NOT_ALLOWED", "error.request.invalid")
                if method not in {"GET", "POST"}:
                    return self._error(405, "P6_PROJECT_SCHEDULE_SETTINGS_METHOD_NOT_ALLOWED", "error.request.invalid")
                try:
                    project_context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = project_context.authorization_context(session.roles)
                scope = BackendScope(
                    project_context.tenant_id,
                    project_context.project_id,
                    project_context.revision,
                )
                try:
                    if method == "GET":
                        settings = self._p6_schedule_snapshot_api.get_settings(
                            scope, auth_context=auth
                        )
                        if settings is None:
                            return self._error(
                                404, "PROJECT_SCHEDULE_SETTINGS_NOT_FOUND", "error.resource.not_found"
                            )
                        return self._json(200, settings)

                    payload = json.loads(body.decode("utf-8") or "{}") if body else {}
                    if not isinstance(payload, dict):
                        raise ValueError("INVALID_PAYLOAD")
                    expected_fields = {
                        "contract_version",
                        "expected_record_revision",
                        "mode",
                        "project_calendar_id",
                        "project_calendar_version",
                        "project_calendar_system",
                        "project_start",
                        "project_finish",
                        "schedule_options",
                        "project_leveling_priority",
                    }
                    if set(payload) != expected_fields:
                        raise ValueError("PROJECT_SCHEDULE_SETTINGS_FIELDS_INVALID")
                    if payload.get("contract_version") != P6_PROJECT_SCHEDULE_SETTINGS_API_VERSION:
                        raise ValueError("INVALID_PROJECT_SCHEDULE_SETTINGS_CONTRACT_VERSION")

                    raw_expected_revision = payload.get("expected_record_revision")
                    if (
                        isinstance(raw_expected_revision, bool)
                        or not isinstance(raw_expected_revision, int)
                        or raw_expected_revision < 0
                    ):
                        raise ValueError("EXPECTED_RECORD_REVISION_REQUIRED")

                    raw_mode = payload.get("mode")
                    if not isinstance(raw_mode, str):
                        raise ValueError("SCHEDULE_MODE_REQUIRED")
                    mode = AuthoritativeScheduleMode(raw_mode)
                    expected_calendar_kind = (
                        "working-day"
                        if mode is AuthoritativeScheduleMode.DATE_BASED
                        else "working-time"
                    )

                    def required_text(field_name: str) -> str:
                        raw = payload.get(field_name)
                        if not isinstance(raw, str) or not raw.strip():
                            raise ValueError(field_name.upper() + "_REQUIRED")
                        return raw

                    def date_only(field_name: str, *, required: bool):
                        if field_name not in payload:
                            if required:
                                raise ValueError(field_name.upper() + "_REQUIRED")
                            return None
                        raw = payload[field_name]
                        if raw is None and not required:
                            return None
                        if not isinstance(raw, str) or not raw.strip() or "T" in raw:
                            raise ValueError("INVALID_" + field_name.upper())
                        try:
                            result = date.fromisoformat(raw)
                        except ValueError as exc:
                            raise ValueError("INVALID_" + field_name.upper()) from exc
                        if result.isoformat() != raw:
                            raise ValueError("INVALID_" + field_name.upper())
                        return result

                    def aware_datetime(field_name: str, *, required: bool):
                        if field_name not in payload:
                            if required:
                                raise ValueError(field_name.upper() + "_REQUIRED")
                            return None
                        raw = payload[field_name]
                        if raw is None and not required:
                            return None
                        if not isinstance(raw, str) or not raw.strip():
                            raise ValueError("INVALID_" + field_name.upper())
                        try:
                            result = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                        except ValueError as exc:
                            raise ValueError("INVALID_" + field_name.upper()) from exc
                        if result.tzinfo is None or result.utcoffset() is None:
                            raise ValueError("TIMEZONE_REQUIRED_FOR_" + field_name.upper())
                        return result

                    if "project_finish" not in payload:
                        raise ValueError("PROJECT_FINISH_FIELD_REQUIRED")
                    if mode is AuthoritativeScheduleMode.DATE_BASED:
                        project_start = date_only("project_start", required=True)
                        project_finish = date_only("project_finish", required=False)
                    else:
                        project_start = aware_datetime("project_start", required=True)
                        project_finish = aware_datetime("project_finish", required=False)

                    options_payload = payload.get("schedule_options")
                    if not isinstance(options_payload, dict):
                        raise ValueError("SCHEDULE_OPTIONS_REQUIRED")
                    expected_option_fields = {item.name for item in dataclass_fields(ScheduleOptions)}
                    if set(options_payload) != expected_option_fields:
                        raise ValueError("SCHEDULE_OPTIONS_SCHEMA_MISMATCH")
                    options = parse_schedule_options_payload(options_payload)

                    raw_priority = payload.get("project_leveling_priority")
                    if isinstance(raw_priority, bool) or not isinstance(raw_priority, int):
                        raise ValueError("PROJECT_LEVELING_PRIORITY_REQUIRED")

                    calendar_id = required_text("project_calendar_id")
                    calendar_version = required_text("project_calendar_version")
                    calendar_system = CalendarSystem(required_text("project_calendar_system"))
                    settings = ProjectScheduleSettings(
                        scope=scope,
                        mode=mode,
                        project_calendar=CalendarReference(
                            calendar_id,
                            calendar_version,
                            expected_calendar_kind,
                            calendar_system,
                        ),
                        project_start=project_start,
                        project_finish=project_finish,
                        schedule_options=options,
                        project_leveling_priority=raw_priority,
                    )
                    result = self._p6_schedule_snapshot_api.save_settings(
                        scope,
                        settings=settings,
                        expected_revision=raw_expected_revision,
                        auth_context=auth,
                    )
                    status_code = 201 if result["record_revision"] == 1 else 200
                    return self._json(status_code, result)
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                except ProjectScheduleSettingsPersistenceError as exc:
                    code = str(exc) or "P6_PROJECT_SCHEDULE_SETTINGS_REQUEST_INVALID"
                    if code == "REVISION_CONFLICT":
                        return self._error(409, code, "error.revision.conflict")
                    return self._error(400, code, "error.request.invalid")
                except (TypeError, ValueError, ArithmeticError, KeyError) as exc:
                    code = str(exc) or "P6_PROJECT_SCHEDULE_SETTINGS_REQUEST_INVALID"
                    return self._error(400, code, "error.request.invalid")
            if path.startswith("/api/projects/") and "/p6/schedule/snapshots" in path and self._p6_schedule_snapshot_api is not None:
                prefix = "/p6/schedule/snapshots"
                project_id = path[len("/api/projects/"):].split(prefix, 1)[0].rstrip("/")
                suffix = path[len("/api/projects/") + len(project_id) + len(prefix):]
                if not project_id:
                    return self._error(400, "P6_SCHEDULE_SNAPSHOT_REQUEST_INVALID", "error.request.invalid")
                if method != "POST" or suffix.strip("/"):
                    return self._error(405, "P6_SCHEDULE_SNAPSHOT_METHOD_NOT_ALLOWED", "error.request.invalid")
                try:
                    project_context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = project_context.authorization_context(session.roles)
                scope = BackendScope(
                    project_context.tenant_id,
                    project_context.project_id,
                    project_context.revision,
                )
                try:
                    payload = json.loads(body.decode("utf-8") or "{}") if body else {}
                    if not isinstance(payload, dict):
                        raise ValueError("INVALID_PAYLOAD")
                    if set(payload) != {"contract_version", "timezone"}:
                        raise ValueError("SCHEDULE_SNAPSHOT_REQUEST_FIELDS_INVALID")
                    if payload.get("contract_version") != P6_SCHEDULE_SNAPSHOT_API_VERSION:
                        raise ValueError("INVALID_SCHEDULE_SNAPSHOT_CONTRACT_VERSION")
                    timezone_name = payload.get("timezone")
                    if not isinstance(timezone_name, str) or not timezone_name.strip():
                        raise ValueError("CALCULATION_TIMEZONE_REQUIRED")
                    result = self._p6_schedule_snapshot_api.publish(
                        scope,
                        timezone_name=timezone_name,
                        auth_context=auth,
                        request_id=(headers or {}).get("X-Request-Id"),
                        idempotency_key=(headers or {}).get("Idempotency-Key"),
                    )
                    return self._json(201, result)
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                except ProjectScheduleSettingsPersistenceError as exc:
                    code = str(exc) or "P6_SCHEDULE_SNAPSHOT_REQUEST_INVALID"
                    if code == "REVISION_CONFLICT":
                        return self._error(409, code, "error.revision.conflict")
                    return self._error(400, code, "error.request.invalid")
                except (ScheduleInputCompositionError, ScheduleSnapshotPublicationError,
                        TypeError, ValueError, ArithmeticError, KeyError) as exc:
                    code = str(exc) or "P6_SCHEDULE_SNAPSHOT_REQUEST_INVALID"
                    return self._error(400, code, "error.request.invalid")
            if path.startswith("/api/projects/") and "/p6/activities" in path and self._p6_activity_master_api is not None:
                prefix = "/p6/activities"
                project_id = path[len("/api/projects/"):].split(prefix, 1)[0].rstrip("/")
                suffix = path[len("/api/projects/") + len(project_id) + len(prefix):]
                if not project_id:
                    return self._error(400, "P6_ACTIVITY_MASTER_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                scope = BackendScope(context.tenant_id, context.project_id, context.revision)

                def parse_activity_date(
                    field_name: str,
                    existing_value: date | datetime | None = None,
                ) -> date | datetime | None:
                    # PATCH distinguishes an omitted field (preserve current value)
                    # from an explicit null (clear an optional date field).
                    if field_name not in payload:
                        return existing_value
                    value = payload[field_name]
                    if value is None:
                        return None
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError("INVALID_" + field_name.upper())
                    try:
                        if "T" in value:
                            return datetime.fromisoformat(value.replace("Z", "+00:00"))
                        return date.fromisoformat(value)
                    except ValueError as exc:
                        raise ValueError("INVALID_" + field_name.upper()) from exc

                def build_activity(
                    activity_id: str,
                    existing: ActivityMaster | None = None,
                ) -> ActivityMaster:
                    duration_raw = payload.get(
                        "duration_value",
                        existing.duration_value if existing is not None else None,
                    )
                    if isinstance(duration_raw, bool) or duration_raw is None:
                        raise ValueError("INVALID_DURATION_VALUE")
                    duration_value = Decimal(str(duration_raw))
                    duration_unit_raw = payload.get(
                        "duration_unit",
                        existing.duration_unit.value if existing is not None else None,
                    )
                    duration_unit = P6ActivityDurationUnit(duration_unit_raw)
                    raw_remaining_duration = payload.get(
                        "remaining_duration",
                        existing.remaining_duration if existing is not None else None,
                    )
                    if raw_remaining_duration is not None and (
                        isinstance(raw_remaining_duration, bool)
                        or not isinstance(raw_remaining_duration, int)
                    ):
                        raise ValueError("INVALID_REMAINING_DURATION")
                    raw_original_duration = payload.get(
                        "original_duration",
                        existing.original_duration if existing is not None else None,
                    )
                    if raw_original_duration is not None and (
                        isinstance(raw_original_duration, bool)
                        or not isinstance(raw_original_duration, int)
                    ):
                        raise ValueError("INVALID_ORIGINAL_DURATION")
                    raw_percent = payload.get(
                        "percent_complete",
                        existing.percent_complete if existing is not None else None,
                    )
                    if raw_percent is not None and (
                        isinstance(raw_percent, bool)
                        or not isinstance(raw_percent, (int, float))
                    ):
                        raise ValueError("INVALID_PERCENT_COMPLETE")
                    raw_short_name = payload.get(
                        "short_name",
                        existing.short_name if existing is not None else None,
                    )
                    if raw_short_name is not None and (
                        not isinstance(raw_short_name, str) or not raw_short_name.strip()
                    ):
                        raise ValueError("INVALID_SHORT_NAME")
                    return ActivityMaster(
                        scope=scope,
                        activity_id=activity_id,
                        duration_value=duration_value,
                        duration_unit=duration_unit,
                        actual_start=parse_activity_date(
                            "actual_start", existing.actual_start if existing is not None else None
                        ),
                        actual_finish=parse_activity_date(
                            "actual_finish", existing.actual_finish if existing is not None else None
                        ),
                        remaining_duration=raw_remaining_duration,
                        remaining_start=parse_activity_date(
                            "remaining_start", existing.remaining_start if existing is not None else None
                        ),
                        percent_complete=None if raw_percent is None else float(raw_percent),
                        percent_complete_type=P6ActivityPercentCompleteType(
                            payload.get(
                                "percent_complete_type",
                                existing.percent_complete_type.value if existing is not None
                                else P6ActivityPercentCompleteType.DURATION.value,
                            )
                        ),
                        name=payload.get(
                            "name", existing.name if existing is not None else ""
                        ),
                        short_name=raw_short_name,
                        activity_type=P6ActivityType.from_p6_value(
                            payload.get(
                                "activity_type",
                                existing.activity_type.value if existing is not None
                                else P6ActivityType.TASK_DEPENDENT.value,
                            )
                        ),
                        status=P6ActivityStatus.from_p6_value(
                            payload.get(
                                "status",
                                existing.status.value if existing is not None
                                else P6ActivityStatus.NOT_STARTED.value,
                            )
                        ),
                        status_code=P6ActivityStatusCode.from_p6_value(
                            payload.get(
                                "status_code",
                                existing.status_code.value if existing is not None
                                else P6ActivityStatusCode.PLANNED.value,
                            )
                        ),
                        expected_finish=parse_activity_date(
                            "expected_finish", existing.expected_finish if existing is not None else None
                        ),
                        planned_finish=parse_activity_date(
                            "planned_finish", existing.planned_finish if existing is not None else None
                        ),
                        leveling_priority=P6ActivityLevelingPriority.from_p6_value(
                            payload.get(
                                "leveling_priority",
                                existing.leveling_priority.value if existing is not None
                                else P6ActivityLevelingPriority.NORMAL.value,
                            )
                        ),
                        original_duration=raw_original_duration,
                        wbs_id=payload.get(
                            "wbs_id", existing.wbs_id if existing is not None else None
                        ),
                    )

                try:
                    parts = suffix.strip("/").split("/") if suffix.strip("/") else []
                    payload = json.loads(body.decode("utf-8") or "{}") if body else {}
                    if not isinstance(payload, dict):
                        raise ValueError("INVALID_PAYLOAD")
                    if payload.get("contract_version", P6_ACTIVITY_MASTER_API_VERSION) != P6_ACTIVITY_MASTER_API_VERSION:
                        raise ValueError("INVALID_CONTRACT_VERSION")
                    if method == "GET" and not parts:
                        result = self._p6_activity_master_api.list(scope, auth_context=auth)
                        return self._json(200, {
                            "contract_version": P6_ACTIVITY_MASTER_API_VERSION,
                            "activities": list(result),
                        })
                    if method == "POST" and not parts:
                        activity_id = payload.get("activity_id")
                        if not isinstance(activity_id, str) or not activity_id.strip():
                            raise ValueError("INVALID_ACTIVITY_ID")
                        result = self._p6_activity_master_api.create(
                            build_activity(activity_id), auth_context=auth
                        )
                        return self._json(201, result)
                    if method == "GET" and len(parts) == 1 and parts[0]:
                        result = self._p6_activity_master_api.get(
                            scope, parts[0], auth_context=auth
                        )
                        if result is None:
                            return self._error(404, "P6_ACTIVITY_MASTER_NOT_FOUND", "error.resource.not_found")
                        return self._json(200, result)
                    if method == "PATCH" and len(parts) == 1 and parts[0]:
                        expected_revision = payload.get("expected_revision")
                        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
                            raise ValueError("EXPECTED_REVISION_REQUIRED")
                        existing = self._p6_activity_master_api.repository.get(scope, parts[0])
                        if existing is None:
                            return self._error(404, "P6_ACTIVITY_MASTER_NOT_FOUND", "error.resource.not_found")
                        result = self._p6_activity_master_api.update(
                            build_activity(parts[0], existing=existing),
                            expected_revision=expected_revision,
                            auth_context=auth,
                        )
                        return self._json(200, result)
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                except ActivityPersistenceError as exc:
                    if str(exc) == "REVISION_CONFLICT":
                        return self._error(409, str(exc), "error.revision.conflict")
                    return self._error(400, str(exc), "error.request.invalid")
                except (TypeError, ValueError, ArithmeticError, KeyError) as exc:
                    return self._error(400, str(exc) or "P6_ACTIVITY_MASTER_REQUEST_INVALID", "error.request.invalid")
            if path.startswith("/api/projects/") and "/p6/wbs" in path and self._p6_wbs_master_api is not None:
                prefix = "/p6/wbs"
                project_id = path[len("/api/projects/"):].split(prefix, 1)[0].rstrip("/")
                suffix = path[len("/api/projects/") + len(project_id) + len(prefix):]
                if not project_id:
                    return self._error(400, "P6_WBS_MASTER_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                scope = BackendScope(context.tenant_id, context.project_id, context.revision)

                def build_wbs(wbs_id: str, existing: WBSMaster | None = None) -> WBSMaster:
                    parent_kind_raw = payload.get(
                        "parent_kind",
                        existing.parent_kind.value if existing is not None else None,
                    )
                    parent_kind = WBSParentKind(parent_kind_raw)
                    parent_wbs_id = payload.get(
                        "parent_wbs_id",
                        existing.parent_wbs_id if existing is not None else None,
                    )
                    raw_sequence = payload.get(
                        "sequence_number",
                        existing.sequence_number if existing is not None else 0,
                    )
                    if isinstance(raw_sequence, bool) or not isinstance(raw_sequence, int):
                        raise ValueError("INVALID_WBS_SEQUENCE_NUMBER")
                    return WBSMaster(
                        scope=scope,
                        wbs_id=wbs_id,
                        parent_kind=parent_kind,
                        parent_wbs_id=parent_wbs_id,
                        code=payload.get("code", existing.code if existing is not None else ""),
                        name=payload.get("name", existing.name if existing is not None else ""),
                        sequence_number=raw_sequence,
                        record_revision=0 if existing is None else existing.record_revision,
                    )

                try:
                    parts = suffix.strip("/").split("/") if suffix.strip("/") else []
                    payload = json.loads(body.decode("utf-8") or "{}") if body else {}
                    if not isinstance(payload, dict):
                        raise ValueError("INVALID_PAYLOAD")
                    if payload.get("contract_version", P6_WBS_MASTER_API_VERSION) != P6_WBS_MASTER_API_VERSION:
                        raise ValueError("INVALID_CONTRACT_VERSION")
                    if method == "GET" and not parts:
                        result = self._p6_wbs_master_api.list(scope, auth_context=auth)
                        return self._json(200, {
                            "contract_version": P6_WBS_MASTER_API_VERSION,
                            "wbs_nodes": list(result),
                        })
                    if method == "POST" and not parts:
                        wbs_id = payload.get("wbs_id")
                        if not isinstance(wbs_id, str) or not wbs_id.strip():
                            raise ValueError("INVALID_WBS_ID")
                        return self._json(
                            201,
                            self._p6_wbs_master_api.create(build_wbs(wbs_id), auth_context=auth),
                        )
                    if method == "GET" and len(parts) == 1 and parts[0]:
                        result = self._p6_wbs_master_api.get(scope, parts[0], auth_context=auth)
                        if result is None:
                            return self._error(404, "P6_WBS_MASTER_NOT_FOUND", "error.resource.not_found")
                        return self._json(200, result)
                    if method == "PATCH" and len(parts) == 1 and parts[0]:
                        expected_revision = payload.get("expected_revision")
                        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
                            raise ValueError("EXPECTED_REVISION_REQUIRED")
                        existing = self._p6_wbs_master_api.repository.get(scope, parts[0])
                        if existing is None:
                            return self._error(404, "P6_WBS_MASTER_NOT_FOUND", "error.resource.not_found")
                        return self._json(
                            200,
                            self._p6_wbs_master_api.update(
                                build_wbs(parts[0], existing=existing),
                                expected_revision=expected_revision,
                                auth_context=auth,
                            ),
                        )
                    if method == "DELETE" and len(parts) == 1 and parts[0]:
                        expected_revision = payload.get("expected_revision")
                        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
                            raise ValueError("EXPECTED_REVISION_REQUIRED")
                        return self._json(
                            200,
                            self._p6_wbs_master_api.delete(
                                scope,
                                parts[0],
                                expected_revision=expected_revision,
                                auth_context=auth,
                            ),
                        )
                    return self._error(405, "P6_WBS_MASTER_METHOD_OR_PATH_UNSUPPORTED", "error.request.invalid")
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                except WBSPersistenceError as exc:
                    if str(exc) == "REVISION_CONFLICT":
                        return self._error(409, str(exc), "error.revision.conflict")
                    if str(exc) == "WBS_NOT_FOUND":
                        return self._error(404, str(exc), "error.resource.not_found")
                    if str(exc) == "WBS_IN_USE":
                        return self._error(409, str(exc), "error.resource.in_use")
                    return self._error(400, str(exc), "error.request.invalid")
                except (TypeError, ValueError, KeyError) as exc:
                    return self._error(400, str(exc) or "P6_WBS_MASTER_REQUEST_INVALID", "error.request.invalid")
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
                    if method == "DELETE" and len(parts) == 1 and parts[0]:
                        expected_revision = payload.get("expected_revision")
                        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
                            raise ValueError("expected_revision required")
                        result = self._p6_relationship_api.delete(scope, parts[0], expected_revision=expected_revision, auth_context=auth)
                        return self._json(200, result)
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
                except RelationshipPersistenceError as exc:
                    if method == "DELETE" and str(exc) == "RELATIONSHIP_NOT_FOUND":
                        return self._error(404, str(exc), "error.p6.relationship.not_found")
                    if method == "DELETE" and str(exc) == "REVISION_CONFLICT":
                        return self._error(409, str(exc), "error.revision.conflict")
                    return self._error(400, "P6_RELATIONSHIP_REQUEST_INVALID", "error.request.invalid")
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
                        result = self._p6_activity_period_actual_api.list(scope, activity_id=payload.get("activity_id"), period_id=payload.get("period_id"), auth_context=auth)
                        return self._json(200, {"contract_version": P6_ACTIVITY_PERIOD_ACTUAL_API_VERSION, "activity_period_actuals": list(result)})
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
            if method == "POST" and path.startswith("/api/projects/") and path.endswith("/p6/resource-assignments"):
                if self._p6_resource_write_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/p6/resource-assignments")].rstrip("/")
                if not project_id:
                    return self._error(400, "P6_RESOURCE_ASSIGNMENT_REQUEST_INVALID", "error.request.invalid")
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
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return self._error(400, "P6_RESOURCE_ASSIGNMENT_REQUEST_INVALID", "error.request.invalid")
                if not isinstance(payload, dict) or payload.get("contract_version") != P6_RESOURCE_WRITE_API_VERSION:
                    return self._error(400, "P6_RESOURCE_ASSIGNMENT_REQUEST_INVALID", "error.request.invalid")
                try:
                    scope = BackendScope(context.tenant_id, context.project_id, context.revision)
                    assignment = P6ResourceAssignment(
                        scope=scope,
                        assignment_id=payload.get("assignment_id", ""),
                        activity_id=payload.get("activity_id", ""),
                        resource_id=payload.get("resource_id", ""),
                        role_id=payload.get("role_id"),
                        units=None if payload.get("units") is None else Decimal(str(payload["units"])),
                        actual_units=None if payload.get("actual_units") is None else Decimal(str(payload["actual_units"])),
                        remaining_units=None if payload.get("remaining_units") is None else Decimal(str(payload["remaining_units"])),
                        planned_cost=None if payload.get("planned_cost") is None else Decimal(str(payload["planned_cost"])),
                        actual_cost=None if payload.get("actual_cost") is None else Decimal(str(payload["actual_cost"])),
                        remaining_cost=None if payload.get("remaining_cost") is None else Decimal(str(payload["remaining_cost"])),
                        unit=payload.get("unit"),
                        currency=payload.get("currency"),
                        calendar_id=payload.get("calendar_id"),
                        calendar_version=payload.get("calendar_version"),
                        note=payload.get("note"),
                        # Never coerce strings or numbers into an explicit driving flag.
                        is_driving=payload.get("is_driving"),
                        units_per_time=(
                            None if payload.get("units_per_time") is None
                            else Decimal(str(payload["units_per_time"]))
                        ),
                        units_per_time_period=payload.get("units_per_time_period"),
                        hours_per_units_time_period=(
                            None if payload.get("hours_per_units_time_period") is None
                            else Decimal(str(payload["hours_per_units_time_period"]))
                        ),
                    )
                    result = self._p6_resource_write_api.save_assignment(assignment, auth_context=auth)
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                except ValueError as exc:
                    code = str(exc)
                    if code == "IMMUTABLE_RESOURCE_ASSIGNMENT":
                        return self._error(409, code, "error.resource_assignment.immutable_conflict")
                    if code == "RESOURCE_ASSIGNMENT_WRITE_SERVICE_NOT_CONFIGURED":
                        return self._error(503, code, "error.resource_assignment.unavailable")
                    return self._error(400, "P6_RESOURCE_ASSIGNMENT_REQUEST_INVALID", "error.request.invalid")
                except (TypeError, ArithmeticError):
                    return self._error(400, "P6_RESOURCE_ASSIGNMENT_REQUEST_INVALID", "error.request.invalid")
                return self._json(200, result)
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
            if method == "POST" and path.startswith("/api/projects/") and path.endswith("/p6/resource-capacities"):
                if self._p6_resource_capacity_write_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/p6/resource-capacities")].rstrip("/")
                if not project_id:
                    return self._error(400, "P6_RESOURCE_CAPACITY_REQUEST_INVALID", "error.request.invalid")
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
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return self._error(400, "P6_RESOURCE_CAPACITY_REQUEST_INVALID", "error.request.invalid")
                if (
                    not isinstance(payload, dict)
                    or payload.get("contract_version") != P6_RESOURCE_CAPACITY_WRITE_API_VERSION
                ):
                    return self._error(400, "P6_RESOURCE_CAPACITY_REQUEST_INVALID", "error.request.invalid")
                try:
                    result = self._p6_resource_capacity_write_api.save_effective_change(
                        BackendScope(context.tenant_id, context.project_id, context.revision),
                        resource_id=payload.get("resource_id"),
                        max_units=payload.get("max_units"),
                        unit_basis=payload.get("unit_basis"),
                        hours_per_time_period=payload.get("hours_per_time_period"),
                        effective_from=payload.get("effective_from"),
                        effective_to=payload.get("effective_to"),
                        expected_revision=payload.get("expected_revision"),
                        close_open_segment=payload.get("close_open_segment", False),
                        auth_context=auth,
                    )
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                except ValueError as exc:
                    code = str(exc)
                    if code in {
                        "REVISION_CONFLICT",
                        "CAPACITY_SEGMENTS_OVERLAP",
                        "IMMUTABLE_RESOURCE_CAPACITY_SEGMENT",
                        "RESOURCE_CAPACITY_INSERT_CONFLICT",
                    }:
                        return self._error(409, code, "error.p6.resource_capacity.conflict")
                    if code == "RESOURCE_CAPACITY_WRITE_SERVICE_NOT_CONFIGURED":
                        return self._error(503, code, "error.p6.resource_capacity.unavailable")
                    if code.startswith("INVALID_") or code.startswith("CAPACITY_"):
                        return self._error(400, code, "error.request.invalid")
                    return self._error(400, "P6_RESOURCE_CAPACITY_REQUEST_INVALID", "error.request.invalid")
                except (TypeError, ArithmeticError):
                    return self._error(400, "P6_RESOURCE_CAPACITY_REQUEST_INVALID", "error.request.invalid")
                return self._json(200, result)
            if method == "POST" and path.startswith("/api/projects/") and "/p6/resource-capacities/" in path and path.endswith("/resolve"):
                if self._p6_resource_capacity_read_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, suffix = path.split("/p6/resource-capacities/", 1)
                project_id = prefix[len("/api/projects/"):]
                resource_id = suffix[: -len("/resolve")].rstrip("/")
                if not project_id or not resource_id or "/" in resource_id:
                    return self._error(400, "P6_RESOURCE_CAPACITY_REQUEST_INVALID", "error.request.invalid")
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
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return self._error(400, "P6_RESOURCE_CAPACITY_REQUEST_INVALID", "error.request.invalid")
                if (
                    not isinstance(payload, dict)
                    or payload.get("contract_version") != P6_RESOURCE_CAPACITY_READ_API_VERSION
                ):
                    return self._error(400, "P6_RESOURCE_CAPACITY_REQUEST_INVALID", "error.request.invalid")
                try:
                    period_raw = payload.get("period")
                    if not isinstance(period_raw, str) or not period_raw.strip():
                        raise ValueError("INVALID_EFFECTIVE_DATE")
                    period = date.fromisoformat(period_raw)
                    basis_raw = payload.get("basis")
                    hours_raw = payload.get("hours_per_time_period")
                    if (basis_raw is None) != (hours_raw is None):
                        raise ValueError("CAPACITY_CONVERSION_INCOMPLETE")
                    basis = (
                        None
                        if basis_raw is None
                        else ResourceCapacityBasis(str(basis_raw))
                    )
                    hours = (
                        None
                        if hours_raw is None
                        else Decimal(str(hours_raw))
                    )
                    result = self._p6_resource_capacity_read_api.capacity_on(
                        BackendScope(context.tenant_id, context.project_id, context.revision),
                        resource_id,
                        period,
                        basis=basis,
                        hours_per_time_period=hours,
                        auth_context=auth,
                    )
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                except ValueError as exc:
                    code = str(exc)
                    if code == "RESOURCE_CAPACITY_NOT_REGISTERED":
                        return self._error(404, code, "error.p6.resource_capacity.not_registered")
                    if code in {
                        "CAPACITY_SEGMENT_NOT_EFFECTIVE",
                        "CAPACITY_SEGMENTS_OVERLAP",
                    }:
                        return self._error(409, code, "error.p6.resource_capacity.conflict")
                    return self._error(400, "P6_RESOURCE_CAPACITY_REQUEST_INVALID", "error.request.invalid")
                except (TypeError, ArithmeticError):
                    return self._error(400, "P6_RESOURCE_CAPACITY_REQUEST_INVALID", "error.request.invalid")
                capacity = result.get("capacity")
                if isinstance(capacity, Decimal):
                    # Serialize the authoritative server-side conversion as a
                    # canonical decimal string (no client-side arithmetic).
                    canonical = capacity.normalize()
                    result = {
                        **result,
                        "capacity": f"{canonical:f}"
                        if capacity.is_finite()
                        else str(capacity),
                    }
                return self._json(200, result)
            if method == "GET" and path.startswith("/api/projects/") and path.endswith("/p6/resource-capacities"):
                if self._p6_resource_capacity_read_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/p6/resource-capacities")].rstrip("/")
                if not project_id:
                    return self._error(400, "P6_RESOURCE_CAPACITY_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                    session = self._api.get_session(session_id, now=now)
                    auth = context.authorization_context(session.roles)
                    result = self._p6_resource_capacity_read_api.list_segments(
                        BackendScope(context.tenant_id, context.project_id, context.revision),
                        None,
                        auth_context=auth,
                    )
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                except ValueError as exc:
                    return self._error(400, str(exc), "error.request.invalid")
                return self._json(200, {
                    "contract_version": P6_RESOURCE_CAPACITY_READ_API_VERSION,
                    "capacities": list(result),
                })
            if method == "GET" and path.startswith("/api/projects/") and "/p6/resource-capacities/" in path:
                if self._p6_resource_capacity_read_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, resource_id = path.split("/p6/resource-capacities/", 1)
                project_id = prefix[len("/api/projects/"):]
                resource_id = resource_id.rstrip("/")
                if not project_id or not resource_id or "/" in resource_id:
                    return self._error(400, "P6_RESOURCE_CAPACITY_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                    session = self._api.get_session(session_id, now=now)
                    auth = context.authorization_context(session.roles)
                    result = self._p6_resource_capacity_read_api.get_profile(
                        BackendScope(context.tenant_id, context.project_id, context.revision),
                        resource_id,
                        auth_context=auth,
                    )
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                except ValueError as exc:
                    code = str(exc)
                    if code == "RESOURCE_CAPACITY_NOT_REGISTERED":
                        return self._error(404, code, "error.p6.resource_capacity.not_registered")
                    if code in {"CAPACITY_SEGMENT_NOT_EFFECTIVE", "CAPACITY_SEGMENTS_OVERLAP"}:
                        return self._error(409, code, "error.p6.resource_capacity.conflict")
                    return self._error(400, "P6_RESOURCE_CAPACITY_REQUEST_INVALID", "error.request.invalid")
                return self._json(200, result)
            if method == "POST" and path.startswith("/api/projects/") and path.endswith("/p6/resource-rates"):
                if self._p6_resource_rate_write_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/p6/resource-rates")].rstrip("/")
                if not project_id:
                    return self._error(400, "P6_RESOURCE_RATE_REQUEST_INVALID", "error.request.invalid")
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
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return self._error(400, "P6_RESOURCE_RATE_REQUEST_INVALID", "error.request.invalid")
                if (
                    not isinstance(payload, dict)
                    or payload.get("contract_version") != P6_RESOURCE_RATE_WRITE_API_VERSION
                ):
                    return self._error(400, "P6_RESOURCE_RATE_REQUEST_INVALID", "error.request.invalid")
                try:
                    result = self._p6_resource_rate_write_api.save_effective_change(
                        BackendScope(context.tenant_id, context.project_id, context.revision),
                        resource_id=payload.get("resource_id"),
                        rate=payload.get("rate"),
                        basis=payload.get("basis"),
                        currency=payload.get("currency"),
                        unit=payload.get("unit"),
                        effective_from=payload.get("effective_from"),
                        effective_to=payload.get("effective_to"),
                        expected_revision=payload.get("expected_revision"),
                        close_open_segment=payload.get("close_open_segment", False),
                        auth_context=auth,
                    )
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                except ValueError as exc:
                    code = str(exc)
                    if code in {
                        "REVISION_CONFLICT",
                        "RATE_INTERVALS_OVERLAP",
                        "IMMUTABLE_RESOURCE_RATE_FACT",
                        "RESOURCE_RATE_INSERT_CONFLICT",
                    }:
                        return self._error(409, code, "error.p6.resource_rate.conflict")
                    if code == "RESOURCE_RATE_WRITE_SERVICE_NOT_CONFIGURED":
                        return self._error(503, code, "error.p6.resource_rate.unavailable")
                    if code.startswith("INVALID_") or code.startswith("RATE_"):
                        return self._error(400, code, "error.request.invalid")
                    return self._error(400, "P6_RESOURCE_RATE_REQUEST_INVALID", "error.request.invalid")
                except (TypeError, ArithmeticError):
                    return self._error(400, "P6_RESOURCE_RATE_REQUEST_INVALID", "error.request.invalid")
                return self._json(200, result)
            if method == "POST" and path.startswith("/api/projects/") and "/p6/resource-rates/" in path and path.endswith("/resolve"):
                if self._p6_resource_rate_read_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, suffix = path.split("/p6/resource-rates/", 1)
                project_id = prefix[len("/api/projects/"):]
                resource_id = suffix[: -len("/resolve")].rstrip("/")
                if not project_id or not resource_id or "/" in resource_id:
                    return self._error(400, "P6_RESOURCE_RATE_REQUEST_INVALID", "error.request.invalid")
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
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return self._error(400, "P6_RESOURCE_RATE_REQUEST_INVALID", "error.request.invalid")
                if (
                    not isinstance(payload, dict)
                    or payload.get("contract_version") != P6_RESOURCE_RATE_READ_API_VERSION
                ):
                    return self._error(400, "P6_RESOURCE_RATE_REQUEST_INVALID", "error.request.invalid")
                try:
                    period_raw = payload.get("period")
                    if not isinstance(period_raw, str) or not period_raw.strip():
                        raise ValueError("INVALID_RATE_EFFECTIVE_DATE")
                    result = self._p6_resource_rate_read_api.rate_on(
                        BackendScope(context.tenant_id, context.project_id, context.revision),
                        resource_id,
                        date.fromisoformat(period_raw),
                        auth_context=auth,
                    )
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                except ValueError as exc:
                    code = str(exc)
                    if code == "RESOURCE_RATE_NOT_REGISTERED":
                        return self._error(404, code, "error.p6.resource_rate.not_registered")
                    if code in {"RATE_NOT_EFFECTIVE", "RATE_INTERVALS_OVERLAP"}:
                        return self._error(409, code, "error.p6.resource_rate.conflict")
                    return self._error(400, "P6_RESOURCE_RATE_REQUEST_INVALID", "error.request.invalid")
                except (TypeError, ArithmeticError):
                    return self._error(400, "P6_RESOURCE_RATE_REQUEST_INVALID", "error.request.invalid")
                return self._json(200, result)
            if method == "GET" and path.startswith("/api/projects/") and path.endswith("/p6/resource-rates"):
                if self._p6_resource_rate_read_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/p6/resource-rates")].rstrip("/")
                if not project_id:
                    return self._error(400, "P6_RESOURCE_RATE_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                    session = self._api.get_session(session_id, now=now)
                    auth = context.authorization_context(session.roles)
                    result = self._p6_resource_rate_read_api.list_rates(
                        BackendScope(context.tenant_id, context.project_id, context.revision),
                        None,
                        auth_context=auth,
                    )
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                except ValueError as exc:
                    return self._error(400, str(exc), "error.request.invalid")
                return self._json(200, {
                    "contract_version": P6_RESOURCE_RATE_READ_API_VERSION,
                    "rates": list(result),
                })
            if method == "GET" and path.startswith("/api/projects/") and "/p6/resource-rates/" in path:
                if self._p6_resource_rate_read_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, resource_id = path.split("/p6/resource-rates/", 1)
                project_id = prefix[len("/api/projects/"):]
                resource_id = resource_id.rstrip("/")
                if not project_id or not resource_id or "/" in resource_id:
                    return self._error(400, "P6_RESOURCE_RATE_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                    session = self._api.get_session(session_id, now=now)
                    auth = context.authorization_context(session.roles)
                    result = self._p6_resource_rate_read_api.get_profile(
                        BackendScope(context.tenant_id, context.project_id, context.revision),
                        resource_id,
                        auth_context=auth,
                    )
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                except ValueError as exc:
                    code = str(exc)
                    if code == "RESOURCE_RATE_NOT_REGISTERED":
                        return self._error(404, code, "error.p6.resource_rate.not_registered")
                    if code in {"RATE_NOT_EFFECTIVE", "RATE_INTERVALS_OVERLAP"}:
                        return self._error(409, code, "error.p6.resource_rate.conflict")
                    return self._error(400, "P6_RESOURCE_RATE_REQUEST_INVALID", "error.request.invalid")
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
            if method == "POST" and path.startswith("/api/projects/") and path.endswith("/change-claims"):
                if self._change_claim_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/change-claims")].rstrip("/")
                if not project_id:
                    return self._error(400, "CHANGE_CLAIM_REQUEST_INVALID", "error.request.invalid")
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
                        raise ValueError("CHANGE_CLAIM_REQUEST_INVALID")
                    occurred_at = datetime.fromisoformat(str(payload.get("occurred_at", "")).replace("Z", "+00:00"))
                    evidence_refs = payload.get("evidence_refs", [])
                    claim_payload = payload.get("payload", {})
                    if not isinstance(evidence_refs, list) or not isinstance(claim_payload, dict):
                        raise ValueError("CHANGE_CLAIM_REQUEST_INVALID")
                    request = ChangeClaimCreateRequest(
                        contract_version=payload.get("contract_version", ""),
                        tenant_id=context.tenant_id,
                        project_id=context.project_id,
                        resource_id=payload.get("resource_id", ""),
                        revision=payload.get("revision", -1),
                        resource_type=ChangeClaimType(payload.get("resource_type", "")),
                        status=ChangeClaimStatus(payload.get("status", "draft")),
                        actor_id=context.user_id,
                        occurred_at=occurred_at,
                        payload=claim_payload,
                        evidence_refs=tuple(evidence_refs),
                        expected_revision=payload.get("expected_revision", -1),
                        idempotency_key=payload.get("idempotency_key", ""),
                    )
                    result = self._change_claim_api.create(request, auth_context=auth)
                except (KeyError, TypeError, ValueError, OverflowError):
                    return self._error(400, "CHANGE_CLAIM_REQUEST_INVALID", "error.request.invalid")
                return self._json(201, result)
            if method == "GET" and path.startswith("/api/projects/") and "/change-claims/" in path:
                if self._change_claim_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, resource_id = path.split("/change-claims/", 1)
                project_id = prefix[len("/api/projects/"):]
                if not project_id or not resource_id or "/" in resource_id:
                    return self._error(400, "CHANGE_CLAIM_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                result = self._change_claim_api.get(
                    ChangeClaimReadRequest(
                        contract_version=P0_CHANGE_CLAIM_API_VERSION,
                        tenant_id=context.tenant_id,
                        project_id=context.project_id,
                        resource_id=resource_id,
                    ),
                    auth_context=auth,
                )
                if result is None:
                    return self._error(404, "CHANGE_CLAIM_NOT_FOUND", "error.change_claim.not_found")
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
            if (
                method in {"GET", "POST"}
                and path.startswith("/api/projects/")
                and path.endswith("/p6/formula-columns")
            ):
                if self._p6_formula_column_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = path[len("/api/projects/"):-len("/p6/formula-columns")]
                if not project_id or "/" in project_id:
                    return self._error(400, "P6_FORMULA_COLUMN_REQUEST_INVALID", "error.request.invalid")
                try:
                    context = self._api.open_project(session_id, project_id, now=now).context
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                session = self._api.get_session(session_id, now=now)
                auth = context.authorization_context(session.roles)
                scope = BackendScope(context.tenant_id, context.project_id, context.revision)
                if method == "GET":
                    columns = self._p6_formula_column_api.list(scope, auth_context=auth)
                    return self._json(200, {
                        "contract_version": P6_FORMULA_COLUMN_API_VERSION,
                        "kind": "formula_column_list",
                        "scope": {
                            "tenant_id": context.tenant_id,
                            "project_id": context.project_id,
                            "project_revision": context.revision,
                        },
                        "formula_columns": list(columns),
                    })
                payload = json.loads(body.decode("utf-8") or "{}")
                if not isinstance(payload, dict):
                    return self._error(400, "P6_FORMULA_COLUMN_REQUEST_INVALID", "error.request.invalid")
                formula_id = payload.get("formula_id")
                title = payload.get("title")
                expression = payload.get("expression")
                if not all(isinstance(item, str) for item in (formula_id, title, expression)):
                    return self._error(400, "P6_FORMULA_COLUMN_REQUEST_INVALID", "error.request.invalid")
                try:
                    result = self._p6_formula_column_api.create(
                        scope,
                        formula_id=formula_id,
                        title=title,
                        expression=expression,
                        auth_context=auth,
                    )
                except P6FormulaColumnError as exc:
                    return self._error(400, str(exc) or "FORMULA_COLUMN_INVALID", "error.request.invalid")
                return self._json(200, result)

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
                try:
                    columns = tuple(
                        layout_column_from_mapping(item) for item in raw_columns
                    )
                except P6LayoutPersistenceError:
                    return self._error(400, "INVALID_LAYOUT_COLUMNS", "error.request.invalid")
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
                try:
                    result = self._p6_layout_definition_api.save(layout, auth_context=auth)
                except P6LayoutPersistenceError as exc:
                    code = str(exc)
                    if code in {"REVISION_CONFLICT", "IMMUTABLE_LAYOUT_REVISION"}:
                        return self._error(409, code, "error.p6.layout.conflict")
                    return self._error(400, code or "INVALID_LAYOUT_REQUEST", "error.request.invalid")
                return self._json(200, {"contract_version": P6_LAYOUT_DEFINITION_API_VERSION, **result["layout"]})
            if (
                method == "GET"
                and path.startswith("/api/projects/")
                and "/p6/layouts/" in path
                and path.endswith("/default")
            ):
                if self._p6_layout_definition_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, layout_path = path.split("/p6/layouts/", 1)
                project_id = prefix[len("/api/projects/"):]
                layout_path = layout_path[:-len("/default")]
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
                try:
                    result = self._p6_layout_definition_api.default_layout(
                        BackendScope(context.tenant_id, context.project_id, context.revision),
                        layout_scope,
                        view_id,
                        auth_context=auth,
                    )
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                if result is None:
                    return self._error(404, "P6_LAYOUT_DEFAULT_NOT_DEFINED", "error.p6.layout.default_not_defined")
                return self._json(200, {"contract_version": P6_LAYOUT_DEFINITION_API_VERSION, **result["layout"]})
            if (
                method == "GET"
                and path.startswith("/api/projects/")
                and "/p6/layouts/" in path
                and path.endswith("/revisions")
            ):
                if self._p6_layout_definition_api is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                prefix, layout_path = path.split("/p6/layouts/", 1)
                project_id = prefix[len("/api/projects/"):]
                layout_path = layout_path[:-len("/revisions")]
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
                try:
                    result = self._p6_layout_definition_api.list_revisions(
                        BackendScope(context.tenant_id, context.project_id, context.revision),
                        layout_scope,
                        view_id,
                        auth_context=auth,
                    )
                except AuthorizationError as exc:
                    return self._error(403, str(exc), "error.authorization.denied")
                return self._json(200, result)
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
            if path.startswith("/api/projects/") and "/ai/assistant/turn" in path:
                parts = path[len("/api/projects/"):].split("/")
                if len(parts) != 4 or not parts[0] or parts[1:] != ["ai", "assistant", "turn"]:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                if method != "POST":
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                if self._ai_action_runtime is None or self._ai_assistant_orchestrator is None:
                    return self._error(503, "AI_ASSISTANT_NOT_CONFIGURED", "error.ai_assistant.not_configured")
                # Bound parsing work before decoding attacker-controlled JSON.
                if len(body) > 128_000:
                    return self._error(400, "AI_ASSISTANT_REQUEST_INVALID", "error.request.invalid")
                try:
                    payload = json.loads(body.decode("utf-8") or "{}")
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return self._error(400, "AI_ASSISTANT_REQUEST_INVALID", "error.request.invalid")
                if not isinstance(payload, dict) or set(payload).difference(
                    {"expected_revision", "message", "language", "history"}
                ):
                    return self._error(400, "AI_ASSISTANT_REQUEST_INVALID", "error.request.invalid")
                expected_revision = payload.get("expected_revision")
                message = payload.get("message")
                language = payload.get("language")
                history_raw = payload.get("history", [])
                if not isinstance(history_raw, list) or len(history_raw) > 12:
                    return self._error(400, "AI_ASSISTANT_REQUEST_INVALID", "error.request.invalid")
                history = []
                history_chars = 0
                for entry in history_raw:
                    if (
                        not isinstance(entry, dict)
                        or set(entry) != {"role", "content"}
                        or not isinstance(entry.get("role"), str)
                        or entry.get("role") not in {"user", "assistant"}
                        or not isinstance(entry.get("content"), str)
                        or not entry["content"].strip()
                        or len(entry["content"]) > 4000
                    ):
                        return self._error(400, "AI_ASSISTANT_REQUEST_INVALID", "error.request.invalid")
                    history_content = entry["content"].strip()
                    history_chars += len(history_content)
                    if history_chars > 12000:
                        return self._error(400, "AI_ASSISTANT_REQUEST_INVALID", "error.request.invalid")
                    history.append({"role": entry["role"], "content": history_content})
                if (
                    isinstance(expected_revision, bool)
                    or not isinstance(expected_revision, int)
                    or expected_revision < 0
                    or not isinstance(message, str)
                    or not 1 <= len(message.strip()) <= 6000
                    or not is_valid_language_tag(language)
                    or len(language) > 64
                ):
                    return self._error(400, "AI_ASSISTANT_REQUEST_INVALID", "error.request.invalid")
                project_id = parts[0]
                try:
                    # Conversation is available to readers; proposal creation is a
                    # separate write capability and is exposed only after write authorization.
                    authorized = self._api.authorize_project(
                        session_id, project_id, Permission.PROJECT_READ, now=now
                    )
                    session = self._api.get_session(session_id, now=now)
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                context = authorized.context
                can_propose = True
                try:
                    self._api.authorize_project(
                        session_id, project_id, Permission.PROJECT_WRITE, now=now
                    )
                except AuthorizationError:
                    can_propose = False
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                runtime_context = AIActionRuntimeContext(
                    subject_id=session.user_id,
                    tenant_id=context.tenant_id,
                    project_id=context.project_id,
                    project_revision_id=str(context.revision),
                    roles=session.roles,
                )
                if expected_revision != context.revision:
                    self._ai_action_runtime.record_request_event(
                        runtime_context,
                        "assistant_turn_stale_revision",
                        metadata={
                            "expected_revision": expected_revision,
                            "current_revision": context.revision,
                        },
                    )
                    return self._error(
                        409, "AI_ASSISTANT_STALE_REVISION", "error.conflict.stale_revision"
                    )
                # Audit metadata only; never persist the user's prompt as part of an audit event.
                self._ai_action_runtime.record_request_event(
                    runtime_context,
                    "assistant_turn_requested",
                    metadata={
                        "language": language.strip(),
                        "message_length": len(message.strip()),
                        "can_propose": can_propose,
                    },
                )
                try:
                    turn = self._ai_assistant_orchestrator.turn(
                        runtime_context,
                        user_message=message.strip(),
                        language=language.strip(),
                        history=tuple(history),
                        allow_mutations=can_propose,
                    )
                except AIAssistantProviderError as exc:
                    self._ai_action_runtime.record_request_event(
                        runtime_context,
                        "assistant_turn_failed",
                        metadata={"reason_code": exc.code},
                    )
                    raise
                proposal = turn.proposal
                proposal_payload = None
                if proposal is not None:
                    proposal_payload = {
                        "proposal_id": proposal.proposal.proposal_id,
                        "tool_name": proposal.proposal.tool_name,
                        "action": proposal.proposal.action,
                        "status": proposal.status,
                        "requires_human_approval": proposal.proposal.requires_human_approval,
                        "requested_by": proposal.proposal.requested_by,
                        "evidence_refs": list(proposal.proposal.evidence_refs),
                        "project_revision_id": proposal.proposal.project_revision_id,
                        "resource_domain": proposal.proposal.resource_domain,
                        "payload": dict(proposal.payload),
                        "result": None if proposal.result is None else dict(proposal.result),
                        "created_at": proposal.created_at.isoformat(),
                        "updated_at": proposal.updated_at.isoformat(),
                        "decided_by": proposal.decided_by,
                        "is_stale": proposal.proposal.project_revision_id != runtime_context.project_revision_id,
                    }
                self._ai_action_runtime.record_request_event(
                    runtime_context,
                    "assistant_turn_completed",
                    proposal_id=None if proposal is None else proposal.proposal.proposal_id,
                    metadata={
                        "kind": turn.kind,
                        "proposal_created": proposal is not None,
                    },
                )
                return self._json(200, {
                    "contract_version": "ai-assistant-turn.v1",
                    "kind": turn.kind,
                    "message": turn.message,
                    "proposal": proposal_payload,
                })
            if path.startswith("/api/projects/") and "/ai/actions/" in path:
                if self._ai_action_runtime is None:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                if method not in {"GET", "POST"}:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                parts = path[len("/api/projects/"):].split("/")
                if not parts or not parts[0] or parts[1:3] != ["ai", "actions"]:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                project_id = parts[0]
                if method == "GET":
                    if len(parts) == 4 and parts[3] == "proposals":
                        read_operation = "list"
                        read_proposal_id = None
                    elif len(parts) == 5 and parts[3] == "proposals" and parts[4]:
                        read_operation = "get"
                        read_proposal_id = parts[4]
                    else:
                        return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                    # Proposal payloads may contain actionable or sensitive project changes.
                    # Only project editors can inspect them; execution still rechecks the
                    # exact AI tool grant and the current revision independently.
                    try:
                        authorized = self._api.authorize_project(
                            session_id, project_id, Permission.PROJECT_WRITE, now=now
                        )
                        session = self._api.get_session(session_id, now=now)
                    except ProjectLifecycleError as exc:
                        if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                            return self._error(403, str(exc), "error.authorization.denied")
                        raise
                    context = authorized.context
                    runtime_context = AIActionRuntimeContext(
                        subject_id=session.user_id,
                        tenant_id=context.tenant_id,
                        project_id=context.project_id,
                        project_revision_id=str(context.revision),
                        roles=session.roles,
                    )
                    if read_operation == "list":
                        records = self._ai_action_runtime.list_proposals(runtime_context)
                    else:
                        records = (self._ai_action_runtime.get_proposal(runtime_context, read_proposal_id or ""),)
                    proposals = []
                    for record in records:
                        proposals.append({
                            "proposal_id": record.proposal.proposal_id,
                            "tool_name": record.proposal.tool_name,
                            "action": record.proposal.action,
                            "status": record.status,
                            "requires_human_approval": record.proposal.requires_human_approval,
                            "requested_by": record.proposal.requested_by,
                            "evidence_refs": list(record.proposal.evidence_refs),
                            "project_revision_id": record.proposal.project_revision_id,
                            "resource_domain": record.proposal.resource_domain,
                            "payload": dict(record.payload),
                            "result": None if record.result is None else dict(record.result),
                            "created_at": record.created_at.isoformat(),
                            "updated_at": record.updated_at.isoformat(),
                            "decided_by": record.decided_by,
                            "is_stale": record.proposal.project_revision_id != runtime_context.project_revision_id,
                        })
                    if read_operation == "get":
                        return self._json(200, {
                            "contract_version": "ai-action-runtime.v1",
                            "proposal": proposals[0],
                        })
                    return self._json(200, {
                        "contract_version": "ai-action-runtime.v1",
                        "proposals": proposals,
                    })
                operation = None
                proposal_id = None
                if len(parts) == 4 and parts[3] == "proposals":
                    operation = "propose"
                elif len(parts) == 6 and parts[3] == "proposals" and parts[4] and parts[5] in {"decision", "execute"}:
                    operation = parts[5]
                    proposal_id = parts[4]
                else:
                    return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
                try:
                    payload = json.loads(body.decode("utf-8") or "{}")
                except json.JSONDecodeError:
                    return self._error(400, "AI_ACTION_REQUEST_INVALID", "error.request.invalid")
                if not isinstance(payload, dict):
                    return self._error(400, "AI_ACTION_REQUEST_INVALID", "error.request.invalid")
                expected_revision = payload.get("expected_revision")
                if (
                    isinstance(expected_revision, bool)
                    or not isinstance(expected_revision, int)
                    or expected_revision < 0
                ):
                    return self._error(400, "AI_ACTION_REQUEST_INVALID", "error.request.invalid")
                try:
                    authorized = self._api.authorize_project(
                        session_id, project_id, Permission.PROJECT_WRITE, now=now
                    )
                    session = self._api.get_session(session_id, now=now)
                except ProjectLifecycleError as exc:
                    if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                        return self._error(403, str(exc), "error.authorization.denied")
                    raise
                context = authorized.context
                runtime_context = AIActionRuntimeContext(
                    subject_id=session.user_id,
                    tenant_id=context.tenant_id,
                    project_id=context.project_id,
                    project_revision_id=str(context.revision),
                    roles=session.roles,
                )
                if expected_revision != context.revision:
                    self._ai_action_runtime.record_request_event(
                        runtime_context,
                        "stale_expected_revision",
                        proposal_id=proposal_id,
                        metadata={
                            "operation": operation,
                            "expected_revision": expected_revision,
                            "current_revision": context.revision,
                        },
                    )
                    return self._error(409, "AI_ACTION_PROPOSAL_STALE_REVISION", "error.conflict.stale_revision")
                if operation == "propose":
                    tool_name = payload.get("tool_name")
                    action_payload = payload.get("payload")
                    evidence_refs = payload.get("evidence_refs", [])
                    if (
                        not isinstance(tool_name, str)
                        or not tool_name.strip()
                        or not isinstance(action_payload, dict)
                        or not isinstance(evidence_refs, list)
                        or any(not isinstance(ref, str) or not ref.strip() for ref in evidence_refs)
                    ):
                        return self._error(400, "AI_ACTION_REQUEST_INVALID", "error.request.invalid")
                    record = self._ai_action_runtime.propose(
                        runtime_context,
                        tool_name=tool_name,
                        payload=action_payload,
                        evidence_refs=tuple(evidence_refs),
                    )
                    return self._json(201, {
                        "contract_version": "ai-action-runtime.v1",
                        "status": record.status,
                        "proposal": {
                            "proposal_id": record.proposal.proposal_id,
                            "tool_name": record.proposal.tool_name,
                            "action": record.proposal.action,
                            "requires_human_approval": record.proposal.requires_human_approval,
                            "requested_by": record.proposal.requested_by,
                            "evidence_refs": list(record.proposal.evidence_refs),
                            "project_revision_id": record.proposal.project_revision_id,
                            "resource_domain": record.proposal.resource_domain,
                            "payload": dict(record.payload),
                            "created_at": record.created_at.isoformat(),
                            "updated_at": record.updated_at.isoformat(),
                            "decided_by": record.decided_by,
                            "is_stale": False,
                        },
                    })
                if operation == "decision":
                    approved = payload.get("approved")
                    if not isinstance(approved, bool):
                        return self._error(400, "AI_ACTION_REQUEST_INVALID", "error.request.invalid")
                    record = self._ai_action_runtime.decide(
                        runtime_context, proposal_id or "", approved=approved
                    )
                    return self._json(200, {
                        "contract_version": "ai-action-runtime.v1",
                        "proposal_id": record.proposal.proposal_id,
                        "status": record.status,
                        "decided_by": record.decided_by,
                    })
                record = self._ai_action_runtime.execute(runtime_context, proposal_id or "")
                return self._json(200, {
                    "contract_version": "ai-action-runtime.v1",
                    "proposal_id": record.proposal.proposal_id,
                    "status": record.status,
                    "result": None if record.result is None else dict(record.result),
                })
            if method == "POST" and path.startswith("/api/projects/") and path.endswith("/open"):
                project_id = path[len("/api/projects/"):-len("/open")]
                if not project_id:
                    return self._error(400, "PROJECT_ID_REQUIRED", "error.project.id_required")
                response = self._api.open_project(session_id, project_id, now=now)
                return self._json(200, {"context": asdict(response.context)})
            if method == "POST" and path == "/api/projects":
                payload = json.loads(body.decode("utf-8") or "{}")
                if not isinstance(payload, dict):
                    return self._error(400, "PROJECT_REQUEST_INVALID", "error.request.invalid")
                response = self._api.create_project(
                    session_id,
                    str(payload.get("project_id", "")),
                    str(payload.get("name", "")),
                    description=payload.get("description", ""),
                    start_date=payload.get("start_date"),
                    date_system=payload.get("date_system", "gregorian"),
                    primary_calendar_id=payload.get("primary_calendar_id"),
                    now=now,
                )
                return self._json(201, {"context": asdict(response.context)})
            if method == "PATCH" and path.startswith("/api/projects/") and path.count("/") == 3:
                project_id = path[len("/api/projects/"):]
                if not project_id:
                    return self._error(400, "PROJECT_ID_REQUIRED", "error.project.id_required")
                payload = json.loads(body.decode("utf-8") or "{}")
                if not isinstance(payload, dict):
                    return self._error(400, "PROJECT_REQUEST_INVALID", "error.request.invalid")
                project = self._api.update_project(
                    session_id,
                    project_id,
                    name=payload.get("name", ""),
                    description=payload.get("description", ""),
                    start_date=payload.get("start_date"),
                    date_system=payload.get("date_system", "gregorian"),
                    primary_calendar_id=payload.get("primary_calendar_id"),
                    expected_revision=payload.get("expected_revision"),
                    now=now,
                )
                return self._json(200, {"project": asdict(project)})
            return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
        except SessionError as exc:
            return self._error(401, str(exc), "error.session.invalid")
        except AuthorizationError as exc:
            return self._error(403, str(exc), "error.authorization.denied")
        except AIAssistantProviderError as exc:
            code = exc.code
            if code == "AI_ASSISTANT_ACTION_NOT_ALLOWED":
                status = 403
            elif code == "AI_ASSISTANT_REQUEST_INVALID":
                status = 400
            elif code in {
                "AI_ASSISTANT_PROVIDER_UNAVAILABLE",
                "AI_ASSISTANT_PROVIDER_RATE_LIMITED",
                "AI_ASSISTANT_PROVIDER_CONFIGURATION_INVALID",
            }:
                status = 503
            else:
                status = 502
            return self._error(status, code, "error.ai_assistant.request_failed")
        except AIActionRuntimeError as exc:
            code = str(exc)
            status = 400
            if code in {"AI_TOOL_NOT_PERMITTED", "AI_ACTION_PERMISSION_CHECK_FAILED"}:
                status = 403
            elif code == "AI_ACTION_PROPOSAL_NOT_FOUND":
                status = 404
            elif code in {
                "AI_ACTION_PROPOSAL_STALE_REVISION",
                "AI_ACTION_PROPOSAL_NOT_PENDING",
                "AI_ACTION_PROPOSAL_NOT_APPROVED",
                "AI_ACTION_PROPOSAL_ID_CONFLICT",
                "AI_ACTION_IDEMPOTENCY_KEY_REUSE",
                "AI_ACTION_EXECUTION_OUTCOME_UNCERTAIN",
                "AI_ACTION_EXECUTION_PRECONDITION_FAILED",
            }:
                status = 409
            elif code == "AI_ACTION_EXECUTION_FAILED":
                status = 502
            elif code.startswith("AI_ACTION_AUDIT_") or code in {
                "AI_ACTION_PROPOSAL_PERSISTENCE_FAILED",
                "AI_ACTION_EXECUTION_RESULT_NOT_PERSISTED",
                "AI_ACTION_EXECUTION_STATE_NOT_PERSISTED",
                "AI_ACTION_EXECUTION_RESERVATION_FAILED",
                "AI_ACTION_IDEMPOTENCY_RESULT_NOT_PERSISTED",
                "AI_ACTION_IDEMPOTENCY_RESULT_INVALID",
                "AI_ACTION_TRANSACTION_FAILED",
            }:
                status = 500
            return self._error(status, code, "error.ai_action.request_failed")
        except ProjectLifecycleError as exc:
            code = str(exc)
            if code == "PROJECT_REVISION_CONFLICT":
                return self._error(409, code, "error.project.revision_conflict")
            if code == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                return self._error(403, code, "error.authorization.denied")
            return self._error(400, code, "error.project.lifecycle")
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self._error(400, str(exc) or "INVALID_REQUEST", "error.request.invalid")

    def _handle_earned_value_route(
        self,
        method: str,
        path: str,
        *,
        session_id: str,
        now: datetime,
        body: bytes,
    ) -> tuple[int, dict[str, str], bytes] | None:
        """Route one versioned project EVM measurement over the Shared Core.

        The request selects the baseline, Data Date, currency and explicit EVM
        settings only. Planned values, progress, actuals, expenses and
        assignment costs are always read from persisted facts; the boundary
        never accepts a client-computed earned value.
        """
        if method != "POST" or not path.startswith("/api/projects/"):
            return None
        marker = "/p6/earned-value"
        if not path.endswith(marker):
            return None
        project_id = path[len("/api/projects/"):-len(marker)]
        if not project_id or "/" in project_id:
            return self._error(
                400, "EVM_REQUEST_INVALID", "error.request.invalid"
            )
        if self._p6_earned_value_read_api is None:
            return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
        try:
            context = self._api.open_project(
                session_id, project_id, now=now
            ).context
        except ProjectLifecycleError as exc:
            if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                return self._error(403, str(exc), "error.authorization.denied")
            raise
        session = self._api.get_session(session_id, now=now)
        auth = context.authorization_context(session.roles)
        scope = BackendScope(
            context.tenant_id, context.project_id, context.revision
        )
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._error(
                400, "EVM_REQUEST_INVALID", "error.request.invalid"
            )
        if not isinstance(payload, dict):
            return self._error(
                400, "EVM_REQUEST_INVALID", "error.request.invalid"
            )
        try:
            self._reject_unknown_keys(
                payload,
                {
                    "contract_version",
                    "baseline_id",
                    "data_date",
                    "currency",
                    "etc_method",
                    "performance_factor",
                    "settings",
                },
                "EVM_REQUEST_UNKNOWN_FIELD",
            )
            baseline_id = self._evm_required_string(
                payload, "baseline_id", "EVM_BASELINE_ID_REQUIRED"
            )
            currency = self._evm_required_string(
                payload, "currency", "EVM_CURRENCY_REQUIRED"
            )
            data_date = self._evm_date(payload.get("data_date"))
            etc_method = payload.get("etc_method")
            if etc_method is not None and (
                not isinstance(etc_method, str) or not etc_method.strip()
            ):
                raise P6EarnedValueReadModelError("EVM_ETC_METHOD_INVALID")
            performance_factor = payload.get("performance_factor")
            if isinstance(performance_factor, bool) or (
                performance_factor is not None
                and not isinstance(performance_factor, (str, int, float))
            ):
                raise P6EarnedValueReadModelError(
                    "EVM_PERFORMANCE_FACTOR_INVALID"
                )
            result = self._p6_earned_value_read_api.get(
                scope,
                baseline_id,
                data_date=data_date,
                currency=currency,
                auth_context=auth,
                etc_method=etc_method,
                performance_factor=performance_factor,
                settings=self._evm_settings(payload.get("settings")),
                contract_version=payload.get(
                    "contract_version", P6_EARNED_VALUE_READ_MODEL_VERSION
                ),
            )
        except AuthorizationError as exc:
            return self._error(403, str(exc), "error.authorization.denied")
        except P6EarnedValueReadModelError as exc:
            return self._evm_error(exc)
        except (
            P6BaselineActivityPersistenceError,
            P6ActivityPeriodActualPersistenceError,
            P6ExpensePersistenceError,
            P6ResourceAssignmentPersistenceError,
            WBSPersistenceError,
            ProjectScheduleSettingsPersistenceError,
        ) as exc:
            code = str(exc)
            if code == "REVISION_CONFLICT":
                return self._error(409, code, "error.p6.evm.conflict")
            return self._error(400, code, "error.p6.evm.invalid")
        return self._json(200, result)

    @staticmethod
    def _reject_unknown_keys(
        payload: Mapping[str, object],
        allowed: set[str],
        code: str,
    ) -> None:
        if set(payload) - allowed:
            raise P6EarnedValueReadModelError(code)

    @staticmethod
    def _evm_required_string(
        payload: Mapping[str, object], key: str, code: str
    ) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise P6EarnedValueReadModelError(code)
        return value

    @classmethod
    def _evm_date(
        cls, value: object, code: str = "EVM_DATA_DATE_INVALID"
    ) -> date:
        if not isinstance(value, str):
            raise P6EarnedValueReadModelError(code)
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise P6EarnedValueReadModelError(code) from exc

    @classmethod
    def _evm_decimal(cls, value: object, code: str) -> Decimal:
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise P6EarnedValueReadModelError(code)
        try:
            result = Decimal(str(value))
        except (ArithmeticError, ValueError) as exc:
            raise P6EarnedValueReadModelError(code) from exc
        if not result.is_finite():
            raise P6EarnedValueReadModelError(code)
        return result

    @classmethod
    def _evm_settings(cls, value: object) -> P6EarnedValueSettings | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise P6EarnedValueReadModelError("EVM_SETTINGS_INVALID")
        cls._reject_unknown_keys(
            value,
            {
                "technique_overrides",
                "wbs_milestones",
                "pv_buckets",
                "pv_curves",
            },
            "EVM_SETTINGS_UNKNOWN_FIELD",
        )
        try:
            return P6EarnedValueSettings(
                technique_overrides=cls._evm_technique_overrides(
                    value.get("technique_overrides", [])
                ),
                wbs_milestones=cls._evm_wbs_milestones(
                    value.get("wbs_milestones", [])
                ),
                pv_buckets=cls._evm_pv_buckets(value.get("pv_buckets", [])),
                pv_curves=cls._evm_pv_curves(value.get("pv_curves", [])),
            )
        except EarnedValueSourceError as exc:
            raise P6EarnedValueReadModelError(str(exc)) from exc

    @classmethod
    def _evm_items(cls, value: object, code: str) -> tuple[dict, ...]:
        if not isinstance(value, list):
            raise P6EarnedValueReadModelError(code)
        items: list[dict] = []
        for item in value:
            if not isinstance(item, dict):
                raise P6EarnedValueReadModelError(code)
            items.append(item)
        return tuple(items)

    @classmethod
    def _evm_technique_overrides(
        cls, value: object
    ) -> tuple[EarnedValueTechniqueOverride, ...]:
        rows: list[EarnedValueTechniqueOverride] = []
        for item in cls._evm_items(value, "EVM_TECHNIQUE_OVERRIDE_INVALID"):
            cls._reject_unknown_keys(
                item,
                {"wbs_id", "technique"},
                "EVM_TECHNIQUE_OVERRIDE_INVALID",
            )
            rows.append(
                EarnedValueTechniqueOverride(
                    cls._evm_required_string(
                        item,
                        "wbs_id",
                        "EVM_TECHNIQUE_OVERRIDE_WBS_ID_INVALID",
                    ),
                    cls._evm_required_string(
                        item,
                        "technique",
                        "EVM_TECHNIQUE_UNSUPPORTED",
                    ),
                )
            )
        return tuple(rows)

    @classmethod
    def _evm_wbs_milestones(
        cls, value: object
    ) -> tuple[EarnedValueWBSMilestone, ...]:
        rows: list[EarnedValueWBSMilestone] = []
        for item in cls._evm_items(value, "EVM_WBS_MILESTONE_INVALID"):
            cls._reject_unknown_keys(
                item,
                {"wbs_id", "milestone_id", "weight", "completed"},
                "EVM_WBS_MILESTONE_INVALID",
            )
            completed = item.get("completed", False)
            if not isinstance(completed, bool):
                raise P6EarnedValueReadModelError(
                    "EVM_WBS_MILESTONE_COMPLETED_INVALID"
                )
            rows.append(
                EarnedValueWBSMilestone(
                    cls._evm_required_string(
                        item,
                        "wbs_id",
                        "EVM_WBS_MILESTONE_WBS_ID_INVALID",
                    ),
                    cls._evm_required_string(
                        item,
                        "milestone_id",
                        "EVM_WBS_MILESTONE_ID_INVALID",
                    ),
                    cls._evm_decimal(
                        item.get("weight"),
                        "EVM_WBS_MILESTONE_WEIGHT_INVALID",
                    ),
                    completed,
                )
            )
        return tuple(rows)

    @classmethod
    def _evm_pv_buckets(
        cls, value: object
    ) -> tuple[EarnedValuePVBucket, ...]:
        rows: list[EarnedValuePVBucket] = []
        for item in cls._evm_items(value, "EVM_PV_BUCKET_INVALID"):
            cls._reject_unknown_keys(
                item,
                {"activity_id", "period_start", "period_finish", "value"},
                "EVM_PV_BUCKET_INVALID",
            )
            rows.append(
                EarnedValuePVBucket(
                    cls._evm_required_string(
                        item,
                        "activity_id",
                        "EVM_PV_BUCKET_ACTIVITY_ID_INVALID",
                    ),
                    cls._evm_date(
                        item.get("period_start"), "EVM_PV_BUCKET_PERIOD_INVALID"
                    ),
                    cls._evm_date(
                        item.get("period_finish"), "EVM_PV_BUCKET_PERIOD_INVALID"
                    ),
                    cls._evm_decimal(
                        item.get("value"), "EVM_PV_BUCKET_VALUE_INVALID"
                    ),
                )
            )
        return tuple(rows)

    @classmethod
    def _evm_pv_curves(
        cls, value: object
    ) -> tuple[EarnedValuePVCurve, ...]:
        rows: list[EarnedValuePVCurve] = []
        for item in cls._evm_items(value, "EVM_PV_CURVE_INVALID"):
            cls._reject_unknown_keys(
                item,
                {"activity_id", "curve_id", "points"},
                "EVM_PV_CURVE_INVALID",
            )
            points: list[EarnedValuePVCurvePoint] = []
            for point in cls._evm_items(
                item.get("points"), "EVM_PV_CURVE_POINTS_INVALID"
            ):
                cls._reject_unknown_keys(
                    point,
                    {"offset_percent", "cumulative_percent"},
                    "EVM_PV_CURVE_POINTS_INVALID",
                )
                points.append(
                    EarnedValuePVCurvePoint(
                        cls._evm_decimal(
                            point.get("offset_percent"),
                            "EVM_PV_CURVE_OFFSET_INVALID",
                        ),
                        cls._evm_decimal(
                            point.get("cumulative_percent"),
                            "EVM_PV_CURVE_CUMULATIVE_INVALID",
                        ),
                    )
                )
            rows.append(
                EarnedValuePVCurve(
                    cls._evm_required_string(
                        item,
                        "activity_id",
                        "EVM_PV_CURVE_ACTIVITY_ID_INVALID",
                    ),
                    cls._evm_required_string(
                        item, "curve_id", "EVM_PV_CURVE_ID_INVALID"
                    ),
                    tuple(points),
                )
            )
        return tuple(rows)

    @classmethod
    def _evm_error(
        cls, exc: P6EarnedValueReadModelError
    ) -> tuple[int, dict[str, str], bytes]:
        code = str(exc)
        if code.startswith("EVM_BASELINE_ACTIVITIES_EMPTY:"):
            return cls._error(404, code, "error.p6.baseline.not_found")
        if code == "REVISION_CONFLICT" or code in {
            "EVM_PROJECT_CALENDAR_REQUIRED",
            "EVM_PROJECT_CALENDAR_UNRESOLVED",
        }:
            return cls._error(409, code, "error.p6.evm.conflict")
        if code.startswith(
            (
                "EVM_ACTUAL_CURRENCY_MISMATCH",
                "EVM_EXPENSE_CURRENCY_MISMATCH",
                "EVM_ASSIGNMENT_CURRENCY_MISMATCH",
            )
        ):
            return cls._error(409, code, "error.p6.evm.conflict")
        return cls._error(400, code, "error.p6.evm.invalid")

    def _handle_baseline_role_route(
        self,
        method: str,
        path: str,
        *,
        session_id: str,
        now: datetime,
        body: bytes,
    ) -> tuple[int, dict[str, str], bytes] | None:
        """Route BAS-01 summary-role assignment and cross-project conversion."""
        marker = "/p6/baselines/"
        if not path.startswith("/api/projects/") or marker not in path:
            return None
        prefix, remainder = path.split(marker, 1)
        project_id = prefix[len("/api/projects/"):]
        if not project_id:
            return self._error(
                400, "P6_BASELINE_REQUEST_INVALID", "error.request.invalid"
            )
        operation: str | None = None
        baseline_id = ""
        role = ""
        if method == "GET" and remainder == "summary":
            operation = "summary"
        elif method == "POST" and remainder == "convert":
            operation = "convert"
        elif method == "POST" and remainder.endswith("/assign"):
            baseline_id = remainder[: -len("/assign")]
            operation = "assign"
        elif (
            method == "GET"
            and remainder.startswith("roles/")
            and remainder.endswith("/history")
        ):
            role = remainder[len("roles/"):-len("/history")]
            operation = "history"
        if operation is None:
            return None
        if "/" in baseline_id or "/" in role:
            return self._error(
                400, "P6_BASELINE_REQUEST_INVALID", "error.request.invalid"
            )
        if operation == "convert":
            if self._p6_baseline_conversion_api is None:
                return self._error(
                    404, "ROUTE_NOT_FOUND", "error.route.not_found"
                )
        elif self._p6_baseline_assignment_api is None:
            return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
        try:
            context = self._api.open_project(
                session_id, project_id, now=now
            ).context
        except ProjectLifecycleError as exc:
            if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                return self._error(403, str(exc), "error.authorization.denied")
            raise
        session = self._api.get_session(session_id, now=now)
        auth = context.authorization_context(session.roles)
        scope = BackendScope(
            context.tenant_id, context.project_id, context.revision
        )

        if operation == "summary":
            try:
                result = self._p6_baseline_assignment_api.summary(
                    scope, auth_context=auth
                )
            except AuthorizationError as exc:
                return self._error(403, str(exc), "error.authorization.denied")
            except P6BaselineAssignmentError as exc:
                return self._baseline_role_error(exc)
            return self._json(200, result)

        if operation == "history":
            try:
                result = self._p6_baseline_assignment_api.history(
                    scope, role, auth_context=auth
                )
            except AuthorizationError as exc:
                return self._error(403, str(exc), "error.authorization.denied")
            except P6BaselineAssignmentError as exc:
                return self._baseline_role_error(exc)
            return self._json(200, result)

        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._error(
                400, "P6_BASELINE_REQUEST_INVALID", "error.request.invalid"
            )
        if not isinstance(payload, dict):
            return self._error(
                400, "P6_BASELINE_REQUEST_INVALID", "error.request.invalid"
            )

        try:
            if operation == "assign":
                if not baseline_id:
                    raise P6BaselineAssignmentError(
                        "P6_BASELINE_REQUEST_INVALID"
                    )
                result = self._p6_baseline_assignment_api.assign(
                    scope,
                    payload.get("role", ""),
                    baseline_id,
                    expected_revision=payload.get("expected_revision"),
                    replace=payload.get("replace", False),
                    auth_context=auth,
                    contract_version=payload.get(
                        "contract_version",
                        P6_BASELINE_ASSIGNMENT_API_VERSION,
                    ),
                )
                return self._json(200, result)

            source_project_id = payload.get("source_project_id", "")
            if not isinstance(source_project_id, str) or not source_project_id.strip():
                return self._error(
                    400,
                    "P6_BASELINE_REQUEST_INVALID",
                    "error.request.invalid",
                )
            try:
                source_context = self._api.open_project(
                    session_id, source_project_id, now=now
                ).context
            except ProjectLifecycleError as exc:
                if str(exc) == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED":
                    return self._error(
                        403, str(exc), "error.authorization.denied"
                    )
                raise
            source_auth = source_context.authorization_context(session.roles)
            source_scope = BackendScope(
                source_context.tenant_id,
                source_context.project_id,
                source_context.revision,
            )
            result = self._p6_baseline_conversion_api.convert(
                source_scope,
                scope,
                source_baseline_id=payload.get("source_baseline_id"),
                target_baseline_id=payload.get("target_baseline_id", ""),
                target_name=payload.get("name", ""),
                baseline_type=payload.get("baseline_type", "USER_SELECTED"),
                notes=payload.get("notes"),
                expected_revision=payload.get("expected_revision"),
                auth_context=auth,
                source_auth_context=source_auth,
                contract_version=payload.get(
                    "contract_version",
                    P6_BASELINE_CONVERSION_API_VERSION,
                ),
            )
            return self._json(200 if result["replayed"] else 201, result)
        except AuthorizationError as exc:
            return self._error(403, str(exc), "error.authorization.denied")
        except P6BaselineAssignmentError as exc:
            return self._baseline_role_error(exc)
        except P6BaselineConversionError as exc:
            return self._baseline_conversion_error(exc)
        except (
            P6BaselinePersistenceError,
            P6BaselineActivityPersistenceError,
            P6CurrentActivityPersistenceError,
        ) as exc:
            code = str(exc)
            if code == "REVISION_CONFLICT":
                return self._error(
                    409, code, "error.p6.baseline.conflict"
                )
            return self._error(400, code, "error.p6.baseline.invalid")

    @classmethod
    def _baseline_role_error(
        cls, exc: P6BaselineAssignmentError
    ) -> tuple[int, dict[str, str], bytes]:
        code = str(exc)
        if code == "BASELINE_NOT_FOUND":
            return cls._error(404, code, "error.p6.baseline.not_found")
        if code == "REVISION_CONFLICT" or code.startswith(
            "BASELINE_ROLE_ALREADY_ASSIGNED:"
        ):
            return cls._error(409, code, "error.p6.baseline.conflict")
        return cls._error(400, code, "error.p6.baseline.invalid")

    @classmethod
    def _baseline_conversion_error(
        cls, exc: P6BaselineConversionError
    ) -> tuple[int, dict[str, str], bytes]:
        code = str(exc)
        if code == "BASELINE_CONVERSION_SOURCE_NOT_FOUND":
            return cls._error(404, code, "error.p6.baseline.not_found")
        if code in {
            "BASELINE_CONVERSION_TARGET_EXISTS",
            "BASELINE_CONVERSION_SOURCE_EMPTY",
        }:
            return cls._error(409, code, "error.p6.baseline.conflict")
        return cls._error(400, code, "error.p6.baseline.invalid")

    def _handle_baseline_update_route(
        self,
        method: str,
        path: str,
        *,
        session_id: str,
        now: datetime,
        body: bytes,
    ) -> tuple[int, dict[str, str], bytes] | None:
        """Route BAS-02 preview/apply/compare over the versioned API.

        The current project state is always read from the persisted current
        activity source inside the service. The request body may select what to
        copy, but it can never supply the current values themselves.
        """
        if method != "POST":
            return None
        marker = "/p6/baselines/"
        if not path.startswith("/api/projects/") or marker not in path:
            return None
        prefix, remainder = path.split(marker, 1)
        project_id = prefix[len("/api/projects/"):]
        operation: str | None = None
        baseline_id = ""
        for suffix, name in (
            ("/update/preview", "preview"),
            ("/update/apply", "apply"),
            ("/compare", "compare"),
        ):
            if remainder.endswith(suffix):
                baseline_id = remainder[: -len(suffix)]
                operation = name
                break
        if operation is None:
            return None
        if not project_id or not baseline_id or "/" in baseline_id:
            return self._error(
                400,
                "P6_BASELINE_UPDATE_REQUEST_INVALID",
                "error.request.invalid",
            )
        if self._p6_baseline_update_api is None:
            return self._error(404, "ROUTE_NOT_FOUND", "error.route.not_found")
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
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._error(
                400,
                "P6_BASELINE_UPDATE_REQUEST_INVALID",
                "error.request.invalid",
            )
        if not isinstance(payload, dict):
            return self._error(
                400,
                "P6_BASELINE_UPDATE_REQUEST_INVALID",
                "error.request.invalid",
            )
        if "current" in payload or "current_activities" in payload:
            return self._error(
                400,
                "BASELINE_UPDATE_CURRENT_BODY_FORBIDDEN",
                "error.request.invalid",
            )
        try:
            contract_version = payload.get("contract_version", "")
            expected_revision = payload.get("expected_revision")
            if isinstance(expected_revision, bool):
                raise P6BaselineUpdateError("BASELINE_UPDATE_REVISION_INVALID")
            if operation == "compare":
                self._reject_unknown_baseline_update_keys(
                    payload,
                    {"contract_version", "expected_revision", "activity_ids"},
                )
                raw_ids = payload.get("activity_ids")
                activity_ids = (
                    None
                    if raw_ids is None
                    else self._baseline_update_id_list(raw_ids)
                )
                result = self._p6_baseline_update_api.compare(
                    scope,
                    baseline_id,
                    expected_revision=expected_revision,
                    auth_context=auth,
                    activity_ids=activity_ids,
                    contract_version=contract_version,
                )
            else:
                selection = self._baseline_update_selection(
                    payload.get("selection")
                )
                target_baseline_id = payload.get("target_baseline_id", "")
                if operation == "preview":
                    self._reject_unknown_baseline_update_keys(
                        payload,
                        {
                            "contract_version",
                            "expected_revision",
                            "target_baseline_id",
                            "selection",
                        },
                    )
                    result = self._p6_baseline_update_api.preview(
                        scope,
                        baseline_id,
                        target_baseline_id,
                        selection,
                        expected_revision=expected_revision,
                        auth_context=auth,
                        contract_version=contract_version,
                    )
                else:
                    self._reject_unknown_baseline_update_keys(
                        payload,
                        {
                            "contract_version",
                            "expected_revision",
                            "target_baseline_id",
                            "selection",
                            "target_name",
                            "baseline_type",
                        },
                    )
                    result = self._p6_baseline_update_api.apply(
                        scope,
                        baseline_id,
                        target_baseline_id,
                        selection,
                        target_name=payload.get("target_name", ""),
                        expected_revision=expected_revision,
                        auth_context=auth,
                        baseline_type=payload.get(
                            "baseline_type", "USER_SELECTED"
                        ),
                        contract_version=contract_version,
                    )
        except AuthorizationError as exc:
            return self._error(403, str(exc), "error.authorization.denied")
        except P6BaselineUpdateError as exc:
            return self._baseline_update_error(exc)
        except (
            P6BaselinePersistenceError,
            P6BaselineActivityPersistenceError,
            P6CurrentActivityPersistenceError,
        ) as exc:
            code = str(exc)
            if code in {
                "REVISION_CONFLICT",
                "IMMUTABLE_BASELINE",
                "IMMUTABLE_BASELINE_ACTIVITIES",
            }:
                return self._error(
                    409, code, "error.p6.baseline.update.conflict"
                )
            return self._error(
                400, code, "error.p6.baseline.update.invalid"
            )
        return self._json(201 if operation == "apply" else 200, result)

    @staticmethod
    def _reject_unknown_baseline_update_keys(
        payload: Mapping[str, object], allowed: set[str]
    ) -> None:
        if set(payload) - allowed:
            raise P6BaselineUpdateError(
                "P6_BASELINE_UPDATE_REQUEST_INVALID"
            )

    @staticmethod
    def _baseline_update_id_list(value: object) -> tuple[str, ...]:
        if not isinstance(value, list) or any(
            not isinstance(item, str)
            or not item.strip()
            or item != item.strip()
            for item in value
        ):
            raise P6BaselineUpdateError(
                "BASELINE_UPDATE_ACTIVITY_IDS_INVALID"
            )
        return tuple(value)

    @classmethod
    def _baseline_update_selection(
        cls, value: object
    ) -> P6BaselineUpdateSelection:
        if value is None:
            return P6BaselineUpdateSelection()
        if not isinstance(value, dict):
            raise P6BaselineUpdateError("BASELINE_UPDATE_SELECTION_INVALID")
        allowed = {
            "activity_ids",
            "fields",
            "add_new_activities",
            "remove_missing_activities",
        }
        if set(value) - allowed:
            raise P6BaselineUpdateError("BASELINE_UPDATE_SELECTION_INVALID")
        raw_ids = value.get("activity_ids")
        activity_ids = (
            None
            if raw_ids is None
            else frozenset(cls._baseline_update_id_list(raw_ids))
        )
        raw_fields = value.get("fields")
        if raw_fields is None:
            fields = frozenset(BASELINE_UPDATE_FIELDS)
        else:
            if not isinstance(raw_fields, list) or any(
                not isinstance(item, str) or not item.strip()
                for item in raw_fields
            ):
                raise P6BaselineUpdateError("BASELINE_UPDATE_FIELDS_INVALID")
            fields = frozenset(raw_fields)
        return P6BaselineUpdateSelection(
            activity_ids=activity_ids,
            fields=fields,
            add_new_activities=value.get("add_new_activities", True),
            remove_missing_activities=value.get(
                "remove_missing_activities", False
            ),
        )

    @classmethod
    def _baseline_update_error(
        cls, exc: P6BaselineUpdateError
    ) -> tuple[int, dict[str, str], bytes]:
        code = str(exc)
        if code == "BASELINE_UPDATE_SOURCE_NOT_FOUND":
            return cls._error(
                404, code, "error.p6.baseline.not_found"
            )
        if code in {
            "BASELINE_UPDATE_STALE_REVISION",
            "BASELINE_UPDATE_TARGET_ALREADY_EXISTS",
            "BASELINE_UPDATE_CURRENT_EMPTY",
        } or code.startswith("BASELINE_UPDATE_CURRENCY_MISMATCH:"):
            return cls._error(
                409, code, "error.p6.baseline.update.conflict"
            )
        if code == "BASELINE_UPDATE_CURRENT_SOURCE_REQUIRED":
            return cls._error(
                503, code, "error.p6.baseline.update.unavailable"
            )
        return cls._error(
            400, code, "error.p6.baseline.update.invalid"
        )

    def _handle_form_route(
        self,
        method: str,
        path: str,
        *,
        session_id: str,
        now: datetime,
        body: bytes,
        headers: Mapping[str, str],
    ) -> tuple[int, dict[str, str], bytes]:
        assert self._form_builder_routes is not None
        split = urlsplit(path)
        route_path = split.path
        query = {
            key: values[-1]
            for key, values in parse_qs(split.query, keep_blank_values=True).items()
        }
        session = self._api.get_session(session_id, now=now)
        if route_path.startswith(ORGANIZATION_ROUTE):
            auth = AuthorizationContext(
                tenant_id=session.tenant_id,
                project_id="__organization__",
                user_id=session.user_id,
                roles=frozenset(session.roles),
            )
        else:
            project_id = route_path[len("/api/projects/"):route_path.find("/forms")].strip("/")
            context = self._api.open_project(session_id, project_id, now=now).context
            auth = context.authorization_context(session.roles)
        return self._form_builder_routes.handle(
            method,
            route_path,
            auth=auth,
            body=body,
            headers=headers,
            query=query,
        )

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
        non_retryable_integrity_errors = {
            "AI_ACTION_EXECUTION_RESULT_NOT_PERSISTED",
            "AI_ACTION_EXECUTION_STATE_NOT_PERSISTED",
            "AI_ACTION_EXECUTION_RESERVATION_FAILED",
            "AI_ACTION_IDEMPOTENCY_RESULT_NOT_PERSISTED",
            "AI_ACTION_IDEMPOTENCY_RESULT_INVALID",
        }
        retryable = status >= 500 and code not in non_retryable_integrity_errors
        return cls._json(status, {
            "code": code,
            "retryable": retryable,
            "message_key": message_key,
            "available_actions": ["retry"] if retryable else [],
        })
