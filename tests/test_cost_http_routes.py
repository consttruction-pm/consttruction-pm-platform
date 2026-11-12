from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession, ProjectSummary
from construction_pm.application.project_lifecycle import ProjectLifecycleService
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.cost_api import CostAPI
from construction_pm.cost_application import CostApplicationService
from construction_pm.cost_persistence import SQLiteCostStore
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes

NOW = datetime(2026, 11, 12, 13, 0, tzinfo=timezone.utc)


class Sessions:
    def __init__(self, session: AuthenticatedSession) -> None:
        self.session = session

    def get(self, session_id: str):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def list_for_user(self, tenant_id: str, user_id: str):
        return (ProjectSummary("p1", tenant_id, "Project One", 2),)

    def get_for_user(self, tenant_id: str, project_id: str, user_id: str):
        if project_id != "p1":
            return None
        return ProjectSummary("p1", tenant_id, "Project One", 2)

    def create_for_user(self, tenant_id: str, user_id: str, project_id: str, name: str, **_):
        return ProjectSummary(project_id, tenant_id, name, 0)


def routes(
    roles: frozenset[str] = frozenset({"planner"}),
    *,
    store: SQLiteCostStore | None = None,
) -> ProjectLifecycleHttpRoutes:
    session = AuthenticatedSession("s1", "u1", "t1", roles, NOW + timedelta(hours=1))
    service = ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    if store is None:
        connection = sqlite3.connect(":memory:")
        store = SQLiteCostStore(connection)
        store.initialize()
    api = CostAPI(
        CostApplicationService(
            store, default_project_policy(), SQLiteTransactionManager(store.connection)
        )
    )
    return ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: NOW})(),
        cost_api=api,
    )


def _call(router, method: str, path: str, payload: dict | None = None, session: str = "s1"):
    body = b"" if payload is None else json.dumps(payload).encode()
    status, _, raw = router.handle(method, path, cookies={"cp_session": session}, body=body)
    return status, json.loads(raw) if raw else {}


def _account(**overrides: object) -> dict[str, object]:
    payload = {
        "account_id": "CA-1",
        "name": "Direct costs",
        "parent_account_id": None,
        "description": "Direct project costs",
        "is_default": False,
        "idempotency_key": "account-key-1",
    }
    payload.update(overrides)
    return payload


def _expense(**overrides: object) -> dict[str, object]:
    payload = {
        "expense_id": "EX-1",
        "name": "Concrete delivery",
        "category": "material",
        "currency": "USD",
        "activity_id": "A-1000",
        "wbs_id": "WBS-1",
        "cost_account_id": "CA-1",
        "expense_date": "2026-11-01",
        "accrual_date": "2026-11-02",
        "planned_amount": "1000.00",
        "actual_amount": "900.00",
        "remaining_amount": "100.00",
        "note": "Batch 4",
        "idempotency_key": "expense-key-1",
    }
    payload.update(overrides)
    return payload


def test_cost_http_account_lifecycle_default_copy_and_history() -> None:
    router = routes()
    status, created = _call(router, "POST", "/api/projects/p1/cost/accounts", _account())
    assert status == 200, created
    assert created["account_id"] == "CA-1" and created["revision"] == 1
    assert created["contract_version"] == "p6-cost-api.v1"

    status, read = _call(router, "GET", "/api/projects/p1/cost/accounts/CA-1")
    assert status == 200 and read["description"] == "Direct project costs"

    status, updated = _call(
        router,
        "PATCH",
        "/api/projects/p1/cost/accounts/CA-1",
        _account(name="Direct project costs", expected_revision=1),
    )
    assert status == 200 and updated["revision"] == 2

    status, conflict = _call(
        router,
        "PATCH",
        "/api/projects/p1/cost/accounts/CA-1",
        _account(name="Stale", expected_revision=1),
    )
    assert status == 409 and conflict["code"] == "COST_REVISION_CONFLICT"

    status, defaulted = _call(
        router,
        "POST",
        "/api/projects/p1/cost/accounts/CA-1/default",
        {"expected_revision": 2},
    )
    assert status == 200 and defaulted["cost_accounts"][0]["is_default"] is True

    status, copied = _call(
        router,
        "POST",
        "/api/projects/p1/cost/accounts/CA-1/copy",
        {"account_id": "CA-2", "name": "Direct costs copy", "idempotency_key": "copy-1"},
    )
    assert status == 200 and copied["account_id"] == "CA-2"
    assert copied["description"] == "Direct project costs"

    status, history = _call(router, "GET", "/api/projects/p1/cost/accounts/CA-1/history")
    assert status == 200, history
    assert [event["event_type"] for event in history["events"]] == [
        "created",
        "updated",
        "default_changed",
    ]

    status, deleted = _call(router, "DELETE", "/api/projects/p1/cost/accounts/CA-2")
    assert status == 400 and deleted["code"] == "COST_REQUEST_INVALID"
    status, deleted = _call(
        router,
        "DELETE",
        "/api/projects/p1/cost/accounts/CA-2?expected_revision=1",
    )
    assert status == 200 and deleted["deleted"] is True
    status, missing = _call(router, "GET", "/api/projects/p1/cost/accounts/CA-2")
    assert status == 404 and missing["code"] == "COST_ACCOUNT_NOT_FOUND"


