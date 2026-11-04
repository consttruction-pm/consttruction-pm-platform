from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

RPS_PROJECT = "preview-rps-01"
ASSIGNMENT_PATH = f"/api/projects/{RPS_PROJECT}/p6/resource-assignments"


def _request(app, method: str, path: str, *, body: bytes = b"", cookie: str | None = None):
    environ: dict[str, object] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
    }
    if body:
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
        "contract_version": "p6-resource-write-api.v1",
        "assignment_id": "RPS-AS-100",
        "activity_id": "A100",
        "resource_id": "RPS-CIVIL-CREW",
        "role_id": "RPS-ROLE-CIVIL",
        "units": "8.0",
        "unit": "hour",
        "planned_cost": "1200.50",
        "currency": "USD",
        "note": "Crew assignment",
    }
    payload.update(overrides)
    return payload


def test_preview_assignments_are_composed_and_persisted(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, body = _request(runtime.app, "GET", ASSIGNMENT_PATH, cookie=planner.session_id)
        assert status == 200, body[:300]
        assert json.loads(body) == {"contract_version": "p6-resource-read-api.v1", "assignments": []}

        status, body = _request(
            runtime.app,
            "POST",
            ASSIGNMENT_PATH,
            cookie=planner.session_id,
            body=json.dumps(_payload()).encode(),
        )
        assert status == 200, body[:300]
        created = json.loads(body)
        assert created["contract_version"] == "p6-resource-write-api.v1"
        assert created["kind"] == "resource_assignment"
        assert created["assignment"]["activity_id"] == "A100"
        assert created["assignment"]["resource_id"] == "RPS-CIVIL-CREW"
        assert created["assignment"]["units"] == "8.0"
        assert created["assignment"]["planned_cost"] == "1200.50"

        status, body = _request(runtime.app, "GET", ASSIGNMENT_PATH, cookie=planner.session_id)
        assert status == 200, body[:300]
        listed = json.loads(body)
        assert listed["contract_version"] == "p6-resource-read-api.v1"
        assert [item["assignment"]["assignment_id"] for item in listed["assignments"]] == ["RPS-AS-100"]

        # A second runtime over the same file must read the persisted row.
        reopened = open_preview_runtime(tmp_path / "preview.sqlite3")
        try:
            reader = reopened.sessions.create(DEMO_USERS_BY_ROLE["planner"])
            status, body = _request(reopened.app, "GET", ASSIGNMENT_PATH, cookie=reader.session_id)
            assert status == 200, body[:300]
            stored = json.loads(body)["assignments"]
            assert stored[0]["assignment"]["assignment_id"] == "RPS-AS-100"
            assert stored[0]["scope"]["project_revision"] == 7
        finally:
            reopened.close()
    finally:
        runtime.close()


def test_preview_assignment_writes_are_authorized_and_immutable(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
        status, body = _request(
            runtime.app,
            "POST",
            ASSIGNMENT_PATH,
            cookie=viewer.session_id,
            body=json.dumps(_payload()).encode(),
        )
        assert status == 403
        assert "RESOURCE_WRITE_NOT_AUTHORIZED" in json.loads(body)["code"]

        status, body = _request(runtime.app, "GET", ASSIGNMENT_PATH, cookie=viewer.session_id)
        assert status == 200, body[:300]

        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, body = _request(
            runtime.app,
            "POST",
            ASSIGNMENT_PATH,
            cookie=planner.session_id,
            body=json.dumps(_payload()).encode(),
        )
        assert status == 200, body[:300]

        # The core treats a stored assignment as immutable; a changed value
        # under the same ID must fail with the documented conflicts, not be
        # silently overwritten by this page.
        status, body = _request(
            runtime.app,
            "POST",
            ASSIGNMENT_PATH,
            cookie=planner.session_id,
            body=json.dumps(_payload(units="9.0")).encode(),
        )
        assert status == 409
        assert json.loads(body)["code"] == "IMMUTABLE_RESOURCE_ASSIGNMENT"

        status, body = _request(
            runtime.app,
            "POST",
            ASSIGNMENT_PATH,
            cookie=planner.session_id,
            body=json.dumps({**_payload(assignment_id="RPS-AS-101"), "contract_version": "foreign"}).encode(),
        )
        assert status == 400
    finally:
        runtime.close()
