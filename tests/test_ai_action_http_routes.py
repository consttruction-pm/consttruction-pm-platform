from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from construction_pm.ai_action_boundary import AIActionPermissionGrant, UserConfiguredAIActionPermissionAdapter
from construction_pm.ai_action_runtime import (
    AIActionRuntime,
    AIActionToolDefinition,
    SQLiteAIActionRuntimeStore,
)
from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectLifecycleService,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes


class Sessions:
    def __init__(self, session):
        self.session = session

    def get(self, session_id):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def list_for_user(self, tenant_id, user_id):
        return (ProjectSummary("p1", tenant_id, "Project One", 2),)

    def get_for_user(self, tenant_id, project_id, user_id):
        if tenant_id != "t1" or user_id != "u1" or project_id != "p1":
            return None
        return ProjectSummary("p1", tenant_id, "Project One", 2)

    def create_for_user(self, tenant_id, user_id, project_id, name):
        return ProjectSummary(project_id, tenant_id, name, 0)


def build_routes(*, runtime_enabled=True):
    now = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
    session = AuthenticatedSession("session-1", "u1", "t1", frozenset({"project_admin"}), now + timedelta(hours=1))
    api = ProjectLifecycleAPI(ProjectLifecycleService(Sessions(session), Projects(), default_project_policy()))
    conn = sqlite3.connect(":memory:")
    store = SQLiteAIActionRuntimeStore(conn)
    executed = []

    grant = AIActionPermissionGrant(
        subject_id="u1", tenant_id="t1", project_id="p1",
        project_revision_id="2", resource_domain="activities",
        operation="create", tool_name="activity.create",
    )

    def validate_payload(payload):
        if set(payload) != {"name"} or not isinstance(payload.get("name"), str) or not payload["name"].strip():
            raise ValueError("invalid activity payload")
        return {"name": payload["name"].strip()}

    def execute(payload, proposal, idempotency_key):
        executed.append((dict(payload), proposal.project_revision_id, idempotency_key))
        return {"activity_id": "a-1", "name": payload["name"]}

    runtime = AIActionRuntime(
        store=store,
        permission_adapter=UserConfiguredAIActionPermissionAdapter(lambda: (grant,)),
        audit_sink=store,
        tools=[AIActionToolDefinition(
            tool_name="activity.create", action="create", resource_domain="activities",
            requires_human_approval=True, validate_payload=validate_payload, execute=execute,
        )],
        clock=lambda: now,
    )
    routes = ProjectLifecycleHttpRoutes(
        api,
        clock=type("Clock", (), {"now": lambda self: now})(),
        ai_action_runtime=runtime if runtime_enabled else None,
    )
    return routes, conn, executed


def request(routes, path, payload, method="POST"):
    return routes.handle(
        method, path, cookies={"cp_session": "session-1"},
        body=json.dumps(payload).encode("utf-8"),
    )


def test_authenticated_project_action_route_runs_propose_approve_execute():
    routes, conn, executed = build_routes()
    status, _, body = request(routes, "/api/projects/p1/ai/actions/proposals", {
        "expected_revision": 2,
        "tool_name": "activity.create",
        "payload": {"name": "  Excavation "},
        "evidence_refs": ["import-row-7"],
        # Privilege/approval fields supplied by a client must not be trusted.
        "requires_human_approval": False,
        "tenant_id": "other-tenant",
        "requested_by": "admin",
    })
    assert status == 201
    proposal = json.loads(body)["proposal"]
    proposal_id = proposal["proposal_id"]
    assert proposal["requires_human_approval"] is True
    assert proposal["payload"] == {"name": "Excavation"}
    assert proposal["project_revision_id"] == "2"

    status, _, body = request(routes, f"/api/projects/p1/ai/actions/proposals/{proposal_id}/decision", {
        "expected_revision": 2, "approved": True,
    })
    assert status == 200
    assert json.loads(body)["status"] == "approved"

    status, _, body = request(routes, f"/api/projects/p1/ai/actions/proposals/{proposal_id}/execute", {
        "expected_revision": 2,
    })
    assert status == 200
    result = json.loads(body)
    assert result["status"] == "executed"
    assert result["result"] == {"activity_id": "a-1", "name": "Excavation"}
    assert len(executed) == 1
    assert executed[0][2] == proposal_id
    assert conn.execute("SELECT COUNT(*) FROM ai_action_audit_events").fetchone()[0] == 5


def test_ai_action_route_rejects_stale_request_revision():
    routes, _, executed = build_routes()
    status, _, body = request(routes, "/api/projects/p1/ai/actions/proposals", {
        "expected_revision": 1,
        "tool_name": "activity.create",
        "payload": {"name": "Excavation"},
    })
    assert status == 409
    assert json.loads(body)["code"] == "AI_ACTION_PROPOSAL_STALE_REVISION"
    assert executed == []


def test_ai_action_route_is_fail_closed_when_runtime_is_not_composed():
    routes, _, _ = build_routes(runtime_enabled=False)
    status, _, body = request(routes, "/api/projects/p1/ai/actions/proposals", {
        "expected_revision": 2,
        "tool_name": "activity.create",
        "payload": {"name": "Excavation"},
    })
    assert status == 404
    assert json.loads(body)["code"] == "ROUTE_NOT_FOUND"
