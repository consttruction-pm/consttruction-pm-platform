from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

PROJECT = "preview-rps-01"
BUDGET = f"/api/projects/{PROJECT}/budget"


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


def _line(**overrides):
    payload = {
        "budget_line_id": "BL-PREVIEW-1",
        "description": "Concrete works",
        "currency": "USD",
        "original_amount": "1000.00",
        "cost_account_id": "CA-1",
        "period_id": "2026",
        "idempotency_key": "idem-line-1",
    }
    payload.update(overrides)
    return payload


def test_preview_budget_persists_lines_changes_funding_and_summary(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])

        status, body = _request(runtime.app, "GET", f"{BUDGET}/lines", cookie=planner.session_id)
        assert status == 200, body[:300]
        assert json.loads(body) == {"contract_version": "p6-budget-api.v1", "budget_lines": []}

        status, body = _request(
            runtime.app, "POST", f"{BUDGET}/lines", body=_line(), cookie=planner.session_id
        )
        assert status == 200, body[:300]
        created = json.loads(body)
        assert created["revision"] == 1 and created["original_amount"] == "1000.00"

        status, body = _request(
            runtime.app,
            "POST",
            f"{BUDGET}/lines/BL-PREVIEW-1/changes",
            body={"change_id": "BC-PREVIEW-1", "amount": "-100.00", "reason": "Reduced scope"},
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]

        status, body = _request(
            runtime.app,
            "POST",
            f"{BUDGET}/changes/BC-PREVIEW-1/status",
            body={"status": "approved", "expected_revision": 1},
            cookie=planner.session_id,
        )
        assert status == 403, body[:300]
        assert json.loads(body)["code"] == "BUDGET_APPROVAL_REQUIRES_ADMIN"

        status, body = _request(
            runtime.app,
            "POST",
            f"{BUDGET}/changes/BC-PREVIEW-1/status",
            body={"status": "approved", "expected_revision": 1, "reason": "change board"},
            cookie=admin.session_id,
        )
        assert status == 200, body[:300]
        assert json.loads(body)["status"] == "approved"

        status, body = _request(
            runtime.app,
            "POST",
            f"{BUDGET}/funding",
            body={
                "funding_id": "FS-PREVIEW-1",
                "name": "Owner equity",
                "source_type": "internal",
                "currency": "USD",
                "amount": "400.00",
                "idempotency_key": "idem-funding-1",
            },
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]

        status, body = _request(runtime.app, "GET", f"{BUDGET}/summary", cookie=viewer.session_id)
        assert status == 200, body[:300]
        assert json.loads(body)["currencies"] == [
            {
                "currency": "USD",
                "original_budget": "1000.00",
                "approved_changes": "-100.00",
                "current_budget": "900.00",
                "pending_changes": "0.00",
                "funding": "400.00",
                "funding_balance": "500.00",
            }
        ]

        status, body = _request(
            runtime.app,
            "POST",
            f"{BUDGET}/lines",
            body=_line(budget_line_id="BL-PREVIEW-2", description="Steel", idempotency_key="idem-line-2"),
            cookie=viewer.session_id,
        )
        assert status == 403, body[:300]

        # The WSGI layer must carry the filter query, not silently return all lines.
        status, body = _request(
            runtime.app, "GET", f"{BUDGET}/lines?search=concrete", cookie=viewer.session_id
        )
        assert status == 200, body[:300]
        assert [item["budget_line_id"] for item in json.loads(body)["budget_lines"]] == [
            "BL-PREVIEW-1"
        ]

        reopened = open_preview_runtime(tmp_path / "preview.sqlite3")
        try:
            reader = reopened.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
            status, body = _request(reopened.app, "GET", f"{BUDGET}/lines", cookie=reader.session_id)
            assert status == 200, body[:300]
            stored = json.loads(body)["budget_lines"]
            assert [item["budget_line_id"] for item in stored] == ["BL-PREVIEW-1"]
            assert stored[0]["revision"] == 1
            status, body = _request(
                reopened.app,
                "GET",
                f"{BUDGET}/lines/BL-PREVIEW-1/history",
                cookie=reader.session_id,
            )
            assert status == 200, body[:300]
            assert [event["event_type"] for event in json.loads(body)["events"]] == ["created"]
            status, body = _request(
                reopened.app, "GET", f"{BUDGET}/summary", cookie=reader.session_id
            )
            assert json.loads(body)["currencies"][0]["current_budget"] == "900.00"
        finally:
            reopened.close()
    finally:
        runtime.close()
