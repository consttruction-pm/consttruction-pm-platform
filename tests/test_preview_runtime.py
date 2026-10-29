from __future__ import annotations

import json
import sqlite3
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

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
    (root / "cubi-platform-logo-primary.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>\n',
        encoding="utf-8",
    )
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
    parsed_path = urlsplit(path)
    environ: dict[str, object] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": parsed_path.path or "/",
        "QUERY_STRING": parsed_path.query,
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
        assert health["seed_version"] == "cubi-preview-seed.v2"
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


def test_preview_v2_workspace_read_projects_persisted_wbs_tree(
    tmp_path: Path,
) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    try:
        assert runtime.health()["wbs_node_count"] == 10
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, _, body = _request(
            runtime.app,
            "GET",
            "/api/v2/workspace/control-room/read",
            cookie=planner.session_id,
            headers=_scope_headers(),
        )
        assert status == 200
        envelope = json.loads(body)
        assert envelope["contract_version"] == "workspace-control-room-read.v2"
        workspace = envelope["workspace"]
        assert workspace["contract_version"] == "workspace-control-room.v2"
        assert workspace["context"] == {
            "tenant_id": RPS_TENANT,
            "project_id": RPS_PROJECT,
            "revision": RPS_REVISION,
        }

        nodes = workspace["wbs_nodes"]
        assert [node["wbs_id"] for node in nodes] == [
            "WBS-RPS-ROOT",
            "WBS-RPS-PM",
            "WBS-RPS-CIVIL",
            "WBS-RPS-PROC",
            "WBS-RPS-ENV",
            "WBS-RPS-MEP",
            "WBS-RPS-COM",
        ]
        root = nodes[0]
        assert root["parent_kind"] == "project"
        assert root["parent_wbs_id"] is None
        assert root["local_code"] == "1"
        civil = next(node for node in nodes if node["wbs_id"] == "WBS-RPS-CIVIL")
        assert civil["parent_kind"] == "wbs"
        assert civil["parent_wbs_id"] == "WBS-RPS-ROOT"
        assert civil["local_code"] == "2"
        assert civil["name"] == "Civil works"
        assert civil["record_revision"] == 1

        activities = workspace["activities"]
        assert len(activities) == 14
        a130 = next(item for item in activities if item["id"] == "A130")
        assert a130["wbs_id"] == "WBS-RPS-CIVIL"
        assert a130["cells"]["activity.wbs"] == "2 Civil works"
        assert a130["cells"]["activity.early_start"] == "2026-10-07"

        # The second demo project in the same tenant must keep its own tree.
        nse_headers = {
            "X-Tenant-Id": RPS_TENANT,
            "X-Project-Id": "preview-nse-02",
            "X-Project-Revision": "2",
        }
        status, _, body = _request(
            runtime.app,
            "GET",
            "/api/v2/workspace/control-room/read",
            cookie=planner.session_id,
            headers=nse_headers,
        )
        assert status == 200
        nse = json.loads(body)["workspace"]
        assert [node["wbs_id"] for node in nse["wbs_nodes"]] == [
            "WBS-NSE-ROOT",
            "WBS-NSE-DESIGN",
            "WBS-NSE-PROC",
        ]
        assert all(
            not item["wbs_id"].startswith("WBS-RPS-") for item in nse["activities"]
        )

        # Stale revision fails closed instead of serving a different revision.
        status, _, body = _request(
            runtime.app,
            "GET",
            "/api/v2/workspace/control-room/read",
            cookie=planner.session_id,
            headers={**_scope_headers(), "X-Project-Revision": "8"},
        )
        assert status == 409
        assert json.loads(body)["code"] == "STALE_WORKSPACE_READ_SCOPE"
    finally:
        runtime.close()


