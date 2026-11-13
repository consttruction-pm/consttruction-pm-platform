from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

RPS_PROJECT = "preview-rps-01"
ACTIVITY_PATH = f"/api/projects/{RPS_PROJECT}/p6/activities"


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


def _progress(**overrides):
    payload = {
        "contract_version": "p6-activity-master-api.v1",
        "expected_revision": 1,
        "percent_complete": 20.5,
        "actual_start": "2026-10-07",
        "actual_finish": None,
        "remaining_duration": 6,
        "status": "In Progress",
    }
    payload.update(overrides)
    return payload


def _activity(app, cookie: str, activity_id: str = "A140") -> dict:
    status, body = _request(app, "GET", ACTIVITY_PATH, cookie=cookie)
    assert status == 200, body[:300]
    activities = json.loads(body)["activities"]
    return next(item["activity"] for item in activities if item["activity"]["activity_id"] == activity_id)


def test_preview_progress_is_stored_by_the_activity_service_and_survives_reopen(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        before = _activity(runtime.app, planner.session_id)
        assert before["status"] == "Not Started"
        assert before["percent_complete"] is None
        assert before["record_revision"] == 1

        status, body = _request(
            runtime.app,
            "PATCH",
            f"{ACTIVITY_PATH}/A140",
            cookie=planner.session_id,
            body=json.dumps(_progress()).encode(),
        )
        assert status == 200, body[:300]
        updated = json.loads(body)
        assert updated["contract_version"] == "p6-activity-master-api.v1"
        assert updated["kind"] == "p6_activity_master"
        activity = updated["activity"]
        assert activity["status"] == "In Progress"
        assert activity["percent_complete"] == 20.5
        assert activity["actual_start"] == "2026-10-07"
        assert activity["actual_finish"] is None
        assert activity["remaining_duration"] == 6
        assert activity["record_revision"] == 2
        # Unrelated activity fields must be preserved by the partial PATCH.
        assert activity["duration_value"] == before["duration_value"]
        assert activity["name"] == before["name"]

        stored = _activity(runtime.app, planner.session_id)
        assert stored["percent_complete"] == 20.5
        assert stored["record_revision"] == 2

        reopened = open_preview_runtime(tmp_path / "preview.sqlite3")
        try:
            reader = reopened.sessions.create(DEMO_USERS_BY_ROLE["planner"])
            persisted = _activity(reopened.app, reader.session_id)
            assert persisted["status"] == "In Progress"
            assert persisted["actual_start"] == "2026-10-07"
            assert persisted["remaining_duration"] == 6
            assert persisted["record_revision"] == 2
        finally:
            reopened.close()
    finally:
        runtime.close()


def test_preview_progress_completion_rules_and_revision_guard(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])

        status, body = _request(
            runtime.app,
            "PATCH",
            f"{ACTIVITY_PATH}/A140",
            cookie=planner.session_id,
            body=json.dumps(_progress(remaining_duration=1.5)).encode(),
        )
        assert status == 400
        assert json.loads(body)["code"] == "INVALID_REMAINING_DURATION"

        status, body = _request(
            runtime.app,
            "PATCH",
            f"{ACTIVITY_PATH}/A140",
            cookie=planner.session_id,
            body=json.dumps(_progress(percent_complete=101)).encode(),
        )
        assert status == 400
        assert json.loads(body)["code"] == "INVALID_PERCENT_COMPLETE"

        completed = {
            "contract_version": "p6-activity-master-api.v1",
            "expected_revision": 1,
            "percent_complete": 100,
            "actual_start": "2026-10-07",
            "actual_finish": "2026-10-10",
            "remaining_duration": 0,
            "status": "Completed",
        }
        status, body = _request(
            runtime.app,
            "PATCH",
            f"{ACTIVITY_PATH}/A140",
            cookie=planner.session_id,
            body=json.dumps(completed).encode(),
        )
        assert status == 200, body[:300]
        assert json.loads(body)["activity"]["status"] == "Completed"

        # The first write moved the row to revision 2; the same expected
        # revision must now conflict instead of overwriting the stored result.
        status, body = _request(
            runtime.app,
            "PATCH",
            f"{ACTIVITY_PATH}/A140",
            cookie=planner.session_id,
            body=json.dumps(_progress()).encode(),
        )
        assert status == 409
        assert json.loads(body)["code"] == "REVISION_CONFLICT"
        assert _activity(runtime.app, planner.session_id)["percent_complete"] == 100
    finally:
        runtime.close()


def test_preview_progress_writes_require_project_write_and_expected_revision(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
        status, body = _request(
            runtime.app,
            "PATCH",
            f"{ACTIVITY_PATH}/A140",
            cookie=viewer.session_id,
            body=json.dumps(_progress()).encode(),
        )
        assert status == 403
        assert "AUTHORIZATION_PERMISSION_DENIED" in json.loads(body)["code"]

        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        payload = _progress()
        del payload["expected_revision"]
        status, body = _request(
            runtime.app,
            "PATCH",
            f"{ACTIVITY_PATH}/A140",
            cookie=planner.session_id,
            body=json.dumps(payload).encode(),
        )
        assert status == 400
        assert json.loads(body)["code"] == "EXPECTED_REVISION_REQUIRED"
        assert _activity(runtime.app, planner.session_id)["status"] == "Not Started"
    finally:
        runtime.close()
