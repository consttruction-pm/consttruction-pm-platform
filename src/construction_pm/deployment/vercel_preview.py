"""Fixture-backed CUBI workspace for Vercel preview deployments.

A preview deployment of the Web project must be reviewable without a
production database. This module composes the existing local preview stack -
the real HTTP routes, the real SQLite repositories and the curated demo
fixtures (including the Riverside Pump Station Upgrade project) - behind the
Vercel functions.

The composition is deliberately unreachable on a production deployment:

* ``VERCEL_ENV=production`` (or ``VERCEL_TARGET_ENV=production``) always
  selects the production runtime, even if the preview flag is set.
* A preview deployment (``VERCEL_ENV=preview``) or an explicit
  ``CUBI_PREVIEW_RUNTIME=1`` for local runs selects this module instead.
* Nothing here writes to PostgreSQL, contacts a paid service, or impersonates
  a production identity: sessions are the demo sessions of the local preview
  and the only data is the fixture seed in an ephemeral SQLite file.
"""

from __future__ import annotations

import json
import os
import re
import threading
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Callable, Mapping
from urllib.parse import parse_qs, urlencode

from construction_pm.preview.runtime import PreviewRuntime, PreviewRuntimeError, open_preview_runtime
from construction_pm.preview.server import (
    SESSION_COOKIE,
    PreviewApplication,
    _cookie_header,
)
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE

DEFAULT_DATABASE = "/tmp/cubi-preview.sqlite3"
DEFAULT_ROLE = "planner"
HEALTH_PATHS = frozenset({"/api/health/live", "/api/health/ready"})
_PREVIEW_PREFIX = "/preview"
_SAFE_DEPLOYMENT = re.compile(r"[^A-Za-z0-9_.-]+")

_lock = threading.RLock()
_cached: dict[str, object] = {}


def preview_mode(environment: Mapping[str, object] | None = None) -> bool:
    """Return True only for an explicitly non-production preview deployment."""

    env = os.environ if environment is None else environment

    def value(name: str) -> str:
        return str(env.get(name, "") or "").strip().lower()

    if value("VERCEL_ENV") == "production" or value("VERCEL_TARGET_ENV") == "production":
        return False
    if value("CUBI_PREVIEW_RUNTIME") in {"1", "true", "yes"}:
        return True
    return value("VERCEL_ENV") == "preview"


def _deployment_database(environment: Mapping[str, object]) -> Path:
    configured = str(environment.get("CUBI_PREVIEW_DATABASE", "") or "").strip()
    if configured:
        return Path(configured)
    # A new deployment must not inherit a seeded file from a previous one.
    marker = str(
        environment.get("VERCEL_DEPLOYMENT_ID")
        or environment.get("VERCEL_URL")
        or ""
    ).strip()
    if not marker:
        return Path(DEFAULT_DATABASE)
    token = _SAFE_DEPLOYMENT.sub("-", marker)[:48]
    return Path(f"/tmp/cubi-preview-{token}.sqlite3")


def _web_root(environment: Mapping[str, object]) -> Path:
    configured = str(
        environment.get("CUBI_PREVIEW_WEB_ROOT")
        or environment.get("CUBI_WEB_ROOT")
        or ""
    ).strip()
    if not configured:
        raise PreviewRuntimeError(
            "PREVIEW_WEB_ROOT_REQUIRED",
            "Set CUBI_WEB_ROOT to the staged preview web root.",
        )
    return Path(configured)


def _restore_path(environ: dict[str, object]) -> str:
    """Map a Vercel rewrite back to the route the preview application expects."""

    path = str(environ.get("PATH_INFO", "/") or "/")
    raw_query = str(environ.get("QUERY_STRING", "") or "")
    parameters = parse_qs(raw_query, keep_blank_values=True)
    rewritten = parameters.pop("__path", None)
    if rewritten:
        suffix = rewritten[0].lstrip("/")
        if suffix == "preview" or suffix.startswith("preview/"):
            path = "/" + suffix
        else:
            path = "/api/" + suffix
    environ["PATH_INFO"] = path
    environ["QUERY_STRING"] = urlencode(parameters, doseq=True) if parameters else ""
    return path


def _session_token(environ: Mapping[str, object]) -> str:
    raw = str(environ.get("HTTP_COOKIE", "") or "")
    if not raw:
        return ""
    cookies = SimpleCookie()
    try:
        cookies.load(raw)
    except Exception:  # noqa: BLE001 - malformed cookies are simply anonymous
        return ""
    morsel = cookies.get(SESSION_COOKIE)
    return morsel.value if morsel is not None else ""


