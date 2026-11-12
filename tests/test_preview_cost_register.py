from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

PROJECT = "preview-rps-01"
COST = f"/api/projects/{PROJECT}/cost"


def _request(app, method: str, path: str, *, body: dict | None = None, cookie: str | None = None):
    raw = b"" if body is None else json.dumps(body).encode()
    environ: dict[str, object] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path.split("?", 1)[0],
        "QUERY_STRING": path.split("?", 1)[1] if "?" in path else "",
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


def _account(**overrides):
    payload = {
        "account_id": "CA-PREVIEW-1",
        "name": "Direct costs",
        "parent_account_id": None,
        "description": "Direct project costs",
        "is_default": True,
        "idempotency_key": "idem-account-1",
    }
    payload.update(overrides)
    return payload


def _expense(**overrides):
    payload = {
        "expense_id": "EX-PREVIEW-1",
        "name": "Concrete delivery",
        "category": "material",
        "currency": "USD",
        "activity_id": "A-1000",
        "wbs_id": "WBS-1",
        "cost_account_id": "CA-PREVIEW-1",
        "expense_date": "2026-11-01",
        "accrual_date": "2026-11-02",
        "planned_amount": "1000.00",
        "actual_amount": "900.00",
        "remaining_amount": "100.00",
        "note": "Batch 4",
        "idempotency_key": "idem-expense-1",
    }
    payload.update(overrides)
    return payload


def test_preview_cost_accounts_expenses_and_summary_persist(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])

        status, body = _request(
            runtime.app, "GET", f"{COST}/accounts", cookie=planner.session_id
        )
        assert status == 200, body[:300]
        assert json.loads(body) == {
            "contract_version": "p6-cost-api.v1",
            "cost_accounts": [],
        }

        status, body = _request(
            runtime.app,
            "POST",
            f"{COST}/accounts",
            body=_account(),
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        created = json.loads(body)
        assert created["revision"] == 1 and created["is_default"] is True

        status, body = _request(
            runtime.app,
            "POST",
            f"{COST}/accounts/CA-PREVIEW-1/copy",
            body={
                "account_id": "CA-PREVIEW-2",
                "name": "Direct costs copy",
                "idempotency_key": "idem-copy-1",
            },
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        assert json.loads(body)["description"] == "Direct project costs"

        status, body = _request(
            runtime.app,
            "POST",
            f"{COST}/expenses",
            body=_expense(),
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        assert json.loads(body)["planned_amount"] == "1000.00"

        status, body = _request(
            runtime.app,
            "PATCH",
            f"{COST}/expenses/EX-PREVIEW-1",
            body=_expense(actual_amount="1000.00", expected_revision=1),
            cookie=planner.session_id,
        )
        assert status == 200, body[:300]
        assert json.loads(body)["revision"] == 2

        status, body = _request(
            runtime.app,
            "PATCH",
            f"{COST}/expenses/EX-PREVIEW-1",
            body=_expense(actual_amount="1.00", expected_revision=1),
            cookie=planner.session_id,
        )
        assert status == 409, body[:300]
        assert json.loads(body)["code"] == "COST_REVISION_CONFLICT"

        status, body = _request(runtime.app, "GET", f"{COST}/summary", cookie=viewer.session_id)
        assert status == 200, body[:300]
        assert json.loads(body)["currencies"] == [
            {
                "currency": "USD",
                "planned_amount": "1000.00",
                "actual_amount": "1000.00",
                "remaining_amount": "100.00",
                "expense_count": 1,
            }
        ]

        status, body = _request(
            runtime.app,
            "POST",
            f"{COST}/expenses",
            body=_expense(expense_id="EX-PREVIEW-2", idempotency_key="idem-expense-2"),
            cookie=viewer.session_id,
        )
        assert status == 403, body[:300]

        # The WSGI layer must carry the filter query, not silently return all rows.
        status, body = _request(
            runtime.app,
            "GET",
            f"{COST}/expenses?category=material&search=concrete",
            cookie=viewer.session_id,
        )
        assert status == 200, body[:300]
        assert [item["expense_id"] for item in json.loads(body)["expenses"]] == [
            "EX-PREVIEW-1"
        ]

        status, body = _request(
            runtime.app,
            "DELETE",
            f"{COST}/accounts/CA-PREVIEW-1?expected_revision=1",
            cookie=planner.session_id,
        )
        assert status == 409, body[:300]
        assert json.loads(body)["code"] == "COST_ACCOUNT_IN_USE"

        reopened = open_preview_runtime(tmp_path / "preview.sqlite3")
        try:
            reader = reopened.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
            status, body = _request(
                reopened.app, "GET", f"{COST}/expenses", cookie=reader.session_id
            )
            assert status == 200, body[:300]
            stored = json.loads(body)["expenses"]
            assert [item["expense_id"] for item in stored] == ["EX-PREVIEW-1"]
            assert stored[0]["revision"] == 2
            status, body = _request(
                reopened.app,
                "GET",
                f"{COST}/expenses/EX-PREVIEW-1/history",
                cookie=reader.session_id,
            )
            assert status == 200, body[:300]
            assert [event["event_type"] for event in json.loads(body)["events"]] == [
                "created",
                "updated",
            ]
            status, body = _request(
                reopened.app, "GET", f"{COST}/summary", cookie=reader.session_id
            )
            assert json.loads(body)["currencies"][0]["actual_amount"] == "1000.00"
        finally:
            reopened.close()
    finally:
        runtime.close()
