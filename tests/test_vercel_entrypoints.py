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
    assert rewrites["/app"] == "/api/shell"
    assert rewrites["/api/:path*"] == "/api?__path=:path*"
    headers = {
        entry["source"]: {item["key"]: item["value"] for item in entry["headers"]}
        for entry in config["headers"]
    }
    assert headers["/login"]["Cache-Control"] == "no-store"
    assert headers["/login"]["X-Frame-Options"] == "DENY"
    assert headers["/login.html"]["X-Content-Type-Options"] == "nosniff"
