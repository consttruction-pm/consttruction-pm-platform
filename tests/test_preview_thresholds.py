from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

PROJECT = "preview-rps-01"
BASE = f"/api/projects/{PROJECT}"


def _request(app, method: str, path: str, *, body: dict | None = None, cookie: str | None = None):
    raw = b"" if body is None else json.dumps(body).encode()
    environ: dict[str, object] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path.split("?", 1)[0],
        "QUERY_STRING": path.split("?", 1)[1] if "?" in path else "",
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": BytesIO(raw),
    }
    if raw:
        environ["CONTENT_TYPE"] = "application/json"
    if cookie is not None:
        environ["HTTP_COOKIE"] = f"cp_session={cookie}"
    captured: dict[str, object] = {}

    def start_response(status, response_headers) -> None:
        captured["status"] = status

    chunks = b"".join(app(environ, start_response))
    return int(str(captured["status"]).split(" ", 1)[0]), chunks


def _threshold(**overrides):
    payload = {
        "threshold_id": "TH-COST-1",
        "name": "Expense ceiling",
        "monitoring_subject": "cost",
        "parameter": "expense_actual_total",
        "currency": "USD",
        "lower_threshold": None,
        "upper_threshold": "100",
        "warning_level": "10",
        "issue_level": "50",
        "responsible_manager": "preview-planner",
        "status": "active",
        "idempotency_key": "idem-threshold-1",
    }
    payload.update(overrides)
    return payload


def _expense(**overrides):
    payload = {
        "expense_id": "EX-THRESHOLD-1",
        "name": "Concrete delivery",
        "category": "material",
        "currency": "USD",
        "expense_date": "2026-11-01",
        "accrual_date": "2026-11-02",
        "planned_amount": "900.00",
        "actual_amount": "900.00",
        "remaining_amount": "0.00",
        "idempotency_key": "idem-expense-threshold-1",
    }
    payload.update(overrides)
    return payload


def test_preview_threshold_monitoring_raises_a_real_issue(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])

        status, body = _request(
            runtime.app, "GET", f"{BASE}/thresholds", cookie=planner.session_id
        )
        assert status == 200, body[:300]
        assert json.loads(body) == {
            "contract_version": "p6-threshold-api.v1",
            "thresholds": [],
        }

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/thresholds",
            body=_threshold(),
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        created = json.loads(body)
        assert created["revision"] == 1 and created["upper_threshold"] == "100"

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/thresholds/TH-COST-1/monitor",
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        first = json.loads(body)
        assert first["run"]["level"] == "normal"
        assert first["run"]["observed_value"] == "0"

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/cost/expenses",
            body=_expense(),
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/thresholds/TH-COST-1/monitor",
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        breached = json.loads(body)
        assert breached["run"]["level"] == "issue"
        assert breached["run"]["observed_value"] == "900"
        issue_id = breached["run"]["generated_issue_id"]
        assert issue_id == "THR-TH-COST-1-R2"

        status, body = _request(
            runtime.app, "GET", f"{BASE}/p6/issues/{issue_id}", cookie=planner.session_id
        )
        assert status == 200, body[:300]
        issue = json.loads(body)["issue"]
        assert issue["issue_id"] == issue_id
        assert issue["issue_type"] == "cost"
        assert issue["status"] == "open" and issue["priority"] == "high"

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/thresholds/TH-COST-1/monitor",
            cookie=planner.session_id,
        )
        repeated = json.loads(body)
        assert repeated["run"]["level"] == "issue"
        assert repeated["run"]["generated_issue_id"] is None

        status, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/thresholds/TH-COST-1/runs",
            cookie=viewer.session_id,
        )
        assert status == 200, body[:300]
        assert [run["level"] for run in json.loads(body)["runs"]] == [
            "normal",
            "issue",
            "issue",
        ]

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/thresholds/TH-COST-1/monitor",
            cookie=viewer.session_id,
        )
        assert status == 403, body[:300]

        status, body = _request(
            runtime.app,
            "PATCH",
            f"{BASE}/thresholds/TH-COST-1",
            body=_threshold(upper_threshold="2000", expected_revision=1),
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        assert json.loads(body)["revision"] == 2

        status, body = _request(
            runtime.app,
            "DELETE",
            f"{BASE}/thresholds/TH-COST-1?expected_revision=2",
            cookie=planner.session_id,
        )
        assert status == 200 and json.loads(body)["deleted"] is True
        status, body = _request(
            runtime.app, "GET", f"{BASE}/thresholds/TH-COST-1", cookie=viewer.session_id
        )
        assert status == 404, body[:300]

        reopened = open_preview_runtime(tmp_path / "preview.sqlite3")
        try:
            reader = reopened.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
            status, body = _request(
                reopened.app, "GET", f"{BASE}/thresholds", cookie=reader.session_id
            )
            assert status == 200 and json.loads(body)["thresholds"] == []
        finally:
            reopened.close()
    finally:
        runtime.close()