def test_preview_wbs_and_activity_write_path_persists_and_rejects_invalid_links(
    tmp_path: Path,
) -> None:
    database = tmp_path / "preview.sqlite3"
    runtime = open_preview_runtime(database, reset=True)
    try:
        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        status, _, body = _request(
            runtime.app,
            "POST",
            "/api/projects",
            cookie=admin.session_id,
            body=json.dumps(
                {"project_id": "preview-wbs-01", "name": "WBS acceptance project"}
            ).encode("utf-8"),
        )
        assert status == 201
        context = json.loads(body)["context"]
        headers = {
            "X-Tenant-Id": context["tenant_id"],
            "X-Project-Id": context["project_id"],
            "X-Project-Revision": str(context["revision"]),
        }
        root_id = "WBS-preview-wbs-01"
        wbs_path = "/api/projects/preview-wbs-01/p6/wbs"
        activity_path = "/api/projects/preview-wbs-01/p6/activities"

        def wbs_create(payload: dict, cookie: str = admin.session_id):
            return _request(
                runtime.app,
                "POST",
                wbs_path,
                cookie=cookie,
                headers=headers,
                body=json.dumps(
                    {"contract_version": "p6-wbs-master-api.v1", **payload}
                ).encode("utf-8"),
            )

        def wbs_update(wbs_id: str, payload: dict):
            return _request(
                runtime.app,
                "PATCH",
                f"{wbs_path}/{wbs_id}",
                cookie=admin.session_id,
                headers=headers,
                body=json.dumps(
                    {"contract_version": "p6-wbs-master-api.v1", **payload}
                ).encode("utf-8"),
            )

        def activity_create(payload: dict, cookie: str = admin.session_id):
            return _request(
                runtime.app,
                "POST",
                activity_path,
                cookie=cookie,
                headers=headers,
                body=json.dumps(
                    {"contract_version": "p6-activity-master-api.v1", **payload}
                ).encode("utf-8"),
            )

        # A new project starts with exactly one project-parent WBS root.
        status, _, body = _request(
            runtime.app, "GET", wbs_path, cookie=admin.session_id, headers=headers
        )
        assert status == 200
        nodes = json.loads(body)["wbs_nodes"]
        assert [node["wbs"]["wbs_id"] for node in nodes] == [root_id]
        assert nodes[0]["wbs"]["parent_kind"] == "project"

        status, _, body = wbs_create(
            {
                "wbs_id": "WBS-WBS01-DESIGN",
                "parent_kind": "wbs",
                "parent_wbs_id": root_id,
                "code": "2",
                "name": "Design",
                "sequence_number": 10,
            }
        )
        assert status == 201
        assert json.loads(body)["wbs"]["record_revision"] == 1

        status, _, body = wbs_create(
            {
                "wbs_id": "WBS-WBS01-SITE",
                "parent_kind": "wbs",
                "parent_wbs_id": root_id,
                "code": "3",
                "name": "Site preparation",
                "sequence_number": 20,
            }
        )
        assert status == 201

        # Sibling codes are unique, parents must exist, and cycles are rejected.
        status, _, body = wbs_create(
            {
                "wbs_id": "WBS-WBS01-DUP",
                "parent_kind": "wbs",
                "parent_wbs_id": root_id,
                "code": "2",
                "name": "Duplicate code",
                "sequence_number": 30,
            }
        )
        assert status == 400
        assert json.loads(body)["code"] == "WBS_SIBLING_CODE_CONFLICT"

        status, _, body = wbs_create(
            {
                "wbs_id": "WBS-WBS01-ORPHAN",
                "parent_kind": "wbs",
                "parent_wbs_id": "WBS-RPS-CIVIL",
                "code": "9",
                "name": "Foreign parent",
                "sequence_number": 40,
            }
        )
        assert status == 400
        assert json.loads(body)["code"] == "WBS_PARENT_NOT_FOUND_OR_SCOPE_MISMATCH"

        status, _, body = wbs_update(
            root_id,
            {
                "parent_kind": "wbs",
                "parent_wbs_id": "WBS-WBS01-DESIGN",
                "expected_revision": 1,
            },
        )
        assert status == 400
        assert json.loads(body)["code"] == "WBS_HIERARCHY_CYCLE"

        status, _, body = wbs_update(
            "WBS-WBS01-DESIGN", {"name": "Detailed design", "expected_revision": 1}
        )
        assert status == 200
        assert json.loads(body)["wbs"]["record_revision"] == 2
        status, _, body = wbs_update(
            "WBS-WBS01-DESIGN", {"name": "Stale write", "expected_revision": 1}
        )
        assert status == 409
        assert json.loads(body)["code"] == "REVISION_CONFLICT"

        # Activities require a canonical WBS and reject a foreign-project node.
        status, _, body = activity_create(
            {
                "activity_id": "NEW-101",
                "name": "No hierarchy link",
                "duration_value": 2,
                "duration_unit": "working-day",
            }
        )
        assert status == 400
        assert json.loads(body)["code"] == "WBS_REQUIRED"

        status, _, body = activity_create(
            {
                "activity_id": "NEW-102",
                "name": "Foreign WBS",
                "duration_value": 2,
                "duration_unit": "working-day",
                "wbs_id": "WBS-RPS-CIVIL",
            }
        )
        assert status == 400
        assert json.loads(body)["code"] == "WBS_NOT_FOUND_OR_SCOPE_MISMATCH"

        status, _, body = activity_create(
            {
                "activity_id": "NEW-100",
                "name": "Concept design",
                "duration_value": 5,
                "duration_unit": "working-day",
                "wbs_id": "WBS-WBS01-DESIGN",
            }
        )
        assert status == 201
        assert json.loads(body)["activity"]["wbs_id"] == "WBS-WBS01-DESIGN"

        # The write is visible through the real read service, including a WBS
        # node that intentionally has no activity.
        status, _, body = _request(
            runtime.app,
            "GET",
            "/api/v2/workspace/control-room/read",
            cookie=admin.session_id,
            headers=headers,
        )
        assert status == 200
        workspace = json.loads(body)["workspace"]
        assert [node["wbs_id"] for node in workspace["wbs_nodes"]] == [
            root_id,
            "WBS-WBS01-DESIGN",
            "WBS-WBS01-SITE",
        ]
        assert [(item["id"], item["wbs_id"]) for item in workspace["activities"]] == [
            ("NEW-100", "WBS-WBS01-DESIGN")
        ]
        assert all(
            item["wbs_id"] != "WBS-WBS01-SITE" for item in workspace["activities"]
        )

        # Independently verify the persisted rows, not only the HTTP projection.
        stored_nodes = runtime.connection.execute(
            "SELECT wbs_id,parent_wbs_id,code,sequence_number FROM wbs_master "
            "WHERE tenant_id=? AND project_id=? ORDER BY sequence_number",
            (RPS_TENANT, "preview-wbs-01"),
        ).fetchall()
        assert [tuple(row) for row in stored_nodes] == [
            (root_id, None, "1", 0),
            ("WBS-WBS01-DESIGN", root_id, "2", 10),
            ("WBS-WBS01-SITE", root_id, "3", 20),
        ]
        stored_assignment = runtime.connection.execute(
            "SELECT wbs_id FROM activity_wbs_assignment "
            "WHERE tenant_id=? AND project_id=? AND activity_id=?",
            (RPS_TENANT, "preview-wbs-01", "NEW-100"),
        ).fetchone()
        assert stored_assignment == ("WBS-WBS01-DESIGN",)

        # Unauthorized principals and foreign tenant scopes fail closed.
        newcomer = runtime.sessions.create(DEMO_USERS_BY_ROLE["newcomer"])
        status, _, body = _request(
            runtime.app,
            "GET",
            wbs_path,
            cookie=newcomer.session_id,
            headers=headers,
        )
        assert status == 403
        status, _, body = _request(
            runtime.app,
            "GET",
            "/api/v2/workspace/control-room/read",
            cookie=admin.session_id,
            headers={**headers, "X-Tenant-Id": "another-tenant"},
        )
        assert status == 403
        assert json.loads(body)["code"] == "CROSS_SCOPE_ACCESS"
    finally:
        runtime.close()

    # A service restart re-reads the same persisted tree from SQLite.
    reopened = open_preview_runtime(database)
    try:
        admin = reopened.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        headers = {
            "X-Tenant-Id": RPS_TENANT,
            "X-Project-Id": "preview-wbs-01",
            "X-Project-Revision": "0",
        }
        status, _, body = _request(
            reopened.app,
            "GET",
            "/api/v2/workspace/control-room/read",
            cookie=admin.session_id,
            headers=headers,
        )
        assert status == 200
        workspace = json.loads(body)["workspace"]
        assert [node["wbs_id"] for node in workspace["wbs_nodes"]] == [
            "WBS-preview-wbs-01",
            "WBS-WBS01-DESIGN",
            "WBS-WBS01-SITE",
        ]
        assert workspace["activities"][0]["wbs_id"] == "WBS-WBS01-DESIGN"
        assert workspace["activities"][0]["cells"]["activity.wbs"] == "2 Detailed design"
    finally:
        reopened.close()


