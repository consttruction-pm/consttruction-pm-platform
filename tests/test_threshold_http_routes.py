from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectLifecycleService,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.threshold_api import ThresholdAPI
from construction_pm.threshold_application import ThresholdApplicationService
from construction_pm.threshold_persistence import SQLiteThresholdStore

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


class Metrics:
    def __init__(self, *values: str) -> None:
        self.values = [Decimal(value) for value in values]

    def observe(self, **_kwargs: object) -> Decimal:
        return self.values.pop(0)


class Writer:
    def __init__(self) -> None:
        self.ids: list[str] = []

    def __call__(self, issue, *, context, occurred_at) -> str:
        self.ids.append(issue.issue_id)
        return issue.issue_id


def routes(roles: frozenset[str] = frozenset({"planner"}), *, metrics: Metrics | None = None):
    session = AuthenticatedSession("s1", "u1", "t1", roles, NOW + timedelta(hours=1))
    service = ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    connection = sqlite3.connect(":memory:")
    store = SQLiteThresholdStore(connection)
    store.initialize()
    writer = Writer()
    api = ThresholdAPI(
        ThresholdApplicationService(
            store,
            default_project_policy(),
            SQLiteTransactionManager(connection),
            metrics or Metrics("6", "8"),
            writer,
        )
    )
    router = ProjectLifecycleHttpRoutes(
        ProjectLifecycleAPI(service),
        clock=type("Clock", (), {"now": lambda self: NOW})(),
        threshold_api=api,
    )
    return router, writer


def _call(router, method: str, path: str, payload: dict | None = None, session: str = "s1"):
    body = b"" if payload is None else json.dumps(payload).encode()
    status, _, raw = router.handle(method, path, cookies={"cp_session": session}, body=body)
    return status, json.loads(raw) if raw else {}


def _threshold(**overrides: object) -> dict[str, object]:
    payload = {
        "threshold_id": "TH-1",
        "name": "Open issue watch",
        "monitoring_subject": "quality",
        "parameter": "open_issue_count",
        "currency": None,
        "lower_threshold": None,
        "upper_threshold": "5",
        "warning_level": "1",
        "issue_level": "3",
        "responsible_manager": "u-manager",
        "status": "active",
        "idempotency_key": "threshold-key-1",
    }
    payload.update(overrides)
    return payload


def test_threshold_http_lifecycle_filters_monitor_and_delete() -> None:
    router, writer = routes()
    status, empty = _call(router, "GET", "/api/projects/p1/thresholds")
    assert status == 200, empty
    assert empty == {"contract_version": "p6-threshold-api.v1", "thresholds": []}

    status, created = _call(router, "POST", "/api/projects/p1/thresholds", _threshold())
    assert status == 200, created
    assert created["threshold_id"] == "TH-1" and created["revision"] == 1
    assert created["contract_version"] == "p6-threshold-api.v1"

    status, listed = _call(
        router,
        "GET",
        "/api/projects/p1/thresholds?parameter=open_issue_count&status=active&search=issue",
    )
    assert status == 200 and [item["threshold_id"] for item in listed["thresholds"]] == [
        "TH-1"
    ]

    status, read = _call(router, "GET", "/api/projects/p1/thresholds/TH-1")
    assert status == 200 and read["name"] == "Open issue watch"

    status, updated = _call(
        router,
        "PATCH",
        "/api/projects/p1/thresholds/TH-1",
        _threshold(name="Open issue watch revised", expected_revision=1),
    )
    assert status == 200 and updated["revision"] == 2

    status, conflict = _call(
        router,
        "PATCH",
        "/api/projects/p1/thresholds/TH-1",
        _threshold(name="Stale", expected_revision=1),
    )
    assert status == 409 and conflict["code"] == "THRESHOLD_REVISION_CONFLICT"

    status, warning = _call(router, "POST", "/api/projects/p1/thresholds/TH-1/monitor")
    assert status == 200, warning
    assert warning["run"]["level"] == "warning" and warning["run"]["observed_value"] == "6"

    status, issue = _call(router, "POST", "/api/projects/p1/thresholds/TH-1/monitor")
    assert status == 200, issue
    assert issue["run"]["level"] == "issue"
    assert issue["run"]["generated_issue_id"] == "THR-TH-1-R2"
    assert writer.ids == ["THR-TH-1-R2"]

    status, runs = _call(router, "GET", "/api/projects/p1/thresholds/TH-1/runs")
    assert status == 200 and [run["level"] for run in runs["runs"]] == ["warning", "issue"]

    status, history = _call(router, "GET", "/api/projects/p1/thresholds/TH-1/history")
    assert status == 200 and [event["event_type"] for event in history["events"]] == [
        "created",
        "updated",
    ]

    status, invalid_delete = _call(router, "DELETE", "/api/projects/p1/thresholds/TH-1")
    assert status == 400 and invalid_delete["code"] == "THRESHOLD_REQUEST_INVALID"
    status, deleted = _call(
        router, "DELETE", "/api/projects/p1/thresholds/TH-1?expected_revision=2"
    )
    assert status == 200 and deleted["deleted"] is True
    status, missing = _call(router, "GET", "/api/projects/p1/thresholds/TH-1")
    assert status == 404 and missing["code"] == "THRESHOLD_NOT_FOUND"


def test_threshold_http_rejects_invalid_payloads_and_unknown_routes() -> None:
    router, _ = routes()
    status, invalid = _call(
        router,
        "POST",
        "/api/projects/p1/thresholds",
        _threshold(issue_level="0.5", warning_level="1"),
    )
    assert status == 400 and invalid["code"] == "INVALID_THRESHOLD_LEVELS"
    status, invalid = _call(
        router, "POST", "/api/projects/p1/thresholds", _threshold(upper_threshold="x")
    )
    assert status == 400 and invalid["code"] == "THRESHOLD_REQUEST_INVALID"
    status, invalid = _call(
        router,
        "POST",
        "/api/projects/p1/thresholds",
        _threshold(parameter="expense_actual_total", currency=None),
    )
    assert status == 400 and invalid["code"] == "THRESHOLD_CURRENCY_REQUIRED"
    status, mismatch = _call(
        router,
        "PATCH",
        "/api/projects/p1/thresholds/TH-404",
        _threshold(threshold_id="TH-405", expected_revision=1),
    )
    assert status == 400 and mismatch["code"] == "THRESHOLD_REQUEST_INVALID"
    status, unknown = _call(router, "GET", "/api/projects/p1/thresholds/TH-1/unknown")
    assert status == 400 and unknown["code"] == "THRESHOLD_REQUEST_INVALID"
    status, missing = _call(router, "GET", "/api/projects/p1/thresholds/TH-404")
    assert status == 404 and missing["code"] == "THRESHOLD_NOT_FOUND"
    status, cross = _call(router, "GET", "/api/projects/p2/thresholds")
    assert status == 403


def test_threshold_http_viewer_can_read_but_not_write() -> None:
    viewer, _ = routes(roles=frozenset({"viewer"}))
    status, empty = _call(viewer, "GET", "/api/projects/p1/thresholds")
    assert status == 200 and empty["thresholds"] == []
    status, denied = _call(viewer, "POST", "/api/projects/p1/thresholds", _threshold())
    assert status == 403 and denied["code"] == "THRESHOLD_PERMISSION_DENIED"
