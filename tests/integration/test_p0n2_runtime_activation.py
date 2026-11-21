"""Live PostgreSQL proof that the production runtime is actually activated.

These tests drive the exact objects ``api/index.py`` composes (``ProductionRuntime``
over PostgreSQL) and the standalone durable worker. They cover the P0-N.2 exit
criteria that cannot be shown with fakes:

* Calendar Registry is built from persisted calendar definitions, snapshots,
  work-hour rules and exceptions for the snapshot's own scope;
* ``_calendar_registry_not_wired`` / ``SCHEDULE_QUERY_NOT_DEPLOYED`` are gone
  from the real path;
* submit -> real worker -> retrieval succeeds on the real database, in both
  thread and process placement;
* a missing calendar fails closed instead of silently using a default;
* cancellation and single-flight de-duplication hold with a real worker;
* jobs are isolated per tenant.

Run with::

    P6_TEST_POSTGRES_DSN=postgresql://postgres@127.0.0.1:5432/construction_pm_test \
        PYTHONPATH=src python -m pytest -q tests/integration/test_p0n2_runtime_activation.py
"""

from __future__ import annotations

import io
import json
import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("P6_TEST_POSTGRES_DSN") or os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip(
        "P6_TEST_POSTGRES_DSN / CONSTRUCTION_PM_POSTGRES_DSN is not configured",
        allow_module_level=True,
    )

pytestmark = pytest.mark.postgres

from construction_pm.backend_p0.models import BackendScope
from construction_pm.calendar_exception_repository import (
    PostgresCalendarExceptionRepository,
)
from construction_pm.calendar_master_repository import (
    CalendarMaster,
    PostgresCalendarMasterRepository,
)
from construction_pm.calendar_snapshot_repository import (
    PostgresCalendarSnapshotRepository,
)
from construction_pm.calendar_work_hours_repository import (
    PostgresCalendarWorkHourRepository,
)
from construction_pm.deployment import production_runtime as production_runtime_module
from construction_pm.deployment.production_runtime import (
    ProductionRuntime,
    ProductionSettings,
)
from construction_pm.deployment.scheduling_worker import (
    SchedulingWorkerRuntime,
    SchedulingWorkerSettings,
)
from construction_pm.identity_session import IdentityUser, PostgresIdentityStore, hash_password
from construction_pm.p6_versioned_resource_calendar_resolver import (
    P6ResourceCalendarResolutionError,
    build_calendar_registry_for_scope,
    calendar_registry_hash,
)
from construction_pm.postgres_scheduling_job_lifecycle import (
    PostgresSchedulingJobRepository,
)
from construction_pm.schedule_calculation_context_repository import (
    PostgresCalculationContextRepository,
    build_persisted_context,
)
from construction_pm.schedule_input_snapshot_repository import (
    PostgresScheduleInputSnapshotRepository,
    build_snapshot,
)
from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.authoritative_schedule import (
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.calendar import WorkingCalendar
from construction_pm.scheduling.calendar_context import CalendarReference
from construction_pm.scheduling_job_api import SchedulingJobAPI, SchedulingJobScope
from construction_pm.scheduling_job_lifecycle import SchedulingJobService

ORIGIN = "https://cubi.example.test"
SECRET = "integration-session-secret-0123456789abcdef"
PASSWORD = "correct horse battery staple"
WEB_ROOT = Path(__file__).resolve().parents[2] / "apps" / "web"


# ---------------------------------------------------------------------------
# seeding
# ---------------------------------------------------------------------------


def _connect():
    return psycopg.connect(DSN, autocommit=True)


def _initialize_calendar_tables(connection) -> None:
    for repository in (
        PostgresCalendarMasterRepository(connection),
        PostgresCalendarSnapshotRepository(connection),
        PostgresCalendarWorkHourRepository(connection),
        PostgresCalendarExceptionRepository(connection),
    ):
        repository.initialize()


def _seed_calendar(
    connection,
    scope: BackendScope,
    *,
    calendar_id: str = "CAL-1",
    calendar_version: str = "1",
) -> CalendarMaster:
    master = PostgresCalendarMasterRepository(connection).save(
        CalendarMaster(
            scope,
            calendar_id,
            calendar_version,
            "working-day",
            f"{calendar_id} calendar",
        )
    )
    PostgresCalendarSnapshotRepository(connection).save(master, WorkingCalendar())
    return master


def _seed_snapshot(
    connection,
    scope: BackendScope,
    *,
    calendar_id: str = "CAL-1",
    calendar_version: str = "1",
    activity_count: int = 1,
) -> str:
    now = datetime(2026, 9, 30, tzinfo=timezone.utc)
    snapshot_id = f"S-{uuid.uuid4().hex}"
    source = AuthoritativeScheduleInput(
        snapshot_id=snapshot_id,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
        project_revision=scope.project_revision,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=CalendarReference(calendar_id, calendar_version),
        activities=tuple(Activity(f"A{index:05d}", 2) for index in range(activity_count)),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 21),
    )
    context = CalculationContext(
        project_id=scope.project_id,
        project_version=scope.project_revision,
        calendar_id=calendar_id,
        calendar_version=calendar_version,
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp=now.isoformat(),
        input_snapshot_id=snapshot_id,
        tenant_id=scope.tenant_id,
        actor_id="authoritative-actor",
    )
    snapshots = PostgresScheduleInputSnapshotRepository(connection)
    contexts = PostgresCalculationContextRepository(connection)
    snapshots.initialize()
    contexts.initialize()
    snapshots.save(build_snapshot(source, context, now))
    contexts.save(build_persisted_context(scope, context))
    return snapshot_id


