import json
from datetime import datetime, timedelta, timezone
import sqlite3

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession, ProjectSummary
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.p6_role_api import P6RoleAPI
from construction_pm.p6_role_repository import SQLiteP6RoleRepository


class Sessions:
    def __init__(self, session): self.session = session
    def get(self, session_id): return self.session if session_id == self.session.session_id else None


class Projects:
    def list_for_user(self, tenant_id, user_id):
        return (ProjectSummary("p1", tenant_id, "Project One", 2),)

    def get_for_user(self, tenant_id, project_id, user_id):
        return ProjectSummary("p1", tenant_id, "Project One", 2) if project_id == "p1" else None

    def create_for_user(self, tenant_id, user_id, project_id, name):
        return ProjectSummary(project_id, tenant_id, name, 0)


def routes():
    now = datetime(2026, 10, 8, tzinfo=timezone.utc)
    session = AuthenticatedSession("s1", "u1", "t1", frozenset({"project_admin"}), now + timedelta(hours=1))
    service = __import__("construction_pm.application.project_lifecycle", fromlist=["ProjectLifecycleService"]).ProjectLifecycleService(
        Sessions(session), Projects(), default_project_policy()
    )
    role_api = P6RoleAPI(SQLiteP6RoleRepository(sqlite3.connect(":memory:")), default_project_policy())
    return ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_role_api=role_api,
    )


def test_p6_role_http_round_trip_and_scope():
    r = routes()
    payload = {"role_id": "role-1", "name": "Site Engineer", "description": "Engineering role"}
    status, _, body = r.handle("POST", "/api/projects/p1/p6/roles", cookies={"cp_session": "s1"}, body=json.dumps(payload).encode())
    assert status == 200
    created = json.loads(body)
    assert created["contract_version"] == "p6-role-api.v1"
    assert created["role"]["record_revision"] == 1

    status, _, body = r.handle("GET", "/api/projects/p1/p6/roles/role-1", cookies={"cp_session": "s1"})
    assert status == 200
    assert json.loads(body) == created

    status, _, body = r.handle("GET", "/api/projects/p1/p6/roles", cookies={"cp_session": "s1"})
    assert status == 200
    assert json.loads(body)["roles"] == [created]


def test_p6_role_http_rejects_malformed_update_and_cross_project():
    r = routes()
    status, _, _ = r.handle("PATCH", "/api/projects/p1/p6/roles/role-1", cookies={"cp_session": "s1"}, body=b"{}")
    assert status == 400
    status, _, _ = r.handle("GET", "/api/projects/other/p6/roles", cookies={"cp_session": "s1"})
    assert status == 403
