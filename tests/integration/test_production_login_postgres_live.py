"""Live PostgreSQL coverage for the production login and workspace surface.

Run with ``CONSTRUCTION_PM_POSTGRES_DSN`` pointing at a disposable database:

    CONSTRUCTION_PM_POSTGRES_DSN=postgresql://postgres@127.0.0.1:55432/cubi_prod_test \
        PYTHONPATH=src python -m pytest -q tests/integration/test_production_login_postgres_live.py

These tests drive the exact WSGI application that ``api/index.py`` exports on
Vercel, through real HTTP semantics (cookies, CSRF, origin, refresh), with
PostgreSQL persistence. They never rely on preview/demo identities.
"""

from __future__ import annotations

import io
import json
import os
import uuid
from pathlib import Path

import pytest

from construction_pm.deployment.production_runtime import (
    ProductionRuntime,
    ProductionSettings,
)
from construction_pm.identity_session import IdentityUser, PostgresIdentityStore, hash_password

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)

ORIGIN = "https://cubi.example.test"
SECRET = "integration-session-secret-0123456789abcdef"
PASSWORD = "correct horse battery staple"
VIEWER_PASSWORD = "viewer horse battery staple"
WEB_ROOT = Path(__file__).resolve().parents[2] / "apps" / "web"


@pytest.fixture(scope="module")
def runtime() -> ProductionRuntime:
    settings = ProductionSettings(
        database_url=os.environ["CONSTRUCTION_PM_POSTGRES_DSN"],
        session_secret=SECRET,
        public_origin=ORIGIN,
        secure_cookies=True,
        static_root=WEB_ROOT,
        max_pool_size=2,
    )
    instance = ProductionRuntime(settings)
    instance._initialize()

    suffix = uuid.uuid4().hex[:10]
    tenant_a = f"tenant-a-{suffix}"
    tenant_b = f"tenant-b-{suffix}"
    project_a = f"project-a-{suffix}"
    project_b = f"project-b-{suffix}"
    users = {
        "admin": IdentityUser(
            user_id=f"user-admin-{suffix}",
            tenant_id=tenant_a,
            email=f"admin-{suffix}@example.test",
            display_name="Admin",
            roles=frozenset({"project_admin"}),
            password_hash=hash_password(PASSWORD),
        ),
        "viewer": IdentityUser(
            user_id=f"user-viewer-{suffix}",
            tenant_id=tenant_a,
            email=f"viewer-{suffix}@example.test",
            display_name="Viewer",
            roles=frozenset({"viewer"}),
            password_hash=hash_password(VIEWER_PASSWORD),
        ),
        "planner": IdentityUser(
            user_id=f"user-planner-{suffix}",
            tenant_id=tenant_a,
            email=f"planner-{suffix}@example.test",
            display_name="Planner",
            roles=frozenset({"planner"}),
            password_hash=hash_password(PASSWORD),
        ),
        "outsider": IdentityUser(
            user_id=f"user-outsider-{suffix}",
            tenant_id=tenant_b,
            email=f"outsider-{suffix}@example.test",
            display_name="Outsider",
            roles=frozenset({"project_admin"}),
            password_hash=hash_password(PASSWORD),
        ),
    }
    connection = instance.pool.acquire()
    try:
        store = PostgresIdentityStore(connection)
        for user in users.values():
            store.upsert_user(user)
        for tenant, project, name in (
            (tenant_a, project_a, "Authorized Project"),
            (tenant_b, project_b, "Other Tenant Project"),
        ):
            connection.execute(
                "INSERT INTO project_lifecycle_projects "
                "(tenant_id, project_id, name) VALUES (%s, %s, %s) "
                "ON CONFLICT (tenant_id, project_id) DO NOTHING",
                (tenant, project, name),
            )
        for user in users.values():
            connection.execute(
                "INSERT INTO project_lifecycle_memberships "
                "(tenant_id, project_id, user_id) VALUES (%s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                (
                    user.tenant_id,
                    project_a if user.tenant_id == tenant_a else project_b,
                    user.user_id,
                ),
            )
        connection.commit()
    finally:
        instance.pool.release(connection, healthy=True)

    instance.test_ids = {  # type: ignore[attr-defined]
        "users": users,
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "project_a": project_a,
        "project_b": project_b,
        # Failed logins are throttled per source IP for 15 minutes and the
        # throttle state is durable. A per-run address keeps the module
        # repeatable against a long-lived database.
        "client_ip": f"2001:db8::{suffix}",
    }
    yield instance
    instance.close()


