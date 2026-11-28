"""Live PostgreSQL acceptance for the operational CUBI production runtime.

Every test in this module runs against a real PostgreSQL database and the same
WSGI application that ``api/index.py`` exposes on Vercel. The runtime is bound
to a throw-away schema so the module can prove the full chain (migration ledger,
identity, project lifecycle, WBS/activities, risks, forms, knowledge and the AI
action runtime) without disturbing another test's schema.

Run with::

    CONSTRUCTION_PM_POSTGRES_DSN=postgresql://... \
        PYTHONPATH=src python -m pytest -q \
        tests/integration/test_cubi_database_operationalization_postgres_live.py

No test here asserts against SQLite, preview-only adapters or demo identities.
"""

from __future__ import annotations

import io
import json
import os
import uuid
from pathlib import Path
from urllib.parse import unquote

import pytest

from construction_pm.deployment.migrations import (
    LEDGER_TABLE,
    MigrationError,
    apply_migrations,
)
from construction_pm.deployment.production_runtime import (
    ProductionRuntime,
    ProductionSettings,
)
from construction_pm.identity_session import (
    IdentityUser,
    PostgresIdentityStore,
    hash_password,
)

# The main CI workflow sets P6_TEST_POSTGRES_DSN; accept it so this module runs
# there as well as in the dedicated PostgreSQL workflow.
if not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN") and os.getenv("P6_TEST_POSTGRES_DSN"):
    os.environ["CONSTRUCTION_PM_POSTGRES_DSN"] = os.environ["P6_TEST_POSTGRES_DSN"]

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)

ORIGIN = "https://cubi.example.test"
SECRET = "operationalization-session-secret-0123456789"
ADMIN_PASSWORD = "admin horse battery staple"
PLANNER_PASSWORD = "planner horse battery staple"
VIEWER_PASSWORD = "viewer horse battery staple"
WEB_ROOT = Path(__file__).resolve().parents[2] / "apps" / "web"
ORG_LIBRARY = "/api/forms/organization"
STARTER_TEMPLATE = "contractor-daily-site-report"
SCHEDULING_WORKER_TOKEN = "operationalization-worker-token-0123456789"