def test_preview_project_deep_link_survives_login_and_rejects_external_redirects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CUBI_PREVIEW_PUBLIC_DEMO", "1")
    runtime = open_preview_runtime(
        tmp_path / "deep-link-preview.sqlite3",
        web_root=_web_root(tmp_path),
        reset=True,
    )
    try:
        app = build_preview_application(runtime)

        status, headers, _ = _request(
            app, "GET", "/app?project=preview-rps-01"
        )
        assert status == 302
        assert headers["location"] == (
            "/preview/login?next=%2Fapp%3Fproject%3Dpreview-rps-01"
        )

        status, _, body = _request(
            app,
            "GET",
            "/preview/login?next=%2Fapp%3Fproject%3Dpreview-rps-01",
        )
        assert status == 200
        assert (
            b'<input type="hidden" name="next" '
            b'value="/app?project=preview-rps-01">'
        ) in body

        status, headers, _ = _request(
            app,
            "POST",
            "/preview/login",
            body=b"role=viewer&next=%2Fapp%3Fproject%3Dpreview-rps-01",
            content_type="application/x-www-form-urlencoded",
        )
        assert status == 303
        assert headers["location"] == "/app?project=preview-rps-01"

        status, headers, _ = _request(
            app,
            "POST",
            "/preview/login",
            body=b"role=viewer&next=https%3A%2F%2Fevil.example%2F",
            content_type="application/x-www-form-urlencoded",
        )
        assert status == 303
        assert headers["location"] == "/app"
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

        # A default browser favicon probe must resolve to the canonical CUBI logo.
        status, headers, body = _request(app, "GET", "/favicon.ico")
        assert status == 200
        assert headers["content-type"] == "image/svg+xml"
        assert body.startswith(b"<svg")
        assert b"</svg>" in body

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


