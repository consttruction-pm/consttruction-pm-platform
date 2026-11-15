"""WSGI-level tests for the production HTTP surface.

The inner API application is stubbed here: these tests are about the boundary
that the real deployment puts in front of it (login, logout, cookies, CSRF,
origin checks, the ``/app`` gate and static delivery). The full composed stack
against PostgreSQL is covered by the integration test.
"""

from __future__ import annotations

import io
import json
import sqlite3
from pathlib import Path
from wsgiref.util import setup_testing_defaults

import pytest

from construction_pm.deployment.production_web import ProductionWebApp, StaticSite, _client_ip
from construction_pm.identity_session import (
    IdentityService,
    IdentityUser,
    SQLiteIdentityStore,
    hash_password,
)

ORIGIN = "https://cubi.example.test"
SECRET = "web-test-session-secret-0123456789abc"
PASSWORD = "correct horse battery staple"


class StubApi:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def __call__(self, environ, start_response):
        self.calls.append((environ["REQUEST_METHOD"], environ["PATH_INFO"]))
        start_response(
            "200 OK",
            [
                ("Content-Type", "application/json"),
                ("Content-Length", "2"),
                ("X-Frame-Options", "DENY"),
            ],
        )
        session_id = environ.get("HTTP_COOKIE", "")
        return [json.dumps({"ok": True, "seen": environ["PATH_INFO"]}).encode()]