def _json_response(start_response, status: int, payload: dict[str, object]):
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    start_response(
        f"{status} {'OK' if status == 200 else 'Service Unavailable'}",
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "DENY"),
            ("Referrer-Policy", "no-referrer"),
        ],
    )
    return [body]


def _replace_session_cookie(raw_cookie: str, token: str) -> str:
    """Replace any presented session cookie; duplicates would shadow the new one."""

    remaining = [
        item.strip()
        for item in raw_cookie.split(";")
        if item.strip() and not item.strip().startswith(SESSION_COOKIE + "=")
    ]
    prefix = f"{SESSION_COOKIE}={token}"
    return "; ".join([prefix, *remaining]) if remaining else prefix


class VercelPreviewApplication:
    """WSGI wrapper that keeps a demo session on every preview request.

    Preview sessions live in the process that created them. A serverless
    deployment may answer consecutive requests on different instances, so a
    known token is reused and an unknown one is replaced with a fresh demo
    session for the configured role. The cookie is always ``Secure`` because a
    Vercel deployment is HTTPS.
    """

    def __init__(
        self,
        application: Callable,
        runtime: PreviewRuntime,
        *,
        role: str = DEFAULT_ROLE,
        secure_cookies: bool = True,
    ) -> None:
        self.application = application
        self.runtime = runtime
        self.role = role
        self.secure_cookies = secure_cookies
        self.user = DEMO_USERS_BY_ROLE.get(role) or DEMO_USERS_BY_ROLE[DEFAULT_ROLE]

    def __call__(self, environ, start_response):
        scoped = dict(environ)
        path = _restore_path(scoped)
        if path in HEALTH_PATHS:
            return self._health(path, start_response)
        if path == _PREVIEW_PREFIX or path.startswith(_PREVIEW_PREFIX + "/"):
            # Sign-in, sign-out and the persona page manage their own cookies.
            return self.application(scoped, start_response)
        cookie = self._ensure_session(scoped)
        captured: dict[str, object] = {}

        def capture(status, headers, exc_info=None):
            resolved = list(headers)
            if cookie and not any(key.lower() == "set-cookie" for key, _ in resolved):
                resolved.append(("Set-Cookie", cookie))
            captured["status"] = status
            if exc_info is not None:
                return start_response(status, resolved, exc_info)
            return start_response(status, resolved)

        return self.application(scoped, capture)

    def _ensure_session(self, environ: dict[str, object]) -> str | None:
        token = _session_token(environ)
        if token and self.runtime.sessions.get(token) is not None:
            return None
        session = self.runtime.sessions.create(self.user)
        environ["HTTP_COOKIE"] = _replace_session_cookie(
            str(environ.get("HTTP_COOKIE", "") or ""), session.session_id
        )
        return _cookie_header(session, secure=self.secure_cookies)[1]

    def _health(self, path: str, start_response):
        if path.endswith("/live"):
            return _json_response(
                start_response,
                200,
                {"status": "ok", "runtime": "preview", "demo_data": True},
            )
        return _json_response(
            start_response,
            200,
            {
                "status": "ready",
                "runtime": "preview",
                "demo_data": True,
                "components": [{"name": "demo-database", "healthy": True}],
            },
        )


def _build(environment: Mapping[str, object]) -> VercelPreviewApplication:
    database = _deployment_database(environment)
    database.parent.mkdir(parents=True, exist_ok=True)
    web_root = _web_root(environment)
    try:
        runtime = open_preview_runtime(database, web_root=web_root)
    except PreviewRuntimeError:
        # A stale seed from an earlier schema must never block a preview.
        try:
            database.unlink()
        except OSError:
            pass
        runtime = open_preview_runtime(database, web_root=web_root)
    application = PreviewApplication(runtime, require_web_build=False)
    role = str(environment.get("CUBI_PREVIEW_AUTO_ROLE", "") or DEFAULT_ROLE).strip()
    return VercelPreviewApplication(application, runtime, role=role)


def get_preview_application(environment: Mapping[str, object] | None = None) -> VercelPreviewApplication:
    """Return the process-wide preview application (seeded once per instance)."""

    env = os.environ if environment is None else environment
    with _lock:
        cached = _cached.get("application")
        if isinstance(cached, VercelPreviewApplication):
            return cached
        application = _build(env)
        _cached["application"] = application
        return application
