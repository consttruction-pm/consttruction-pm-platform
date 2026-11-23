"""Access rules for the shared Reference Testing Workspace.

The reference dataset is one shared copy. Every authenticated user may read it,
nobody may edit the source project through an ordinary project write, and the
reviewer / test-operator roles have distinct, explicit scopes. These tests
exercise the real WSGI application and the real SQLite preview store; they do
not assert fixture values for calculated data.
"""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    Permission,
    default_project_policy,
    default_role_permissions,
)
from construction_pm.application.reference_access import (
    REFERENCE_WORKSPACE_ROLES,
    ReferenceReadOnlyPolicy,
)
from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.server import build_preview_application
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE, PREVIEW_TENANT_ID

REFERENCE_PROJECTS = ("CUBI-REF-001", "CUBI-REF-002", "CUBI-REF-003")


def _request_with_headers(
    app,
    method: str,
    path: str,
    *,
    body: bytes = b"",
    cookie: str | None = None,
    headers: dict[str, str] | None = None,
    content_type: str = "application/json",
):
    parsed = urlsplit(path)
    environ: dict[str, object] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": parsed.path or "/",
        "QUERY_STRING": parsed.query,
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
    return (
        int(str(captured["status"]).split(" ", 1)[0]),
        captured["headers"],
        chunks,
    )


def _request(app, method: str, path: str, **kwargs):
    status, _headers, chunks = _request_with_headers(app, method, path, **kwargs)
    return status, chunks


@pytest.fixture(scope="module")
def runtime(tmp_path_factory):
    path = tmp_path_factory.mktemp("reference-access") / "preview.sqlite3"
    instance = open_preview_runtime(path, reset=True)
    yield instance
    instance.close()


def _session(runtime, role: str):
    return runtime.sessions.create(DEMO_USERS_BY_ROLE[role])


def _project_ids(runtime, role: str) -> list[str]:
    session = _session(runtime, role)
    status, body = _request(runtime.app, "GET", "/api/projects", cookie=session.session_id)
    assert status == 200, body[:300]
    return [item["project_id"] for item in json.loads(body)["projects"]]


def test_reference_roles_are_read_derived() -> None:
    permissions = default_role_permissions()

    assert REFERENCE_WORKSPACE_ROLES == {"viewer", "reviewer", "test_operator"}
    assert Permission.PROJECT_READ in permissions["reviewer"]
    assert Permission.CALCULATION_RUN in permissions["reviewer"]
    assert Permission.SCENARIO_READ in permissions["reviewer"]
    assert Permission.SCENARIO_WRITE not in permissions["reviewer"]

    assert Permission.SCENARIO_WRITE in permissions["test_operator"]
    assert Permission.CALCULATION_RUN in permissions["test_operator"]

    # A source edit is never part of a reference role, and a scenario grant is
    # not an alias of project write.
    for role in REFERENCE_WORKSPACE_ROLES:
        assert Permission.PROJECT_WRITE not in permissions[role]
        assert Permission.PROJECT_ADMIN not in permissions[role]
        assert Permission.PROJECT_SCHEDULE not in permissions[role]


def test_reference_policy_denies_source_mutation_even_for_a_planner() -> None:
    policy = ReferenceReadOnlyPolicy(default_project_policy(), REFERENCE_PROJECTS)
    planner = frozenset({"planner"})

    def context(project_id: str) -> AuthorizationContext:
        return AuthorizationContext(PREVIEW_TENANT_ID, project_id, "preview-planner", planner)

    assert policy.is_allowed(context("CUBI-REF-001"), Permission.PROJECT_READ)
    for permission in (
        Permission.PROJECT_WRITE,
        Permission.PROJECT_ADMIN,
        Permission.PROJECT_SCHEDULE,
    ):
        assert not policy.is_allowed(context("CUBI-REF-001"), permission)
        with pytest.raises(PermissionError):
            policy.require(context("CUBI-REF-001"), permission)

    # The rule is scoped to the reference dataset, not to every project.
    assert policy.is_allowed(context("preview-rps-01"), Permission.PROJECT_WRITE)


