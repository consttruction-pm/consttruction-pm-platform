"""Live PostgreSQL acceptance for the shared CUBI reference projects.

Three identities with different permissions (platform owner, planner, viewer)
must all see CUBI-REF-001/002/003 without per-user project memberships or copied
data; the same project ids and revisions must resolve everywhere; writes must
still follow server policy; and the data must survive a runtime restart because
it lives in PostgreSQL, not in a request-scoped fixture.

Run with::

    CONSTRUCTION_PM_POSTGRES_DSN=postgresql://... \
        PYTHONPATH=src python -m pytest -q \
        tests/integration/test_postgres_reference_projects_live.py
"""

from __future__ import annotations

import io
import json
import os
import uuid
from pathlib import Path
from urllib.parse import unquote

import pytest

from construction_pm.deployment.production_runtime import (
    ProductionRuntime,
    ProductionSettings,
)
from construction_pm.identity_session import (
    IdentityUser,
    PostgresIdentityStore,
    hash_password,
)
from construction_pm.importing.reference_persistence import (
    REFERENCE_ENGINE_VERSION,
    REFERENCE_RULES_VERSION,
)
from construction_pm.importing.reference_postgres import (
    ensure_reference_projects_postgres,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)

ORIGIN = "https://cubi.example.test"
SECRET = "reference-projects-session-secret-0123456789"
PASSWORDS = {
    "owner": "owner horse battery staple",
    "planner": "planner horse battery staple",
    "viewer": "viewer horse battery staple",
}
PROJECT_IDS = ("CUBI-REF-001", "CUBI-REF-002", "CUBI-REF-003")
WEB_ROOT = Path(__file__).resolve().parents[2] / "apps" / "web"


def _build_runtime(schema: str) -> ProductionRuntime:
    settings = ProductionSettings(
        database_url=os.environ["CONSTRUCTION_PM_POSTGRES_DSN"],
        session_secret=SECRET,
        public_origin=ORIGIN,
        secure_cookies=True,
        static_root=WEB_ROOT,
        max_pool_size=2,
        schema=schema,
    )
    runtime = ProductionRuntime(settings)
    runtime._initialize()
    return runtime


@pytest.fixture(scope="module")
def live():
    import psycopg

    suffix = uuid.uuid4().hex[:10]
    schema = f"cubi_ref_{suffix}"
    setup = psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"], autocommit=True)
    try:
        setup.execute(f'CREATE SCHEMA "{schema}"')
    finally:
        setup.close()

    tenant = f"tenant-ref-{suffix}"
    runtime = _build_runtime(schema)
    connection = runtime.pool.acquire()
    try:
        outcome = ensure_reference_projects_postgres(connection, tenant_id=tenant)
        users = {
            "owner": IdentityUser(
                user_id=f"user-owner-{suffix}",
                tenant_id=tenant,
                email=f"owner-{suffix}@example.test",
                display_name="Owner",
                roles=frozenset({"global_admin"}),
                password_hash=hash_password(PASSWORDS["owner"]),
            ),
            "planner": IdentityUser(
                user_id=f"user-planner-{suffix}",
                tenant_id=tenant,
                email=f"planner-{suffix}@example.test",
                display_name="Planner",
                roles=frozenset({"planner"}),
                password_hash=hash_password(PASSWORDS["planner"]),
            ),
            "viewer": IdentityUser(
                user_id=f"user-viewer-{suffix}",
                tenant_id=tenant,
                email=f"viewer-{suffix}@example.test",
                display_name="Viewer",
                roles=frozenset({"viewer"}),
                password_hash=hash_password(PASSWORDS["viewer"]),
            ),
        }
        store = PostgresIdentityStore(connection)
        for user in users.values():
            store.upsert_user(user)
        connection.commit()
    finally:
        runtime.pool.release(connection, healthy=True)

    runtime.test_ids = {  # type: ignore[attr-defined]
        "schema": schema,
        "tenant": tenant,
        "suffix": suffix,
        "users": users,
        "client_ip": f"2001:db8:ref::{suffix}",
        "outcome": outcome,
    }
    yield runtime
    runtime.close()
    teardown = psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"], autocommit=True)
    try:
        teardown.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
    finally:
        teardown.close()


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