def _seed_ready_scope(*, activity_count: int = 1) -> tuple[BackendScope, str]:
    suffix = uuid.uuid4().hex[:10]
    scope = BackendScope(f"T-p0n2-{suffix}", f"P-p0n2-{suffix}", 0)
    connection = _connect()
    try:
        _initialize_calendar_tables(connection)
        _seed_calendar(connection, scope)
        snapshot_id = _seed_snapshot(
            connection, scope, activity_count=activity_count
        )
    finally:
        connection.close()
    return scope, snapshot_id


# ---------------------------------------------------------------------------
# in-process API + worker helpers
# ---------------------------------------------------------------------------


def _api_and_service(connection) -> tuple[SchedulingJobAPI, SchedulingJobService]:
    repository = PostgresSchedulingJobRepository(connection)
    repository.initialize()
    service = SchedulingJobService(repository)
    api = SchedulingJobAPI(
        service,
        snapshot_repository=PostgresScheduleInputSnapshotRepository(connection),
    )
    return api, service


def _job_scope(scope: BackendScope, *, user_id: str = "u1") -> SchedulingJobScope:
    return SchedulingJobScope(
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
        project_revision=scope.project_revision,
        user_id=user_id,
        roles=frozenset({"project_admin"}),
    )


# ---------------------------------------------------------------------------
# HTTP helpers around the exact WSGI app
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def runtime() -> ProductionRuntime:
    settings = ProductionSettings(
        database_url=DSN,
        session_secret=SECRET,
        public_origin=ORIGIN,
        secure_cookies=True,
        static_root=WEB_ROOT,
        max_pool_size=3,
    )
    instance = ProductionRuntime(settings)
    instance._initialize()
    suffix = uuid.uuid4().hex[:10]
    tenant_id = f"tenant-p0n2-{suffix}"
    project_id = f"project-p0n2-{suffix}"
    user = IdentityUser(
        user_id=f"user-p0n2-{suffix}",
        tenant_id=tenant_id,
        email=f"user-{suffix}@example.test",
        display_name="P0N2 Planner",
        roles=frozenset({"project_admin", "enterprise_admin", "planner"}),
        password_hash=hash_password(PASSWORD),
    )
    connection = instance.pool.acquire()
    try:
        PostgresIdentityStore(connection).upsert_user(user)
        connection.execute(
            "INSERT INTO project_lifecycle_projects "
            "(tenant_id, project_id, name) VALUES (%s, %s, %s) "
            "ON CONFLICT (tenant_id, project_id) DO NOTHING",
            (tenant_id, project_id, "P0N2 Project"),
        )
        connection.execute(
            "INSERT INTO project_lifecycle_memberships "
            "(tenant_id, project_id, user_id) VALUES (%s, %s, %s) "
            "ON CONFLICT DO NOTHING",
            (tenant_id, project_id, user.user_id),
        )
        connection.commit()
    finally:
        instance.pool.release(connection, healthy=True)

    other_user = IdentityUser(
        user_id=f"user-other-{suffix}",
        tenant_id=f"tenant-other-{suffix}",
        email=f"other-{suffix}@example.test",
        display_name="Other Tenant",
        roles=frozenset({"project_admin", "enterprise_admin"}),
        password_hash=hash_password(PASSWORD),
    )
    connection = instance.pool.acquire()
    try:
        PostgresIdentityStore(connection).upsert_user(other_user)
        connection.commit()
    finally:
        instance.pool.release(connection, healthy=True)

    instance.test_ids = {  # type: ignore[attr-defined]
        "tenant_id": tenant_id,
        "project_id": project_id,
        "user": user,
        "other_user": other_user,
        "client_ip": f"2001:db8:{suffix[:4]}:{suffix[4:8]}::1",
    }
    yield instance
    instance.close()