def test_preview_resource_capacity_write_closes_open_segment_and_persists(
    tmp_path: Path,
) -> None:
    database = tmp_path / "preview.sqlite3"
    list_path = f"/api/projects/{RPS_PROJECT}/p6/resource-capacities"
    runtime = open_preview_runtime(database, reset=True)
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])

        payload = {
            "contract_version": "p6-resource-capacity-write-api.v1",
            "expected_revision": RPS_REVISION,
            "resource_id": "RPS-CIVIL-CREW",
            "max_units": "10",
            "unit_basis": "day",
            "hours_per_time_period": "8",
            "effective_from": "2026-11-01",
            "effective_to": None,
            "close_open_segment": True,
        }

        def submit(body: dict, cookie: str):
            return _request(
                runtime.app,
                "POST",
                list_path,
                cookie=cookie,
                headers=_scope_headers(),
                body=json.dumps(body).encode("utf-8"),
            )

        status, _, body = submit(payload, viewer.session_id)
        assert status == 403
        assert "project.write" in json.loads(body)["code"]

        status, _, body = submit(
            {**payload, "expected_revision": RPS_REVISION - 1},
            planner.session_id,
        )
        assert status == 409
        assert json.loads(body)["code"] == "REVISION_CONFLICT"

        status, _, body = submit(
            {
                **payload,
                "max_units": "9",
                "effective_from": "2026-10-20",
                "close_open_segment": False,
            },
            planner.session_id,
        )
        assert status == 409
        assert json.loads(body)["code"] == "CAPACITY_SEGMENTS_OVERLAP"

        status, _, body = submit(payload, planner.session_id)
        assert status == 200
        written = json.loads(body)
        assert written["contract_version"] == "p6-resource-capacity-write-api.v1"
        assert written["kind"] == "resource_capacity_write"
        assert written["status"] == "REGISTERED"
        assert written["capacity"]["max_units"] == "10"
        assert written["capacity"]["effective_from"] == "2026-11-01"
        assert written["capacity"]["effective_to"] is None
        assert written["capacity"]["source"] == "manual-entry:preview-planner"
        assert len(written["capacity"]["identity"]) == 64
        assert written["superseded"]["effective_to"] == "2026-10-31"
        assert written["superseded"]["identity"] != written["superseded"][
            "replacement_identity"
        ]

        status, _, body = _request(
            runtime.app,
            "GET",
            list_path,
            cookie=planner.session_id,
            headers=_scope_headers(),
        )
        assert status == 200
        active = [item["capacity"] for item in json.loads(body)["capacities"]]
        assert [
            (item["max_units"], item["effective_from"], item["effective_to"])
            for item in active
        ] == [
            ("8", "2026-09-21", "2026-10-14"),
            ("12", "2026-10-15", "2026-10-31"),
            ("10", "2026-11-01", None),
        ]
        assert written["superseded"]["identity"] not in {
            item["identity"] for item in active
        }

        resolve_path = f"{list_path}/RPS-CIVIL-CREW/resolve"

        def resolve(period: str, basis: str | None = "week"):
            return _request(
                runtime.app,
                "POST",
                resolve_path,
                cookie=planner.session_id,
                headers=_scope_headers(),
                body=json.dumps(
                    {
                        "contract_version": "p6-resource-capacity-read-api.v1",
                        "period": period,
                        "basis": basis,
                        "hours_per_time_period": None
                        if basis is None
                        else "40",
                    }
                ).encode("utf-8"),
            )

        status, _, body = resolve("2026-11-02")
        assert status == 200
        resolved = json.loads(body)
        assert resolved["kind"] == "resource_capacity_value"
        assert resolved["status"] == "RESOLVED"
        assert resolved["basis"] == "week"
        assert resolved["capacity"] == "50"
        assert resolved["source"] == "manual-entry:preview-planner"

        status, _, body = resolve("2026-10-16")
        assert status == 200
        assert json.loads(body)["capacity"] == "60"

        status, _, body = resolve("2026-09-01")
        assert status == 409
        assert json.loads(body)["code"] == "CAPACITY_SEGMENT_NOT_EFFECTIVE"
    finally:
        runtime.close()

    reopened = open_preview_runtime(database)
    try:
        planner = reopened.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, _, body = _request(
            reopened.app,
            "GET",
            f"/api/projects/{RPS_PROJECT}/p6/resource-capacities/RPS-CIVIL-CREW",
            cookie=planner.session_id,
            headers=_scope_headers(),
        )
        assert status == 200
        persisted = json.loads(body)
        assert [segment["max_units"] for segment in persisted["segments"]] == [
            "8",
            "12",
            "10",
        ]
        assert persisted["segments"][1]["effective_to"] == "2026-10-31"
        assert persisted["segments"][2]["source"] == "manual-entry:preview-planner"
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


