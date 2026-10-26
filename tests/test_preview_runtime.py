from __future__ import annotations

import json
import sqlite3
from io import BytesIO
from pathlib import Path

import pytest

from construction_pm.preview.runtime import PreviewRuntimeError, open_preview_runtime
from construction_pm.preview.server import build_preview_application
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

RPS_PROJECT = "preview-rps-01"
RPS_REVISION = 7
RPS_TENANT = "cubi-preview-tenant"


def _web_root(tmp_path: Path) -> Path:
    root = tmp_path / "web"
    source = root / "dist" / "web" / "src"
    source.mkdir(parents=True)
    (source / "landing-entry.js").write_text("export {};\n", encoding="utf-8")
    (root / "app.html").write_text(
        '<!doctype html><html><body><div id="app"></div></body></html>',
        encoding="utf-8",
    )
    (root / "styles.css").write_text("body { margin: 0; }\n", encoding="utf-8")
    return root


def _request(
    app,
    method: str,
    path: str,
    *,
    body: bytes = b"",
    cookie: str | None = None,
    headers: dict[str, str] | None = None,
    content_type: str = "application/json",
):
    environ: dict[str, object] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
    }
    if body:
        environ["CONTENT_TYPE"] = content_type
    if cookie is not None:
        environ["HTTP_COOKIE"] = f"cp_session={cookie}"
    for key, value in (headers or {}).items():
        environ["HTTP_" + key.upper().replace("-", "_")] = value
    captured: dict[str, object] = {}

    def start_response(status, response_headers) -> None:
        captured["status"] = status
        captured["headers"] = response_headers

    chunks = b"".join(app(environ, start_response))
    status_code = int(str(captured["status"]).split(" ", 1)[0])
    response_headers = {
        str(key).lower(): str(value)
        for key, value in captured.get("headers", [])  # type: ignore[union-attr]
    }
    return status_code, response_headers, chunks


def _session_cookie(headers: dict[str, str]) -> str:
    raw = headers["set-cookie"]
    return raw.split(";", 1)[0].split("=", 1)[1]


def _scope_headers() -> dict[str, str]:
    return {
        "X-Tenant-Id": RPS_TENANT,
        "X-Project-Id": RPS_PROJECT,
        "X-Project-Revision": str(RPS_REVISION),
    }


def test_preview_database_guard_refuses_and_preserves_foreign_sqlite(tmp_path: Path) -> None:
    database = tmp_path / "workspace.sqlite3"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE real_work (id INTEGER PRIMARY KEY, title TEXT)")
    connection.execute("INSERT INTO real_work(title) VALUES ('do not lose')")
    connection.commit()
    connection.close()

    with pytest.raises(PreviewRuntimeError) as excinfo:
        open_preview_runtime(database, reset=True)

    assert excinfo.value.code == "PREVIEW_DATABASE_NOT_OWNED"
    connection = sqlite3.connect(database)
    try:
        assert connection.execute("SELECT title FROM real_work").fetchall() == [
            ("do not lose",)
        ]
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name='preview_meta'"
            ).fetchone()
            is None
        )
    finally:
        connection.close()


def test_preview_runtime_serves_real_calculated_reads_and_rejects_stale_revision(
    tmp_path: Path,
) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        health = runtime.health()
        assert health["mode"] == "local-full-stack-preview"
        assert health["seed_version"] == "cubi-preview-seed.v1"
        assert health["project_count"] == 2
        assert health["demo_project_count"] == 2
        assert health["activity_count"] == 20

        session = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, _, body = _request(
            runtime.app, "GET", "/api/session", cookie=session.session_id
        )
        assert status == 200
        assert json.loads(body)["roles"] == ["planner"]

        status, _, body = _request(
            runtime.app,
            "GET",
            "/api/v1/workspace/control-room/read",
            cookie=session.session_id,
            headers=_scope_headers(),
        )
        assert status == 200
        envelope = json.loads(body)
        assert envelope["contract_version"] == "workspace-control-room-read.v1"
        workspace = envelope["workspace"]
        assert len(workspace["activities"]) == 14
        assert [column["id"] for column in workspace["columns"]][:2] == [
            "activity.id",
            "activity.name",
        ]
        assert len(workspace["columns"]) == 20

        a130 = next(
            activity
            for activity in workspace["activities"]
            if activity["id"] == "A130"
        )
        assert a130["wbs_id"] == "2 Civil works"
        assert a130["cells"]["activity.early_start"] == "2026-10-07"
        assert a130["cells"]["activity.early_finish"] == "2026-10-13"
        assert a130["cells"]["activity.total_float"] == -3
        assert a130["cells"]["activity.is_critical"] is True
        assert a130["gantt"] == {
            "start": "2026-10-07",
            "finish": "2026-10-13",
            "progressPercent": 37.5,
            "critical": True,
        }

        stale_headers = {**_scope_headers(), "X-Project-Revision": "8"}
        status, _, body = _request(
            runtime.app,
            "GET",
            "/api/v1/workspace/control-room/read",
            cookie=session.session_id,
            headers=stale_headers,
        )
        assert status == 400
        assert json.loads(body)["code"] == "REVISION_CONFLICT"
    finally:
        runtime.close()


