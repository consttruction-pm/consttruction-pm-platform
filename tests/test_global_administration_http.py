"""HTTP-level tests for ``/api/admin/*`` through the real production boundary.

These tests exercise ``ProductionWebApp`` -> CSRF/origin gate ->
``GlobalAdministrationHttpMiddleware`` -> ``GlobalAdministrationService`` with a
real PostgreSQL identity store. They only run when
``CONSTRUCTION_PM_POSTGRES_DSN`` is set (CI skips them; the evidence run sets it).

The point is to prove what the unit tests cannot: that the administrator's
browser session cookie is the one the platform actually issues, that the CSRF
header is enforced, that a non-admin session is rejected with 403 at the HTTP
layer, and that reauthentication failures reach the client as 403 rather than
silently succeeding.
"""

from __future__ import annotations

import io
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote
from wsgiref.util import setup_testing_defaults

import pytest

from construction_pm.deployment.production_web import ProductionWebApp, StaticSite
from construction_pm.global_administration import (
    GLOBAL_ADMIN_ROLE,
    GlobalAdministrationService,
    PostgresGlobalAdministrationStore,
)
from construction_pm.global_administration_http import GlobalAdministrationHttpMiddleware
from construction_pm.identity_session import (
    SESSION_COOKIE_NAME,
    IdentityService,
    IdentityUser,
    PostgresIdentityStore,
    hash_password,
)