def call(runtime, method, path, *, body=None, cookie="", csrf="", query="", headers=None):
    from wsgiref.util import setup_testing_defaults

    environ: dict[str, object] = {}
    setup_testing_defaults(environ)
    environ["REQUEST_METHOD"] = method
    environ["PATH_INFO"] = path
    environ["QUERY_STRING"] = query
    environ["wsgi.url_scheme"] = "https"
    environ["HTTP_ORIGIN"] = ORIGIN
    environ["HTTP_X_FORWARDED_PROTO"] = "https"
    environ["HTTP_X_FORWARDED_FOR"] = runtime.test_ids.get("client_ip", "203.0.113.7")
    for key, value in (headers or {}).items():
        environ["HTTP_" + key.upper().replace("-", "_")] = value
    raw = b"" if body is None else json.dumps(body).encode("utf-8")
    environ["CONTENT_LENGTH"] = str(len(raw))
    environ["wsgi.input"] = io.BytesIO(raw)
    if body is not None:
        environ["CONTENT_TYPE"] = "application/json"
    environ["HTTP_COOKIE"] = cookie
    if csrf:
        environ["HTTP_X_CSRF_TOKEN"] = csrf

    captured: dict[str, object] = {}

    def start_response(status, response_headers):
        captured["status"] = status
        captured["headers"] = response_headers

    payload = b"".join(runtime(environ, start_response))
    headers_out: dict[str, list[str]] = {}
    for key, value in captured["headers"]:
        headers_out.setdefault(key.lower(), []).append(value)
    return int(str(captured["status"]).split()[0]), headers_out, payload


def login(runtime, user_key: str, password: str = PASSWORD) -> tuple[str, str]:
    from urllib.parse import unquote

    user = runtime.test_ids["users"][user_key]
    status, headers, body = call(
        runtime, "POST", "/api/session", body={"email": user.email, "password": password}
    )
    assert status == 200, body
    cookies = headers["set-cookie"]
    session = next(value for value in cookies if value.startswith("cp_session="))
    csrf = next(value for value in cookies if value.startswith("cubi_csrf="))
    assert "Secure" in session and "HttpOnly" in session
    return (
        session.split(";", 1)[0],
        unquote(csrf.split(";", 1)[0].split("=", 1)[1]),
    )


def test_health_readiness_uses_the_database(runtime):
    status, _, body = call(runtime, "GET", "/api/health/live")
    assert status == 200
    assert json.loads(body)["status"] == "ok"

    status, _, body = call(runtime, "GET", "/api/health/ready")
    assert status == 200
    assert json.loads(body)["status"] == "ready"


def test_unauthenticated_app_is_gated_and_api_rejects(runtime):
    status, headers, _ = call(runtime, "GET", "/app", query="project=x&view=live")
    assert status == 302
    assert headers["location"][0].startswith("/login?next=")

    status, _, body = call(runtime, "GET", "/api/session")
    assert status == 401
    assert json.loads(body)["code"] == "SESSION_REQUIRED"


def test_wrong_password_is_generic_and_does_not_issue_a_session(runtime):
    user = runtime.test_ids["users"]["admin"]
    status, headers, body = call(
        runtime, "POST", "/api/session", body={"email": user.email, "password": "wrong password value"}
    )
    assert status == 401
    assert json.loads(body)["code"] == "AUTHENTICATION_FAILED"
    assert "set-cookie" not in headers


