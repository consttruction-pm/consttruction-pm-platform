"""Integrated engineering acceptance over the production runtime.

One project is driven through the whole recovered engineering chain on an
isolated PostgreSQL schema and the same WSGI application ``api/index.py``
exposes: identity and project lifecycle, calendar/WBS/activities, Data Date and
progress, durable rescheduling, Schedule Variance, costs, budget integration,
stored reports and earned value, and project closeout.

The purpose is not to re-test each slice's internals but to prove that the
surfaces agree with each other in one live project: progress moves the forecast
without moving the baseline or Planned Duration, rescheduling keeps its
immutable result, earned value reads the captured baseline rather than the
budget register, closeout is gated by the same issue facts the issue API writes,
and every cross-tenant or read-only request fails closed.

Run with::

    CONSTRUCTION_PM_POSTGRES_DSN=postgresql://... \
        PYTHONPATH=src python -m pytest -q \
        tests/integration/test_engineering_acceptance_postgres_live.py
"""

from __future__ import annotations

import io
import json
import os
import uuid
from datetime import date
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

if not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN") and os.getenv("P6_TEST_POSTGRES_DSN"):
    os.environ["CONSTRUCTION_PM_POSTGRES_DSN"] = os.getenv("P6_TEST_POSTGRES_DSN")

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)

ORIGIN = "https://cubi.example.test"
SECRET = "engineering-acceptance-session-secret-0123456789"
ADMIN_PASSWORD = "acceptance admin horse battery staple"
PLANNER_PASSWORD = "acceptance planner horse battery staple"
VIEWER_PASSWORD = "acceptance viewer horse battery staple"
WORKER_TOKEN = "acceptance-worker-token-0123456789"
WEB_ROOT = Path(__file__).resolve().parents[2] / "apps" / "web"


def _schema_name() -> str:
    return f"cubi_accept_{uuid.uuid4().hex[:12]}"


@pytest.fixture(scope="module")
def runtime() -> ProductionRuntime:
    import psycopg

    schema = _schema_name()
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
        scheduling_worker_token=WORKER_TOKEN,
    )
    instance = ProductionRuntime(settings)
    instance._initialize()

    suffix = uuid.uuid4().hex[:10]
    tenant_a = f"tenant-accept-a-{suffix}"
    tenant_b = f"tenant-accept-b-{suffix}"
    users = {
        "admin": IdentityUser(
            user_id=f"user-accept-admin-{suffix}",
            tenant_id=tenant_a,
            email=f"accept-admin-{suffix}@example.test",
            display_name="Acceptance Admin",
            roles=frozenset({"project_admin", "enterprise_admin"}),
            password_hash=hash_password(ADMIN_PASSWORD),
        ),
        "planner": IdentityUser(
            user_id=f"user-accept-planner-{suffix}",
            tenant_id=tenant_a,
            email=f"accept-planner-{suffix}@example.test",
            display_name="Acceptance Planner",
            roles=frozenset({"planner", "enterprise_user"}),
            password_hash=hash_password(PLANNER_PASSWORD),
        ),
        "viewer": IdentityUser(
            user_id=f"user-accept-viewer-{suffix}",
            tenant_id=tenant_a,
            email=f"accept-viewer-{suffix}@example.test",
            display_name="Acceptance Viewer",
            roles=frozenset({"viewer", "enterprise_viewer"}),
            password_hash=hash_password(VIEWER_PASSWORD),
        ),
        "outsider": IdentityUser(
            user_id=f"user-accept-outsider-{suffix}",
            tenant_id=tenant_b,
            email=f"accept-outsider-{suffix}@example.test",
            display_name="Other Tenant",
            roles=frozenset({"project_admin", "enterprise_admin"}),
            password_hash=hash_password(ADMIN_PASSWORD),
        ),
    }
    connection = instance.pool.acquire()
    try:
        store = PostgresIdentityStore(connection)
        for user in users.values():
            store.upsert_user(user)
        connection.commit()
    finally:
        instance.pool.release(connection, healthy=True)

    instance.test_ids = {  # type: ignore[attr-defined]
        "schema": schema,
        "users": users,
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "suffix": suffix,
        "client_ip": f"2001:db8:acc::{suffix}",
    }
    yield instance
    instance.close()
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
    environ["HTTP_X_FORWARDED_FOR"] = runtime.test_ids["client_ip"]
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


