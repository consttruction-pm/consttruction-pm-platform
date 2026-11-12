from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectLifecycleService,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.risk_api import RiskAPI
from construction_pm.risk_application import RiskApplicationService
from construction_pm.risk_persistence import SQLiteRiskStore

NOW = datetime(2026, 11, 12, 15, 0, tzinfo=timezone.utc)


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


def routes(roles: frozenset[str] = frozenset({"planner"})):
    session = AuthenticatedSession("s1", "u1", "t1", roles, NOW + timedelta(hours=1))
    service = ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    connection = sqlite3.connect(":memory:")
    store = SQLiteRiskStore(connection)
    store.initialize()
    api = RiskAPI(
        RiskApplicationService(
            store, default_project_policy(), SQLiteTransactionManager(connection)
        )
    )
    router = ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: NOW})(),
        risk_api=api,
    )
    return router


def _call(router, method: str, path: str, payload: dict | None = None, session: str = "s1"):
    body = b"" if payload is None else json.dumps(payload).encode()
    status, _, raw = router.handle(method, path, cookies={"cp_session": session}, body=body)
    return status, json.loads(raw) if raw else {}


def _risk(**overrides: object) -> dict[str, object]:
    payload = {
        "risk_id": "RK-1",
        "title": "Supplier lead time slips",
        "description": "Primary steel supplier may miss the framed date.",
        "category": "schedule",
        "status": "open",
        "probability": 3,
        "impact": 4,
        "response_strategy": "mitigate",
        "owner": "u-owner",
        "date_identified": "2026-11-01",
        "response_owner": "u-response",
        "response_due_date": "2026-12-01",
        "responsible_manager": "u-manager",
        "closure_note": None,
        "idempotency_key": "risk-key-1",
    }
    payload.update(overrides)
    return payload


def test_risk_http_lifecycle_filters_status_and_delete() -> None:
    router = routes()
    status, empty = _call(router, "GET", "/api/projects/p1/risks")
    assert status == 200, empty
    assert empty == {"contract_version": "p6-risk-api.v1", "risks": []}

    status, created = _call(router, "POST", "/api/projects/p1/risks", _risk())
    assert status == 200, created
    assert created["risk_id"] == "RK-1" and created["revision"] == 1
    assert created["score"] == 12 and created["exposure_level"] == "high"
    assert created["contract_version"] == "p6-risk-api.v1"

    status, listed = _call(
        router,
        "GET",
        "/api/projects/p1/risks?category=schedule&status=open&response_strategy=mitigate&exposure=high&search=supplier",
    )
    assert status == 200 and [item["risk_id"] for item in listed["risks"]] == ["RK-1"]

    status, read = _call(router, "GET", "/api/projects/p1/risks/RK-1")
    assert status == 200 and read["title"] == "Supplier lead time slips"

    status, updated = _call(
        router,
        "PATCH",
        "/api/projects/p1/risks/RK-1",
        _risk(status="mitigating", expected_revision=1, reason="Plan approved"),
    )
    assert status == 200 and updated["revision"] == 2
    assert updated["status"] == "mitigating"

    status, conflict = _call(
        router,
        "PATCH",
        "/api/projects/p1/risks/RK-1",
        _risk(status="monitoring", expected_revision=1),
    )
    assert status == 409 and conflict["code"] == "RISK_REVISION_CONFLICT"

    status, closed = _call(
        router,
        "PATCH",
        "/api/projects/p1/risks/RK-1",
        _risk(status="closed", closure_note="Delivered", expected_revision=2),
    )
    assert status == 200 and closed["status"] == "closed"

    status, history = _call(router, "GET", "/api/projects/p1/risks/RK-1/history")
    assert status == 200 and [event["event_type"] for event in history["events"]] == [
        "created",
        "status_changed",
        "status_changed",
    ]
    assert history["events"][1]["reason"] == "Plan approved"

    status, invalid_delete = _call(router, "DELETE", "/api/projects/p1/risks/RK-1")
    assert status == 400 and invalid_delete["code"] == "RISK_REQUEST_INVALID"
    status, deleted = _call(
        router, "DELETE", "/api/projects/p1/risks/RK-1?expected_revision=3"
    )
    assert status == 200 and deleted["deleted"] is True
    status, missing = _call(router, "GET", "/api/projects/p1/risks/RK-1")
    assert status == 404 and missing["code"] == "RISK_NOT_FOUND"


def test_risk_http_rejects_invalid_payloads_and_unknown_routes() -> None:
    router = routes()
    status, invalid = _call(
        router,
        "POST",
        "/api/projects/p1/risks",
        _risk(probability=6),
    )
    assert status == 400 and invalid["code"] == "INVALID_RISK_PROBABILITY"
    status, invalid = _call(
        router, "POST", "/api/projects/p1/risks", _risk(status="closed")
    )
    assert status == 400 and invalid["code"] == "RISK_CLOSURE_NOTE_REQUIRED"
    status, invalid = _call(
        router, "POST", "/api/projects/p1/risks", _risk(category="bogus")
    )
    assert status == 400 and invalid["code"] == "INVALID_RISK_CATEGORY"
    status, invalid = _call(
        router, "POST", "/api/projects/p1/risks", _risk(probability="3")
    )
    assert status == 400 and invalid["code"] == "INVALID_RISK_PROBABILITY"
    _call(router, "POST", "/api/projects/p1/risks", _risk())
    status, mismatch = _call(
        router,
        "PATCH",
        "/api/projects/p1/risks/RK-404",
        _risk(risk_id="RK-405", expected_revision=1),
    )
    assert status == 400 and mismatch["code"] == "RISK_REQUEST_INVALID"
    status, unknown = _call(router, "GET", "/api/projects/p1/risks/RK-1/unknown")
    assert status == 400 and unknown["code"] == "RISK_REQUEST_INVALID"
    status, missing = _call(router, "GET", "/api/projects/p1/risks/RK-404")
    assert status == 404 and missing["code"] == "RISK_NOT_FOUND"
    status, cross = _call(router, "GET", "/api/projects/p2/risks")
    assert status == 403


def test_risk_http_viewer_can_read_but_not_write() -> None:
    viewer = routes(roles=frozenset({"viewer"}))
    status, empty = _call(viewer, "GET", "/api/projects/p1/risks")
    assert status == 200 and empty["risks"] == []
    status, denied = _call(viewer, "POST", "/api/projects/p1/risks", _risk())
    assert status == 403 and denied["code"] == "RISK_PERMISSION_DENIED"