def test_admin_full_flow_login_projects_open_workspace_refresh_logout(runtime):
    ids = runtime.test_ids
    cookie, csrf = login(runtime, "admin")

    status, _, body = call(runtime, "GET", "/api/session", cookie=cookie)
    assert status == 200
    session = json.loads(body)
    assert session["user_id"] == ids["users"]["admin"].user_id
    assert session["tenant_id"] == ids["tenant_a"]
    assert cookie.split("=", 1)[1] not in body.decode()

    status, _, body = call(runtime, "GET", "/api/projects", cookie=cookie)
    assert status == 200
    listed = json.loads(body)["projects"]
    assert [project["project_id"] for project in listed] == [ids["project_a"]]

    status, _, body = call(
        runtime, "POST", f"/api/projects/{ids['project_a']}/open", cookie=cookie
    )
    assert status == 403
    assert json.loads(body)["code"] == "CSRF_TOKEN_INVALID"

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{ids['project_a']}/open",
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    context = json.loads(body)["context"]
    assert context == {
        "tenant_id": ids["tenant_a"],
        "project_id": ids["project_a"],
        "revision": 0,
        "user_id": ids["users"]["admin"].user_id,
    }

    status, _, body = call(
        runtime,
        "GET",
        "/api/v2/workspace/control-room/read",
        cookie=cookie,
        headers={
            "X-Tenant-Id": ids["tenant_a"],
            "X-Project-Id": ids["project_a"],
            "X-Project-Revision": "0",
        },
    )
    assert status == 200, body
    workspace = json.loads(body)
    assert workspace["contract_version"] == "workspace-control-room-read.v2"

    status, _, body = call(
        runtime, "GET", "/app", cookie=cookie, query="project=" + ids["project_a"] + "&view=live"
    )
    assert status == 200
    assert b"<html" in body.lower()

    # Refresh: the same cookie still resolves to the same project scope.
    status, _, body = call(runtime, "GET", "/api/session", cookie=cookie)
    assert status == 200
    status, _, body = call(runtime, "GET", "/api/projects", cookie=cookie)
    assert status == 200
    assert [project["project_id"] for project in json.loads(body)["projects"]] == [
        ids["project_a"]
    ]

    status, _, _ = call(runtime, "DELETE", "/api/session", cookie=cookie, csrf=csrf)
    assert status == 204

    status, _, body = call(runtime, "GET", "/api/session", cookie=cookie)
    assert status == 401
    status, headers, _ = call(runtime, "GET", "/app", cookie=cookie)
    assert status == 302


def test_viewer_can_read_but_not_mutate(runtime):
    ids = runtime.test_ids
    cookie, csrf = login(runtime, "viewer", VIEWER_PASSWORD)

    status, _, body = call(
        runtime, "GET", f"/api/projects/{ids['project_a']}", cookie=cookie
    )
    assert status == 200
    revision = json.loads(body)["project"]["revision"]

    status, _, _ = call(
        runtime,
        "GET",
        "/api/v2/workspace/control-room/read",
        cookie=cookie,
        headers={
            "X-Tenant-Id": ids["tenant_a"],
            "X-Project-Id": ids["project_a"],
            "X-Project-Revision": str(revision),
        },
    )
    assert status == 200

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{ids['project_a']}/p6/udfs/p6-field-registry.v1",
        cookie=cookie,
        csrf=csrf,
        body={
            "udf_id": "UDF-LIVE-VIEWER",
            "subject_area": "Activity",
            "display_name": "Viewer Attempt",
            "data_type": "string",
        },
    )
    assert status == 403
    assert json.loads(body)["code"] == "AUTHORIZATION_PERMISSION_DENIED"


