from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_baseline_activity_repository import (
    P6BaselineActivity,
    SQLiteP6BaselineActivityRepository,
)
from construction_pm.p6_baseline_repository import (
    P6Baseline,
    SQLiteP6BaselineRepository,
)
from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE, PREVIEW_TENANT_ID

RPS_PROJECT = "preview-rps-01"
PERIOD_PATH = f"/api/projects/{RPS_PROJECT}/p6/financial-periods"
EVM_PATH = f"/api/projects/{RPS_PROJECT}/p6/earned-value"


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


def _period(**overrides):
    payload = {
        "period_id": "FY-2026-Q4",
        "name": "Q4 2026",
        "start_date": "2026-10-01",
        "end_date": "2026-12-31",
        "status": "OPEN",
    }
    payload.update(overrides)
    return payload


def _revision(runtime) -> int:
    summaries = runtime.store.project_rows()
    return next(
        int(item["revision"])
        for item in summaries
        if item["project_id"] == RPS_PROJECT
    )


def _seed_baseline(runtime) -> None:
    """Store one baseline so the earned-value read model has measured facts.

    The product has no baseline-capture route yet (GAP-BAS-03); this test seeds
    the authoritative repository directly to exercise the EVM read boundary.
    """
    scope = BackendScope(PREVIEW_TENANT_ID, RPS_PROJECT, _revision(runtime))
    baselines = SQLiteP6BaselineRepository(runtime.connection)
    baselines.upsert(
        P6Baseline(
            scope=scope,
            baseline_id="BL-PREVIEW-1",
            name="Preview baseline",
            baseline_type="PRIMARY",
            source_revision=scope.project_revision,
            created_at="2026-10-01T00:00:00+00:00",
        )
    )
    SQLiteP6BaselineActivityRepository(runtime.connection).save_many(
        (
            P6BaselineActivity(
                scope=scope,
                baseline_id="BL-PREVIEW-1",
                activity_id="A100",
                planned_start=date(2026, 9, 21),
                planned_finish=date(2026, 10, 2),
                budgeted_cost=Decimal("1000.00"),
                currency="USD",
                wbs_id=None,
            ),
            P6BaselineActivity(
                scope=scope,
                baseline_id="BL-PREVIEW-1",
                activity_id="A130",
                planned_start=date(2026, 9, 28),
                planned_finish=date(2026, 10, 9),
                budgeted_cost=Decimal("2500.00"),
                currency="USD",
                wbs_id=None,
            ),
        )
    )