def _schema_name(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _apply_drift_free_schema(schema: str):
    """Create a schema and run the production registry in it."""

    import psycopg

    connection = psycopg.connect(
        os.environ["CONSTRUCTION_PM_POSTGRES_DSN"],
        autocommit=True,
        options=f"-c search_path={schema}",
    )
    try:
        connection.execute(f'CREATE SCHEMA "{schema}"')
        report = apply_migrations(connection)
        return connection, report
    except BaseException:
        connection.close()
        raise


@pytest.fixture(scope="module")
def runtime() -> ProductionRuntime:
    schema = _schema_name("cubi_op")
    import psycopg

    setup = psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"], autocommit=True)
    try:
        setup.execute(f'CREATE SCHEMA "{schema}"')
    finally:
        setup.close()

    settings = ProductionSettings(
        database_url=os.environ["CONSTRUCTION_PM_POSTGRES_DSN"],
        session_secret=SECRET,
        public_origin=ORIGIN,
        secure_cookies=True,
        static_root=WEB_ROOT,
        max_pool_size=2,
        schema=schema,
        scheduling_worker_token=SCHEDULING_WORKER_TOKEN,
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
            roles=frozenset({"project_admin", "enterprise_admin"}),
            password_hash=hash_password(ADMIN_PASSWORD),
        ),
        "planner": IdentityUser(
            user_id=f"user-planner-{suffix}",
            tenant_id=tenant_a,
            email=f"planner-{suffix}@example.test",
            display_name="Planner",
            roles=frozenset({"planner", "enterprise_user"}),
            password_hash=hash_password(PLANNER_PASSWORD),
        ),
        "viewer": IdentityUser(
            user_id=f"user-viewer-{suffix}",
            tenant_id=tenant_a,
            email=f"viewer-{suffix}@example.test",
            display_name="Viewer",
            roles=frozenset({"viewer", "enterprise_viewer"}),
            password_hash=hash_password(VIEWER_PASSWORD),
        ),
        "outsider": IdentityUser(
            user_id=f"user-outsider-{suffix}",
            tenant_id=tenant_b,
            email=f"outsider-{suffix}@example.test",
            display_name="Outsider",
            roles=frozenset({"project_admin", "enterprise_admin"}),
            password_hash=hash_password(ADMIN_PASSWORD),
        ),
    }
    connection = instance.pool.acquire()
    try:
        store = PostgresIdentityStore(connection)
        for user in users.values():
            store.upsert_user(user)
        for tenant, project, name in (
            (tenant_a, project_a, "Operational Project"),
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
        "schema": schema,
        "users": users,
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "project_a": project_a,
        "project_b": project_b,
        "client_ip": f"2001:db8::{suffix}",
        "suffix": suffix,
    }

    # Create the single project-root WBS through the real HTTP surface. Later
    # tests add child nodes, because P6 permits exactly one root per project.
    planner_cookie, planner_csrf = login(instance, "planner", PLANNER_PASSWORD)
    root_wbs = f"root-{suffix}"
    status, _, body = call(
        instance,
        "POST",
        f"/api/projects/{project_a}/p6/wbs",
        body={
            "wbs_id": root_wbs,
            "code": f"1-{suffix}",
            "name": "Project summary",
            "parent_kind": "project",
            "sequence_number": 1,
        },
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 201, body
    instance.test_ids["root_wbs"] = root_wbs  # type: ignore[index]
    yield instance
    instance.close()
    teardown = psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"], autocommit=True)
    try:
        teardown.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
    finally:
        teardown.close()


def call(
    runtime,
    method,
    path,
    *,
    body=None,
    cookie="",
    csrf="",
    query="",
    headers=None,
):
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


def login(runtime, key: str, password: str) -> tuple[str, str]:
    user = runtime.test_ids["users"][key]
    status, headers, body = call(
        runtime, "POST", "/api/session", body={"email": user.email, "password": password}
    )
    assert status == 200, body
    cookies = headers["set-cookie"]
    session = next(value for value in cookies if value.startswith("cp_session="))
    csrf = next(value for value in cookies if value.startswith("cubi_csrf="))
    return (
        session.split(";", 1)[0],
        unquote(csrf.split(";", 1)[0].split("=", 1)[1]),
    )


def _details(runtime, cookie, project_id=None):
    ids = runtime.test_ids
    return {
        "X-Tenant-Id": ids["tenant_a"],
        "X-Project-Id": project_id or ids["project_a"],
        "X-Project-Revision": "0",
    }


# ---------------------------------------------------------------------------
# P0-B: versioned migration ledger and drift detection
# ---------------------------------------------------------------------------


def test_migration_ledger_is_versioned_idempotent_and_reports_drift():
    schema = _schema_name("cubi_mig")
    connection, first = _apply_drift_free_schema(schema)
    try:
        assert first.ledger_version == 23
        assert len(first.applied) == 23
        assert first.already_applied == ()
        assert first.table_count == 111
        assert first.drift is None

        second = apply_migrations(connection)
        assert second.applied == ()
        assert second.already_applied == tuple(range(1, 24))
        assert second.drift is None
        assert second.table_count == 111

        rows = connection.execute(
            f"SELECT version, name, checksum, step_revision, runtime_version "
            f"FROM {LEDGER_TABLE} ORDER BY version"
        ).fetchall()
        assert [row[0] for row in rows] == list(range(1, 24))
        assert all(row[2] and row[3] >= 1 and row[4] == 23 for row in rows)

        # An edited history is reported, never silently accepted.
        connection.execute(
            f"UPDATE {LEDGER_TABLE} SET checksum='tampered' WHERE version=1"
        )
        tampered = apply_migrations(connection)
        assert tampered.drift is not None
        assert tampered.drift["checksum"]

        # A database ahead of the code fails closed.
        connection.execute(
            f"INSERT INTO {LEDGER_TABLE} "
            "(version, name, checksum, step_revision, duration_ms, runtime_version) "
            "VALUES (999, 'future', 'x', 1, 0, 999)"
        )
        with pytest.raises(MigrationError) as unknown:
            apply_migrations(connection)
        assert unknown.value.code == "MIGRATION_HISTORY_UNKNOWN"
    finally:
        connection.execute(f'DROP SCHEMA "{schema}" CASCADE')
        connection.close()


def test_structural_drift_can_fail_closed():
    schema = _schema_name("cubi_drift")
    connection, _ = _apply_drift_free_schema(schema)
    try:
        connection.execute(
            "ALTER TABLE project_risk ADD COLUMN shadow_column TEXT"
        )
        reported = apply_migrations(connection)
        assert reported.drift is not None
        assert "structure" in reported.drift["structural"]
        with pytest.raises(MigrationError) as excinfo:
            apply_migrations(connection, drift_policy="fail")
        assert excinfo.value.code == "SCHEMA_DRIFT_DETECTED"
    finally:
        connection.execute(f'DROP SCHEMA "{schema}" CASCADE')
        connection.close()


def test_runtime_readiness_uses_the_migrated_schema(runtime):
    status, _, body = call(runtime, "GET", "/api/health/live")
    assert status == 200
    assert json.loads(body)["status"] == "ok"

    status, _, body = call(runtime, "GET", "/api/health/ready")
    assert status == 200
    readiness = json.loads(body)
    assert readiness["status"] == "ready"
    assert readiness["schema"]["version"] == 23
    assert readiness["schema"]["tables"] == 111


# ---------------------------------------------------------------------------
# P0-C/P0-E: identity, project, WBS/activity save and restore
# ---------------------------------------------------------------------------


def test_project_wbs_activity_save_survives_logout_and_new_session(runtime):
    ids = runtime.test_ids
    project = ids["project_a"]
    suffix = uuid.uuid4().hex[:8]
    cookie, csrf = login(runtime, "planner", PLANNER_PASSWORD)

    status, _, body = call(runtime, "GET", "/api/session", cookie=cookie)
    assert status == 200
    assert json.loads(body)["user_id"] == ids["users"]["planner"].user_id

    status, _, body = call(
        runtime, "POST", f"/api/projects/{project}/open", cookie=cookie, csrf=csrf
    )
    assert status == 200, body

    wbs_id = f"wbs-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/wbs",
        body={
            "wbs_id": wbs_id,
            "code": f"1.1-{suffix}",
            "name": "Site works",
            "parent_kind": "wbs",
            "parent_wbs_id": ids["root_wbs"],
            "sequence_number": 1,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body

    activity_id = f"act-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/activities",
        body={
            "activity_id": activity_id,
            "name": "Pour concrete",
            "duration_value": 5,
            "duration_unit": "working-day",
            "wbs_id": wbs_id,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body
    assert json.loads(body)["activity"]["activity_id"] == activity_id

    status, _, body = call(
        runtime,
        "GET",
        "/api/v2/workspace/control-room/read",
        cookie=cookie,
        headers=_details(runtime, cookie),
    )
    assert status == 200, body
    workspace = json.loads(body)
    assert workspace["contract_version"] == "workspace-control-room-read.v2"

    status, _, _ = call(runtime, "DELETE", "/api/session", cookie=cookie, csrf=csrf)
    assert status == 204

    status, _, body = call(runtime, "GET", "/api/session", cookie=cookie)
    assert status == 401
    assert json.loads(body)["code"] in {"SESSION_NOT_FOUND", "SESSION_REQUIRED"}

    # A brand-new login (new cookie) reads the same durable activity.
    cookie_two, _ = login(runtime, "planner", PLANNER_PASSWORD)
    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/p6/activities/{activity_id}",
        cookie=cookie_two,
    )
    assert status == 200, body
    activity = json.loads(body)["activity"]
    assert activity["name"] == "Pour concrete"
    assert activity["wbs_id"] == wbs_id


def test_optimistic_locking_conflict_is_reported(runtime):
    ids = runtime.test_ids
    project = ids["project_a"]
    suffix = uuid.uuid4().hex[:8]
    cookie, csrf = login(runtime, "planner", PLANNER_PASSWORD)
    call(runtime, "POST", f"/api/projects/{project}/open", cookie=cookie, csrf=csrf)

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/wbs",
        body={
            "wbs_id": f"wbs2-{suffix}",
            "code": f"1.2-{suffix}",
            "name": "Second front",
            "parent_kind": "wbs",
            "parent_wbs_id": ids["root_wbs"],
            "sequence_number": 2,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body

    activity_id = f"act2-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/activities",
        body={
            "activity_id": activity_id,
            "name": "Rebar",
            "duration_value": 3,
            "duration_unit": "working-day",
            "wbs_id": f"wbs2-{suffix}",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body

    status, _, body = call(
        runtime,
        "PATCH",
        f"/api/projects/{project}/p6/activities/{activity_id}",
        body={"name": "Rebar fixed", "expected_revision": 1},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body

    status, _, body = call(
        runtime,
        "PATCH",
        f"/api/projects/{project}/p6/activities/{activity_id}",
        body={"name": "Stale edit", "expected_revision": 1},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "REVISION_CONFLICT"


# ---------------------------------------------------------------------------
# P0-E: risks
# ---------------------------------------------------------------------------


def test_risk_create_read_update_and_idempotent_replay(runtime):
    ids = runtime.test_ids
    project = ids["project_a"]
    suffix = uuid.uuid4().hex[:8]
    cookie, csrf = login(runtime, "admin", ADMIN_PASSWORD)
    call(runtime, "POST", f"/api/projects/{project}/open", cookie=cookie, csrf=csrf)

    risk_id = f"risk-{suffix}"
    payload = {
        "risk_id": risk_id,
        "title": "Late steel delivery",
        "category": "schedule",
        "probability": 4,
        "impact": 5,
        "response_strategy": "mitigate",
        "owner": "procurement",
        "date_identified": "2026-11-01",
        "idempotency_key": f"idem-{suffix}",
    }
    status, _, body = call(
        runtime, "POST", f"/api/projects/{project}/risks", body=payload,
        cookie=cookie, csrf=csrf,
    )
    assert status == 200, body
    created = json.loads(body)
    assert created["score"] == 20 and created["exposure_level"] == "critical"

    status, _, body = call(
        runtime, "POST", f"/api/projects/{project}/risks", body=payload,
        cookie=cookie, csrf=csrf,
    )
    assert status == 200, body
    assert json.loads(body)["revision"] == created["revision"]

    status, _, body = call(
        runtime, "GET", f"/api/projects/{project}/risks?category=schedule", cookie=cookie
    )
    assert status == 200
    listed = json.loads(body)["risks"]
    assert any(item["risk_id"] == risk_id for item in listed)

    status, _, body = call(
        runtime,
        "PATCH",
        f"/api/projects/{project}/risks/{risk_id}",
        body={
            **payload,
            "title": "Late steel delivery (escalated)",
            "expected_revision": 1,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    assert json.loads(body)["revision"] == 2

    status, _, body = call(
        runtime, "GET", f"/api/projects/{project}/risks/{risk_id}/history", cookie=cookie
    )
    assert status == 200, body
    history = json.loads(body)
    assert len(history["events"]) >= 2
    assert {event["event_type"] for event in history["events"]} >= {
        "created",
        "updated",
    }


# ---------------------------------------------------------------------------
# P0-F: forms library, submission and approval history
# ---------------------------------------------------------------------------


def _sample_values(template: dict) -> dict:
    values = {}
    for field in template.get("fields", []):
        kind = field.get("type")
        if kind in {"number", "integer", "quantity", "currency"}:
            values[field["field_id"]] = 10
        elif kind == "percent":
            values[field["field_id"]] = 0.5
        elif kind == "date":
            values[field["field_id"]] = "2026-11-20"
        elif kind == "select":
            options = field.get("options") or []
            values[field["field_id"]] = options[0]["option_id"] if options else "n/a"
        elif kind == "boolean":
            values[field["field_id"]] = True
        elif kind in {"file", "formula", "engine"}:
            continue
        else:
            values[field["field_id"]] = "Operational value"
    values.update(
        {
            "workforce": 12,
            "hours_worked": 8.5,
            "planned_qty": 200,
            "completed_qty": 150,
            "planned_work": "Concrete pour",
            "completed_work": "Concrete poured",
        }
    )
    return values


def test_forms_template_submission_and_approval_are_durable(runtime):
    ids = runtime.test_ids
    project = ids["project_a"]
    suffix = uuid.uuid4().hex[:8]
    admin_cookie, admin_csrf = login(runtime, "admin", ADMIN_PASSWORD)
    planner_cookie, planner_csrf = login(runtime, "planner", PLANNER_PASSWORD)

    status, _, body = call(
        runtime, "POST", f"{ORG_LIBRARY}/seed", body={}, cookie=admin_cookie,
        csrf=admin_csrf,
    )
    assert status == 200, body
    assert json.loads(body)["seeded"] >= 10

    template_id = f"daily-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"{ORG_LIBRARY}/templates/{STARTER_TEMPLATE}/copy",
        body={
            "target_library": "project",
            "target_project_id": project,
            "new_template_id": template_id,
            "publish": True,
        },
        cookie=admin_cookie,
        csrf=admin_csrf,
    )
    assert status in {200, 201}, body
    published = json.loads(body)
    assert published["status"] == "published"
    assert published["published_version"] == 1

    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/forms/templates/{template_id}/versions/1",
        cookie=admin_cookie,
    )
    assert status == 200, body
    template_payload = json.loads(body)["payload"]

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/forms/submissions",
        body={
            "template_id": template_id,
            "template_version": 1,
            "library": "project",
            "values": _sample_values(template_payload),
            "tables": {
                "work_items": [
                    {
                        "item": "Concrete",
                        "unit": "m3",
                        "planned_qty": 100,
                        "actual_qty": 80,
                        "remarks": "ok",
                    }
                ]
            },
            "report_date": "2026-11-20",
            "title": "Daily site report",
        },
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 200, body
    submission = json.loads(body)
    submission_id = submission["submission_id"]
    assert submission["status"] == "draft"
    assert submission["author"] == ids["users"]["planner"].user_id

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/forms/submissions/{submission_id}/transition",
        body={
            "action": "submit",
            "expected_revision": submission["record_revision"],
        },
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 200, body
    after_submit = json.loads(body)
    assert after_submit["status"] == "submitted"

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/forms/submissions/{submission_id}/transition",
        body={
            "action": "start_review",
            "expected_revision": after_submit["record_revision"],
        },
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 200, body
    under_review = json.loads(body)
    assert under_review["status"] == "under_review"

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/forms/submissions/{submission_id}/transition",
        body={
            "action": "approve",
            "expected_revision": under_review["record_revision"],
        },
        cookie=admin_cookie,
        csrf=admin_csrf,
    )
    assert status == 200, body
    assert json.loads(body)["status"] == "approved"

    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/forms/submissions/{submission_id}/revisions",
        cookie=admin_cookie,
    )
    assert status == 200, body
    history = json.loads(body)
    assert [revision["event_type"] for revision in history["revisions"]][:1] == ["created"]
    assert any(
        approval["action"] == "approve" for approval in history["approvals"]
    )

    # A fresh session still reads the approved submission and its version pin.
    later_cookie, _ = login(runtime, "admin", ADMIN_PASSWORD)
    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/forms/submissions/{submission_id}",
        cookie=later_cookie,
    )
    assert status == 200, body
    restored = json.loads(body)
    assert restored["status"] == "approved"
    assert restored["template_version"] == 1


def test_missing_required_form_values_are_rejected(runtime):
    ids = runtime.test_ids
    project = ids["project_a"]
    suffix = uuid.uuid4().hex[:8]
    cookie, csrf = login(runtime, "admin", ADMIN_PASSWORD)
    call(runtime, "POST", f"{ORG_LIBRARY}/seed", body={}, cookie=cookie, csrf=csrf)

    template_id = f"daily-missing-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"{ORG_LIBRARY}/templates/{STARTER_TEMPLATE}/copy",
        body={
            "target_library": "project",
            "target_project_id": project,
            "new_template_id": template_id,
            "publish": True,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/forms/submissions",
        body={
            "template_id": template_id,
            "template_version": 1,
            "library": "project",
            "values": {},
            "tables": {},
            "report_date": "2026-11-20",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    submission = json.loads(body)

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/forms/submissions/{submission['submission_id']}/transition",
        body={
            "action": "submit",
            "expected_revision": submission["record_revision"],
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    validation = json.loads(body)
    assert validation["valid"] is False
    assert validation["issues"]


# ---------------------------------------------------------------------------
# P0-G: AI action proposal/approval/execution on the real project
# ---------------------------------------------------------------------------


def test_ai_action_proposal_is_human_approved_before_any_mutation(runtime):
    ids = runtime.test_ids
    project = ids["project_a"]
    suffix = uuid.uuid4().hex[:8]
    cookie, csrf = login(runtime, "admin", ADMIN_PASSWORD)
    call(runtime, "POST", f"/api/projects/{project}/open", cookie=cookie, csrf=csrf)

    wbs_id = f"ai-wbs-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/wbs",
        body={
            "wbs_id": wbs_id,
            "code": f"1.3-{suffix}",
            "name": "AI front",
            "parent_kind": "wbs",
            "parent_wbs_id": ids["root_wbs"],
            "sequence_number": 3,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body

    activity_id = f"ai-act-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/ai/actions/proposals",
        body={
            "expected_revision": 0,
            "tool_name": "activity.create",
            "payload": {
                "activity_id": activity_id,
                "name": "Excavate",
                "duration_value": 4,
                "duration_unit": "working-day",
                "wbs_id": wbs_id,
            },
            "evidence_refs": [wbs_id],
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body
    proposal = json.loads(body)
    proposal_id = proposal["proposal"]["proposal_id"]
    assert proposal["status"] == "proposed"
    assert proposal["proposal"]["requires_human_approval"] is True

    # Nothing has been written before approval.
    status, _, _ = call(
        runtime, "GET", f"/api/projects/{project}/p6/activities/{activity_id}", cookie=cookie
    )
    assert status == 404

    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/ai/actions/proposals",
        cookie=cookie,
    )
    assert status == 200
    assert any(
        item["proposal_id"] == proposal_id for item in json.loads(body)["proposals"]
    )

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/ai/actions/proposals/{proposal_id}/decision",
        body={"expected_revision": 0, "approved": True},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    assert json.loads(body)["status"] == "approved"

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/ai/actions/proposals/{proposal_id}/execute",
        body={"expected_revision": 0},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    execution = json.loads(body)
    assert execution["status"] == "executed"

    status, _, body = call(
        runtime, "GET", f"/api/projects/{project}/p6/activities/{activity_id}", cookie=cookie
    )
    assert status == 200, body
    assert json.loads(body)["activity"]["name"] == "Excavate"

    # A duplicate execution is rejected without a second mutation.
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/ai/actions/proposals/{proposal_id}/execute",
        body={"expected_revision": 0},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "AI_ACTION_PROPOSAL_NOT_APPROVED"

    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/ai/actions/proposals/{proposal_id}",
        cookie=cookie,
    )
    assert status == 200
    assert json.loads(body)["proposal"]["status"] == "executed"


def test_ai_proposal_rejects_stale_revision_and_viewer(runtime):
    ids = runtime.test_ids
    project = ids["project_a"]
    cookie, csrf = login(runtime, "admin", ADMIN_PASSWORD)

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/ai/actions/proposals",
        body={
            "expected_revision": 1,
            "tool_name": "activity.create",
            "payload": {"activity_id": "stale", "name": "x"},
            "evidence_refs": [],
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "AI_ACTION_PROPOSAL_STALE_REVISION"

    viewer_cookie, viewer_csrf = login(runtime, "viewer", VIEWER_PASSWORD)
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/ai/actions/proposals",
        body={
            "expected_revision": 0,
            "tool_name": "activity.create",
            "payload": {"activity_id": "denied", "name": "x"},
            "evidence_refs": [],
        },
        cookie=viewer_cookie,
        csrf=viewer_csrf,
    )
    assert status == 403, body


# ---------------------------------------------------------------------------
# P0-H: tenant isolation, permissions and CSRF
# ---------------------------------------------------------------------------


def test_tenant_isolation_and_viewer_write_denial(runtime):
    ids = runtime.test_ids
    project = ids["project_a"]

    outsider_cookie, outsider_csrf = login(runtime, "outsider", ADMIN_PASSWORD)
    status, _, body = call(runtime, "GET", "/api/projects", cookie=outsider_cookie)
    assert status == 200
    assert [item["project_id"] for item in json.loads(body)["projects"]] == [
        ids["project_b"]
    ]

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/open",
        cookie=outsider_cookie,
        csrf=outsider_csrf,
    )
    assert status == 403, body

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/risks",
        body={
            "risk_id": "cross-tenant",
            "title": "x",
            "category": "schedule",
            "probability": 1,
            "impact": 1,
            "response_strategy": "avoid",
            "owner": "x",
            "date_identified": "2026-11-01",
        },
        cookie=outsider_cookie,
        csrf=outsider_csrf,
    )
    assert status == 403, body

    viewer_cookie, viewer_csrf = login(runtime, "viewer", VIEWER_PASSWORD)
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/risks",
        body={
            "risk_id": "viewer-risk",
            "title": "x",
            "category": "schedule",
            "probability": 1,
            "impact": 1,
            "response_strategy": "avoid",
            "owner": "x",
            "date_identified": "2026-11-01",
        },
        cookie=viewer_cookie,
        csrf=viewer_csrf,
    )
    assert status == 403, body

    status, _, body = call(
        runtime,
        "GET",
        "/api/v2/workspace/control-room/read",
        cookie=viewer_cookie,
        headers={
            "X-Tenant-Id": ids["tenant_b"],
            "X-Project-Id": project,
            "X-Project-Revision": "0",
        },
    )
    assert status == 403
    assert json.loads(body)["code"] == "CROSS_SCOPE_ACCESS"

    # Missing CSRF on a write is rejected before any repository call.
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/open",
        cookie=viewer_cookie,
    )
    assert status == 403
    assert json.loads(body)["code"] == "CSRF_TOKEN_INVALID"


# ---------------------------------------------------------------------------
# Knowledge is durable and honest about missing coverage
# ---------------------------------------------------------------------------


def test_knowledge_survives_and_reports_missing_coverage(runtime):
    ids = runtime.test_ids
    project = ids["project_a"]
    planner_cookie, planner_csrf = login(runtime, "planner", PLANNER_PASSWORD)

    status, _, body = call(runtime, "GET", "/api/knowledge/locales", cookie=planner_cookie)
    assert status == 200
    assert "locales" in json.loads(body)

    status, _, body = call(runtime, "GET", "/api/knowledge/coverage", cookie=planner_cookie)
    assert status == 200
    coverage = json.loads(body)
    assert coverage["contract_version"] == "cubi-knowledge-coverage.v1"
    assert coverage["sources"]
    assert all(source["counts"]["total"] == 0 for source in coverage["sources"])

    status, _, body = call(
        runtime, "GET", "/api/knowledge/search", query="q=schedule", cookie=planner_cookie
    )
    assert status == 200
    search = json.loads(body)
    assert search["insufficient_knowledge"] is True
    assert search["hits"] == []

    title = f"Site rule {uuid.uuid4().hex[:6]}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/knowledge",
        body={
            "title": title,
            "kind": "note",
            "content": "Concrete pours require a curing record.",
        },
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 201, body

    status, _, body = call(
        runtime, "GET", f"/api/projects/{project}/knowledge", cookie=planner_cookie
    )
    assert status == 200
    listing = json.loads(body)
    assert any(entry.get("title") == title for entry in listing["entries"])



def test_username_signup_is_durable_and_duplicate_recovery_keeps_postgres_usable(runtime):
    suffix = runtime.test_ids["suffix"]
    username = f"signup-{suffix}"
    status, headers, body = call(
        runtime, "POST", "/api/signup",
        body={"username": username, "password": "signup password battery staple"},
    )
    assert status == 201, body
    created = json.loads(body)
    assert created["roles"] == ["viewer"]
    session_cookie = next(
        value.split(";", 1)[0] for value in headers["set-cookie"]
        if value.startswith("cp_session=")
    )
    status, _, body = call(runtime, "GET", "/api/session", cookie=session_cookie)
    assert status == 200
    assert json.loads(body)["user_id"] == created["user_id"]

    status, _, body = call(
        runtime, "POST", "/api/signup",
        body={"username": username.upper(), "password": "signup password battery staple"},
    )
    assert status == 409
    assert json.loads(body)["code"] == "USERNAME_TAKEN"

    status, _, body = call(
        runtime, "POST", "/api/signup",
        body={"username": f"signup-next-{suffix}", "password": "signup password battery staple"},
    )
    assert status == 201, body



# ---------------------------------------------------------------------------
# P0-E: threshold register end-to-end over the production PostgreSQL runtime
# ---------------------------------------------------------------------------


def _threshold_payload(threshold_id: str, **overrides):
    payload = {
        "threshold_id": threshold_id,
        "name": "Open issue ceiling",
        "monitoring_subject": "quality",
        "parameter": "open_issue_count",
        "currency": None,
        "lower_threshold": None,
        "upper_threshold": "4",
        "warning_level": "2",
        "issue_level": "3",
        "responsible_manager": "Planner",
        "status": "active",
    }
    payload.update(overrides)
    return payload


def _db_rows(runtime, statement: str, params: tuple = ()):
    import psycopg

    connection = psycopg.connect(
        os.environ["CONSTRUCTION_PM_POSTGRES_DSN"],
        autocommit=True,
        options=f"-c search_path={runtime.test_ids['schema']}",
    )
    try:
        return connection.execute(statement, params).fetchall()
    finally:
        connection.close()


def test_threshold_register_end_to_end_over_postgres(runtime):
    ids = runtime.test_ids
    project = ids["project_a"]
    base = f"/api/projects/{project}/thresholds"
    planner_cookie, planner_csrf = login(runtime, "planner", PLANNER_PASSWORD)
    viewer_cookie, viewer_csrf = login(runtime, "viewer", VIEWER_PASSWORD)
    outsider_cookie, outsider_csrf = login(runtime, "outsider", ADMIN_PASSWORD)
    threshold_id = f"TH-E2E-{ids['suffix']}"

    # 1. The register starts empty for this project.
    status, _, body = call(runtime, "GET", base, cookie=planner_cookie)
    assert status == 200, body
    assert json.loads(body)["thresholds"] == []

    # 2. Create, persisted through the production composition.
    status, _, body = call(
        runtime,
        "POST",
        base,
        body=_threshold_payload(threshold_id),
        cookie=planner_cookie,
        csrf=planner_csrf,
        headers={"Idempotency-Key": f"idem-{threshold_id}"},
    )
    assert status == 200, body
    created = json.loads(body)
    assert created["revision"] == 1 and created["upper_threshold"] == "4"

    # 3. Reload in a new request: the row is a real PostgreSQL record.
    status, _, body = call(runtime, "GET", f"{base}/{threshold_id}", cookie=planner_cookie)
    assert status == 200, body
    assert json.loads(body)["revision"] == 1
    stored = _db_rows(
        runtime,
        "SELECT revision, threshold_json FROM project_threshold "
        "WHERE tenant_id=%s AND project_id=%s AND threshold_id=%s",
        (ids["tenant_a"], project, threshold_id),
    )
    assert len(stored) == 1 and stored[0][0] == 1

    # 4. Edit with expected_revision, then verify the new revision.
    status, _, body = call(
        runtime,
        "PATCH",
        f"{base}/{threshold_id}",
        body=_threshold_payload(threshold_id, upper_threshold="9", expected_revision=1),
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 200, body
    assert json.loads(body)["revision"] == 2
    status, _, body = call(runtime, "GET", f"{base}/{threshold_id}", cookie=planner_cookie)
    assert json.loads(body)["revision"] == 2
    assert json.loads(body)["upper_threshold"] == "9"

    # 5. A stale revision is rejected and changes nothing.
    status, _, body = call(
        runtime,
        "PATCH",
        f"{base}/{threshold_id}",
        body=_threshold_payload(threshold_id, upper_threshold="1", expected_revision=1),
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "THRESHOLD_REVISION_CONFLICT"
    status, _, body = call(runtime, "GET", f"{base}/{threshold_id}", cookie=planner_cookie)
    assert json.loads(body)["revision"] == 2 and json.loads(body)["upper_threshold"] == "9"

    # 6. Audit history records both transitions.
    status, _, body = call(runtime, "GET", f"{base}/{threshold_id}/history", cookie=planner_cookie)
    assert status == 200, body
    events = json.loads(body)["events"]
    assert [(event["event_type"], event["revision"]) for event in events] == [
        ("created", 1),
        ("updated", 2),
    ]

    # 7. Monitoring writes an immutable run; the open-issue source is connected.
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/{threshold_id}/monitor",
        body={},
        cookie=planner_cookie,
        csrf=planner_csrf,
        headers={"Idempotency-Key": f"monitor-{threshold_id}"},
    )
    assert status == 200, body
    run = json.loads(body)["run"]
    assert run["level"] == "normal" and run["observed_value"] == "0"
    runs = _db_rows(
        runtime,
        "SELECT run_sequence FROM project_threshold_run "
        "WHERE tenant_id=%s AND project_id=%s AND threshold_id=%s",
        (ids["tenant_a"], project, threshold_id),
    )
    assert runs == [(1,)]

    # A parameter whose source is not deployed fails closed instead of
    # inventing an observed value.
    cost_id = f"TH-COST-{ids['suffix']}"
    status, _, body = call(
        runtime,
        "POST",
        base,
        body=_threshold_payload(
            cost_id,
            monitoring_subject="cost",
            parameter="expense_actual_total",
            currency="USD",
        ),
        cookie=planner_cookie,
        csrf=planner_csrf,
        headers={"Idempotency-Key": f"idem-{cost_id}"},
    )
    assert status == 200, body
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/{cost_id}/monitor",
        body={},
        cookie=planner_cookie,
        csrf=planner_csrf,
        headers={"Idempotency-Key": f"monitor-{cost_id}"},
    )
    assert status == 400, body
    assert json.loads(body)["code"] == "THRESHOLD_EXPENSE_SOURCE_NOT_CONNECTED"

    # 8. Permissions: a viewer reads but never writes; another tenant cannot
    # reach the project at all.
    status, _, body = call(runtime, "GET", base, cookie=viewer_cookie)
    assert status == 200 and len(json.loads(body)["thresholds"]) == 2
    status, _, body = call(
        runtime,
        "POST",
        base,
        body=_threshold_payload(f"TH-VIEWER-{ids['suffix']}"),
        cookie=viewer_cookie,
        csrf=viewer_csrf,
        headers={"Idempotency-Key": f"idem-viewer-{ids['suffix']}"},
    )
    assert status == 403, body
    status, _, body = call(runtime, "GET", base, cookie=outsider_cookie)
    assert status == 403, body

    # 9. Delete with the current revision, then confirm the row and its runs
    # are gone while the audit trail still proves the full cycle.
    status, _, body = call(
        runtime,
        "DELETE",
        f"{base}/{threshold_id}",
        body={"expected_revision": 2},
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 200, body
    status, _, body = call(runtime, "GET", f"{base}/{threshold_id}", cookie=planner_cookie)
    assert status == 404, body
    assert _db_rows(
        runtime,
        "SELECT COUNT(*) FROM project_threshold "
        "WHERE tenant_id=%s AND project_id=%s",
        (ids["tenant_a"], project),
    ) == [(1,)]
    audit = _db_rows(
        runtime,
        "SELECT event_type, revision FROM project_threshold_audit "
        "WHERE tenant_id=%s AND project_id=%s AND entity_id=%s ORDER BY revision",
        (ids["tenant_a"], project, threshold_id),
    )
    assert audit == [("created", 1), ("updated", 2), ("deleted", 3)]


def _issue_payload(issue_id: str, **overrides):
    payload = {
        "issue_id": issue_id,
        "title": "Late facade delivery",
        "description": "Curtain wall package slipped behind the crane release.",
        "issue_type": "schedule",
        "status": "open",
        "priority": "high",
        "owner": "Site Planner",
        "date_identified": "2026-11-01",
        "due_date": "2026-11-20",
    }
    payload.update(overrides)
    return payload


def test_issue_register_is_reachable_and_durable_over_postgres(runtime):
    """The issue API is composed in production, so /p6/issues is a real route.

    Before this assertion the runtime built ``P6IssueAPI`` but never passed it
    to the router: every call fell through to ROUTE_NOT_FOUND, which left
    monitoring and project control without their durable issue backbone.
    """

    ids = runtime.test_ids
    project = ids["project_a"]
    base = f"/api/projects/{project}/p6/issues"
    planner_cookie, planner_csrf = login(runtime, "planner", PLANNER_PASSWORD)
    viewer_cookie, viewer_csrf = login(runtime, "viewer", VIEWER_PASSWORD)
    outsider_cookie, outsider_csrf = login(runtime, "outsider", ADMIN_PASSWORD)
    issue_id = f"ISS-E2E-{ids['suffix']}"

    # 1. The route exists and the register starts empty (no ROUTE_NOT_FOUND).
    status, _, body = call(runtime, "GET", base, cookie=planner_cookie)
    assert status == 200, body
    assert json.loads(body)["issues"] == []

    # 2. Create, persisted through the production composition.
    status, _, body = call(
        runtime,
        "POST",
        base,
        body=_issue_payload(issue_id),
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 200, body
    created = json.loads(body)["issue"]
    assert created["issue_id"] == issue_id and created["record_revision"] == 1

    # 3. A new request reads the same row back, and the row exists in PostgreSQL.
    status, _, body = call(runtime, "GET", f"{base}/{issue_id}", cookie=planner_cookie)
    assert status == 200, body
    assert json.loads(body)["issue"]["record_revision"] == 1
    stored = _db_rows(
        runtime,
        "SELECT record_revision, status, issue_type FROM p6_issue "
        "WHERE tenant_id=%s AND project_id=%s AND issue_id=%s",
        (ids["tenant_a"], project, issue_id),
    )
    assert stored == [(1, "open", "schedule")]

    # 4. A duplicate identifier is rejected without touching the stored row.
    status, _, body = call(
        runtime,
        "POST",
        base,
        body=_issue_payload(issue_id, title="Duplicate"),
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "ISSUE_ALREADY_EXISTS"

    # 5. A guarded edit moves the record to a new revision.
    status, _, body = call(
        runtime,
        "PATCH",
        f"{base}/{issue_id}",
        body=_issue_payload(
            issue_id, status="in_progress", expected_revision=1
        ),
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 200, body
    assert json.loads(body)["issue"]["record_revision"] == 2
    status, _, body = call(runtime, "GET", f"{base}/{issue_id}", cookie=planner_cookie)
    assert json.loads(body)["issue"]["status"] == "in_progress"

    # 6. A stale revision is refused and changes nothing.
    status, _, body = call(
        runtime,
        "PATCH",
        f"{base}/{issue_id}",
        body=_issue_payload(
            issue_id, status="resolved", resolution_note="Recovered", expected_revision=1
        ),
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "ISSUE_REVISION_CONFLICT"
    status, _, body = call(runtime, "GET", f"{base}/{issue_id}", cookie=planner_cookie)
    assert json.loads(body)["issue"]["record_revision"] == 2
    assert json.loads(body)["issue"]["status"] == "in_progress"

    # 7. History is durable, not reconstructed from the current row.
    status, _, body = call(
        runtime, "GET", f"{base}/{issue_id}/history", cookie=planner_cookie
    )
    assert status == 200, body
    events = [entry["event"]["event_type"] for entry in json.loads(body)["events"]]
    assert events[0] == "created"
    assert "status_changed" in events

    # 8. Read is open to a viewer; write and foreign tenants are denied.
    status, _, body = call(runtime, "GET", base, cookie=viewer_cookie)
    assert status == 200, body
    assert len(json.loads(body)["issues"]) == 1
    status, _, body = call(
        runtime,
        "POST",
        base,
        body=_issue_payload(f"ISS-VIEWER-{ids['suffix']}"),
        cookie=viewer_cookie,
        csrf=viewer_csrf,
    )
    assert status == 403, body
    status, _, body = call(runtime, "GET", base, cookie=outsider_cookie)
    assert status == 403, body

    # 9. Delete with the current revision removes the row but keeps the audit.
    status, _, body = call(
        runtime,
        "DELETE",
        f"{base}/{issue_id}",
        body={"expected_revision": 2},
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 200, body
    status, _, body = call(runtime, "GET", f"{base}/{issue_id}", cookie=planner_cookie)
    assert status == 404, body
    assert _db_rows(
        runtime,
        "SELECT COUNT(*) FROM p6_issue WHERE tenant_id=%s AND project_id=%s AND issue_id=%s",
        (ids["tenant_a"], project, issue_id),
    ) == [(0,)]
    trail = _db_rows(
        runtime,
        "SELECT event_type FROM p6_issue_event "
        "WHERE tenant_id=%s AND project_id=%s AND issue_id=%s ORDER BY event_sequence",
        (ids["tenant_a"], project, issue_id),
    )
    assert [row[0] for row in trail][0] == "created"
    assert trail[-1][0] == "deleted"


def test_calendar_register_is_reachable_and_feeds_the_schedule_registry(runtime):
    """Calendars reach the router and the evaluator's registry in production.

    Before this wiring the router answered ROUTE_NOT_FOUND for every calendar
    call and the schedule query raised SCHEDULE_QUERY_NOT_DEPLOYED, so no
    calculation could ever produce a date, a float or a critical path.
    """

    from construction_pm.calendar_master_repository import PostgresCalendarMasterRepository
    from construction_pm.calendar_snapshot_repository import (
        PostgresCalendarSnapshotRepository,
    )
    from construction_pm.deployment.calendar_registry import (
        build_postgres_calendar_registry,
    )
    from construction_pm.scheduling.calendar import WorkingCalendar
    from construction_pm.scheduling.calendar_system import CalendarSystem

    ids = runtime.test_ids
    project = ids["project_a"]
    base = f"/api/projects/{project}/p6/calendars"
    planner_cookie, planner_csrf = login(runtime, "planner", PLANNER_PASSWORD)
    viewer_cookie, viewer_csrf = login(runtime, "viewer", VIEWER_PASSWORD)
    calendar_id = f"CAL-E2E-{ids['suffix']}"
    version = "v1"

    # 1. The catalog is reachable (200, not ROUTE_NOT_FOUND).
    status, _, body = call(runtime, "GET", base, cookie=planner_cookie)
    assert status == 200, body
    assert json.loads(body)["kind"] == "calendar_catalog"
    before = len(json.loads(body)["calendars"])

    # 2. A calendar master is created through the production router.
    status, _, body = call(
        runtime,
        "POST",
        base,
        body={
            "calendar_id": calendar_id,
            "calendar_version": version,
            "calendar_type": "project",
            "kind": "working-day",
            "name": "E2E working calendar",
        },
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 200, body
    created = json.loads(body)
    assert created["calendar_id"] == calendar_id

    # 3. It is listed from the durable row, and the master really exists.
    status, _, body = call(runtime, "GET", base, cookie=planner_cookie)
    assert status == 200, body
    listed = json.loads(body)["calendars"]
    assert len(listed) == before + 1
    assert any(item["calendar_id"] == calendar_id for item in listed)
    assert _db_rows(
        runtime,
        "SELECT record_revision FROM calendar_master "
        "WHERE tenant_id=%s AND project_id=%s AND calendar_id=%s AND calendar_version=%s",
        (ids["tenant_a"], project, calendar_id, version),
    ) == [(1,)]

    # 4. A stored definition makes the calendar consumable: the registry the
    #    evaluator uses resolves it and honours the working weekdays.
    status, _, body = call(runtime, "GET", "/api/projects", cookie=planner_cookie)
    assert status == 200, body
    revision = int(
        next(
            item["revision"]
            for item in json.loads(body)["projects"]
            if item["project_id"] == project
        )
    )
    from construction_pm.backend_p0.models import BackendScope

    import psycopg

    seeded = psycopg.connect(
        os.environ["CONSTRUCTION_PM_POSTGRES_DSN"],
        autocommit=True,
        options=f"-c search_path={ids['schema']}",
    )
    scope = BackendScope(ids["tenant_a"], project, revision)
    master_repository = PostgresCalendarMasterRepository(seeded)
    snapshot_repository = PostgresCalendarSnapshotRepository(seeded)
    master = master_repository.get(scope, calendar_id, version)
    assert master is not None
    definition = WorkingCalendar(
        working_weekdays=frozenset({0, 1, 2, 3, 4}), system=CalendarSystem.GREGORIAN
    )
    snapshot_repository.save(master, definition)
    registry = build_postgres_calendar_registry(seeded)
    from construction_pm.scheduling.calendar_context import CalendarReference

    resolver = registry.resolve(
        CalendarReference(calendar_id, version, "working-day", CalendarSystem.GREGORIAN)
    )
    assert resolver is not None
    assert snapshot_repository.get(master) is not None
    seeded.close()

    # 5. The schedule query reaches the evaluator instead of failing as
    #    "not deployed"; the factory is the durable registry now.
    status, _, body = call(
        runtime,
        "POST",
        "/api/v1/schedule/query",
        body={
            "contract_version": "schedule-query.v1",
            "query_id": f"q-{ids['suffix']}",
            "scope": {
                "tenant_id": ids["tenant_a"],
                "project_id": project,
                "project_revision": revision,
            },
            "requested_by": runtime.test_ids["users"]["planner"].user_id,
            "query_text": "schedule facts",
            "kind": "fact",
            "language": "en",
        },
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 400, status
    # The registry is built first and succeeds; the request then fails on the
    # missing immutable snapshot, which is the next honest validation, not a
    # "not deployed" shortcut.
    query_error = json.loads(body)["code"]
    assert query_error == "SCHEDULE_INPUT_SNAPSHOT_ID_REQUIRED"

    # 6. A viewer reads the catalog but cannot create a calendar.
    status, _, body = call(runtime, "GET", base, cookie=viewer_cookie)
    assert status == 200, body
    status, _, body = call(
        runtime,
        "POST",
        base,
        body={
            "calendar_id": f"CAL-VIEWER-{ids['suffix']}",
            "calendar_version": version,
            "calendar_type": "project",
            "kind": "working-day",
            "name": "Viewer calendar",
        },
        cookie=viewer_cookie,
        csrf=viewer_csrf,
    )
    assert status == 403, body

    # 7. Delete with the current revision removes the master.
    status, _, body = call(
        runtime,
        "DELETE",
        f"{base}/{calendar_id}/{version}",
        body={"expected_revision": 1},
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 200, body
    assert _db_rows(
        runtime,
        "SELECT COUNT(*) FROM calendar_master "
        "WHERE tenant_id=%s AND project_id=%s AND calendar_id=%s",
        (ids["tenant_a"], project, calendar_id),
    ) == [(0,)]


def _workspace_read_without_facts(runtime, scope):
    """Project the workspace with the pre-change provider shape (no facts).

    Before this slice the production composition built the provider without a
    ``schedule_facts_provider``, so the grid could never show a calculated date
    or float. This helper reproduces that shape over the same durable rows.
    """

    import psycopg

    from construction_pm.activity_master_repository import (
        PostgresActivityMasterRepository,
    )
    from construction_pm.backend_p0.workspace_read_provider import (
        PersistedWorkspaceReadProvider,
    )
    from construction_pm.relationship_master_repository import (
        PostgresRelationshipMasterRepository,
    )
    from construction_pm.wbs_master_repository import PostgresWBSMasterRepository

    connection = psycopg.connect(
        os.environ["CONSTRUCTION_PM_POSTGRES_DSN"],
        autocommit=True,
        options=f"-c search_path={runtime.test_ids['schema']}",
    )
    try:
        provider = PersistedWorkspaceReadProvider(
            activity_repository=PostgresActivityMasterRepository(connection),
            wbs_repository=PostgresWBSMasterRepository(connection),
            relationship_repository=PostgresRelationshipMasterRepository(connection),
        )
        result = provider.read(scope)
        return {item["id"]: item["cells"] for item in result["workspace"]["activities"]}
    finally:
        connection.close()


def test_published_snapshot_drives_production_workspace_float_and_critical_path(runtime):
    """A published snapshot is projected by the production workspace read.

    The whole chain runs through the deployed WSGI composition: persisted WBS,
    activities, a relationship, a durable calendar definition, saved schedule
    settings and an immutable snapshot publication. The grid must then show the
    Shared Core early/late dates, total float, free float and criticality, and
    a new session must read the same snapshot identity and the same numbers.
    """

    import psycopg

    from construction_pm.backend_p0.models import BackendScope
    from construction_pm.backend_p0.workspace_read_provider import (
        PersistedWorkspaceReadProvider,
    )
    from construction_pm.calendar_master_repository import PostgresCalendarMasterRepository
    from construction_pm.calendar_snapshot_repository import (
        PostgresCalendarSnapshotRepository,
    )
    from construction_pm.schedule_input_snapshot_repository import (
        PostgresScheduleInputSnapshotRepository,
    )
    from construction_pm.scheduling.calendar import WorkingCalendar
    from construction_pm.scheduling.calendar_system import CalendarSystem
    from construction_pm.scheduling.schedule_options import ScheduleOptions
    from construction_pm.project_schedule_settings_repository import (
        _schedule_options_payload,
    )

    ids = runtime.test_ids
    project = ids["project_a"]
    suffix = uuid.uuid4().hex[:8]
    cookie, csrf = login(runtime, "planner", PLANNER_PASSWORD)

    status, _, body = call(runtime, "GET", "/api/projects", cookie=cookie)
    assert status == 200, body
    project_revision = int(
        next(
            item["revision"]
            for item in json.loads(body)["projects"]
            if item["project_id"] == project
        )
    )

    # 1. A durable calendar with a stored definition. The router can create the
    #    master; the immutable definition is written through the same
    #    PostgreSQL repository the application uses (the API has no endpoint
    #    for defining a root calendar's working week yet).
    calendar_id, calendar_version = f"CAL-SCHED-{suffix}", "v1"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/calendars",
        body={
            "calendar_id": calendar_id,
            "calendar_version": calendar_version,
            "calendar_type": "project",
            "kind": "working-day",
            "name": "Production schedule calendar",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    seeded = psycopg.connect(
        os.environ["CONSTRUCTION_PM_POSTGRES_DSN"],
        autocommit=True,
        options=f"-c search_path={ids['schema']}",
    )
    try:
        scope = BackendScope(ids["tenant_a"], project, project_revision)
        master_repository = PostgresCalendarMasterRepository(seeded)
        snapshot_repository_cal = PostgresCalendarSnapshotRepository(seeded)
        master = master_repository.get(scope, calendar_id, calendar_version)
        assert master is not None
        snapshot_repository_cal.save(
            master,
            WorkingCalendar(
                working_weekdays=frozenset({0, 1, 2, 3, 4}),
                system=CalendarSystem.GREGORIAN,
            ),
        )
        assert snapshot_repository_cal.get(master) is not None
    finally:
        seeded.close()

    # 2. Persisted WBS and two linked activities.
    wbs_id = f"wbs-sched-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/wbs",
        body={
            "wbs_id": wbs_id,
            "code": f"2-{suffix}",
            "name": "Structure",
            "parent_kind": "wbs",
            "parent_wbs_id": ids["root_wbs"],
            "sequence_number": 2,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body

    first, second = f"ACT-A-{suffix}", f"ACT-B-{suffix}"
    for activity_id, duration, name in ((first, 3, "Excavate"), (second, 2, "Footings")):
        status, _, body = call(
            runtime,
            "POST",
            f"/api/projects/{project}/p6/activities",
            body={
                "activity_id": activity_id,
                "name": name,
                "duration_value": duration,
                "duration_unit": "working-day",
                "wbs_id": wbs_id,
            },
            cookie=cookie,
            csrf=csrf,
        )
        assert status == 201, body

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/relationships",
        body={
            "relationship_id": f"REL-{suffix}",
            "predecessor_id": first,
            "successor_id": second,
            "relationship_type": "FS",
            "lag_value": "0",
            "lag_unit": "working-day",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status in {200, 201}, body

    # 3. Schedule settings bound to the stored calendar.
    settings_payload = {
        "contract_version": "p6-project-schedule-settings-api.v1",
        "expected_record_revision": 0,
        "mode": "DATE_BASED",
        "project_calendar_id": calendar_id,
        "project_calendar_version": calendar_version,
        "project_calendar_system": "gregorian",
        "project_start": "2026-11-02",
        "project_finish": None,
        "schedule_options": _schedule_options_payload(ScheduleOptions()),
        "project_leveling_priority": 50,
    }
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/schedule/settings",
        body=settings_payload,
        cookie=cookie,
        csrf=csrf,
    )
    assert status in {200, 201}, body

    # 4. Publish an immutable snapshot through the production router.
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/schedule/snapshots",
        body={
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status in {200, 201}, body
    published = json.loads(body)
    snapshot_id = published["snapshot_id"]
    snapshot_hash = published["snapshot_hash"]
    calculation_identity = published["calculation_identity"]
    assert published["kind"] == "schedule_input_snapshot"
    assert snapshot_hash and calculation_identity

    # 5. The workspace read projects the Shared Core result, not raw inputs.
    headers = {
        "X-Tenant-Id": ids["tenant_a"],
        "X-Project-Id": project,
        "X-Project-Revision": str(project_revision),
    }
    status, _, body = call(
        runtime,
        "GET",
        "/api/v2/workspace/control-room/read",
        cookie=cookie,
        headers=headers,
    )
    assert status == 200, body
    workspace = json.loads(body)
    activities = workspace["workspace"]["activities"]
    cells_by_activity = {item["id"]: item["cells"] for item in activities}
    gantt_by_activity = {item["id"]: item["gantt"] for item in activities}
    for activity_id in (first, second):
        cells = cells_by_activity[activity_id]
        for field_id in (
            "activity.early_start",
            "activity.early_finish",
            "activity.late_start",
            "activity.late_finish",
            "activity.total_float",
            "activity.free_float",
            "activity.is_critical",
        ):
            assert field_id in cells, (activity_id, field_id)
        # Multiple float-path membership is projected only when the shared
        # calculation produced it; with the option disabled the cell must be
        # absent rather than a fabricated path number.
        assert "activity.float_path" not in cells
        assert isinstance(gantt_by_activity[activity_id]["critical"], bool)
        assert cells["start"] == cells["activity.early_start"]
        assert cells["finish"] == cells["activity.early_finish"]

    # The relationship must push the successor after its predecessor, and the
    # chain sets the critical path: both activities carry zero total float.
    first_cells = cells_by_activity[first]
    second_cells = cells_by_activity[second]
    assert first_cells["activity.early_finish"] <= second_cells["activity.early_start"]
    assert first_cells["activity.total_float"] == 0
    assert second_cells["activity.total_float"] == 0
    assert first_cells["activity.is_critical"] is True
    assert second_cells["activity.is_critical"] is True

    # 6. A new session and a new request read the same snapshot identity.
    second_cookie, _ = login(runtime, "planner", PLANNER_PASSWORD)
    status, _, body = call(
        runtime,
        "GET",
        "/api/v2/workspace/control-room/read",
        cookie=second_cookie,
        headers=headers,
    )
    assert status == 200, body
    reloaded = {
        item["id"]: item["cells"]
        for item in json.loads(body)["workspace"]["activities"]
    }
    for activity_id in (first, second):
        assert reloaded[activity_id]["activity.early_start"] == cells_by_activity[activity_id]["activity.early_start"]
        assert reloaded[activity_id]["activity.total_float"] == 0

    # The snapshot is immutable and revision-bound in storage.
    reader = psycopg.connect(
        os.environ["CONSTRUCTION_PM_POSTGRES_DSN"],
        autocommit=True,
        options=f"-c search_path={ids['schema']}",
    )
    try:
        snapshots = PostgresScheduleInputSnapshotRepository(reader)
        stored = snapshots.get(scope, snapshot_id)
        assert stored is not None and stored.snapshot_hash == snapshot_hash
        stale_scope = BackendScope(ids["tenant_a"], project, project_revision + 1)
        try:
            snapshots.get(stale_scope, snapshot_id)
        except Exception as exc:  # revision binding is enforced, not ignored
            assert "REVISION_CONFLICT" in str(exc) or type(exc).__name__ == "ScheduleSnapshotPersistenceError"
        else:
            raise AssertionError("a snapshot must not be readable under another revision")
        assert snapshots.get(BackendScope(ids["tenant_b"], project, project_revision), snapshot_id) is None
    finally:
        reader.close()

    # 7. Regression proof: the same repositories through the pre-change provider
    #    shape (no facts provider) cannot invent float or a date.
    bare_read = _workspace_read_without_facts(runtime, scope)
    assert "activity.total_float" not in bare_read[first]
    assert "activity.early_start" not in bare_read[first]

    # 8. Stale project revision is refused by the v2 read contract.
    status, _, body = call(
        runtime,
        "GET",
        "/api/v2/workspace/control-room/read",
        cookie=cookie,
        headers={**headers, "X-Project-Revision": str(project_revision + 1)},
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "STALE_WORKSPACE_READ_SCOPE"

    # 9. Authorization: a viewer reads, but never publishes; another tenant is
    #    refused before any schedule work happens.
    viewer_cookie, viewer_csrf = login(runtime, "viewer", VIEWER_PASSWORD)
    status, _, body = call(
        runtime,
        "GET",
        "/api/v2/workspace/control-room/read",
        cookie=viewer_cookie,
        headers=headers,
    )
    assert status == 200, body
    assert json.loads(body)["workspace"]["activities"]
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/schedule/snapshots",
        body={"contract_version": "p6-schedule-snapshot-api.v1", "timezone": "UTC"},
        cookie=viewer_cookie,
        csrf=viewer_csrf,
    )
    assert status == 403, body
    outsider_cookie, outsider_csrf = login(runtime, "outsider", ADMIN_PASSWORD)
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/schedule/snapshots",
        body={"contract_version": "p6-schedule-snapshot-api.v1", "timezone": "UTC"},
        cookie=outsider_cookie,
        csrf=outsider_csrf,
    )
    assert status == 403, body
    status, _, body = call(
        runtime, "GET", f"/api/projects/{project}/p6/schedule/settings", cookie=outsider_cookie
    )
    assert status == 403, body

    # 10. Fail closed: settings that point at a calendar without a stored
    #     definition make publication refuse instead of inventing dates.
    bare_calendar = f"CAL-BARE-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/calendars",
        body={
            "calendar_id": bare_calendar,
            "calendar_version": "v1",
            "calendar_type": "project",
            "kind": "working-day",
            "name": "Undefined calendar",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/p6/schedule/settings",
        cookie=cookie,
    )
    assert status == 200, body
    current_revision = json.loads(body)["record_revision"]
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/schedule/settings",
        body={
            **settings_payload,
            "expected_record_revision": current_revision,
            "project_calendar_id": bare_calendar,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status in {200, 201}, body
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/schedule/snapshots",
        body={"contract_version": "p6-schedule-snapshot-api.v1", "timezone": "UTC"},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 400, body
    failure = json.loads(body)["code"]
    assert "CALENDAR_SNAPSHOT" in failure or "CALENDAR_VERSION" in failure, failure

    # 11. An undefined calendar must not poison the rest of the database: the
    #     previously published snapshot still projects, because the registry
    #     only consumes calendars that have a stored definition.
    status, _, body = call(
        runtime,
        "GET",
        "/api/v2/workspace/control-room/read",
        cookie=cookie,
        headers=headers,
    )
    assert status == 200, body
    still_projected = {
        item["id"]: item["cells"]
        for item in json.loads(body)["workspace"]["activities"]
    }
    assert still_projected[first]["activity.early_start"] == first_cells["activity.early_start"]


def test_root_calendar_definition_is_managed_through_the_authenticated_api(runtime):
    """A user defines a root calendar entirely through the product API.

    Slice 4 proved float and critical path once a definition existed, but the
    definition itself could only be written through the repository. This test
    uses no repository write for the normal workflow: the authenticated router
    creates the master and its immutable working week atomically, the registry
    resolves exactly that definition, and a published snapshot evaluates with
    it after a fresh login.
    """

    from datetime import date

    import psycopg

    from construction_pm.deployment.calendar_registry import (
        build_postgres_calendar_registry,
    )
    from construction_pm.project_schedule_settings_repository import (
        _schedule_options_payload,
    )
    from construction_pm.scheduling.calendar_context import CalendarReference
    from construction_pm.scheduling.calendar_system import CalendarSystem
    from construction_pm.scheduling.schedule_options import ScheduleOptions

    ids = runtime.test_ids
    project = ids["project_a"]
    suffix = uuid.uuid4().hex[:8]
    cookie, csrf = login(runtime, "planner", PLANNER_PASSWORD)
    viewer_cookie, viewer_csrf = login(runtime, "viewer", VIEWER_PASSWORD)
    outsider_cookie, _ = login(runtime, "outsider", ADMIN_PASSWORD)

    base = f"/api/projects/{project}/p6/calendars"
    calendar_id, calendar_version = f"CAL-DEF-{suffix}", "v1"
    # Tuesday..Saturday week with a Wednesday holiday: a default Monday..Friday
    # calendar would schedule the Monday project start, this one cannot.
    definition = {
        "system": "gregorian",
        "working_weekdays": [1, 2, 3, 4, 5],
        "holidays": ["2026-11-04"],
    }

    # 1. The router creates master and definition in one authenticated call.
    status, _, body = call(
        runtime,
        "POST",
        base,
        body={
            "calendar_id": calendar_id,
            "calendar_version": calendar_version,
            "calendar_type": "project",
            "kind": "working-day",
            "name": "Root calendar via API",
            "definition": definition,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    created = json.loads(body)
    assert created["schedulable"] is True
    assert created["record_revision"] == 1

    # 2. A fresh session reopens the stored definition unchanged.
    fresh_cookie, fresh_csrf = login(runtime, "planner", PLANNER_PASSWORD)
    detail_path = f"{base}/{calendar_id}/{calendar_version}/definition"
    status, _, body = call(runtime, "GET", detail_path, cookie=fresh_cookie)
    assert status == 200, body
    stored = json.loads(body)
    assert stored["contract_version"] == "p6-calendar-definition.v1"
    assert stored["schedulable"] is True
    assert stored["definition"]["working_weekdays"] == [1, 2, 3, 4, 5]
    assert stored["definition"]["holidays"] == ["2026-11-04"]
    assert stored["definition"]["system"] == "gregorian"
    assert stored["calendar"]["record_revision"] == 1

    # 3. The definition is durable and came from this request, not a fixture.
    assert _db_rows(
        runtime,
        "SELECT record_revision FROM calendar_master "
        "WHERE tenant_id=%s AND project_id=%s AND calendar_id=%s AND calendar_version=%s",
        (ids["tenant_a"], project, calendar_id, calendar_version),
    ) == [(1,)]
    snapshot_rows = _db_rows(
        runtime,
        "SELECT snapshot_json FROM calendar_master_snapshot "
        "WHERE tenant_id=%s AND project_id=%s AND calendar_id=%s AND calendar_version=%s",
        (ids["tenant_a"], project, calendar_id, calendar_version),
    )
    assert len(snapshot_rows) == 1
    durable_definition = snapshot_rows[0][0]
    assert durable_definition["working_weekdays"] == [1, 2, 3, 4, 5]
    assert durable_definition["holidays"] == ["2026-11-04"]

    # 4. Idempotent replay is accepted; a different definition is immutable
    #    because a published calculation must stay reproducible.
    status, _, body = call(
        runtime,
        "PUT",
        detail_path,
        body={"expected_revision": 1, "definition": definition},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    assert json.loads(body)["calendar"]["record_revision"] == 1
    status, _, body = call(
        runtime,
        "PUT",
        detail_path,
        body={
            "expected_revision": 1,
            "definition": {**definition, "working_weekdays": [0, 1, 2, 3, 4]},
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "CALENDAR_DEFINITION_IMMUTABLE"

    # 5. A bare master is visible but explicitly not schedulable.
    bare_id = f"CAL-BARE-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        base,
        body={
            "calendar_id": bare_id,
            "calendar_version": "v1",
            "calendar_type": "project",
            "kind": "working-day",
            "name": "Bare master",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    assert json.loads(body)["schedulable"] is False
    status, _, body = call(runtime, "GET", f"{base}/{bare_id}/v1/definition", cookie=cookie)
    assert status == 200, body
    assert json.loads(body)["definition"] is None
    assert json.loads(body)["schedulable"] is False

    # 6. Sealing that master is revision guarded, and a stale write is refused.
    bare_detail = f"{base}/{bare_id}/v1/definition"
    status, _, body = call(
        runtime,
        "PUT",
        bare_detail,
        body={"expected_revision": 2, "definition": definition},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "REVISION_CONFLICT"
    status, _, body = call(
        runtime,
        "PUT",
        bare_detail,
        body={"expected_revision": 1, "definition": definition},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    assert json.loads(body)["calendar"]["record_revision"] == 2
    status, _, body = call(
        runtime,
        "PUT",
        bare_detail,
        body={"expected_revision": 1, "definition": definition},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "REVISION_CONFLICT"

    # 7. A rejected definition leaves no master behind (atomic over HTTP).
    malformed_id = f"CAL-HTTP-BAD-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        base,
        body={
            "calendar_id": malformed_id,
            "calendar_version": "v1",
            "calendar_type": "project",
            "kind": "working-day",
            "name": "Malformed",
            "definition": {"working_weekdays": []},
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 400, body
    assert json.loads(body)["code"] == "CALENDAR_DEFINITION_WORKING_WEEK_REQUIRED"
    assert _db_rows(
        runtime,
        "SELECT COUNT(*) FROM calendar_master WHERE tenant_id=%s AND project_id=%s AND calendar_id=%s",
        (ids["tenant_a"], project, malformed_id),
    ) == [(0,)]

    # 8. Authorization: viewer reads the definition but cannot change it; a
    #    foreign tenant cannot read it at all.
    status, _, body = call(runtime, "GET", detail_path, cookie=viewer_cookie)
    assert status == 200, body
    status, _, body = call(
        runtime,
        "PUT",
        detail_path,
        body={"expected_revision": 1, "definition": definition},
        cookie=viewer_cookie,
        csrf=viewer_csrf,
    )
    assert status == 403, body
    status, _, body = call(runtime, "GET", detail_path, cookie=outsider_cookie)
    assert status == 403, body

    # 9. The evaluator's registry resolves exactly the stored definition.
    connection = psycopg.connect(
        os.environ["CONSTRUCTION_PM_POSTGRES_DSN"],
        autocommit=True,
        options=f"-c search_path={ids['schema']}",
    )
    try:
        registry = build_postgres_calendar_registry(connection)
        resolver = registry.resolve(
            CalendarReference(
                calendar_id, calendar_version, "working-day", CalendarSystem.GREGORIAN
            )
        )
        assert resolver is not None
        assert resolver.is_working_day(date(2026, 11, 2)) is False  # Monday
        assert resolver.is_working_day(date(2026, 11, 3)) is True   # Tuesday
        assert resolver.is_working_day(date(2026, 11, 4)) is False  # holiday
        assert resolver.is_working_day(date(2026, 11, 7)) is True   # Saturday
        assert registry.resolve(
            CalendarReference(bare_id, "v1", "working-day", CalendarSystem.GREGORIAN)
        ) is not None  # sealed in step 6
    finally:
        connection.close()

    # 10. The definition really drives a published calculation: the project
    #     starts on Monday 2026-11-02, which this calendar does not work.
    activity_id = f"ACT-CAL-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/activities",
        body={
            "activity_id": activity_id,
            "name": "Calendar-driven task",
            "duration_value": 2,
            "duration_unit": "working-day",
            "wbs_id": ids["root_wbs"],
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body
    # Another live test in this module may already own the project's single
    # settings row, so the guarded write starts from its current revision.
    settings_rows = _db_rows(
        runtime,
        "SELECT record_revision FROM project_schedule_settings "
        "WHERE tenant_id=%s AND project_id=%s",
        (ids["tenant_a"], project),
    )
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/schedule/settings",
        body={
            "contract_version": "p6-project-schedule-settings-api.v1",
            "expected_record_revision": int(settings_rows[0][0]) if settings_rows else 0,
            "mode": "DATE_BASED",
            "project_calendar_id": calendar_id,
            "project_calendar_version": calendar_version,
            "project_calendar_system": "gregorian",
            "project_start": "2026-11-02",
            "project_finish": None,
            "schedule_options": _schedule_options_payload(ScheduleOptions()),
            "project_leveling_priority": 50,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status in {200, 201}, body
    status, _, body = call(runtime, "GET", "/api/projects", cookie=cookie)
    assert status == 200, body
    project_revision = int(
        next(
            item["revision"]
            for item in json.loads(body)["projects"]
            if item["project_id"] == project
        )
    )
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/schedule/snapshots",
        body={
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status in {200, 201}, body
    published = json.loads(body)
    snapshot_id = published["snapshot_id"]
    assert published["snapshot_hash"] and published["calculation_identity"]

    def _query_facts(query_id: str, cookie_value: str, csrf_value: str) -> dict:
        status, _, body = call(
            runtime,
            "POST",
            "/api/v1/schedule/query",
            body={
                "contract_version": "schedule-query.v1",
                "query_id": query_id,
                "scope": {
                    "tenant_id": ids["tenant_a"],
                    "project_id": project,
                    "project_revision": project_revision,
                },
                "requested_by": ids["users"]["planner"].user_id,
                "query_text": "schedule facts",
                "kind": "fact",
                "language": "en",
                "constraints": {"snapshot_id": snapshot_id},
            },
            cookie=cookie_value,
            csrf=csrf_value,
        )
        assert status == 200, body
        result = json.loads(body)
        assert result["contract_version"] == "schedule-query-result.v1"
        return dict(result["data"])

    # A reload in a new session evaluates the same immutable snapshot to the
    # same facts; the snapshot identity is the published one either way.
    first_facts = _query_facts(f"q-{suffix}-1", cookie, csrf)
    reload_cookie, reload_csrf = login(runtime, "planner", PLANNER_PASSWORD)
    reloaded_facts = _query_facts(f"q-{suffix}-2", reload_cookie, reload_csrf)
    assert reloaded_facts == first_facts

    status, _, body = call(
        runtime,
        "GET",
        "/api/v2/workspace/control-room/read",
        cookie=reload_cookie,
        headers={
            "X-Tenant-Id": ids["tenant_a"],
            "X-Project-Id": project,
            "X-Project-Revision": str(project_revision),
        },
    )
    assert status == 200, body
    cells = {
        item["id"]: item["cells"]
        for item in json.loads(body)["workspace"]["activities"]
    }[activity_id]
    early_start = date.fromisoformat(cells["activity.early_start"])
    # Monday 2026-11-02 is not a working day of the API-defined calendar.
    assert early_start == date(2026, 11, 3)
    assert cells["start"] == cells["activity.early_start"]
    assert "activity.total_float" in cells


def test_resources_and_assignments_drive_the_production_schedule(runtime):
    """Resources and activity resource assignments are real production facts.

    The whole chain is the deployed one: the planner registers a resource and a
    resource-dependent activity, writes assignments and their time-phased rows
    through the authenticated router, and the Shared Core composer derives the
    duration from exactly those rows. A publication without periods fails
    closed; with periods it publishes a duration the persisted activity never
    held. Capacity, rates, optimistic locking, authorization, tenant isolation
    and a fresh-session reload are proven on the same database.
    """

    from datetime import date

    from construction_pm.project_schedule_settings_repository import (
        _schedule_options_payload,
    )
    from construction_pm.scheduling.schedule_options import ScheduleOptions

    ids = runtime.test_ids
    project = ids["project_a"]
    suffix = uuid.uuid4().hex[:8]
    cookie, csrf = login(runtime, "planner", PLANNER_PASSWORD)
    viewer_cookie, viewer_csrf = login(runtime, "viewer", VIEWER_PASSWORD)
    outsider_cookie, _ = login(runtime, "outsider", ADMIN_PASSWORD)

    status, _, body = call(runtime, "GET", "/api/projects", cookie=cookie)
    assert status == 200, body
    project_revision = int(
        next(
            item["revision"]
            for item in json.loads(body)["projects"]
            if item["project_id"] == project
        )
    )

    # 1. Calendars are created through the authenticated definition API: one
    #    project calendar and one resource calendar, both working Mon..Fri.
    base_calendars = f"/api/projects/{project}/p6/calendars"
    project_calendar = f"CAL-RS-{suffix}"
    resource_calendar = f"CAL-RCR-{suffix}"
    definition = {"system": "gregorian", "working_weekdays": [0, 1, 2, 3, 4]}
    for calendar_id, calendar_type, name in (
        (project_calendar, "project", "Resource slice project calendar"),
        (resource_calendar, "resource", "Resource slice crew calendar"),
    ):
        status, _, body = call(
            runtime,
            "POST",
            base_calendars,
            body={
                "calendar_id": calendar_id,
                "calendar_version": "v1",
                "calendar_type": calendar_type,
                "kind": "working-day",
                "name": name,
                "definition": definition,
            },
            cookie=cookie,
            csrf=csrf,
        )
        assert status == 200, body
        assert json.loads(body)["schedulable"] is True

    # 2. The resource master is written by the product route. A stale calendar
    #    reference is rejected before any row exists.
    base_resources = f"/api/projects/{project}/p6/resources"
    resource_id = f"R-CREW-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        base_resources,
        body={
            "resource_id": resource_id,
            "name": "Crew without calendar",
            "resource_type": "labor",
            "calendar_id": f"CAL-MISSING-{suffix}",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "RESOURCE_CALENDAR_NOT_FOUND"

    resource_body = {
        "resource_id": resource_id,
        "name": "Civil crew",
        "resource_type": "labor",
        "calendar_id": resource_calendar,
        "default_units_per_time": "8",
        "unit_of_measure": "labor-unit",
        "email": f"crew-{suffix}@example.test",
    }
    status, _, body = call(
        runtime, "POST", base_resources, body=resource_body, cookie=cookie, csrf=csrf
    )
    assert status == 200, body
    created_resource = json.loads(body)
    assert created_resource["contract_version"] == "p6-resource-api.v1"
    assert created_resource["resource"]["record_revision"] == 1
    assert created_resource["resource"]["calendar_id"] == resource_calendar

    status, _, body = call(
        runtime, "GET", f"{base_resources}/{resource_id}", cookie=cookie
    )
    assert status == 200, body
    assert json.loads(body) == created_resource
    assert _db_rows(
        runtime,
        "SELECT record_revision FROM p6_resource_master "
        "WHERE tenant_id=%s AND project_id=%s AND resource_id=%s",
        (ids["tenant_a"], project, resource_id),
    ) == [(1,)]

    # 3. A persisted WBS and a Resource Dependent activity whose stored duration
    #    (2 days) intentionally disagrees with the assignment contract (5 days).
    wbs_id = f"wbs-res-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/wbs",
        body={
            "wbs_id": wbs_id,
            "code": f"3-{suffix}",
            "name": "Resource work",
            "parent_kind": "wbs",
            "parent_wbs_id": ids["root_wbs"],
            "sequence_number": 3,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body

    activity_id = f"ACT-RD-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/activities",
        body={
            "activity_id": activity_id,
            "name": "Place concrete with crew",
            "duration_value": 2,
            "duration_unit": "working-day",
            "activity_type": "Resource Dependent",
            "wbs_id": wbs_id,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body

    settings_rows = _db_rows(
        runtime,
        "SELECT record_revision FROM project_schedule_settings "
        "WHERE tenant_id=%s AND project_id=%s",
        (ids["tenant_a"], project),
    )
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/schedule/settings",
        body={
            "contract_version": "p6-project-schedule-settings-api.v1",
            "expected_record_revision": int(settings_rows[0][0]) if settings_rows else 0,
            "mode": "DATE_BASED",
            "project_calendar_id": project_calendar,
            "project_calendar_version": "v1",
            "project_calendar_system": "gregorian",
            "project_start": "2026-11-02",
            "project_finish": None,
            "schedule_options": _schedule_options_payload(ScheduleOptions()),
            "project_leveling_priority": 50,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status in {200, 201}, body

    # 4. The assignment is written through the versioned write contract.
    base_assignments = f"/api/projects/{project}/p6/resource-assignments"
    assignment_id = f"AS-RD-{suffix}"
    assignment_body = {
        "contract_version": "p6-resource-write-api.v1",
        "assignment_id": assignment_id,
        "activity_id": activity_id,
        "resource_id": resource_id,
        "units": "40",
        "unit": "labor-unit",
        "calendar_id": resource_calendar,
        "calendar_version": "v1",
        "is_driving": True,
        "units_per_time": "8",
        "units_per_time_period": "day",
        "hours_per_units_time_period": "8",
        "note": "five crew days",
    }
    status, _, body = call(
        runtime, "POST", base_assignments, body=assignment_body, cookie=cookie, csrf=csrf
    )
    assert status == 200, body
    created_assignment = json.loads(body)
    assert created_assignment["contract_version"] == "p6-resource-write-api.v1"
    assert created_assignment["assignment"]["units"] == "40"
    assert created_assignment["assignment"]["is_driving"] is True
    assert created_assignment["assignment"]["calendar_id"] == resource_calendar

    # An assignment is immutable: the same identity with a different payload is
    # refused instead of silently rewriting published demand.
    status, _, body = call(
        runtime,
        "POST",
        base_assignments,
        body={**assignment_body, "units": "32"},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "IMMUTABLE_RESOURCE_ASSIGNMENT"

    # An incomplete Units/Time triple is a validation failure, not a partial row.
    status, _, body = call(
        runtime,
        "POST",
        base_assignments,
        body={
            "contract_version": "p6-resource-write-api.v1",
            "assignment_id": f"AS-BAD-{suffix}",
            "activity_id": activity_id,
            "resource_id": resource_id,
            "units": "8",
            "units_per_time": "8",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 400, body
    assert json.loads(body)["code"] == "P6_RESOURCE_ASSIGNMENT_REQUEST_INVALID"

    # 5. Publication reads the persisted rows: without time-phased demand the
    #    composer refuses, because the duration cannot be placed.
    snapshot_path = f"/api/projects/{project}/p6/schedule/snapshots"
    status, _, body = call(
        runtime,
        "POST",
        snapshot_path,
        body={
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 400, body
    assert json.loads(body)["code"].startswith(
        "RESOURCE_DEPENDENT_ASSIGNMENT_PERIODS_REQUIRED"
    )

    # 6. Five daily demand rows make the contract complete: 5 x 8 = 40 units.
    base_periods = f"/api/projects/{project}/p6/resource-assignment-periods"
    working_days = (
        "2026-11-02",
        "2026-11-03",
        "2026-11-04",
        "2026-11-05",
        "2026-11-06",
    )
    for period_start in working_days:
        status, _, body = call(
            runtime,
            "POST",
            base_periods,
            body={
                "assignment_id": assignment_id,
                "activity_id": activity_id,
                "resource_id": resource_id,
                "period_start": period_start,
                "units": "8",
                "cost": "0",
            },
            cookie=cookie,
            csrf=csrf,
        )
        assert status == 200, body
        assert json.loads(body)["period"]["units"] == "8"

    status, _, body = call(
        runtime,
        "POST",
        snapshot_path,
        body={
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body
    published = json.loads(body)
    snapshot_id = published["snapshot_id"]
    assert published["snapshot_hash"] and published["calculation_identity"]

    # 7. Workspace Read projects the calculated duration (5 days) and dates
    #    while the persisted Planned Duration stays 2: the calculation consumed
    #    the assignment rows, not the activity master value.
    workspace_headers = {
        "X-Tenant-Id": ids["tenant_a"],
        "X-Project-Id": project,
        "X-Project-Revision": str(project_revision),
    }
    status, _, body = call(
        runtime,
        "GET",
        "/api/v2/workspace/control-room/read",
        cookie=cookie,
        headers=workspace_headers,
    )
    assert status == 200, body
    cells = {
        item["id"]: item["cells"] for item in json.loads(body)["workspace"]["activities"]
    }[activity_id]
    assert cells["duration"] == 5
    assert cells["activity.planned_duration"] == "2"
    assert cells["activity.early_start"] == "2026-11-02"
    assert cells["activity.early_finish"] == "2026-11-06"
    assert cells["start"] == "2026-11-02"
    assert cells["finish"] == "2026-11-06"

    def schedule_facts(query_id: str, session_cookie: str, session_csrf: str) -> dict:
        status, _, body = call(
            runtime,
            "POST",
            "/api/v1/schedule/query",
            body={
                "contract_version": "schedule-query.v1",
                "query_id": query_id,
                "scope": {
                    "tenant_id": ids["tenant_a"],
                    "project_id": project,
                    "project_revision": project_revision,
                },
                "requested_by": ids["users"]["planner"].user_id,
                "query_text": "resource dependent facts",
                "kind": "fact",
                "language": "en",
                "constraints": {"snapshot_id": snapshot_id},
            },
            cookie=session_cookie,
            csrf=session_csrf,
        )
        assert status == 200, body
        result = json.loads(body)
        assert result["contract_version"] == "schedule-query-result.v1"
        return dict(result["data"])

    facts = schedule_facts(f"q-res-{suffix}-1", cookie, csrf)
    assert facts["activities"][activity_id]["duration"] == 5
    assert facts["activities"][activity_id]["start"] == "2026-11-02"
    assert facts["activities"][activity_id]["finish"] == "2026-11-06"

    # 8. Durable rows exist in PostgreSQL for exactly these facts.
    assert _db_rows(
        runtime,
        "SELECT COUNT(*) FROM p6_resource_assignment "
        "WHERE tenant_id=%s AND project_id=%s AND assignment_id=%s",
        (ids["tenant_a"], project, assignment_id),
    ) == [(1,)]
    assert _db_rows(
        runtime,
        "SELECT COUNT(*) FROM p6_resource_assignment_period_value "
        "WHERE tenant_id=%s AND project_id=%s AND assignment_id=%s",
        (ids["tenant_a"], project, assignment_id),
    ) == [(5,)]

    # 9. A new session reloads the same ids and values, and the same published
    #    snapshot evaluates to the same facts.
    reload_cookie, reload_csrf = login(runtime, "planner", PLANNER_PASSWORD)
    status, _, body = call(
        runtime, "GET", f"{base_assignments}/{assignment_id}", cookie=reload_cookie
    )
    assert status == 200, body
    reloaded_assignment = json.loads(body)
    assert reloaded_assignment["assignment"] == created_assignment["assignment"]

    status, _, body = call(
        runtime, "GET", base_periods, cookie=reload_cookie
    )
    assert status == 200, body
    reloaded_periods = {
        item["period"]["period_start"]: item["period"]["units"]
        for item in json.loads(body)["periods"]
        if item["period"]["assignment_id"] == assignment_id
    }
    assert reloaded_periods == {day: "8" for day in working_days}

    assert schedule_facts(f"q-res-{suffix}-2", reload_cookie, reload_csrf) == facts

    status, _, body = call(
        runtime,
        "GET",
        "/api/v2/workspace/control-room/read",
        cookie=reload_cookie,
        headers=workspace_headers,
    )
    assert status == 200, body
    reloaded_cells = {
        item["id"]: item["cells"] for item in json.loads(body)["workspace"]["activities"]
    }[activity_id]
    assert reloaded_cells["duration"] == 5
    assert reloaded_cells["activity.early_finish"] == "2026-11-06"

    # 10. Effective-dated capacity and rate facts are real product writes and
    #     are resolved from the same durable stores after a reload.
    capacity_body = {
        "contract_version": "p6-resource-capacity-write-api.v1",
        "resource_id": resource_id,
        "max_units": "8",
        "unit_basis": "day",
        "hours_per_time_period": "8",
        "effective_from": "2026-11-01",
        "effective_to": None,
        "expected_revision": project_revision,
    }
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/resource-capacities",
        body=capacity_body,
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    capacity_identity = json.loads(body)["capacity"]["identity"]
    assert capacity_identity

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/resource-capacities/{resource_id}/resolve",
        body={
            "contract_version": "p6-resource-capacity-read-api.v1",
            "period": "2026-11-03",
            "basis": "day",
            "hours_per_time_period": "8",
        },
        cookie=reload_cookie,
        csrf=reload_csrf,
    )
    assert status == 200, body
    resolved_capacity = json.loads(body)
    assert resolved_capacity["capacity"] == "8"
    assert resolved_capacity["basis"] == "day"

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/resource-rates",
        body={
            "contract_version": "p6-resource-rate-write-api.v1",
            "resource_id": resource_id,
            "rate": "1200",
            "basis": "per_day",
            "currency": "USD",
            "unit": "labor-unit",
            "effective_from": "2026-11-01",
            "effective_to": None,
            "expected_revision": project_revision,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    rate_identity = json.loads(body)["rate"]["identity"]
    assert rate_identity

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/resource-rates/{resource_id}/resolve",
        body={
            "contract_version": "p6-resource-rate-read-api.v1",
            "period": "2026-11-03",
        },
        cookie=reload_cookie,
        csrf=reload_csrf,
    )
    assert status == 200, body
    resolved_rate = json.loads(body)
    assert resolved_rate["rate"] == "1200"
    assert resolved_rate["basis"] == "per_day"
    assert resolved_rate["currency"] == "USD"

    # 11. Optimistic locking on the resource master, plus deactivate/restore.
    status, _, body = call(
        runtime,
        "PATCH",
        f"{base_resources}/{resource_id}",
        body={**resource_body, "name": "Senior civil crew", "expected_revision": 1},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    assert json.loads(body)["resource"]["record_revision"] == 2

    status, _, body = call(
        runtime,
        "PATCH",
        f"{base_resources}/{resource_id}",
        body={**resource_body, "name": "Stale write", "expected_revision": 1},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "REVISION_CONFLICT"

    status, _, body = call(
        runtime,
        "PATCH",
        f"{base_resources}/{resource_id}",
        body={**resource_body, "name": "Retired crew", "is_active": False, "expected_revision": 2},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    assert json.loads(body)["resource"]["is_active"] is False
    assert json.loads(body)["resource"]["record_revision"] == 3

    status, _, body = call(
        runtime,
        "PATCH",
        f"{base_resources}/{resource_id}",
        body={**resource_body, "name": "Civil crew", "is_active": True, "expected_revision": 3},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    restored = json.loads(body)
    assert restored["resource"]["is_active"] is True
    assert restored["resource"]["record_revision"] == 4
    assert (
        restored["resource"]["name"],
        restored["resource"]["calendar_id"],
        restored["resource"]["default_units_per_time"],
    ) == ("Civil crew", resource_calendar, "8")

    # 12. Authorization and tenant isolation on every resource surface.
    status, _, body = call(runtime, "GET", base_resources, cookie=viewer_cookie)
    assert status == 200, body
    assert any(
        item["resource"]["resource_id"] == resource_id
        for item in json.loads(body)["resources"]
    )
    status, _, body = call(
        runtime,
        "POST",
        base_resources,
        body={**resource_body, "resource_id": f"R-VIEWER-{suffix}"},
        cookie=viewer_cookie,
        csrf=viewer_csrf,
    )
    assert status == 403, body
    status, _, body = call(
        runtime,
        "POST",
        base_assignments,
        body={**assignment_body, "assignment_id": f"AS-VIEWER-{suffix}"},
        cookie=viewer_cookie,
        csrf=viewer_csrf,
    )
    assert status == 403, body
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/resource-rates",
        body={
            "contract_version": "p6-resource-rate-write-api.v1",
            "resource_id": resource_id,
            "rate": "900",
            "basis": "per_day",
            "currency": "USD",
            "unit": "labor-unit",
            "effective_from": "2026-12-01",
            "expected_revision": project_revision,
        },
        cookie=viewer_cookie,
        csrf=viewer_csrf,
    )
    assert status == 403, body

    for path in (
        base_resources,
        f"{base_resources}/{resource_id}",
        base_assignments,
        f"{base_assignments}/{assignment_id}",
        f"/api/projects/{project}/p6/resource-capacities",
        f"/api/projects/{project}/p6/resource-rates",
    ):
        status, _, body = call(runtime, "GET", path, cookie=outsider_cookie)
        assert status == 403, (path, body)

    # The capacity write is also project-revision guarded.
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/resource-capacities",
        body={
            **capacity_body,
            "max_units": "10",
            "effective_from": "2026-12-01",
            "expected_revision": project_revision + 1,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "REVISION_CONFLICT"


# ---------------------------------------------------------------------------
# Data Date + Progress: the shared engine consumes persisted progress facts
# ---------------------------------------------------------------------------


def test_data_date_and_progress_are_operational_end_to_end(runtime):
    """Data Date and progress survive the full production chain.

    One independent project is driven through the real HTTP surface: Data Date
    is stored in the project schedule settings, Actual Start/Finish, percent
    complete and Remaining Duration are stored on the Activity Master with
    append-only history, the shared scheduler is re-run, and a new session
    reads the same stored values. Planned Duration and baseline fields must be
    untouched, and the revision conflict and authorization boundaries must
    still hold.
    """

    from datetime import date

    import psycopg

    from construction_pm.activity_progress_history import (
        PostgresActivityProgressHistoryRepository,
    )
    from construction_pm.backend_p0.models import BackendScope
    from construction_pm.project_schedule_settings_repository import (
        _schedule_options_payload,
    )
    from construction_pm.scheduling.schedule_options import ScheduleOptions

    ids = runtime.test_ids
    suffix = uuid.uuid4().hex[:8]
    project = f"project-dd-{suffix}"
    tenant = ids["tenant_a"]
    admin, admin_csrf = login(runtime, "admin", ADMIN_PASSWORD)

    # 1. An independent project created through the real lifecycle API.
    status, _, body = call(
        runtime,
        "POST",
        "/api/projects",
        body={
            "project_id": project,
            "name": f"Data date acceptance {suffix}",
            "start_date": "2026-11-02",
        },
        cookie=admin,
        csrf=admin_csrf,
    )
    assert status == 201, body
    project_revision = int(json.loads(body)["context"]["revision"])

    # Membership for the planner and viewer is provisioned in this isolated
    # schema; the project-admin surface is not the subject of this slice.
    seed = psycopg.connect(
        os.environ["CONSTRUCTION_PM_POSTGRES_DSN"],
        autocommit=True,
        options=f"-c search_path={ids['schema']}",
    )
    try:
        for key in ("planner", "viewer"):
            seed.execute(
                "INSERT INTO project_lifecycle_memberships "
                "(tenant_id, project_id, user_id) VALUES (%s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                (tenant, project, ids["users"][key].user_id),
            )
    finally:
        seed.close()

    cookie, csrf = login(runtime, "planner", PLANNER_PASSWORD)

    # 2. A durable working-week calendar defined through the product route.
    calendar_id, calendar_version = f"CAL-DD-{suffix}", "v1"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/calendars",
        body={
            "calendar_id": calendar_id,
            "calendar_version": calendar_version,
            "calendar_type": "project",
            "kind": "working-day",
            "name": "Data date calendar",
            "definition": {
                "system": "gregorian",
                "working_weekdays": [0, 1, 2, 3, 4],
            },
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    assert json.loads(body)["schedulable"] is True
    resource_calendar = f"CAL-DDR-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/calendars",
        body={
            "calendar_id": resource_calendar,
            "calendar_version": "v1",
            "calendar_type": "resource",
            "kind": "working-day",
            "name": "Data date crew calendar",
            "definition": {
                "system": "gregorian",
                "working_weekdays": [0, 1, 2, 3, 4],
            },
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body

    # 3. WBS and a three-activity chain A -> B -> C.
    root_wbs = f"root-dd-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/wbs",
        body={
            "wbs_id": root_wbs,
            "code": f"1-{suffix}",
            "name": "Project summary",
            "parent_kind": "project",
            "sequence_number": 1,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body

    wbs_id = f"wbs-dd-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/wbs",
        body={
            "wbs_id": wbs_id,
            "code": f"2-{suffix}",
            "name": "Structure",
            "parent_kind": "wbs",
            "parent_wbs_id": root_wbs,
            "sequence_number": 2,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body

    activity_a, activity_b, activity_c = (
        f"DD-A-{suffix}",
        f"DD-B-{suffix}",
        f"DD-C-{suffix}",
    )
    planned_durations = {activity_a: 3, activity_b: 2, activity_c: 2}
    for activity_id, duration, name in (
        (activity_a, 3, "Excavate"),
        (activity_b, 2, "Footings"),
        (activity_c, 2, "Backfill"),
    ):
        status, _, body = call(
            runtime,
            "POST",
            f"/api/projects/{project}/p6/activities",
            body={
                "activity_id": activity_id,
                "name": name,
                "duration_value": duration,
                "duration_unit": "working-day",
                "wbs_id": wbs_id,
            },
            cookie=cookie,
            csrf=csrf,
        )
        assert status == 201, body

    for index, (predecessor, successor) in enumerate(
        ((activity_a, activity_b), (activity_b, activity_c))
    ):
        status, _, body = call(
            runtime,
            "POST",
            f"/api/projects/{project}/p6/relationships",
            body={
                "relationship_id": f"REL-DD-{index}-{suffix}",
                "predecessor_id": predecessor,
                "successor_id": successor,
                "relationship_type": "FS",
                "lag_value": "0",
                "lag_unit": "working-day",
            },
            cookie=cookie,
            csrf=csrf,
        )
        assert status in {200, 201}, body

    # 4. A resource assignment on the not-started successor, proving progress
    #    and the resource surface coexist on the same project.
    resource_id = f"RES-DD-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/resources",
        body={
            "resource_id": resource_id,
            "name": "Civil crew",
            "resource_type": "labor",
            "calendar_id": resource_calendar,
            "default_units_per_time": "8",
            "unit_of_measure": "labor-unit",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    assignment_id = f"AS-DD-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/resource-assignments",
        body={
            "contract_version": "p6-resource-write-api.v1",
            "assignment_id": assignment_id,
            "activity_id": activity_c,
            "resource_id": resource_id,
            "units": "16",
            "unit": "labor-unit",
            "calendar_id": resource_calendar,
            "calendar_version": "v1",
            "units_per_time": "8",
            "units_per_time_period": "day",
            "hours_per_units_time_period": "8",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body

    # 5. Data Date stored in the project schedule settings.
    settings_payload = {
        "contract_version": "p6-project-schedule-settings-api.v1",
        "expected_record_revision": 0,
        "mode": "DATE_BASED",
        "project_calendar_id": calendar_id,
        "project_calendar_version": calendar_version,
        "project_calendar_system": "gregorian",
        "project_start": "2026-11-02",
        "project_finish": None,
        "schedule_options": _schedule_options_payload(
            ScheduleOptions(data_date=date(2026, 11, 16))
        ),
        "project_leveling_priority": 50,
    }
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/schedule/settings",
        body=settings_payload,
        cookie=cookie,
        csrf=csrf,
    )
    assert status in {200, 201}, body
    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/p6/schedule/settings",
        cookie=cookie,
    )
    assert status == 200, body
    stored_settings = json.loads(body)
    assert stored_settings["schedule_options"]["data_date"] == "2026-11-16"
    settings_revision = stored_settings["record_revision"]

    # 6. Actual Start / Actual Finish / percent / Remaining Duration, stored on
    #    the Activity Master with an immutable progress event.
    status, _, body = call(
        runtime,
        "PATCH",
        f"/api/projects/{project}/p6/activities/{activity_a}",
        body={
            "expected_revision": 1,
            "actual_start": "2026-11-02",
            "actual_finish": "2026-11-04",
            "percent_complete": 100.0,
            "remaining_duration": 0,
            "status": "Completed",
            "status_code": "Active",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    status, _, body = call(
        runtime,
        "PATCH",
        f"/api/projects/{project}/p6/activities/{activity_b}",
        body={
            "expected_revision": 1,
            "actual_start": "2026-11-05",
            "percent_complete": 40.0,
            "remaining_duration": 2,
            "status": "In Progress",
            "status_code": "Active",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    assert json.loads(body)["activity"]["percent_complete"] == 40.0

    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/p6/activities/{activity_b}/progress-history",
        cookie=cookie,
    )
    assert status == 200, body
    history = json.loads(body)
    assert [event["to_record_revision"] for event in history["events"]] == [2]
    assert history["percent_complete_trend"][-1]["percent_complete"] == "40.0"
    assert history["out_of_sequence_review"]["is_out_of_sequence"] is False

    # A stale revision must not overwrite or re-audit the stored progress.
    stale = psycopg.connect(
        os.environ["CONSTRUCTION_PM_POSTGRES_DSN"],
        autocommit=True,
        options=f"-c search_path={ids['schema']}",
    )
    try:
        stale_events = PostgresActivityProgressHistoryRepository(stale).list(
            BackendScope(tenant, project, project_revision), activity_b
        )
        assert len(stale_events) == 1
        assert stale_events[0].changes and any(
            change.field == "percent_complete" and change.after == "40.0"
            for change in stale_events[0].changes
        )
    finally:
        stale.close()

    status, _, body = call(
        runtime,
        "PATCH",
        f"/api/projects/{project}/p6/activities/{activity_b}",
        body={"expected_revision": 1, "percent_complete": 90.0},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "REVISION_CONFLICT"
    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/p6/activities/{activity_b}/progress-history",
        cookie=cookie,
    )
    assert len(json.loads(body)["events"]) == 1

    # 7. Re-run the shared scheduler with the stored Data Date and progress.
    status, _, body = call(runtime, "GET", "/api/projects", cookie=cookie)
    assert status == 200, body
    project_revision = int(
        next(
            item["revision"]
            for item in json.loads(body)["projects"]
            if item["project_id"] == project
        )
    )
    headers = {
        "X-Tenant-Id": tenant,
        "X-Project-Id": project,
        "X-Project-Revision": str(project_revision),
    }

    def publish_and_read():
        status, _, body = call(
            runtime,
            "POST",
            f"/api/projects/{project}/p6/schedule/snapshots",
            body={
                "contract_version": "p6-schedule-snapshot-api.v1",
                "timezone": "UTC",
            },
            cookie=cookie,
            csrf=csrf,
        )
        assert status in {200, 201}, body
        assert json.loads(body)["kind"] == "schedule_input_snapshot"
        status, _, body = call(
            runtime,
            "GET",
            "/api/v2/workspace/control-room/read",
            cookie=cookie,
            headers=headers,
        )
        assert status == 200, body
        workspace = json.loads(body)["workspace"]
        return (
            {item["id"]: item["cells"] for item in workspace["activities"]},
            {item["id"]: item["gantt"] for item in workspace["activities"]},
        )

    def save_settings(data_date):
        status, _, body = call(
            runtime,
            "GET",
            f"/api/projects/{project}/p6/schedule/settings",
            cookie=cookie,
        )
        assert status == 200, body
        revision = json.loads(body)["record_revision"]
        status, _, body = call(
            runtime,
            "POST",
            f"/api/projects/{project}/p6/schedule/settings",
            body={
                **settings_payload,
                "expected_record_revision": revision,
                "schedule_options": _schedule_options_payload(
                    ScheduleOptions(data_date=data_date)
                ),
            },
            cookie=cookie,
            csrf=csrf,
        )
        assert status in {200, 201}, body

    cells, gantt = publish_and_read()

    # An in-progress activity keeps its Actual Start; the Data Date bounds the
    # remaining work, so the forecast finish moves to the current period.
    assert cells[activity_b]["activity.early_start"] == "2026-11-05"
    assert gantt[activity_b]["start"] == "2026-11-05"
    assert gantt[activity_b]["progressPercent"] == 40
    assert cells[activity_b]["activity.early_finish"] >= "2026-11-16"
    assert gantt[activity_b]["finish"] == cells[activity_b]["activity.early_finish"]
    with_data_date_finish = cells[activity_b]["activity.early_finish"]

    # Scheduling the same progress facts without a Data Date finishes earlier:
    # the stored Data Date is the actual driver, not a label on the settings.
    save_settings(None)
    no_date_cells, _ = publish_and_read()
    assert no_date_cells[activity_b]["activity.early_start"] == "2026-11-05"
    assert (
        no_date_cells[activity_b]["activity.early_finish"]
        < with_data_date_finish
    )

    # Restoring the Data Date reproduces the identical forecast.
    save_settings(date(2026, 11, 16))
    cells, gantt = publish_and_read()
    assert cells[activity_b]["activity.early_finish"] == with_data_date_finish
    # The chain stays critical and the stored progress does not invent float.
    assert cells[activity_b]["activity.total_float"] == 0
    assert cells[activity_c]["activity.total_float"] == 0
    assert cells[activity_b]["activity.is_critical"] is True
    assert cells[activity_c]["activity.is_critical"] is True
    assert (
        cells[activity_b]["activity.early_finish"]
        <= cells[activity_c]["activity.early_start"]
    )
    # Planned Duration and baselines are untouched by progress recording.
    for activity_id, duration in planned_durations.items():
        assert cells[activity_id]["activity.planned_duration"] == str(duration)
        assert not any(key.startswith("activity.baseline") for key in cells[activity_id])

    # 8. A new session reads the same stored values and the same forecast.
    reload_cookie, _ = login(runtime, "planner", PLANNER_PASSWORD)
    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/p6/schedule/settings",
        cookie=reload_cookie,
    )
    assert status == 200, body
    assert json.loads(body)["schedule_options"]["data_date"] == "2026-11-16"
    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/p6/activities",
        cookie=reload_cookie,
    )
    assert status == 200, body
    stored = {
        item["activity"]["activity_id"]: item["activity"]
        for item in json.loads(body)["activities"]
    }
    assert stored[activity_a]["status"] == "Completed"
    assert stored[activity_a]["actual_finish"] == "2026-11-04"
    assert stored[activity_b]["percent_complete"] == 40.0
    assert stored[activity_b]["remaining_duration"] == 2
    assert stored[activity_b]["actual_start"] == "2026-11-05"
    for activity_id, duration in planned_durations.items():
        assert stored[activity_id]["duration_value"] == str(duration)
    status, _, body = call(
        runtime,
        "GET",
        "/api/v2/workspace/control-room/read",
        cookie=reload_cookie,
        headers=headers,
    )
    assert status == 200, body
    reloaded = {
        item["id"]: item["cells"]
        for item in json.loads(body)["workspace"]["activities"]
    }
    for activity_id in (activity_a, activity_b, activity_c):
        assert (
            reloaded[activity_id]["activity.planned_duration"]
            == cells[activity_id]["activity.planned_duration"]
        )
    assert (
        reloaded[activity_b]["activity.early_start"]
        == cells[activity_b]["activity.early_start"]
    )
    assert (
        reloaded[activity_b]["activity.total_float"]
        == cells[activity_b]["activity.total_float"]
    )

    # 9. Authorization: a viewer reads the stored progress but cannot write it;
    #    another tenant sees nothing.
    viewer_cookie, viewer_csrf = login(runtime, "viewer", VIEWER_PASSWORD)
    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/p6/activities/{activity_b}/progress-history",
        cookie=viewer_cookie,
    )
    assert status == 200, body
    assert json.loads(body)["events"]
    status, _, body = call(
        runtime,
        "PATCH",
        f"/api/projects/{project}/p6/activities/{activity_b}",
        body={"expected_revision": 2, "percent_complete": 60.0},
        cookie=viewer_cookie,
        csrf=viewer_csrf,
    )
    assert status == 403, body
    outsider_cookie, outsider_csrf = login(runtime, "outsider", ADMIN_PASSWORD)
    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/p6/activities/{activity_b}/progress-history",
        cookie=outsider_cookie,
    )
    assert status == 403, body
    status, _, body = call(
        runtime,
        "PATCH",
        f"/api/projects/{project}/p6/activities/{activity_b}",
        body={"expected_revision": 2, "percent_complete": 60.0},
        cookie=outsider_cookie,
        csrf=outsider_csrf,
    )
    assert status == 403, body

    # 10. The stored settings still carry the same record revision, so a stale
    #     editor cannot silently move the Data Date.
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/schedule/settings",
        body={
            **settings_payload,
            "expected_record_revision": settings_revision - 1,
            "schedule_options": _schedule_options_payload(
                ScheduleOptions(data_date=date(2026, 12, 1))
            ),
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "REVISION_CONFLICT"


def test_rescheduling_jobs_and_schedule_variance_are_operational_end_to_end(runtime):
    """Durable rescheduling and Schedule Variance over the production runtime.

    One independent project is driven through the real HTTP surface: a schedule
    snapshot is published, a durable job is submitted and stored, a real worker
    executes the one shared engine, the immutable result is read back by a new
    request and a new session, duplicate submission is single-flight, a second
    worker tick cannot recalculate a completed job, and viewer/tenant
    authorization is enforced. A baseline captured from published facts and the
    master Planned Duration must stay unchanged while progress and the Data
    Date move the forecast, and Tracking must report the resulting Schedule
    Variance from the same stored facts.
    """

    from datetime import date

    import psycopg

    from construction_pm.project_schedule_settings_repository import (
        _schedule_options_payload,
    )
    from construction_pm.scheduling.schedule_options import ScheduleOptions

    ids = runtime.test_ids
    suffix = uuid.uuid4().hex[:8]
    project = f"project-rsch-{suffix}"
    tenant = ids["tenant_a"]
    admin, admin_csrf = login(runtime, "admin", ADMIN_PASSWORD)

    # 1. Independent project and memberships for the planner and viewer.
    status, _, body = call(
        runtime,
        "POST",
        "/api/projects",
        body={
            "project_id": project,
            "name": f"Rescheduling acceptance {suffix}",
            "start_date": "2026-11-02",
        },
        cookie=admin,
        csrf=admin_csrf,
    )
    assert status == 201, body
    seed = psycopg.connect(
        os.environ["CONSTRUCTION_PM_POSTGRES_DSN"],
        autocommit=True,
        options=f"-c search_path={ids['schema']}",
    )
    try:
        for key in ("planner", "viewer"):
            seed.execute(
                "INSERT INTO project_lifecycle_memberships "
                "(tenant_id, project_id, user_id) VALUES (%s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                (tenant, project, ids["users"][key].user_id),
            )
    finally:
        seed.close()
    cookie, csrf = login(runtime, "planner", PLANNER_PASSWORD)

    def project_revision() -> int:
        status, _, body = call(runtime, "GET", "/api/projects", cookie=cookie)
        assert status == 200, body
        return int(
            next(
                item["revision"]
                for item in json.loads(body)["projects"]
                if item["project_id"] == project
            )
        )

    # 2. Durable working-week calendar, WBS and an FS chain with a stored
    #    planned finish that becomes the comparison plan.
    calendar_id, calendar_version = f"CAL-RSCH-{suffix}", "v1"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/calendars",
        body={
            "calendar_id": calendar_id,
            "calendar_version": calendar_version,
            "calendar_type": "project",
            "kind": "working-day",
            "name": "Rescheduling calendar",
            "definition": {
                "system": "gregorian",
                "working_weekdays": [0, 1, 2, 3, 4],
            },
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body

    root_wbs = f"root-rsch-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/wbs",
        body={
            "wbs_id": root_wbs,
            "code": f"1-{suffix}",
            "name": "Project summary",
            "parent_kind": "project",
            "sequence_number": 1,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body
    wbs_id = f"wbs-rsch-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/wbs",
        body={
            "wbs_id": wbs_id,
            "code": f"2-{suffix}",
            "name": "Structure",
            "parent_kind": "wbs",
            "parent_wbs_id": root_wbs,
            "sequence_number": 2,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body

    activity_a, activity_b = f"RSCH-A-{suffix}", f"RSCH-B-{suffix}"
    planned_durations = {activity_a: 4, activity_b: 3}
    planned_finish = {activity_a: "2026-11-10", activity_b: "2026-11-14"}
    for activity_id, duration, name in (
        (activity_a, 4, "Place concrete"),
        (activity_b, 3, "Cure and inspect"),
    ):
        status, _, body = call(
            runtime,
            "POST",
            f"/api/projects/{project}/p6/activities",
            body={
                "activity_id": activity_id,
                "name": name,
                "duration_value": duration,
                "duration_unit": "working-day",
                "wbs_id": wbs_id,
                "planned_finish": planned_finish[activity_id],
            },
            cookie=cookie,
            csrf=csrf,
        )
        assert status == 201, body
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/relationships",
        body={
            "relationship_id": f"REL-RSCH-{suffix}",
            "predecessor_id": activity_a,
            "successor_id": activity_b,
            "relationship_type": "FS",
            "lag_value": "0",
            "lag_unit": "working-day",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status in {200, 201}, body

    settings_payload = {
        "contract_version": "p6-project-schedule-settings-api.v1",
        "expected_record_revision": 0,
        "mode": "DATE_BASED",
        "project_calendar_id": calendar_id,
        "project_calendar_version": calendar_version,
        "project_calendar_system": "gregorian",
        "project_start": "2026-11-02",
        "project_finish": None,
        "schedule_options": _schedule_options_payload(
            ScheduleOptions(data_date=date(2026, 11, 16))
        ),
        "project_leveling_priority": 50,
    }
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/schedule/settings",
        body=settings_payload,
        cookie=cookie,
        csrf=csrf,
    )
    assert status in {200, 201}, body

    def publish_snapshot() -> str:
        status, _, body = call(
            runtime,
            "POST",
            f"/api/projects/{project}/p6/schedule/snapshots",
            body={
                "contract_version": "p6-schedule-snapshot-api.v1",
                "timezone": "UTC",
            },
            cookie=cookie,
            csrf=csrf,
        )
        assert status in {200, 201}, body
        payload = json.loads(body)
        assert payload["kind"] == "schedule_input_snapshot"
        return payload["snapshot_id"]

    def save_settings(data_date) -> None:
        status, _, body = call(
            runtime,
            "GET",
            f"/api/projects/{project}/p6/schedule/settings",
            cookie=cookie,
        )
        assert status == 200, body
        revision = json.loads(body)["record_revision"]
        status, _, body = call(
            runtime,
            "POST",
            f"/api/projects/{project}/p6/schedule/settings",
            body={
                **settings_payload,
                "expected_record_revision": revision,
                "schedule_options": _schedule_options_payload(
                    ScheduleOptions(data_date=data_date)
                ),
            },
            cookie=cookie,
            csrf=csrf,
        )
        assert status in {200, 201}, body

    def workspace_cells():
        headers = {
            "X-Tenant-Id": tenant,
            "X-Project-Id": project,
            "X-Project-Revision": str(project_revision()),
        }
        status, _, body = call(
            runtime,
            "GET",
            "/api/v2/workspace/control-room/read",
            cookie=cookie,
            headers=headers,
        )
        assert status == 200, body
        workspace = json.loads(body)["workspace"]
        return {item["id"]: item["cells"] for item in workspace["activities"]}

    def tracking_rows():
        status, _, body = call(
            runtime,
            "GET",
            f"/api/projects/{project}/tracking/read",
            cookie=cookie,
        )
        assert status == 200, body
        payload = json.loads(body)
        assert payload["contract_version"] == "tracking-read-model.v1"
        return {row["activity_id"]: row for row in payload["rows"]}

    snapshot_one = publish_snapshot()
    revision_one = project_revision()
    cells_before = workspace_cells()
    for activity_id, duration in planned_durations.items():
        assert cells_before[activity_id]["activity.planned_duration"] == str(duration)

    # 3. A durable job is submitted at the snapshot's own revision. The row is
    #    stored before any worker runs, and duplicate submission is single-flight.
    submit_path = f"/api/v1/schedule/projects/{project}/jobs"
    status, _, body = call(
        runtime,
        "POST",
        submit_path,
        body={"snapshot_id": snapshot_one},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 202, body
    submitted = json.loads(body)
    job_id = submitted["job_id"]
    assert submitted["state"] == "QUEUED"
    assert submitted["deduplicated"] is False

    status, _, body = call(
        runtime,
        "POST",
        submit_path,
        body={"snapshot_id": snapshot_one},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    duplicate = json.loads(body)
    assert duplicate["deduplicated"] is True
    assert duplicate["job_id"] == job_id

    stored_job = _db_rows(
        runtime,
        "SELECT state, attempts, revision, request_fingerprint, run_parameters_json "
        "FROM scheduling_jobs WHERE tenant_id=%s AND project_id=%s AND job_id=%s",
        (tenant, project, job_id),
    )
    assert len(stored_job) == 1
    assert stored_job[0][0] == "QUEUED"
    stored_parameters = json.loads(stored_job[0][4])
    assert stored_parameters["snapshot_id"] == snapshot_one
    assert stored_parameters["project_revision"] == str(revision_one)

    status, _, body = call(
        runtime,
        "GET",
        f"{submit_path}/{job_id}/result",
        cookie=cookie,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "SCHEDULING_JOB_NOT_SUCCEEDED"

    # 4. The real worker claims and executes the job on the shared engine.
    tick_headers = {"X-Worker-Token": SCHEDULING_WORKER_TOKEN}
    status, _, body = call(
        runtime, "POST", "/api/v1/schedule/worker/tick", body={}, headers=tick_headers
    )
    assert status == 200, body
    outcome = json.loads(body)
    assert outcome["outcome"]["claimed"] == 1
    assert outcome["outcome"]["succeeded"] == 1

    status, _, body = call(
        runtime, "GET", f"{submit_path}/{job_id}", cookie=cookie
    )
    assert status == 200, body
    status_view = json.loads(body)
    assert status_view["state"] == "SUCCEEDED"
    assert status_view["revision"] >= 2
    completed_revision = status_view["revision"]

    status, _, body = call(
        runtime, "GET", f"{submit_path}/{job_id}/result", cookie=cookie
    )
    assert status == 200, body
    result_view = json.loads(body)
    output_hash = result_view["result"]["output_hash"]
    assert len(output_hash) == 64
    assert result_view["result"]["payload"]["activity_count"] == 2

    stored = _db_rows(
        runtime,
        "SELECT state, attempts, revision FROM scheduling_jobs "
        "WHERE tenant_id=%s AND project_id=%s AND job_id=%s",
        (tenant, project, job_id),
    )
    assert stored == [("SUCCEEDED", 1, completed_revision)]
    stored_results = _db_rows(
        runtime,
        "SELECT engine_version, calculation_identity, output_hash "
        "FROM scheduling_job_results "
        "WHERE tenant_id=%s AND project_id=%s AND job_id=%s",
        (tenant, project, job_id),
    )
    assert stored_results == [
        (
            status_view["engine_version"],
            status_view["calculation_identity"],
            output_hash,
        )
    ]

    # A second tick has nothing to claim, so the same run is never recalculated.
    status, _, body = call(
        runtime, "POST", "/api/v1/schedule/worker/tick", body={}, headers=tick_headers
    )
    assert status == 200, body
    assert json.loads(body)["outcome"]["claimed"] == 0
    assert json.loads(body)["outcome"]["succeeded"] == 0

    # A new request and a new session retrieve the identical immutable result.
    reload_cookie, _ = login(runtime, "planner", PLANNER_PASSWORD)
    status, _, body = call(
        runtime, "GET", f"{submit_path}/{job_id}/result", cookie=reload_cookie
    )
    assert status == 200, body
    assert json.loads(body)["result"]["output_hash"] == output_hash

    # A completed run is a new generation, never a silently reused result.
    status, _, body = call(
        runtime,
        "POST",
        submit_path,
        body={"snapshot_id": snapshot_one},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 202, body
    second_generation = json.loads(body)
    assert second_generation["job_id"] != job_id
    status, _, body = call(
        runtime,
        "POST",
        f"{submit_path}/{second_generation['job_id']}/cancel",
        body={},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    assert json.loads(body)["state"] == "CANCELLED"

    # 5. A baseline captured from the published facts is an immutable stored
    #    window; its rows must not move when progress is recorded.
    baseline_id = f"BL-RSCH-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/baselines/capture",
        body={
            "contract_version": "p6-baseline-capture-api.v1",
            "baseline_id": baseline_id,
            "name": "Approved plan",
            "baseline_type": "USER_SELECTED",
            "expected_revision": revision_one,
            "currency": "USD",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body
    captured = json.loads(body)
    assert captured["kind"] == "p6_baseline_capture"
    assert captured["counts"]["activities"] == 2
    assert captured["baseline"]["baseline_id"] == baseline_id

    status, _, body = call(
        runtime, "GET", f"/api/projects/{project}/p6/baselines", cookie=cookie
    )
    assert status == 200, body
    assert [
        item["baseline"]["baseline_id"] for item in json.loads(body)["baselines"]
    ] == [baseline_id]
    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/p6/baselines/{baseline_id}/activities",
        cookie=cookie,
    )
    assert status == 200, body
    baseline_windows = {
        item["activity_id"]: (item["planned_start"], item["planned_finish"])
        for item in json.loads(body)["activities"]
    }
    assert baseline_windows == {
        activity_a: ("2026-11-02", "2026-11-05"),
        activity_b: ("2026-11-06", "2026-11-10"),
    }
    baseline_hash_query = (
        "SELECT activity_id, planned_start, planned_finish, budgeted_cost, "
        "currency, wbs_id, earned_value_technique FROM p6_baseline_activity "
        "WHERE tenant_id=%s AND project_id=%s AND baseline_id=%s "
        "ORDER BY activity_id"
    )
    baseline_before = _db_rows(
        runtime, baseline_hash_query, (tenant, project, baseline_id)
    )

    # 6. Progress moves the forecast, but Planned Duration and the stored
    #    baseline rows stay untouched.
    status, _, body = call(
        runtime,
        "PATCH",
        f"/api/projects/{project}/p6/activities/{activity_a}",
        body={
            "expected_revision": 1,
            "actual_start": "2026-11-10",
            "percent_complete": 60.0,
            "remaining_duration": 2,
            "status": "In Progress",
            "status_code": "Active",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body

    publish_snapshot()
    cells_with_date = workspace_cells()
    rows_with_date = tracking_rows()
    assert (
        cells_with_date[activity_a]["activity.planned_duration"]
        == str(planned_durations[activity_a])
    )
    assert (
        cells_with_date[activity_b]["activity.planned_duration"]
        == str(planned_durations[activity_b])
    )

    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/p6/activities/{activity_a}",
        cookie=cookie,
    )
    assert status == 200, body
    progressed = json.loads(body)["activity"]
    assert progressed["percent_complete"] == 60.0
    assert progressed["status"] == "In Progress"
    assert progressed["actual_start"] == "2026-11-10"
    assert progressed["planned_finish"] == planned_finish[activity_a]

    tracked_a = rows_with_date[activity_a]
    assert tracked_a["planned_finish"] == planned_finish[activity_a]
    assert tracked_a["finish"] >= "2026-11-16"
    variance_with_date = tracked_a["finish_variance_days"]
    assert variance_with_date == (
        date.fromisoformat(tracked_a["finish"])
        - date.fromisoformat(planned_finish[activity_a])
    ).days
    assert variance_with_date > 0
    finish_with_date = tracked_a["finish"]

    # 7. The stored Data Date is the actual driver of the variance: without it
    #    the same progress finishes earlier and the Schedule Variance shrinks;
    #    restoring it reproduces the identical forecast and variance.
    save_settings(None)
    publish_snapshot()
    rows_without_date = tracking_rows()
    assert rows_without_date[activity_a]["finish"] < finish_with_date
    assert rows_without_date[activity_a]["finish_variance_days"] < variance_with_date

    save_settings(date(2026, 11, 16))
    publish_snapshot()
    rows_restored = tracking_rows()
    assert rows_restored[activity_a]["finish"] == finish_with_date
    assert rows_restored[activity_a]["finish_variance_days"] == variance_with_date

    # Planned Duration and the master planned finish never move; the baseline
    # rows captured before progress are byte-for-byte the same facts.
    cells_after = workspace_cells()
    for activity_id, duration in planned_durations.items():
        assert cells_after[activity_id]["activity.planned_duration"] == str(duration)
    status, _, body = call(
        runtime, "GET", f"/api/projects/{project}/p6/activities", cookie=cookie
    )
    assert status == 200, body
    masters = {
        item["activity"]["activity_id"]: item["activity"]
        for item in json.loads(body)["activities"]
    }
    for activity_id, duration in planned_durations.items():
        assert masters[activity_id]["duration_value"] == str(duration)
        assert masters[activity_id]["planned_finish"] == planned_finish[activity_id]
    baseline_after = _db_rows(
        runtime, baseline_hash_query, (tenant, project, baseline_id)
    )
    assert baseline_after == baseline_before

    # 8. Authorization: a viewer can read status and result but cannot submit or
    #    cancel; another tenant cannot see the run at all.
    viewer_cookie, viewer_csrf = login(runtime, "viewer", VIEWER_PASSWORD)
    status, _, body = call(
        runtime, "GET", f"{submit_path}/{job_id}", cookie=viewer_cookie
    )
    assert status == 200, body
    status, _, body = call(
        runtime, "GET", f"{submit_path}/{job_id}/result", cookie=viewer_cookie
    )
    assert status == 200, body
    assert json.loads(body)["result"]["output_hash"] == output_hash
    status, _, body = call(
        runtime,
        "POST",
        submit_path,
        body={"snapshot_id": snapshot_one},
        cookie=viewer_cookie,
        csrf=viewer_csrf,
    )
    assert status == 403, body
    assert json.loads(body)["code"] == "AUTHORIZATION_PERMISSION_DENIED"
    status, _, body = call(
        runtime,
        "POST",
        f"{submit_path}/{job_id}/cancel",
        body={},
        cookie=viewer_cookie,
        csrf=viewer_csrf,
    )
    assert status == 403, body

    outsider_cookie, _ = login(runtime, "outsider", ADMIN_PASSWORD)
    status, _, body = call(
        runtime, "GET", f"{submit_path}/{job_id}", cookie=outsider_cookie
    )
    assert status == 403, body
    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/p6/baselines",
        cookie=outsider_cookie,
    )
    assert status == 403, body


# ---------------------------------------------------------------------------
# Costs: the expense register and its rollup into the immutable baseline
# ---------------------------------------------------------------------------


def test_expenses_are_operational_and_roll_into_the_baseline(runtime):
    """Cost facts are durable, authorized and captured into Schedule Variance.

    One independent project is driven through the real HTTP surface: a schedule
    is published, activity- and WBS-linked expenses are recorded and read back
    in a new session, an identical replay is idempotent, a changed replay is a
    conflict, and baseline capture rolls the activity-linked planned cost into
    the immutable baseline window while a WBS-only expense is reported as
    unattributed instead of silently disappearing. Viewer and tenant
    authorization is enforced, and cost never moves the schedule.
    """

    from construction_pm.project_schedule_settings_repository import (
        _schedule_options_payload,
    )
    from construction_pm.scheduling.schedule_options import ScheduleOptions

    ids = runtime.test_ids
    suffix = uuid.uuid4().hex[:8]
    project = f"project-cost-{suffix}"
    tenant = ids["tenant_a"]
    admin, admin_csrf = login(runtime, "admin", ADMIN_PASSWORD)

    status, _, body = call(
        runtime,
        "POST",
        "/api/projects",
        body={
            "project_id": project,
            "name": f"Cost acceptance {suffix}",
            "start_date": "2026-11-02",
        },
        cookie=admin,
        csrf=admin_csrf,
    )
    assert status == 201, body
    import psycopg

    seed = psycopg.connect(
        os.environ["CONSTRUCTION_PM_POSTGRES_DSN"],
        autocommit=True,
        options=f"-c search_path={ids['schema']}",
    )
    try:
        for key in ("planner", "viewer"):
            seed.execute(
                "INSERT INTO project_lifecycle_memberships "
                "(tenant_id, project_id, user_id) VALUES (%s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                (tenant, project, ids["users"][key].user_id),
            )
    finally:
        seed.close()
    cookie, csrf = login(runtime, "planner", PLANNER_PASSWORD)

    def project_revision() -> int:
        status, _, body = call(runtime, "GET", "/api/projects", cookie=cookie)
        assert status == 200, body
        return int(
            next(
                item["revision"]
                for item in json.loads(body)["projects"]
                if item["project_id"] == project
            )
        )

    calendar_id, calendar_version = f"CAL-COST-{suffix}", "v1"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/calendars",
        body={
            "calendar_id": calendar_id,
            "calendar_version": calendar_version,
            "calendar_type": "project",
            "kind": "working-day",
            "name": "Cost calendar",
            "definition": {
                "system": "gregorian",
                "working_weekdays": [0, 1, 2, 3, 4],
            },
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body

    root_wbs = f"root-cost-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/wbs",
        body={
            "wbs_id": root_wbs,
            "code": f"1-{suffix}",
            "name": "Project summary",
            "parent_kind": "project",
            "sequence_number": 1,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body
    wbs_id = f"wbs-cost-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/wbs",
        body={
            "wbs_id": wbs_id,
            "code": f"2-{suffix}",
            "name": "Structure",
            "parent_kind": "wbs",
            "parent_wbs_id": root_wbs,
            "sequence_number": 2,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body

    activity_id = f"COST-A-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/activities",
        body={
            "activity_id": activity_id,
            "name": "Place concrete",
            "duration_value": 3,
            "duration_unit": "working-day",
            "wbs_id": wbs_id,
            "planned_finish": "2026-11-04",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/schedule/settings",
        body={
            "contract_version": "p6-project-schedule-settings-api.v1",
            "expected_record_revision": 0,
            "mode": "DATE_BASED",
            "project_calendar_id": calendar_id,
            "project_calendar_version": calendar_version,
            "project_calendar_system": "gregorian",
            "project_start": "2026-11-02",
            "project_finish": None,
            "schedule_options": _schedule_options_payload(
                ScheduleOptions(data_date=None)
            ),
            "project_leveling_priority": 50,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status in {200, 201}, body

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/schedule/snapshots",
        body={
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status in {200, 201}, body

    # 1. The register starts empty and is readable without a body.
    status, _, body = call(
        runtime, "GET", f"/api/projects/{project}/p6/expenses", cookie=cookie
    )
    assert status == 200, body
    assert json.loads(body)["expenses"] == []

    revision = project_revision()
    expense_a = f"EXP-A-{suffix}"
    expense_w = f"EXP-W-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/expenses",
        body={
            "expense_id": expense_a,
            "name": "Concrete supply",
            "category": "MATERIAL",
            "activity_id": activity_id,
            "expense_date": "2026-11-03",
            "planned_cost": "1500.25",
            "actual_cost": "0",
            "remaining_cost": "1500.25",
            "currency": "USD",
            "note": "activity-linked budget",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    stored_expense = json.loads(body)["expense"]
    assert stored_expense["expense_id"] == expense_a
    assert stored_expense["planned_cost"] == "1500.25"
    assert stored_expense["activity_id"] == activity_id

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/expenses",
        body={
            "expense_id": expense_w,
            "name": "Site overhead",
            "category": "OVERHEAD",
            "wbs_id": root_wbs,
            "planned_cost": "100",
            "currency": "USD",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body

    # 2. Filters are query parameters, not a request body.
    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/p6/expenses",
        cookie=cookie,
        query=f"activity_id={activity_id}",
    )
    assert status == 200, body
    assert [
        item["expense"]["expense_id"] for item in json.loads(body)["expenses"]
    ] == [expense_a]
    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/p6/expenses",
        cookie=cookie,
        query=f"wbs_id={root_wbs}",
    )
    assert status == 200, body
    assert [
        item["expense"]["expense_id"] for item in json.loads(body)["expenses"]
    ] == [expense_w]

    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/p6/expenses/{expense_a}",
        cookie=cookie,
    )
    assert status == 200, body
    assert json.loads(body)["expense"]["actual_cost"] == "0"

    # A new session reads the identical stored cost facts.
    reload_cookie, _ = login(runtime, "planner", PLANNER_PASSWORD)
    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/p6/expenses/{expense_a}",
        cookie=reload_cookie,
    )
    assert status == 200, body
    assert json.loads(body)["expense"]["remaining_cost"] == "1500.25"

    # 3. An identical replay is idempotent; a changed payload is a conflict.
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/expenses",
        body={
            "expense_id": expense_a,
            "name": "Concrete supply",
            "category": "MATERIAL",
            "activity_id": activity_id,
            "expense_date": "2026-11-03",
            "planned_cost": "1500.25",
            "actual_cost": "0",
            "remaining_cost": "1500.25",
            "currency": "USD",
            "note": "activity-linked budget",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/expenses",
        body={
            "expense_id": expense_a,
            "name": "Changed after the fact",
            "category": "MATERIAL",
            "activity_id": activity_id,
            "planned_cost": "9999",
            "currency": "USD",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "IMMUTABLE_EXPENSE"

    stored_rows = _db_rows(
        runtime,
        "SELECT expense_id, activity_id, wbs_id, planned_cost, actual_cost, "
        "remaining_cost, currency, project_revision FROM p6_expense "
        "WHERE tenant_id=%s AND project_id=%s ORDER BY expense_id",
        (tenant, project),
    )
    assert stored_rows == [
        (expense_a, activity_id, None, "1500.25", "0", "1500.25", "USD", revision),
        (expense_w, None, root_wbs, "100", None, None, "USD", revision),
    ]

    # 4. Baseline capture rolls the activity-linked planned cost into the
    #    immutable window and reports the WBS-only expense as unattributed.
    baseline_id = f"BL-COST-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/baselines/capture",
        body={
            "contract_version": "p6-baseline-capture-api.v1",
            "baseline_id": baseline_id,
            "name": "Costed plan",
            "baseline_type": "USER_SELECTED",
            "expected_revision": revision,
            "currency": "USD",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body
    captured = json.loads(body)
    assert captured["counts"]["activities"] == 1
    assert captured["counts"]["budgeted_cost"] == "1500.25"
    assert captured["unattributed_expense_ids"] == [expense_w]

    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/p6/baselines/{baseline_id}/activities",
        cookie=cookie,
    )
    assert status == 200, body
    rows = {item["activity_id"]: item for item in json.loads(body)["activities"]}
    assert rows[activity_id]["budgeted_cost"] == "1500.25"
    assert rows[activity_id]["currency"] == "USD"

    # Cost is not schedule: planned duration and planned finish are untouched.
    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/p6/activities/{activity_id}",
        cookie=cookie,
    )
    assert status == 200, body
    master = json.loads(body)["activity"]
    assert master["duration_value"] == "3"
    assert master["planned_finish"] == "2026-11-04"

    # 5. Authorization: a viewer reads cost but cannot record it; another
    #    tenant sees nothing and cannot write.
    viewer_cookie, viewer_csrf = login(runtime, "viewer", VIEWER_PASSWORD)
    status, _, body = call(
        runtime, "GET", f"/api/projects/{project}/p6/expenses", cookie=viewer_cookie
    )
    assert status == 200, body
    assert len(json.loads(body)["expenses"]) == 2
    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/p6/expenses/{expense_a}",
        cookie=viewer_cookie,
    )
    assert status == 200, body
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/expenses",
        body={
            "expense_id": f"EXP-V-{suffix}",
            "name": "Viewer attempt",
            "category": "OTHER",
            "planned_cost": "1",
            "currency": "USD",
        },
        cookie=viewer_cookie,
        csrf=viewer_csrf,
    )
    assert status == 403, body
    assert json.loads(body)["code"] == "AUTHORIZATION_PERMISSION_DENIED"

    outsider_cookie, outsider_csrf = login(runtime, "outsider", ADMIN_PASSWORD)
    status, _, body = call(
        runtime,
        "GET",
        f"/api/projects/{project}/p6/expenses",
        cookie=outsider_cookie,
    )
    assert status == 403, body
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/expenses",
        body={
            "expense_id": f"EXP-O-{suffix}",
            "name": "Outsider attempt",
            "category": "OTHER",
        },
        cookie=outsider_cookie,
        csrf=outsider_csrf,
    )
    assert status == 403, body

    final_rows = _db_rows(
        runtime,
        "SELECT expense_id FROM p6_expense WHERE tenant_id=%s AND project_id=%s "
        "ORDER BY expense_id",
        (tenant, project),
    )
    assert final_rows == [(expense_a,), (expense_w,)]


# ---------------------------------------------------------------------------
# Budget integration: the register, its derived summary and the threshold source
# ---------------------------------------------------------------------------


def test_budget_register_is_operational_end_to_end(runtime):
    """Original budget, changes, funding and the derived summary over PostgreSQL.

    The production runtime now serves the budget register through
    ``PostgresBudgetStore``. This test drives the real HTTP surface: line
    creation is idempotent, updates are revision-guarded, a pending change is
    visible but not counted, approval is admin-only and moves the current
    budget, funding is stored separately, the summary derives the balance, the
    audit history is ordered, and a ``budget_balance`` threshold observes the
    same stored rows.
    """

    ids = runtime.test_ids
    suffix = uuid.uuid4().hex[:8]
    project = f"project-budget-{suffix}"
    tenant = ids["tenant_a"]
    admin, admin_csrf = login(runtime, "admin", ADMIN_PASSWORD)

    status, _, body = call(
        runtime,
        "POST",
        "/api/projects",
        body={
            "project_id": project,
            "name": f"Budget acceptance {suffix}",
            "start_date": "2026-11-02",
        },
        cookie=admin,
        csrf=admin_csrf,
    )
    assert status == 201, body
    import psycopg

    seed = psycopg.connect(
        os.environ["CONSTRUCTION_PM_POSTGRES_DSN"],
        autocommit=True,
        options=f"-c search_path={ids['schema']}",
    )
    try:
        for key in ("admin", "planner", "viewer"):
            seed.execute(
                "INSERT INTO project_lifecycle_memberships "
                "(tenant_id, project_id, user_id) VALUES (%s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                (tenant, project, ids["users"][key].user_id),
            )
    finally:
        seed.close()
    cookie, csrf = login(runtime, "planner", PLANNER_PASSWORD)

    base = f"/api/projects/{project}/budget"
    line_body = {
        "budget_line_id": "BL-1",
        "description": "Civil works",
        "currency": "USD",
        "original_amount": "1000.00",
        "cost_account_id": "CA-1",
        "period_id": "FY26",
    }

    # 1. Create is idempotent under the request header and a fresh session can
    #    read the stored line.
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/lines",
        body=line_body,
        cookie=cookie,
        csrf=csrf,
        headers={"Idempotency-Key": "line-1"},
    )
    assert status == 200, body
    created = json.loads(body)
    assert created["budget_line_id"] == "BL-1"
    assert created["original_amount"] == "1000.00"
    assert created["revision"] == 1
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/lines",
        body=line_body,
        cookie=cookie,
        csrf=csrf,
        headers={"Idempotency-Key": "line-1"},
    )
    assert status == 200, body
    assert json.loads(body)["revision"] == 1

    # A different payload under the same idempotency key is a conflict.
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/lines",
        body={**line_body, "original_amount": "2000.00"},
        cookie=cookie,
        csrf=csrf,
        headers={"Idempotency-Key": "line-1"},
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "BUDGET_IDEMPOTENCY_KEY_REUSE"

    reload_cookie, _ = login(runtime, "planner", PLANNER_PASSWORD)
    status, _, body = call(
        runtime, "GET", f"{base}/lines/BL-1", cookie=reload_cookie
    )
    assert status == 200, body
    assert json.loads(body)["original_amount"] == "1000.00"

    status, _, body = call(
        runtime, "GET", f"{base}/lines", cookie=cookie, query="currency=USD&search=civil"
    )
    assert status == 200, body
    assert [item["budget_line_id"] for item in json.loads(body)["budget_lines"]] == ["BL-1"]
    status, _, body = call(
        runtime, "GET", f"{base}/lines", cookie=cookie, query="currency=EUR"
    )
    assert status == 200, body
    assert json.loads(body)["budget_lines"] == []

    # 2. Updates are revision-guarded.
    status, _, body = call(
        runtime,
        "PATCH",
        f"{base}/lines/BL-1",
        body={
            **line_body,
            "original_amount": "1200.00",
            "expected_revision": 1,
            "reason": "approved re-estimate",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    assert json.loads(body)["revision"] == 2
    status, _, body = call(
        runtime,
        "PATCH",
        f"{base}/lines/BL-1",
        body={**line_body, "original_amount": "1300.00", "expected_revision": 1},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "BUDGET_REVISION_CONFLICT"

    # 3. A pending change is visible but not counted; approval is admin-only.
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/lines/BL-1/changes",
        body={
            "change_id": "CH-1",
            "amount": "250.00",
            "reason": "scope increase",
            "status": "pending",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    assert json.loads(body)["status"] == "pending"
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/lines/BL-1/changes",
        body={
            "change_id": "CH-2",
            "amount": "100.00",
            "reason": "unapproved extra",
            "status": "pending",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body

    status, _, body = call(
        runtime,
        "GET",
        f"{base}/summary",
        cookie=cookie,
    )
    assert status == 200, body
    summary = json.loads(body)["currencies"]
    assert len(summary) == 1
    assert summary[0]["original_budget"] == "1200.00"
    assert summary[0]["approved_changes"] == "0.00"
    assert summary[0]["current_budget"] == "1200.00"
    assert summary[0]["pending_changes"] == "350.00"

    status, _, body = call(
        runtime,
        "POST",
        f"{base}/changes/CH-1/status",
        body={"status": "approved", "expected_revision": 1},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 403, body
    assert json.loads(body)["code"] == "BUDGET_APPROVAL_REQUIRES_ADMIN"

    status, _, body = call(
        runtime,
        "POST",
        f"{base}/changes/CH-1/status",
        body={"status": "approved", "expected_revision": 1, "reason": "owner approved"},
        cookie=admin,
        csrf=admin_csrf,
    )
    assert status == 200, body
    approved = json.loads(body)
    assert approved["status"] == "approved"
    assert approved["revision"] == 2

    # 4. Funding is stored separately and the summary derives the balance.
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/funding",
        body={
            "funding_id": "FD-1",
            "name": "Owner capital",
            "source_type": "internal",
            "currency": "USD",
            "amount": "500.00",
            "period_id": "FY26",
        },
        cookie=cookie,
        csrf=csrf,
        headers={"Idempotency-Key": "funding-1"},
    )
    assert status == 200, body
    assert json.loads(body)["amount"] == "500.00"
    status, _, body = call(
        runtime,
        "PATCH",
        f"{base}/funding/FD-1",
        body={
            "name": "Owner capital",
            "source_type": "internal",
            "currency": "USD",
            "amount": "700.00",
            "period_id": "FY26",
            "expected_revision": 1,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    assert json.loads(body)["revision"] == 2

    status, _, body = call(runtime, "GET", f"{base}/summary", cookie=cookie)
    assert status == 200, body
    summary = json.loads(body)["currencies"][0]
    assert summary["original_budget"] == "1200.00"
    assert summary["approved_changes"] == "250.00"
    assert summary["current_budget"] == "1450.00"
    assert summary["pending_changes"] == "100.00"
    assert summary["funding"] == "700.00"
    assert summary["funding_balance"] == "750.00"

    # 5. The audit trail is ordered and the rows are stored in PostgreSQL.
    status, _, body = call(runtime, "GET", f"{base}/lines/BL-1/history", cookie=cookie)
    assert status == 200, body
    events = json.loads(body)["events"]
    assert [event["event_type"] for event in events] == ["created", "updated"]
    assert [event["revision"] for event in events] == [1, 2]
    assert all(event["occurred_at"] for event in events)
    status, _, body = call(runtime, "GET", f"{base}/lines/BL-1/changes", cookie=cookie)
    assert status == 200, body
    assert [
        (item["change_id"], item["status"], item["revision"])
        for item in json.loads(body)["changes"]
    ] == [("CH-1", "approved", 2), ("CH-2", "pending", 1)]
    stored = _db_rows(
        runtime,
        "SELECT budget_line_id, revision FROM project_budget_line "
        "WHERE tenant_id=%s AND project_id=%s",
        (tenant, project),
    )
    assert stored == [("BL-1", 2)]

    # 6. A budget_balance threshold observes the same stored rows.
    threshold_id = f"THR-BUD-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/thresholds",
        body={
            "threshold_id": threshold_id,
            "name": "Budget balance ceiling",
            "monitoring_subject": "cost",
            "parameter": "budget_balance",
            "currency": "USD",
            "lower_threshold": None,
            "upper_threshold": "1000.00",
            "warning_level": "2",
            "issue_level": "3",
            "responsible_manager": "Planner",
            "status": "active",
        },
        cookie=admin,
        csrf=admin_csrf,
        headers={"Idempotency-Key": f"thr-{threshold_id}"},
    )
    assert status == 200, body
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/thresholds/{threshold_id}/monitor",
        body={},
        cookie=admin,
        csrf=admin_csrf,
        headers={"Idempotency-Key": f"monitor-{threshold_id}"},
    )
    assert status == 200, body
    run = json.loads(body)["run"]
    assert run["observed_value"] == "750"
    assert run["level"] == "normal"

    # 7. Authorization: viewers read, cannot write; another tenant sees nothing.
    viewer_cookie, viewer_csrf = login(runtime, "viewer", VIEWER_PASSWORD)
    status, _, body = call(runtime, "GET", f"{base}/lines", cookie=viewer_cookie)
    assert status == 200, body
    status, _, body = call(runtime, "GET", f"{base}/summary", cookie=viewer_cookie)
    assert status == 200, body
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/lines",
        body={**line_body, "budget_line_id": "BL-V"},
        cookie=viewer_cookie,
        csrf=viewer_csrf,
        headers={"Idempotency-Key": "viewer-line"},
    )
    assert status == 403, body
    assert json.loads(body)["code"] == "BUDGET_PERMISSION_DENIED"

    outsider_cookie, _ = login(runtime, "outsider", ADMIN_PASSWORD)
    status, _, body = call(runtime, "GET", f"{base}/lines", cookie=outsider_cookie)
    assert status == 403, body
    assert _db_rows(
        runtime,
        "SELECT budget_line_id FROM project_budget_line "
        "WHERE tenant_id=%s AND project_id=%s",
        (tenant, project),
    ) == [("BL-1",)]


# ---------------------------------------------------------------------------
# Reports: the stored register, immutable runs and the EVM measurement
# ---------------------------------------------------------------------------


def test_reports_and_earned_value_are_operational_end_to_end(runtime):
    """Stored reports, schedules and earned value over real PostgreSQL facts.

    One independent project is driven through the production WSGI surface. A
    report definition is stored, replayed idempotently, run into an immutable
    snapshot and read back by a fresh session, filtered by a bound parameter and
    exported from the stored run only. A schedule is created, updated with a
    revision guard and recorded in history. The same project's captured
    baseline is then measured through the versioned EVM route, which must read
    planned value, progress and cost from persisted rows and leave the immutable
    baseline untouched. Viewer and cross-tenant access are enforced throughout.
    """

    import psycopg

    from construction_pm.project_schedule_settings_repository import (
        _schedule_options_payload,
    )
    from construction_pm.scheduling.schedule_options import ScheduleOptions

    ids = runtime.test_ids
    suffix = uuid.uuid4().hex[:8]
    project = f"project-rep-{suffix}"
    tenant = ids["tenant_a"]
    admin, admin_csrf = login(runtime, "admin", ADMIN_PASSWORD)

    # 1. Independent project with planner and viewer memberships.
    status, _, body = call(
        runtime,
        "POST",
        "/api/projects",
        body={
            "project_id": project,
            "name": f"Reports acceptance {suffix}",
            "start_date": "2026-11-02",
        },
        cookie=admin,
        csrf=admin_csrf,
    )
    assert status == 201, body
    seed = psycopg.connect(
        os.environ["CONSTRUCTION_PM_POSTGRES_DSN"],
        autocommit=True,
        options=f"-c search_path={ids['schema']}",
    )
    try:
        for key in ("planner", "viewer"):
            seed.execute(
                "INSERT INTO project_lifecycle_memberships "
                "(tenant_id, project_id, user_id) VALUES (%s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                (tenant, project, ids["users"][key].user_id),
            )
    finally:
        seed.close()
    cookie, csrf = login(runtime, "planner", PLANNER_PASSWORD)

    def project_revision() -> int:
        status, _, body = call(runtime, "GET", "/api/projects", cookie=cookie)
        assert status == 200, body
        return int(
            next(
                item["revision"]
                for item in json.loads(body)["projects"]
                if item["project_id"] == project
            )
        )

    # 2. Durable calendar, WBS, activity and schedule settings.
    calendar_id, calendar_version = f"CAL-REP-{suffix}", "v1"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/calendars",
        body={
            "calendar_id": calendar_id,
            "calendar_version": calendar_version,
            "calendar_type": "project",
            "kind": "working-day",
            "name": "Reporting calendar",
            "definition": {
                "system": "gregorian",
                "working_weekdays": [0, 1, 2, 3, 4],
            },
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body

    root_wbs = f"root-rep-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/wbs",
        body={
            "wbs_id": root_wbs,
            "code": f"1-{suffix}",
            "name": "Project summary",
            "parent_kind": "project",
            "sequence_number": 1,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body
    wbs_id = f"wbs-rep-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/wbs",
        body={
            "wbs_id": wbs_id,
            "code": f"2-{suffix}",
            "name": "Construction",
            "parent_kind": "wbs",
            "parent_wbs_id": root_wbs,
            "sequence_number": 2,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body

    activity_id = f"REP-A-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/activities",
        body={
            "activity_id": activity_id,
            "name": "Place concrete",
            "duration_value": 3,
            "duration_unit": "working-day",
            "wbs_id": wbs_id,
            "planned_finish": "2026-11-04",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body

    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/schedule/settings",
        body={
            "contract_version": "p6-project-schedule-settings-api.v1",
            "expected_record_revision": 0,
            "mode": "DATE_BASED",
            "project_calendar_id": calendar_id,
            "project_calendar_version": calendar_version,
            "project_calendar_system": "gregorian",
            "project_start": "2026-11-02",
            "project_finish": None,
            "schedule_options": _schedule_options_payload(
                ScheduleOptions(data_date=None)
            ),
            "project_leveling_priority": 50,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status in {200, 201}, body
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/schedule/snapshots",
        body={
            "contract_version": "p6-schedule-snapshot-api.v1",
            "timezone": "UTC",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status in {200, 201}, body

    # 3. A costed plan captured as an immutable baseline window.
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/expenses",
        body={
            "expense_id": f"EXP-{suffix}",
            "name": "Concrete supply",
            "category": "MATERIAL",
            "activity_id": activity_id,
            "expense_date": "2026-11-03",
            "planned_cost": "1000",
            "actual_cost": "0",
            "remaining_cost": "1000",
            "currency": "USD",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body

    baseline_id = f"BL-REP-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/baselines/capture",
        body={
            "contract_version": "p6-baseline-capture-api.v1",
            "baseline_id": baseline_id,
            "name": "Approved plan",
            "baseline_type": "USER_SELECTED",
            "expected_revision": project_revision(),
            "currency": "USD",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body
    captured = json.loads(body)
    assert captured["counts"]["activities"] == 1
    assert float(captured["counts"]["budgeted_cost"]) == 1000.0
    baseline_query = (
        "SELECT activity_id, planned_start, planned_finish, budgeted_cost, "
        "currency FROM p6_baseline_activity "
        "WHERE tenant_id=%s AND project_id=%s AND baseline_id=%s "
        "ORDER BY activity_id"
    )
    baseline_before = _db_rows(
        runtime, baseline_query, (tenant, project, baseline_id)
    )
    assert baseline_before == [
        (activity_id, "2026-11-02", "2026-11-04", "1000", "USD")
    ]

    # 4. Progress is recorded on the current activity without touching the
    #    stored baseline window.
    status, _, body = call(
        runtime,
        "PATCH",
        f"/api/projects/{project}/p6/activities/{activity_id}",
        body={
            "expected_revision": 1,
            "actual_start": "2026-11-02",
            "percent_complete": 40.0,
            "remaining_duration": 2,
            "status": "In Progress",
            "status_code": "Active",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body

    # 5. The report catalogue is served from the shared definition.
    base = f"/api/projects/{project}/reports"
    status, _, body = call(runtime, "GET", f"{base}/catalogue", cookie=cookie)
    assert status == 200, body
    catalogue = json.loads(body)
    subjects = {item["subject"] for item in catalogue["subjects"]}
    assert subjects == {"activities", "resources", "risks"}
    assert "csv" in catalogue["export_formats"]

    # 6. A definition is stored once and a replay returns the same revision.
    report_id = "REP-1"
    definition_body = {
        "report_id": report_id,
        "name": "Activity status",
        "description": "Current stored progress",
        "subject": "activities",
        "columns": ["activity_id", "name", "status", "percent_complete"],
        "parameters": [
            {"key": "status", "required": False, "default": "In Progress"}
        ],
    }
    status, _, body = call(
        runtime,
        "POST",
        base,
        body=definition_body,
        cookie=cookie,
        csrf=csrf,
        headers={"Idempotency-Key": f"rep-def-{suffix}"},
    )
    assert status == 200, body
    created = json.loads(body)
    assert created["report_id"] == report_id
    assert created["record_revision"] == 1
    assert created["parameters"][0]["default"] == "In Progress"

    status, _, body = call(
        runtime,
        "POST",
        base,
        body=definition_body,
        cookie=cookie,
        csrf=csrf,
        headers={"Idempotency-Key": f"rep-def-{suffix}"},
    )
    assert status == 200, body
    assert json.loads(body)["record_revision"] == 1

    status, _, body = call(
        runtime,
        "POST",
        base,
        body={**definition_body, "name": "Different shape"},
        cookie=cookie,
        csrf=csrf,
        headers={"Idempotency-Key": f"rep-def-{suffix}"},
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "REPORT_IDEMPOTENCY_KEY_REUSE"

    status, _, body = call(
        runtime,
        "GET",
        base,
        cookie=cookie,
        query="subject=activities&search=Activity",
    )
    assert status == 200, body
    listed = json.loads(body)["reports"]
    assert [item["report_id"] for item in listed] == [report_id]
    status, _, body = call(runtime, "GET", f"{base}/{report_id}", cookie=cookie)
    assert status == 200, body
    assert json.loads(body)["columns"] == [
        "activity_id",
        "name",
        "status",
        "percent_complete",
    ]
    status, _, body = call(
        runtime, "GET", f"{base}/{report_id}/history", cookie=cookie
    )
    assert status == 200, body
    assert [item["event_type"] for item in json.loads(body)["events"]] == [
        "created"
    ]

    # 7. A run materializes the bound default from stored facts, and an
    #    explicit parameter overrides it for the same stored definition.
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/{report_id}/run",
        body={},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    run = json.loads(body)
    run_id = run["run_id"]
    assert run["row_count"] == 1
    assert run["rows"] == [
        {
            "activity_id": activity_id,
            "name": "Place concrete",
            "status": "In Progress",
            "percent_complete": 40.0,
        }
    ]
    assert run["parameters"] == {"status": "In Progress"}
    assert run["parameter_sources"] == {"status": "default"}

    status, _, body = call(
        runtime,
        "POST",
        f"{base}/{report_id}/run",
        body={"parameters": {"status": "Not Started"}},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    empty = json.loads(body)
    assert empty["row_count"] == 0
    assert empty["parameter_sources"] == {"status": "explicit"}

    status, _, body = call(
        runtime, "GET", f"{base}/{report_id}/runs", cookie=cookie
    )
    assert status == 200, body
    stored_runs = json.loads(body)["runs"]
    assert len(stored_runs) == 2
    assert {item["run_id"] for item in stored_runs} == {run_id, empty["run_id"]}

    # 8. A new session retrieves the stored run, and the export is rendered
    #    from that snapshot only.
    fresh_cookie, _ = login(runtime, "planner", PLANNER_PASSWORD)
    status, _, body = call(
        runtime,
        "GET",
        f"{base}/{report_id}/runs/{run_id}",
        cookie=fresh_cookie,
    )
    assert status == 200, body
    assert json.loads(body)["rows"] == run["rows"]
    status, headers, body = call(
        runtime,
        "GET",
        f"{base}/{report_id}/runs/{run_id}/export",
        cookie=fresh_cookie,
        query="format=csv",
    )
    assert status == 200, body
    assert headers["x-content-sha256"][0]
    assert activity_id in body.decode("utf-8")

    # 9. A schedule is stored, updated under a revision guard and audited.
    schedule_body = {
        "schedule_id": "SCH-1",
        "cadence": "daily",
        "run_time": "09:00",
        "timezone": "UTC",
        "project_revision": project_revision(),
        "export_format": "csv",
        "locale": "en",
        "parameters": {"status": "In Progress"},
        "enabled": True,
    }
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/{report_id}/schedules",
        body=schedule_body,
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    schedule = json.loads(body)
    assert schedule["schedule_id"] == "SCH-1"
    assert schedule["revision"] == 1
    assert schedule["next_run_at"]

    status, _, body = call(
        runtime,
        "PUT",
        f"{base}/{report_id}/schedules/SCH-1",
        body={
            **schedule_body,
            "run_time": "10:00",
            "expected_revision": 1,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    updated = json.loads(body)
    assert updated["revision"] == 2
    assert updated["run_time"] == "10:00"

    status, _, body = call(
        runtime,
        "PUT",
        f"{base}/{report_id}/schedules/SCH-1",
        body={
            **schedule_body,
            "run_time": "11:00",
            "expected_revision": 1,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "REPORT_SCHEDULE_REVISION_CONFLICT"

    status, _, body = call(
        runtime,
        "GET",
        f"{base}/{report_id}/schedules",
        cookie=cookie,
    )
    assert status == 200, body
    assert [
        item["schedule_id"] for item in json.loads(body)["schedules"]
    ] == ["SCH-1"]
    status, _, body = call(
        runtime,
        "GET",
        f"{base}/{report_id}/schedules/SCH-1",
        cookie=cookie,
    )
    assert status == 200, body
    assert json.loads(body)["revision"] == 2
    status, _, body = call(
        runtime,
        "GET",
        f"{base}/{report_id}/schedules/SCH-1/history",
        cookie=cookie,
    )
    assert status == 200, body
    assert [item["event_type"] for item in json.loads(body)["events"]] == [
        "created",
        "updated",
    ]

    # 10. The earned-value route measures the captured baseline from persisted
    #     planned value, current progress and stored cost.
    evm_path = f"/api/projects/{project}/p6/earned-value"
    evm_body = {
        "contract_version": "p6-earned-value-read-model.v1",
        "baseline_id": baseline_id,
        "data_date": "2026-11-10",
        "currency": "USD",
    }
    status, _, body = call(
        runtime, "POST", evm_path, body=evm_body, cookie=cookie, csrf=csrf
    )
    assert status == 200, body
    measurement = json.loads(body)
    assert measurement["kind"] == "p6_earned_value_read_model"
    assert measurement["baseline_id"] == baseline_id
    assert measurement["data_date"] == "2026-11-10"
    assert measurement["currency"] == "USD"
    earned = measurement["earned_value"]
    assert float(earned["budget_at_completion"]) == 1000.0
    assert float(earned["planned_value"]) == 1000.0
    assert float(earned["earned_value"]) == 400.0
    assert float(earned["actual_cost"]) == 0.0

    status, _, body = call(
        runtime,
        "POST",
        evm_path,
        body={**evm_body, "client_value": "999"},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 400, body
    assert json.loads(body)["code"] == "EVM_REQUEST_UNKNOWN_FIELD"

    status, _, body = call(
        runtime,
        "POST",
        evm_path,
        body={**evm_body, "data_date": "2026-11-20"},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    assert json.loads(body)["data_date"] == "2026-11-20"

    # 11. Authorization: a viewer reads reports, runs and the measurement but
    #     cannot write; another tenant sees nothing.
    viewer_cookie, viewer_csrf = login(runtime, "viewer", VIEWER_PASSWORD)
    status, _, body = call(runtime, "GET", base, cookie=viewer_cookie)
    assert status == 200, body
    status, _, body = call(
        runtime, "GET", f"{base}/{report_id}/runs/{run_id}", cookie=viewer_cookie
    )
    assert status == 200, body
    status, _, body = call(
        runtime, "POST", evm_path, body=evm_body, cookie=viewer_cookie, csrf=viewer_csrf
    )
    assert status == 200, body
    status, _, body = call(
        runtime,
        "POST",
        base,
        body={**definition_body, "report_id": "REP-V"},
        cookie=viewer_cookie,
        csrf=viewer_csrf,
        headers={"Idempotency-Key": "viewer-report"},
    )
    assert status == 403, body
    assert json.loads(body)["code"] == "REPORT_PERMISSION_DENIED"
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/{report_id}/schedules",
        body={**schedule_body, "schedule_id": "SCH-V"},
        cookie=viewer_cookie,
        csrf=viewer_csrf,
    )
    assert status == 403, body
    assert json.loads(body)["code"] == "REPORT_SCHEDULE_PERMISSION_DENIED"

    outsider_cookie, _ = login(runtime, "outsider", ADMIN_PASSWORD)
    status, _, body = call(runtime, "GET", base, cookie=outsider_cookie)
    assert status == 403, body
    status, _, body = call(
        runtime, "POST", evm_path, body=evm_body, cookie=outsider_cookie
    )
    assert status == 403, body

    # 12. Every stored row belongs to this tenant/project, and the baseline has
    #     not moved while the measurement and exports were produced.
    assert _db_rows(
        runtime,
        "SELECT report_id, revision FROM project_report_definition "
        "WHERE tenant_id=%s AND project_id=%s",
        (tenant, project),
    ) == [(report_id, 1)]
    assert _db_rows(
        runtime,
        "SELECT report_id, generated_by FROM project_report_run "
        "WHERE tenant_id=%s AND project_id=%s ORDER BY generated_at, run_id",
        (tenant, project),
    ) == [
        (report_id, ids["users"]["planner"].user_id),
        (report_id, ids["users"]["planner"].user_id),
    ]
    assert _db_rows(
        runtime,
        "SELECT schedule_id, cadence, enabled FROM project_report_schedule "
        "WHERE tenant_id=%s AND project_id=%s",
        (tenant, project),
    ) == [("SCH-1", "daily", 1)]
    assert _db_rows(
        runtime, baseline_query, (tenant, project, baseline_id)
    ) == baseline_before


# ---------------------------------------------------------------------------
# P0-M: project closeout and reopening over stored facts
# ---------------------------------------------------------------------------


def test_project_closeout_and_reopening_are_durable_over_postgres(runtime):
    """Closing is a guarded lifecycle operation, not a status edit.

    The project used here is created inside this test so its issue register is
    deterministic; every closeout request still travels through the production
    WSGI composition, and every assertion reads PostgreSQL back.
    """

    ids = runtime.test_ids
    tenant = ids["tenant_a"]
    project = f"closeout-{ids['suffix']}"
    base = f"/api/projects/{project}/closeout"
    admin_cookie, admin_csrf = login(runtime, "admin", ADMIN_PASSWORD)
    planner_cookie, planner_csrf = login(runtime, "planner", PLANNER_PASSWORD)
    viewer_cookie, _viewer_csrf = login(runtime, "viewer", VIEWER_PASSWORD)
    outsider_cookie, outsider_csrf = login(runtime, "outsider", ADMIN_PASSWORD)
    admin_id = ids["users"]["admin"].user_id

    connection = runtime.pool.acquire()
    try:
        connection.execute(
            "INSERT INTO project_lifecycle_projects "
            "(tenant_id, project_id, name) VALUES (%s, %s, %s)",
            (tenant, project, "Closeout Project"),
        )
        for key in ("admin", "planner", "viewer"):
            connection.execute(
                "INSERT INTO project_lifecycle_memberships "
                "(tenant_id, project_id, user_id) VALUES (%s, %s, %s)",
                (tenant, project, ids["users"][key].user_id),
            )
        connection.commit()
    finally:
        runtime.pool.release(connection, healthy=True)

    # 1. A project with no closeout row reads as open at revision zero.
    status, _, body = call(runtime, "GET", base, cookie=admin_cookie)
    assert status == 200, body
    payload = json.loads(body)
    assert payload["contract_version"] == "project-closeout.v1"
    assert payload["closeout"] == {
        "project_id": project,
        "state": "open",
        "record_revision": 0,
        "closed_at": None,
        "closed_by": "",
        "note": "",
        "open_issue_count": 0,
        "updated_at": None,
    }
    status, _, body = call(runtime, "GET", f"{base}/history", cookie=viewer_cookie)
    assert status == 200, body
    assert json.loads(body)["events"] == []

    # 2. Read is open to a viewer; only a project administrator may close.
    status, _, body = call(runtime, "GET", base, cookie=viewer_cookie)
    assert status == 200, body
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/close",
        body={"expected_revision": 0, "note": "planner attempt"},
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 403, body
    assert json.loads(body)["code"] == "CLOSEOUT_PERMISSION_DENIED"
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/close",
        body={"expected_revision": 0},
        cookie=outsider_cookie,
        csrf=outsider_csrf,
    )
    assert status == 403, body

    # 3. An open issue blocks closeout, and nothing is written.
    issue_base = f"/api/projects/{project}/p6/issues"
    issue_one = f"ISS-CLOSEOUT-1-{ids['suffix']}"
    status, _, body = call(
        runtime,
        "POST",
        issue_base,
        body=_issue_payload(issue_one),
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 200, body
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/close",
        body={"expected_revision": 0, "note": "attempt with open issue"},
        cookie=admin_cookie,
        csrf=admin_csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "CLOSEOUT_OPEN_ISSUES:1"
    assert _db_rows(
        runtime,
        "SELECT COUNT(*) FROM project_closeout WHERE tenant_id=%s AND project_id=%s",
        (tenant, project),
    ) == [(0,)]

    # 4. Once the issue is resolved, closeout succeeds with revision one.
    status, _, body = call(
        runtime,
        "PATCH",
        f"{issue_base}/{issue_one}",
        body=_issue_payload(
            issue_one,
            status="resolved",
            resolution_note="Facade delivered",
            expected_revision=1,
        ),
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 200, body
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/close",
        body={"expected_revision": 0, "note": "all issues resolved"},
        cookie=admin_cookie,
        csrf=admin_csrf,
    )
    assert status == 200, body
    closed = json.loads(body)["closeout"]
    assert closed["state"] == "closed"
    assert closed["record_revision"] == 1
    assert closed["closed_by"] == admin_id
    assert closed["closed_at"] is not None
    assert closed["note"] == "all issues resolved"
    assert closed["open_issue_count"] == 0

    # 5. A repeated close is an idempotent no-op, even with a stale revision,
    #    and it does not append a second event.
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/close",
        body={"expected_revision": 7},
        cookie=admin_cookie,
        csrf=admin_csrf,
    )
    assert status == 200, body
    assert json.loads(body)["closeout"]["record_revision"] == 1
    assert _db_rows(
        runtime,
        "SELECT COUNT(*) FROM project_closeout_event "
        "WHERE tenant_id=%s AND project_id=%s",
        (tenant, project),
    ) == [(1,)]

    # 6. Reopening moves to revision two and clears the closed fields.
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/reopen",
        body={"expected_revision": 1, "note": "punch list rework"},
        cookie=admin_cookie,
        csrf=admin_csrf,
    )
    assert status == 200, body
    reopened = json.loads(body)["closeout"]
    assert reopened["state"] == "open"
    assert reopened["record_revision"] == 2
    assert reopened["closed_at"] is None and reopened["closed_by"] == ""
    assert reopened["note"] == "punch list rework"
    # A repeated reopen is also an idempotent no-op.
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/reopen",
        body={"expected_revision": 0},
        cookie=admin_cookie,
        csrf=admin_csrf,
    )
    assert status == 200, body
    assert json.loads(body)["closeout"]["record_revision"] == 2

    # 7. Re-closing a reopened project with an open issue is blocked again.
    issue_two = f"ISS-CLOSEOUT-2-{ids['suffix']}"
    status, _, body = call(
        runtime,
        "POST",
        issue_base,
        body=_issue_payload(issue_two, title="Second open issue"),
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 200, body
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/close",
        body={"expected_revision": 2},
        cookie=admin_cookie,
        csrf=admin_csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "CLOSEOUT_OPEN_ISSUES:1"
    status, _, body = call(
        runtime,
        "PATCH",
        f"{issue_base}/{issue_two}",
        body=_issue_payload(
            issue_two,
            title="Second open issue",
            status="closed",
            resolution_note="Verified on site",
            expected_revision=1,
        ),
        cookie=planner_cookie,
        csrf=planner_csrf,
    )
    assert status == 200, body
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/close",
        body={"expected_revision": 2, "note": "second close"},
        cookie=admin_cookie,
        csrf=admin_csrf,
    )
    assert status == 200, body
    assert json.loads(body)["closeout"]["record_revision"] == 3

    # 8. A stale revision against a real state change is a conflict.
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/reopen",
        body={"expected_revision": 1},
        cookie=admin_cookie,
        csrf=admin_csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "CLOSEOUT_REVISION_CONFLICT"
    assert _db_rows(
        runtime,
        "SELECT state, record_revision FROM project_closeout "
        "WHERE tenant_id=%s AND project_id=%s",
        (tenant, project),
    ) == [("closed", 3)]

    # 9. Malformed bodies and unknown subpaths fail closed without writing.
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/close",
        body={},
        cookie=admin_cookie,
        csrf=admin_csrf,
    )
    assert status == 400, body
    assert json.loads(body)["code"] == "CLOSEOUT_REQUEST_INVALID"
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/close",
        body={"expected_revision": True},
        cookie=admin_cookie,
        csrf=admin_csrf,
    )
    assert status == 400, body
    status, _, body = call(
        runtime, "GET", f"{base}/unknown", cookie=admin_cookie
    )
    assert status == 400, body
    assert json.loads(body)["code"] == "CLOSEOUT_REQUEST_INVALID"

    # 10. Reopen once more so the ledger ends open, then read the full history.
    status, _, body = call(
        runtime,
        "POST",
        f"{base}/reopen",
        body={"expected_revision": 3, "note": "final reopen"},
        cookie=admin_cookie,
        csrf=admin_csrf,
    )
    assert status == 200, body
    assert json.loads(body)["closeout"]["record_revision"] == 4
    status, _, body = call(runtime, "GET", f"{base}/history", cookie=viewer_cookie)
    assert status == 200, body
    events = json.loads(body)["events"]
    assert [(item["record_revision"], item["action"]) for item in events] == [
        (1, "closed"),
        (2, "reopened"),
        (3, "closed"),
        (4, "reopened"),
    ]
    assert all(item["actor_id"] == admin_id for item in events)
    assert [item["note"] for item in events] == [
        "all issues resolved",
        "punch list rework",
        "second close",
        "final reopen",
    ]

    # 11. The stored rows are exact, and the V26 status field never moved:
    #     closeout is its own fact, not an alias of project status.
    assert _db_rows(
        runtime,
        "SELECT state, record_revision, closed_by, note, open_issue_count "
        "FROM project_closeout WHERE tenant_id=%s AND project_id=%s",
        (tenant, project),
    ) == [("open", 4, "", "final reopen", 0)]
    assert _db_rows(
        runtime,
        "SELECT event_id, action, record_revision, actor_id "
        "FROM project_closeout_event WHERE tenant_id=%s AND project_id=%s "
        "ORDER BY record_revision",
        (tenant, project),
    ) == [
        ("closed-1", "closed", 1, admin_id),
        ("reopened-2", "reopened", 2, admin_id),
        ("closed-3", "closed", 3, admin_id),
        ("reopened-4", "reopened", 4, admin_id),
    ]
    assert _db_rows(
        runtime,
        "SELECT status, revision FROM project_lifecycle_projects "
        "WHERE tenant_id=%s AND project_id=%s",
        (tenant, project),
    ) == [("active", 0)]

    # 12. Cross-tenant history stays invisible.
    status, _, body = call(
        runtime, "GET", f"{base}/history", cookie=outsider_cookie
    )
    assert status == 403, body
