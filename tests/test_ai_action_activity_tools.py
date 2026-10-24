from __future__ import annotations

import json
import sqlite3
from decimal import Decimal

import pytest

from construction_pm.ai_action_activity_tools import build_activity_create_runtime
from construction_pm.ai_action_boundary import (
    AIActionPermissionGrant,
    UserConfiguredAIActionPermissionAdapter,
)
from construction_pm.ai_action_runtime import (
    AIActionRuntimeContext,
    AIActionRuntimeError,
)
from construction_pm.application.authorization import default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.activity_master_repository import SQLiteActivityMasterRepository


def build_runtime(database_path):
    connection = sqlite3.connect(str(database_path))
    transaction_manager = SQLiteTransactionManager(connection)
    activity_repository = SQLiteActivityMasterRepository(connection)
    grants = [
        AIActionPermissionGrant(
            subject_id="user-1",
            tenant_id="tenant-1",
            project_id="project-1",
            project_revision_id="12",
            resource_domain="activities",
            operation="create",
            tool_name="activity.create",
        )
    ]
    runtime = build_activity_create_runtime(
        activity_master_repository=activity_repository,
        authorization_policy=default_project_policy(),
        permission_adapter=UserConfiguredAIActionPermissionAdapter(lambda: tuple(grants)),
        transaction_manager=transaction_manager,
    )
    runtime_store = runtime.store
    context = AIActionRuntimeContext(
        subject_id="user-1",
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision_id="12",
        roles=frozenset({"project_admin"}),
    )
    return connection, transaction_manager, activity_repository, runtime_store, runtime, context, grants


def activity_payload(**overrides):
    result = {
        "activity_id": "A-100",
        "name": "Excavation",
        "duration_value": "3.5",
        "duration_unit": "working-day",
    }
    result.update(overrides)
    return result


def test_activity_create_tool_uses_authenticated_api_and_shared_transaction(tmp_path):
    database_path = tmp_path / "activity-tool.sqlite"
    connection, manager, repo, store, runtime, context, _ = build_runtime(database_path)
    try:
        proposed = runtime.propose(
            context, tool_name="activity.create", payload=activity_payload(),
            evidence_refs=("intake-row-4",),
        )
        assert proposed.status == "proposed"
        assert proposed.proposal.requested_by == context.subject_id

        approved = runtime.decide(context, proposed.proposal.proposal_id, approved=True)
        assert approved.status == "approved"

        executed = runtime.execute(context, proposed.proposal.proposal_id)
        assert executed.status == "executed"
        assert executed.result is not None
        assert executed.result["contract_version"] == "p6-activity-master-api.v1"
        assert executed.result["activity"]["activity_id"] == "A-100"
        assert executed.result["activity"]["duration_value"] == "3.5"

        # A second physical connection proves both the project mutation and the
        # execution result were committed, not merely visible in the writer's cache.
        fresh_connection = sqlite3.connect(str(database_path))
        try:
            fresh_repo = SQLiteActivityMasterRepository(fresh_connection)
            stored = fresh_repo.get(BackendScope("tenant-1", "project-1", 12), "A-100")
            assert stored is not None
            assert stored.name == "Excavation"
            assert stored.duration_value == Decimal("3.5")
            fresh_store = SQLiteAIActionRuntimeStore(fresh_connection)
            fresh_proposal = fresh_store.get(
                proposed.proposal.proposal_id,
                tenant_id="tenant-1",
                project_id="project-1",
            )
            assert fresh_proposal is not None
            assert fresh_proposal.status == "executed"
            assert fresh_proposal.result == executed.result
            row = fresh_connection.execute(
                "SELECT fingerprint, result_json FROM ai_action_tool_idempotency "
                "WHERE tenant_id=? AND project_id=? AND tool_name=? AND idempotency_key=?",
                ("tenant-1", "project-1", "activity.create", proposed.proposal.proposal_id),
            ).fetchone()
            assert row is not None
            assert json.loads(row[1]) == executed.result
            assert fresh_connection.execute(
                "SELECT COUNT(*) FROM ai_action_audit_events WHERE proposal_id=?",
                (proposed.proposal.proposal_id,),
            ).fetchone()[0] >= 5
        finally:
            fresh_connection.close()
    finally:
        connection.close()


def test_activity_create_tool_denies_revoked_grant_before_mutation(tmp_path):
    database_path = tmp_path / "activity-tool-deny.sqlite"
    connection, _, repo, store, runtime, context, grants = build_runtime(database_path)
    try:
        proposed = runtime.propose(context, tool_name="activity.create", payload=activity_payload())
        runtime.decide(context, proposed.proposal.proposal_id, approved=True)
        grants.clear()

        with pytest.raises(AIActionRuntimeError, match="AI_TOOL_NOT_PERMITTED"):
            runtime.execute(context, proposed.proposal.proposal_id)

        assert repo.get(BackendScope("tenant-1", "project-1", 12), "A-100") is None
        stored = store.get(
            proposed.proposal.proposal_id, tenant_id="tenant-1", project_id="project-1"
        )
        assert stored is not None
        assert stored.status == "approved"
        assert connection.execute(
            "SELECT COUNT(*) FROM ai_action_audit_events "
            "WHERE proposal_id=? AND event_type='permission_denied'",
            (proposed.proposal.proposal_id,),
        ).fetchone()[0] == 1
    finally:
        connection.close()


def test_activity_create_payload_rejects_invalid_duration_and_unknown_fields(tmp_path):
    database_path = tmp_path / "activity-tool-validation.sqlite"
    connection, _, _, _, runtime, context, _ = build_runtime(database_path)
    try:
        with pytest.raises(AIActionRuntimeError, match="AI_ACTION_TOOL_PAYLOAD_INVALID"):
            runtime.propose(
                context, tool_name="activity.create",
                payload=activity_payload(duration_value="-1"),
            )
        with pytest.raises(AIActionRuntimeError, match="AI_ACTION_TOOL_PAYLOAD_INVALID"):
            runtime.propose(
                context, tool_name="activity.create",
                payload=activity_payload(tenant_id="attacker-tenant"),
            )
        assert connection.execute("SELECT COUNT(*) FROM activity_master").fetchone()[0] == 0
    finally:
        connection.close()


def test_activity_create_tool_rejects_split_connection_wiring(tmp_path):
    database_path = tmp_path / "activity-tool-split.sqlite"
    connection = sqlite3.connect(str(database_path))
    other_connection = sqlite3.connect(":memory:")
    try:
        manager = SQLiteTransactionManager(connection)
        repo = SQLiteActivityMasterRepository(connection)
        api = P6ActivityMasterAPI(repo, default_project_policy())
        idem = SQLiteAIActionExecutionIdempotencyStore(other_connection)
        with pytest.raises(
            AIActionRuntimeError,
            match="AI_ACTION_ACTIVITY_TOOL_TRANSACTION_CONNECTION_MISMATCH",
        ):
            build_activity_create_tool(
                activity_api=api,
                idempotency_store=idem,
                transaction_manager=manager,
            )
    finally:
        connection.close()
        other_connection.close()