def test_preview_server_guards_login_banner_static_files_and_logout(
    tmp_path: Path,
) -> None:
    runtime = open_preview_runtime(
        tmp_path / "preview.sqlite3",
        web_root=_web_root(tmp_path),
        reset=True,
    )
    try:
        app = build_preview_application(runtime)

        status, headers, _ = _request(app, "GET", "/app")
        assert status == 302
        assert headers["location"] == "/preview/login?next=%2Fapp"

        status, _, body = _request(app, "GET", "/preview/health")
        assert status == 200
        health = json.loads(body)
        assert health["production"] is False
        assert health["demo_data"] is True
        assert health["database"].endswith("preview.sqlite3")

        status, headers, _ = _request(
            app,
            "POST",
            "/preview/login",
            body=b"role=planner&next=%2Fapp",
            content_type="application/x-www-form-urlencoded",
        )
        assert status == 303
        assert headers["location"] == "/app"
        cookie = _session_cookie(headers)

        status, _, body = _request(app, "GET", "/app", cookie=cookie)
        assert status == 200
        assert b"LOCAL PREVIEW" in body
        assert b"preview-planner" in body

        status, _, body = _request(app, "GET", "/api/session", cookie=cookie)
        assert status == 200
        assert json.loads(body)["roles"] == ["planner"]

        status, _, body = _request(app, "GET", "/dist/web/src/landing-entry.js")
        assert status == 200
        assert body.startswith(b"export {};")

        status, _, _ = _request(app, "GET", "/.preview/cubi-preview.sqlite3")
        assert status == 404

        status, _, _ = _request(app, "GET", "/api/session")
        assert status == 401

        status, headers, _ = _request(app, "POST", "/preview/logout", cookie=cookie)
        assert status == 303
        assert headers["location"] == "/preview/login"

        status, _, _ = _request(app, "GET", "/api/session", cookie=cookie)
        assert status == 401
    finally:
        runtime.close()


def test_preview_interchange_round_trip_uses_real_codec_and_mappings(
    tmp_path: Path,
) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        export_path = (
            f"/api/projects/{RPS_PROJECT}/p6/interchange/PRIMAVERA_XML/export"
        )
        export_payload = {
            "values": [{"activity.id": "A130", "activity.name": "Earthworks"}],
            "extensions": [{"p6.primavera.xml.object": "Activity"}],
        }
        status, _, body = _request(
            runtime.app,
            "POST",
            export_path,
            cookie=planner.session_id,
            headers=_scope_headers(),
            body=json.dumps(export_payload).encode("utf-8"),
        )
        assert status == 200
        exported = json.loads(body)
        assert exported["contract_version"] == "p6-interchange-api.v1"
        assert exported["format"] == "PRIMAVERA_XML"
        assert exported["document"]["encoding"] == "utf-8"
        document = exported["document"]["data"]
        assert "<Id>A130</Id>" in document
        assert "<Name>Earthworks</Name>" in document

        import_path = (
            f"/api/projects/{RPS_PROJECT}/p6/interchange/PRIMAVERA_XML/import"
        )
        status, _, body = _request(
            runtime.app,
            "POST",
            import_path,
            cookie=planner.session_id,
            headers=_scope_headers(),
            body=document.encode("utf-8"),
            content_type="application/xml",
        )
        assert status == 200
        imported = json.loads(body)
        assert imported["rows"] == [
            {
                "values": {"activity.id": "A130", "activity.name": "Earthworks"},
                "extensions": {"p6.primavera.xml.object": "Activity"},
                "warnings": [],
            }
        ]

        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
        status, _, body = _request(
            runtime.app,
            "POST",
            import_path,
            cookie=viewer.session_id,
            headers=_scope_headers(),
            body=document.encode("utf-8"),
            content_type="application/xml",
        )
        assert status == 403
        assert "authorization denied" in json.loads(body)["code"]
    finally:
        runtime.close()


