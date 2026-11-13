from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

PROJECT = "preview-rps-01"
BASE = f"/api/projects/{PROJECT}/reports"


def _request(
    app,
    method: str,
    path: str,
    *,
    body: dict | None = None,
    cookie: str | None = None,
    headers: dict[str, str] | None = None,
):
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
    for key, value in (headers or {}).items():
        environ[f"HTTP_{key.upper().replace('-', '_')}"] = value
    captured: dict[str, object] = {}

    def start_response(status, response_headers) -> None:
        captured["status"] = status

    chunks = b"".join(app(environ, start_response))
    return int(str(captured["status"]).split(" ", 1)[0]), chunks


def _report(**overrides):
    payload = {
        "report_id": "RPT-ACT",
        "name": "Activity register",
        "description": "Stored activities with duration.",
        "subject": "activities",
        "columns": ["activity_id", "name", "duration"],
        "idempotency_key": "report-key-1",
    }
    payload.update(overrides)
    return payload


def test_report_definition_run_and_readback(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])

        status, body = _request(runtime.app, "POST", BASE, body=_report(), cookie=planner.session_id)
        assert status == 200, body[:400]
        created = json.loads(body)
        assert created["contract_version"] == "p6-report-api.v1"
        assert created["report_id"] == "RPT-ACT"
        assert created["record_revision"] == 1
        assert created["columns"] == ["activity_id", "name", "duration"]

        status, body = _request(runtime.app, "POST", BASE, body=_report(), cookie=planner.session_id)
        assert status == 200, body[:400]
        assert json.loads(body)["record_revision"] == 1

        status, body = _request(runtime.app, "GET", BASE, cookie=viewer.session_id)
        assert status == 200, body[:400]
        listed = json.loads(body)
        assert [item["report_id"] for item in listed["reports"]] == ["RPT-ACT"]
        subjects = {item["subject"] for item in listed["catalogue"]}
        assert subjects == {"activities", "resources", "risks"}
        activity_fields = next(
            item for item in listed["catalogue"] if item["subject"] == "activities"
        )
        assert {field["key"] for field in activity_fields["fields"]} >= {
            "activity_id",
            "name",
            "duration",
        }

        status, body = _request(
            runtime.app, "POST", f"{BASE}/RPT-ACT/run", cookie=planner.session_id
        )
        assert status == 200, body[:400]
        run = json.loads(body)
        assert run["run_id"] == "RUN-RPT-ACT-1"
        assert run["report_revision"] == 1
        assert run["columns"] == ["activity_id", "name", "duration"]
        assert run["row_count"] == 14
        assert run["generated_by"] == planner.user_id
        assert set(run["rows"][0]) == {"activity_id", "name", "duration"}

        status, body = _request(
            runtime.app, "GET", f"{BASE}/RPT-ACT/runs", cookie=viewer.session_id
        )
        assert status == 200, body[:400]
        runs = json.loads(body)["runs"]
        assert len(runs) == 1
        assert runs[0]["run_id"] == run["run_id"]
        assert "rows" not in runs[0]

        status, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/RPT-ACT/runs/{run['run_id']}",
            cookie=viewer.session_id,
        )
        assert status == 200, body[:400]
        readback = json.loads(body)
        assert readback["rows"] == run["rows"]
        assert readback["generated_at"] == run["generated_at"]

        status, body = _request(
            runtime.app, "GET", f"{BASE}/RPT-ACT/history", cookie=planner.session_id
        )
        assert status == 200, body[:400]
        events = json.loads(body)["events"]
        assert [(item["revision"], item["event_type"]) for item in events] == [(1, "created")]

        denied = _report(report_id="RPT-DENIED", idempotency_key="report-key-denied")
        status, body = _request(runtime.app, "POST", BASE, body=denied, cookie=viewer.session_id)
        assert status == 403, body[:300]
        assert json.loads(body)["code"] == "REPORT_PERMISSION_DENIED"
    finally:
        runtime.close()


