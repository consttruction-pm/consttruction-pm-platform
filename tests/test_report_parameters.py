from __future__ import annotations

import json
import sqlite3
from io import BytesIO
from pathlib import Path

import pytest

from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE
from construction_pm.report_parameters import (
    ReportParameterError,
    apply_parameters,
    resolve_parameters,
)
from construction_pm.report_parameters import ReportParameterBinding
from construction_pm.report_persistence import (
    ReportDefinition,
    SQLiteReportStore,
)

PROJECT = "preview-rps-01"
BASE = f"/api/projects/{PROJECT}/reports"


def _request(app, method: str, path: str, *, body: dict | None = None, cookie=None):
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

    def start_response(status, headers) -> None:
        captured["status"] = status

    chunks = b"".join(app(environ, start_response))
    return int(str(captured["status"]).split(" ", 1)[0]), chunks


def _definition(**overrides) -> dict:
    payload = {
        "report_id": "RPT-PARAM",
        "name": "Parameterized activities",
        "subject": "activities",
        "columns": ["activity_id", "name", "status", "actual_start"],
        "parameters": [{"key": "status", "required": True}],
        "idempotency_key": "param-key-1",
    }
    payload.update(overrides)
    return payload


@pytest.fixture()
def runtime(tmp_path: Path):
    instance = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        yield instance
    finally:
        instance.close()


def _planner(runtime):
    return runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])


def test_definition_parameters_filter_rows_and_record_provenance(runtime) -> None:
    planner = _planner(runtime)
    created = {
        **_definition(),
        "parameters": [
            {"key": "status", "required": True},
            {"key": "actual_start_from", "default": "2026-09-22"},
        ],
    }
    status, body = _request(runtime.app, "POST", BASE, body=created, cookie=planner.session_id)
    assert status == 200, body[:400]
    definition = json.loads(body)
    assert definition["parameters"] == [
        {
            "key": "actual_start_from",
            "label": "Actual Start From",
            "data_type": "date",
            "choices": [],
            "required": False,
            "default": "2026-09-22",
        },
        {
            "key": "status",
            "label": "Status",
            "data_type": "enum",
            "choices": ["Not Started", "In Progress", "Completed"],
            "required": True,
            "default": None,
        },
    ]

    status, body = _request(
        runtime.app,
        "POST",
        f"{BASE}/RPT-PARAM/run",
        body={"parameters": {"status": "Completed"}},
        cookie=planner.session_id,
    )
    assert status == 200, body[:400]
    run = json.loads(body)
    assert run["parameters"] == {
        "actual_start_from": "2026-09-22",
        "status": "Completed",
    }
    assert run["parameter_sources"] == {
        "actual_start_from": "default",
        "status": "explicit",
    }
    assert run["rows"]
    assert all(row["status"] == "Completed" for row in run["rows"])
    assert all(row["actual_start"] >= "2026-09-22" for row in run["rows"])
    assert "A100" not in {row["activity_id"] for row in run["rows"]}

    status, body = _request(
        runtime.app, "GET", f"{BASE}/RPT-PARAM/runs/{run['run_id']}", cookie=planner.session_id
    )
    assert status == 200, body[:400]
    readback = json.loads(body)
    assert readback["parameters"] == run["parameters"]


def test_catalogue_lists_subject_parameters(runtime) -> None:
    planner = _planner(runtime)
    status, body = _request(
        runtime.app, "GET", f"{BASE}/catalogue", cookie=planner.session_id
    )
    assert status == 200, body[:400]
    catalogue = {
        item["subject"]: item["parameters"] for item in json.loads(body)["parameters"]
    }
    assert [item["key"] for item in catalogue["activities"]] == [
        "status",
        "activity_type",
        "actual_start_from",
        "actual_start_to",
    ]
    assert catalogue["risks"][2]["choices"] == []
    assert catalogue["risks"][2]["data_type"] == "integer"


