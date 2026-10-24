from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable, Mapping, Protocol
from uuid import uuid4

from .ai_action_boundary import (
    AIActionApprovalService,
    AIActionAuditSink,
    AIActionBoundaryError,
    AIActionDecision,
    AIActionProposal,
    AIToolPermissionAdapter,
)


class AIActionRuntimeError(ValueError):
    """Stable error code for a denied, stale, conflicting, or failed AI action."""


@dataclass(frozen=True)
class AIActionRuntimeContext:
    """Trusted scope resolved by the authenticated application layer, never by the model."""

    subject_id: str
    tenant_id: str
    project_id: str
    project_revision_id: str

    def validate(self) -> None:
        for name, value in (
            ("subject_id", self.subject_id),
            ("tenant_id", self.tenant_id),
            ("project_id", self.project_id),
            ("project_revision_id", self.project_revision_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise AIActionRuntimeError(f"AI_ACTION_CONTEXT_{name.upper()}_REQUIRED")


PayloadValidator = Callable[[Mapping[str, object]], Mapping[str, object]]
ToolExecutor = Callable[
    [Mapping[str, object], AIActionProposal, str], Mapping[str, object]
]


@dataclass(frozen=True)
class AIActionToolDefinition:
    """A server-registered action; clients cannot choose its privilege or approval policy."""

    tool_name: str
    action: str
    resource_domain: str
    requires_human_approval: bool
    validate_payload: PayloadValidator
    execute: ToolExecutor

    def validate(self) -> None:
        for name, value in (
            ("tool_name", self.tool_name),
            ("action", self.action),
            ("resource_domain", self.resource_domain),
        ):
            if not isinstance(value, str) or not value.strip():
                raise AIActionRuntimeError(f"AI_ACTION_TOOL_{name.upper()}_REQUIRED")
        if not isinstance(self.requires_human_approval, bool):
            raise AIActionRuntimeError("AI_ACTION_TOOL_APPROVAL_POLICY_INVALID")
        if not callable(self.validate_payload) or not callable(self.execute):
            raise AIActionRuntimeError("AI_ACTION_TOOL_HANDLER_REQUIRED")


@dataclass(frozen=True)
class AIActionStoredProposal:
    proposal: AIActionProposal
    payload: Mapping[str, object]
    status: str
    created_at: datetime
    updated_at: datetime
    decided_by: str | None = None
    result: Mapping[str, object] | None = None


class AIActionRuntimeAuditSink(AIActionAuditSink, Protocol):
    def record_event(
        self,
        proposal: AIActionProposal,
        event_type: str,
        *,
        actor_id: str | None = None,
        metadata: Mapping[str, object] | None = None,
        happened_at: datetime | None = None,
    ) -> None: ...

    def record_scope_event(
        self,
        *,
        tenant_id: str,
        project_id: str,
        actor_id: str,
        event_type: str,
        metadata: Mapping[str, object],
        happened_at: datetime,
        proposal_id: str | None = None,
    ) -> None: ...


class AIActionRuntimeStore(Protocol):
    def create(self, record: AIActionStoredProposal) -> None: ...

    def get(
        self, proposal_id: str, *, tenant_id: str, project_id: str
    ) -> AIActionStoredProposal | None: ...

    def list_for_project(
        self, tenant_id: str, project_id: str, *, limit: int = 100
    ) -> tuple[AIActionStoredProposal, ...]: ...

    def transition(
        self,
        proposal: AIActionProposal,
        *,
        expected_status: str,
        next_status: str,
        updated_at: datetime,
        decided_by: str | None = None,
        result: Mapping[str, object] | None = None,
    ) -> bool: ...


def _json_object(value: Mapping[str, object], error_code: str) -> str:
    try:
        encoded = json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise AIActionRuntimeError(error_code) from exc
    return encoded


def _proposal_json(proposal: AIActionProposal) -> str:
    raw = asdict(proposal)
    raw["evidence_refs"] = list(proposal.evidence_refs)
    return _json_object(raw, "AI_ACTION_PROPOSAL_NOT_SERIALIZABLE")


def _decode_proposal(raw_value: object) -> AIActionProposal:
    try:
        raw = json.loads(str(raw_value))
        if not isinstance(raw, dict):
            raise ValueError("proposal must be an object")
        raw["evidence_refs"] = tuple(raw["evidence_refs"])
        proposal = AIActionProposal(**raw)
        proposal.validate()
        return proposal
    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise AIActionRuntimeError("AI_ACTION_STORED_PROPOSAL_INVALID") from exc


class _SqlAIActionRuntimeStore:
    placeholder = "?"

    def __init__(self, connection: object) -> None:
        self.connection = connection
        self.initialize()

    def initialize(self) -> None:
        p = self.placeholder
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS ai_action_proposals (
                proposal_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                project_revision_id TEXT NOT NULL,
                status TEXT NOT NULL,
                proposal_json TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                decided_by TEXT,
                result_json TEXT
            )"""
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_ai_action_scope_status "
            "ON ai_action_proposals (tenant_id, project_id, status)"
        )
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS ai_action_audit_events (
                event_id TEXT PRIMARY KEY,
                happened_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                proposal_id TEXT NOT NULL,
                actor_id TEXT,
                event_json TEXT NOT NULL
            )"""
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_ai_action_audit_scope "
            "ON ai_action_audit_events (tenant_id, project_id, proposal_id, happened_at)"
        )

    def create(self, record: AIActionStoredProposal) -> None:
        proposal = record.proposal
        payload_json = _json_object(record.payload, "AI_ACTION_PAYLOAD_NOT_SERIALIZABLE")
        proposal_json = _proposal_json(proposal)
        p = self.placeholder
        try:
            self.connection.execute(
                "INSERT INTO ai_action_proposals "
                "(proposal_id, tenant_id, project_id, project_revision_id, status, proposal_json, "
                "payload_json, created_at, updated_at, decided_by, result_json) "
                f"VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p})",
                (
                    proposal.proposal_id, proposal.tenant_id, proposal.project_id,
                    proposal.project_revision_id, record.status, proposal_json, payload_json,
                    record.created_at.isoformat(), record.updated_at.isoformat(),
                    record.decided_by, None if record.result is None else _json_object(
                        record.result, "AI_ACTION_RESULT_NOT_SERIALIZABLE"
                    ),
                ),
            )
        except Exception as exc:
            # Keep storage failures distinct from an actual duplicate-ID conflict.
            raise AIActionRuntimeError("AI_ACTION_PROPOSAL_PERSISTENCE_FAILED") from exc
        fresh = self.get(
            proposal.proposal_id, tenant_id=proposal.tenant_id, project_id=proposal.project_id
        )
        if fresh is None or _proposal_json(fresh.proposal) != proposal_json or _json_object(
            fresh.payload, "AI_ACTION_PAYLOAD_NOT_SERIALIZABLE"
        ) != payload_json:
            raise AIActionRuntimeError("AI_ACTION_PROPOSAL_PERSISTENCE_FAILED")

    def get(
        self, proposal_id: str, *, tenant_id: str, project_id: str
    ) -> AIActionStoredProposal | None:
        p = self.placeholder
        row = self.connection.execute(
            "SELECT proposal_json, payload_json, status, created_at, updated_at, decided_by, result_json "
            "FROM ai_action_proposals WHERE proposal_id=" + p + " AND tenant_id=" + p + " AND project_id=" + p,
            (proposal_id, tenant_id, project_id),
        ).fetchone()
        if row is None:
            return None
        try:
            payload = json.loads(str(row[1]))
            result = None if row[6] is None else json.loads(str(row[6]))
            if not isinstance(payload, dict) or (result is not None and not isinstance(result, dict)):
                raise ValueError("payload/result must be objects")
            created_at = datetime.fromisoformat(str(row[3]))
            updated_at = datetime.fromisoformat(str(row[4]))
            if created_at.tzinfo is None or updated_at.tzinfo is None:
                raise ValueError("stored timestamps must be timezone-aware")
            return AIActionStoredProposal(
                proposal=_decode_proposal(row[0]),
                payload=payload,
                status=str(row[2]),
                created_at=created_at,
                updated_at=updated_at,
                decided_by=None if row[5] is None else str(row[5]),
                result=result,
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise AIActionRuntimeError("AI_ACTION_STORED_PROPOSAL_INVALID") from exc

    def list_for_project(
        self, tenant_id: str, project_id: str, *, limit: int = 100
    ) -> tuple[AIActionStoredProposal, ...]:
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise AIActionRuntimeError("AI_ACTION_TENANT_SCOPE_REQUIRED")
        if not isinstance(project_id, str) or not project_id.strip():
            raise AIActionRuntimeError("AI_ACTION_PROJECT_SCOPE_REQUIRED")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
            raise AIActionRuntimeError("AI_ACTION_LIST_LIMIT_INVALID")
        p = self.placeholder
        rows = self.connection.execute(
            "SELECT proposal_id FROM ai_action_proposals "
            "WHERE tenant_id=" + p + " AND project_id=" + p
            + " ORDER BY updated_at DESC, proposal_id DESC LIMIT " + p,
            (tenant_id, project_id, limit),
        ).fetchall()
        records = []
        for row in rows:
            record = self.get(str(row[0]), tenant_id=tenant_id, project_id=project_id)
            if record is not None:
                records.append(record)
        return tuple(records)

    def transition(
        self,
        proposal: AIActionProposal,
        *,
        expected_status: str,
        next_status: str,
        updated_at: datetime,
        decided_by: str | None = None,
        result: Mapping[str, object] | None = None,
    ) -> bool:
        p = self.placeholder
        result_json = None if result is None else _json_object(
            result, "AI_ACTION_RESULT_NOT_SERIALIZABLE"
        )
        cursor = self.connection.execute(
            "UPDATE ai_action_proposals SET status=" + p + ", updated_at=" + p
            + ", decided_by=COALESCE(" + p + ", decided_by), result_json=COALESCE(" + p + ", result_json)"
            + " WHERE proposal_id=" + p + " AND tenant_id=" + p + " AND project_id=" + p
            + " AND project_revision_id=" + p + " AND status=" + p,
            (
                next_status, updated_at.isoformat(), decided_by, result_json,
                proposal.proposal_id, proposal.tenant_id, proposal.project_id,
                proposal.project_revision_id, expected_status,
            ),
        )
        return cursor.rowcount == 1

    def record(self, proposal: AIActionProposal, decision: AIActionDecision) -> None:
        proposal.validate()
        decision.validate()
        self.record_event(
            proposal,
            "decision",
            actor_id=decision.actor_id,
            metadata={"decision": decision.decision, "audit_event": decision.audit_event},
        )

    def record_scope_event(
        self,
        *,
        tenant_id: str,
        project_id: str,
        actor_id: str,
        event_type: str,
        metadata: Mapping[str, object],
        happened_at: datetime,
        proposal_id: str | None = None,
    ) -> None:
        for name, value in (
            ("tenant_id", tenant_id), ("project_id", project_id),
            ("actor_id", actor_id), ("event_type", event_type),
        ):
            if not isinstance(value, str) or not value.strip():
                raise AIActionRuntimeError(f"AI_ACTION_AUDIT_{name.upper()}_REQUIRED")
        if happened_at.tzinfo is None or happened_at.utcoffset() is None:
            raise AIActionRuntimeError("AI_ACTION_AUDIT_TIMESTAMP_MUST_BE_AWARE")
        if proposal_id is not None and (not isinstance(proposal_id, str) or not proposal_id.strip()):
            raise AIActionRuntimeError("AI_ACTION_AUDIT_PROPOSAL_ID_INVALID")
        event_id = str(uuid4())
        metadata_json = _json_object(metadata, "AI_ACTION_AUDIT_METADATA_INVALID")
        event_json = _json_object({
            "scope": {"tenant_id": tenant_id, "project_id": project_id},
            "proposal_id": proposal_id,
            "metadata": json.loads(metadata_json),
        }, "AI_ACTION_AUDIT_EVENT_INVALID")
        p = self.placeholder
        self.connection.execute(
            "INSERT INTO ai_action_audit_events "
            "(event_id, happened_at, event_type, tenant_id, project_id, proposal_id, actor_id, event_json) "
            f"VALUES ({p},{p},{p},{p},{p},{p},{p},{p})",
            (
                event_id, happened_at.isoformat(), event_type, tenant_id,
                project_id, proposal_id or f"request:{event_id}", actor_id, event_json,
            ),
        )

    def record_event(
        self,
        proposal: AIActionProposal,
        event_type: str,
        *,
        actor_id: str | None = None,
        metadata: Mapping[str, object] | None = None,
        happened_at: datetime | None = None,
    ) -> None:
        proposal.validate()
        if not isinstance(event_type, str) or not event_type.strip():
            raise AIActionRuntimeError("AI_ACTION_AUDIT_EVENT_TYPE_REQUIRED")
        when = happened_at or datetime.now(timezone.utc)
        if when.tzinfo is None or when.utcoffset() is None:
            raise AIActionRuntimeError("AI_ACTION_AUDIT_TIMESTAMP_MUST_BE_AWARE")
        metadata_json = _json_object(metadata or {}, "AI_ACTION_AUDIT_METADATA_INVALID")
        event_json = _json_object(
            {"proposal": json.loads(_proposal_json(proposal)), "metadata": json.loads(metadata_json)},
            "AI_ACTION_AUDIT_EVENT_INVALID",
        )
        p = self.placeholder
        self.connection.execute(
            "INSERT INTO ai_action_audit_events "
            "(event_id, happened_at, event_type, tenant_id, project_id, proposal_id, actor_id, event_json) "
            f"VALUES ({p},{p},{p},{p},{p},{p},{p},{p})",
            (
                str(uuid4()), when.isoformat(), event_type, proposal.tenant_id,
                proposal.project_id, proposal.proposal_id, actor_id, event_json,
            ),
        )


class SQLiteAIActionRuntimeStore(_SqlAIActionRuntimeStore):
    """SQLite proposal and audit store; the caller owns commit/rollback."""

    placeholder = "?"

    def __init__(self, connection: sqlite3.Connection) -> None:
        super().__init__(connection)


class PostgresAIActionRuntimeStore(_SqlAIActionRuntimeStore):
    """PostgreSQL proposal and audit store; the caller owns commit/rollback."""

    placeholder = "%s"


class AIActionRuntime:
    """Server-side proposal/approval/execution path with scope, revision, and replay guards."""

    def __init__(
        self,
        *,
        store: AIActionRuntimeStore,
        permission_adapter: AIToolPermissionAdapter,
        audit_sink: AIActionRuntimeAuditSink,
        tools: Iterable[AIActionToolDefinition],
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        definitions: dict[str, AIActionToolDefinition] = {}
        for definition in tools:
            definition.validate()
            if definition.tool_name in definitions:
                raise AIActionRuntimeError("DUPLICATE_AI_ACTION_TOOL")
            definitions[definition.tool_name] = definition
        self.store = store
        self.permission_adapter = permission_adapter
        self.audit_sink = audit_sink
        self.tools = definitions
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def propose(
        self,
        context: AIActionRuntimeContext,
        *,
        tool_name: str,
        payload: Mapping[str, object],
        evidence_refs: tuple[str, ...] = (),
    ) -> AIActionStoredProposal:
        context.validate()
        definition = self.tools.get(tool_name)
        if definition is None:
            raise AIActionRuntimeError("AI_ACTION_TOOL_NOT_REGISTERED")
        try:
            validated_payload = definition.validate_payload(payload)
            if not isinstance(validated_payload, Mapping):
                raise TypeError("payload validator must return a mapping")
            # Validate serializability before creating a record or calling a tool.
            _json_object(validated_payload, "AI_ACTION_TOOL_PAYLOAD_INVALID")
        except (TypeError, ValueError) as exc:
            if isinstance(exc, AIActionRuntimeError):
                raise
            raise AIActionRuntimeError("AI_ACTION_TOOL_PAYLOAD_INVALID") from exc
        proposal = AIActionProposal(
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            proposal_id=str(uuid4()),
            tool_name=definition.tool_name,
            action=definition.action,
            requires_human_approval=definition.requires_human_approval,
            requested_by=context.subject_id,
            evidence_refs=evidence_refs,
            project_revision_id=context.project_revision_id,
            resource_domain=definition.resource_domain,
        )
        proposal.validate()
        self._require_permission(proposal, context.subject_id, actor_id=context.subject_id)
        now = self._now()
        status = "proposed" if proposal.requires_human_approval else "approved"
        record = AIActionStoredProposal(
            proposal=proposal,
            payload=dict(validated_payload),
            status=status,
            created_at=now,
            updated_at=now,
        )
        self.store.create(record)
        self.audit_sink.record_event(
            proposal, "proposal_created", actor_id=context.subject_id,
            metadata={"status": status, "requires_human_approval": proposal.requires_human_approval},
            happened_at=now,
        )
        return record

    def record_request_event(
        self,
        context: AIActionRuntimeContext,
        event_type: str,
        *,
        metadata: Mapping[str, object],
        proposal_id: str | None = None,
    ) -> None:
        """Persist a scoped HTTP-level event that occurs before a proposal can be created."""
        context.validate()
        self.audit_sink.record_scope_event(
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            actor_id=context.subject_id,
            event_type=event_type,
            metadata=metadata,
            happened_at=self._now(),
            proposal_id=proposal_id,
        )

    def list_proposals(
        self, context: AIActionRuntimeContext, *, limit: int = 100
    ) -> tuple[AIActionStoredProposal, ...]:
        """Return recent proposals only within the authenticated tenant/project scope."""
        context.validate()
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
            raise AIActionRuntimeError("AI_ACTION_LIST_LIMIT_INVALID")
        return self.store.list_for_project(
            context.tenant_id, context.project_id, limit=limit
        )

    def get_proposal(
        self, context: AIActionRuntimeContext, proposal_id: str
    ) -> AIActionStoredProposal:
        """Read a proposal within trusted tenant/project scope, including stale proposals."""
        context.validate()
        return self._get_scoped(context, proposal_id)

    def decide(
        self,
        context: AIActionRuntimeContext,
        proposal_id: str,
        *,
        approved: bool,
    ) -> AIActionStoredProposal:
        context.validate()
        if not isinstance(approved, bool):
            raise AIActionRuntimeError("AI_ACTION_APPROVAL_DECISION_INVALID")
        record = self._get_scoped(context, proposal_id)
        self._assert_current_revision(record, context)
        proposal = record.proposal
        if record.status != "proposed" or not proposal.requires_human_approval:
            self.audit_sink.record_event(
                proposal, "decision_replay_or_state_conflict", actor_id=context.subject_id,
                metadata={"current_status": record.status}, happened_at=self._now(),
            )
            raise AIActionRuntimeError("AI_ACTION_PROPOSAL_NOT_PENDING")
        decision_service = AIActionApprovalService(self.permission_adapter, self.audit_sink)
        try:
            decision_service.decide(
                proposal, actor_id=context.subject_id, approved=approved, subject_id=context.subject_id
            )
        except AIActionBoundaryError as exc:
            self.audit_sink.record_event(
                proposal, "decision_denied", actor_id=context.subject_id,
                metadata={"reason_code": str(exc)}, happened_at=self._now(),
            )
            raise AIActionRuntimeError(str(exc)) from exc
        next_status = "approved" if approved else "rejected"
        now = self._now()
        changed = self.store.transition(
            proposal, expected_status="proposed", next_status=next_status,
            updated_at=now, decided_by=context.subject_id,
        )
        if not changed:
            self.audit_sink.record_event(
                proposal, "decision_state_conflict", actor_id=context.subject_id,
                metadata={"attempted_status": next_status}, happened_at=now,
            )
            raise AIActionRuntimeError("AI_ACTION_PROPOSAL_NOT_PENDING")
        self.audit_sink.record_event(
            proposal, "proposal_approved" if approved else "proposal_rejected",
            actor_id=context.subject_id, metadata={"status": next_status}, happened_at=now,
        )
        fresh = self._get_scoped(context, proposal_id)
        if fresh is None:
            raise AIActionRuntimeError("AI_ACTION_PROPOSAL_PERSISTENCE_FAILED")
        return fresh

    def execute(
        self, context: AIActionRuntimeContext, proposal_id: str
    ) -> AIActionStoredProposal:
        context.validate()
        record = self._get_scoped(context, proposal_id)
        self._assert_current_revision(record, context)
        proposal = record.proposal
        definition = self.tools.get(proposal.tool_name)
        if definition is None:
            raise AIActionRuntimeError("AI_ACTION_TOOL_NOT_REGISTERED")
        if record.status != "approved":
            self.audit_sink.record_event(
                proposal, "execution_replay_or_race_blocked", actor_id=context.subject_id,
                metadata={"current_status": record.status}, happened_at=self._now(),
            )
            raise AIActionRuntimeError("AI_ACTION_PROPOSAL_NOT_APPROVED")
        # Re-check the exact grant immediately before claiming the action for execution.
        self._require_permission(proposal, context.subject_id, actor_id=context.subject_id)
        now = self._now()
        if not self.store.transition(
            proposal, expected_status="approved", next_status="executing", updated_at=now,
        ):
            self.audit_sink.record_event(
                proposal, "execution_replay_or_race_blocked", actor_id=context.subject_id,
                metadata={"reason_code": "AI_ACTION_PROPOSAL_NOT_APPROVED"}, happened_at=now,
            )
            raise AIActionRuntimeError("AI_ACTION_PROPOSAL_NOT_APPROVED")
        self.audit_sink.record_event(
            proposal, "execution_started", actor_id=context.subject_id,
            metadata={"expected_revision": proposal.project_revision_id}, happened_at=now,
        )
        try:
            # The tool implementation must pass proposal.project_revision_id as an
            # optimistic-lock precondition to its real application use case and use
            # proposal.proposal_id as its idempotency key.
            result = definition.execute(record.payload, proposal, proposal.proposal_id)
            if not isinstance(result, Mapping):
                raise TypeError("AI action executor must return a mapping")
            _json_object(result, "AI_ACTION_EXECUTOR_RESULT_INVALID")
        except Exception as exc:
            # An executor can fail after its authoritative mutation committed but before
            # returning a result. Treat the outcome as uncertain by default; marking it
            # "failed" would be a false claim and could encourage an unsafe retry.
            uncertain_at = self._now()
            state_persisted = False
            try:
                state_persisted = self.store.transition(
                    proposal, expected_status="executing", next_status="uncertain",
                    updated_at=uncertain_at,
                )
            except Exception:
                # Keep the request fail-closed even if the state store is unavailable.
                # The proposal will remain executing/uncertain and cannot be replayed
                # through the normal approved-only execution path.
                state_persisted = False
            self.audit_sink.record_event(
                proposal, "execution_outcome_uncertain", actor_id=context.subject_id,
                metadata={
                    "failure_type": type(exc).__name__,
                    "uncertain_state_persisted": state_persisted,
                    "automatic_retry_allowed": False,
                },
                happened_at=uncertain_at,
            )
            raise AIActionRuntimeError("AI_ACTION_EXECUTION_OUTCOME_UNCERTAIN") from exc

        completed_at = self._now()
        try:
            persisted = self.store.transition(
                proposal, expected_status="executing", next_status="executed",
                updated_at=completed_at, result=result,
            )
        except Exception as exc:
            self.audit_sink.record_event(
                proposal, "execution_persistence_uncertain", actor_id=context.subject_id,
                metadata={"failure_type": type(exc).__name__}, happened_at=completed_at,
            )
            raise AIActionRuntimeError("AI_ACTION_EXECUTION_RESULT_NOT_PERSISTED") from exc
        if not persisted:
            self.audit_sink.record_event(
                proposal, "execution_persistence_uncertain", actor_id=context.subject_id,
                metadata={"reason_code": "AI_ACTION_EXECUTION_RESULT_NOT_PERSISTED"},
                happened_at=completed_at,
            )
            raise AIActionRuntimeError("AI_ACTION_EXECUTION_RESULT_NOT_PERSISTED")
        self.audit_sink.record_event(
            proposal, "execution_succeeded", actor_id=context.subject_id,
            metadata={"result_keys": sorted(str(key) for key in result.keys())},
            happened_at=completed_at,
        )
        fresh = self._get_scoped(context, proposal_id)
        if fresh is None or fresh.status != "executed":
            raise AIActionRuntimeError("AI_ACTION_EXECUTION_RESULT_NOT_PERSISTED")
        return fresh

    def _get_scoped(
        self, context: AIActionRuntimeContext, proposal_id: str
    ) -> AIActionStoredProposal:
        if not isinstance(proposal_id, str) or not proposal_id.strip():
            raise AIActionRuntimeError("AI_ACTION_PROPOSAL_ID_REQUIRED")
        record = self.store.get(
            proposal_id, tenant_id=context.tenant_id, project_id=context.project_id
        )
        if record is None:
            # Avoid disclosing whether an ID exists in another tenant/project.
            raise AIActionRuntimeError("AI_ACTION_PROPOSAL_NOT_FOUND")
        return record

    def _assert_current_revision(
        self, record: AIActionStoredProposal, context: AIActionRuntimeContext
    ) -> None:
        if record.proposal.project_revision_id != context.project_revision_id:
            self.audit_sink.record_event(
                record.proposal, "stale_revision_blocked", actor_id=context.subject_id,
                metadata={
                    "proposal_revision": record.proposal.project_revision_id,
                    "current_revision": context.project_revision_id,
                }, happened_at=self._now(),
            )
            raise AIActionRuntimeError("AI_ACTION_PROPOSAL_STALE_REVISION")

    def _require_permission(
        self, proposal: AIActionProposal, subject_id: str, *, actor_id: str
    ) -> None:
        try:
            allowed = self.permission_adapter.allowed(proposal, subject_id=subject_id)
        except Exception as exc:
            self.audit_sink.record_event(
                proposal, "permission_check_failed", actor_id=actor_id,
                metadata={"failure_type": type(exc).__name__}, happened_at=self._now(),
            )
            raise AIActionRuntimeError("AI_ACTION_PERMISSION_CHECK_FAILED") from exc
        if not allowed:
            denied = AIActionDecision(
                proposal_id=proposal.proposal_id, decision="denied",
                actor_id=actor_id, audit_event="ai_action_decision",
            )
            denied.validate()
            self.audit_sink.record(proposal, denied)
            self.audit_sink.record_event(
                proposal, "permission_denied", actor_id=actor_id,
                metadata={"reason_code": "AI_TOOL_NOT_PERMITTED"}, happened_at=self._now(),
            )
            raise AIActionRuntimeError("AI_TOOL_NOT_PERMITTED")

    def _now(self) -> datetime:
        value = self.clock()
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise AIActionRuntimeError("AI_ACTION_CLOCK_MUST_BE_TIMEZONE_AWARE")
        return value


__all__ = [
    "AIActionRuntimeError",
    "AIActionRuntimeContext",
    "AIActionToolDefinition",
    "AIActionStoredProposal",
    "AIActionRuntimeStore",
    "SQLiteAIActionRuntimeStore",
    "PostgresAIActionRuntimeStore",
    "AIActionRuntime",
]
