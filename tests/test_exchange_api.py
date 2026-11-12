from __future__ import annotations

import csv
import io
import json
from io import BytesIO
from pathlib import Path

from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

PROJECT = "preview-rps-01"
BASE = f"/api/projects/{PROJECT}/exchange"
COLUMNS = (
    "resource_id",
    "name",
    "resource_type",
    "parent_resource_id",
    "calendar_id",
    "default_units_per_time",
    "unit_of_measure",
    "email",
    "is_active",
)


def _csv(rows: list[dict[str, object]], columns: tuple[str, ...] = COLUMNS) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(columns), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({column: row.get(column, "") for column in columns})
    return buffer.getvalue()


def _resource(**values: object) -> dict[str, object]:
    row: dict[str, object] = {
        "resource_id": "E2E-ROW",
        "name": "Row",
        "resource_type": "labor",
        "is_active": "true",
    }
    row.update(values)
    return row


HEADER = _csv([])


def _request(
    app,
    method: str,
    path: str,
    *,
    body: dict | None = None,
    cookie: str | None = None,
):
    raw = b"" if body is None else json.dumps(body).encode()
    path_only, _, query_string = path.partition("?")
    environ: dict[str, object] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path_only,
        "QUERY_STRING": query_string,
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


def _json(body: bytes) -> dict:
    return json.loads(body)


def test_catalogue_and_exports_use_authoritative_rows(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
        status, body = _request(
            runtime.app, "GET", f"{BASE}/datasets", cookie=viewer.session_id
        )
        assert status == 200, body[:400]
        catalogue = _json(body)
        assert catalogue["contract_version"] == "p6-exchange-api.v1"
        datasets = {entry["dataset"]: entry for entry in catalogue["datasets"]}
        assert set(datasets) == {
            "activities",
            "resources",
            "risks",
            "wbs",
            "assignments",
            "costs",
        }
        assert datasets["resources"]["importable"] is True
        assert datasets["activities"]["importable"] is True
        assert datasets["wbs"]["importable"] is True
        assert datasets["assignments"]["importable"] is True
        assert datasets["costs"]["importable"] is True
        assert datasets["risks"]["importable"] is False

        status, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/export?dataset=resources",
            cookie=viewer.session_id,
        )
        assert status == 200, body[:400]
        exported = _json(body)
        assert exported["dataset"] == "resources"
        assert exported["row_count"] > 0
        assert exported["row_count"] == len(exported["content"].splitlines()) - 1
        assert exported["content"].splitlines()[0] == (
            "resource_id,name,resource_type,parent_resource_id,calendar_id,"
            "default_units_per_time,unit_of_measure,email,is_active"
        )

        status, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/export?dataset=activities",
            cookie=viewer.session_id,
        )
        assert status == 200, body[:400]
        activities = _json(body)
        assert activities["row_count"] >= 14
        assert "activity_id" in activities["content"].splitlines()[0]

        status, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/export?dataset=risks",
            cookie=viewer.session_id,
        )
        assert status == 200, body[:400]
        risks = _json(body)
        assert "score" in risks["content"].splitlines()[0]

        status, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/export?dataset=unknown",
            cookie=viewer.session_id,
        )
        assert status == 400
        assert _json(body)["code"] == "EXCHANGE_DATASET_UNKNOWN"
    finally:
        runtime.close()


def test_resource_preview_apply_history_and_idempotent_replay(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        content = _csv(
            [
                _resource(
                    resource_id="E2E-IMP-CREW",
                    name="E2E crew",
                    email="e2e.crew@example.test",
                ),
                _resource(
                    resource_id="E2E-IMP-CHILD",
                    name="E2E child",
                    parent_resource_id="E2E-IMP-CREW",
                    is_active="false",
                ),
            ]
        )
        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/import/preview",
            body={"dataset": "resources", "content": content},
            cookie=admin.session_id,
        )
        assert status == 200, body[:600]
        preview = _json(body)
        assert preview["valid"] is True
        assert preview["row_count"] == 2
        assert preview["accepted"] == 2
        assert preview["errors"] == []
        assert preview["rows"][0]["resource_id"] == "E2E-IMP-CREW"

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/import",
            body={
                "dataset": "resources",
                "content": content,
                "idempotency_key": "imp-key-1",
            },
            cookie=admin.session_id,
        )
        assert status == 200, body[:600]
        applied = _json(body)
        assert applied["valid"] is True
        assert applied["replayed"] is False
        assert applied["created"] == ["E2E-IMP-CREW", "E2E-IMP-CHILD"]
        assert applied["run_id"].startswith("EXR-resources-")

        status, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/export?dataset=resources",
            cookie=admin.session_id,
        )
        exported = _json(body)
        assert "E2E-IMP-CHILD,E2E child,labor,E2E-IMP-CREW" in exported["content"]

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/import",
            body={
                "dataset": "resources",
                "content": content,
                "idempotency_key": "imp-key-1",
            },
            cookie=admin.session_id,
        )
        assert status == 200, body[:600]
        replay = _json(body)
        assert replay["replayed"] is True
        assert replay["run_id"] == applied["run_id"]
        assert replay["created"] == applied["created"]

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/import",
            body={
                "dataset": "resources",
                "content": _csv([_resource(resource_id="E2E-OTHER", name="Other")]),
                "idempotency_key": "imp-key-1",
            },
            cookie=admin.session_id,
        )
        assert status == 409
        assert _json(body)["code"] == "EXCHANGE_IDEMPOTENCY_KEY_REUSE"

        status, body = _request(
            runtime.app, "GET", f"{BASE}/imports", cookie=admin.session_id
        )
        assert status == 200, body[:400]
        runs = _json(body)["runs"]
        assert runs[0]["mode"] == "apply"
        assert {run["mode"] for run in runs} == {"preview", "apply"}
    finally:
        runtime.close()