def test_preview_financial_periods_are_composed_and_persisted(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, body = _request(runtime.app, "GET", PERIOD_PATH, cookie=planner.session_id)
        assert status == 200, body[:300]
        assert json.loads(body) == {
            "contract_version": "p6-financial-period-api.v1",
            "financial_periods": [],
        }

        status, body = _request(
            runtime.app,
            "POST",
            PERIOD_PATH,
            cookie=planner.session_id,
            body=json.dumps(_period()).encode(),
        )
        assert status == 200, body[:300]
        created = json.loads(body)
        assert created["kind"] == "p6_financial_period"
        assert created["financial_period"]["period_id"] == "FY-2026-Q4"
        assert created["financial_period"]["status"] == "OPEN"

        status, body = _request(runtime.app, "GET", PERIOD_PATH, cookie=planner.session_id)
        assert status == 200, body[:300]
        listed = json.loads(body)["financial_periods"]
        assert [item["financial_period"]["name"] for item in listed] == ["Q4 2026"]

        status, body = _request(
            runtime.app,
            "GET",
            f"{PERIOD_PATH}/FY-2026-Q4",
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        assert json.loads(body)["financial_period"]["end_date"] == "2026-12-31"

        reopened = open_preview_runtime(tmp_path / "preview.sqlite3")
        try:
            reader = reopened.sessions.create(DEMO_USERS_BY_ROLE["planner"])
            status, body = _request(reopened.app, "GET", PERIOD_PATH, cookie=reader.session_id)
            assert status == 200, body[:300]
            stored = json.loads(body)["financial_periods"]
            assert stored[0]["financial_period"]["period_id"] == "FY-2026-Q4"
        finally:
            reopened.close()
    finally:
        runtime.close()


def test_preview_financial_period_writes_are_authorized_and_immutable(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
        status, body = _request(
            runtime.app,
            "POST",
            PERIOD_PATH,
            cookie=viewer.session_id,
            body=json.dumps(_period()).encode(),
        )
        assert status == 403
        assert "AUTHORIZATION_PERMISSION_DENIED" in json.loads(body)["code"]

        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, body = _request(
            runtime.app,
            "POST",
            PERIOD_PATH,
            cookie=planner.session_id,
            body=json.dumps(_period(status="PENDING")).encode(),
        )
        assert status == 400
        assert json.loads(body)["code"] == "P6_FINANCIAL_PERIOD_REQUEST_INVALID"

        status, body = _request(
            runtime.app,
            "POST",
            PERIOD_PATH,
            cookie=planner.session_id,
            body=json.dumps(_period()).encode(),
        )
        assert status == 200, body[:300]

        status, body = _request(
            runtime.app,
            "POST",
            PERIOD_PATH,
            cookie=planner.session_id,
            body=json.dumps(_period(name="Changed name")).encode(),
        )
        assert status == 400
        assert json.loads(body)["code"] == "P6_FINANCIAL_PERIOD_REQUEST_INVALID"
    finally:
        runtime.close()


def test_preview_financial_period_http_rejects_invalid_dates_before_persisting(
    tmp_path: Path,
) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        invalid_periods = (
            _period(start_date="2026-02-30", end_date="2026-03-31"),
            _period(start_date="2026-10-01", end_date="2026-09-30"),
        )
        for invalid in invalid_periods:
            status, body = _request(
                runtime.app,
                "POST",
                PERIOD_PATH,
                cookie=planner.session_id,
                body=json.dumps(invalid).encode(),
            )
            assert status == 400, body[:300]
            assert json.loads(body)["code"] == "P6_FINANCIAL_PERIOD_REQUEST_INVALID"

        status, body = _request(runtime.app, "GET", PERIOD_PATH, cookie=planner.session_id)
        assert status == 200, body[:300]
        assert json.loads(body)["financial_periods"] == []
    finally:
        runtime.close()


def test_preview_earned_value_read_model_measures_stored_baseline_facts(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        _seed_baseline(runtime)
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        payload = {
            "contract_version": "p6-earned-value-read-model.v1",
            "baseline_id": "BL-PREVIEW-1",
            "data_date": "2026-10-12",
            "currency": "USD",
            "etc_method": "PF_ONE",
        }
        status, body = _request(
            runtime.app,
            "POST",
            EVM_PATH,
            cookie=planner.session_id,
            body=json.dumps(payload).encode(),
        )
        assert status == 200, body[:600]
        measured = json.loads(body)
        assert measured["contract_version"] == "p6-earned-value-read-model.v1"
        assert measured["kind"] == "p6_earned_value_read_model"
        assert measured["baseline_id"] == "BL-PREVIEW-1"
        assert measured["data_date"] == "2026-10-12"
        assert measured["currency"] == "USD"
        assert measured["earned_value"]["budget_at_completion"] == "3500.00"
        assert measured["earned_value"]["planned_value"]
        assert measured["earned_value"]["earned_value"]
        assert measured["earned_value"]["actual_cost"]
        assert measured["pv_method"]
        assert isinstance(measured["activities"], list)

        # The request never supplies computed values; extra fields fail closed.
        status, body = _request(
            runtime.app,
            "POST",
            EVM_PATH,
            cookie=planner.session_id,
            body=json.dumps({**payload, "planned_value": "999"}).encode(),
        )
        assert status == 400
        assert json.loads(body)["code"] == "EVM_REQUEST_UNKNOWN_FIELD"

        status, body = _request(
            runtime.app,
            "POST",
            EVM_PATH,
            cookie=planner.session_id,
            body=json.dumps({**payload, "baseline_id": "MISSING"}).encode(),
        )
        assert status == 404
        assert json.loads(body)["code"].startswith("EVM_BASELINE_ACTIVITIES_EMPTY")
    finally:
        runtime.close()
