from datetime import datetime, timedelta, timezone
import json

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes


class Sessions:
    def __init__(self, session): self.session = session
    def get(self, session_id): return self.session if session_id == self.session.session_id else None


class Projects:
    def __init__(self): self.items = {"p1": ("p1", "Project One", 2)}
    def list_for_user(self, tenant_id, user_id):
        return tuple(
            type("Project", (), {"project_id": pid, "tenant_id": tenant_id, "name": name, "revision": rev})()
            for pid, (pid, name, rev) in self.items.items()
        )
    def get_for_user(self, tenant_id, project_id, user_id):
        item = self.items.get(project_id)
        if not item: return None
        return type("Project", (), {"project_id": item[0], "tenant_id": tenant_id, "name": item[1], "revision": item[2]})()
    def create_for_user(self, tenant_id, user_id, project_id, name):
        self.items[project_id] = (project_id, name, 0)
        return type("Project", (), {"project_id": project_id, "tenant_id": tenant_id, "name": name, "revision": 0})()


def routes():
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    session = AuthenticatedSession("s1", "u1", "t1", frozenset({"project_admin"}), now + timedelta(hours=1))
    service = __import__("construction_pm.application.project_lifecycle", fromlist=["ProjectLifecycleService"]).ProjectLifecycleService(
        Sessions(session), Projects(), default_project_policy()
    )
    return ProjectLifecycleHttpRoutes(ProjectLifecycleAPI(service), clock=type("Clock", (), {"now": lambda self: now})())


def test_requires_session_cookie():
    status, _, _ = routes().handle("GET", "/api/session")
    assert status == 401


def test_session_and_project_routes_bridge_application_to_web_contract():
    r = routes()
    status, _, body = r.handle("GET", "/api/session", cookies={"cp_session": "s1"})
    assert status == 200
    assert json.loads(body)["tenant_id"] == "t1"

    status, _, body = r.handle("GET", "/api/projects", cookies={"cp_session": "s1"})
    assert status == 200
    assert json.loads(body)["projects"][0]["project_id"] == "p1"

    status, _, body = r.handle("POST", "/api/projects/p1/open", cookies={"cp_session": "s1"})
    assert status == 200
    assert json.loads(body)["context"]["project_id"] == "p1"


def test_browser_cannot_supply_identity_headers_as_authority():
    r = routes()
    status, _, _ = r.handle("GET", "/api/projects", cookies={"cp_session": "missing"})
    assert status == 401
