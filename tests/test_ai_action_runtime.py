from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

import pytest

from construction_pm.ai_action_boundary import (
    AIActionPermissionGrant,
    UserConfiguredAIActionPermissionAdapter,
)
from construction_pm.ai_action_runtime import (
    AIActionExecutionRejected,
    AIActionRuntime,
    AIActionRuntimeContext,
    AIActionRuntimeError,
    AIActionToolDefinition,
    SQLiteAIActionRuntimeStore,
)
from construction_pm.ai_action_execution_verification_contract import (
    AI_ACTION_EXECUTION_VERIFICATION_VERSION,
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

    def run(payload, proposal, idempotency_key, context):
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


def verification_payload(**overrides):
    payload = {
        "contract_version": AI_ACTION_EXECUTION_VERIFICATION_VERSION,
        "status": "UNAVAILABLE",
        "reason_code": "CALCULATION_TIMEZONE_REQUIRED",
        "activity": None,
        "project_finish": None,
        "calculation_run_identity": None,
        "snapshot": None,
        "query_id": None,
    }
    payload.update(overrides)
    return payload


def computed_verification(**overrides):
    payload = {
        "contract_version": AI_ACTION_EXECUTION_VERIFICATION_VERSION,
        "status": "COMPUTED",
        "reason_code": None,
        "activity": {
            "activity_id": "activity-1",
            "start": "2026-10-19",
            "finish": "2026-10-20",
            "duration": 2,
            "duration_unit": "working-day",
            "critical": True,
        },
        "project_finish": "2026-10-20",
        "calculation_run_identity": "run-identity-1",
        "snapshot": {
            "snapshot_id": "SNAP-1",
            "snapshot_hash": "a" * 64,
            "calculation_identity": "b" * 64,
        },
        "query_id": "ai-action-execution:proposal-1",
    }
    payload.update(overrides)
    return payload


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
    stale_record = runtime.store.get(
        record.proposal.proposal_id, tenant_id="tenant-1", project_id="project-1"
    )
    assert stale_record is not None
    assert stale_record.status == "stale"
    with pytest.raises(AIActionRuntimeError, match="AI_ACTION_PROPOSAL_NOT_PENDING"):
        runtime.decide(context, record.proposal.proposal_id, approved=True)
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


def test_execution_failure_is_marked_uncertain_and_cannot_be_replayed():
    side_effects = []

    def fail_after_possible_commit(payload, proposal, idempotency_key, context):
        # Simulate an executor that has applied a side effect but fails before returning
        # the result to the orchestration layer.
        side_effects.append((proposal.proposal_id, dict(payload)))
        raise RuntimeError("executor response lost after a possible commit")

    conn, _, runtime, context, _, _ = setup_runtime(executor=fail_after_possible_commit)
    record = runtime.propose(context, tool_name="activity.create", payload={"name": "Excavation"})
    runtime.decide(context, record.proposal.proposal_id, approved=True)

    with pytest.raises(AIActionRuntimeError, match="AI_ACTION_EXECUTION_OUTCOME_UNCERTAIN"):
        runtime.execute(context, record.proposal.proposal_id)
    state = conn.execute(
        "SELECT status FROM ai_action_proposals WHERE proposal_id=?",
        (record.proposal.proposal_id,),
    ).fetchone()
    assert state[0] == "uncertain"
    assert conn.execute(
        "SELECT COUNT(*) FROM ai_action_audit_events WHERE event_type='execution_outcome_uncertain'"
    ).fetchone()[0] == 1
    assert len(side_effects) == 1

    # Normal execution only accepts "approved"; an uncertain outcome is never replayed
    # without an explicit reconciliation workflow.
    with pytest.raises(AIActionRuntimeError, match="AI_ACTION_PROPOSAL_NOT_APPROVED"):
        runtime.execute(context, record.proposal.proposal_id)
    assert len(side_effects) == 1


def test_known_execution_rejection_is_blocked_not_uncertain():
    def reject(payload, proposal, idempotency_key, context):
        raise AIActionExecutionRejected("AI_TEST_PRECONDITION_FAILED")

    conn, store, runtime, context, _, _ = setup_runtime(executor=reject)
    record = runtime.propose(context, tool_name="activity.create", payload={"name": "Excavation"})
    runtime.decide(context, record.proposal.proposal_id, approved=True)
    with pytest.raises(AIActionRuntimeError, match="AI_TEST_PRECONDITION_FAILED"):
        runtime.execute(context, record.proposal.proposal_id)
    stored = store.get(
        record.proposal.proposal_id, tenant_id="tenant-1", project_id="project-1"
    )
    assert stored is not None
    assert stored.status == "blocked"
    assert conn.execute(
        "SELECT COUNT(*) FROM ai_action_audit_events "
        "WHERE proposal_id=? AND event_type='execution_precondition_failed'",
        (record.proposal.proposal_id,),
    ).fetchone()[0] == 1
    assert conn.execute(
        "SELECT COUNT(*) FROM ai_action_audit_events "
        "WHERE proposal_id=? AND event_type='execution_outcome_uncertain'",
        (record.proposal.proposal_id,),
    ).fetchone()[0] == 0


def test_execution_verification_persists_audits_and_round_trips():
    result = {"activity": {"activity_id": "activity-1", "name": "Excavation"}}

    def succeed(payload, proposal, idempotency_key, context):
        return result

    conn, store, runtime, context, _, _ = setup_runtime(executor=succeed)
    record = runtime.propose(context, tool_name="activity.create", payload={"name": "Excavation"})
    runtime.decide(context, record.proposal.proposal_id, approved=True)
    runtime.execute(context, record.proposal.proposal_id)
    expected = computed_verification(query_id=f"ai-action-execution:{record.proposal.proposal_id}")

    stored = runtime.record_execution_verification(
        context, record.proposal.proposal_id, expected
    )
    assert stored.status == "executed"
    assert stored.execution_verification == expected
    fresh = store.get(
        record.proposal.proposal_id, tenant_id="tenant-1", project_id="project-1"
    )
    assert fresh is not None
    assert fresh.execution_verification == expected
    events = conn.execute(
        "SELECT event_json FROM ai_action_audit_events "
        "WHERE proposal_id=? AND event_type='execution_verification_recorded'",
        (record.proposal.proposal_id,),
    ).fetchall()
    assert len(events) == 1
    metadata = json.loads(events[0][0])["metadata"]
    assert metadata["status"] == "COMPUTED"
    assert metadata["snapshot_id"] == "SNAP-1"
    assert metadata["previous_status"] is None


def test_execution_verification_rejects_cross_activity_result_mismatch():
    result = {"activity": {"activity_id": "activity-1"}}

    def succeed(payload, proposal, idempotency_key, context):
        return result

    _, store, runtime, context, _, _ = setup_runtime(executor=succeed)
    record = runtime.propose(context, tool_name="activity.create", payload={"name": "Excavation"})
    runtime.decide(context, record.proposal.proposal_id, approved=True)
    runtime.execute(context, record.proposal.proposal_id)
    mismatched = computed_verification()
    mismatched["activity"] = dict(mismatched["activity"], activity_id="activity-other")
    with pytest.raises(AIActionRuntimeError, match="AI_ACTION_VERIFICATION_RESULT_MISMATCH"):
        runtime.record_execution_verification(
            context, record.proposal.proposal_id, mismatched
        )
    stored = store.get(
        record.proposal.proposal_id, tenant_id="tenant-1", project_id="project-1"
    )
    assert stored is not None
    assert stored.execution_verification is None


def test_stored_verification_is_isolated_by_proposal_revision_and_must_be_valid():
    result = {"activity": {"activity_id": "activity-1"}}

    def succeed(payload, proposal, idempotency_key, context):
        return result

    conn, store, runtime, context, _, _ = setup_runtime(executor=succeed)
    record = runtime.propose(context, tool_name="activity.create", payload={"name": "Excavation"})
    runtime.decide(context, record.proposal.proposal_id, approved=True)
    runtime.execute(context, record.proposal.proposal_id)
    payload = verification_payload()
    runtime.record_execution_verification(context, record.proposal.proposal_id, payload)
    conn.execute(
        "UPDATE ai_action_execution_verifications SET project_revision_id='99' "
        "WHERE proposal_id=?",
        (record.proposal.proposal_id,),
    )
    hidden = store.get(
        record.proposal.proposal_id, tenant_id="tenant-1", project_id="project-1"
    )
    assert hidden is not None
    assert hidden.execution_verification is None

    conn.execute(
        "UPDATE ai_action_execution_verifications SET project_revision_id='12', "
        "verification_json='{\"contract_version\":\"ai-action-execution-verification.v1\"}' "
        "WHERE proposal_id=?",
        (record.proposal.proposal_id,),
    )
    with pytest.raises(AIActionRuntimeError, match="AI_ACTION_STORED_VERIFICATION_INVALID"):
        store.get(
            record.proposal.proposal_id, tenant_id="tenant-1", project_id="project-1"
        )


def test_verification_overwrite_audits_previous_status_and_reads_latest():
    result = {"activity": {"activity_id": "activity-1"}}

    def succeed(payload, proposal, idempotency_key, context):
        return result

    conn, store, runtime, context, _, _ = setup_runtime(executor=succeed)
    record = runtime.propose(context, tool_name="activity.create", payload={"name": "Excavation"})
    runtime.decide(context, record.proposal.proposal_id, approved=True)
    runtime.execute(context, record.proposal.proposal_id)
    runtime.record_execution_verification(
        context, record.proposal.proposal_id, verification_payload()
    )
    updated = verification_payload(
        status="FAILED", reason_code="SCHEDULE_VERIFICATION_FAILED"
    )
    stored = runtime.record_execution_verification(
        context, record.proposal.proposal_id, updated
    )
    assert stored.execution_verification == updated
    fresh = store.get(
        record.proposal.proposal_id, tenant_id="tenant-1", project_id="project-1"
    )
    assert fresh is not None
    assert fresh.execution_verification == updated
    events = conn.execute(
        "SELECT event_json FROM ai_action_audit_events "
        "WHERE proposal_id=? AND event_type='execution_verification_recorded' "
        "ORDER BY rowid",
        (record.proposal.proposal_id,),
    ).fetchall()
    assert len(events) == 2
    second = json.loads(events[1][0])["metadata"]
    assert second["status"] == "FAILED"
    assert second["previous_status"] == "UNAVAILABLE"
    assert conn.execute(
        "SELECT COUNT(*) FROM ai_action_execution_verifications WHERE proposal_id=?",
        (record.proposal.proposal_id,),
    ).fetchone()[0] == 1


def test_store_rejects_malformed_verification_before_writing():
    result = {"activity": {"activity_id": "activity-1"}}

    def succeed(payload, proposal, idempotency_key, context):
        return result

    _, store, runtime, context, _, _ = setup_runtime(executor=succeed)
    record = runtime.propose(context, tool_name="activity.create", payload={"name": "Excavation"})
    runtime.decide(context, record.proposal.proposal_id, approved=True)
    executed = runtime.execute(context, record.proposal.proposal_id)
    with pytest.raises(AIActionRuntimeError, match="AI_ACTION_VERIFICATION_INVALID"):
        store.save_execution_verification(
            executed.proposal,
            verification={"contract_version": AI_ACTION_EXECUTION_VERIFICATION_VERSION},
            recorded_at=datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc),
        )


