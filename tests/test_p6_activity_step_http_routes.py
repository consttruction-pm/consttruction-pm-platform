from datetime import datetime, timedelta, timezone
import json

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession, ProjectSummary, ProjectLifecycleService
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.models import BackendScope
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.p6_activity_step_api import P6_ACTIVITY_STEP_API_VERSION


class Sessions:
    def __init__(self, session):
        self.session = session

    def get(self, session_id):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def list_for_user(self, tenant_id, user_id):
        return (ProjectSummary("p1", tenant_id, "Project One", 2),)

    def get_for_user(self, tenant_id, project_id, user_id):
        if project_id != "p1":
            return None
        return ProjectSummary("p1", tenant_id, "Project One", 2)

    def create_for_user(self, tenant_id, user_id, project_id, name, **_):
        return ProjectSummary(project_id, tenant_id, name, 0)


class FakeActivityStepAPI:
    def __init__(self):
        self.calls = []

    def list(self, scope, *, activity_id=None, auth_context):
        self.calls.append(("list", scope, activity_id, auth_context))
        return ({
            "contract_version": P6_ACTIVITY_STEP_API_VERSION,
            "kind": "p6_activity_step",
            "scope": {"tenant_id": scope.tenant_id, "project_id": scope.project_id, "project_revision": scope.project_revision},
            "step": {"step_id": "S-1", "activity_id": "A-100", "sequence": 1, "description": "Inspect formwork", "weight": "10.50", "start_date": "2026-11-01", "finish_date": "2026-11-02", "udf_values": []},
        },)

    def get(self, scope, step_id, *, auth_context):
        self.calls.append(("get", scope, step_id, auth_context))
        if step_id == "missing":
            return None
        return self.list(scope, activity_id=None, auth_context=auth_context)[0]


def routes():
    now = datetime(2026, 11, 5, tzinfo=timezone.utc)
    session = AuthenticatedSession("s1", "u1", "t1", frozenset({"project_admin"}), now + timedelta(hours=1))
    service = ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    fake = FakeActivityStepAPI()
    router = ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_activity_step_api=fake,
    )
    return router, fake


def test_activity_step_http_list_returns_only_authenticated_project_revision_and_supports_activity_filter():
    router, fake = routes()
    status, _, body = router.handle(
        "GET", "/api/projects/p1/p6/activity-steps?activity_id=A-100",
        cookies={"cp_session": "s1"},
    )

    payload = json.loads(body)
    assert status == 200
    assert payload["contract_version"] == P6_ACTIVITY_STEP_API_VERSION
    assert payload["scope"] == {"tenant_id": "t1", "project_id": "p1", "project_revision": 2}
    assert payload["steps"][0]["step"]["weight"] == "10.50"
    assert fake.calls[-1][0:3] == ("list", BackendScope("t1", "p1", 2), "A-100")


def test_activity_step_http_get_missing_and_cross_project_are_not_disclosed():
    router, _ = routes()
    status, _, body = router.handle(
        "GET", "/api/projects/p1/p6/activity-steps/missing",
        cookies={"cp_session": "s1"},
    )
    assert status == 404
    assert json.loads(body)["error"]["code"] == "P6_ACTIVITY_STEP_NOT_FOUND"

    status, _, body = router.handle(
        "GET", "/api/projects/other/p6/activity-steps",
        cookies={"cp_session": "s1"},
    )
    assert status == 403
    assert json.loads(body)["error"]["code"] == "PROJECT_NOT_FOUND_OR_NOT_AUTHORIZED"


def test_activity_step_http_requires_an_authenticated_session():
    router, _ = routes()
    status, _, body = router.handle("GET", "/api/projects/p1/p6/activity-steps")
    assert status == 401
    assert json.loads(body)["error"]["code"] == "SESSION_REQUIRED"