def test_planner_can_write_project_but_not_administer(runtime):
    ids = runtime.test_ids
    cookie, csrf = login(runtime, "planner")

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{ids['project_a']}/p6/udfs/p6-field-registry.v1",
        cookie=cookie,
        csrf=csrf,
        body={
            "udf_id": "UDF-LIVE-PLANNER",
            "subject_area": "Activity",
            "display_name": "Planner Field",
            "data_type": "string",
        },
    )
    assert status == 200, body

    status, _, body = call(
        runtime,
        "POST",
        "/api/projects",
        cookie=cookie,
        csrf=csrf,
        body={"project_id": f"planner-created-{uuid.uuid4().hex[:6]}", "name": "Nope"},
    )
    assert status == 403


def test_admin_can_create_a_project(runtime):
    ids = runtime.test_ids
    cookie, csrf = login(runtime, "admin")
    project_id = f"admin-created-{uuid.uuid4().hex[:8]}"
    status, _, body = call(
        runtime,
        "POST",
        "/api/projects",
        cookie=cookie,
        csrf=csrf,
        body={"project_id": project_id, "name": "New Project"},
    )
    assert status == 201, body
    created = json.loads(body)["context"]
    assert created["project_id"] == project_id
    assert created["tenant_id"] == ids["tenant_a"]


def test_cross_tenant_scope_is_rejected(runtime):
    ids = runtime.test_ids
    cookie, csrf = login(runtime, "admin")

    # Tenant A's admin cannot open tenant B's project.
    status, _, _ = call(
        runtime, "POST", f"/api/projects/{ids['project_b']}/open", cookie=cookie, csrf=csrf
    )
    assert status == 403

    # Nor can the request header redirect the read to another tenant.
    status, _, body = call(
        runtime,
        "GET",
        "/api/v2/workspace/control-room/read",
        cookie=cookie,
        headers={
            "X-Tenant-Id": ids["tenant_b"],
            "X-Project-Id": ids["project_a"],
            "X-Project-Revision": "0",
        },
    )
    assert status == 403
    assert json.loads(body)["code"] == "CROSS_SCOPE_ACCESS"

    # The tenant B user holds a membership in tenant B's project only.
    outsider_cookie, outsider_csrf = login(runtime, "outsider")
    status, _, _ = call(
        runtime, "POST", f"/api/projects/{ids['project_a']}/open", cookie=outsider_cookie, csrf=outsider_csrf
    )
    assert status == 403

    outsider_cookie, _ = login(runtime, "outsider")
    status, _, body = call(runtime, "GET", "/api/projects", cookie=outsider_cookie)
    assert status == 200
    assert [project["project_id"] for project in json.loads(body)["projects"]] == [
        ids["project_b"]
    ]
    status, _, body = call(runtime, "GET", "/api/projects", cookie=outsider_cookie)
    assert status == 200
    assert ids["project_a"] not in body.decode()


def test_stale_revision_is_rejected(runtime):
    ids = runtime.test_ids
    cookie, _ = login(runtime, "admin")
    status, _, body = call(
        runtime,
        "GET",
        "/api/v2/workspace/control-room/read",
        cookie=cookie,
        headers={
            "X-Tenant-Id": ids["tenant_a"],
            "X-Project-Id": ids["project_a"],
            "X-Project-Revision": "999",
        },
    )
    assert status == 409
    assert json.loads(body)["code"] == "STALE_WORKSPACE_READ_SCOPE"


def test_login_rate_limit_returns_429(runtime):
    user = runtime.test_ids["users"]["planner"]
    attempt = {"email": user.email, "password": "definitely wrong password"}
    statuses = [
        call(runtime, "POST", "/api/session", body=attempt)[0] for _ in range(6)
    ]
    assert statuses[:5] == [401] * 5
    assert statuses[5] == 429
    status, headers, _ = call(runtime, "POST", "/api/session", body=attempt)
    assert status == 429
    assert headers["retry-after"] == ["900"]