def call(runtime, method, path, *, body=None, cookie="", csrf="", headers=None):
    from wsgiref.util import setup_testing_defaults

    environ: dict[str, object] = {}
    setup_testing_defaults(environ)
    environ["REQUEST_METHOD"] = method
    environ["PATH_INFO"] = path
    environ["QUERY_STRING"] = ""
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
    return int(str(captured["status"]).split()[0]), payload


def login_with_headers(runtime, user: IdentityUser) -> tuple[str, str]:
    from urllib.parse import unquote
    from wsgiref.util import setup_testing_defaults

    environ: dict[str, object] = {}
    setup_testing_defaults(environ)
    environ["REQUEST_METHOD"] = "POST"
    environ["PATH_INFO"] = "/api/session"
    environ["wsgi.url_scheme"] = "https"
    environ["HTTP_ORIGIN"] = ORIGIN
    environ["HTTP_X_FORWARDED_PROTO"] = "https"
    environ["HTTP_X_FORWARDED_FOR"] = runtime.test_ids["client_ip"]
    raw = json.dumps({"email": user.email, "password": PASSWORD}).encode("utf-8")
    environ["CONTENT_LENGTH"] = str(len(raw))
    environ["CONTENT_TYPE"] = "application/json"
    environ["wsgi.input"] = io.BytesIO(raw)
    captured: dict[str, object] = {}

    def start_response(status, response_headers):
        captured["status"] = status
        captured["headers"] = response_headers

    body = b"".join(runtime(environ, start_response))
    assert int(str(captured["status"]).split()[0]) == 200, body
    cookies = [
        value for key, value in captured["headers"] if key.lower() == "set-cookie"
    ]
    session = next(value for value in cookies if value.startswith("cp_session="))
    csrf = next(value for value in cookies if value.startswith("cubi_csrf="))
    return (
        session.split(";", 1)[0],
        unquote(csrf.split(";", 1)[0].split("=", 1)[1]),
    )


# ---------------------------------------------------------------------------
# Calendar Registry: real, scoped, version-pinned
# ---------------------------------------------------------------------------


def test_calendar_registry_is_built_from_persisted_calendars():
    scope, _ = _seed_ready_scope()
    connection = _connect()
    try:
        registry = build_calendar_registry_for_scope(
            scope=scope,
            calendar_repository=PostgresCalendarMasterRepository(connection),
            snapshot_repository=PostgresCalendarSnapshotRepository(connection),
            exception_repository=PostgresCalendarExceptionRepository(connection),
            work_hours_repository=PostgresCalendarWorkHourRepository(connection),
        )
        resolver = registry.resolve(CalendarReference("CAL-1", "1"))
        assert resolver is not None
        assert [entry.reference.calendar_id for entry in registry.entries()] == ["CAL-1"]
    finally:
        connection.close()


