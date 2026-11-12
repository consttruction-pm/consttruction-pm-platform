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


def _risk(**overrides):
    payload = {
        "risk_id": "RK-PREVIEW-1",
        "title": "Supplier lead time slips",
        "description": "Primary steel supplier may miss the framed date.",
        "category": "schedule",
        "status": "open",
        "probability": 3,
        "impact": 4,
        "response_strategy": "mitigate",
        "owner": "preview-planner",
        "date_identified": "2026-11-01",
        "response_owner": "preview-planner",
        "response_due_date": "2026-12-01",
        "responsible_manager": "preview-planner",
        "idempotency_key": "idem-risk-1",
    }
    payload.update(overrides)
    return payload


def test_preview_risk_register_persists_and_enforces_roles(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])

        status, body = _request(runtime.app, "GET", f"{BASE}/risks", cookie=planner.session_id)
        assert status == 200, body[:300]
        assert json.loads(body) == {"contract_version": "p6-risk-api.v1", "risks": []}

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/risks",
            body=_risk(),
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        created = json.loads(body)
        assert created["revision"] == 1
        assert created["score"] == 12 and created["exposure_level"] == "high"

        status, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/risks?category=schedule&status=open&exposure=high",
            cookie=viewer.session_id,
        )
        assert status == 200, body[:300]
        assert [item["risk_id"] for item in json.loads(body)["risks"]] == ["RK-PREVIEW-1"]

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/risks",
            body=_risk(risk_id="RK-PREVIEW-2", idempotency_key="idem-risk-2"),
            cookie=viewer.session_id,
        )
        assert status == 403, body[:300]

        status, body = _request(
            runtime.app,
            "PATCH",
            f"{BASE}/risks/RK-PREVIEW-1",
            body=_risk(
                status="mitigating",
                expected_revision=1,
                reason="Plan approved",
            ),
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        assert json.loads(body)["status"] == "mitigating"
        assert json.loads(body)["revision"] == 2

        status, body = _request(
            runtime.app,
            "PATCH",
            f"{BASE}/risks/RK-PREVIEW-1",
            body=_risk(status="monitoring", expected_revision=1),
            cookie=planner.session_id,
        )
        assert status == 409, body[:300]

        status, body = _request(
            runtime.app,
            "PATCH",
            f"{BASE}/risks/RK-PREVIEW-1",
            body=_risk(
                status="closed", closure_note="Delivered", expected_revision=2
            ),
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]

        status, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/risks/RK-PREVIEW-1/history",
            cookie=viewer.session_id,
        )
        assert status == 200, body[:300]
        assert [event["event_type"] for event in json.loads(body)["events"]] == [
            "created",
            "status_changed",
            "status_changed",
        ]

        reopened = open_preview_runtime(tmp_path / "preview.sqlite3")
        try:
            reader = reopened.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
            status, body = _request(
                reopened.app,
                "GET",
                f"{BASE}/risks/RK-PREVIEW-1",
                cookie=reader.session_id,
            )
            assert status == 200, body[:300]
            persisted = json.loads(body)
            assert persisted["status"] == "closed"
            assert persisted["closure_note"] == "Delivered"
            assert persisted["revision"] == 3
        finally:
            reopened.close()

        status, body = _request(
            runtime.app,
            "DELETE",
            f"{BASE}/risks/RK-PREVIEW-1?expected_revision=3",
            cookie=planner.session_id,
        )
        assert status == 200 and json.loads(body)["deleted"] is True
        status, body = _request(
            runtime.app, "GET", f"{BASE}/risks/RK-PREVIEW-1", cookie=viewer.session_id
        )
        assert status == 404, body[:300]
    finally:
        runtime.close()