def test_run_rejects_missing_unknown_and_invalid_parameters(runtime) -> None:
    planner = _planner(runtime)
    status, body = _request(runtime.app, "POST", BASE, body=_definition(), cookie=planner.session_id)
    assert status == 200, body[:400]

    status, body = _request(
        runtime.app, "POST", f"{BASE}/RPT-PARAM/run", cookie=planner.session_id
    )
    assert status == 400, body[:300]
    assert json.loads(body)["code"] == "REPORT_PARAMETER_REQUIRED"

    status, body = _request(
        runtime.app,
        "POST",
        f"{BASE}/RPT-PARAM/run",
        body={"parameters": {"unknown": "x", "status": "Completed"}},
        cookie=planner.session_id,
    )
    assert status == 400, body[:300]
    assert json.loads(body)["code"] == "REPORT_PARAMETER_UNKNOWN"

    status, body = _request(
        runtime.app,
        "POST",
        f"{BASE}/RPT-PARAM/run",
        body={"parameters": {"status": "Done"}},
        cookie=planner.session_id,
    )
    assert status == 400, body[:300]
    assert json.loads(body)["code"] == "REPORT_PARAMETER_INVALID"

    status, body = _request(
        runtime.app,
        "POST",
        f"{BASE}/RPT-PARAM/run",
        body={"parameters": ["status"]},
        cookie=planner.session_id,
    )
    assert status == 400, body[:300]

    status, body = _request(
        runtime.app, "GET", f"{BASE}/RPT-PARAM/runs", cookie=planner.session_id
    )
    assert json.loads(body)["runs"] == []


def test_definition_rejects_unknown_duplicate_and_invalid_bindings(runtime) -> None:
    planner = _planner(runtime)
    status, body = _request(
        runtime.app,
        "POST",
        BASE,
        body=_definition(parameters=[{"key": "budget"}]),
        cookie=planner.session_id,
    )
    assert status == 400, body[:300]
    assert json.loads(body)["code"] == "REPORT_PARAMETER_UNKNOWN"

    status, body = _request(
        runtime.app,
        "POST",
        BASE,
        body=_definition(
            parameters=[{"key": "status"}, {"key": "status", "required": True}]
        ),
        cookie=planner.session_id,
    )
    assert status == 400, body[:300]
    assert json.loads(body)["code"] == "REPORT_PARAMETER_DUPLICATED"

    status, body = _request(
        runtime.app,
        "POST",
        BASE,
        body=_definition(
            report_id="RPT-BAD-DEFAULT",
            parameters=[{"key": "activity_type", "default": "Unknown Type"}],
        ),
        cookie=planner.session_id,
    )
    assert status == 400, body[:300]
    assert json.loads(body)["code"] == "REPORT_PARAMETER_INVALID"

    status, body = _request(
        runtime.app,
        "POST",
        BASE,
        body=_definition(parameters={"status": "Completed"}),
        cookie=planner.session_id,
    )
    assert status == 400, body[:300]
    assert json.loads(body)["code"] == "INVALID_REPORT_PARAMETER_LIST"


def test_parameter_change_changes_idempotency_fingerprint(runtime) -> None:
    planner = _planner(runtime)
    status, body = _request(runtime.app, "POST", BASE, body=_definition(), cookie=planner.session_id)
    assert status == 200, body[:400]

    status, body = _request(
        runtime.app,
        "POST",
        BASE,
        body=_definition(
            parameters=[{"key": "status", "required": False, "default": "Completed"}]
        ),
        cookie=planner.session_id,
    )
    assert status == 409, body[:300]
    assert json.loads(body)["code"] == "REPORT_IDEMPOTENCY_KEY_REUSE"


