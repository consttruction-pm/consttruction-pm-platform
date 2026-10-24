from __future__ import annotations

import json
import sqlite3
from decimal import Decimal, InvalidOperation
from typing import Callable, Mapping

from .ai_action_boundary import AIActionProposal
from .ai_action_runtime import (
    AIActionRuntimeContext,
    AIActionRuntimeError,
    AIActionToolDefinition,
)
from .application.authorization import AuthorizationContext
from .backend_p0.idempotency import fingerprint
from .backend_p0.models import BackendScope
from .p6_activity_master_api import P6ActivityMasterAPI
from .activity_master_repository import ActivityMaster
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

        scope = BackendScope(context.tenant_id, context.project_id, revision)
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
        auth = AuthorizationContext(
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            user_id=context.subject_id,
            roles=context.roles,
        )
        request_fingerprint = fingerprint({
            "operation": "activity.create",
            "tenant_id": context.tenant_id,
            "project_id": context.project_id,
            "project_revision_id": context.project_revision_id,
            "payload": dict(payload),
        })

        return idempotency_store.execute(
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            tool_name=proposal.tool_name,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            mutation=lambda: activity_api.create(activity, auth_context=auth),
        )

    return AIActionToolDefinition(
        tool_name="activity.create",
        action="create",
        resource_domain="activities",
        requires_human_approval=True,
        validate_payload=validate_payload,
        execute=execute,
    )


__all__ = [
    "AIActionExecutionIdempotencyStore",
    "SQLiteAIActionExecutionIdempotencyStore",
    "PostgresAIActionExecutionIdempotencyStore",
    "build_activity_create_tool",
]