def test_public_demo_login_is_read_only_and_warns_about_shared_fixture_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CUBI_PREVIEW_PUBLIC_DEMO", "1")
    runtime = open_preview_runtime(
        tmp_path / "public-preview.sqlite3",
        web_root=_web_root(tmp_path),
        reset=True,
    )
    try:
        app = build_preview_application(runtime)

        status, _, body = _request(app, "GET", "/preview/login")
        assert status == 200
        assert b"PUBLIC READ-ONLY DEMO" in body
        assert b"shared fixture data" in body.lower()
        assert b"confidential information" in body.lower()
        assert b'value="viewer"' in body
        assert b'value="planner"' not in body
        assert b'value="admin"' not in body

        status, headers, body = _request(
            app,
            "POST",
            "/preview/login",
            body=b"role=planner&next=%2Fapp",
            content_type="application/x-www-form-urlencoded",
        )
        assert status == 403
        assert "set-cookie" not in headers
        assert b"read-only" in body.lower()

        status, headers, _ = _request(
            app,
            "POST",
            "/preview/login",
            body=b"role=viewer&next=%2Fapp",
            content_type="application/x-www-form-urlencoded",
        )
        assert status == 303
        cookie = _session_cookie(headers)

        status, _, body = _request(app, "GET", "/app", cookie=cookie)
        assert status == 200
        assert b"PUBLIC DEMO" in body
        assert b"preview-viewer" in body

        status, _, body = _request(app, "GET", "/preview/health")
        assert status == 200
        health = json.loads(body)
        assert health == {
            "status": "ok",
            "production": False,
            "demo_data": True,
            "public_demo": True,
            "read_only": True,
        }
        # Anonymous readiness probes must not disclose internal deployment or
        # tenant details that are present in the runtime's private health data.
        for internal_key in (
            "database",
            "web_root",
            "tenant_id",
            "project_count",
            "demo_project_count",
            "activity_count",
            "wbs_node_count",
            "capacity_segment_count",
            "session_count",
            "assistant",
        ):
            assert internal_key not in health
        assert str(tmp_path) not in body.decode("utf-8")
        assert RPS_TENANT not in body.decode("utf-8")

        status, _, body = _request(app, "GET", "/api/session", cookie=cookie)
        assert status == 200
        assert json.loads(body)["roles"] == ["viewer"]
    finally:
        runtime.close()


