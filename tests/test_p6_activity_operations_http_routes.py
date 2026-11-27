"""HTTP acceptance for POST /api/projects/{id}/p6/activity-operations.

The route is the only way the workspace performs Cut/Copy/Paste/Delete, so these
tests drive the real WSGI app: session cookie, project context, permission
policy, idempotency header and error mapping all participate.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
import json
import sqlite3

from construction_pm.activity_master_repository import (
    ActivityMaster,
    SQLiteActivityMasterRepository,
)
from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectSummary,
    ProjectLifecycleService,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.http.wsgi import ProjectLifecycleWsgiApp
from construction_pm.p6_activity_master_api import P6ActivityMasterAPI
from construction_pm.p6_activity_operations import (
    ActivityOperationStore,
    P6ActivityOperationAPI,
    P6_ACTIVITY_OPERATIONS_API_VERSION,
)
from construction_pm.p6_wbs_master_api import P6WBSMasterAPI
from construction_pm.relationship_master_repository import (
    RelationshipMaster,
    SQLiteRelationshipMasterRepository,
)
from construction_pm.scheduling.activity import ActivityStatus, ActivityStatusCode
from construction_pm.scheduling.time_duration import DurationUnit
from construction_pm.wbs_master_repository import (
    SQLiteWBSMasterRepository,
    WBSParentKind,
    WBSMaster,
)

SCOPE = BackendScope("t1", "p1", 2)


class Sessions:
    def __init__(self, session: AuthenticatedSession) -> None:
        self.session = session

    def get(self, session_id: str):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def __init__(self) -> None:
        self.items = {"p1": ("p1", "Project One", 2)}

    def list_for_user(self, tenant_id: str, user_id: str):
        return tuple(
            ProjectSummary(pid, tenant_id, name, revision)
            for pid, (_, name, revision) in self.items.items()
        )

    def get_for_user(self, tenant_id: str, project_id: str, user_id: str):
        item = self.items.get(project_id)
        if item is None:
            return None
        return ProjectSummary(item[0], tenant_id, item[1], item[2])

    def create_for_user(self, tenant_id, user_id, project_id, name, **_):
        self.items[project_id] = (project_id, name, 0)
        return ProjectSummary(project_id, tenant_id, name, 0)

    def update_for_user(self, **_):
        return None

    def record_defaults_application_for_user(self, **_):
        return None

    def defaults_history_for_user(self, *_a, **_k):
        return ()


def _app(*, role: str = "planner"):
    now = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", "t1", frozenset({role}), now + timedelta(hours=1)
    )
    policy = default_project_policy()
    lifecycle = ProjectLifecycleAPI(
        ProjectLifecycleService(Sessions(session), Projects(), policy)
    )
    connection = sqlite3.connect(":memory:")
    activities = SQLiteActivityMasterRepository(connection)
    wbs = SQLiteWBSMasterRepository(connection)
    relationships = SQLiteRelationshipMasterRepository(connection)
    store = ActivityOperationStore(connection, placeholder="?")
    store.initialize()
    wbs.save(
        WBSMaster(
            scope=SCOPE,
            wbs_id="W-ROOT",
            parent_kind=WBSParentKind.PROJECT,
            parent_wbs_id=None,
            code="1",
            name="Root",
            sequence_number=0,
        )
    )
    activities.save(
        ActivityMaster(
            scope=SCOPE,
            activity_id="A-1",
            duration_value=Decimal("3"),
            duration_unit=DurationUnit.WORKING_DAY,
            name="A-1",
            wbs_id="W-ROOT",
            status=ActivityStatus.IN_PROGRESS,
            status_code=ActivityStatusCode.ACTIVE,
            percent_complete=10.0,
            actual_start=date(2026, 1, 1),
        )
    )
    operation_api = P6ActivityOperationAPI(
        activity_repository=activities,
        wbs_repository=wbs,
        store=store,
        authorization_policy=policy,
        transaction_manager=SQLiteTransactionManager(connection),
    )
    routes = ProjectLifecycleHttpRoutes(
        lifecycle,
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_activity_master_api=P6ActivityMasterAPI(activities, policy),
        p6_activity_operation_api=operation_api,
        p6_wbs_master_api=P6WBSMasterAPI(wbs, policy),
    )
    return ProjectLifecycleWsgiApp(routes), activities, connection, relationships


def _request(app, method: str, path: str, payload: dict | None = None,
             *, idempotency_key: str | None = "idem-1"):
    body = json.dumps(payload or {}).encode("utf-8")
    status: list[str] = []
    chunks: list[bytes] = []
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "HTTP_COOKIE": "cp_session=s1",
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
    }
    if idempotency_key is not None:
        environ["HTTP_IDEMPOTENCY_KEY"] = idempotency_key

    def start_response(value, headers):
        status.append(value)

    chunks.extend(app(environ, start_response))
    return status[0], json.loads(b"".join(chunks))


def _payload(operation: str, ids, **extra):
    return {
        "contract_version": P6_ACTIVITY_OPERATIONS_API_VERSION,
        "operation": operation,
        "activity_ids": ids,
        **extra,
    }


def test_copy_route_creates_persisted_activity_and_replays():
    app, activities, _, _ = _app()
    path = "/api/projects/p1/p6/activity-operations"

    status, created = _request(app, "POST", path, _payload("copy", ["A-1"]))
    assert status == "200 OK"
    assert created["created"] == [
        {"source_activity_id": "A-1", "activity_id": "A-1-COPY"}
    ]
    assert created["replayed"] is False
    assert activities.get(SCOPE, "A-1-COPY") is not None

    status, replay = _request(app, "POST", path, _payload("copy", ["A-1"]))
    assert status == "200 OK"
    assert replay["replayed"] is True
    assert activities.get(SCOPE, "A-1-COPY2") is None


def test_missing_idempotency_key_is_a_request_error():
    app, _, _, _ = _app()
    status, body = _request(
        app,
        "POST",
        "/api/projects/p1/p6/activity-operations",
        _payload("copy", ["A-1"]),
        idempotency_key=None,
    )
    assert status == "400 Bad Request"
    assert body["code"] == "IDEMPOTENCY_KEY_REQUIRED"


def test_viewer_receives_forbidden():
    app, activities, _, _ = _app(role="viewer")
    status, body = _request(
        app,
        "POST",
        "/api/projects/p1/p6/activity-operations",
        _payload("copy", ["A-1"]),
    )
    assert status == "403 Forbidden"
    assert body["code"].startswith("AUTHORIZATION")
    assert activities.get(SCOPE, "A-1-COPY") is None


def test_delete_blocked_and_confirmation_details_are_returned():
    app, activities, connection, relationships = _app()
    connection.execute(
        "CREATE TABLE p6_expense (tenant_id TEXT, project_id TEXT, activity_id TEXT)"
    )
    connection.execute(
        "INSERT INTO p6_expense (tenant_id, project_id, activity_id) VALUES (?,?,?)",
        ("t1", "p1", "A-1"),
    )
    path = "/api/projects/p1/p6/activity-operations"

    status, blocked = _request(
        app, "POST", path, _payload("delete", ["A-1"], confirm_dependencies=True)
    )
    assert status == "409 Conflict"
    assert blocked["code"] == "P6_ACTIVITY_DELETE_BLOCKED_DEPENDENCIES"
    assert blocked["details"] == {"blocking_expense": 1}
    assert activities.get(SCOPE, "A-1") is not None

    connection.execute("DELETE FROM p6_expense")
    activities.save(
        ActivityMaster(
            scope=SCOPE,
            activity_id="A-2",
            duration_value=Decimal("3"),
            duration_unit=DurationUnit.WORKING_DAY,
            name="A-2",
            wbs_id="W-ROOT",
        )
    )
    relationships.save(
        RelationshipMaster(
            scope=SCOPE,
            relationship_id="R-1",
            predecessor_id="A-1",
            successor_id="A-2",
        )
    )
    status, needs_confirm = _request(
        app, "POST", path, _payload("delete", ["A-1"]), idempotency_key="k2"
    )
    assert status == "409 Conflict"
    assert needs_confirm["code"] == "P6_ACTIVITY_DELETE_CONFIRMATION_REQUIRED"
    assert needs_confirm["details"]["relationships"] == 1

    status, deleted = _request(
        app,
        "POST",
        path,
        _payload("delete", ["A-1"], confirm_dependencies=True),
        idempotency_key="k3",
    )
    assert status == "200 OK"
    assert deleted["deleted_count"] == 1
    assert activities.get(SCOPE, "A-1") is None
    assert relationships.get(SCOPE, "R-1") is None


def test_unknown_operation_and_method_are_rejected():
    app, _, _, _ = _app()
    path = "/api/projects/p1/p6/activity-operations"
    status, body = _request(app, "POST", path, _payload("explode", ["A-1"]))
    assert status == "400 Bad Request"
    assert body["code"] == "P6_ACTIVITY_OPERATION_INVALID"

    status, body = _request(app, "GET", path)
    assert status == "404 Not Found"
    assert body["code"] == "ROUTE_NOT_FOUND"