def test_preview_reports_row_and_column_errors(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        content = _csv(
            [
                _resource(resource_id="E2E-BAD-1", name="Bad type", resource_type="robot"),
                _resource(
                    resource_id="E2E-BAD-2",
                    name="Bad calendar",
                    calendar_id="CAL-DOES-NOT-EXIST",
                    email="not-an-email",
                    is_active="maybe",
                ),
                _resource(
                    resource_id="E2E-BAD-3",
                    name="Missing parent",
                    parent_resource_id="E2E-NO-PARENT",
                ),
                _resource(resource_id="E2E-BAD-3", name="Duplicate"),
                _resource(
                    resource_id="E2E-BAD-4",
                    name="Cycle A",
                    parent_resource_id="E2E-BAD-5",
                ),
                _resource(
                    resource_id="E2E-BAD-5",
                    name="Cycle B",
                    parent_resource_id="E2E-BAD-4",
                ),
            ],
            COLUMNS + ("extra",),
        )
        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/import/preview",
            body={"dataset": "resources", "content": content},
            cookie=admin.session_id,
        )
        assert status == 200, body[:600]
        preview = _json(body)
        assert preview["valid"] is False
        codes = {(error["row"], error["field"], error["code"]) for error in preview["errors"]}
        assert (1, "extra", "EXCHANGE_COLUMN_UNKNOWN") in codes
        assert (2, "resource_type", "INVALID_RESOURCE_TYPE") in codes
        assert (3, "calendar_id", "RESOURCE_CALENDAR_NOT_FOUND") in codes
        assert (3, "email", "INVALID_RESOURCE_EMAIL") in codes
        assert (3, "is_active", "INVALID_RESOURCE_ACTIVE_FLAG") in codes
        assert (4, "parent_resource_id", "RESOURCE_PARENT_NOT_FOUND") in codes
        assert (5, "resource_id", "RESOURCE_ID_DUPLICATE_IN_FILE") in codes
        assert (6, "parent_resource_id", "RESOURCE_HIERARCHY_CYCLE") in codes
        assert (7, "parent_resource_id", "RESOURCE_HIERARCHY_CYCLE") in codes

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/import",
            body={
                "dataset": "resources",
                "content": content,
                "idempotency_key": "imp-invalid-1",
            },
            cookie=admin.session_id,
        )
        assert status == 400
        rejected = _json(body)
        assert rejected["valid"] is False
        assert rejected["errors"]

        status, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/export?dataset=resources",
            cookie=admin.session_id,
        )
        assert "E2E-BAD-2" not in _json(body)["content"]
    finally:
        runtime.close()


def test_existing_ids_and_read_only_datasets_are_rejected(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        status, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/export?dataset=resources",
            cookie=admin.session_id,
        )
        first = _json(body)["content"].splitlines()[1]
        existing_id = first.split(",")[0]
        content = _csv(
            [_resource(resource_id=existing_id, name="Duplicate")]
        )
        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/import/preview",
            body={"dataset": "resources", "content": content},
            cookie=admin.session_id,
        )
        assert status == 200
        codes = {error["code"] for error in _json(body)["errors"]}
        assert "RESOURCE_ALREADY_EXISTS" in codes

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/import/preview",
            body={"dataset": "risks", "content": "risk_id\nR1\n"},
            cookie=admin.session_id,
        )
        assert status == 400
        assert _json(body)["code"] == "EXCHANGE_DATASET_READ_ONLY"

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/import",
            body={"dataset": "resources", "content": HEADER},
            cookie=admin.session_id,
        )
        assert status == 400
        assert _json(body)["code"] == "EXCHANGE_IDEMPOTENCY_KEY_REQUIRED"
    finally:
        runtime.close()


def test_viewer_reads_but_cannot_apply(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        content = _csv([_resource(resource_id="E2E-IMPROLE", name="Crew")])
        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/import/preview",
            body={"dataset": "resources", "content": content},
            cookie=viewer.session_id,
        )
        assert status == 200
        assert _json(body)["valid"] is True

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/import",
            body={
                "dataset": "resources",
                "content": content,
                "idempotency_key": "imp-viewer-1",
            },
            cookie=viewer.session_id,
        )
        assert status == 403
        assert _json(body)["code"] == "EXCHANGE_PERMISSION_DENIED"

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/import",
            body={
                "dataset": "resources",
                "content": content,
                "idempotency_key": "imp-planner-1",
            },
            cookie=planner.session_id,
        )
        assert status == 200, body[:400]
        assert _json(body)["created"] == ["E2E-IMPROLE"]
    finally:
        runtime.close()


