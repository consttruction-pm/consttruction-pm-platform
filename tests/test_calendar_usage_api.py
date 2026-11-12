from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

PROJECT = "preview-rps-01"
BASE = f"/api/projects/{PROJECT}"
CALENDAR = "/p6/calendars/CUBI-RPS-CAL/1"


def _request(app, method: str, path: str, *, body: dict | None = None, cookie: str | None = None):
    raw = b"" if body is None else json.dumps(body).encode()
    environ: dict[str, object] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": "",
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


def _assignment(**overrides):
    payload = {
        "contract_version": "p6-resource-write-api.v1",
        "assignment_id": "ASG-CAL-USE-1",
        "activity_id": "A100",
        "resource_id": "RPS-CIVIL-CREW",
        "units": "8",
        "calendar_id": "CUBI-RPS-CAL",
        "calendar_version": "1",
    }
    payload.update(overrides)
    return payload


def test_calendar_usage_lists_stored_references(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])

        status, body = _request(runtime.app, "GET", f"{BASE}{CALENDAR}/uses", cookie=planner.session_id)
        assert status == 200, body[:300]
        usage = json.loads(body)
        assert usage["contract_version"] == "p6-calendar-usage-api.v1"
        assert usage["kind"] == "calendar_usage"
        assert usage["calendar"] == {"calendar_id": "CUBI-RPS-CAL", "calendar_version": "1"}
        # The seeded civil crew references the calendar by id without a version.
        assert usage["total"] == 1
        assert usage["counts"] == {"resource_calendar_assignment": 1}
        assert usage["usages"][0]["reference_id"] == "RPS-CIVIL-CREW"
        assert usage["usages"][0]["details"]["calendar_version"] is None

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/p6/resource-assignments",
            body=_assignment(),
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        assert json.loads(body)["assignment"]["calendar_id"] == "CUBI-RPS-CAL"

        status, body = _request(runtime.app, "GET", f"{BASE}{CALENDAR}/uses", cookie=planner.session_id)
        assert status == 200, body[:300]
        usage = json.loads(body)
        assert usage["total"] == 2
        assert usage["counts"] == {
            "resource_assignment_calendar": 1,
            "resource_calendar_assignment": 1,
        }
        assert [item["kind"] for item in usage["usages"]] == [
            "resource_assignment_calendar",
            "resource_calendar_assignment",
        ]
        assert usage["usages"][0]["details"]["activity_id"] == "A100"

        status, body = _request(runtime.app, "GET", f"{BASE}{CALENDAR}/uses", cookie=viewer.session_id)
        assert status == 200, body[:300]
        assert json.loads(body)["total"] == 2
    finally:
        runtime.close()


def test_calendar_usage_rejects_unknown_calendar_and_bad_reference(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])

        status, body = _request(
            runtime.app, "GET", f"{BASE}/p6/calendars/MISSING-CAL/1/uses", cookie=planner.session_id
        )
        assert status == 404, body[:300]
        assert json.loads(body)["code"] == "P6_CALENDAR_NOT_FOUND"

        status, body = _request(
            runtime.app, "GET", f"{BASE}/p6/calendars/CUBI-RPS-CAL/9/uses", cookie=planner.session_id
        )
        assert status == 404, body[:300]

        status, body = _request(runtime.app, "GET", f"{BASE}/p6/calendars//1/uses", cookie=planner.session_id)
        assert status == 400, body[:300]
        assert json.loads(body)["code"] == "P6_CALENDAR_REQUEST_INVALID"
    finally:
        runtime.close()
