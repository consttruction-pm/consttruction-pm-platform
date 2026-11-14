from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession, ProjectSummary
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.models import BackendScope
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.p6_activity_period_actual_api import P6_ACTIVITY_PERIOD_ACTUAL_API_VERSION
from construction_pm.p6_activity_period_actual_repository import P6ActivityPeriodActualPersistenceError


class Sessions:
    def __init__(self, session): self.session = session
    def get(self, session_id): return self.session if session_id == self.session.session_id else None


class Projects:
    def list_for_user(self, tenant_id, user_id):
        return (ProjectSummary("p1", tenant_id, "Project One", 2),)

    def get_for_user(self, tenant_id, project_id, user_id):
        if project_id != "p1": return None
        return ProjectSummary("p1", tenant_id, "Project One", 2)

    def create_for_user(self, tenant_id, user_id, project_id, name, **_):
        return ProjectSummary(project_id, tenant_id, name, 0)


class FakeActivityPeriodActualAPI:
    def __init__(self): self.calls = []

    def create(self, actual, *, auth_context):
        self.calls.append(("create", actual, auth_context))
        if actual.actual_id == "immutable":
            raise P6ActivityPeriodActualPersistenceError("IMMUTABLE_ACTIVITY_PERIOD_ACTUAL")
        return {"contract_version": P6_ACTIVITY_PERIOD_ACTUAL_API_VERSION, "kind": "p6_activity_period_actual", "activity_period_actual": {"actual_id": actual.actual_id}}

    def get(self, scope, actual_id, *, auth_context):
        self.calls.append(("get", scope, actual_id, auth_context))
        if actual_id == "missing": return None
        return {"contract_version": P6_ACTIVITY_PERIOD_ACTUAL_API_VERSION, "activity_period_actual": {"actual_id": actual_id}}

    def list(self, scope, *, activity_id=None, period_id=None, auth_context):
        self.calls.append(("list", scope, activity_id, period_id, auth_context))
        return ({"contract_version": P6_ACTIVITY_PERIOD_ACTUAL_API_VERSION, "activity_period_actual": {"actual_id": "x1"}},)


def routes():
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    session = AuthenticatedSession("s1", "u1", "t1", frozenset({"project_admin"}), now + timedelta(hours=1))
    service = __import__("construction_pm.application.project_lifecycle", fromlist=["ProjectLifecycleService"]).ProjectLifecycleService(
        Sessions(session), Projects(), default_project_policy()
    )
    fake = FakeActivityPeriodActualAPI()
    return ProjectLifecycleHttpRoutes(ProjectLifecycleAPI(service), clock=type("Clock", (), {"now": lambda self: now})(), p6_activity_period_actual_api=fake), fake


def test_activity_period_actual_http_create_preserves_scope_and_decimal_values():
    routes_instance, fake = routes()
    payload = {"actual_id": "x1", "activity_id": "a1", "period_id": "2026-09", "actual_units": "3.125", "actual_cost": "20.50", "unit": "h", "currency": "USD", "note": "period actual"}
    status, _, body = routes_instance.handle("POST", "/api/projects/p1/p6/activity-period-actuals", cookies={"cp_session": "s1"}, body=json.dumps(payload).encode())
    assert status == 200
    assert json.loads(body)["contract_version"] == P6_ACTIVITY_PERIOD_ACTUAL_API_VERSION
    call = fake.calls[-1]
    assert call[0] == "create"
    assert call[1].scope == BackendScope("t1", "p1", 2)
    assert call[1].actual_units == Decimal("3.125")
    assert call[1].actual_cost == Decimal("20.50")


def test_activity_period_actual_http_list_get_and_cross_scope_rejection():
    routes_instance, _ = routes()
    status, _, body = routes_instance.handle("GET", "/api/projects/p1/p6/activity-period-actuals", cookies={"cp_session": "s1"}, body=json.dumps({"activity_id": "a1", "period_id": "2026-09"}).encode())
    assert status == 200
    assert json.loads(body)["activity_period_actuals"][0]["activity_period_actual"]["actual_id"] == "x1"
    status, _, body = routes_instance.handle("GET", "/api/projects/p1/p6/activity-period-actuals/x1", cookies={"cp_session": "s1"})
    assert status == 200
    assert json.loads(body)["activity_period_actual"]["actual_id"] == "x1"
    status, _, _ = routes_instance.handle("GET", "/api/projects/p1/p6/activity-period-actuals/missing", cookies={"cp_session": "s1"})
    assert status == 404
    status, _, _ = routes_instance.handle("GET", "/api/projects/other/p6/activity-period-actuals/x1", cookies={"cp_session": "s1"})
    assert status == 403


