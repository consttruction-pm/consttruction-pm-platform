from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

PROJECT = "preview-rps-01"
BASE = f"/api/projects/{PROJECT}/administration"


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


def _entry(**overrides):
    payload = {
        "dictionary_code": "cost_category",
        "entry_id": "LABOUR",
        "label": "Labour",
        "sequence": 10,
        "is_active": True,
        "idempotency_key": "admin-dict-1",
    }
    payload.update(overrides)
    return payload


def test_administration_defaults_matrix_and_viewer_read(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])

        status, body = _request(
            runtime.app, "GET", f"{BASE}/preferences", cookie=viewer.session_id
        )
        assert status == 200, body[:400]
        defaults = json.loads(body)
        assert defaults["contract_version"] == "p6-administration-api.v1"
        assert defaults["currency"] == "USD"
        assert defaults["unit_of_measure"] == "day"
        assert defaults["date_display"] == "gregorian"
        assert defaults["decimal_places"] == 2
        assert defaults["fiscal_year_start_month"] == 1
        assert defaults["revision"] == 0
        assert defaults["updated_at"] is None

        status, body = _request(
            runtime.app, "GET", f"{BASE}/permission-matrix", cookie=viewer.session_id
        )
        assert status == 200, body[:400]
        matrix = json.loads(body)
        roles = {entry["role"]: entry["permissions"] for entry in matrix["roles"]}
        assert set(roles) == {"planner", "project_admin", "viewer"}
        assert roles["viewer"] == ["form.read", "knowledge.read", "project.read"]
        assert "project.admin" in roles["project_admin"]
        assert "project.admin" not in roles["planner"]
        assert "form.approve" in roles["project_admin"]
        assert matrix["permissions"] == sorted(matrix["permissions"])
        assert len(matrix["permissions"]) == 19
    finally:
        runtime.close()


def test_preferences_are_admin_only_and_revision_guarded(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])

        updated = {
            "currency": "IRR",
            "unit_of_measure": "hour",
            "date_display": "jalali",
            "decimal_places": 0,
            "fiscal_year_start_month": 4,
            "expected_revision": 0,
        }
        status, body = _request(
            runtime.app, "PUT", f"{BASE}/preferences", body=updated, cookie=admin.session_id
        )
        assert status == 200, body[:400]
        saved = json.loads(body)
        assert saved["currency"] == "IRR"
        assert saved["date_display"] == "jalali"
        assert saved["fiscal_year_start_month"] == 4
        assert saved["revision"] == 1
        assert saved["updated_by"] == "preview-admin"

        status, body = _request(
            runtime.app,
            "PUT",
            f"{BASE}/preferences",
            body={**updated, "expected_revision": 0},
            cookie=admin.session_id,
        )
        assert status == 409, body[:400]
        assert json.loads(body)["code"] == "ADMIN_PREFERENCES_REVISION_CONFLICT"

        status, body = _request(
            runtime.app, "PUT", f"{BASE}/preferences", body=updated, cookie=planner.session_id
        )
        assert status == 403, body[:400]
        assert json.loads(body)["code"] == "ADMIN_PERMISSION_DENIED"

        status, body = _request(
            runtime.app,
            "PUT",
            f"{BASE}/preferences",
            body={**updated, "currency": "usd", "expected_revision": 1},
            cookie=admin.session_id,
        )
        assert status == 400, body[:400]

        status, body = _request(
            runtime.app, "GET", f"{BASE}/preferences", cookie=planner.session_id
        )
        assert status == 200, body[:400]
        assert json.loads(body)["currency"] == "IRR"
    finally:
        runtime.close()