def login(runtime, key: str) -> tuple[str, str]:
    user = runtime.test_ids["users"][key]
    status, headers, body = call(
        runtime,
        "POST",
        "/api/session",
        body={"email": user.email, "password": PASSWORDS[key]},
    )
    assert status == 200, body
    cookies = headers["set-cookie"]
    session = next(value for value in cookies if value.startswith("cp_session="))
    csrf = next(value for value in cookies if value.startswith("cubi_csrf="))
    return (
        session.split(";", 1)[0],
        unquote(csrf.split(";", 1)[0].split("=", 1)[1]),
    )


def list_projects(runtime, key: str) -> list[dict[str, object]]:
    cookie, _ = login(runtime, key)
    status, _, body = call(runtime, "GET", "/api/projects", cookie=cookie)
    assert status == 200, body
    return json.loads(body)["projects"]


def _sql(runtime, query: str, params: tuple[object, ...] = ()):
    connection = runtime.pool.acquire()
    try:
        return connection.execute(query, params).fetchall()
    finally:
        runtime.pool.release(connection, healthy=True)


# ---------------------------------------------------------------------------
# Shared visibility: no per-user membership or copied rows
# ---------------------------------------------------------------------------


def test_every_authenticated_role_sees_the_three_shared_projects(live):
    expected = set(PROJECT_IDS)
    for key in ("owner", "planner", "viewer"):
        projects = list_projects(live, key)
        assert {row["project_id"] for row in projects} == expected, key
        assert all(row["revision"] == 1 for row in projects)
        assert all(row["tenant_id"] == live.test_ids["tenant"] for row in projects)

    # Visibility comes from the shared registry, not duplicated memberships.
    rows = _sql(
        live,
        "SELECT count(*) FROM project_lifecycle_memberships "
        "WHERE tenant_id=%s AND project_id = ANY(%s)",
        (live.test_ids["tenant"], list(PROJECT_IDS)),
    )
    assert rows[0][0] == 0


def test_every_role_resolves_the_same_project_identity_and_name(live):
    seen: dict[str, tuple[str, int]] = {}
    for key in ("owner", "planner", "viewer"):
        cookie, _ = login(live, key)
        for project_id in PROJECT_IDS:
            status, _, body = call(
                live, "GET", f"/api/projects/{project_id}", cookie=cookie
            )
            assert status == 200, (key, project_id, body)
            project = json.loads(body)["project"]
            assert project["project_id"] == project_id
            seen.setdefault(project_id, (project["name"], project["revision"]))
            assert seen[project_id] == (project["name"], project["revision"])


# ---------------------------------------------------------------------------
# Isolation and durable domain counts
# ---------------------------------------------------------------------------


def test_project_data_is_scoped_by_project_without_cross_project_leakage(live):
    tenant = live.test_ids["tenant"]
    per_project = {
        project_id: _sql(
            live,
            "SELECT count(*) FROM activity_master WHERE tenant_id=%s AND project_id=%s",
            (tenant, project_id),
        )[0][0]
        for project_id in PROJECT_IDS
    }
    assert set(per_project.values()) == {180}
    total = _sql(
        live,
        "SELECT count(*) FROM activity_master WHERE tenant_id=%s",
        (tenant,),
    )[0][0]
    assert total == sum(per_project.values())

    # The WBS read for one project only returns nodes stored under that project.
    cookie, _ = login(live, "planner")
    status, _, body = call(
        live,
        "GET",
        "/api/projects/CUBI-REF-002/p6/wbs",
        cookie=cookie,
    )
    assert status == 200, body
    nodes = json.loads(body)["wbs_nodes"]
    expected_codes = {
        row[0]
        for row in _sql(
            live,
            "SELECT code FROM wbs_master WHERE tenant_id=%s AND project_id=%s",
            (tenant, "CUBI-REF-002"),
        )
    }
    assert {node["wbs"]["code"] for node in nodes} == expected_codes
    assert len(nodes) == len(expected_codes) == 129


def test_enterprise_registers_are_durable_and_complete_per_project(live):
    tenant = live.test_ids["tenant"]
    for table, per_project in (
        ("project_risk", 15),
        ("project_documents", 15),
        ("p6_issue", 8),
    ):
        counts = {
            project_id: _sql(
                live,
                f"SELECT count(*) FROM {table} WHERE tenant_id=%s AND project_id=%s",
                (tenant, project_id),
            )[0][0]
            for project_id in PROJECT_IDS
        }
        assert counts == {project_id: per_project for project_id in PROJECT_IDS}, table

    # Enterprise tasks are keyed by tenant/task id; the project lives in the
    # durable task payload, so the per-project page query reads the same rows.
    task_counts = {
        project_id: _sql(
            live,
            "SELECT count(*) FROM enterprise_tasks "
            "WHERE tenant_id=%s AND task_json::jsonb->>'project_id'=%s",
            (tenant, project_id),
        )[0][0]
        for project_id in PROJECT_IDS
    }
    assert task_counts == {project_id: 12 for project_id in PROJECT_IDS}

    # The frozen bundle's Enterprise registers are also queryable through the
    # durable workbench store (one row per kind/record).
    kinds = {
        row[0]: row[1]
        for row in _sql(
            live,
            "SELECT kind, count(*) FROM enterprise_records "
            "WHERE tenant_id=%s AND payload_json::jsonb->>'project_id'=%s "
            "GROUP BY kind",
            (tenant, "CUBI-REF-001"),
        )
    }
    assert kinds["contracts"] == 5
    assert kinds["milestones"] == 12
    assert kinds["procurement"] == 5
    assert kinds["teams"] == 8