class FakeActivityMasterAPI:
    def __init__(self, activity_ids=("a1",)):
        self.activity_ids = set(activity_ids)
        self.calls = []

    def get(self, scope, activity_id, *, auth_context):
        self.calls.append((scope, activity_id))
        if activity_id not in self.activity_ids:
            return None
        return {"contract_version": "p6-activity-master-api.v1", "kind": "p6_activity_master", "activity": {"activity_id": activity_id}}


class FakeFinancialPeriodAPI:
    def __init__(self, period_ids=("2026-09",)):
        self.period_ids = set(period_ids)
        self.calls = []

    def get(self, scope, period_id, *, auth_context):
        self.calls.append((scope, period_id))
        if period_id not in self.period_ids:
            return None
        return {"contract_version": "p6-financial-period-api.v1", "kind": "p6_financial_period", "financial_period": {"period_id": period_id}}


def routes_with_registers():
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    session = AuthenticatedSession("s1", "u1", "t1", frozenset({"project_admin"}), now + timedelta(hours=1))
    service = __import__("construction_pm.application.project_lifecycle", fromlist=["ProjectLifecycleService"]).ProjectLifecycleService(
        Sessions(session), Projects(), default_project_policy()
    )
    fake = FakeActivityPeriodActualAPI()
    activities = FakeActivityMasterAPI()
    periods = FakeFinancialPeriodAPI()
    routes_instance = ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_activity_period_actual_api=fake,
        p6_activity_master_api=activities,
        p6_financial_period_api=periods,
    )
    return routes_instance, fake, activities, periods


def test_activity_period_actual_http_list_reads_query_filters_without_a_request_body():
    routes_instance, fake, _, _ = routes_with_registers()
    status, _, body = routes_instance.handle(
        "GET",
        "/api/projects/p1/p6/activity-period-actuals?activity_id=a1&period_id=2026-09",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    assert json.loads(body)["activity_period_actuals"][0]["activity_period_actual"]["actual_id"] == "x1"
    assert fake.calls[-1][0] == "list"
    assert fake.calls[-1][2:4] == ("a1", "2026-09")


def test_activity_period_actual_http_create_rejects_dangling_activity_and_period():
    routes_instance, fake, activities, periods = routes_with_registers()
    payload = {"actual_id": "x1", "activity_id": "missing", "period_id": "2026-09", "actual_units": "1"}
    status, _, body = routes_instance.handle(
        "POST", "/api/projects/p1/p6/activity-period-actuals", cookies={"cp_session": "s1"}, body=json.dumps(payload).encode()
    )
    assert status == 404
    assert json.loads(body)["code"] == "P6_ACTIVITY_PERIOD_ACTUAL_ACTIVITY_NOT_FOUND"
    assert fake.calls == []
    payload = {"actual_id": "x1", "activity_id": "a1", "period_id": "2026-10", "actual_units": "1"}
    status, _, body = routes_instance.handle(
        "POST", "/api/projects/p1/p6/activity-period-actuals", cookies={"cp_session": "s1"}, body=json.dumps(payload).encode()
    )
    assert status == 404
    assert json.loads(body)["code"] == "P6_ACTIVITY_PERIOD_ACTUAL_PERIOD_NOT_FOUND"
    assert fake.calls == []
    payload = {"actual_id": "x1", "activity_id": "a1", "period_id": "2026-09", "actual_units": "1"}
    status, _, _ = routes_instance.handle(
        "POST", "/api/projects/p1/p6/activity-period-actuals", cookies={"cp_session": "s1"}, body=json.dumps(payload).encode()
    )
    assert status == 200
    assert fake.calls[-1][0] == "create"
    assert activities.calls[-1][1] == "a1"
    assert periods.calls[-1][1] == "2026-09"


def test_activity_period_actual_http_maps_an_immutable_identity_to_409():
    routes_instance, _, _, _ = routes_with_registers()
    payload = {"actual_id": "immutable", "activity_id": "a1", "period_id": "2026-09", "actual_units": "4"}
    status, _, body = routes_instance.handle(
        "POST", "/api/projects/p1/p6/activity-period-actuals", cookies={"cp_session": "s1"}, body=json.dumps(payload).encode()
    )
    assert status == 409
    assert json.loads(body)["code"] == "IMMUTABLE_ACTIVITY_PERIOD_ACTUAL"
