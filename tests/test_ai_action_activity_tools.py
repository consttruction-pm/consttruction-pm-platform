from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
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
    AIActionToolDefinition,
    AIActionRuntime,
    SQLiteAIActionRuntimeStore,
)
from construction_pm.application.authorization import default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.activity_master_repository import SQLiteActivityMasterRepository
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectLifecycleService,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes


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


def test_activity_create_runtime_rejects_split_connection_wiring(tmp_path):
    database_path = tmp_path / "activity-tool-split.sqlite"
    connection = sqlite3.connect(str(database_path))
    other_connection = sqlite3.connect(":memory:")
    try:
        SQLiteActivityMasterRepository(connection)
        mismatched_manager = SQLiteTransactionManager(other_connection)
        with pytest.raises(
            AIActionRuntimeError,
            match="AI_ACTION_ACTIVITY_TOOL_TRANSACTION_CONNECTION_MISMATCH",
        ):
            build_activity_create_runtime(
                activity_master_repository=SQLiteActivityMasterRepository(connection),
                authorization_policy=default_project_policy(),
                permission_adapter=UserConfiguredAIActionPermissionAdapter(lambda: ()),
                transaction_manager=mismatched_manager,
            )
    finally:
        connection.close()
        other_connection.close()



def test_atomic_executor_error_rolls_back_partial_sql_and_blocks_replay(tmp_path):
    database_path = tmp_path / "activity-tool-uncertain.sqlite"
    connection = sqlite3.connect(str(database_path))
    manager = SQLiteTransactionManager(connection)
    connection.execute("CREATE TABLE action_probe (probe_value TEXT NOT NULL)")
    connection.commit()
    store = SQLiteAIActionRuntimeStore(connection)
    grants = [
        AIActionPermissionGrant(
            subject_id="user-1", tenant_id="tenant-1", project_id="project-1",
            project_revision_id="12", resource_domain="activities",
            operation="create", tool_name="probe.create",
        )
    ]
    calls = []

    def validate_payload(payload):
        if set(payload) != {"value"} or not isinstance(payload.get("value"), str):
            raise ValueError("invalid probe")
        return {"value": payload["value"]}

    def execute(payload, proposal, idempotency_key, context):
        calls.append(proposal.proposal_id)
        connection.execute("INSERT INTO action_probe (probe_value) VALUES (?)", (payload["value"],))
        raise RuntimeError("simulated lost tool response")

    runtime = AIActionRuntime(
        store=store,
        permission_adapter=UserConfiguredAIActionPermissionAdapter(lambda: tuple(grants)),
        audit_sink=store,
        tools=[AIActionToolDefinition(
            tool_name="probe.create",
            action="create",
            resource_domain="activities",
            requires_human_approval=True,
            validate_payload=validate_payload,
            execute=execute,
        )],
        transaction_manager=manager,
    )
    context = AIActionRuntimeContext(
        subject_id="user-1", tenant_id="tenant-1", project_id="project-1",
        project_revision_id="12", roles=frozenset({"project_admin"}),
    )
    try:
        proposal = runtime.propose(context, tool_name="probe.create", payload={"value": "one"})
        runtime.decide(context, proposal.proposal.proposal_id, approved=True)

        with pytest.raises(AIActionRuntimeError, match="AI_ACTION_EXECUTION_OUTCOME_UNCERTAIN"):
            runtime.execute(context, proposal.proposal.proposal_id)

        persisted = store.get(
            proposal.proposal.proposal_id, tenant_id="tenant-1", project_id="project-1"
        )
        assert persisted is not None
        assert persisted.status == "uncertain"
        assert connection.execute("SELECT COUNT(*) FROM action_probe").fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM ai_action_audit_events "
            "WHERE proposal_id=? AND event_type='execution_outcome_uncertain'",
            (proposal.proposal.proposal_id,),
        ).fetchone()[0] == 1

        with pytest.raises(AIActionRuntimeError, match="AI_ACTION_PROPOSAL_NOT_APPROVED"):
            runtime.execute(context, proposal.proposal.proposal_id)
        assert calls == [proposal.proposal.proposal_id]
        assert connection.execute("SELECT COUNT(*) FROM action_probe").fetchone()[0] == 0
    finally:
        connection.close()