def test_report_revision_guard_and_delete(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, body = _request(runtime.app, "POST", BASE, body=_report(), cookie=planner.session_id)
        assert status == 200, body[:300]

        update = _report(
            name="Activity register v2",
            columns=["activity_id", "name", "status"],
            expected_revision=2,
        )
        status, body = _request(
            runtime.app, "PUT", f"{BASE}/RPT-ACT", body=update, cookie=planner.session_id
        )
        assert status == 409, body[:300]
        assert json.loads(body)["code"] == "REPORT_REVISION_CONFLICT"

        update["expected_revision"] = 1
        status, body = _request(
            runtime.app, "PUT", f"{BASE}/RPT-ACT", body=update, cookie=planner.session_id
        )
        assert status == 200, body[:300]
        updated = json.loads(body)
        assert updated["record_revision"] == 2
        assert updated["name"] == "Activity register v2"
        assert updated["columns"] == ["activity_id", "name", "status"]

        status, body = _request(
            runtime.app, "POST", f"{BASE}/RPT-ACT/run", cookie=planner.session_id
        )
        assert status == 200, body[:300]
        assert json.loads(body)["report_revision"] == 2

        status, body = _request(
            runtime.app,
            "DELETE",
            f"{BASE}/RPT-ACT",
            body={"expected_revision": 1},
            cookie=planner.session_id,
        )
        assert status == 409, body[:300]

        status, body = _request(
            runtime.app,
            "DELETE",
            f"{BASE}/RPT-ACT",
            body={"expected_revision": 2, "reason": "duplicate report"},
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        assert json.loads(body)["deleted"] is True

        status, body = _request(runtime.app, "GET", f"{BASE}/RPT-ACT", cookie=planner.session_id)
        assert status == 404, body[:300]
        assert json.loads(body)["code"] == "REPORT_NOT_FOUND"

        status, body = _request(
            runtime.app, "GET", f"{BASE}/RPT-ACT/history", cookie=planner.session_id
        )
        assert status == 404, body[:300]
    finally:
        runtime.close()


def test_report_definition_validation(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])

        for payload, code in (
            (_report(subject="documents"), "INVALID_REPORT_SUBJECT"),
            (_report(columns=["activity_id", "budget"]), "REPORT_COLUMN_NOT_IN_SUBJECT"),
            (_report(columns=["activity_id", "activity_id"]), "REPORT_COLUMN_DUPLICATED"),
            (_report(columns=[]), "REPORT_COLUMNS_REQUIRED"),
            (_report(idempotency_key=""), "REPORT_IDEMPOTENCY_KEY_REQUIRED"),
            (_report(report_id=""), "INVALID_REPORT_ID"),
        ):
            status, body = _request(runtime.app, "POST", BASE, body=payload, cookie=planner.session_id)
            assert status == 400, (code, status, body[:300])
            assert json.loads(body)["code"] == code

        status, body = _request(
            runtime.app, "POST", BASE, body=_report(), cookie=planner.session_id
        )
        assert status == 200, body[:300]

        reused = _report(columns=["activity_id"], idempotency_key="report-key-1")
        status, body = _request(runtime.app, "POST", BASE, body=reused, cookie=planner.session_id)
        assert status == 409, body[:300]
        assert json.loads(body)["code"] == "REPORT_IDEMPOTENCY_KEY_REUSE"

        status, body = _request(
            runtime.app, "GET", f"{BASE}/RPT-MISSING/run", cookie=planner.session_id
        )
        assert status in {400, 404}, body[:300]

        status, body = _request(
            runtime.app, "POST", f"{BASE}/RPT-MISSING/run", cookie=planner.session_id
        )
        assert status == 404, body[:300]
        assert json.loads(body)["code"] == "REPORT_NOT_FOUND"
    finally:
        runtime.close()


def test_report_runs_read_resource_and_risk_subjects(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])

        resources = _report(
            report_id="RPT-RES",
            name="Resource register",
            subject="resources",
            columns=["resource_id", "name", "calendar_id", "is_active"],
            idempotency_key="report-res-1",
        )
        status, body = _request(runtime.app, "POST", BASE, body=resources, cookie=planner.session_id)
        assert status == 200, body[:300]
        status, body = _request(
            runtime.app, "POST", f"{BASE}/RPT-RES/run", cookie=planner.session_id
        )
        assert status == 200, body[:300]
        run = json.loads(body)
        assert run["row_count"] == 1
        assert run["rows"][0]["resource_id"] == "RPS-CIVIL-CREW"
        crew = run["rows"][0]
        assert crew["calendar_id"] == "CUBI-RPS-CAL"
        assert crew["is_active"] is True

        status, body = _request(
            runtime.app,
            "POST",
            f"/api/projects/{PROJECT}/risks",
            body={
                "risk_id": "RPT-RISK-1",
                "title": "Late steel delivery",
                "category": "schedule",
                "status": "open",
                "probability": 3,
                "impact": 4,
                "response_strategy": "mitigate",
                "owner": "u-owner",
                "date_identified": "2026-11-01",
            },
            headers={"Idempotency-Key": "risk-report-1"},
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]

        risks = _report(
            report_id="RPT-RISK",
            name="Risk register",
            subject="risks",
            columns=["risk_id", "title", "score", "exposure_level"],
            idempotency_key="report-risk-1",
        )
        status, body = _request(runtime.app, "POST", BASE, body=risks, cookie=planner.session_id)
        assert status == 200, body[:300]
        status, body = _request(
            runtime.app, "POST", f"{BASE}/RPT-RISK/run", cookie=planner.session_id
        )
        assert status == 200, body[:300]
        run = json.loads(body)
        assert run["row_count"] == 1
        assert run["rows"] == [
            {
                "risk_id": "RPT-RISK-1",
                "title": "Late steel delivery",
                "score": 12,
                "exposure_level": "high",
            }
        ]
    finally:
        runtime.close()


def test_unexpected_report_fault_is_a_server_error_without_internal_text() -> None:
    from construction_pm.api_errors import APIErrorCategory
    from construction_pm.report_application import ReportApplicationService

    error = ReportApplicationService.error_dto(RuntimeError("password=hunter2"))
    assert error.category is APIErrorCategory.PERSISTENCE
    assert error.code == "REPORT_INTERNAL_ERROR"
    assert error.message == ""
