import json
from datetime import datetime, timedelta, timezone
import sqlite3

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession, ProjectSummary
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.p6_resource_master_repository import (
    P6Resource,
    SQLiteP6ResourceRepository,
)
from construction_pm.p6_role_api import P6RoleAPI
from construction_pm.p6_role_details_api import P6RoleDetailsAPI
from construction_pm.p6_role_dictionary_repository import (
    SQLiteP6RoleDictionaryRepository,
)
from construction_pm.p6_role_repository import SQLiteP6RoleRepository


class Sessions:
    def __init__(self, session): self.session = session
    def get(self, session_id): return self.session if session_id == self.session.session_id else None


class Projects:
    def list_for_user(self, tenant_id, user_id):
        return (ProjectSummary("p1", tenant_id, "Project One", 2),)

    def get_for_user(self, tenant_id, project_id, user_id):
        return ProjectSummary("p1", tenant_id, "Project One", 2) if project_id == "p1" else None

    def create_for_user(self, tenant_id, user_id, project_id, name, **_):
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


def role_routes():
    connection = sqlite3.connect(":memory:")
    policy = default_project_policy()
    roles = SQLiteP6RoleRepository(connection)
    resources = SQLiteP6ResourceRepository(connection)
    resources.save(P6Resource("t1", "p1", 2, "RES-A", "Crew A"))
    dictionary = SQLiteP6RoleDictionaryRepository(connection)
    now = datetime(2026, 10, 8, tzinfo=timezone.utc)
    session = AuthenticatedSession("s1", "u1", "t1", frozenset({"project_admin"}), now + timedelta(hours=1))
    service = __import__("construction_pm.application.project_lifecycle", fromlist=["ProjectLifecycleService"]).ProjectLifecycleService(
        Sessions(session), Projects(), policy
    )
    return ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_role_api=P6RoleAPI(roles, policy),
        p6_role_details_api=P6RoleDetailsAPI(roles, resources, dictionary, policy),
    )


