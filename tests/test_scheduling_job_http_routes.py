"""HTTP acceptance for the durable scheduling job routes.

One real WSGI-facing request submits a job, a token-authenticated worker
request executes it on the P0-N engine, and the same API returns the status and
the result. The pre-existing synchronous ``POST /api/v1/schedule/query`` route
is exercised unchanged in the same harness so backward compatibility is proven,
not assumed.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta, timezone

from construction_pm.application.authorization import default_project_policy
from construction_pm.application.project_lifecycle import (
    AuthenticatedSession,
    ProjectLifecycleService,
    ProjectSummary,
)
from construction_pm.application.project_lifecycle_api import ProjectLifecycleAPI
from construction_pm.backend_p0.authoritative_schedule_query import (
    AuthoritativeScheduleQueryProvider,
)
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.schedule_query import (
    SCHEDULE_QUERY_VERSION,
    ScheduleQueryAPI,
    ScheduleQueryApplicationService,
)
from construction_pm.http.project_lifecycle_routes import ProjectLifecycleHttpRoutes
from construction_pm.schedule_calculation_context_repository import (
    SQLiteCalculationContextRepository,
    build_persisted_context,
)
from construction_pm.schedule_input_snapshot_repository import (
    SQLiteScheduleInputSnapshotRepository,
    build_snapshot,
)
from construction_pm.scheduling.activity import Activity
from construction_pm.scheduling.authoritative_schedule import (
    AuthoritativeScheduleInput,
    AuthoritativeScheduleMode,
)
from construction_pm.scheduling.calendar import WorkingCalendar, WorkingTimeResolver
from construction_pm.scheduling.calculation_context import CalculationContext
from construction_pm.scheduling.calendar_context import (
    CalendarReference,
    CalendarResolverRegistry,
)
from construction_pm.scheduling_execution_budget import GlobalExecutionBudget
from construction_pm.scheduling_job_api import SchedulingJobAPI
from construction_pm.scheduling_job_lifecycle import (
    InMemorySchedulingJobRepository,
    SchedulingJobService,
)
from construction_pm.scheduling_job_runner import SchedulingEngineJobRunner

TENANT = "t1"
PROJECT = "p1"
REVISION = 2
SNAPSHOT_ID = "S-HTTP"
WORKER_TOKEN = "http-worker-token"
COOKIE = {"cp_session": "s1"}


class Sessions:
    def __init__(self, session):
        self.session = session

    def get(self, session_id):
        return self.session if session_id == self.session.session_id else None


class Projects:
    def list_for_user(self, tenant_id, user_id):
        return (ProjectSummary(PROJECT, tenant_id, "Project One", REVISION),)

    def get_for_user(self, tenant_id, project_id, user_id):
        if project_id != PROJECT:
            return None
        return ProjectSummary(PROJECT, tenant_id, "Project One", REVISION)

    def create_for_user(self, tenant_id, user_id, project_id, name, **_):
        return ProjectSummary(project_id, tenant_id, name, 0)


def _provider() -> AuthoritativeScheduleQueryProvider:
    calendar = CalendarReference("CAL-1", "1")
    source = AuthoritativeScheduleInput(
        snapshot_id=SNAPSHOT_ID,
        tenant_id=TENANT,
        project_id=PROJECT,
        project_revision=REVISION,
        mode=AuthoritativeScheduleMode.DATE_BASED,
        project_calendar=calendar,
        activities=(Activity("A", 2), Activity("B", 3), Activity("C", 1)),
        relationships=(),
        activity_calendar_assignments=(),
        project_start=date(2026, 9, 21),
    )
    context = CalculationContext(
        project_id=PROJECT,
        project_version=REVISION,
        calendar_id="CAL-1",
        calendar_version="1",
        rules_version="rules-1",
        engine_version="engine-1",
        timezone="UTC",
        calculation_timestamp="2026-09-30T00:00:00+00:00",
        input_snapshot_id=SNAPSHOT_ID,
        tenant_id=TENANT,
    )
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    snapshots = SQLiteScheduleInputSnapshotRepository(connection)
    contexts = SQLiteCalculationContextRepository(connection)
    snapshots.save(
        build_snapshot(source, context, datetime(2026, 9, 30, tzinfo=timezone.utc))
    )
    contexts.save(
        build_persisted_context(BackendScope(TENANT, PROJECT, REVISION), context)
    )
    registry = CalendarResolverRegistry(
        day_resolvers={"CAL-1@1": WorkingTimeResolver(WorkingCalendar())}
    )
    return AuthoritativeScheduleQueryProvider(
        snapshots,
        lambda: registry,
        calculation_context_repository=contexts,
    )


def _routes():
    now = datetime(2026, 10, 20, tzinfo=timezone.utc)
    session = AuthenticatedSession(
        "s1", "u1", TENANT, frozenset({"project_admin"}), now + timedelta(hours=1)
    )
    lifecycle = ProjectLifecycleAPI(
        ProjectLifecycleService(Sessions(session), Projects(), default_project_policy())
    )
    provider = _provider()
    service = SchedulingJobService(InMemorySchedulingJobRepository())
    runner = SchedulingEngineJobRunner(
        service,
        provider=provider,
        budget=GlobalExecutionBudget(2),
        poll_interval=0.002,
    )
    job_api = SchedulingJobAPI(
        service,
        runner=runner,
        worker_token=WORKER_TOKEN,
        snapshot_repository=provider.snapshot_repository,
    )
    query_api = ScheduleQueryAPI(
        ScheduleQueryApplicationService(
            provider=provider,
            authorization_policy=default_project_policy(),
        )
    )
    routes = ProjectLifecycleHttpRoutes(
        lifecycle,
        clock=type("Clock", (), {"now": lambda self: now})(),
        schedule_query_api=query_api,
        scheduling_job_api=job_api,
    )
    return routes, provider


def _decode(response):
    status, headers, body = response
    return status, headers, json.loads(body.decode("utf-8"))


def _submit_job(routes, **overrides):
    payload = {"snapshot_id": SNAPSHOT_ID, **overrides}
    return routes.handle(
        "POST",
        f"/api/v1/schedule/projects/{PROJECT}/jobs",
        cookies=COOKIE,
        body=json.dumps(payload).encode("utf-8"),
    )


def _direct_hash(provider: AuthoritativeScheduleQueryProvider) -> str:
    from construction_pm.application.authorization import AuthorizationContext
    from construction_pm.control_intelligence.contracts import ControlScope
    from construction_pm.control_intelligence.query import (
        ScheduleQueryKind,
        ScheduleQueryRequest,
    )

    answer = provider.execute(
        ScheduleQueryRequest(
            query_id="direct",
            scope=ControlScope(TENANT, PROJECT, REVISION),
            requested_by="u1",
            query_text="authoritative schedule run",
            kind=ScheduleQueryKind.FACT,
            language="en",
            constraints={"snapshot_id": SNAPSHOT_ID},
        ),
        auth_context=AuthorizationContext(
            TENANT, PROJECT, "u1", frozenset({"project_admin"})
        ),
    )
    return answer.source_refs[0].content_hash


def test_api_submits_a_job_and_reads_status_and_result_after_a_worker_tick():
    routes, provider = _routes()

    submitted = _submit_job(routes)
    status, _, view = _decode(submitted)
    assert status == 202
    assert view["state"] == "QUEUED"
    assert view["contract_version"] == "scheduling-job.v1"
    job_id = view["job_id"]

    # The worker authenticates with its token, not a browser session.
    tick = routes.handle(
        "POST",
        "/api/v1/schedule/worker/tick",
        headers={"X-Worker-Token": WORKER_TOKEN},
        body=b"{}",
    )
    tick_status, _, outcome = _decode(tick)
    assert tick_status == 200
    assert outcome["outcome"]["claimed"] == 1
    assert outcome["outcome"]["succeeded"] == 1

    status_response = routes.handle(
        "GET", f"/api/v1/schedule/projects/{PROJECT}/jobs/{job_id}", cookies=COOKIE
    )
    read_status, _, read_view = _decode(status_response)
    assert read_status == 200
    assert read_view["state"] == "SUCCEEDED"

    result_response = routes.handle(
        "GET",
        f"/api/v1/schedule/projects/{PROJECT}/jobs/{job_id}/result",
        cookies=COOKIE,
    )
    result_status, _, result_view = _decode(result_response)
    assert result_status == 200
    assert result_view["result"]["output_hash"] == _direct_hash(provider)
    assert result_view["result"]["payload"]["activity_count"] == 3


def test_deduplicated_submission_is_reported_as_already_accepted():
    routes, _ = _routes()
    first = _decode(_submit_job(routes))[2]
    second_status, _, second = _decode(_submit_job(routes))
    assert second_status == 200
    assert second["deduplicated"] is True
    assert second["job_id"] == first["job_id"]


def test_cross_scope_echo_and_missing_snapshot_are_rejected():
    routes, _ = _routes()
    cross_status, _, cross = _decode(_submit_job(routes, tenant_id="t2"))
    assert cross_status == 403
    assert cross["code"] == "CROSS_SCOPE_ACCESS"

    missing_status, _, missing = _decode(_submit_job(routes, snapshot_id="S-NONE"))
    assert missing_status == 404
    assert missing["code"] == "SCHEDULING_JOB_SNAPSHOT_NOT_FOUND"

    workload_status, _, workload = _decode(_submit_job(routes, activity_count=50))
    assert workload_status == 409
    assert workload["code"] == "SCHEDULING_JOB_WORKLOAD_MISMATCH"


def test_job_routes_require_a_session_and_worker_routes_require_the_token():
    routes, _ = _routes()
    no_session = routes.handle(
        "POST",
        f"/api/v1/schedule/projects/{PROJECT}/jobs",
        body=json.dumps({"snapshot_id": SNAPSHOT_ID}).encode("utf-8"),
    )
    assert no_session[0] == 401

    forbidden_status, _, forbidden = _decode(
        routes.handle("POST", "/api/v1/schedule/worker/tick", body=b"{}")
    )
    assert forbidden_status == 403
    assert forbidden["code"] == "SCHEDULING_WORKER_UNAUTHORIZED"

    wrong_status, _, _ = _decode(
        routes.handle(
            "POST",
            "/api/v1/schedule/worker/tick",
            headers={"X-Worker-Token": "wrong"},
            body=b"{}",
        )
    )
    assert wrong_status == 403

    status_status, _, status_view = _decode(
        routes.handle(
            "GET",
            "/api/v1/schedule/worker/status",
            headers={"X-Worker-Token": WORKER_TOKEN},
        )
    )
    assert status_status == 200
    assert status_view["worker"]["execution_mode"] == "thread"


def test_cancel_route_terminates_a_queued_job():
    routes, _ = _routes()
    job_id = _decode(_submit_job(routes))[2]["job_id"]
    status, _, view = _decode(
        routes.handle(
            "POST",
            f"/api/v1/schedule/projects/{PROJECT}/jobs/{job_id}/cancel",
            cookies=COOKIE,
        )
    )
    assert status == 200
    assert view["state"] == "CANCELLED"
    result_status, _, result = _decode(
        routes.handle(
            "GET",
            f"/api/v1/schedule/projects/{PROJECT}/jobs/{job_id}/result",
            cookies=COOKIE,
        )
    )
    assert result_status == 409
    assert result["code"] == "SCHEDULING_JOB_NOT_SUCCEEDED"


def test_synchronous_schedule_query_route_is_unchanged():
    routes, _ = _routes()
    payload = {
        "contract_version": SCHEDULE_QUERY_VERSION,
        "query_id": "Q-HTTP",
        "scope": {"tenant_id": TENANT, "project_id": PROJECT, "project_revision": REVISION},
        "requested_by": "u1",
        "query_text": "show schedule",
        "kind": "fact",
        "language": "en",
        "constraints": {"snapshot_id": SNAPSHOT_ID},
    }
    response = routes.handle(
        "POST",
        "/api/v1/schedule/query",
        cookies=COOKIE,
        body=json.dumps(payload).encode("utf-8"),
    )
    status, _, body = _decode(response)
    assert status == 200
    assert body["contract_version"] == "schedule-query-result.v1"
    assert body["query_id"] == "Q-HTTP"
    assert body["data"]["activity_count"] == 3