def test_integrated_engineering_acceptance_end_to_end(runtime):
    from construction_pm.project_schedule_settings_repository import (
        _schedule_options_payload,
    )
    from construction_pm.scheduling.schedule_options import ScheduleOptions

    ids = runtime.test_ids
    tenant = ids["tenant_a"]
    suffix = uuid.uuid4().hex[:8]
    project = f"project-accept-{suffix}"
    admin, admin_csrf = login(runtime, "admin", ADMIN_PASSWORD)

    # -- 1. Identity, membership and project lifecycle --------------------
    status, _, body = call(
        runtime,
        "POST",
        "/api/projects",
        body={
            "project_id": project,
            "name": f"Integrated acceptance {suffix}",
            "start_date": "2026-11-02",
        },
        cookie=admin,
        csrf=admin_csrf,
    )
    assert status == 201, body
    seed_connection = runtime.pool.acquire()
    try:
        for key in ("planner", "viewer"):
            seed_connection.execute(
                "INSERT INTO project_lifecycle_memberships "
                "(tenant_id, project_id, user_id) VALUES (%s, %s, %s) "
                "ON CONFLICT DO NOTHING",
                (tenant, project, ids["users"][key].user_id),
            )
        seed_connection.commit()
    finally:
        runtime.pool.release(seed_connection, healthy=True)
    cookie, csrf = login(runtime, "planner", PLANNER_PASSWORD)
    viewer_cookie, viewer_csrf = login(runtime, "viewer", VIEWER_PASSWORD)
    outsider_cookie, outsider_csrf = login(runtime, "outsider", ADMIN_PASSWORD)

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

    # -- 2. Calendar, WBS, an FS chain and one stored Data Date -----------
    calendar_id, calendar_version = f"CAL-ACC-{suffix}", "v1"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/calendars",
        body={
            "calendar_id": calendar_id,
            "calendar_version": calendar_version,
            "calendar_type": "project",
            "kind": "working-day",
            "name": "Acceptance calendar",
            "definition": {"system": "gregorian", "working_weekdays": [0, 1, 2, 3, 4]},
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body

    root_wbs = f"root-acc-{suffix}"
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
    wbs_id = f"wbs-acc-{suffix}"
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

    activity_a, activity_b = f"ACC-A-{suffix}", f"ACC-B-{suffix}"
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
            "relationship_id": f"REL-ACC-{suffix}",
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
            body={"contract_version": "p6-schedule-snapshot-api.v1", "timezone": "UTC"},
            cookie=cookie,
            csrf=csrf,
        )
        assert status in {200, 201}, body
        payload = json.loads(body)
        assert payload["kind"] == "schedule_input_snapshot"
        return payload["snapshot_id"]

    def save_data_date(data_date) -> None:
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

    def tracking_rows():
        status, _, body = call(
            runtime, "GET", f"/api/projects/{project}/tracking/read", cookie=cookie
        )
        assert status == 200, body
        payload = json.loads(body)
        assert payload["contract_version"] == "tracking-read-model.v1"
        return {row["activity_id"]: row for row in payload["rows"]}

    def workspace_cells():
        status, _, body = call(
            runtime,
            "GET",
            "/api/v2/workspace/control-room/read",
            cookie=cookie,
            headers={
                "X-Tenant-Id": tenant,
                "X-Project-Id": project,
                "X-Project-Revision": str(project_revision()),
            },
        )
        assert status == 200, body
        workspace = json.loads(body)["workspace"]
        return {item["id"]: item["cells"] for item in workspace["activities"]}

    snapshot_id = publish_snapshot()
    for activity_id, duration in planned_durations.items():
        assert workspace_cells()[activity_id]["activity.planned_duration"] == str(
            duration
        )

    # -- 3. Durable rescheduling on the shared engine ---------------------
    submit_path = f"/api/v1/schedule/projects/{project}/jobs"
    status, _, body = call(
        runtime,
        "POST",
        submit_path,
        body={"snapshot_id": snapshot_id},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 202, body
    job_id = json.loads(body)["job_id"]
    status, _, body = call(
        runtime, "POST", "/api/v1/schedule/worker/tick", body={},
        headers={"X-Worker-Token": WORKER_TOKEN},
    )
    assert status == 200, body
    assert json.loads(body)["outcome"]["succeeded"] == 1
    status, _, body = call(runtime, "GET", f"{submit_path}/{job_id}/result", cookie=cookie)
    assert status == 200, body
    result = json.loads(body)["result"]
    output_hash = result["output_hash"]
    assert len(output_hash) == 64
    assert result["payload"]["activity_count"] == 2
    status, _, body = call(
        runtime, "POST", "/api/v1/schedule/worker/tick", body={},
        headers={"X-Worker-Token": WORKER_TOKEN},
    )
    assert status == 200, body
    assert json.loads(body)["outcome"]["claimed"] == 0

    # -- 4. Costed plan captured as the immutable comparison window ------
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/expenses",
        body={
            "expense_id": f"EXP-ACC-{suffix}",
            "name": "Concrete supply",
            "category": "MATERIAL",
            "activity_id": activity_a,
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

    baseline_id = f"BL-ACC-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        f"/api/projects/{project}/p6/baselines/capture",
        body={
            "contract_version": "p6-baseline-capture-api.v1",
            "baseline_id": baseline_id,
            "name": "Approved acceptance plan",
            "baseline_type": "USER_SELECTED",
            "expected_revision": project_revision(),
            "currency": "USD",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 201, body
    assert json.loads(body)["counts"]["activities"] == 2
    assert float(json.loads(body)["counts"]["budgeted_cost"]) == 1000.0
    baseline_query = (
        "SELECT activity_id, planned_start, planned_finish, budgeted_cost, currency "
        "FROM p6_baseline_activity "
        "WHERE tenant_id=%s AND project_id=%s AND baseline_id=%s ORDER BY activity_id"
    )
    baseline_before = _db_rows(runtime, baseline_query, (tenant, project, baseline_id))
    assert baseline_before == [
        (activity_a, "2026-11-02", "2026-11-05", "1000", "USD"),
        (activity_b, "2026-11-06", "2026-11-10", "0", "USD"),
    ]

    # -- 5. Progress and the stored Data Date drive the forecast ---------
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
    rows_with_date = tracking_rows()
    variance = rows_with_date[activity_a]["finish_variance_days"]
    assert variance == (
        date.fromisoformat(rows_with_date[activity_a]["finish"])
        - date.fromisoformat(planned_finish[activity_a])
    ).days
    assert variance > 0

    save_data_date(None)
    publish_snapshot()
    rows_without_date = tracking_rows()
    assert rows_without_date[activity_a]["finish_variance_days"] < variance
    save_data_date(date(2026, 11, 16))
    publish_snapshot()
    assert tracking_rows()[activity_a]["finish_variance_days"] == variance

    for activity_id, duration in planned_durations.items():
        assert workspace_cells()[activity_id]["activity.planned_duration"] == str(duration)
    masters = {
        item["activity"]["activity_id"]: item["activity"]
        for item in json.loads(
            call(runtime, "GET", f"/api/projects/{project}/p6/activities", cookie=cookie)[2]
        )["activities"]
    }
    for activity_id, duration in planned_durations.items():
        assert masters[activity_id]["duration_value"] == str(duration)
        assert masters[activity_id]["planned_finish"] == planned_finish[activity_id]
    assert _db_rows(runtime, baseline_query, (tenant, project, baseline_id)) == baseline_before

    # -- 6. Stored reports read the same progress -------------------------
    report_base = f"/api/projects/{project}/reports"
    report_id = "REP-ACC"
    status, _, body = call(
        runtime,
        "POST",
        report_base,
        body={
            "report_id": report_id,
            "name": "Activity status",
            "description": "Acceptance progress",
            "subject": "activities",
            "columns": ["activity_id", "name", "status", "percent_complete"],
            "parameters": [
                {"key": "status", "required": False, "default": "In Progress"}
            ],
        },
        cookie=cookie,
        csrf=csrf,
        headers={"Idempotency-Key": f"rep-{suffix}"},
    )
    assert status == 200, body
    status, _, body = call(
        runtime, "POST", f"{report_base}/{report_id}/run", body={}, cookie=cookie, csrf=csrf
    )
    assert status == 200, body
    run = json.loads(body)
    assert run["row_count"] == 1
    assert run["rows"] == [
        {
            "activity_id": activity_a,
            "name": "Place concrete",
            "status": "In Progress",
            "percent_complete": 60.0,
        }
    ]
    status, headers, body = call(
        runtime,
        "GET",
        f"{report_base}/{report_id}/runs/{run['run_id']}/export",
        cookie=cookie,
        query="format=csv",
    )
    assert status == 200, body
    assert headers["x-content-sha256"][0]
    assert activity_a in body.decode("utf-8")

    # -- 7. Budget integration is a separate register --------------------
    budget_base = f"/api/projects/{project}/budget"
    line_body = {
        "budget_line_id": "BL-1",
        "description": "Civil works",
        "currency": "USD",
        "original_amount": "1000.00",
        "cost_account_id": "CA-1",
        "period_id": "FY26",
    }
    status, _, body = call(
        runtime,
        "POST",
        f"{budget_base}/lines",
        body=line_body,
        cookie=cookie,
        csrf=csrf,
        headers={"Idempotency-Key": "acc-line"},
    )
    assert status == 200, body
    status, _, body = call(
        runtime,
        "PATCH",
        f"{budget_base}/lines/BL-1",
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
    for change_id, amount in (("CH-1", "250.00"), ("CH-2", "100.00")):
        status, _, body = call(
            runtime,
            "POST",
            f"{budget_base}/lines/BL-1/changes",
            body={
                "change_id": change_id,
                "amount": amount,
                "reason": "scope",
                "status": "pending",
            },
            cookie=cookie,
            csrf=csrf,
        )
        assert status == 200, body
    status, _, body = call(
        runtime,
        "POST",
        f"{budget_base}/changes/CH-1/status",
        body={"status": "approved", "expected_revision": 1},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 403, body
    status, _, body = call(
        runtime,
        "POST",
        f"{budget_base}/changes/CH-1/status",
        body={"status": "approved", "expected_revision": 1, "reason": "owner decided"},
        cookie=admin,
        csrf=admin_csrf,
    )
    assert status == 200, body
    status, _, body = call(
        runtime,
        "POST",
        f"{budget_base}/funding",
        body={
            "funding_id": "FD-1",
            "name": "Owner capital",
            "source_type": "internal",
            "currency": "USD",
            "amount": "700.00",
            "period_id": "FY26",
        },
        cookie=cookie,
        csrf=csrf,
        headers={"Idempotency-Key": "acc-funding"},
    )
    assert status == 200, body
    status, _, body = call(runtime, "GET", f"{budget_base}/summary", cookie=cookie)
    assert status == 200, body
    summary = json.loads(body)["currencies"][0]
    assert (
        summary["original_budget"],
        summary["approved_changes"],
        summary["current_budget"],
        summary["pending_changes"],
        summary["funding"],
        summary["funding_balance"],
    ) == ("1200.00", "250.00", "1450.00", "100.00", "700.00", "750.00")

    threshold_id = f"THR-ACC-{suffix}"
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
        headers={"Idempotency-Key": f"mon-{threshold_id}"},
    )
    assert status == 200, body
    monitor = json.loads(body)["run"]
    assert monitor["observed_value"] == "750"
    assert monitor["level"] == "normal"

    # -- 8. Earned value reads the baseline, not the budget register -----
    evm_path = f"/api/projects/{project}/p6/earned-value"
    evm_body = {
        "contract_version": "p6-earned-value-read-model.v1",
        "baseline_id": baseline_id,
        "data_date": "2026-11-10",
        "currency": "USD",
    }
    # The default ETC method needs a remaining cost per activity; the in-progress
    # activity has none stored on the master, so the route must fail closed
    # rather than invent a zero.
    status, _, body = call(
        runtime, "POST", evm_path, body=evm_body, cookie=cookie, csrf=csrf
    )
    assert status == 400, body
    assert json.loads(body)["code"] == "EARNED_VALUE_REMAINING_COST_REQUIRED"
    status, _, body = call(
        runtime,
        "POST",
        evm_path,
        body={**evm_body, "etc_method": "PF_ONE"},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    earned = json.loads(body)["earned_value"]
    assert float(earned["budget_at_completion"]) == 1000.0
    assert float(earned["planned_value"]) == 1000.0
    assert float(earned["earned_value"]) == 600.0
    assert float(earned["actual_cost"]) == 0.0

    # -- 9. Closeout is gated by the same issue facts --------------------
    closeout_base = f"/api/projects/{project}/closeout"
    issue_base = f"/api/projects/{project}/p6/issues"
    issue_id = f"ISS-ACC-{suffix}"
    status, _, body = call(
        runtime,
        "POST",
        issue_base,
        body={
            "issue_id": issue_id,
            "title": "Facade delivery",
            "description": "Curtain wall behind the crane release.",
            "issue_type": "schedule",
            "status": "open",
            "priority": "high",
            "owner": "Site Planner",
            "date_identified": "2026-11-01",
            "due_date": "2026-11-20",
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    status, _, body = call(
        runtime,
        "POST",
        f"{closeout_base}/close",
        body={"expected_revision": 0},
        cookie=admin,
        csrf=admin_csrf,
    )
    assert status == 409, body
    assert json.loads(body)["code"] == "CLOSEOUT_OPEN_ISSUES:1"
    status, _, body = call(
        runtime,
        "PATCH",
        f"{issue_base}/{issue_id}",
        body={
            "issue_id": issue_id,
            "title": "Facade delivery",
            "description": "Curtain wall behind the crane release.",
            "issue_type": "schedule",
            "status": "resolved",
            "priority": "high",
            "owner": "Site Planner",
            "date_identified": "2026-11-01",
            "due_date": "2026-11-20",
            "resolution_note": "Delivered",
            "expected_revision": 1,
        },
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 200, body
    status, _, body = call(
        runtime,
        "POST",
        f"{closeout_base}/close",
        body={"expected_revision": 0, "note": "accepted"},
        cookie=admin,
        csrf=admin_csrf,
    )
    assert status == 200, body
    assert json.loads(body)["closeout"]["record_revision"] == 1
    status, _, body = call(
        runtime,
        "POST",
        f"{closeout_base}/reopen",
        body={"expected_revision": 1, "note": "final inspection"},
        cookie=admin,
        csrf=admin_csrf,
    )
    assert status == 200, body
    assert json.loads(body)["closeout"]["state"] == "open"

    # -- 10. Cross-surface authorization and tenant isolation ------------
    for path in (
        f"/api/projects/{project}/tracking/read",
        f"{report_base}/{report_id}/runs/{run['run_id']}",
        f"{budget_base}/lines",
        f"{budget_base}/summary",
        closeout_base,
    ):
        status, _, body = call(runtime, "GET", path, cookie=viewer_cookie)
        assert status == 200, (path, body)
    status, _, body = call(
        runtime, "POST", evm_path, body={**evm_body, "etc_method": "PF_ONE"}, cookie=viewer_cookie, csrf=viewer_csrf
    )
    assert status == 200, body
    status, _, body = call(
        runtime,
        "POST",
        f"{budget_base}/lines",
        body={**line_body, "budget_line_id": "BL-VIEWER"},
        cookie=viewer_cookie,
        csrf=viewer_csrf,
        headers={"Idempotency-Key": "viewer-line"},
    )
    assert status == 403, body
    status, _, body = call(
        runtime,
        "POST",
        f"{closeout_base}/close",
        body={"expected_revision": 2},
        cookie=viewer_cookie,
        csrf=viewer_csrf,
    )
    assert status == 403, body

    for path in (
        f"/api/projects/{project}/tracking/read",
        f"{budget_base}/lines",
        closeout_base,
    ):
        status, _, body = call(runtime, "GET", path, cookie=outsider_cookie)
        assert status == 403, (path, body)
    status, _, body = call(
        runtime, "POST", evm_path, body={**evm_body, "etc_method": "PF_ONE"}, cookie=outsider_cookie, csrf=outsider_csrf
    )
    assert status == 403, body

    # -- 11. One final consistency read across every stored surface ------
    status, _, body = call(
        runtime, "GET", f"{submit_path}/{job_id}/result", cookie=cookie
    )
    assert status == 200, body
    assert json.loads(body)["result"]["output_hash"] == output_hash
    assert _db_rows(
        runtime,
        "SELECT state, attempts FROM scheduling_jobs "
        "WHERE tenant_id=%s AND project_id=%s AND job_id=%s",
        (tenant, project, job_id),
    ) == [("SUCCEEDED", 1)]
    assert _db_rows(runtime, baseline_query, (tenant, project, baseline_id)) == baseline_before
    assert _db_rows(
        runtime,
        "SELECT activity_id, duration_value, planned_finish FROM activity_master "
        "WHERE tenant_id=%s AND project_id=%s ORDER BY activity_id",
        (tenant, project),
    ) == [
        (activity_a, str(planned_durations[activity_a]), planned_finish[activity_a]),
        (activity_b, str(planned_durations[activity_b]), planned_finish[activity_b]),
    ]
    stored_budget = _db_rows(
        runtime,
        "SELECT budget_line_id, revision, line_json FROM project_budget_line "
        "WHERE tenant_id=%s AND project_id=%s",
        (tenant, project),
    )
    assert [(row[0], row[1]) for row in stored_budget] == [("BL-1", 2)]
    assert json.loads(stored_budget[0][2])["original_amount"] == "1200.00"
    assert _db_rows(
        runtime,
        "SELECT state, record_revision FROM project_closeout "
        "WHERE tenant_id=%s AND project_id=%s",
        (tenant, project),
    ) == [("open", 2)]
    assert _db_rows(
        runtime,
        "SELECT action, record_revision FROM project_closeout_event "
        "WHERE tenant_id=%s AND project_id=%s ORDER BY record_revision",
        (tenant, project),
    ) == [("closed", 1), ("reopened", 2)]
    assert _db_rows(
        runtime,
        "SELECT status FROM project_lifecycle_projects "
        "WHERE tenant_id=%s AND project_id=%s",
        (tenant, project),
    ) == [("active",)]