def test_verification_survives_reopen_and_stays_inside_tenant_scope(tmp_path):
    database_path = tmp_path / "verification-restart.sqlite"
    connection = sqlite3.connect(str(database_path))
    store = SQLiteAIActionRuntimeStore(connection)
    grants = [grant()]

    def run(payload, proposal, idempotency_key, context):
        return {"activity": {"activity_id": "activity-1"}}

    runtime = AIActionRuntime(
        store=store,
        permission_adapter=UserConfiguredAIActionPermissionAdapter(lambda: tuple(grants)),
        audit_sink=store,
        tools=[tool(run)],
        clock=lambda: datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc),
    )
    context = AIActionRuntimeContext(
        subject_id="user-1",
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision_id="12",
    )
    record = runtime.propose(context, tool_name="activity.create", payload={"name": "Excavation"})
    runtime.decide(context, record.proposal.proposal_id, approved=True)
    runtime.execute(context, record.proposal.proposal_id)
    expected = verification_payload()
    runtime.record_execution_verification(context, record.proposal.proposal_id, expected)
    # The production composition owns the transaction boundary; commit simulates a
    # completed request before the process (and connection) is replaced.
    connection.commit()
    connection.close()

    reopened = sqlite3.connect(str(database_path))
    try:
        fresh_store = SQLiteAIActionRuntimeStore(reopened)
        fresh = fresh_store.get(
            record.proposal.proposal_id, tenant_id="tenant-1", project_id="project-1"
        )
        assert fresh is not None
        assert fresh.status == "executed"
        assert fresh.execution_verification == expected
        # A different tenant/project cannot read the same proposal or its verification.
        assert fresh_store.get(
            record.proposal.proposal_id, tenant_id="tenant-other", project_id="project-1"
        ) is None
        assert fresh_store.get(
            record.proposal.proposal_id, tenant_id="tenant-1", project_id="project-other"
        ) is None
        assert fresh_store.list_for_project("tenant-other", "project-1") == ()
    finally:
        reopened.close()
