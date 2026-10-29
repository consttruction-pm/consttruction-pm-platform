from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

RPS_PROJECT = "preview-rps-01"
RPS_TENANT = "cubi-preview-tenant"
RPS_REVISION = 7
RPS_CALENDAR = "CUBI-RPS-CAL"


def _request(
    app,
    method: str,
    path: str,
    *,
    body: bytes = b"",
    cookie: str | None = None,
    headers: dict[str, str] | None = None,
):
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
    for key, value in (headers or {}).items():
        environ["HTTP_" + key.upper().replace("-", "_")] = value
    captured: dict[str, object] = {}

    def start_response(status, response_headers) -> None:
        captured["status"] = status
        captured["headers"] = response_headers

    chunks = b"".join(app(environ, start_response))
    return int(str(captured["status"]).split(" ", 1)[0]), chunks


def _headers() -> dict[str, str]:
    return {
        "X-Tenant-Id": RPS_TENANT,
        "X-Project-Id": RPS_PROJECT,
        "X-Project-Revision": str(RPS_REVISION),
    }


def _activity_facts(runtime, cookie: str) -> dict[str, dict[str, object]]:
    status, body = _request(
        runtime.app,
        "GET",
        "/api/v1/workspace/control-room/read",
        cookie=cookie,
        headers=_headers(),
    )
    assert status == 200, body[:300]
    workspace = json.loads(body)["workspace"]
    return {activity["id"]: activity for activity in workspace["activities"]}


def _save_holiday(runtime, cookie: str, date: str, **extra):
    payload = {
        "date": date,
        "mode": "nonwork",
        "system": "gregorian",
        "intervals": [],
        **extra,
    }
    return _request(
        runtime.app,
        "POST",
        f"/api/projects/{RPS_PROJECT}/p6/calendars/{RPS_CALENDAR}/1/exceptions",
        body=json.dumps(payload).encode("utf-8"),
        cookie=cookie,
        headers=_headers(),
    )


def test_persisted_holiday_changes_the_authoritative_cpm_result(tmp_path: Path) -> None:
    database = tmp_path / "preview.sqlite3"
    runtime = open_preview_runtime(database, reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        before = _activity_facts(runtime, planner.session_id)
        assert before["A140"]["cells"]["activity.early_start"] == "2026-10-14"
        assert before["A140"]["cells"]["activity.early_finish"] == "2026-10-27"

        status, body = _save_holiday(runtime, planner.session_id, "2026-10-20")
        assert status == 200, body[:300]
        saved = json.loads(body)
        assert saved["date"] == "2026-10-20"
        assert saved["mode"] == "nonwork"

        # The same immutable snapshot now resolves through the persisted
        # exception overlay. A140 loses one working day inside its window and
        # the following fixture holiday (2026-10-28) pushes the finish once more.
        after = _activity_facts(runtime, planner.session_id)
        assert after["A140"]["cells"]["activity.early_start"] == "2026-10-14"
        assert after["A140"]["cells"]["activity.early_finish"] == "2026-10-29"
        assert after["A140"]["gantt"]["finish"] == "2026-10-29"
        assert (
            after["A160"]["cells"]["activity.early_start"]
            > before["A160"]["cells"]["activity.early_start"]
        )

        status, body = _request(
            runtime.app,
            "GET",
            f"/api/projects/{RPS_PROJECT}/p6/calendars/{RPS_CALENDAR}/1/exceptions",
            cookie=planner.session_id,
            headers=_headers(),
        )
        assert status == 200
        listed = json.loads(body)["exceptions"]
        assert [item["date"] for item in listed] == ["2026-10-20"]
    finally:
        runtime.close()

    # The holiday is persisted data: reopening the same database must keep the
    # exception and the shifted authoritative result without reseeding.
    reopened = open_preview_runtime(database)
    try:
        planner = reopened.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        persisted = _activity_facts(reopened, planner.session_id)
        assert persisted["A140"]["cells"]["activity.early_finish"] == "2026-10-29"
        exceptions = reopened.connection.execute(
            "SELECT exception_date, mode FROM calendar_exception "
            "WHERE tenant_id=? AND project_id=? AND calendar_id=?",
            (RPS_TENANT, RPS_PROJECT, RPS_CALENDAR),
        ).fetchall()
        assert exceptions == [("2026-10-20", "nonwork")]
    finally:
        reopened.close()


def test_holiday_write_rejects_viewer_and_immutable_conflicts(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
        status, body = _save_holiday(runtime, viewer.session_id, "2026-10-20")
        assert status == 403
        assert "project.write" in json.loads(body)["code"]

        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, _ = _save_holiday(runtime, planner.session_id, "2026-10-20")
        assert status == 200

        # Repeating the exact record is idempotent; reusing the same date with
        # a different definition must fail instead of silently rewriting it.
        status, body = _save_holiday(runtime, planner.session_id, "2026-10-20")
        assert status == 200
        status, body = _save_holiday(
            runtime, planner.session_id, "2026-10-20", mode="total-work-hours",
            total_work_hours="4",
        )
        assert status == 400
        assert json.loads(body)["code"] == "P6_CALENDAR_REQUEST_INVALID"

        status, body = _save_holiday(runtime, planner.session_id, "2026-13-01")
        assert status == 400
        assert json.loads(body)["code"] == "P6_CALENDAR_REQUEST_INVALID"

        status, body = _save_holiday(
            runtime, planner.session_id, "2026-10-21", mode="not-a-mode"
        )
        assert status == 400
        assert json.loads(body)["code"] == "P6_CALENDAR_REQUEST_INVALID"
    finally:
        runtime.close()
