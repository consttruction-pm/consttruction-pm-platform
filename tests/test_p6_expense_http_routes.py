from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession, ProjectSummary
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.models import BackendScope
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.p6_expense_api import P6_EXPENSE_API_VERSION
from construction_pm.p6_expense_repository import P6ExpensePersistenceError


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


class FakeExpenseAPI:
    def __init__(self):
        self.calls = []

    def create(self, expense, *, auth_context):
        self.calls.append(("create", expense, auth_context))
        return {"contract_version": P6_EXPENSE_API_VERSION, "expense": {"expense_id": expense.expense_id}}

    def get(self, scope, expense_id, *, auth_context):
        self.calls.append(("get", scope, expense_id, auth_context))
        return None if expense_id == "missing" else {
            "contract_version": P6_EXPENSE_API_VERSION,
            "expense": {"expense_id": expense_id},
        }

    def list(self, scope, *, activity_id=None, wbs_id=None, auth_context):
        self.calls.append(("list", scope, activity_id, wbs_id, auth_context))
        return ({"contract_version": P6_EXPENSE_API_VERSION, "expense": {"expense_id": "e-1"}},)


def routes(roles=frozenset({"project_admin"}), expense_api=None):
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    session = AuthenticatedSession("s1", "u1", "t1", roles, now + timedelta(hours=1))
    service = __import__("construction_pm.application.project_lifecycle", fromlist=["ProjectLifecycleService"]).ProjectLifecycleService(
        Sessions(session), Projects(), default_project_policy()
    )
    fake = FakeExpenseAPI() if expense_api is None else expense_api
    return ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: now})(),
        p6_expense_api=fake,
    ), fake


def test_p6_expense_http_create_preserves_scope_and_decimal_values():
    r, fake = routes()
    payload = {
        "expense_id": "e-1", "name": "Temporary facilities", "category": "SITE",
        "activity_id": "a-1", "wbs_id": "wbs-1", "expense_date": "2026-09-15",
        "planned_cost": "1200.50", "actual_cost": "400.25", "remaining_cost": "800.25",
        "currency": "USD", "note": "stored period expense",
    }
    status, _, body = r.handle("POST", "/api/projects/p1/p6/expenses",
                                cookies={"cp_session": "s1"}, body=json.dumps(payload).encode())
    assert status == 200
    assert json.loads(body)["contract_version"] == P6_EXPENSE_API_VERSION
    call = fake.calls[-1]
    assert call[0] == "create"
    assert call[1].scope == BackendScope("t1", "p1", 2)
    assert call[1].planned_cost == Decimal("1200.50")


def test_p6_expense_http_list_and_get_and_cross_scope_rejection():
    r, fake = routes()
    status, _, body = r.handle("GET", "/api/projects/p1/p6/expenses",
                                cookies={"cp_session": "s1"},
                                body=json.dumps({"activity_id": "a-1"}).encode())
    assert status == 200
    assert json.loads(body)["expenses"][0]["expense"]["expense_id"] == "e-1"

    status, _, body = r.handle("GET", "/api/projects/p1/p6/expenses/e-1", cookies={"cp_session": "s1"})
    assert status == 200
    assert json.loads(body)["expense"]["expense_id"] == "e-1"

    status, _, _ = r.handle("GET", "/api/projects/other/p6/expenses/e-1", cookies={"cp_session": "s1"})
    assert status == 403


def test_p6_expense_http_list_reads_query_filters_and_accepts_a_bodyless_get():
    r, fake = routes()
    status, _, body = r.handle(
        "GET", "/api/projects/p1/p6/expenses?activity_id=a-1&wbs_id=wbs-1",
        cookies={"cp_session": "s1"},
    )
    assert status == 200
    assert json.loads(body)["expenses"][0]["expense"]["expense_id"] == "e-1"
    call = fake.calls[-1]
    assert call[0] == "list"
    assert call[2] == "a-1"
    assert call[3] == "wbs-1"


def test_p6_expense_http_viewer_can_read_but_cannot_record_cost():
    r, fake = routes(roles=frozenset({"viewer"}))
    status, _, body = r.handle(
        "GET", "/api/projects/p1/p6/expenses", cookies={"cp_session": "s1"}
    )
    assert status == 200, body

    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/expenses",
        cookies={"cp_session": "s1"},
        body=json.dumps({"expense_id": "e-2", "name": "Crane", "category": "SITE"}).encode(),
    )
    assert status == 403, body
    assert json.loads(body)["code"] == "AUTHORIZATION_PERMISSION_DENIED"
    assert all(call[0] != "create" for call in fake.calls)


class _ConflictingExpenseAPI(FakeExpenseAPI):
    def __init__(self, code):
        super().__init__()
        self.code = code

    def create(self, expense, *, auth_context):
        raise P6ExpensePersistenceError(self.code)


def test_p6_expense_http_immutable_replay_is_a_conflict_not_an_overwrite():
    r, _ = routes(expense_api=_ConflictingExpenseAPI("IMMUTABLE_EXPENSE"))
    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/expenses",
        cookies={"cp_session": "s1"},
        body=json.dumps({"expense_id": "e-1", "name": "Changed", "category": "SITE"}).encode(),
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "IMMUTABLE_EXPENSE"


def test_p6_expense_http_revision_conflict_is_a_conflict():
    r, _ = routes(expense_api=_ConflictingExpenseAPI("REVISION_CONFLICT"))
    status, _, body = r.handle(
        "GET", "/api/projects/p1/p6/expenses/e-1", cookies={"cp_session": "s1"}
    )
    assert status == 200
    status, _, body = r.handle(
        "POST",
        "/api/projects/p1/p6/expenses",
        cookies={"cp_session": "s1"},
        body=json.dumps({"expense_id": "e-1", "name": "x", "category": "SITE"}).encode(),
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "REVISION_CONFLICT"
