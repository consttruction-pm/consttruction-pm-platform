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
        assert first.ledger_version == 17
        assert len(first.applied) == 17
        assert first.already_applied == ()
        assert first.table_count == 98
        assert first.drift is None

        second = apply_migrations(connection)
        assert second.applied == ()
        assert second.already_applied == tuple(range(1, 18))
        assert second.drift is None
        assert second.table_count == 98

        rows = connection.execute(
            f"SELECT version, name, checksum, step_revision, runtime_version "
            f"FROM {LEDGER_TABLE} ORDER BY version"
        ).fetchall()
        assert [row[0] for row in rows] == list(range(1, 18))
        assert all(row[2] and row[3] >= 1 and row[4] == 17 for row in rows)

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
    assert readiness["schema"]["version"] == 17
    assert readiness["schema"]["tables"] == 98


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