def test_calendar_registry_is_scoped_and_hash_is_stable():
    scope, _ = _seed_ready_scope()
    other, _ = _seed_ready_scope()
    connection = _connect()
    try:
        def build(target):
            return build_calendar_registry_for_scope(
                scope=target,
                calendar_repository=PostgresCalendarMasterRepository(connection),
                snapshot_repository=PostgresCalendarSnapshotRepository(connection),
                exception_repository=PostgresCalendarExceptionRepository(connection),
                work_hours_repository=PostgresCalendarWorkHourRepository(connection),
            )

        first = build(scope)
        assert calendar_registry_hash(first) == calendar_registry_hash(build(scope))
        # The other project's identical-looking calendar is a different row and
        # must not be returned by this scope's registry.
        assert build(other).entries()[0].reference.calendar_id == "CAL-1"
        with pytest.raises(KeyError):
            build(other).resolve(CalendarReference("CAL-MISSING", "1"))
    finally:
        connection.close()


def test_missing_calendar_version_fails_closed_without_latest_fallback():
    scope, _ = _seed_ready_scope()
    connection = _connect()
    try:
        registry = build_calendar_registry_for_scope(
            scope=scope,
            calendar_repository=PostgresCalendarMasterRepository(connection),
            snapshot_repository=PostgresCalendarSnapshotRepository(connection),
            exception_repository=PostgresCalendarExceptionRepository(connection),
            work_hours_repository=PostgresCalendarWorkHourRepository(connection),
        )
        with pytest.raises(KeyError):
            registry.resolve(CalendarReference("CAL-1", "2"))
    finally:
        connection.close()


def test_unregistered_base_calendar_fails_closed():
    scope, _ = _seed_ready_scope()
    connection = _connect()
    try:
        master = PostgresCalendarMasterRepository(connection).save(
            CalendarMaster(
                scope,
                "CAL-CHILD",
                "1",
                "working-day",
                "Child",
                base_calendar_id="CAL-ABSENT",
                base_calendar_version="9",
            )
        )
        PostgresCalendarSnapshotRepository(connection).save(master, WorkingCalendar())
        with pytest.raises(
            P6ResourceCalendarResolutionError, match="BASE_CALENDAR_NOT_REGISTERED"
        ):
            build_calendar_registry_for_scope(
                scope=scope,
                calendar_repository=PostgresCalendarMasterRepository(connection),
                snapshot_repository=PostgresCalendarSnapshotRepository(connection),
                exception_repository=PostgresCalendarExceptionRepository(connection),
                work_hours_repository=PostgresCalendarWorkHourRepository(connection),
            )
    finally:
        connection.close()


def test_production_runtime_source_no_longer_contains_the_wiring_blocker():
    source = Path(production_runtime_module.__file__).read_text(encoding="utf-8")
    assert "_calendar_registry_not_wired" not in source
    assert "SCHEDULE_QUERY_NOT_DEPLOYED" not in source
    assert "build_calendar_registry_for_scope" in source


def test_production_composition_keeps_every_http_surface_wired(runtime):
    """Merging P0-N.2 must not shadow the AI Workbench, Enterprise or admin surfaces.

    The runtime builds the P6 app first and then wraps it; the workbench is the
    outermost middleware so its own routes win. Walking ``_app`` proves the whole
    chain is present in the assembled production object, not just imported.
    """
    from construction_pm.ai_workbench.http import AIWorkbenchHttpMiddleware
    from construction_pm.enterprise_task_http import EnterpriseTaskHttpMiddleware
    from construction_pm.global_administration_http import (
        GlobalAdministrationHttpMiddleware,
    )

    chain = []
    app = runtime.api_app
    while app is not None:
        chain.append(app)
        app = getattr(app, "_app", None)
    assert isinstance(chain[0], AIWorkbenchHttpMiddleware)
    assert isinstance(chain[1], EnterpriseTaskHttpMiddleware)
    assert isinstance(chain[2], GlobalAdministrationHttpMiddleware)
    # The fourth entry is the innermost P6 app built with the calendar registry
    # and the durable job repository.
    assert len(chain) == 4


# ---------------------------------------------------------------------------
# HTTP submit -> real worker -> retrieval
# ---------------------------------------------------------------------------


