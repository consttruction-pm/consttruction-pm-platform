"""Tests for the Vercel entrypoints in the ``apps/web`` project root.

The production Vercel project is rooted at ``apps/web``, so its functions live
in ``apps/web/api`` and import the runtime staged into ``vercel-runtime``.
These tests cover the bootstrap behaviour without a database: liveness must
stay honest, and every other route must report a configuration requirement
instead of pretending to be authenticated or ready.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import re
from pathlib import Path

import pytest

WEB_ROOT = Path(__file__).resolve().parents[1] / "apps" / "web"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    before = dict(os.environ)
    try:
        spec.loader.exec_module(module)
    finally:
        # The entrypoints default CUBI_WEB_ROOT for the deployed layout; never
        # leak that into the rest of the suite.
        os.environ.clear()
        os.environ.update(before)
    return module


@pytest.fixture()
def unconfigured(monkeypatch):
    for name in (
        "CONSTRUCTION_PM_DATABASE_URL",
        "CONSTRUCTION_PM_SESSION_SECRET",
        "CONSTRUCTION_PM_PUBLIC_ORIGIN",
    ):
        monkeypatch.delenv(name, raising=False)
    from construction_pm.deployment import production_runtime

    monkeypatch.setattr(production_runtime, "_RUNTIME", None)
    return _load("cubi_vercel_index", WEB_ROOT / "api" / "index.py"), _load(
        "cubi_vercel_shell", WEB_ROOT / "api" / "shell.py"
    )


def _call(app, method: str, path: str, query: str = "", body: bytes = b""):
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "wsgi.url_scheme": "https",
        "wsgi.input": io.BytesIO(body),
        "CONTENT_LENGTH": str(len(body)),
        "HTTP_X_FORWARDED_PROTO": "https",
    }
    captured: dict[str, object] = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    payload = b"".join(app(environ, start_response))
    headers = {key.lower(): value for key, value in captured["headers"]}
    return int(str(captured["status"]).split()[0]), headers, payload


def test_liveness_stays_available_without_configuration(unconfigured):
    index, _ = unconfigured
    status, headers, body = _call(index.app, "GET", "/api", "__path=health/live")
    assert status == 200
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert json.loads(body)["status"] == "ok"


def test_readiness_reports_configuration_required(unconfigured):
    index, _ = unconfigured
    status, _, body = _call(index.app, "GET", "/api", "__path=health/ready")
    assert status == 503
    assert json.loads(body) == {"status": "not_ready", "code": "CONFIGURATION_REQUIRED"}


def test_login_is_not_faked_when_configuration_is_missing(unconfigured):
    index, _ = unconfigured
    status, _, body = _call(index.app, "POST", "/api", "__path=session", b"{}")
    assert status == 503
    assert json.loads(body)["code"] == "CONFIGURATION_REQUIRED"


def test_app_shell_never_serves_workspace_html_without_configuration(unconfigured):
    _, shell = unconfigured
    status, headers, body = _call(shell.app, "GET", "/api/shell")
    assert status == 503
    assert headers["x-frame-options"] == "DENY"
    assert headers["x-content-type-options"] == "nosniff"
    assert b"<html" in body
    assert b"workspace" not in body.lower()


def test_entrypoints_expose_a_wsgi_callable():
    assert callable(_load("cubi_index_callable", WEB_ROOT / "api" / "index.py").app)
    assert callable(_load("cubi_shell_callable", WEB_ROOT / "api" / "shell.py").app)


def test_project_configuration_targets_the_authenticated_runtime():
    config = json.loads((WEB_ROOT / "vercel.json").read_text(encoding="utf-8"))
    assert config["outputDirectory"] == "vercel-site"
    assert config["buildCommand"].endswith("vercel-project-build.mjs")
    for function in config["functions"].values():
        # The Vercel schema types includeFiles as one glob string.
        assert isinstance(function["includeFiles"], str)
        assert function["includeFiles"].startswith("vercel-runtime/")
    rewrites = {entry["source"]: entry["destination"] for entry in config["rewrites"]}
    assert rewrites["/app"] == "/api/shell?__path=app"
    assert rewrites["/app/"] == "/api/shell?__path=app"
    assert rewrites["/app/:path*/"] == "/api/shell?__path=app/:path*"
    assert rewrites["/enterprise"] == "/api/shell?__path=enterprise"
    assert rewrites["/enterprise/"] == "/api/shell?__path=enterprise"
    assert rewrites["/api/:path*"] == "/api?__path=:path*"
    redirects = {entry["source"]: entry["destination"] for entry in config.get("redirects", [])}
    # The Enterprise document links back to ``/workbench/``; the deployment must
    # serve the Personal Workbench document there instead of the platform 404.
    # It is the same application shell as ``/app``: the client router keys the
    # Personal Workbench off the address, so the address must stay ``/workbench/``.
    assert rewrites["/workbench"] == "/api/shell?__path=app"
    assert rewrites["/workbench/"] == "/api/shell?__path=app"
    assert rewrites["/workbench/:path*"] == "/api/shell?__path=app"
    assert "/workbench" not in redirects
    headers = {
        entry["source"]: {item["key"]: item["value"] for item in entry["headers"]}
        for entry in config["headers"]
    }
    assert headers["/login"]["Cache-Control"] == "no-store"
    assert headers["/login"]["X-Frame-Options"] == "DENY"
    assert headers["/login.html"]["X-Content-Type-Options"] == "nosniff"


def test_shell_resolves_each_workspace_route_without_a_second_shell():
    shell = _load("cubi_shell_paths", WEB_ROOT / "api" / "shell.py")
    assert shell._workspace_path({"PATH_INFO": "/api/shell", "QUERY_STRING": "__path=app"}) == "/app"
    assert shell._workspace_path({"PATH_INFO": "/api/shell", "QUERY_STRING": "__path=enterprise"}) == "/enterprise"
    assert shell._workspace_path({"PATH_INFO": "/api/shell", "QUERY_STRING": "__path=enterprise/"}) == "/enterprise"
    assert shell._workspace_path({"PATH_INFO": "/enterprise/", "QUERY_STRING": ""}) == "/enterprise"
    # The Personal Workbench and the administration panel are documents of the
    # same session-gated family and ship no static file of their own.
    assert shell._workspace_path({"PATH_INFO": "/api/shell", "QUERY_STRING": "__path=workbench"}) == "/workbench"
    assert shell._workspace_path({"PATH_INFO": "/api/shell", "QUERY_STRING": "__path=admin"}) == "/admin"
    # An unknown rewrite never turns into an arbitrary route.
    assert shell._workspace_path({"PATH_INFO": "/api/shell", "QUERY_STRING": "__path=docs"}) == "/app"
    assert shell._workspace_path({"PATH_INFO": "/api/shell", "QUERY_STRING": "__path=etc/passwd"}) == "/app"

def test_canonical_preview_routes_api_and_shell_through_the_same_runtime(monkeypatch):
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.delenv("VERCEL_TARGET_ENV", raising=False)
    monkeypatch.setenv("CUBI_PREVIEW_USE_CANONICAL_DATABASE", "1")
    index = _load("cubi_canonical_index", WEB_ROOT / "api" / "index.py")
    shell = _load("cubi_canonical_shell", WEB_ROOT / "api" / "shell.py")
    calls = []

    class CanonicalRuntime:
        def __call__(self, environ, start_response):
            calls.append((environ["REQUEST_METHOD"], environ["PATH_INFO"]))
            start_response("200 OK", [("Content-Type", "text/plain"), ("Content-Length", "9")])
            return [b"canonical"]

    runtime = CanonicalRuntime()
    monkeypatch.setattr(index, "get_runtime", lambda: runtime)
    monkeypatch.setattr(shell, "get_runtime", lambda: runtime)

    api_status, _, api_body = _call(index.app, "GET", "/api", "__path=health/ready")
    shell_status, _, shell_body = _call(shell.app, "GET", "/api/shell", "__path=app")

    assert api_status == shell_status == 200
    assert api_body == shell_body == b"canonical"
    assert calls == [("GET", "/api"), ("GET", "/app")]


def test_supabase_session_pooler_integration_dsn_is_accepted(monkeypatch, tmp_path):
    from construction_pm.deployment.production_runtime import ProductionSettings

    (tmp_path / "index.html").write_text("<!doctype html>", encoding="utf-8")
    (tmp_path / "app.html").write_text("<!doctype html>", encoding="utf-8")
    dsn = "postgresql://postgres.project-ref:secret@aws-0-eu-central-1.pooler.supabase.com:5432/postgres?sslmode=require"
    monkeypatch.delenv("CONSTRUCTION_PM_DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_URL_NON_POOLING", dsn)
    monkeypatch.setenv("CONSTRUCTION_PM_SESSION_SECRET", "test-session-secret-with-at-least-32-characters")
    monkeypatch.setenv("CONSTRUCTION_PM_PUBLIC_ORIGIN", "https://preview.example.test")
    monkeypatch.setenv("CUBI_WEB_ROOT", str(tmp_path))

    settings = ProductionSettings.from_environment()

    assert settings.database_url == dsn
    assert settings.public_origin == "https://preview.example.test"


def test_shipped_html_contains_no_unresolved_merge_markers():
    """The public documents are served verbatim.

    A conflict marker left in a committed page is not a build error: Vercel
    serves it and the marker becomes visible text on the live preview. Guard
    every HTML document the project ships, including the nested locales.
    """

    documents = [*WEB_ROOT.glob("*.html"), *WEB_ROOT.glob("public/**/*.html")]
    assert documents, "the project ships HTML documents"

    def markers(text: str) -> list[str]:
        found = []
        for number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if (
                stripped.startswith("<<<<<<<")
                or stripped.startswith(">>>>>>>")
                or re.fullmatch(r"={7}", stripped)
            ):
                found.append(f"{number}:{line}")
        return found

    offenders = {
        str(path.relative_to(WEB_ROOT)): markers(path.read_text(encoding="utf-8"))
        for path in documents
    }
    assert {name: found for name, found in offenders.items() if found} == {}