def _xlsx_base64(rows: list[list[object]], columns: tuple[str, ...] = COLUMNS) -> str:
    import base64

    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(list(columns))
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def test_xlsx_export_streams_a_typed_workbook(tmp_path: Path) -> None:
    from openpyxl import load_workbook

    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])

        status, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/export?dataset=activities&format=xlsx",
            cookie=viewer.session_id,
        )
        assert status == 200, body[:400]
        workbook = load_workbook(BytesIO(body))
        sheet = workbook.active
        headers = [cell.value for cell in sheet[1]]
        assert headers == [
            "activity_id",
            "name",
            "activity_type",
            "status",
            "actual_start",
            "expected_finish",
            "duration_value",
            "duration_unit",
            "percent_complete",
            "wbs_id",
        ]
        duration_column = headers.index("duration_value") + 1
        assert isinstance(
            sheet.cell(row=2, column=duration_column).value, (int, float)
        )

        status, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/export?dataset=resources&format=csv",
            cookie=viewer.session_id,
        )
        assert status == 200
        assert _json(body)["format"] == "csv"

        status, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/export?dataset=resources&format=pdf",
            cookie=viewer.session_id,
        )
        assert status == 400
        assert _json(body)["code"] == "EXCHANGE_FORMAT_UNSUPPORTED"
    finally:
        runtime.close()


def test_xlsx_resource_import_preview_and_apply(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        content = _xlsx_base64(
            [
                ["E2E-XLSX-CREW", "XLSX crew", "labor", "", "", "1.5", "", "", "true"],
                ["E2E-XLSX-CHILD", "XLSX child", "labor", "E2E-XLSX-CREW", "", "", "", "", "false"],
            ]
        )
        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/import/preview",
            body={"dataset": "resources", "content": content, "format": "xlsx"},
            cookie=admin.session_id,
        )
        assert status == 200, body[:600]
        preview = _json(body)
        assert preview["valid"] is True
        assert preview["row_count"] == 2
        assert preview["rows"][0]["default_units_per_time"] == "1.5"
        assert preview["rows"][1]["is_active"] is False

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/import",
            body={
                "dataset": "resources",
                "content": content,
                "format": "xlsx",
                "idempotency_key": "xlsx-key-1",
            },
            cookie=admin.session_id,
        )
        assert status == 200, body[:600]
        applied = _json(body)
        assert applied["created"] == ["E2E-XLSX-CREW", "E2E-XLSX-CHILD"]
        assert applied["format"] == "xlsx"

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/import",
            body={
                "dataset": "resources",
                "content": content,
                "format": "xlsx",
                "idempotency_key": "xlsx-key-1",
            },
            cookie=admin.session_id,
        )
        assert status == 200, body[:300]
        assert _json(body)["replayed"] is True

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/import/preview",
            body={"dataset": "resources", "content": "not-base64!", "format": "xlsx"},
            cookie=admin.session_id,
        )
        assert status == 400, body[:300]
        assert _json(body)["code"] == "EXCHANGE_XLSX_INVALID"

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/import/preview",
            body={
                "dataset": "resources",
                "content": _xlsx_base64(
                    [["E2E-BAD", "Bad"]], columns=("resource_id", "name")
                ),
                "format": "xlsx",
            },
            cookie=admin.session_id,
        )
        assert status == 200, body[:300]
        missing = _json(body)
        assert missing["valid"] is False
        assert {error["code"] for error in missing["errors"]} == {
            "EXCHANGE_COLUMN_MISSING"
        }
    finally:
        runtime.close()


def test_csv_export_neutralises_formula_injection(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        content = _csv(
            [_resource(resource_id="E2E-FORMULA", name="=SUM(1,1)")]
        )
        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/import",
            body={
                "dataset": "resources",
                "content": content,
                "idempotency_key": "formula-key-1",
            },
            cookie=admin.session_id,
        )
        assert status == 200, body[:400]

        status, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/export?dataset=resources",
            cookie=admin.session_id,
        )
        assert status == 200, body[:400]
        exported = _json(body)["content"]
        parsed = list(csv.reader(io.StringIO(exported)))
        names = {row[0]: row[1] for row in parsed[1:]}
        assert names["E2E-FORMULA"] == "'=SUM(1,1)"

        status, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/export?dataset=resources&format=xlsx",
            cookie=admin.session_id,
        )
        assert status == 200, body[:400]
        from openpyxl import load_workbook

        sheet = load_workbook(BytesIO(body)).active
        headers = [cell.value for cell in sheet[1]]
        name_column = headers.index("name") + 1
        values = [
            sheet.cell(row=index, column=name_column).value
            for index in range(2, sheet.max_row + 1)
        ]
        assert "'=SUM(1,1)" in values
    finally:
        runtime.close()