@pytest.fixture()
def site_root(tmp_path: Path) -> Path:
    (tmp_path / "index.html").write_text("<!doctype html><title>CUBI</title>", encoding="utf-8")
    (tmp_path / "app.html").write_text("<!doctype html><title>CUBI Workspace</title>", encoding="utf-8")
    (tmp_path / "login.html").write_text("<!doctype html><title>CUBI Login</title>", encoding="utf-8")
    public = tmp_path / "public"
    public.mkdir()
    (public / "theme.css").write_text("body{}", encoding="utf-8")
    dist = tmp_path / "dist" / "web" / "src"
    dist.mkdir(parents=True)
    (dist / "main.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "dist" / "landing-entry.bundle.js").write_text("console.log(2)", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("not public", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def identity() -> IdentityService:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    store = SQLiteIdentityStore(connection)
    store.initialize()
    store.upsert_user(
        IdentityUser(
            user_id="user-1",
            tenant_id="tenant-a",
            email="engineer@example.test",
            display_name="Engineer",
            roles=frozenset({"planner"}),
            password_hash=hash_password(PASSWORD),
        )
    )
    return IdentityService(store, csrf_secret=SECRET)


@pytest.fixture()
def app(identity: IdentityService, site_root: Path) -> ProductionWebApp:
    return ProductionWebApp(
        api_app=StubApi(),
        identity=identity,
        site=StaticSite(site_root),
        public_origin=ORIGIN,
        secure_cookies=True,
        readiness=lambda: {"status": "ready", "components": []},
    )


def call(
    app,
    method: str,
    path: str,
    *,
    body: object | None = None,
    cookie: str = "",
    headers: dict[str, str] | None = None,
    origin: str | None = ORIGIN,
    query: str = "",
    scheme: str = "https",
) -> tuple[int, dict[str, list[str]], bytes]:
    environ: dict[str, object] = {}
    setup_testing_defaults(environ)
    environ["REQUEST_METHOD"] = method
    environ["PATH_INFO"] = path
    environ["QUERY_STRING"] = query
    environ["wsgi.url_scheme"] = scheme
    if origin is not None:
        environ["HTTP_ORIGIN"] = origin
    for key, value in (headers or {}).items():
        environ["HTTP_" + key.upper().replace("-", "_")] = value
    raw = b"" if body is None else json.dumps(body).encode("utf-8")
    environ["CONTENT_LENGTH"] = str(len(raw))
    environ["wsgi.input"] = io.BytesIO(raw)
    if body is not None:
        environ["CONTENT_TYPE"] = "application/json"
    environ["HTTP_COOKIE"] = cookie

    captured: dict[str, object] = {}

    def start_response(status, response_headers):
        captured["status"] = status
        captured["headers"] = response_headers

    payload = b"".join(app(environ, start_response))
    headers_out: dict[str, list[str]] = {}
    for key, value in captured["headers"]:
        headers_out.setdefault(key.lower(), []).append(value)
    return int(str(captured["status"]).split()[0]), headers_out, payload


def login(app) -> tuple[str, str]:
    status, headers, body = call(
        app, "POST", "/api/session", body={"email": "engineer@example.test", "password": PASSWORD}
    )
    assert status == 200, body
    cookies = headers["set-cookie"]
    session = next(value for value in cookies if value.startswith("cp_session="))
    csrf = next(value for value in cookies if value.startswith("cubi_csrf="))
    from urllib.parse import unquote

    return session.split(";", 1)[0], unquote(csrf.split(";", 1)[0].split("=", 1)[1])


def test_login_page_is_anonymous_and_not_cached(app):
    status, headers, body = call(app, "GET", "/login")
    assert status == 200
    assert headers["cache-control"] == ["no-store"]
    assert b"CUBI Login" in body


def test_app_without_session_redirects_to_login_and_keeps_target(app):
    status, headers, _ = call(app, "GET", "/app", query="project=preview-rps-01&view=live")
    assert status == 302
    location = headers["location"][0]
    assert location.startswith("/login?next=/app")
    assert "project%3Dpreview-rps-01" in location
    assert "view%3Dlive" in location
    assert headers["cache-control"] == ["no-store"]


def test_login_rejects_foreign_origin(app):
    status, _, body = call(
        app,
        "POST",
        "/api/session",
        body={"email": "engineer@example.test", "password": PASSWORD},
        origin="https://evil.example",
    )
    assert status == 403
    assert json.loads(body)["code"] == "ORIGIN_NOT_ALLOWED"


def test_login_rejects_missing_origin(app):
    status, _, _ = call(
        app,
        "POST",
        "/api/session",
        body={"email": "engineer@example.test", "password": PASSWORD},
        origin=None,
    )
    assert status == 403


def test_login_rejects_non_json_and_oversized_bodies(app):
    status, _, _ = call(app, "POST", "/api/session", body=None)
    assert status == 400

    environ_body = b"x" * (9 * 1024)
    status, _, _ = call(app, "POST", "/api/session", body=environ_body.decode("latin-1"))
    assert status == 400


def test_login_returns_generic_401_without_issuing_cookies(app):
    status, headers, body = call(
        app, "POST", "/api/session", body={"email": "engineer@example.test", "password": "wrong-password-1"}
    )
    assert status == 401
    assert json.loads(body) == {"code": "AUTHENTICATION_FAILED"}
    assert "set-cookie" not in headers


def test_login_sets_hardened_cookies_and_never_returns_the_token(app):
    status, headers, body = call(
        app, "POST", "/api/session", body={"email": "engineer@example.test", "password": PASSWORD}
    )
    assert status == 200
    cookies = headers["set-cookie"]
    session = next(value for value in cookies if value.startswith("cp_session="))
    for attribute in ("HttpOnly", "Secure", "SameSite=Lax", "Path=/", "Max-Age="):
        assert attribute in session
    token = session.split(";", 1)[0].split("=", 1)[1]
    payload = json.loads(body)
    assert token not in body.decode()
    assert payload["user_id"] == "user-1"
    assert payload["tenant_id"] == "tenant-a"
    assert payload["roles"] == ["planner"]
    assert "token" not in payload


def test_session_survives_across_requests_and_app_serves_shell(app):
    cookie, _ = login(app)
    status, headers, body = call(app, "GET", "/api/session", cookie=cookie)
    assert status == 200

    status, headers, body = call(app, "GET", "/app", cookie=cookie, query="project=p1&view=live")
    assert status == 200
    assert b"CUBI Workspace" in body
    assert headers["cache-control"] == ["no-store"]


def test_login_page_redirects_an_authenticated_user_to_the_next_target(app):
    cookie, _ = login(app)
    status, headers, _ = call(app, "GET", "/login", cookie=cookie, query="next=%2Fapp%3Fproject%3Dp1")
    assert status == 303
    assert headers["location"] == ["/app?project=p1"]


def test_login_page_sanitizes_open_redirect_targets(app):
    cookie, _ = login(app)
    for hostile in ("//evil.example/app", "https://evil.example/", "/\\evil", "/app\nX"):
        status, headers, _ = call(app, "GET", "/login", cookie=cookie, query=f"next={hostile}")
        if status == 303:
            assert headers["location"][0] == "/app?view=live"


def test_unsafe_api_requests_require_origin_and_csrf(app):
    cookie, csrf = login(app)

    status, _, body = call(app, "POST", "/api/projects/p1/open", cookie=cookie, origin=None)
    assert status == 403
    assert json.loads(body)["code"] == "CSRF_ORIGIN_MISMATCH"

    status, _, body = call(app, "POST", "/api/projects/p1/open", cookie=cookie, origin=ORIGIN)
    assert status == 403
    assert json.loads(body)["code"] == "CSRF_TOKEN_INVALID"

    status, _, _ = call(
        app,
        "POST",
        "/api/projects/p1/open",
        cookie=cookie,
        origin=ORIGIN,
        headers={"X-CSRF-Token": csrf},
    )
    assert status == 200


def test_unsafe_api_request_with_forged_session_cookie_is_rejected(app):
    status, _, body = call(
        app,
        "POST",
        "/api/projects/p1/open",
        cookie="cp_session=forged; cubi_csrf=forged",
        origin=ORIGIN,
        headers={"X-CSRF-Token": "forged"},
    )
    assert status == 403


def test_read_requests_do_not_require_csrf(app):
    cookie, _ = login(app)
    status, _, _ = call(app, "GET", "/api/projects", cookie=cookie)
    assert status == 200


def test_logout_requires_csrf_and_clears_cookies(app):
    cookie, csrf = login(app)
    status, _, _ = call(app, "DELETE", "/api/session", cookie=cookie, origin=ORIGIN)
    assert status == 403

    status, headers, _ = call(
        app, "DELETE", "/api/session", cookie=cookie, origin=ORIGIN, headers={"X-CSRF-Token": csrf}
    )
    assert status == 204
    cookies = headers["set-cookie"]
    assert any(value.startswith("cp_session=;") and "Max-Age=0" in value for value in cookies)
    assert any(value.startswith("cubi_csrf=;") and "Max-Age=0" in value for value in cookies)

    token = cookie.split("=", 1)[1]
    assert app.identity.resolve(token) is None
    status, _, _ = call(app, "GET", "/app", cookie=cookie)
    assert status == 302


def test_logout_without_a_session_still_clears_cookies(app):
    status, headers, _ = call(app, "DELETE", "/api/session", origin=ORIGIN)
    assert status == 204
    assert "set-cookie" in headers


def test_api_rewrite_path_is_restored_before_delegation(app):
    cookie, _ = login(app)
    status, _, body = call(
        app, "GET", "/api/index", cookie=cookie, query="__path=projects&x=1"
    )
    assert status == 200
    assert json.loads(body)["seen"] == "/api/projects"


def test_platform_header_fallback_restores_the_original_api_path(app):
    cookie, _ = login(app)
    status, _, body = call(
        app,
        "GET",
        "/api/index",
        cookie=cookie,
        headers={"X-Vercel-Original-Path": "/api/projects/p1"},
    )
    assert status == 200
    assert json.loads(body)["seen"] == "/api/projects/p1"


def test_health_endpoints_are_split(app):
    status, _, body = call(app, "GET", "/api/health/live")
    assert status == 200
    assert json.loads(body)["status"] == "ok"

    status, _, body = call(app, "GET", "/api/health/ready")
    assert status == 200
    assert json.loads(body)["status"] == "ready"


def test_readiness_failure_returns_503(site_root, identity):
    app = ProductionWebApp(
        api_app=StubApi(),
        identity=identity,
        site=StaticSite(site_root),
        public_origin=ORIGIN,
        secure_cookies=True,
        readiness=lambda: {"status": "not_ready"},
    )
    status, _, body = call(app, "GET", "/api/health/ready")
    assert status == 503
    assert json.loads(body)["status"] == "not_ready"


def test_static_assets_have_cache_headers_and_no_directory_listing(app):
    status, headers, body = call(app, "GET", "/theme.css", origin=None)
    assert status == 200
    assert headers["content-type"] == ["text/css; charset=utf-8"]
    assert body == b"body{}"

    status, headers, _ = call(app, "GET", "/dist/main.js", origin=None)
    assert status == 200
    assert "immutable" in headers["cache-control"][0]

    # The Vercel build flattens bundles into public/dist; the shell references
    # them as /dist/<name>.bundle.js.
    status, _, _ = call(app, "GET", "/dist/landing-entry.bundle.js", origin=None)
    assert status == 200

    status, _, _ = call(app, "GET", "/", origin=None)
    assert status == 200


def test_static_site_refuses_traversal_and_dotfiles(app, site_root):
    assert call(app, "GET", "/../secret.txt", origin=None)[0] == 404
    assert call(app, "GET", "/%2e%2e/secret.txt", origin=None)[0] == 404
    assert call(app, "GET", "/.git/config", origin=None)[0] == 404
    assert call(app, "GET", "/missing-file.js", origin=None)[0] == 404


def test_security_headers_and_hsts(app):
    status, headers, _ = call(app, "GET", "/login", scheme="https", origin=None)
    assert status == 200
    assert headers["x-content-type-options"] == ["nosniff"]
    assert headers["x-frame-options"] == ["DENY"]
    assert headers["referrer-policy"] == ["no-referrer"]
    assert headers["strict-transport-security"] == ["max-age=63072000; includeSubDomains"]


def test_unsupported_method_on_html_surface_is_405(app):
    status, _, body = call(app, "POST", "/login", origin=None)
    assert status == 405
    assert json.loads(body)["code"] == "METHOD_NOT_ALLOWED"


def test_unknown_api_route_goes_to_the_application_app(app):
    cookie, _ = login(app)
    status, _, _ = call(app, "GET", "/api/v2/workspace/control-room/read", cookie=cookie)
    assert status == 200


def test_plain_http_origins_are_only_accepted_on_loopback(site_root, identity):
    def build(origin: str) -> ProductionWebApp:
        return ProductionWebApp(
            api_app=StubApi(),
            identity=identity,
            site=StaticSite(site_root),
            public_origin=origin,
            secure_cookies=False,
            readiness=lambda: {"status": "ready"},
        )

    build("http://127.0.0.1:4180")
    build("http://localhost:4180")
    with pytest.raises(ValueError):
        build("http://cubi.example.test")
    with pytest.raises(ValueError):
        build("http://203.0.113.9")


def test_direct_catch_all_function_invocation_has_no_route(identity, site_root):
    stub = StubApi()
    app = ProductionWebApp(
        api_app=stub,
        identity=identity,
        site=StaticSite(site_root),
        public_origin=ORIGIN,
        secure_cookies=True,
        readiness=lambda: {"status": "ready"},
    )
    cookie, _ = login(app)
    status, _, body = call(app, "GET", "/api", cookie=cookie)
    assert status == 200
    assert json.loads(body)["seen"] == "/api/__cubi_root"


def test_client_ip_prefers_the_platform_single_value_header():
    environ = {
        "HTTP_X_REAL_IP": "203.0.113.5",
        "HTTP_X_FORWARDED_FOR": "198.51.100.9, 203.0.113.5",
    }
    assert _client_ip(environ) == "203.0.113.5"
    assert _client_ip({"HTTP_X_FORWARDED_FOR": "198.51.100.9, 203.0.113.5"}) == "198.51.100.9"
    assert _client_ip({"REMOTE_ADDR": "203.0.113.7"}) == "203.0.113.7"
