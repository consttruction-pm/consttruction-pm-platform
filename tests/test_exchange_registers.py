from __future__ import annotations

import base64
import csv
import io
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from construction_pm.application.authorization import (
    AuthorizationContext,
    default_project_policy,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.exchange_application import (
    ExchangeService,
    RESOURCE_COLUMNS,
    WBS_COLUMNS,
)
from construction_pm.exchange_persistence import SQLiteExchangeStore
from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE
from construction_pm.p6_resource_master_repository import SQLiteP6ResourceRepository
from construction_pm.backend_p0.transactions import SQLiteTransactionManager


PROJECT = "preview-rps-01"
BASE = f"/api/projects/{PROJECT}/exchange"


def _csv(rows: list[dict[str, object]], columns: tuple[str, ...]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(columns), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({column: row.get(column, "") for column in columns})
    return buffer.getvalue()


def _request(app, method: str, path: str, *, body: dict | None = None, cookie: str):
    raw = b"" if body is None else json.dumps(body).encode()
    captured: dict[str, object] = {}

    def start_response(status, headers) -> None:
        captured["status"] = status

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path.partition("?")[0],
        "QUERY_STRING": path.partition("?")[2],
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": io.BytesIO(raw),
        "HTTP_COOKIE": f"cp_session={cookie}",
    }
    chunks = b"".join(app(environ, start_response))
    return int(str(captured["status"]).split(" ", 1)[0]), chunks


def _json(body: bytes) -> dict:
    return json.loads(body)


def _preview(app, cookie: str, dataset: str, content: str, fmt: str = "csv") -> dict:
    status, body = _request(
        app,
        "POST",
        f"{BASE}/import/preview",
        body={"dataset": dataset, "content": content, "format": fmt},
        cookie=cookie,
    )
    assert status == 200, body[:800]
    return _json(body)


def _apply(
    app, cookie: str, dataset: str, content: str, key: str, fmt: str = "csv"
) -> tuple[int, dict]:
    status, body = _request(
        app,
        "POST",
        f"{BASE}/import",
        body={
            "dataset": dataset,
            "content": content,
            "idempotency_key": key,
            "format": fmt,
        },
        cookie=cookie,
    )
    return status, _json(body)


def _export(app, cookie: str, dataset: str) -> list[dict[str, str]]:
    status, body = _request(
        app, "GET", f"{BASE}/export?dataset={dataset}", cookie=cookie
    )
    assert status == 200, body[:400]
    payload = _json(body)
    return list(csv.DictReader(io.StringIO(payload["content"])))


def _xlsx_base64(rows: list[dict[str, object]], columns: tuple[str, ...]) -> str:
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(list(columns))
    for row in rows:
        sheet.append([row.get(column) for column in columns])
    output = io.BytesIO()
    workbook.save(output)
    return base64.b64encode(output.getvalue()).decode("ascii")


def test_wbs_import_preview_apply_round_trip_and_idempotency(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        content = _csv(
            [
                {
                    "wbs_id": "WBS-E2E-ROOT",
                    "code": "9",
                    "name": "E2E root",
                    "parent_wbs_id": "WBS-RPS-ROOT",
                    "sequence_number": "70",
                },
                {
                    "wbs_id": "WBS-E2E-CHILD",
                    "code": "9.1",
                    "name": "E2E child",
                    "parent_wbs_id": "WBS-E2E-ROOT",
                    "sequence_number": "71",
                },
            ],
            WBS_COLUMNS,
        )

        preview = _preview(runtime.app, admin.session_id, "wbs", content)
        assert preview["valid"] is True, preview["errors"]
        assert preview["row_count"] == 2
        # Preview is read-only.
        assert not {
            row["wbs_id"] for row in _export(runtime.app, admin.session_id, "wbs")
        } & {"WBS-E2E-ROOT", "WBS-E2E-CHILD"}

        status, applied = _apply(
            runtime.app, admin.session_id, "wbs", content, "wbs-key-1"
        )
        assert status == 200, applied
        assert applied["created"] == ["WBS-E2E-ROOT", "WBS-E2E-CHILD"]
        assert applied["atomic"] is True

        exported = {
            row["wbs_id"]: row
            for row in _export(runtime.app, admin.session_id, "wbs")
        }
        assert exported["WBS-E2E-CHILD"]["parent_wbs_id"] == "WBS-E2E-ROOT"
        assert exported["WBS-E2E-CHILD"]["code"] == "9.1"

        status, replay = _apply(
            runtime.app, admin.session_id, "wbs", content, "wbs-key-1"
        )
        assert status == 200, replay
        assert replay["replayed"] is True
        assert replay["run_id"] == applied["run_id"]

        changed = content.replace("E2E child", "E2E child changed")
        status, conflict = _apply(
            runtime.app, admin.session_id, "wbs", changed, "wbs-key-1"
        )
        assert status == 409, conflict
        assert conflict["code"] == "EXCHANGE_IDEMPOTENCY_KEY_REUSE"
    finally:
        runtime.close()


def test_activity_assignment_and_cost_round_trip(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])

        resource = _csv(
            [
                {
                    "resource_id": "RES-E2E-1",
                    "name": "E2E crew",
                    "resource_type": "labor",
                    "is_active": "true",
                }
            ],
            RESOURCE_COLUMNS,
        )
        status, result = _apply(
            runtime.app, admin.session_id, "resources", resource, "res-key-1"
        )
        assert status == 200, result

        activity = _csv(
            [
                {
                    "activity_id": "ACT-E2E-1",
                    "name": "E2E activity",
                    "activity_type": "Task Dependent",
                    "status": "In Progress",
                    "actual_start": "2026-01-05",
                    "expected_finish": "2026-01-09",
                    "duration_value": "4.5",
                    "duration_unit": "working-day",
                    "percent_complete": "40",
                    "wbs_id": "WBS-RPS-PM",
                }
            ],
            (
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
            ),
        )
        status, result = _apply(
            runtime.app, admin.session_id, "activities", activity, "act-key-1"
        )
        assert status == 200, result
        exported = {
            row["activity_id"]: row
            for row in _export(runtime.app, admin.session_id, "activities")
        }
        assert exported["ACT-E2E-1"]["duration_value"] == "4.5"
        assert exported["ACT-E2E-1"]["actual_start"] == "2026-01-05"
        assert exported["ACT-E2E-1"]["status"] == "In Progress"

        assignment = _csv(
            [
                {
                    "assignment_id": "RA-E2E-1",
                    "activity_id": "ACT-E2E-1",
                    "resource_id": "RES-E2E-1",
                    "units": "10.50",
                    "actual_units": "2.25",
                    "remaining_units": "8.25",
                    "planned_cost": "100.10",
                    "actual_cost": "20.05",
                    "remaining_cost": "80.05",
                    "currency": "USD",
                }
            ],
            (
                "assignment_id",
                "activity_id",
                "resource_id",
                "role_id",
                "units",
                "actual_units",
                "remaining_units",
                "planned_cost",
                "actual_cost",
                "remaining_cost",
                "unit",
                "currency",
                "calendar_id",
            ),
        )
        status, result = _apply(
            runtime.app, admin.session_id, "assignments", assignment, "ra-key-1"
        )
        assert status == 200, result
        exported = {
            row["assignment_id"]: row
            for row in _export(runtime.app, admin.session_id, "assignments")
        }
        assert exported["RA-E2E-1"]["units"] == "10.50"
        assert exported["RA-E2E-1"]["planned_cost"] == "100.10"

        cost = _csv(
            [
                {
                    "expense_id": "EXP-E2E-1",
                    "name": "E2E cost",
                    "category": "Other",
                    "activity_id": "ACT-E2E-1",
                    "wbs_id": "",
                    "expense_date": "2026-01-06",
                    "planned_cost": "100.10",
                    "actual_cost": "20.05",
                    "remaining_cost": "80.05",
                    "currency": "USD",
                    "note": "imported",
                }
            ],
            (
                "expense_id",
                "name",
                "category",
                "activity_id",
                "wbs_id",
                "expense_date",
                "planned_cost",
                "actual_cost",
                "remaining_cost",
                "currency",
                "note",
            ),
        )
        status, result = _apply(
            runtime.app, admin.session_id, "costs", cost, "cost-key-1"
        )
        assert status == 200, result
        exported = {
            row["expense_id"]: row
            for row in _export(runtime.app, admin.session_id, "costs")
        }
        assert exported["EXP-E2E-1"]["expense_date"] == "2026-01-06"
        assert exported["EXP-E2E-1"]["planned_cost"] == "100.10"
    finally:
        runtime.close()


def test_xlsx_import_for_wbs_and_invalid_references_fail_closed(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        payload = _xlsx_base64(
            [
                {
                    "wbs_id": "WBS-XLSX-1",
                    "code": "10",
                    "name": "XLSX root",
                    "parent_wbs_id": "WBS-RPS-ROOT",
                    "sequence_number": 80,
                }
            ],
            WBS_COLUMNS,
        )
        preview = _preview(runtime.app, admin.session_id, "wbs", payload, "xlsx")
        assert preview["valid"] is True, preview["errors"]
        status, applied = _apply(
            runtime.app, admin.session_id, "wbs", payload, "wbs-xlsx-1", "xlsx"
        )
        assert status == 200, applied

        missing = _csv(
            [
                {
                    "assignment_id": "RA-E2E-MISSING",
                    "activity_id": "NO-SUCH-ACTIVITY",
                    "resource_id": "NO-SUCH-RESOURCE",
                }
            ],
            (
                "assignment_id",
                "activity_id",
                "resource_id",
                "role_id",
                "units",
                "actual_units",
                "remaining_units",
                "planned_cost",
                "actual_cost",
                "remaining_cost",
                "unit",
                "currency",
                "calendar_id",
            ),
        )
        preview = _preview(runtime.app, admin.session_id, "assignments", missing)
        codes = {error["code"] for error in preview["errors"]}
        assert preview["valid"] is False
        assert "ASSIGNMENT_ACTIVITY_NOT_FOUND" in codes
        assert "ASSIGNMENT_RESOURCE_NOT_FOUND" in codes
    finally:
        runtime.close()


class _FailingResourceAPI:
    def __init__(self, repository) -> None:
        self.repository = repository
        self.created: list[str] = []
        self.calendar_repository = type(
            "Calendars", (), {"list": lambda self, scope: ()}
        )()

    def create(self, resource, *, auth_context):
        if resource.resource_id == "FAIL-SECOND":
            raise RuntimeError("simulated repository failure")
        self.repository.save(resource)
        self.created.append(resource.resource_id)


class _ResourceList:
    def __init__(self, connection) -> None:
        self.repository = SQLiteP6ResourceRepository(connection)

    def list(self, tenant_id, project_id, project_revision):
        return self.repository.list(tenant_id, project_id, project_revision)


def test_failed_row_rolls_back_the_whole_batch(tmp_path: Path) -> None:
    connection = sqlite3.connect(tmp_path / "exchange.sqlite3")
    store = SQLiteExchangeStore(connection)
    store.initialize()
    resources = SQLiteP6ResourceRepository(connection)
    api = _FailingResourceAPI(resources)
    service = ExchangeService(
        store=store,
        activity_repository=type("A", (), {"list": lambda self, scope: ()})(),
        resource_repository=_ResourceList(connection),
        resource_api=api,
        risk_store=type("R", (), {})(),
        authorization_policy=default_project_policy(),
        transaction_manager=SQLiteTransactionManager(connection),
    )
    scope = BackendScope("t1", "p1", 1)
    context = AuthorizationContext("t1", "p1", "u1", frozenset({"project_admin"}))
    content = _csv(
        [
            {"resource_id": "OK-FIRST", "name": "First", "resource_type": "labor"},
            {"resource_id": "FAIL-SECOND", "name": "Second", "resource_type": "labor"},
        ],
        RESOURCE_COLUMNS,
    )

    result = service.apply_import(
        scope=scope,
        dataset="resources",
        content=content,
        idempotency_key="atomic-key",
        context=context,
        occurred_at=datetime(2026, 1, 5, tzinfo=timezone.utc),
    )

    assert result["valid"] is False
    assert result["atomic"] is True
    assert {error["code"] for error in result["errors"]} == {"EXCHANGE_APPLY_FAILED"}
    assert resources.list("t1", "p1", 1) == ()
    assert store.read_idempotency("t1", "p1", "atomic-key") is None
    assert any(
        run.mode == "apply" and not run.result["valid"]
        for run in store.list_runs("t1", "p1")
    )


def test_quoted_multiline_csv_round_trips_without_splitting(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        name = 'Crew, "A"\nsecond line'
        content = _csv(
            [
                {
                    "resource_id": "RES-E2E-QUOTED",
                    "name": name,
                    "resource_type": "labor",
                    "is_active": "true",
                }
            ],
            RESOURCE_COLUMNS,
        )
        preview = _preview(runtime.app, admin.session_id, "resources", content)
        assert preview["valid"] is True, preview["errors"]
        status, applied = _apply(
            runtime.app, admin.session_id, "resources", content, "quoted-key-1"
        )
        assert status == 200, applied
        exported = {
            row["resource_id"]: row
            for row in _export(runtime.app, admin.session_id, "resources")
        }
        assert exported["RES-E2E-QUOTED"]["name"] == name
    finally:
        runtime.close()