def request(routes, method, path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else b""
    status, _, response = routes.handle(method, path, cookies={"cp_session": "s1"}, body=body)
    return status, json.loads(response) if response else None


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


def test_role_http_hierarchy_conflicts_and_tree_order():
    r = role_routes()
    assert request(r, "POST", "/api/projects/p1/p6/roles", {"role_id": "ROLE-ENG", "name": "Engineering"})[0] == 200
    status, created = request(
        r, "POST", "/api/projects/p1/p6/roles",
        {"role_id": "ROLE-CIVIL", "name": "Civil", "parent_role_id": "ROLE-ENG"},
    )
    assert status == 200
    assert created["role"]["parent_role_id"] == "ROLE-ENG"
    assert created["role"]["calculate_costs_from_units"] is True

    status, body = request(r, "POST", "/api/projects/p1/p6/roles", {"role_id": "ROLE-CIVIL", "name": "Duplicate"})
    assert status == 409
    assert body["code"] == "ROLE_ALREADY_EXISTS"
    status, body = request(
        r, "POST", "/api/projects/p1/p6/roles",
        {"role_id": "ROLE-X", "name": "X", "parent_role_id": "MISSING"},
    )
    assert status == 409
    assert body["code"] == "ROLE_PARENT_NOT_FOUND"
    status, body = request(
        r, "PATCH", "/api/projects/p1/p6/roles/ROLE-ENG",
        {"name": "Engineering", "parent_role_id": "ROLE-CIVIL", "expected_revision": 1},
    )
    assert status == 409
    assert body["code"] == "ROLE_HIERARCHY_CYCLE"

    status, body = request(r, "GET", "/api/projects/p1/p6/roles")
    assert status == 200
    assert [item["role"]["role_id"] for item in body["roles"]] == ["ROLE-ENG", "ROLE-CIVIL"]


def test_role_http_rates_are_effective_dated_and_revision_guarded():
    r = role_routes()
    assert request(r, "POST", "/api/projects/p1/p6/roles", {"role_id": "ROLE-1", "name": "Role"})[0] == 200
    status, created = request(
        r, "POST", "/api/projects/p1/p6/roles/ROLE-1/rates",
        {"effective_from": "2026-12-01", "rate_type": "Standard", "rate": "25.5", "unit": "h", "currency": "USD"},
    )
    assert status == 200, created
    assert created["contract_version"] == "p6-role-rate-api.v1"
    assert created["rate"]["rate"] == "25.5"
    assert created["rate"]["record_revision"] == 1

    status, body = request(
        r, "POST", "/api/projects/p1/p6/roles/ROLE-1/rates",
        {"effective_from": "2026-12-01", "rate_type": "Standard", "rate": "99", "unit": "h", "currency": "USD"},
    )
    assert status == 409
    assert body["code"] == "ROLE_RATE_ALREADY_EXISTS"

    status, updated = request(
        r, "PATCH", "/api/projects/p1/p6/roles/ROLE-1/rates/2026-12-01",
        {"rate_type": "Standard", "rate": "27", "unit": "h", "currency": "USD", "expected_revision": 1},
    )
    assert status == 200
    assert updated["rate"]["rate"] == "27"
    assert updated["rate"]["record_revision"] == 2
    status, body = request(
        r, "PATCH", "/api/projects/p1/p6/roles/ROLE-1/rates/2026-12-01",
        {"rate_type": "Standard", "rate": "28", "unit": "h", "currency": "USD", "expected_revision": 1},
    )
    assert status == 409
    assert body["code"] == "REVISION_CONFLICT"
    status, body = request(
        r, "POST", "/api/projects/p1/p6/roles/ROLE-1/rates",
        {"effective_from": "2026-12-01", "rate_type": "Night", "rate": "30", "unit": "day", "currency": "USD"},
    )
    assert status == 400
    assert body["code"] == "INVALID_ROLE_RATE_UNIT"

    status, body = request(r, "GET", "/api/projects/p1/p6/roles/ROLE-1/rates")
    assert status == 200
    assert len(body["rates"]) == 1
    assert body["rates"][0]["record_revision"] == 2


def test_role_http_limits_and_resource_proficiency_round_trip():
    r = role_routes()
    assert request(r, "POST", "/api/projects/p1/p6/roles", {"role_id": "ROLE-1", "name": "Role"})[0] == 200
    status, created = request(
        r, "POST", "/api/projects/p1/p6/roles/ROLE-1/limits",
        {"effective_from": "2026-12-01", "max_units": "8", "unit_basis": "units"},
    )
    assert status == 200
    assert created["limit"]["max_units"] == "8"
    status, body = request(
        r, "POST", "/api/projects/p1/p6/roles/ROLE-1/limits",
        {"effective_from": "2026-12-01", "max_units": "10", "unit_basis": "units"},
    )
    assert status == 409
    assert body["code"] == "ROLE_LIMIT_ALREADY_EXISTS"
    status, updated = request(
        r, "PATCH", "/api/projects/p1/p6/roles/ROLE-1/limits/2026-12-01",
        {"max_units": "75", "unit_basis": "percent", "expected_revision": 1},
    )
    assert status == 200
    assert updated["limit"]["unit_basis"] == "percent"
    assert updated["limit"]["record_revision"] == 2

    status, created = request(
        r, "POST", "/api/projects/p1/p6/roles/ROLE-1/resources",
        {"resource_id": "RES-A", "proficiency": "Expert", "is_primary": True},
    )
    assert status == 200
    assert created["resource"]["proficiency"] == "expert"
    assert created["resource"]["is_primary"] is True
    status, updated = request(
        r, "PATCH", "/api/projects/p1/p6/roles/ROLE-1/resources/RES-A",
        {"proficiency": "master", "is_primary": True, "expected_revision": 1},
    )
    assert status == 200
    assert updated["resource"]["proficiency"] == "master"
    assert updated["resource"]["record_revision"] == 2

    status, body = request(r, "GET", "/api/projects/p1/p6/roles/ROLE-1/resources")
    assert status == 200
    assert [item["resource_id"] for item in body["resources"]] == ["RES-A"]
    status, body = request(
        r, "DELETE", "/api/projects/p1/p6/roles/ROLE-1/resources/RES-A",
        {"expected_revision": 2},
    )
    assert status == 200
    assert body["kind"] == "role_resource_removed"
    status, body = request(r, "GET", "/api/projects/p1/p6/roles/ROLE-1/resources")
    assert body["resources"] == []

    status, body = request(
        r, "POST", "/api/projects/p1/p6/roles/ROLE-1/resources",
        {"resource_id": "MISSING", "proficiency": "expert", "is_primary": False},
    )
    assert status == 404
    assert body["code"] == "ROLE_RESOURCE_NOT_FOUND"
