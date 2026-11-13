from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

PROJECT = "preview-rps-01"
ISSUES = f"/api/projects/{PROJECT}/p6/issues"


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
        captured["headers"] = response_headers

    chunks = b"".join(app(environ, start_response))
    return int(str(captured["status"]).split(" ", 1)[0]), chunks


def _payload(**overrides):
    payload = {
        "issue_id": "ISSUE-PREVIEW-1",
        "title": "Late approval of the façade sample",
        "description": "The sample approval is blocking the curtain-wall start.",
        "issue_type": "schedule",
        "status": "open",
        "priority": "high",
        "owner": "planner",
        "date_identified": "2026-11-04",
        "due_date": "2026-11-18",
        "wbs_id": "WBS-PREVIEW-1",
        "activity_id": "A1000",
        "document_refs": ["DOC-PREVIEW-1"],
    }
    payload.update(overrides)
    return payload


def test_preview_issue_register_persists_across_restart(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, body = _request(runtime.app, "GET", ISSUES, cookie=planner.session_id)
        assert status == 200, body[:300]
        assert json.loads(body) == {"contract_version": "p6-issue-api.v1", "issues": []}

        status, body = _request(
            runtime.app, "POST", ISSUES, body=_payload(), cookie=planner.session_id
        )
        assert status == 200, body[:300]
        created = json.loads(body)
        assert created["kind"] == "p6_issue"
        assert created["issue"]["record_revision"] == 1
        assert created["issue"]["document_refs"] == ["DOC-PREVIEW-1"]

        status, body = _request(
            runtime.app, "POST", f"{ISSUES}/ISSUE-PREVIEW-1/comments",
            body={"comment": "Sample reissued", "expected_revision": 1},
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        assert json.loads(body)["issue"]["record_revision"] == 2

        status, body = _request(
            runtime.app, "GET", f"{ISSUES}?priority=high", cookie=planner.session_id
        )
        assert status == 200, body[:300]
        assert len(json.loads(body)["issues"]) == 1

        # A WSGI query string must reach the issue route: with a second record
        # present, a wrong or dropped filter would return both rows.
        status, body = _request(
            runtime.app,
            "POST",
            ISSUES,
            body=_payload(issue_id="ISSUE-PREVIEW-2", title="Minor punch item", priority="low"),
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        status, body = _request(
            runtime.app, "GET", f"{ISSUES}?priority=high", cookie=planner.session_id
        )
        assert status == 200, body[:300]
        high = json.loads(body)["issues"]
        assert [item["issue"]["issue_id"] for item in high] == ["ISSUE-PREVIEW-1"]
        status, body = _request(
            runtime.app,
            "GET",
            f"{ISSUES}?status=resolved",
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        assert json.loads(body)["issues"] == []
        status, body = _request(
            runtime.app,
            "GET",
            f"{ISSUES}?search=punch",
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        assert [item["issue"]["issue_id"] for item in json.loads(body)["issues"]] == [
            "ISSUE-PREVIEW-2"
        ]

        reopened = open_preview_runtime(tmp_path / "preview.sqlite3")
        try:
            reader = reopened.sessions.create(DEMO_USERS_BY_ROLE["planner"])
            status, body = _request(reopened.app, "GET", ISSUES, cookie=reader.session_id)
            assert status == 200, body[:300]
            stored = json.loads(body)["issues"]
            assert stored[0]["issue"]["issue_id"] == "ISSUE-PREVIEW-1"
            assert stored[0]["issue"]["record_revision"] == 2

            status, body = _request(
                reopened.app, "GET", f"{ISSUES}/ISSUE-PREVIEW-1/history",
                cookie=reader.session_id,
            )
            assert status == 200, body[:300]
            assert [event["event"]["event_type"] for event in json.loads(body)["events"]] == [
                "created", "commented",
            ]
        finally:
            reopened.close()
    finally:
        runtime.close()


def test_preview_issue_permissions_and_revision_conflicts(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
        status, body = _request(
            runtime.app, "POST", ISSUES, body=_payload(), cookie=viewer.session_id
        )
        assert status == 403
        assert "AUTHORIZATION_PERMISSION_DENIED" in json.loads(body)["code"]

        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, _ = _request(
            runtime.app, "POST", ISSUES, body=_payload(), cookie=planner.session_id
        )
        assert status == 200

        status, body = _request(
            runtime.app, "PUT", f"{ISSUES}/ISSUE-PREVIEW-1",
            body=_payload(priority="critical", expected_revision=1),
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        assert json.loads(body)["issue"]["record_revision"] == 2

        status, body = _request(
            runtime.app, "PUT", f"{ISSUES}/ISSUE-PREVIEW-1",
            body=_payload(priority="low", expected_revision=1),
            cookie=planner.session_id,
        )
        assert status == 409
        assert json.loads(body)["code"] == "ISSUE_REVISION_CONFLICT"

        # The competing write must not have been dropped by the conflict.
        status, body = _request(
            runtime.app, "GET", f"{ISSUES}/ISSUE-PREVIEW-1", cookie=planner.session_id
        )
        assert status == 200
        assert json.loads(body)["issue"]["priority"] == "critical"
    finally:
        runtime.close()
