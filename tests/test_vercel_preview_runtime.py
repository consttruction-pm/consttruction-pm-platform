"""Tests for the fixture-backed Vercel preview composition.

The composition must stay unreachable on production deployments, must restore
the rewritten route, and must keep a demo session without any PostgreSQL.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode

import pytest

from construction_pm.deployment import vercel_preview
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

WEB_ROOT = Path(__file__).resolve().parents[1] / "apps" / "web"


def test_production_never_selects_the_preview_runtime():
    assert vercel_preview.preview_mode({"VERCEL_ENV": "production"}) is False
    assert vercel_preview.preview_mode(
        {"VERCEL_ENV": "production", "CUBI_PREVIEW_RUNTIME": "1"}
    ) is False
    assert vercel_preview.preview_mode({"VERCEL_TARGET_ENV": "production"}) is False


def test_preview_deployment_and_explicit_local_flag_select_the_runtime():
    assert vercel_preview.preview_mode({"VERCEL_ENV": "preview"}) is True
    assert vercel_preview.preview_mode({"CUBI_PREVIEW_RUNTIME": "1"}) is True
    assert vercel_preview.preview_mode({}) is False


def test_restore_path_maps_api_and_preview_routes():
    environ = {"PATH_INFO": "/api", "QUERY_STRING": "__path=projects&view=live"}
    assert vercel_preview._restore_path(environ) == "/api/projects"
    assert environ["QUERY_STRING"] == "view=live"

    environ = {"PATH_INFO": "/api", "QUERY_STRING": "__path=preview/login&next=%2Fapp"}
    assert vercel_preview._restore_path(environ) == "/preview/login"
    assert environ["QUERY_STRING"] == "next=%2Fapp"


class _Sessions:
    def __init__(self) -> None:
        self.created: list[object] = []
        self.known: dict[str, object] = {}

    def create(self, user):
        session = SimpleNamespace(session_id=f"token-{len(self.created) + 1}")
        self.created.append(user)
        self.known[session.session_id] = session
        return session

    def get(self, token):
        return self.known.get(token)


class _Runtime:
    def __init__(self) -> None:
        self.sessions = _Sessions()


def _call(app, method: str, path: str, query: str = "", cookie: str = ""):
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "wsgi.url_scheme": "https",
        "wsgi.input": io.BytesIO(b""),
        "CONTENT_LENGTH": "0",
    }
    if cookie:
        environ["HTTP_COOKIE"] = cookie
    captured: dict[str, object] = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    body = b"".join(app(environ, start_response))
    headers = {key.lower(): value for key, value in captured["headers"]}
    return int(str(captured["status"]).split()[0]), headers, body


def _echo(environ, start_response):
    start_response("200 OK", [("Content-Type", "application/json")])
    payload = {
        "path": environ["PATH_INFO"],
        "query": environ["QUERY_STRING"],
        "cookie": environ.get("HTTP_COOKIE", ""),
    }
    return [json.dumps(payload).encode("utf-8")]


def test_wrapper_issues_a_secure_demo_session_and_forwards_the_route():
    runtime = _Runtime()
    app = vercel_preview.VercelPreviewApplication(_echo, runtime, role="planner")
    status, headers, body = _call(app, "GET", "/api", "__path=projects")
    assert status == 200
    assert json.loads(body)["path"] == "/api/projects"
    cookie = headers["set-cookie"]
    assert cookie.startswith("cp_session=token-1")
    assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=Lax" in cookie
    assert runtime.sessions.created == [DEMO_USERS_BY_ROLE["planner"]]


def test_known_session_is_reused_instead_of_creating_another():
    runtime = _Runtime()
    app = vercel_preview.VercelPreviewApplication(_echo, runtime, role="planner")
    _, headers, _ = _call(app, "GET", "/api", "__path=projects")
    token = headers["set-cookie"].split(";", 1)[0]
    status, headers, body = _call(app, "GET", "/api", "__path=projects", cookie=token)
    assert status == 200
    assert "set-cookie" not in headers
    assert len(runtime.sessions.created) == 1
    assert token in json.loads(body)["cookie"]


def test_health_probes_report_preview_without_touching_the_demo_app():
    runtime = _Runtime()
    seen: list[str] = []

    def app_under_test(environ, start_response):
        seen.append(environ["PATH_INFO"])
        return _echo(environ, start_response)

    app = vercel_preview.VercelPreviewApplication(app_under_test, runtime)
    status, _, body = _call(app, "GET", "/api", "__path=health/live")
    assert status == 200
    assert json.loads(body) == {"status": "ok", "runtime": "preview", "demo_data": True}
    status, _, body = _call(app, "GET", "/api", "__path=health/ready")
    assert status == 200
    payload = json.loads(body)
    assert payload["status"] == "ready" and payload["runtime"] == "preview"
    assert seen == []


def test_preview_paths_keep_their_own_cookie_behaviour():
    runtime = _Runtime()
    app = vercel_preview.VercelPreviewApplication(_echo, runtime)
    status, headers, body = _call(app, "GET", "/api", "__path=preview/login")
    assert status == 200
    assert "set-cookie" not in headers
    assert runtime.sessions.created == []
    assert json.loads(body)["path"] == "/preview/login"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    before = dict(os.environ)
    try:
        spec.loader.exec_module(module)
    finally:
        os.environ.clear()
        os.environ.update(before)
    return module


def test_entrypoint_selects_the_preview_runtime_only_outside_production(monkeypatch):
    index = _load("cubi_vercel_index_preview", WEB_ROOT / "api" / "index.py")
    calls: list[str] = []

    def fake_application():
        def application(environ, start_response):
            calls.append(vercel_preview._restore_path(dict(environ)))
            start_response("200 OK", [("Content-Type", "application/json")])
            return [b'{"status":"ok","runtime":"preview"}']

        return application

    monkeypatch.setattr(
        "construction_pm.deployment.vercel_preview.get_preview_application",
        fake_application,
    )

    monkeypatch.setenv("VERCEL_ENV", "preview")
    status, _, body = _call(index.app, "GET", "/api", "__path=health/live")
    assert status == 200 and json.loads(body)["runtime"] == "preview"
    assert calls == ["/api/health/live"]

    calls.clear()
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("CUBI_PREVIEW_RUNTIME", "1")
    status, _, body = _call(index.app, "GET", "/api", "__path=health/live")
    assert status == 200
    assert json.loads(body) == {"status": "ok"}
    assert calls == []


def test_preview_configuration_is_routed_to_the_api_function():
    config = json.loads((WEB_ROOT / "vercel.json").read_text(encoding="utf-8"))
    rewrites = {entry["source"]: entry["destination"] for entry in config["rewrites"]}
    assert rewrites["/preview/:path*"] == "/api?__path=preview/:path*"
    assert rewrites["/dist/main.bundle.js"] == "/dist/web/src/main.bundle.js"
    headers = {
        entry["source"]: {item["key"]: item["value"] for item in entry["headers"]}
        for entry in config["headers"]
    }
    assert headers["/preview/(.*)"]["Cache-Control"] == "no-store"


@pytest.mark.parametrize("role", ["planner", "viewer", "admin"])
def test_every_demo_role_can_open_the_workspace(role):
    runtime = _Runtime()
    app = vercel_preview.VercelPreviewApplication(_echo, runtime, role=role)
    _call(app, "GET", "/api", "__path=projects")
    assert runtime.sessions.created[0].role == role


def test_deployment_database_is_scoped_to_the_deployment():
    first = vercel_preview._deployment_database({"VERCEL_URL": "cubi-a.example.vercel.app"})
    second = vercel_preview._deployment_database({"VERCEL_URL": "cubi-b.example.vercel.app"})
    assert first != second
    assert str(first).startswith("/tmp/cubi-preview-")
    explicit = vercel_preview._deployment_database({"CUBI_PREVIEW_DATABASE": "/tmp/x.sqlite3"})
    assert explicit == Path("/tmp/x.sqlite3")


def test_query_string_is_restored_for_the_workspace_request():
    environ = {
        "PATH_INFO": "/api",
        "QUERY_STRING": urlencode({"__path": "v2/workspace/control-room/read", "project": "preview-rps-01"}),
    }
    assert vercel_preview._restore_path(environ) == "/api/v2/workspace/control-room/read"
    assert environ["QUERY_STRING"] == "project=preview-rps-01"


def test_fixture_runtime_serves_the_riverside_workspace(tmp_path):
    application = vercel_preview._build(
        {
            "CUBI_PREVIEW_DATABASE": str(tmp_path / "preview.sqlite3"),
            "CUBI_PREVIEW_WEB_ROOT": str(WEB_ROOT),
        }
    )
    status, headers, body = _call(application, "GET", "/app", "project=preview-rps-01&view=live")
    assert status == 200
    assert b'name="cubi-login-path"' in body
    cookie = headers["set-cookie"].split(";", 1)[0]

    status, _, body = _call(application, "GET", "/api", "__path=session", cookie=cookie)
    assert status == 200
    assert json.loads(body)["user_id"] == "preview-planner"

    status, _, body = _call(application, "GET", "/api", "__path=projects", cookie=cookie)
    assert status == 200
    projects = {project["project_id"]: project for project in json.loads(body)["projects"]}
    assert projects["preview-rps-01"]["name"] == "Riverside Pump Station Upgrade"

    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/api",
        "QUERY_STRING": "__path=v2/workspace/control-room/read",
        "wsgi.url_scheme": "https",
        "wsgi.input": io.BytesIO(b""),
        "CONTENT_LENGTH": "0",
        "HTTP_COOKIE": cookie,
        "HTTP_X_PROJECT_ID": "preview-rps-01",
        "HTTP_X_TENANT_ID": "cubi-preview-tenant",
        "HTTP_X_PROJECT_REVISION": "7",
    }
    captured: dict[str, object] = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    payload = b"".join(application(environ, start_response))
    assert int(str(captured["status"]).split()[0]) == 200
    workspace = json.loads(payload)["workspace"]
    assert len(workspace["activities"]) > 0