def test_preview_layout_survives_runtime_restart_and_viewer_write_is_denied(
    tmp_path: Path,
) -> None:
    database = tmp_path / "preview.sqlite3"
    layout_path = f"/api/projects/{RPS_PROJECT}/p6/layouts/project/activity"

    runtime = open_preview_runtime(database, reset=True)
    try:
        session = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, _, body = _request(
            runtime.app,
            "GET",
            layout_path,
            cookie=session.session_id,
            headers=_scope_headers(),
        )
        assert status == 200
        layout = json.loads(body)
        assert layout["revision"] == 1

        columns = layout["columns"]
        columns[0]["visible"] = False
        payload = {
            "revision": 2,
            "columns": columns,
            "metadata": {"source": "preview-runtime-test"},
        }
        status, _, body = _request(
            runtime.app,
            "POST",
            layout_path,
            cookie=session.session_id,
            headers=_scope_headers(),
            body=json.dumps(payload).encode("utf-8"),
        )
        assert status == 200
        assert json.loads(body)["revision"] == 2
    finally:
        runtime.close()

    reopened = open_preview_runtime(database)
    try:
        planner = reopened.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, _, body = _request(
            reopened.app,
            "GET",
            layout_path,
            cookie=planner.session_id,
            headers=_scope_headers(),
        )
        assert status == 200
        stored = json.loads(body)
        assert stored["revision"] == 2
        assert stored["columns"][0]["visible"] is False

        viewer = reopened.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
        denied_payload = {
            "revision": 3,
            "columns": stored["columns"],
            "metadata": {},
        }
        status, _, body = _request(
            reopened.app,
            "POST",
            layout_path,
            cookie=viewer.session_id,
            headers=_scope_headers(),
            body=json.dumps(denied_payload).encode("utf-8"),
        )
        assert status == 403
        assert json.loads(body)["code"] == "authorization denied"

        status, _, body = _request(
            reopened.app, "GET", "/api/session", cookie=viewer.session_id
        )
        assert status == 200
        assert json.loads(body)["roles"] == ["viewer"]
    finally:
        reopened.close()


def test_preview_resource_capacity_read_uses_registered_effective_dated_ceilings(
    tmp_path: Path,
) -> None:
    database = tmp_path / "preview.sqlite3"
    list_path = f"/api/projects/{RPS_PROJECT}/p6/resource-capacities"
    profile_path = f"{list_path}/RPS-CIVIL-CREW"

    runtime = open_preview_runtime(database, reset=True)
    try:
        assert runtime.health()["capacity_segment_count"] == 3
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, _, body = _request(
            runtime.app,
            "GET",
            list_path,
            cookie=planner.session_id,
            headers=_scope_headers(),
        )
        assert status == 200
        payload = json.loads(body)
        assert payload["contract_version"] == "p6-resource-capacity-read-api.v1"
        assert len(payload["capacities"]) == 2
        first, second = payload["capacities"]
        assert first["capacity"]["resource_id"] == "RPS-CIVIL-CREW"
        assert first["capacity"]["max_units"] == "8"
        assert first["capacity"]["unit_basis"] == "day"
        assert first["capacity"]["hours_per_time_period"] == "8"
        assert first["capacity"]["units_per_hour"] == "1"
        assert first["capacity"]["effective_from"] == "2026-09-21"
        assert first["capacity"]["effective_to"] == "2026-10-14"
        assert first["capacity"]["source"] == "preview-fixture:RPS-rev7-capacity-1"
        assert second["capacity"]["max_units"] == "12"
        assert second["capacity"]["effective_from"] == "2026-10-15"
        assert second["capacity"]["effective_to"] is None
        assert len(first["capacity"]["identity"]) == 64
        assert first["capacity"]["identity"] != second["capacity"]["identity"]

        status, _, body = _request(
            runtime.app,
            "GET",
            profile_path,
            cookie=planner.session_id,
            headers=_scope_headers(),
        )
        assert status == 200
        profile = json.loads(body)
        assert profile["kind"] == "resource_capacity_profile"
        assert profile["status"] == "REGISTERED"
        assert profile["resource_id"] == "RPS-CIVIL-CREW"
        assert [segment["max_units"] for segment in profile["segments"]] == [
            "8",
            "12",
        ]

        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
        status, _, body = _request(
            runtime.app,
            "GET",
            profile_path,
            cookie=viewer.session_id,
            headers=_scope_headers(),
        )
        assert status == 200
        assert json.loads(body)["status"] == "REGISTERED"

        status, _, body = _request(
            runtime.app,
            "GET",
            f"{list_path}/UNREGISTERED-RESOURCE",
            cookie=planner.session_id,
            headers=_scope_headers(),
        )
        assert status == 404
        assert json.loads(body)["code"] == "RESOURCE_CAPACITY_NOT_REGISTERED"
    finally:
        runtime.close()

    reopened = open_preview_runtime(database)
    try:
        planner = reopened.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, _, body = _request(
            reopened.app,
            "GET",
            profile_path,
            cookie=planner.session_id,
            headers=_scope_headers(),
        )
        assert status == 200
        persisted = json.loads(body)
        assert [segment["max_units"] for segment in persisted["segments"]] == [
            "8",
            "12",
        ]
        assert persisted["segments"][1]["source"] == "preview-fixture:RPS-rev7-capacity-2"
    finally:
        reopened.close()


