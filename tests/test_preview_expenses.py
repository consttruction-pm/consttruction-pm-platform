from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

RPS_PROJECT = "preview-rps-01"
EXPENSE_PATH = f"/api/projects/{RPS_PROJECT}/p6/expenses"
ACCOUNT_PATH = f"/api/projects/{RPS_PROJECT}/p6/cost-accounts"


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


def _expense(**overrides):
    payload = {
        "contract_version": "p6-expense-api.v1",
        "expense_id": "EXP-PREVIEW-100",
        "name": "Concrete pump rental",
        "category": "Equipment",
        "activity_id": "A100",
        "wbs_id": None,
        "expense_date": "2026-10-01",
        "planned_cost": "1250.50",
        "actual_cost": None,
        "remaining_cost": "1250.50",
        "currency": "USD",
        "note": "Seeded by the preview expense surface test",
    }
    payload.update(overrides)
    return payload


def _account(**overrides):
    payload = {
        "contract_version": "p6-cost-account-api.v1",
        "account_id": "CA-PREVIEW-CIVIL",
        "name": "Civil works",
        "parent_account_id": None,
        "description": "Civil cost account",
    }
    payload.update(overrides)
    return payload


def test_preview_expenses_are_composed_and_persisted(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, body = _request(runtime.app, "GET", EXPENSE_PATH, cookie=planner.session_id)
        assert status == 200, body[:300]
        assert json.loads(body) == {"contract_version": "p6-expense-api.v1", "expenses": []}

        status, body = _request(
            runtime.app,
            "POST",
            EXPENSE_PATH,
            cookie=planner.session_id,
            body=json.dumps(_expense()).encode(),
        )
        assert status == 200, body[:300]
        created = json.loads(body)
        assert created["contract_version"] == "p6-expense-api.v1"
        assert created["kind"] == "p6_expense"
        assert created["expense"]["expense_id"] == "EXP-PREVIEW-100"
        assert created["expense"]["activity_id"] == "A100"
        assert created["expense"]["planned_cost"] == "1250.50"
        assert created["expense"]["actual_cost"] is None

        status, body = _request(runtime.app, "GET", EXPENSE_PATH, cookie=planner.session_id)
        assert status == 200, body[:300]
        listed = json.loads(body)
        assert [item["expense"]["expense_id"] for item in listed["expenses"]] == ["EXP-PREVIEW-100"]

        status, body = _request(
            runtime.app,
            "GET",
            f"{EXPENSE_PATH}/EXP-PREVIEW-100",
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        assert json.loads(body)["expense"]["currency"] == "USD"

        # A second runtime over the same file must read the persisted row.
        reopened = open_preview_runtime(tmp_path / "preview.sqlite3")
        try:
            reader = reopened.sessions.create(DEMO_USERS_BY_ROLE["planner"])
            status, body = _request(reopened.app, "GET", EXPENSE_PATH, cookie=reader.session_id)
            assert status == 200, body[:300]
            stored = json.loads(body)["expenses"]
            assert stored[0]["expense"]["expense_id"] == "EXP-PREVIEW-100"
            assert stored[0]["scope"]["project_revision"] == 7
        finally:
            reopened.close()
    finally:
        runtime.close()


def test_preview_cost_accounts_are_composed_and_persisted(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, body = _request(runtime.app, "GET", ACCOUNT_PATH, cookie=planner.session_id)
        assert status == 200, body[:300]
        assert json.loads(body) == {
            "contract_version": "p6-cost-account-api.v1",
            "cost_accounts": [],
        }

        status, body = _request(
            runtime.app,
            "POST",
            ACCOUNT_PATH,
            cookie=planner.session_id,
            body=json.dumps(_account()).encode(),
        )
        assert status == 200, body[:300]
        created = json.loads(body)
        assert created["kind"] == "p6_cost_account"
        assert created["cost_account"]["account_id"] == "CA-PREVIEW-CIVIL"
        assert created["cost_account"]["parent_account_id"] is None

        status, body = _request(runtime.app, "GET", ACCOUNT_PATH, cookie=planner.session_id)
        assert status == 200, body[:300]
        listed = json.loads(body)["cost_accounts"]
        assert [item["cost_account"]["account_id"] for item in listed] == ["CA-PREVIEW-CIVIL"]

        reopened = open_preview_runtime(tmp_path / "preview.sqlite3")
        try:
            reader = reopened.sessions.create(DEMO_USERS_BY_ROLE["planner"])
            status, body = _request(reopened.app, "GET", ACCOUNT_PATH, cookie=reader.session_id)
            assert status == 200, body[:300]
            stored = json.loads(body)["cost_accounts"]
            assert stored[0]["cost_account"]["description"] == "Civil cost account"
            assert stored[0]["scope"]["project_revision"] == 7
        finally:
            reopened.close()
    finally:
        runtime.close()


def test_preview_expense_and_cost_account_writes_are_authorized_and_immutable(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
        status, body = _request(
            runtime.app,
            "POST",
            EXPENSE_PATH,
            cookie=viewer.session_id,
            body=json.dumps(_expense()).encode(),
        )
        assert status == 403
        assert "project.write" in json.loads(body)["code"]

        status, body = _request(
            runtime.app,
            "POST",
            ACCOUNT_PATH,
            cookie=viewer.session_id,
            body=json.dumps(_account()).encode(),
        )
        assert status == 403
        assert "project.write" in json.loads(body)["code"]

        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, body = _request(
            runtime.app,
            "POST",
            EXPENSE_PATH,
            cookie=planner.session_id,
            body=json.dumps(_expense()).encode(),
        )
        assert status == 200, body[:300]

        # The core treats stored expenses as immutable; a changed value under the
        # same ID must fail instead of being silently overwritten by the page.
        status, body = _request(
            runtime.app,
            "POST",
            EXPENSE_PATH,
            cookie=planner.session_id,
            body=json.dumps(_expense(planned_cost="999.00")).encode(),
        )
        assert status == 400
        assert json.loads(body)["code"] == "P6_EXPENSE_REQUEST_INVALID"

        status, body = _request(
            runtime.app,
            "POST",
            ACCOUNT_PATH,
            cookie=planner.session_id,
            body=json.dumps(_account()).encode(),
        )
        assert status == 200, body[:300]

        status, body = _request(
            runtime.app,
            "POST",
            ACCOUNT_PATH,
            cookie=planner.session_id,
            body=json.dumps(_account(name="Changed civil works")).encode(),
        )
        assert status == 400
        assert json.loads(body)["code"] == "P6_COST_ACCOUNT_REQUEST_INVALID"

        status, body = _request(
            runtime.app,
            "POST",
            ACCOUNT_PATH,
            cookie=planner.session_id,
            body=json.dumps(_account(account_id="CA-PREVIEW-SELF", parent_account_id="CA-PREVIEW-SELF")).encode(),
        )
        assert status == 400
        assert json.loads(body)["code"] == "P6_COST_ACCOUNT_REQUEST_INVALID"
    finally:
        runtime.close()