class _RouteSessions:
    def __init__(self, session):
        self.session = session

    def get(self, session_id):
        return self.session if session_id == self.session.session_id else None


class _RouteProjects:
    def list_for_user(self, tenant_id, user_id):
        if tenant_id != "tenant-1" or user_id != "user-1":
            return ()
        return (ProjectSummary("project-1", tenant_id, "Route test project", 12),)

    def get_for_user(self, tenant_id, project_id, user_id):
        if tenant_id != "tenant-1" or project_id != "project-1" or user_id != "user-1":
            return None
        return ProjectSummary("project-1", tenant_id, "Route test project", 12)

    def create_for_user(self, tenant_id, user_id, project_id, name):
        return ProjectSummary(project_id, tenant_id, name, 0)


def test_authenticated_http_route_executes_real_activity_create_and_fresh_readback(tmp_path):
    database_path = tmp_path / "activity-route-e2e.sqlite"
    connection = sqlite3.connect(str(database_path))
    manager = SQLiteTransactionManager(connection)
    activity_repository = SQLiteActivityMasterRepository(connection)
    now = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "session-1", "user-1", "tenant-1", frozenset({"project_admin"}),
        now + timedelta(hours=2),
    )
    lifecycle_api = ProjectLifecycleAPI(
        ProjectLifecycleService(
            _RouteSessions(session), _RouteProjects(), default_project_policy()
        )
    )
    grant = AIActionPermissionGrant(
        subject_id="user-1", tenant_id="tenant-1", project_id="project-1",
        project_revision_id="12", resource_domain="activities",
        operation="create", tool_name="activity.create",
    )
    runtime = build_activity_create_runtime(
        activity_master_repository=activity_repository,
        authorization_policy=default_project_policy(),
        permission_adapter=UserConfiguredAIActionPermissionAdapter(lambda: (grant,)),
        transaction_manager=manager,
        clock=lambda: now,
    )

    class FixedClock:
        def now(self):
            return now

    routes = ProjectLifecycleHttpRoutes(
        lifecycle_api, clock=FixedClock(), ai_action_runtime=runtime
    )

    def request(path, payload):
        return routes.handle(
            "POST", path, cookies={"cp_session": "session-1"},
            body=json.dumps(payload).encode("utf-8"),
        )

    try:
        status, _, body = request("/api/projects/project-1/ai/actions/proposals", {
            "expected_revision": 12,
            "tool_name": "activity.create",
            "payload": {
                "activity_id": "A-HTTP-1",
                "name": "Blinding concrete",
                "duration_value": "1.5",
                "duration_unit": "working-day",
            },
            "tenant_id": "client-spoofed-tenant",
            "requested_by": "client-spoofed-user",
            "requires_human_approval": False,
        })
        assert status == 201
        proposal_dto = json.loads(body)["proposal"]
        proposal_id = proposal_dto["proposal_id"]
        assert proposal_dto["requires_human_approval"] is True

        status, _, body = request(
            f"/api/projects/project-1/ai/actions/proposals/{proposal_id}/decision",
            {"expected_revision": 12, "approved": True},
        )
        assert status == 200
        assert json.loads(body)["status"] == "approved"

        status, _, body = request(
            f"/api/projects/project-1/ai/actions/proposals/{proposal_id}/execute",
            {"expected_revision": 12},
        )
        assert status == 200
        outcome = json.loads(body)
        assert outcome["status"] == "executed"
        assert outcome["result"]["activity"]["activity_id"] == "A-HTTP-1"

        fresh = sqlite3.connect(str(database_path))
        try:
            fresh_repo = SQLiteActivityMasterRepository(fresh)
            persisted = fresh_repo.get(BackendScope("tenant-1", "project-1", 12), "A-HTTP-1")
            assert persisted is not None
            assert persisted.name == "Blinding concrete"
            fresh_store = SQLiteAIActionRuntimeStore(fresh)
            final_proposal = fresh_store.get(
                proposal_id, tenant_id="tenant-1", project_id="project-1"
            )
            assert final_proposal is not None
            assert final_proposal.status == "executed"
            assert final_proposal.proposal.requested_by == "user-1"
        finally:
            fresh.close()
    finally:
        connection.close()