def test_parameter_resolution_and_filtering_for_all_subjects() -> None:
    resolved = resolve_parameters(
        "activities",
        (
            ReportParameterBinding("status", required=True),
            ReportParameterBinding("actual_start_to", default="2026-10-01"),
        ),
        {"status": "Completed"},
    )
    assert resolved.values == (
        ("actual_start_to", "2026-10-01"),
        ("status", "Completed"),
    )
    assert resolved.sources == (
        ("actual_start_to", "default"),
        ("status", "explicit"),
    )

    rows = (
        {"activity_id": "A1", "status": "Completed", "actual_start": "2026-09-21"},
        {"activity_id": "A2", "status": "Completed", "actual_start": "2026-10-02"},
        {"activity_id": "A3", "status": "Not Started", "actual_start": None},
    )
    filtered = apply_parameters("activities", rows, resolved.mapping())
    assert [row["activity_id"] for row in filtered] == ["A1"]

    resources = (
        {"resource_id": "R1", "resource_type": "labor", "is_active": True},
        {"resource_id": "R2", "resource_type": "material", "is_active": False},
    )
    filtered = apply_parameters(
        "resources", resources, {"resource_type": "labor", "is_active": "true"}
    )
    assert [row["resource_id"] for row in filtered] == ["R1"]

    risks = (
        {"risk_id": "K1", "status": "open", "category": "Technical", "score": 9},
        {"risk_id": "K2", "status": "open", "category": "technical", "score": 20},
        {"risk_id": "K3", "status": "open", "category": "cost", "score": 25},
    )
    filtered = apply_parameters(
        "risks",
        risks,
        {"status": "open", "category": "technical", "min_score": "10"},
    )
    assert [row["risk_id"] for row in filtered] == ["K2"]

    with pytest.raises(ReportParameterError):
        resolve_parameters("activities", (), {"status": "Completed"})
    with pytest.raises(ReportParameterError):
        apply_parameters("risks", risks, {"min_score": "not-a-number"})


_OLD_DEFINITION_SQL = """
CREATE TABLE project_report_definition (
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    report_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    subject TEXT NOT NULL,
    columns_json TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, project_id, report_id)
)
"""

_OLD_RUN_SQL = """
CREATE TABLE project_report_run (
    run_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    report_id TEXT NOT NULL,
    report_revision INTEGER NOT NULL,
    project_revision INTEGER NOT NULL,
    subject TEXT NOT NULL,
    columns_json TEXT NOT NULL,
    rows_json TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    generated_by TEXT NOT NULL,
    PRIMARY KEY (tenant_id, project_id, run_id)
)
"""


def test_initialize_migrates_pre_parameter_schema_without_data_loss() -> None:
    connection = sqlite3.connect(":memory:")
    connection.executescript(_OLD_DEFINITION_SQL)
    connection.executescript(_OLD_RUN_SQL)
    connection.execute(
        """INSERT INTO project_report_definition
           (tenant_id, project_id, report_id, name, description, subject,
            columns_json, revision, created_at, updated_at)
           VALUES ('t', 'p', 'RPT-OLD', 'Old', '', 'activities',
                   '["activity_id"]', 2, '2026-01-01T00:00:00+00:00',
                   '2026-01-01T00:00:00+00:00')"""
    )
    connection.execute(
        """INSERT INTO project_report_run
           (run_id, tenant_id, project_id, report_id, report_revision,
            project_revision, subject, columns_json, rows_json,
            generated_at, generated_by)
           VALUES ('RUN-OLD', 't', 'p', 'RPT-OLD', 2, 5, 'activities',
                   '["activity_id"]', '[{"activity_id": "A1"}]',
                   '2026-01-02T00:00:00+00:00', 'planner')"""
    )
    connection.commit()

    store = SQLiteReportStore(connection)
    store.initialize()

    stored = store.get_definition("t", "p", "RPT-OLD")
    assert stored.revision == 2
    assert stored.definition.columns == ("activity_id",)
    assert stored.definition.parameters == ()

    run = store.get_run("t", "p", "RPT-OLD", "RUN-OLD")
    assert run.rows == ({"activity_id": "A1"},)
    assert run.parameters == ()
    assert run.parameter_sources == ()

    # Parameter definitions now persist and round-trip through the same table.
    updated = ReportDefinition(
        "t",
        "p",
        "RPT-OLD",
        "Old",
        "activities",
        ("activity_id", "status"),
        parameters=(ReportParameterBinding("status", required=True),),
    )
    store.update_definition(
        updated,
        expected_revision=2,
        actor_id="planner",
        occurred_at=run.generated_at,
    )
    reread = store.get_definition("t", "p", "RPT-OLD")
    assert reread.revision == 3
    assert reread.definition.parameters == (
        ReportParameterBinding("status", required=True),
    )
