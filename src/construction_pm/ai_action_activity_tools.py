from __future__ import annotations

import json
import sqlite3
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Callable, Mapping

from .ai_action_boundary import AIActionProposal, AIToolPermissionAdapter
from .ai_action_runtime import (
    AIActionExecutionRejected,
    AIActionRuntime,
    AIActionRuntimeContext,
    AIActionRuntimeError,
    AIActionToolDefinition,
    PostgresAIActionRuntimeStore,
    SQLiteAIActionRuntimeStore,
)
from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy
from .backend_p0.idempotency import fingerprint
from .backend_p0.models import BackendScope
from .p6_activity_master_api import P6ActivityMasterAPI
from .activity_master_repository import (
    ActivityMaster,
    ActivityMasterRepository,
    ActivityPersistenceError,
    PostgresActivityMasterRepository,
    SQLiteActivityMasterRepository,
)
from .scheduling.activity import (
    ActivityLevelingPriority,
    ActivityStatus,
    ActivityStatusCode,
    ActivityType,
    PercentCompleteType,
)
from .scheduling.time_duration import DurationUnit


class AIActionExecutionIdempotencyStore:
    """Durable idempotency records that participate in the same DB transaction as the mutation.

    The store deliberately does not commit or roll back. Its caller must use the same
    connection and application-owned transaction as the authoritative use case.
    """

    def __init__(self, connection: object, *, placeholder: str) -> None:
        if placeholder not in {"?", "%s"}:
            raise ValueError("UNSUPPORTED_SQL_PLACEHOLDER")
        self.connection = connection
        self.placeholder = placeholder
        was_in_transaction = bool(getattr(connection, "in_transaction", False))
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS ai_action_tool_idempotency (
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                result_json TEXT,
                PRIMARY KEY (tenant_id, project_id, tool_name, idempotency_key)
            )"""
        )
        # SQLite DDL/setup may be committed when this repository owns setup. Never
        # commit an already active application transaction. PostgreSQL setup follows
        # the application's transaction lifecycle.
        if isinstance(connection, sqlite3.Connection) and not was_in_transaction:
            connection.commit()

    def execute(
        self,
        *,
        tenant_id: str,
        project_id: str,
        tool_name: str,
        idempotency_key: str,
        request_fingerprint: str,
        mutation: Callable[[], Mapping[str, object]],
    ) -> Mapping[str, object]:
        for name, value in (
            ("tenant_id", tenant_id),
            ("project_id", project_id),
            ("tool_name", tool_name),
            ("idempotency_key", idempotency_key),
            ("fingerprint", request_fingerprint),
        ):
            if not isinstance(value, str) or not value.strip():
                raise AIActionRuntimeError(f"AI_ACTION_IDEMPOTENCY_{name.upper()}_REQUIRED")

        p = self.placeholder
        cursor = self.connection.execute(
            "INSERT INTO ai_action_tool_idempotency "
            "(tenant_id, project_id, tool_name, idempotency_key, fingerprint, result_json) "
            f"VALUES ({p},{p},{p},{p},{p},NULL) "
            "ON CONFLICT (tenant_id, project_id, tool_name, idempotency_key) DO NOTHING",
            (tenant_id, project_id, tool_name, idempotency_key, request_fingerprint),
        )
        if cursor.rowcount == 1:
            result = mutation()
            if not isinstance(result, Mapping):
                raise AIActionRuntimeError("AI_ACTION_IDEMPOTENCY_RESULT_INVALID")
            try:
                encoded = json.dumps(dict(result), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            except (TypeError, ValueError) as exc:
                raise AIActionRuntimeError("AI_ACTION_IDEMPOTENCY_RESULT_INVALID") from exc
            updated = self.connection.execute(
                "UPDATE ai_action_tool_idempotency SET result_json=" + p
                + " WHERE tenant_id=" + p + " AND project_id=" + p
                + " AND tool_name=" + p + " AND idempotency_key=" + p
                + " AND fingerprint=" + p + " AND result_json IS NULL",
                (encoded, tenant_id, project_id, tool_name, idempotency_key, request_fingerprint),
            )
            if updated.rowcount != 1:
                raise AIActionRuntimeError("AI_ACTION_IDEMPOTENCY_RESULT_NOT_PERSISTED")
            return dict(result)

        row = self.connection.execute(
            "SELECT fingerprint, result_json FROM ai_action_tool_idempotency "
            "WHERE tenant_id=" + p + " AND project_id=" + p
            + " AND tool_name=" + p + " AND idempotency_key=" + p,
            (tenant_id, project_id, tool_name, idempotency_key),
        ).fetchone()
        if row is None:
            raise AIActionRuntimeError("AI_ACTION_IDEMPOTENCY_RESULT_NOT_PERSISTED")
        if str(row[0]) != request_fingerprint:
            raise AIActionRuntimeError("AI_ACTION_IDEMPOTENCY_KEY_REUSE")
        if row[1] is None:
            raise AIActionRuntimeError("AI_ACTION_IDEMPOTENCY_RESULT_NOT_PERSISTED")
        try:
            replay = json.loads(str(row[1]))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AIActionRuntimeError("AI_ACTION_IDEMPOTENCY_RESULT_INVALID") from exc
        if not isinstance(replay, dict):
            raise AIActionRuntimeError("AI_ACTION_IDEMPOTENCY_RESULT_INVALID")
        return replay


class SQLiteAIActionExecutionIdempotencyStore(AIActionExecutionIdempotencyStore):
    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__(connection, placeholder="?")


class PostgresAIActionExecutionIdempotencyStore(AIActionExecutionIdempotencyStore):
    def __init__(self, connection: object) -> None:
        super().__init__(connection, placeholder="%s")


def _build_activity_runtime(
    *,
    activity_master_repository: ActivityMasterRepository,
    authorization_policy: AuthorizationPolicy,
    permission_adapter: AIToolPermissionAdapter,
    transaction_manager: object,
    clock: Callable[[], datetime] | None,
    include_update: bool,
) -> AIActionRuntime:
    """Compose real typed activity tools over one authoritative connection.

    There is intentionally no default grant adapter and no in-memory fallback. The
    activity repository, action proposal/audit tables, tool idempotency table and
    transaction manager are all bound to one supported SQLite or PostgreSQL connection.
    """
    connection = getattr(transaction_manager, "connection", None)
    repository_connection = getattr(activity_master_repository, "connection", None)
    if connection is None or repository_connection is not connection:
        raise AIActionRuntimeError("AI_ACTION_ACTIVITY_TOOL_TRANSACTION_CONNECTION_MISMATCH")

    if isinstance(activity_master_repository, SQLiteActivityMasterRepository):
        if not isinstance(connection, sqlite3.Connection):
            raise AIActionRuntimeError("AI_ACTION_ACTIVITY_TOOL_STORAGE_ADAPTER_MISMATCH")
        runtime_store = SQLiteAIActionRuntimeStore(connection)
        idempotency_store = SQLiteAIActionExecutionIdempotencyStore(connection)
    elif isinstance(activity_master_repository, PostgresActivityMasterRepository):
        runtime_store = PostgresAIActionRuntimeStore(connection)
        idempotency_store = PostgresAIActionExecutionIdempotencyStore(connection)
    else:
        raise AIActionRuntimeError("AI_ACTION_ACTIVITY_TOOL_STORAGE_ADAPTER_UNSUPPORTED")

    activity_api = P6ActivityMasterAPI(activity_master_repository, authorization_policy)
    tools: list[AIActionToolDefinition] = [
        build_activity_create_tool(
            activity_api=activity_api,
            idempotency_store=idempotency_store,
            transaction_manager=transaction_manager,
        )
    ]
    if include_update:
        tools.append(
            build_activity_update_tool(
                activity_api=activity_api,
                idempotency_store=idempotency_store,
                transaction_manager=transaction_manager,
            )
        )
    return AIActionRuntime(
        store=runtime_store,
        permission_adapter=permission_adapter,
        audit_sink=runtime_store,
        tools=tuple(tools),
        clock=clock,
        transaction_manager=transaction_manager,
    )


def build_activity_create_runtime(
    *,
    activity_master_repository: ActivityMasterRepository,
    authorization_policy: AuthorizationPolicy,
    permission_adapter: AIToolPermissionAdapter,
    transaction_manager: object,
    clock: Callable[[], datetime] | None = None,
) -> AIActionRuntime:
    """Compose only the create tool; retained for callers that require that narrow surface."""
    return _build_activity_runtime(
        activity_master_repository=activity_master_repository,
        authorization_policy=authorization_policy,
        permission_adapter=permission_adapter,
        transaction_manager=transaction_manager,
        clock=clock,
        include_update=False,
    )


def build_activity_action_runtime(
    *,
    activity_master_repository: ActivityMasterRepository,
    authorization_policy: AuthorizationPolicy,
    permission_adapter: AIToolPermissionAdapter,
    transaction_manager: object,
    clock: Callable[[], datetime] | None = None,
) -> AIActionRuntime:
    """Compose the production create and update tools with the same guarantees."""
    return _build_activity_runtime(
        activity_master_repository=activity_master_repository,
        authorization_policy=authorization_policy,
        permission_adapter=permission_adapter,
        transaction_manager=transaction_manager,
        clock=clock,
        include_update=True,
    )


def _execution_binding(
    proposal: AIActionProposal,
    context: AIActionRuntimeContext,
) -> tuple[BackendScope, AuthorizationContext]:
    """Derive all scope and identity values from trusted execution context only."""
    context.validate()
    try:
        revision = int(context.project_revision_id, 10)
    except (TypeError, ValueError) as exc:
        raise AIActionRuntimeError("AI_ACTION_ACTIVITY_PROJECT_REVISION_INVALID") from exc
    if revision < 0 or str(revision) != context.project_revision_id:
        raise AIActionRuntimeError("AI_ACTION_ACTIVITY_PROJECT_REVISION_INVALID")
    if (
        proposal.tenant_id != context.tenant_id
        or proposal.project_id != context.project_id
        or proposal.project_revision_id != context.project_revision_id
        or proposal.requested_by != context.subject_id
    ):
        raise AIActionRuntimeError("AI_ACTION_ACTIVITY_TOOL_SCOPE_MISMATCH")
    return (
        BackendScope(context.tenant_id, context.project_id, revision),
        AuthorizationContext(
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            user_id=context.subject_id,
            roles=context.roles,
        ),
    )


def build_activity_create_tool(
    *,
    activity_api: P6ActivityMasterAPI,
    idempotency_store: AIActionExecutionIdempotencyStore,
    transaction_manager: object,
) -> AIActionToolDefinition:
    """Build a real Activity Master create tool over the authoritative authenticated API.

    The activity repository, idempotency store, AI proposal/audit store and transaction
    manager must share one connection. This factory rejects split-connection wiring
    instead of silently offering a false atomicity guarantee.
    """
    connection = getattr(transaction_manager, "connection", None)
    repository_connection = getattr(activity_api.repository, "connection", None)
    idempotency_connection = getattr(idempotency_store, "connection", None)
    if connection is None or repository_connection is not connection or idempotency_connection is not connection:
        raise AIActionRuntimeError("AI_ACTION_ACTIVITY_TOOL_TRANSACTION_CONNECTION_MISMATCH")

    allowed_keys = {
        "activity_id", "name", "duration_value", "duration_unit",
        "activity_type", "status", "status_code",
        "percent_complete_type", "leveling_priority",
    }

    def validate_payload(payload: Mapping[str, object]) -> Mapping[str, object]:
        if not isinstance(payload, Mapping) or not set(payload).issubset(allowed_keys):
            raise ValueError("ACTIVITY_CREATE_PAYLOAD_INVALID")
        required = ("activity_id", "name", "duration_value", "duration_unit")
        if any(key not in payload for key in required):
            raise ValueError("ACTIVITY_CREATE_REQUIRED_FIELD_MISSING")
        if any(not isinstance(payload.get(key), str) or not str(payload.get(key)).strip()
               for key in ("activity_id", "name", "duration_unit")):
            raise ValueError("ACTIVITY_CREATE_TEXT_FIELD_INVALID")
        raw_duration = payload.get("duration_value")
        if isinstance(raw_duration, bool):
            raise ValueError("ACTIVITY_CREATE_DURATION_INVALID")
        try:
            duration = Decimal(str(raw_duration))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("ACTIVITY_CREATE_DURATION_INVALID") from exc
        if not duration.is_finite() or duration < 0:
            raise ValueError("ACTIVITY_CREATE_DURATION_INVALID")

        duration_unit = DurationUnit(str(payload["duration_unit"]))
        activity_type = ActivityType.from_p6_value(
            str(payload.get("activity_type", ActivityType.TASK_DEPENDENT.value))
        )
        status = ActivityStatus.from_p6_value(
            str(payload.get("status", ActivityStatus.NOT_STARTED.value))
        )
        status_code = ActivityStatusCode.from_p6_value(
            str(payload.get("status_code", ActivityStatusCode.PLANNED.value))
        )
        percent_type = PercentCompleteType(
            str(payload.get("percent_complete_type", PercentCompleteType.DURATION.value))
        )
        leveling_priority = ActivityLevelingPriority.from_p6_value(
            str(payload.get("leveling_priority", ActivityLevelingPriority.NORMAL.value))
        )
        return {
            "activity_id": str(payload["activity_id"]).strip(),
            "name": str(payload["name"]).strip(),
            "duration_value": str(duration),
            "duration_unit": duration_unit.value,
            "activity_type": activity_type.value,
            "status": status.value,
            "status_code": status_code.value,
            "percent_complete_type": percent_type.value,
            "leveling_priority": leveling_priority.value,
        }

    def execute(
        payload: Mapping[str, object],
        proposal: AIActionProposal,
        idempotency_key: str,
        context: AIActionRuntimeContext,
    ) -> Mapping[str, object]:
        # Scope, actor, and roles come only from the authenticated request context.
        scope, auth = _execution_binding(proposal, context)
        activity = ActivityMaster(
            scope=scope,
            activity_id=str(payload["activity_id"]),
            duration_value=Decimal(str(payload["duration_value"])),
            duration_unit=DurationUnit(str(payload["duration_unit"])),
            name=str(payload["name"]),
            activity_type=ActivityType.from_p6_value(str(payload["activity_type"])),
            status=ActivityStatus.from_p6_value(str(payload["status"])),
            status_code=ActivityStatusCode.from_p6_value(str(payload["status_code"])),
            percent_complete_type=PercentCompleteType(str(payload["percent_complete_type"])),
            leveling_priority=ActivityLevelingPriority.from_p6_value(str(payload["leveling_priority"])),
        )
        request_fingerprint = fingerprint({
            "operation": "activity.create",
            "tenant_id": context.tenant_id,
            "project_id": context.project_id,
            "project_revision_id": context.project_revision_id,
            "payload": dict(payload),
        })

        def mutation() -> Mapping[str, object]:
            try:
                return activity_api.create(activity, auth_context=auth)
            except AuthorizationError as exc:
                raise AIActionExecutionRejected("AI_TOOL_NOT_PERMITTED") from exc
            except ActivityPersistenceError as exc:
                if str(exc) == "REVISION_CONFLICT":
                    # An existing activity ID is a known pre-write rejection, not
                    # an uncertain side effect that would require reconciliation.
                    raise AIActionExecutionRejected(
                        "AI_ACTION_ACTIVITY_ALREADY_EXISTS"
                    ) from exc
                raise AIActionExecutionRejected(
                    "AI_ACTION_ACTIVITY_CREATE_REJECTED"
                ) from exc

        return idempotency_store.execute(
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            tool_name=proposal.tool_name,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            mutation=mutation,
        )

    return AIActionToolDefinition(
        tool_name="activity.create",
        action="create",
        resource_domain="activities",
        requires_human_approval=True,
        validate_payload=validate_payload,
        execute=execute,
        description=(
            "Prepare a proposal to create one activity. The user must provide an activity ID, "
            "activity name, duration value, and duration unit; never invent missing project values."
        ),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["activity_id", "name", "duration_value", "duration_unit"],
            "properties": {
                "activity_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "The exact activity ID supplied or confirmed by the user.",
                },
                "name": {
                    "type": "string",
                    "minLength": 1,
                    "description": "The activity name supplied or confirmed by the user.",
                },
                "duration_value": {
                    "type": "number",
                    "minimum": 0,
                    "description": "The non-negative duration explicitly supplied or confirmed by the user.",
                },
                "duration_unit": {
                    "type": "string",
                    "enum": ["working-day", "working-hour"],
                    "description": "The duration unit explicitly supplied or confirmed by the user.",
                },
            },
        },
    )


def build_activity_update_tool(
    *,
    activity_api: P6ActivityMasterAPI,
    idempotency_store: AIActionExecutionIdempotencyStore,
    transaction_manager: object,
) -> AIActionToolDefinition:
    """Build a field-limited, revision-locked Activity Master edit tool.

    A proposal carries only the activity identity, the record revision the user saw,
    and the requested name/duration change. Scope, actor, project revision, and roles
    are always taken from the trusted execution context. Actual dates, progress,
    status codes, relationships, resources, and costs are not writable here.
    """
    connection = getattr(transaction_manager, "connection", None)
    repository_connection = getattr(activity_api.repository, "connection", None)
    idempotency_connection = getattr(idempotency_store, "connection", None)
    if connection is None or repository_connection is not connection or idempotency_connection is not connection:
        raise AIActionRuntimeError("AI_ACTION_ACTIVITY_TOOL_TRANSACTION_CONNECTION_MISMATCH")

    allowed_keys = {"activity_id", "expected_revision", "name", "duration_value", "duration_unit"}

    def validate_payload(payload: Mapping[str, object]) -> Mapping[str, object]:
        if not isinstance(payload, Mapping) or not set(payload).issubset(allowed_keys):
            raise ValueError("ACTIVITY_UPDATE_PAYLOAD_INVALID")
        if "activity_id" not in payload or "expected_revision" not in payload:
            raise ValueError("ACTIVITY_UPDATE_REQUIRED_FIELD_MISSING")
        activity_id = payload.get("activity_id")
        if not isinstance(activity_id, str) or not activity_id.strip():
            raise ValueError("ACTIVITY_UPDATE_ACTIVITY_ID_INVALID")
        expected_revision = payload.get("expected_revision")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 1:
            raise ValueError("ACTIVITY_UPDATE_EXPECTED_REVISION_INVALID")

        normalized: dict[str, object] = {
            "activity_id": activity_id.strip(),
            "expected_revision": expected_revision,
        }
        changed = False
        if "name" in payload:
            name = payload.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("ACTIVITY_UPDATE_NAME_INVALID")
            normalized["name"] = name.strip()
            changed = True
        duration_keys = {"duration_value", "duration_unit"} & set(payload)
        if duration_keys:
            if duration_keys != {"duration_value", "duration_unit"}:
                raise ValueError("ACTIVITY_UPDATE_DURATION_PAIR_REQUIRED")
            raw_duration = payload.get("duration_value")
            if isinstance(raw_duration, bool):
                raise ValueError("ACTIVITY_UPDATE_DURATION_INVALID")
            try:
                duration = Decimal(str(raw_duration))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise ValueError("ACTIVITY_UPDATE_DURATION_INVALID") from exc
            if not duration.is_finite() or duration < 0:
                raise ValueError("ACTIVITY_UPDATE_DURATION_INVALID")
            normalized["duration_value"] = str(duration)
            normalized["duration_unit"] = DurationUnit(str(payload.get("duration_unit"))).value
            changed = True
        if not changed:
            raise ValueError("ACTIVITY_UPDATE_NO_CHANGES")
        return normalized

    def execute(
        payload: Mapping[str, object],
        proposal: AIActionProposal,
        idempotency_key: str,
        context: AIActionRuntimeContext,
    ) -> Mapping[str, object]:
        scope, auth = _execution_binding(proposal, context)
        activity_id = str(payload["activity_id"])
        expected_revision = int(payload["expected_revision"])
        changes: dict[str, object] = {}
        if "name" in payload:
            changes["name"] = str(payload["name"])
        if "duration_value" in payload:
            changes["duration_value"] = str(payload["duration_value"])
            changes["duration_unit"] = str(payload["duration_unit"])
        request_fingerprint = fingerprint({
            "operation": "activity.update",
            "tenant_id": context.tenant_id,
            "project_id": context.project_id,
            "project_revision_id": context.project_revision_id,
            "payload": dict(payload),
        })

        def mutation() -> Mapping[str, object]:
            try:
                return activity_api.update_fields(
                    scope,
                    activity_id,
                    expected_revision=expected_revision,
                    changes=changes,
                    auth_context=auth,
                )
            except AuthorizationError as exc:
                raise AIActionExecutionRejected("AI_TOOL_NOT_PERMITTED") from exc
            except ActivityPersistenceError as exc:
                code = str(exc)
                if code == "ACTIVITY_NOT_FOUND":
                    raise AIActionExecutionRejected("AI_ACTION_ACTIVITY_NOT_FOUND") from exc
                if code == "REVISION_CONFLICT":
                    raise AIActionExecutionRejected(
                        "AI_ACTION_ACTIVITY_REVISION_CONFLICT"
                    ) from exc
                raise AIActionExecutionRejected(
                    "AI_ACTION_ACTIVITY_UPDATE_REJECTED"
                ) from exc
            except ValueError as exc:
                # All payload and type validation happens before the repository write.
                raise AIActionExecutionRejected(
                    "AI_ACTION_ACTIVITY_UPDATE_REJECTED"
                ) from exc

        return idempotency_store.execute(
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            tool_name=proposal.tool_name,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            mutation=mutation,
        )

    return AIActionToolDefinition(
        tool_name="activity.update",
        action="update",
        resource_domain="activities",
        requires_human_approval=True,
        validate_payload=validate_payload,
        execute=execute,
        description=(
            "Prepare a proposal to change only an existing activity's name and/or duration. "
            "Use the exact activity ID and saved record revision the user supplies; never invent "
            "revisions, durations, progress, actual dates, relationships, or resources."
        ),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["activity_id", "expected_revision"],
            "properties": {
                "activity_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "The exact existing activity ID supplied or confirmed by the user.",
                },
                "expected_revision": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "The activity record revision the user is editing.",
                },
                "name": {
                    "type": "string",
                    "minLength": 1,
                    "description": "A new activity name explicitly requested by the user.",
                },
                "duration_value": {
                    "type": "number",
                    "minimum": 0,
                    "description": "A new non-negative duration explicitly requested together with its unit.",
                },
                "duration_unit": {
                    "type": "string",
                    "enum": ["working-day", "working-hour"],
                    "description": "The duration unit explicitly requested together with the new value.",
                },
            },
        },
    )


__all__ = [
    "AIActionExecutionIdempotencyStore",
    "SQLiteAIActionExecutionIdempotencyStore",
    "PostgresAIActionExecutionIdempotencyStore",
    "build_activity_create_tool",
    "build_activity_update_tool",
    "build_activity_create_runtime",
    "build_activity_action_runtime",
]