def test_http_submit_runs_on_real_worker_and_result_is_retrieved(runtime):
    ids = runtime.test_ids
    cookie, csrf = login_with_headers(runtime, ids["user"])
    project_id = ids["project_id"]
    scope = BackendScope(ids["tenant_id"], project_id, 0)
    connection = _connect()
    try:
        _initialize_calendar_tables(connection)
        _seed_calendar(connection, scope)
        snapshot_id = _seed_snapshot(connection, scope, activity_count=3)
    finally:
        connection.close()

    status, body = call(
        runtime,
        "POST",
        f"/api/v1/schedule/projects/{project_id}/jobs",
        body={"contract_version": "scheduling-job.v1", "snapshot_id": snapshot_id},
        cookie=cookie,
        csrf=csrf,
    )
    assert status == 202, body
    job = json.loads(body)
    assert job["state"] == "QUEUED"
    job_id = job["job_id"]

    worker = SchedulingWorkerRuntime(
        SchedulingWorkerSettings(database_url=DSN, slots=2, owner=f"test-{job_id[:6]}")
    )
    try:
        outcome = worker.drain(timeout=60)
    finally:
        worker.close()
    assert outcome.succeeded == 1, outcome.as_dict()

    status, body = call(
        runtime,
        "GET",
        f"/api/v1/schedule/projects/{project_id}/jobs/{job_id}",
        cookie=cookie,
    )
    assert status == 200, body
    assert json.loads(body)["state"] == "SUCCEEDED"

    status, body = call(
        runtime,
        "GET",
        f"/api/v1/schedule/projects/{project_id}/jobs/{job_id}/result",
        cookie=cookie,
    )
    assert status == 200, body
    result = json.loads(body)["result"]
    assert result["output_hash"] == result["payload"]["calculation_run_identity"]
    assert set(result["payload"]["activities"]) == {"A00000", "A00001", "A00002"}


def test_duplicate_submit_is_single_flight_and_runs_once(runtime):
    ids = runtime.test_ids
    cookie, csrf = login_with_headers(runtime, ids["user"])
    project_id = ids["project_id"]
    scope = BackendScope(ids["tenant_id"], project_id, 0)
    connection = _connect()
    try:
        _seed_calendar(
            connection,
            scope,
            calendar_id="CAL-DUP",
            calendar_version="1",
        )
        snapshot_id = _seed_snapshot(
            connection,
            scope,
            calendar_id="CAL-DUP",
            calendar_version="1",
            activity_count=2,
        )
    finally:
        connection.close()

    status_first, body_first = call(
        runtime,
        "POST",
        f"/api/v1/schedule/projects/{project_id}/jobs",
        body={"contract_version": "scheduling-job.v1", "snapshot_id": snapshot_id},
        cookie=cookie,
        csrf=csrf,
    )
    assert status_first == 202, body_first
    status_second, body_second = call(
        runtime,
        "POST",
        f"/api/v1/schedule/projects/{project_id}/jobs",
        body={"contract_version": "scheduling-job.v1", "snapshot_id": snapshot_id},
        cookie=cookie,
        csrf=csrf,
    )
    assert status_second == 200, body_second
    first = json.loads(body_first)
    second = json.loads(body_second)
    assert first["job_id"] == second["job_id"]
    assert second["deduplicated"] is True

    worker = SchedulingWorkerRuntime(
        SchedulingWorkerSettings(database_url=DSN, slots=1, owner="test-dedup")
    )
    try:
        worker.drain(timeout=60)
    finally:
        worker.close()
    final = json.loads(
        call(
            runtime,
            "GET",
            f"/api/v1/schedule/projects/{project_id}/jobs/{first['job_id']}",
            cookie=cookie,
        )[1]
    )
    assert final["state"] == "SUCCEEDED"
    # attempts counts real claims, so one execution proves the second submit
    # never created a second runnable job.
    assert final["attempts"] == 1