def test_cost_http_expense_lifecycle_filters_summary_and_delete() -> None:
    router = routes()
    _call(router, "POST", "/api/projects/p1/cost/accounts", _account())
    status, created = _call(router, "POST", "/api/projects/p1/cost/expenses", _expense())
    assert status == 200, created
    assert created["planned_amount"] == "1000.00" and created["revision"] == 1

    status, listed = _call(
        router,
        "GET",
        "/api/projects/p1/cost/expenses?category=material&cost_account_id=CA-1&search=concrete",
    )
    assert status == 200 and [item["expense_id"] for item in listed["expenses"]] == ["EX-1"]

    status, updated = _call(
        router,
        "PATCH",
        "/api/projects/p1/cost/expenses/EX-1",
        _expense(actual_amount="1000.00", expected_revision=1),
    )
    assert status == 200 and updated["actual_amount"] == "1000.00" and updated["revision"] == 2

    status, conflict = _call(
        router,
        "PATCH",
        "/api/projects/p1/cost/expenses/EX-1",
        _expense(actual_amount="1.00", expected_revision=1),
    )
    assert status == 409 and conflict["code"] == "COST_REVISION_CONFLICT"

    status, summary = _call(router, "GET", "/api/projects/p1/cost/summary")
    assert status == 200, summary
    assert summary["currencies"] == [
        {
            "currency": "USD",
            "planned_amount": "1000.00",
            "actual_amount": "1000.00",
            "remaining_amount": "100.00",
            "expense_count": 1,
        }
    ]

    status, history = _call(router, "GET", "/api/projects/p1/cost/expenses/EX-1/history")
    assert status == 200 and [event["event_type"] for event in history["events"]] == [
        "created",
        "updated",
    ]

    status, deleted = _call(
        router,
        "DELETE",
        "/api/projects/p1/cost/expenses/EX-1",
        {"expected_revision": 2, "reason": "duplicate entry"},
    )
    assert status == 200 and deleted["deleted"] is True
    status, missing = _call(router, "GET", "/api/projects/p1/cost/expenses/EX-1")
    assert status == 404 and missing["code"] == "EXPENSE_NOT_FOUND"


def test_cost_http_rejects_invalid_payloads_and_unknown_routes() -> None:
    router = routes()
    status, invalid = _call(
        router, "POST", "/api/projects/p1/cost/expenses", _expense(planned_amount="12.345")
    )
    assert status == 400 and invalid["code"] == "COST_REQUEST_INVALID"
    status, invalid = _call(
        router, "POST", "/api/projects/p1/cost/expenses", _expense(category="travel")
    )
    assert status == 400 and invalid["code"] == "INVALID_EXPENSE_CATEGORY"
    status, unknown = _call(router, "GET", "/api/projects/p1/cost/unknown")
    assert status == 400 and unknown["code"] == "COST_REQUEST_INVALID"
    status, missing = _call(router, "GET", "/api/projects/p1/cost/accounts/CA-404")
    assert status == 404 and missing["code"] == "COST_ACCOUNT_NOT_FOUND"
    status, cross = _call(router, "GET", "/api/projects/p2/cost/accounts")
    assert status == 403


def test_cost_http_viewer_can_read_but_not_write() -> None:
    viewer = routes(roles=frozenset({"viewer"}))
    status, empty = _call(viewer, "GET", "/api/projects/p1/cost/expenses")
    assert status == 200 and empty["expenses"] == []
    status, denied = _call(viewer, "POST", "/api/projects/p1/cost/expenses", _expense())
    assert status == 403 and denied["code"] == "COST_PERMISSION_DENIED"