def test_dictionary_crud_idempotency_and_history(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/dictionaries",
            body=_entry(),
            cookie=admin.session_id,
        )
        assert status == 200, body[:400]
        created = json.loads(body)
        assert created["entry_id"] == "LABOUR"
        assert created["revision"] == 1
        assert created["dictionary_code"] == "cost_category"

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/dictionaries",
            body=_entry(),
            cookie=admin.session_id,
        )
        assert status == 200, body[:400]
        assert json.loads(body)["revision"] == 1

        status, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/dictionaries?dictionary_code=cost_category&search=lab",
            cookie=admin.session_id,
        )
        assert status == 200, body[:400]
        listed = json.loads(body)
        assert [entry["entry_id"] for entry in listed["entries"]] == ["LABOUR"]
        assert "expense_category" in listed["dictionary_codes"]

        status, body = _request(
            runtime.app,
            "PATCH",
            f"{BASE}/dictionaries/cost_category/LABOUR",
            body={
                "label": "Direct labour",
                "sequence": 5,
                "is_active": False,
                "expected_revision": 1,
            },
            cookie=admin.session_id,
        )
        assert status == 200, body[:400]
        revised = json.loads(body)
        assert revised["label"] == "Direct labour"
        assert revised["is_active"] is False
        assert revised["revision"] == 2

        status, body = _request(
            runtime.app,
            "PATCH",
            f"{BASE}/dictionaries/cost_category/LABOUR",
            body={"label": "Stale", "expected_revision": 1},
            cookie=admin.session_id,
        )
        assert status == 409, body[:400]
        assert json.loads(body)["code"] == "ADMIN_DICTIONARY_REVISION_CONFLICT"

        status, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/history",
            cookie=admin.session_id,
        )
        assert status == 200, body[:400]
        actions = [event["action"] for event in json.loads(body)["events"]]
        assert actions.count("created") == 1
        assert actions.count("updated") == 1

        status, body = _request(
            runtime.app,
            "DELETE",
            f"{BASE}/dictionaries/cost_category/LABOUR",
            body={"expected_revision": 2},
            cookie=admin.session_id,
        )
        assert status == 200, body[:400]
        assert json.loads(body)["deleted"] is True

        status, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/dictionaries/cost_category/LABOUR",
            cookie=admin.session_id,
        )
        assert status == 404, body[:400]
        assert json.loads(body)["code"] == "ADMIN_DICTIONARY_NOT_FOUND"

        status, body = _request(
            runtime.app,
            "GET",
            f"{BASE}/history",
            cookie=admin.session_id,
        )
        actions = [event["action"] for event in json.loads(body)["events"]]
        assert actions.count("deleted") == 1
    finally:
        runtime.close()


def test_dictionary_validation_and_idempotency_reuse(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/dictionaries",
            body=_entry(idempotency_key=""),
            cookie=admin.session_id,
        )
        assert status == 400, body[:400]

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/dictionaries",
            body=_entry(dictionary_code="unknown_code"),
            cookie=admin.session_id,
        )
        assert status == 400, body[:400]

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/dictionaries",
            body=_entry(entry_id="bad entry"),
            cookie=admin.session_id,
        )
        assert status == 400, body[:400]

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/dictionaries",
            body=_entry(),
            cookie=admin.session_id,
        )
        assert status == 200, body[:400]

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/dictionaries",
            body=_entry(label="Different payload"),
            cookie=admin.session_id,
        )
        assert status == 409, body[:400]
        assert json.loads(body)["code"] == "ADMIN_IDEMPOTENCY_KEY_REUSE"

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/dictionaries",
            body=_entry(idempotency_key="admin-dict-2"),
            cookie=admin.session_id,
        )
        assert status == 409, body[:400]
        assert json.loads(body)["code"] == "ADMIN_DICTIONARY_ID_ALREADY_EXISTS"

        status, body = _request(
            runtime.app,
            "POST",
            f"{BASE}/dictionaries",
            body=_entry(entry_id="PLANT", idempotency_key="admin-dict-3"),
            cookie=viewer.session_id,
        )
        assert status == 403, body[:400]
        assert json.loads(body)["code"] == "ADMIN_PERMISSION_DENIED"
    finally:
        runtime.close()
