from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession, ProjectSummary
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.models import BackendScope
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.p6_activity_period_actual_api import P6_ACTIVITY_PERIOD_ACTUAL_API_VERSION


class Sessions:
    def __init__(self, session): self.session = session
    def get(self, session_id): return self.session if session_id == self.session.session_id else None


class Projects:
    def list_for_user(self, tenant_id, user_id):
        return (ProjectSummary("p1", tenant_id, "Project One", 2),)

    def get_for_user(self, tenant_id, project_id, user_id):
        if project_id != "p1": return None
        return ProjectSummary("p1", tenant_id, "Project One", 2)

    def create_for_user(self, tenant_id, user_id, project_id, name):
        return ProjectSummary(project_id, tenant_id, name, 0)


class FakeActivityPeriodActualAPI:
    def __init__(self):
        self.calls = []

    def create(self, actual, *, auth_context):
        self.calls.append(("create", actual, auth_context))
        return {
            "contract_version": P6_ACTIVITY_PERIOD_ACTUAL_API_VERSION,
            "kind": "p6_activity_period_actual",
            "activity_period_actual": {"actual_id": actual.actual_id},
        }

    def get(self, scope, actual_id, *, auth_context):
        self.calls.append(("get", scope, actual_id, auth_context))
        if actual_id == "missing": return None
        return {
            "contract_version": P6_ACTIVITY_PERIOD_ACTUAL_API_VERSION,
            "activity_period_actual": {"actual_id": actual_id},
        }

    def list(self, scope, *, activity_id=None, period_id=None, auth_context):
        self.calls.append(("list", scope, activity_id, period_id, auth_context))
        return ({
            "contract_version": P6_ACTIVITY_PERIOD_ACTUAL_API_VERSION,
            "activity_period_actual": {"actual_id": "x1"},
        },)


def routes():
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", "t1", frozenset({"project_admin"}), now + timedelta(hours=1)
    )
    service = __import__(
        "construction_pm.application.project_lifecycle",
        fromlist=["ProjectLifecycleService"],
    ).ProjectLifecycleService(
        Sessions(session), Projects(), default_project_policy()
    )
    fake = FakeActivityPeriodActualAPI()
    return ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_activity_period_actual_api=fake,
    ), fake


def test_activity_period_actual_http_create_preserves_scope_and_decimal_values():
    routes_instance, fake = routes()
    payload = {
        "actual_id": "x1",
        "activity_id": "a1",
        "period_id": "2026-09",
        "actual_units": "3.125",
        "actual_cost": "20.50",
        "unit": "h",
        "currency": "USD",
        "note": "period actual",
    }
    status, _, body = routes_instance.handle(
        "POST",
        "/api/projects/p1/p6/activity-period-actuals",
        cookies={"cp_session": "s1"},
        body=json.dumps(payload).encode(),
    )
    assert status == 200
    assert json.loads(body)["contract_version"] == P6_ACTIVITY_PERIOD_ACTUAL_API_VERSION
    call = fake.calls[-1]
    assert call[0] == "create"
    assert call[1].scope == BackendScope("t1", "p1", 2)
    assert call[1].actual_units == Decimal("3.125")
    assert call[1].actual_cost == Decimal("20.50")


def test_activity_period_actual_http_list_get_and_cross_scope_rejection():
    routes_instance, fake = routes()

    status, _, body = routes_instance.handle(
        "GET",
        "/api/projects/p1/p6/activity-period-actuals",
        cookies={"cp_session": "s1"},
        body=json.dumps({"activity_id": "a1", "period_id": "2026-09"}).encode(),
    )
    assert status == 200
    assert json.loads(body)["activity_period_actuals"][0]["activity_period_actual"]["actual_id"] == "x1"

    status, _, body = routes_instance.handle(
        "GET",
        "/api/projects/p1/p6/activity-period-actuals/x1",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    assert json.loads(body)["activity_period_actual"]["actual_id"] == "x1"

    status, _, _ = routes_instance.handle(
        "GET",
        "/api/projects/p1/p6/activity-period-actuals/missing",
        cookies={"cp_session": "s1"},
    )
    assert status == 404

    status, _, _ = routes_instance.handle(
        "GET",
        "/api/projects/other/p6/activity-period-actuals/x1",
        cookies={"cp_session": "s1"},
    )
    assert status == 403
