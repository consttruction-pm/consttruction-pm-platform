from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import load_workbook

from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE
from construction_pm.report_export import (
    ReportExportError,
    build_report_export,
)
from construction_pm.report_persistence import ReportRun

PROJECT = "preview-rps-01"
BASE = f"/api/projects/{PROJECT}/reports"


def _run(**overrides) -> ReportRun:
    payload = dict(
        run_id="RUN-RPT-ACT-1",
        tenant_id="tenant-preview",
        project_id=PROJECT,
        report_id="RPT-ACT",
        report_revision=3,
        project_revision=7,
        subject="activities",
        columns=("activity_id", "name", "actual_start", "duration"),
        rows=(
            {
                "activity_id": "A1",
                "name": "Milestone",
                "actual_start": "2026-01-05",
                "duration": "12.5",
            },
            {
                "activity_id": "A2",
                "name": "آب‌بندی",
                "actual_start": None,
                "duration": "0",
            },
        ),
        generated_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        generated_by="planner",
    )
    payload.update(overrides)
    return ReportRun(**payload)


def test_csv_export_uses_catalogue_labels_and_stored_rows() -> None:
    document = build_report_export(_run(), "csv")
    assert document.filename == "activities-RPT-ACT-RUN-RPT-ACT-1.csv"
    assert document.content_type == "text/csv; charset=utf-8"
    assert document.row_count == 2
    text = document.data.decode("utf-8")
    assert text.startswith("\ufeff")
    reader = list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))
    assert reader[0] == ["Activity ID", "Activity Name", "Actual Start", "Duration"]
    assert reader[1] == ["A1", "Milestone", "2026-01-05", "12.5"]
    assert reader[2] == ["A2", "آب‌بندی", "", "0"]


def test_xlsx_export_preserves_column_order_and_types() -> None:
    document = build_report_export(_run(), "xlsx")
    assert document.content_type == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    workbook = load_workbook(BytesIO(document.data))
    sheet = workbook.active
    assert sheet.title == "activities"
    assert [cell.value for cell in sheet[1]] == [
        "Activity ID",
        "Activity Name",
        "Actual Start",
        "Duration",
    ]
    assert sheet["A2"].value == "A1"
    assert sheet["C2"].value.date() == date(2026, 1, 5)
    assert sheet["D2"].value == pytest.approx(12.5)
    assert sheet["C3"].value is None
    assert sheet.freeze_panes == "A2"


def test_export_rejects_unsupported_format_and_unknown_column() -> None:
    with pytest.raises(ReportExportError) as error:
        build_report_export(_run(), "pdf")
    assert str(error.value) == "REPORT_EXPORT_FORMAT_UNSUPPORTED"

    with pytest.raises(ReportExportError) as error:
        build_report_export(_run(columns=("activity_id", "budget")), "csv")
    assert str(error.value) == "REPORT_EXPORT_COLUMN_UNKNOWN"


def _request(app, method, path, *, body=None, cookie=None):
    raw = b"" if body is None else json.dumps(body).encode()
    query = ""
    if "?" in path:
        path, query = path.split("?", 1)
    environ: dict[str, object] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": BytesIO(raw),
    }
    if raw:
        environ["CONTENT_TYPE"] = "application/json"
    if cookie is not None:
        environ["HTTP_COOKIE"] = f"cp_session={cookie}"
    captured: dict[str, object] = {}

    def start_response(status, response_headers):
        captured["status"] = status
        captured["headers"] = {key.lower(): value for key, value in response_headers}

    chunks = b"".join(app(environ, start_response))
    return int(str(captured["status"]).split(" ", 1)[0]), captured["headers"], chunks


def test_report_run_export_over_http(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])

        created = {
            "report_id": "RPT-ACT",
            "name": "Activity register",
            "subject": "activities",
            "columns": ["activity_id", "name", "duration"],
            "idempotency_key": "export-key-1",
        }
        status, _, body = _request(runtime.app, "POST", BASE, body=created, cookie=planner.session_id)
        assert status == 200, body[:300]
        status, _, body = _request(
            runtime.app, "POST", f"{BASE}/RPT-ACT/run", cookie=planner.session_id
        )
        assert status == 200, body[:300]
        run = json.loads(body)

        status, headers, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/RPT-ACT/runs/{run['run_id']}/export?format=csv",
            cookie=viewer.session_id,
        )
        assert status == 200, body[:300]
        assert headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in headers["content-disposition"]
        assert headers["x-report-run"] == run["run_id"]
        assert headers["x-content-sha256"]
        exported = list(csv.reader(io.StringIO(body.decode("utf-8").lstrip("\ufeff"))))
        assert exported[0] == ["Activity ID", "Activity Name", "Duration"]
        assert len(exported) == run["row_count"] + 1
        assert exported[1][0] == run["rows"][0]["activity_id"]

        status, headers, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/RPT-ACT/runs/{run['run_id']}/export?format=xlsx",
            cookie=viewer.session_id,
        )
        assert status == 200, body[:300]
        assert headers["content-type"].endswith("spreadsheetml.sheet")
        workbook = load_workbook(BytesIO(body))
        assert [cell.value for cell in workbook.active[1]] == [
            "Activity ID",
            "Activity Name",
            "Duration",
        ]

        status, _, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/RPT-ACT/runs/{run['run_id']}/export?format=pdf",
            cookie=viewer.session_id,
        )
        assert status == 400, body[:300]
        assert json.loads(body)["code"] == "REPORT_EXPORT_FORMAT_UNSUPPORTED"

        status, _, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/RPT-ACT/runs/RUN-MISSING/export?format=csv",
            cookie=viewer.session_id,
        )
        assert status == 404, body[:300]

        status, _, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/RPT-ACT/runs/{run['run_id']}/export?format=csv",
        )
        assert status in {401, 403}, body[:300]
    finally:
        runtime.close()


def test_csv_export_neutralises_formula_injection() -> None:
    run = _run(
        columns=("activity_id", "name"),
        rows=(
            {"activity_id": "A1", "name": "=HYPERLINK(\"http://example.test\")"},
            {"activity_id": "A2", "name": "@SUM(A1:A2)"},
        ),
    )
    text = build_report_export(run, "csv").data.decode("utf-8").lstrip("\ufeff")
    reader = list(csv.reader(io.StringIO(text)))
    assert reader[1][1] == "'=HYPERLINK(\"http://example.test\")"
    assert reader[2][1] == "'@SUM(A1:A2)"

    workbook = load_workbook(BytesIO(build_report_export(run, "xlsx").data))
    cell = workbook.active["B2"]
    assert cell.value == "'=HYPERLINK(\"http://example.test\")"
    assert cell.data_type == "s"
