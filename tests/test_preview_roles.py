from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

RPS_PROJECT = "preview-rps-01"


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


def _path(role_id: str = "") -> str:
    suffix = f"/{role_id}" if role_id else ""
    return f"/api/projects/{RPS_PROJECT}/p6/roles{suffix}"


def test_preview_roles_are_composed_and_persisted(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, body = _request(runtime.app, "GET", _path(), cookie=planner.session_id)
        assert status == 200, body[:300]
        assert json.loads(body) == {"contract_version": "p6-role-api.v1", "roles": []}

        payload = {
            "role_id": "RPS-ROLE-CIVIL",
            "name": "Civil Engineer",
            "description": "Site civil engineering role",
        }
        status, body = _request(
            runtime.app,
            "POST",
            _path(),
            cookie=planner.session_id,
            body=json.dumps(payload).encode(),
        )
        assert status == 200, body[:300]
        created = json.loads(body)["role"]
        assert created == {
            "role_id": "RPS-ROLE-CIVIL",
            "name": "Civil Engineer",
            "description": "Site civil engineering role",
            "parent_role_id": None,
            "calculate_costs_from_units": True,
            "record_revision": 1,
        }

        status, body = _request(
            runtime.app,
            "PATCH",
            _path("RPS-ROLE-CIVIL"),
            cookie=planner.session_id,
            body=json.dumps(
                {
                    "name": "Senior Civil Engineer",
                    "description": "Site civil engineering role",
                    "expected_revision": 1,
                }
            ).encode(),
        )
        assert status == 200, body[:300]
        updated = json.loads(body)["role"]
        assert updated["name"] == "Senior Civil Engineer"
        assert updated["record_revision"] == 2

        # A second runtime over the same file must read the persisted rows,
        # proving the route is backed by the repository rather than memory.
        reopened = open_preview_runtime(tmp_path / "preview.sqlite3")
        try:
            reader = reopened.sessions.create(DEMO_USERS_BY_ROLE["planner"])
            status, body = _request(reopened.app, "GET", _path(), cookie=reader.session_id)
            assert status == 200, body[:300]
            assert json.loads(body)["roles"] == [
                {
                    "contract_version": "p6-role-api.v1",
                    "kind": "p6_role",
                    "scope": {
                        "tenant_id": "cubi-preview-tenant",
                        "project_id": RPS_PROJECT,
                        "project_revision": 7,
                    },
                    "role": updated,
                }
            ]
        finally:
            reopened.close()
    finally:
        runtime.close()


def test_preview_role_writes_are_authorized_and_revision_checked(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
        status, body = _request(
            runtime.app,
            "POST",
            _path(),
            cookie=viewer.session_id,
            body=json.dumps({"role_id": "ROLE-1", "name": "Role"}).encode(),
        )
        assert status == 403
        assert "AUTHORIZATION_PERMISSION_DENIED" in json.loads(body)["code"]

        status, body = _request(runtime.app, "GET", _path(), cookie=viewer.session_id)
        assert status == 200, body[:300]

        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, _ = _request(
            runtime.app,
            "POST",
            _path(),
            cookie=planner.session_id,
            body=json.dumps({"role_id": "ROLE-1", "name": "Role"}).encode(),
        )
        assert status == 200

        status, body = _request(
            runtime.app,
            "PATCH",
            _path("ROLE-1"),
            cookie=planner.session_id,
            body=json.dumps(
                {"name": "Role v2", "expected_revision": 5}
            ).encode(),
        )
        assert status == 409
        assert json.loads(body)["code"] == "REVISION_CONFLICT"
    finally:
        runtime.close()


def test_preview_role_rates_limits_and_proficiency_persist_across_reopen(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, _ = _request(
            runtime.app, "POST", _path(), cookie=planner.session_id,
            body=json.dumps({"role_id": "ROLE-CIVIL", "name": "Civil"}).encode(),
        )
        assert status == 200
        status, body = _request(
            runtime.app, "POST", _path("ROLE-CIVIL") + "/rates",
            cookie=planner.session_id,
            body=json.dumps({
                "effective_from": "2026-12-01", "rate_type": "Standard",
                "rate": "25.5", "unit": "h", "currency": "USD",
            }).encode(),
        )
        assert status == 200, body[:300]
        status, body = _request(
            runtime.app, "POST", _path("ROLE-CIVIL") + "/limits",
            cookie=planner.session_id,
            body=json.dumps({
                "effective_from": "2026-12-01", "max_units": "8", "unit_basis": "units",
            }).encode(),
        )
        assert status == 200, body[:300]
        status, body = _request(
            runtime.app, "POST", _path("ROLE-CIVIL") + "/resources",
            cookie=planner.session_id,
            body=json.dumps({
                "resource_id": "RPS-CIVIL-CREW", "proficiency": "Expert", "is_primary": True,
            }).encode(),
        )
        assert status == 200, body[:300]
        assert json.loads(body)["resource"]["proficiency"] == "expert"

        reopened = open_preview_runtime(tmp_path / "preview.sqlite3")
        try:
            reader = reopened.sessions.create(DEMO_USERS_BY_ROLE["planner"])
            status, body = _request(reopened.app, "GET", _path("ROLE-CIVIL") + "/rates", cookie=reader.session_id)
            assert status == 200
            rates = json.loads(body)["rates"]
            assert [(item["effective_from"], item["rate_type"], item["rate"]) for item in rates] == [
                ("2026-12-01", "Standard", "25.5")
            ]
            status, body = _request(reopened.app, "GET", _path("ROLE-CIVIL") + "/limits", cookie=reader.session_id)
            assert status == 200
            limits = json.loads(body)["limits"]
            assert [(item["effective_from"], item["max_units"]) for item in limits] == [("2026-12-01", "8")]
            status, body = _request(reopened.app, "GET", _path("ROLE-CIVIL") + "/resources", cookie=reader.session_id)
            assert status == 200
            resources = json.loads(body)["resources"]
            assert [(item["resource_id"], item["proficiency"], item["is_primary"]) for item in resources] == [
                ("RPS-CIVIL-CREW", "expert", True)
            ]
        finally:
            reopened.close()
    finally:
        runtime.close()