def test_reviewer_reads_the_shared_reference_dataset_without_membership(runtime) -> None:
    for role in ("reviewer", "test_operator"):
        ids = _project_ids(runtime, role)
        assert sorted(ids) == sorted(REFERENCE_PROJECTS), (role, ids)

        session = _session(runtime, role)
        status, body = _request(
            runtime.app, "GET", "/api/projects/CUBI-REF-001", cookie=session.session_id
        )
        assert status == 200, body[:300]
        assert json.loads(body)["project"]["project_id"] == "CUBI-REF-001"

        status, body = _request(
            runtime.app,
            "GET",
            "/api/projects/CUBI-REF-001/p6/activities",
            cookie=session.session_id,
            headers={
                "X-Tenant-Id": PREVIEW_TENANT_ID,
                "X-Project-Id": "CUBI-REF-001",
                "X-Project-Revision": "1",
            },
        )
        assert status == 200, body[:300]
        assert len(json.loads(body)["activities"]) == 180


def test_reviewer_cannot_change_reference_source_data(runtime) -> None:
    session = _session(runtime, "reviewer")
    status, body = _request(
        runtime.app,
        "PATCH",
        "/api/projects/CUBI-REF-001",
        body=json.dumps({"name": "changed"}).encode(),
        cookie=session.session_id,
    )
    assert status == 403, body[:300]
    assert json.loads(body)["code"] == "AUTHORIZATION_PERMISSION_DENIED"


def test_shared_dataset_is_readable_but_not_writable_for_every_persona(runtime) -> None:
    for role in ("planner", "viewer", "newcomer"):
        ids = _project_ids(runtime, role)
        assert set(REFERENCE_PROJECTS) <= set(ids), (role, ids)

    session = _session(runtime, "planner")
    status, body = _request(
        runtime.app,
        "PATCH",
        "/api/projects/CUBI-REF-002",
        body=json.dumps({"name": "changed"}).encode(),
        cookie=session.session_id,
    )
    assert status == 403, body[:300]


def test_login_page_offers_reference_personas(tmp_path: Path) -> None:
    runtime = open_preview_runtime(
        tmp_path / "login.sqlite3",
        web_root=_web_root(tmp_path),
        reset=True,
    )
    try:
        app = build_preview_application(runtime)
        status, body = _request(app, "GET", "/preview/login")
        assert status == 200
        assert b'value="reviewer"' in body
        assert b'value="test_operator"' in body

        status, headers, _ = _request_with_headers(
            app,
            "POST",
            "/preview/login",
            body=b"role=reviewer&next=%2Fworkbench%2F",
            content_type="application/x-www-form-urlencoded",
        )
        assert status == 303
        cookie = next(
            value.split("=", 1)[1].split(";", 1)[0]
            for key, value in headers
            if key.lower() == "set-cookie"
        )

        status, body = _request(app, "GET", "/api/projects", cookie=cookie)
        assert status == 200
        ids = [item["project_id"] for item in json.loads(body)["projects"]]
        assert sorted(ids) == sorted(REFERENCE_PROJECTS)
    finally:
        runtime.close()


def _web_root(tmp_path: Path) -> Path:
    root = tmp_path / "web"
    source = root / "dist" / "web" / "src"
    source.mkdir(parents=True)
    (source / "landing-entry.js").write_text("export {};\n", encoding="utf-8")
    for name in ("app.html", "enterprise.html", "ai-workbench.html"):
        (root / name).write_text("<!doctype html><html><body></body></html>", encoding="utf-8")
    (root / "styles.css").write_text("body { margin: 0; }\n", encoding="utf-8")
    (root / "ai-workbench.css").write_text(".aiw-shell { min-height: 100vh; }\n", encoding="utf-8")
    return root