def test_missing_calendar_makes_the_real_job_fail_closed(runtime):
    scope, _ = _seed_ready_scope(activity_count=1)
    # The snapshot references a calendar that was never persisted for the scope.
    connection = _connect()
    try:
        broken_snapshot = f"S-{uuid.uuid4().hex}"
        # Seed a second snapshot whose context points at the absent calendar.
        now = datetime(2026, 9, 30, tzinfo=timezone.utc)
        source = AuthoritativeScheduleInput(
            snapshot_id=broken_snapshot,
            tenant_id=scope.tenant_id,
            project_id=scope.project_id,
            project_revision=scope.project_revision,
            mode=AuthoritativeScheduleMode.DATE_BASED,
            project_calendar=CalendarReference("CAL-ABSENT", "1"),
            activities=(Activity("A00000", 2),),
            relationships=(),
            activity_calendar_assignments=(),
            project_start=date(2026, 9, 21),
        )
        context = CalculationContext(
            project_id=scope.project_id,
            project_version=scope.project_revision,
            calendar_id="CAL-ABSENT",
            calendar_version="1",
            rules_version="rules-1",
            engine_version="engine-1",
            timezone="UTC",
            calculation_timestamp=now.isoformat(),
            input_snapshot_id=broken_snapshot,
            tenant_id=scope.tenant_id,
            actor_id="authoritative-actor",
        )
        PostgresScheduleInputSnapshotRepository(connection).save(
            build_snapshot(source, context, now)
        )
        PostgresCalculationContextRepository(connection).save(
            build_persisted_context(scope, context)
        )
        api, _ = _api_and_service(connection)

        view = api.submit(_job_scope(scope), snapshot_id=broken_snapshot)
        worker = SchedulingWorkerRuntime(
            SchedulingWorkerSettings(database_url=DSN, slots=1, owner="test-missing")
        )
        try:
            outcome = worker.drain(timeout=60)
        finally:
            worker.close()
        assert outcome.failed == 1 and outcome.succeeded == 0, outcome.as_dict()
        final = api.status(_job_scope(scope), view.job.job_id)
        assert final.job.state.value == "FAILED"
        assert "CAL-ABSENT@1" in (final.job.last_error or "")
    finally:
        connection.close()


def test_cancel_before_claim_prevents_execution(runtime):
    scope, snapshot_id = _seed_ready_scope()
    connection = _connect()
    try:
        api, _ = _api_and_service(connection)
        view = api.submit(_job_scope(scope), snapshot_id=snapshot_id)
        cancelled = api.cancel(_job_scope(scope), view.job.job_id)
        assert cancelled.job.state.value == "CANCELLED"

        worker = SchedulingWorkerRuntime(
            SchedulingWorkerSettings(database_url=DSN, slots=1, owner="test-cancel")
        )
        try:
            worker.drain(timeout=30)
        finally:
            worker.close()
        final = api.status(_job_scope(scope), view.job.job_id)
        assert final.job.state.value == "CANCELLED"
        assert final.job.attempts == 0
    finally:
        connection.close()


def test_process_placement_runs_in_a_real_child_process(runtime):
    scope, snapshot_id = _seed_ready_scope(activity_count=4)
    connection = _connect()
    try:
        api, _ = _api_and_service(connection)
        view = api.submit(
            _job_scope(scope),
            snapshot_id=snapshot_id,
            activity_count=4,
            relationship_count=0,
        )
        worker = SchedulingWorkerRuntime(
            SchedulingWorkerSettings(
                database_url=DSN,
                execution_mode="process",
                slots=2,
                owner="test-process",
                poll_interval=0.05,
            )
        )
        try:
            outcome = worker.drain(timeout=120)
        finally:
            worker.close()
        assert outcome.process_starts >= 1, outcome.as_dict()
        assert outcome.succeeded == 1, outcome.as_dict()
        assert api.status(_job_scope(scope), view.job.job_id).job.state.value == "SUCCEEDED"
    finally:
        connection.close()


def test_job_is_not_visible_to_another_tenant_session(runtime):
    scope, snapshot_id = _seed_ready_scope()
    connection = _connect()
    try:
        api, _ = _api_and_service(connection)
        view = api.submit(_job_scope(scope), snapshot_id=snapshot_id)

        cookie, _ = login_with_headers(runtime, runtime.test_ids["other_user"])
        status, body = call(
            runtime,
            "GET",
            f"/api/v1/schedule/projects/{scope.project_id}/jobs/{view.job.job_id}",
            cookie=cookie,
        )
        assert status == 403, body
        # Leave no queued job behind for other workers in this shared database.
        api.cancel(_job_scope(scope), view.job.job_id)
    finally:
        connection.close()
