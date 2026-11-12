from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import AuthenticatedSession, ProjectSummary
from construction_pm.application.project_lifecycle import ProjectLifecycleService
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.budget_api import BudgetAPI
from construction_pm.budget_application import BudgetApplicationService
from construction_pm.budget_persistence import SQLiteBudgetStore
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
    store: SQLiteBudgetStore | None = None,
) -> ProjectLifecycleHttpRoutes:
    session = AuthenticatedSession("s1", "u1", "t1", roles, NOW + timedelta(hours=1))
    service = ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    if store is None:
        connection = sqlite3.connect(":memory:")
        store = SQLiteBudgetStore(connection)
        store.initialize()
    api = BudgetAPI(
        BudgetApplicationService(
            store, default_project_policy(), SQLiteTransactionManager(store.connection)
        )
    )
    return ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: NOW})(),
        budget_api=api,
    )


def _call(router, method: str, path: str, payload: dict | None = None, session: str = "s1"):
    body = b"" if payload is None else json.dumps(payload).encode()
    status, _, raw = router.handle(
        method, path, cookies={"cp_session": session}, body=body
    )
    return status, json.loads(raw) if raw else {}


def _line(**overrides: object) -> dict[str, object]:
    payload = {
        "budget_line_id": "BL-1",
        "description": "Concrete works",
        "currency": "USD",
        "original_amount": "1000.00",
        "cost_account_id": "CA-1",
        "period_id": "2026",
        "idempotency_key": "line-key-1",
    }
    payload.update(overrides)
    return payload


def _change(**overrides: object) -> dict[str, object]:
    payload = {
        "change_id": "BC-1",
        "amount": "-100.00",
        "reason": "Reduced scope",
    }
    payload.update(overrides)
    return payload


def _funding(**overrides: object) -> dict[str, object]:
    payload = {
        "funding_id": "FS-1",
        "name": "Owner equity",
        "source_type": "internal",
        "currency": "USD",
        "amount": "400.00",
        "idempotency_key": "funding-key-1",
    }
    payload.update(overrides)
    return payload


def test_budget_http_line_lifecycle_and_filtering() -> None:
    router = routes()
    status, created = _call(router, "POST", "/api/projects/p1/budget/lines", _line())
    assert status == 200, created
    assert created["budget_line_id"] == "BL-1"
    assert created["original_amount"] == "1000.00"
    assert created["contract_version"] == "p6-budget-api.v1"

    status, read = _call(router, "GET", "/api/projects/p1/budget/lines/BL-1")
    assert status == 200 and read["revision"] == 1

    status, listed = _call(router, "GET", "/api/projects/p1/budget/lines?search=concrete")
    assert status == 200, listed
    assert [item["budget_line_id"] for item in listed["budget_lines"]] == ["BL-1"]
    status, missing = _call(router, "GET", "/api/projects/p1/budget/lines?currency=EUR")
    assert status == 200 and missing["budget_lines"] == []

    status, updated = _call(
        router,
        "PATCH",
        "/api/projects/p1/budget/lines/BL-1",
        _line(description="Concrete works revised", expected_revision=1),
    )
    assert status == 200, updated
    assert updated["revision"] == 2 and updated["description"] == "Concrete works revised"

    status, conflict = _call(
        router,
        "PATCH",
        "/api/projects/p1/budget/lines/BL-1",
        _line(description="Stale", expected_revision=1),
    )
    assert status == 409 and conflict["code"] == "BUDGET_REVISION_CONFLICT"

    status, history = _call(router, "GET", "/api/projects/p1/budget/lines/BL-1/history")
    assert status == 200, history
    assert [event["event_type"] for event in history["events"]] == ["created", "updated"]


def test_budget_http_change_approval_updates_summary() -> None:
    connection = sqlite3.connect(":memory:")
    store = SQLiteBudgetStore(connection)
    store.initialize()
    router = routes(store=store)
    _call(router, "POST", "/api/projects/p1/budget/lines", _line())
    status, change = _call(
        router, "POST", "/api/projects/p1/budget/lines/BL-1/changes", _change()
    )
    assert status == 200, change
    assert change["status"] == "pending"

    status, pending_summary = _call(router, "GET", "/api/projects/p1/budget/summary")
    assert status == 200, pending_summary
    assert pending_summary["currencies"][0]["current_budget"] == "1000.00"
    assert pending_summary["currencies"][0]["pending_changes"] == "-100.00"

    status, denied = _call(
        router,
        "POST",
        "/api/projects/p1/budget/changes/BC-1/status",
        {"status": "approved", "expected_revision": 1},
    )
    assert status == 403 and denied["code"] == "BUDGET_APPROVAL_REQUIRES_ADMIN"

    admin = routes(roles=frozenset({"project_admin"}), store=store)
    status, approved = _call(
        admin,
        "POST",
        "/api/projects/p1/budget/changes/BC-1/status",
        {"status": "approved", "expected_revision": 1, "reason": "change board"},
    )
    assert status == 200, approved
    assert approved["status"] == "approved" and approved["revision"] == 2

    status, changes = _call(admin, "GET", "/api/projects/p1/budget/lines/BL-1/changes")
    assert status == 200 and changes["changes"][0]["status"] == "approved"


def test_budget_http_funding_create_update_and_revision_conflict() -> None:
    router = routes()
    status, created = _call(router, "POST", "/api/projects/p1/budget/funding", _funding())
    assert status == 200, created
    assert created["amount"] == "400.00"

    status, updated = _call(
        router,
        "PATCH",
        "/api/projects/p1/budget/funding/FS-1",
        _funding(amount="450.00", expected_revision=1),
    )
    assert status == 200, updated
    assert updated["revision"] == 2 and updated["amount"] == "450.00"

    status, conflict = _call(
        router,
        "PATCH",
        "/api/projects/p1/budget/funding/FS-1",
        _funding(amount="1.00", expected_revision=1),
    )
    assert status == 409 and conflict["code"] == "BUDGET_REVISION_CONFLICT"

    status, listed = _call(router, "GET", "/api/projects/p1/budget/funding")
    assert status == 200 and len(listed["funding_sources"]) == 1


def test_budget_http_rejects_invalid_amounts_and_unknown_routes() -> None:
    router = routes()
    status, invalid = _call(
        router, "POST", "/api/projects/p1/budget/lines", _line(original_amount="12.345")
    )
    assert status == 400 and invalid["code"] == "BUDGET_REQUEST_INVALID"
    status, invalid = _call(
        router, "POST", "/api/projects/p1/budget/lines", _line(original_amount=100.0)
    )
    assert status == 400 and invalid["code"] == "BUDGET_REQUEST_INVALID"
    status, unknown = _call(router, "GET", "/api/projects/p1/budget/unknown")
    assert status == 400 and unknown["code"] == "BUDGET_REQUEST_INVALID"
    status, missing = _call(router, "GET", "/api/projects/p1/budget/lines/BL-404")
    assert status == 404 and missing["code"] == "BUDGET_LINE_NOT_FOUND"
    status, cross = _call(router, "GET", "/api/projects/p2/budget/lines")
    assert status == 403


def test_viewer_can_read_but_not_write() -> None:
    viewer = routes(roles=frozenset({"viewer"}))
    status, empty = _call(viewer, "GET", "/api/projects/p1/budget/lines")
    assert status == 200 and empty["budget_lines"] == []
    status, denied = _call(viewer, "POST", "/api/projects/p1/budget/lines", _line())
    assert status == 403 and denied["code"] == "BUDGET_PERMISSION_DENIED"