ORIGIN = "https://cubi.example.test"
CSRF_SECRET = "admin-http-test-secret-0123456789abcd"
LIVE = bool(os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"))


class _StubApi:
    """Fallback app: it must never be reached for ``/api/admin``."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, environ, start_response):  # noqa: ANN001 - WSGI
        self.calls.append(str(environ.get("PATH_INFO", "")))
        body = json.dumps({"ok": True}).encode("utf-8")
        start_response("200 OK", [("Content-Type", "application/json"), ("Content-Length", str(len(body)))])
        return [body]


def test_session_cookie_is_the_platform_cookie() -> None:
    # Regression guard: the middleware once read ``cubi_session`` while the
    # platform issues ``cp_session``, so every real request was 401.
    from construction_pm import global_administration_http as module

    assert module.SESSION_COOKIE == SESSION_COOKIE_NAME == "cp_session"


def call(app, method: str, path: str, *, body: object | None = None, cookie: str = "",
         headers: dict[str, str] | None = None, query: str = "") -> tuple[int, dict[str, list[str]], bytes]:
    environ: dict[str, object] = {}
    setup_testing_defaults(environ)
    environ["REQUEST_METHOD"] = method
    environ["PATH_INFO"] = path
    environ["QUERY_STRING"] = query
    environ["wsgi.url_scheme"] = "https"
    environ["HTTP_ORIGIN"] = ORIGIN
    for key, value in (headers or {}).items():
        environ["HTTP_" + key.upper().replace("-", "_")] = value
    raw = b"" if body is None else json.dumps(body).encode("utf-8")
    environ["CONTENT_LENGTH"] = str(len(raw))
    environ["wsgi.input"] = io.BytesIO(raw)
    if body is not None:
        environ["CONTENT_TYPE"] = "application/json"
    environ["HTTP_COOKIE"] = cookie
    captured: dict[str, object] = {}

    def start_response(status, response_headers):  # noqa: ANN001
        captured["status"] = status
        captured["headers"] = response_headers

    payload = b"".join(app(environ, start_response))
    out: dict[str, list[str]] = {}
    for key, value in captured["headers"]:
        out.setdefault(key.lower(), []).append(value)
    return int(str(captured["status"]).split()[0]), out, payload


def _cookies(headers: dict[str, list[str]]) -> tuple[str, str]:
    values = headers.get("set-cookie", [])
    session = next(value for value in values if value.startswith(f"{SESSION_COOKIE_NAME}="))
    csrf = next(value for value in values if value.startswith("cubi_csrf="))
    token = session.split(";", 1)[0]
    csrf_value = unquote(csrf.split(";", 1)[0].split("=", 1)[1])
    return token, csrf_value


LIVE_REASON = "CONSTRUCTION_PM_POSTGRES_DSN is not configured"
live = pytest.mark.skipif(not LIVE, reason=LIVE_REASON)


def _connect():
    import psycopg

    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"], autocommit=False)


def _bootstrap(connection) -> None:
    from construction_pm.deployment.schema import initialize_production_schema

    initialize_production_schema(connection)
    connection.commit()


@live
def test_live_admin_http_flow(tmp_path: Path) -> None:
    suffix = secrets.token_hex(4)
    admin_email = f"owner-{suffix}@cubisite.test"
    admin_password = "Owner-" + secrets.token_urlsafe(12)

    (tmp_path / "index.html").write_text("<!doctype html><title>CUBI</title>", encoding="utf-8")
    (tmp_path / "app.html").write_text("<!doctype html><title>CUBI Workspace</title>", encoding="utf-8")
    (tmp_path / "login.html").write_text("<!doctype html><title>CUBI Login</title>", encoding="utf-8")

    with _connect() as connection:
        _bootstrap(connection)
        store = PostgresIdentityStore(connection)
        store.upsert_user(
            IdentityUser(
                user_id=f"usr-owner-{suffix}",
                tenant_id="platform-owner",
                email=admin_email,
                display_name="Product Owner",
                roles=frozenset({GLOBAL_ADMIN_ROLE}),
                password_hash=hash_password(admin_password),
            )
        )
        connection.commit()

        identity = IdentityService(store, csrf_secret=CSRF_SECRET)
        service = GlobalAdministrationService(PostgresGlobalAdministrationStore(connection), identity)
        stub = _StubApi()
        app = ProductionWebApp(
            api_app=GlobalAdministrationHttpMiddleware(stub, service),
            identity=identity,
            site=StaticSite(tmp_path),
            public_origin=ORIGIN,
            secure_cookies=True,
            readiness=lambda: {"status": "ready", "components": []},
        )

        # 1. No session -> 401 from the admin boundary, not a redirect.
        status, _, body = call(app, "GET", "/api/admin/dashboard")
        assert status == 401, body
        assert json.loads(body)["code"] == "SESSION_REQUIRED"

        # 2. Login issues the platform's cookie names.
        status, headers, body = call(
            app, "POST", "/api/session", body={"email": admin_email, "password": admin_password}
        )
        assert status == 200, body
        session_cookie, csrf = _cookies(headers)
        connection.commit()

        def admin(method: str, path: str, *, body: object | None = None, with_csrf: bool = True, query: str = ""):
            extra = {"X-CSRF-Token": csrf} if with_csrf else {}
            return call(app, method, path, body=body, cookie=session_cookie, headers=extra, query=query)

        # 3. Dashboard and roles.
        status, _, body = admin("GET", "/api/admin/dashboard")
        assert status == 200, body
        dashboard = json.loads(body)
        assert dashboard["database"] == "connected"
        assert len(dashboard["role_catalog"]) == 11

        status, _, body = admin("GET", "/api/admin/roles")
        assert status == 200 and len(json.loads(body)["roles"]) == 11

        # 4. A state-changing call without the CSRF header is rejected upstream.
        status, _, body = admin("POST", "/api/admin/users", body={}, with_csrf=False)
        assert status == 403, body
        assert json.loads(body)["code"] == "CSRF_TOKEN_INVALID"

        # 5. Create a normal user, then edit it: enable/lock/role change.
        created_email = f"editor-{suffix}@cubisite.test"
        status, _, body = admin(
            "POST",
            "/api/admin/users",
            body={
                "email": created_email,
                "tenant_id": f"org-{suffix}",
                "display_name": "Editor",
                "roles": ["engineering_viewer"],
                "locale": "fa",
            },
        )
        assert status == 201, body
        created = json.loads(body)
        user_id = created["user"]["user_id"]
        first_password = created["temporary_password"]
        assert created["user"]["role_keys"] == ["engineering_viewer"]
        connection.commit()

        status, _, body = admin("PATCH", f"/api/admin/users/{user_id}", body={"roles": ["engineering_planner"], "locked": True})
        assert status == 200, body
        updated = json.loads(body)["user"]
        assert updated["role_keys"] == ["engineering_planner"]
        assert updated["locked"] is True
        connection.commit()

        status, _, body = admin("PATCH", f"/api/admin/users/{user_id}", body={"locked": False, "display_name": "Editor Two"})
        assert status == 200, body
        assert json.loads(body)["user"]["display_name"] == "Editor Two"
        connection.commit()

        # 6. A test account needs a test tenant and an expiry.
        status, _, body = admin(
            "POST",
            "/api/admin/users",
            body={
                "email": f"test-{suffix}@cubisite.test",
                "tenant_id": f"test-{suffix}",
                "display_name": "Test",
                "roles": ["test_user"],
                "is_test_user": True,
                "locale": "en",
            },
        )
        assert status == 400, body
        assert json.loads(body)["code"] == "TEST_USER_REQUIRES_EXPIRY"

        status, _, body = admin(
            "POST",
            "/api/admin/users",
            body={
                "email": f"test-{suffix}@cubisite.test",
                "tenant_id": f"test-{suffix}",
                "display_name": "Test",
                "roles": ["test_user"],
                "is_test_user": True,
                "locale": "en",
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
            },
        )
        assert status == 201, body
        test_payload = json.loads(body)
        test_user = test_payload["user"]
        test_password = test_payload["temporary_password"]
        assert test_user["is_test_user"] is True
        connection.commit()

        # 7. Granting/removing global_admin requires reauthentication.
        status, _, body = admin("PATCH", f"/api/admin/users/{user_id}", body={"roles": ["global_admin"]})
        assert status == 403, body
        assert json.loads(body)["code"] == "REAUTHENTICATION_REQUIRED"

        status, _, body = admin(
            "PATCH",
            f"/api/admin/users/{user_id}",
            body={"roles": ["global_admin"], "confirm_password": "wrong-password"},
        )
        assert status == 403, body
        assert json.loads(body)["code"] == "REAUTHENTICATION_FAILED"

        status, _, body = admin(
            "PATCH",
            f"/api/admin/users/{user_id}",
            body={"roles": ["global_admin"], "confirm_password": admin_password},
        )
        assert status == 200, body
        connection.commit()

        # 8. A non-admin session (the disposable test account) is rejected at the
        # HTTP layer, even though it is a perfectly valid login.
        status, headers, body = call(
            app, "POST", "/api/session", body={"email": f"test-{suffix}@cubisite.test", "password": test_password}
        )
        assert status == 200, body
        child_cookie, _ = _cookies(headers)
        connection.commit()
        status, _, body = call(app, "GET", "/api/admin/dashboard", cookie=child_cookie)
        assert status == 403, body
        assert json.loads(body)["code"] == "GLOBAL_ADMIN_REQUIRED"

        # 9. Password reset requires reauthentication, then works.
        status, headers, body = call(
            app, "POST", "/api/session", body={"email": created_email, "password": first_password}
        )
        assert status == 200, body
        child_cookie, _ = _cookies(headers)
        connection.commit()
        status, _, body = admin("POST", f"/api/admin/users/{user_id}/password-reset", body={})
        assert status == 403, body
        assert json.loads(body)["code"] == "REAUTHENTICATION_REQUIRED"

        status, _, body = admin(
            "POST",
            f"/api/admin/users/{user_id}/password-reset",
            body={"confirm_password": admin_password, "reason": "http test"},
        )
        assert status == 200, body
        second_password = json.loads(body)["temporary_password"]
        assert second_password and second_password != first_password
        connection.commit()

        # The old child session is revoked by the reset, and the new password logs in.
        status, _, body = call(app, "GET", "/api/admin/users", cookie=child_cookie, query="limit=5")
        assert status == 401, body
        status, headers, body = call(
            app, "POST", "/api/session", body={"email": created_email, "password": second_password}
        )
        assert status == 200, body
        fresh_cookie, _ = _cookies(headers)
        connection.commit()

        # 10. Revoke sessions requires reauthentication and kills the child session.
        status, _, body = admin(
            "POST",
            f"/api/admin/users/{user_id}/revoke-sessions",
            body={"confirm_password": admin_password},
        )
        assert status == 200, body
        assert json.loads(body)["sessions_revoked"] >= 1
        connection.commit()
        status, _, _ = call(app, "GET", "/api/admin/users", cookie=fresh_cookie, query="limit=5")
        assert status == 401

        # 11. The audit trail recorded the actions.
        status, _, body = admin("GET", "/api/admin/audit", query="limit=50")
        assert status == 200, body
        actions = {entry["action"] for entry in json.loads(body)["entries"]}
        assert {"user.create", "user.update", "user.password_reset", "user.sessions_revoked"} <= actions

        # 12. An expired test account cannot log in (login-time enforcement).
        status, _, body = admin(
            "POST",
            "/api/admin/users",
            body={
                "email": f"expired-{suffix}@cubisite.test",
                "tenant_id": f"test-{suffix}",
                "display_name": "Expired",
                "roles": ["test_user"],
                "is_test_user": True,
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
            },
        )
        assert status == 201, body
        expired_id = json.loads(body)["user"]["user_id"]
        expired_password = json.loads(body)["temporary_password"]
        status, _, body = admin(
            "PATCH",
            f"/api/admin/users/{expired_id}",
            body={"expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()},
        )
        assert status == 200, body
        connection.commit()
        status, headers, _ = call(
            app, "POST", "/api/session", body={"email": f"expired-{suffix}@cubisite.test", "password": expired_password}
        )
        assert status == 401
        assert "set-cookie" not in headers

        # The stub API never saw an admin path.
        assert not [path for path in stub.calls if path.startswith("/api/admin")]