def test_http_register_reads_are_served_from_the_durable_rows(live):
    tenant = live.test_ids["tenant"]
    cookie, _ = login(live, "planner")
    status, _, body = call(
        live, "GET", "/api/projects/CUBI-REF-001/risks", cookie=cookie
    )
    assert status == 200, body
    risks = json.loads(body)["risks"]
    stored_ids = {
        row[0]
        for row in _sql(
            live,
            "SELECT risk_id FROM project_risk WHERE tenant_id=%s AND project_id=%s",
            (tenant, "CUBI-REF-001"),
        )
    }
    assert len(risks) == 15
    assert {item["risk_id"] for item in risks} == stored_ids

    owner_cookie, _ = login(live, "owner")
    status, _, body = call(
        live,
        "GET",
        "/api/enterprise/tasks",
        query="project_id=CUBI-REF-001",
        cookie=owner_cookie,
    )
    assert status == 200, body
    tasks = json.loads(body)["tasks"]
    assert len(tasks) == 12
    assert all(task["project_id"] == "CUBI-REF-001" for task in tasks)


def test_calculated_values_come_from_the_canonical_engine_manifests(live):
    tenant = live.test_ids["tenant"]
    rows = _sql(
        live,
        "SELECT project_id, status, engine_version, output_hash, manifest_json "
        "FROM cubi_reference_schedule_run WHERE tenant_id=%s ORDER BY project_id",
        (tenant,),
    )
    assert [row[0] for row in rows] == list(PROJECT_IDS)
    contexts = {
        row[0]: row[1]
        for row in _sql(
            live,
            "SELECT project_id, rules_version FROM schedule_calculation_context "
            "WHERE tenant_id=%s",
            (tenant,),
        )
    }
    for project_id, status, engine_version, output_hash, manifest_json in rows:
        manifest = json.loads(manifest_json)
        assert status == "SUCCESS", project_id
        assert engine_version == REFERENCE_ENGINE_VERSION
        assert contexts[project_id] == REFERENCE_RULES_VERSION
        assert output_hash and len(output_hash) == 64
        assert manifest["project_revision"] == 1
        assert manifest["status"] == "SUCCESS"


# ---------------------------------------------------------------------------
# Authorization still follows server policy
# ---------------------------------------------------------------------------


