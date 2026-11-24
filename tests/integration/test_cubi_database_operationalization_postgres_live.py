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
        assert first.ledger_version == 16
        assert len(first.applied) == 16
        assert first.already_applied == ()
        assert first.table_count == 95
        assert first.drift is None

        second = apply_migrations(connection)
        assert second.applied == ()
        assert second.already_applied == tuple(range(1, 17))
        assert second.drift is None
        assert second.table_count == 95

        rows = connection.execute(
            f"SELECT version, name, checksum, step_revision, runtime_version "
            f"FROM {LEDGER_TABLE} ORDER BY version"
        ).fetchall()
        assert [row[0] for row in rows] == list(range(1, 17))
        assert all(row[2] and row[3] >= 1 and row[4] == 16 for row in rows)

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
    assert readiness["schema"]["version"] == 16
    assert readiness["schema"]["tables"] == 95


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
    assert status == 200, body
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