def test_preview_project_metadata_edit_is_revision_guarded_and_survives_restart(
    tmp_path: Path,
) -> None:
    database = tmp_path / "preview.sqlite3"
    runtime = open_preview_runtime(database, reset=True)
    try:
        admin = runtime.sessions.create(DEMO_USERS_BY_ROLE["admin"])
        status, _, body = _request(
            runtime.app,
            "POST",
            "/api/projects",
            cookie=admin.session_id,
            body=json.dumps(
                {
                    "project_id": "preview-meta-01",
                    "name": "Metadata project",
                    "description": "Original scope",
                    "start_date": "2026-11-02",
                    "date_system": "jalali",
                }
            ).encode("utf-8"),
        )
        assert status == 201
        assert json.loads(body)["context"]["revision"] == 0

        status, _, body = _request(
            runtime.app, "GET", "/api/projects/preview-meta-01",
            cookie=admin.session_id,
        )
        assert status == 200
        created = json.loads(body)["project"]
        assert created["description"] == "Original scope"
        assert created["start_date"] == "2026-11-02"
        assert created["date_system"] == "jalali"

        status, _, body = _request(
            runtime.app,
            "PATCH",
            "/api/projects/preview-meta-01",
            cookie=admin.session_id,
            body=json.dumps(
                {
                    "name": "Metadata project renamed",
                    "description": "Revised scope",
                    "start_date": "2026-11-09",
                    "date_system": "gregorian",
                    "primary_calendar_id": "CAL-EDIT",
                    "expected_revision": 0,
                }
            ).encode("utf-8"),
        )
        assert status == 200
        updated = json.loads(body)["project"]
        assert updated["settings_revision"] == 1
        assert updated["revision"] == 0, (
            "a metadata edit must not move the workspace data revision that "
            "persisted WBS/activity rows are stamped with"
        )
        assert updated["name"] == "Metadata project renamed"
        assert updated["primary_calendar_id"] == "CAL-EDIT"

        status, _, body = _request(
            runtime.app,
            "PATCH",
            "/api/projects/preview-meta-01",
            cookie=admin.session_id,
            body=json.dumps(
                {"name": "Stale overwrite", "expected_revision": 0}
            ).encode("utf-8"),
        )
        assert status == 409
        assert json.loads(body)["code"] == "PROJECT_REVISION_CONFLICT"

        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])
        status, _, _ = _request(
            runtime.app,
            "PATCH",
            "/api/projects/preview-meta-01",
            cookie=viewer.session_id,
            body=json.dumps(
                {"name": "Viewer edit", "expected_revision": 1}
            ).encode("utf-8"),
        )
        assert status == 403
    finally:
        runtime.close()

    reopened = open_preview_runtime(database)
    try:
        planner = reopened.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        status, _, body = _request(
            reopened.app, "GET", "/api/projects/preview-meta-01",
            cookie=planner.session_id,
        )
        assert status == 200
        persisted = json.loads(body)["project"]
        assert persisted["name"] == "Metadata project renamed"
        assert persisted["description"] == "Revised scope"
        assert persisted["start_date"] == "2026-11-09"
        assert persisted["date_system"] == "gregorian"
        assert persisted["primary_calendar_id"] == "CAL-EDIT"
        assert persisted["settings_revision"] == 1
        assert persisted["revision"] == 0
    finally:
        reopened.close()