def test_preview_project_creation_initializes_real_workspace_and_persists(
    tmp_path: Path,
) -> None:
    database = tmp_path / "preview.sqlite3"
    runtime = open_preview_runtime(database, reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, _, body = _request(
            runtime.app,
            "POST",
            "/api/projects",
            cookie=planner.session_id,
            body=json.dumps(
                {"project_id": "preview-new-01", "name": "New preview project"}
            ).encode("utf-8"),
        )
        assert status == 403
        assert json.loads(body)["code"].startswith("authorization denied")

        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        status, _, body = _request(
            runtime.app,
            "POST",
            "/api/projects",
            cookie=admin.session_id,
            body=json.dumps(
                {"project_id": "preview-new-01", "name": "New preview project"}
            ).encode("utf-8"),
        )
        assert status == 201
        context = json.loads(body)["context"]
        assert context["project_id"] == "preview-new-01"
        new_headers = {
            "X-Tenant-Id": context["tenant_id"],
            "X-Project-Id": context["project_id"],
            "X-Project-Revision": str(context["revision"]),
        }

        status, _, body = _request(
            runtime.app,
            "GET",
            "/api/v1/workspace/control-room/read",
            cookie=planner.session_id,
            headers=new_headers,
        )
        assert status == 200
        workspace = json.loads(body)["workspace"]
        assert workspace["activities"] == []
        assert len(workspace["columns"]) == 20
        assert workspace["columns"][0]["id"] == "activity.id"

        status, _, body = _request(
            runtime.app,
            "GET",
            "/api/projects/preview-new-01/p6/layouts/project/activity",
            cookie=planner.session_id,
            headers=new_headers,
        )
        assert status == 200
        assert json.loads(body)["revision"] == 1

        status, _, body = _request(
            runtime.app,
            "GET",
            "/api/projects/preview-new-01/p6/resource-capacities",
            cookie=planner.session_id,
            headers=new_headers,
        )
        assert status == 200
        assert json.loads(body)["capacities"] == []

        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
        status, _, body = _request(
            runtime.app,
            "POST",
            "/api/projects",
            cookie=viewer.session_id,
            body=json.dumps(
                {"project_id": "preview-viewer-01", "name": "Denied"}
            ).encode("utf-8"),
        )
        assert status == 403
        assert json.loads(body)["code"].startswith("authorization denied")
    finally:
        runtime.close()

    reopened = open_preview_runtime(database)
    try:
        projects = reopened.store.list_for_user(
            "cubi-preview-tenant", DEMO_USERS_BY_ROLE["planner"].user_id
        )
        assert "preview-new-01" in [project.project_id for project in projects]
        created = next(
            project for project in projects if project.project_id == "preview-new-01"
        )
        assert created.name == "New preview project"
    finally:
        reopened.close()
