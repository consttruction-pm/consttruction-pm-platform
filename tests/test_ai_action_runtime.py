from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from construction_pm.ai_action_boundary import (
    AIActionPermissionGrant,
    UserConfiguredAIActionPermissionAdapter,
)
from construction_pm.ai_action_runtime import (
    AIActionRuntime,
    AIActionRuntimeContext,
    AIActionRuntimeError,
    AIActionToolDefinition,
    SQLiteAIActionRuntimeStore,
)


def grant() -> AIActionPermissionGrant:
    return AIActionPermissionGrant(
        subject_id="user-1",
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision_id="12",
        resource_domain="activities",
        operation="create",
        tool_name="activity.create",
    )


def tool(executor):
    def validate_payload(payload):
        if set(payload) != {"name"} or not isinstance(payload.get("name"), str) or not payload["name"].strip():
            raise ValueError("name is required")
        return {"name": payload["name"].strip()}

    return AIActionToolDefinition(
        tool_name="activity.create",
        action="create",
        resource_domain="activities",
        requires_human_approval=True,
        validate_payload=validate_payload,
        execute=executor,
    )


def setup_runtime(*, grants=None, executor=None):
    conn = sqlite3.connect(":memory:")
    store = SQLiteAIActionRuntimeStore(conn)
    current_grants = list([grant()] if grants is None else grants)
    calls = []

    def run(payload, proposal, idempotency_key):
        calls.append((dict(payload), proposal.project_revision_id, idempotency_key))
        return {"activity_id": "activity-1", "name": payload["name"]}

    runtime = AIActionRuntime(
        store=store,
        permission_adapter=UserConfiguredAIActionPermissionAdapter(lambda: tuple(current_grants)),
        audit_sink=store,
        tools=[tool(executor or run)],
        clock=lambda: datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc),
    )
    context = AIActionRuntimeContext(
        subject_id="user-1",
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision_id="12",
    )
    return conn, store, runtime, context, current_grants, calls


def test_proposal_is_persisted_and_server_owns_action_policy():
    conn, store, runtime, context, _, _ = setup_runtime()
    record = runtime.propose(context, tool_name="activity.create", payload={"name": "  Excavation  "})
    conn.commit()

    assert record.status == "proposed"
    assert record.proposal.requires_human_approval is True
    assert record.proposal.requested_by == "user-1"
    assert record.payload == {"name": "Excavation"}
    fresh = store.get(record.proposal.proposal_id, tenant_id="tenant-1", project_id="project-1")
    assert fresh is not None
    assert fresh.proposal.proposal_id == record.proposal.proposal_id
    events = conn.execute("SELECT event_type FROM ai_action_audit_events").fetchall()
    assert [event[0] for event in events] == ["proposal_created"]


def test_proposal_rejects_unregistered_tool_and_invalid_payload():
    _, _, runtime, context, _, _ = setup_runtime()
    with pytest.raises(AIActionRuntimeError, match="AI_ACTION_TOOL_NOT_REGISTERED"):
        runtime.propose(context, tool_name="project.delete", payload={})
    with pytest.raises(AIActionRuntimeError, match="AI_ACTION_TOOL_PAYLOAD_INVALID"):
        runtime.propose(context, tool_name="activity.create", payload={"name": "", "extra": "no"})


def test_approval_then_execution_runs_tool_once_and_persists_result():
    conn, store, runtime, context, _, calls = setup_runtime()
    record = runtime.propose(context, tool_name="activity.create", payload={"name": "Excavation"})
    approved = runtime.decide(context, record.proposal.proposal_id, approved=True)
    assert approved.status == "approved"

    executed = runtime.execute(context, record.proposal.proposal_id)
    conn.commit()
    assert executed.status == "executed"
    assert executed.result == {"activity_id": "activity-1", "name": "Excavation"}
    assert len(calls) == 1
    assert calls[0][2] == record.proposal.proposal_id
    events = conn.execute("SELECT event_type FROM ai_action_audit_events ORDER BY rowid").fetchall()
    assert [event[0] for event in events] == [
        "proposal_created", "decision", "proposal_approved", "execution_started", "execution_succeeded"
    ]


def test_execution_rechecks_grant_revocation_before_calling_tool():
    conn, _, runtime, context, current_grants, calls = setup_runtime()
    record = runtime.propose(context, tool_name="activity.create", payload={"name": "Excavation"})
    runtime.decide(context, record.proposal.proposal_id, approved=True)
    current_grants.clear()

    with pytest.raises(AIActionRuntimeError, match="AI_TOOL_NOT_PERMITTED"):
        runtime.execute(context, record.proposal.proposal_id)
    assert calls == []
    assert conn.execute(
        "SELECT COUNT(*) FROM ai_action_audit_events WHERE event_type='permission_denied'"
    ).fetchone()[0] == 1


def test_stale_revision_is_denied_before_approval_or_execution():
    _, _, runtime, context, _, calls = setup_runtime()
    record = runtime.propose(context, tool_name="activity.create", payload={"name": "Excavation"})
    stale_context = AIActionRuntimeContext(
        subject_id=context.subject_id,
        tenant_id=context.tenant_id,
        project_id=context.project_id,
        project_revision_id="13",
    )
    with pytest.raises(AIActionRuntimeError, match="AI_ACTION_PROPOSAL_STALE_REVISION"):
        runtime.decide(stale_context, record.proposal.proposal_id, approved=True)
    assert calls == []


def test_proposal_is_not_discoverable_across_project_or_tenant_scope():
    _, _, runtime, context, _, _ = setup_runtime()
    record = runtime.propose(context, tool_name="activity.create", payload={"name": "Excavation"})
    other_scope = AIActionRuntimeContext(
        subject_id="user-2",
        tenant_id="tenant-other",
        project_id="project-other",
        project_revision_id="12",
    )
    with pytest.raises(AIActionRuntimeError, match="AI_ACTION_PROPOSAL_NOT_FOUND"):
        runtime.decide(other_scope, record.proposal.proposal_id, approved=True)


def test_execution_failure_is_recorded_and_cannot_be_replayed():
    def fail(payload, proposal, idempotency_key):
        raise RuntimeError("do not expose implementation detail")

    conn, _, runtime, context, _, _ = setup_runtime(executor=fail)
    record = runtime.propose(context, tool_name="activity.create", payload={"name": "Excavation"})
    runtime.decide(context, record.proposal.proposal_id, approved=True)

    with pytest.raises(AIActionRuntimeError, match="AI_ACTION_EXECUTION_FAILED"):
        runtime.execute(context, record.proposal.proposal_id)
    failed = conn.execute(
        "SELECT status FROM ai_action_proposals WHERE proposal_id=?",
        (record.proposal.proposal_id,),
    ).fetchone()
    assert failed[0] == "failed"
    assert conn.execute(
        "SELECT COUNT(*) FROM ai_action_audit_events WHERE event_type='execution_failed'"
    ).fetchone()[0] == 1