def test_viewer_cannot_write_but_owner_can(live):
    cookie, csrf = login(live, "viewer")
    status, _, body = call(
        live,
        "POST",
        "/api/projects/CUBI-REF-001/p6/wbs",
        body={
            "wbs_id": "ref-qa-denied",
            "code": "QA-DENIED",
            "name": "Denied",
            "parent_kind": "project",
            "sequence_number": 99,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 403, body

    owner_cookie, owner_csrf = login(live, "owner")
    status, _, body = call(
        live,
        "GET",
        "/api/projects/CUBI-REF-001/p6/wbs",
        cookie=owner_cookie,
    )
    assert status == 200, body
    root = next(
        node
        for node in json.loads(body)["wbs_nodes"]
        if node["wbs"]["parent_kind"] == "project"
    )
    suffix = live.test_ids["suffix"]
    status, _, body = call(
        live,
        "POST",
        "/api/projects/CUBI-REF-001/p6/wbs",
        body={
            "wbs_id": f"owner-node-{suffix}",
            "code": f"OWNER-{suffix}",
            "name": "Owner verified write",
            "parent_kind": "wbs",
            "parent_wbs_id": root["wbs"]["wbs_id"],
            "sequence_number": 900,
        },
        cookie=owner_cookie,
        csrf=owner_csrf,
    )
    assert status == 201, body


# ---------------------------------------------------------------------------
# Durability across a restart
# ---------------------------------------------------------------------------


def test_data_survives_a_fresh_runtime_on_the_same_schema(live):
    schema = live.test_ids["schema"]
    tenant = live.test_ids["tenant"]
    before = _sql(
        live,
        "SELECT count(*) FROM activity_master WHERE tenant_id=%s",
        (tenant,),
    )[0][0]

    # A second runtime re-runs the additive migrations, rebuilds every pool and
    # adapter, and must read the same rows: the data is not request-scoped.
    restarted = _build_runtime(schema)
    try:
        restarted.test_ids = dict(live.test_ids)  # type: ignore[attr-defined]
        for key in ("owner", "planner", "viewer"):
            projects = list_projects(restarted, key)
            assert {row["project_id"] for row in projects} == set(PROJECT_IDS), key
        after = _sql(
            restarted,
            "SELECT count(*) FROM activity_master WHERE tenant_id=%s",
            (tenant,),
        )[0][0]
        assert after == before == 540
        manifests = _sql(
            restarted,
            "SELECT count(*) FROM cubi_reference_import WHERE tenant_id=%s",
            (tenant,),
        )[0][0]
        assert manifests == 3
    finally:
        restarted.close()


def test_reimport_rebuilds_a_project_whose_lifecycle_row_was_lost(live):
    """A partial import recovers: child rows are cleared in FK order and rewritten."""

    tenant = live.test_ids["tenant"]
    connection = live.pool.acquire()
    try:
        connection.execute(
            "DELETE FROM project_lifecycle_projects WHERE tenant_id=%s AND project_id=%s",
            (tenant, "CUBI-REF-003"),
        )
        connection.commit()
    finally:
        live.pool.release(connection, healthy=True)

    connection = live.pool.acquire()
    try:
        outcome = ensure_reference_projects_postgres(connection, tenant_id=tenant)
    finally:
        live.pool.release(connection, healthy=True)

    assert [project.project_id for project in outcome.projects] == ["CUBI-REF-003"]
    for table, expected in (
        ("activity_master", 180),
        ("wbs_master", 145),
        ("project_risk", 15),
        ("project_documents", 15),
        ("p6_issue", 8),
    ):
        total = _sql(
            live,
            f"SELECT count(*) FROM {table} WHERE tenant_id=%s AND project_id=%s",
            (tenant, "CUBI-REF-003"),
        )[0][0]
        assert total == expected, table
    imports = _sql(
        live,
        "SELECT count(*) FROM cubi_reference_import WHERE tenant_id=%s",
        (tenant,),
    )[0][0]
    assert imports == 3


def test_production_boot_seeds_the_reference_tenant_from_environment(monkeypatch):
    """`CUBI_REFERENCE_TENANT` makes the real runtime register the bundle."""

    import psycopg

    suffix = uuid.uuid4().hex[:10]
    schema = f"cubi_refboot_{suffix}"
    tenant = f"tenant-refboot-{suffix}"
    setup = psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"], autocommit=True)
    try:
        setup.execute(f'CREATE SCHEMA "{schema}"')
    finally:
        setup.close()

    monkeypatch.setenv("CUBI_REFERENCE_TENANT", tenant)
    runtime = _build_runtime(schema)
    try:
        counts = _sql(
            runtime,
            "SELECT project_id, count(*) FROM activity_master "
            "WHERE tenant_id=%s GROUP BY project_id ORDER BY project_id",
            (tenant,),
        )
        assert counts == [(project_id, 180) for project_id in PROJECT_IDS]
        manifests = _sql(
            runtime,
            "SELECT project_id, status FROM cubi_reference_import "
            "WHERE tenant_id=%s ORDER BY project_id",
            (tenant,),
        )
        assert manifests == [(project_id, "COMPLETE") for project_id in PROJECT_IDS]
    finally:
        runtime.close()

    # A second boot on the same schema re-registers nothing: the import stays
    # idempotent under the boot hook as well.
    second = _build_runtime(schema)
    try:
        total = _sql(
            second,
            "SELECT count(*) FROM activity_master WHERE tenant_id=%s",
            (tenant,),
        )[0][0]
        assert total == 540
        imports = _sql(
            second,
            "SELECT count(*) FROM cubi_reference_import WHERE tenant_id=%s",
            (tenant,),
        )[0][0]
        assert imports == 3
    finally:
        second.close()
        teardown = psycopg.connect(
            os.environ["CONSTRUCTION_PM_POSTGRES_DSN"], autocommit=True
        )
        try:
            teardown.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        finally:
            teardown.close()
