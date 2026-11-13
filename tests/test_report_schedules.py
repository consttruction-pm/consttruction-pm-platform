"""Durable report schedules: next-run rules, claims, execution and audit."""

from __future__ import annotations

import io
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    Permission,
    RoleBasedAuthorizationPolicy,
)
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.preview.runtime import open_preview_runtime
from construction_pm.preview.storage import DEMO_USERS_BY_ROLE
from construction_pm.report_application import ReportApplicationService
from construction_pm.report_export import build_report_export
from construction_pm.report_parameters import ReportParameterBinding
from construction_pm.report_persistence import ReportDefinition, SQLiteReportStore
from construction_pm.report_schedules import (
    ReportSchedule,
    ReportScheduleError,
    ReportScheduleRevisionConflict,
    ReportScheduleRunner,
    ReportScheduleService,
    SQLiteReportScheduleStore,
    compute_next_run,
)

TENANT = "tenant-sched"
PROJECT = "project-sched"
USER = "planner-sched"
NOW = datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc)


class _Dataset:
    def __init__(self, rows):
        self.rows = rows

    def build(self, scope, subject, columns, parameters=None):
        return tuple({column: row.get(column) for column in columns} for row in self.rows)


def _policy() -> RoleBasedAuthorizationPolicy:
    return RoleBasedAuthorizationPolicy(
        {
            "planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE}),
            "viewer": frozenset({Permission.PROJECT_READ}),
        }
    )


def _context(role: str = "planner") -> AuthorizationContext:
    return AuthorizationContext(TENANT, PROJECT, USER, frozenset({role}))


@pytest.fixture()
def env(tmp_path: Path):
    connection = sqlite3.connect(tmp_path / "schedules.sqlite3")
    reports = SQLiteReportStore(connection)
    reports.initialize()
    store = SQLiteReportScheduleStore(connection)
    store.initialize()
    transactions = SQLiteTransactionManager(connection)
    application = ReportApplicationService(
        reports,
        _Dataset(
            [
                {"activity_id": "A1", "name": "Dig", "status": "Completed"},
                {"activity_id": "A2", "name": "Pour", "status": "In Progress"},
            ]
        ),
        _policy(),
        transactions,
    )
    service = ReportScheduleService(store, reports, _policy(), transactions)
    reports.create_definition(
        ReportDefinition(
            tenant_id=TENANT,
            project_id=PROJECT,
            report_id="RPT-1",
            name="Activities",
            subject="activities",
            columns=("activity_id", "name", "status"),
            parameters=(
                ReportParameterBinding("status", required=False, default="Completed"),
            ),
        ),
        idempotency_key="definition-key",
        actor_id=USER,
        occurred_at=NOW,
    )
    yield SimpleNamespace(
        connection=connection,
        reports=reports,
        store=store,
        service=service,
        application=application,
        transactions=transactions,
    )
    connection.close()


def _schedule(**overrides) -> ReportSchedule:
    data = dict(
        tenant_id=TENANT,
        project_id=PROJECT,
        report_id="RPT-1",
        schedule_id="SCH-1",
        cadence="daily",
        run_time="09:00",
        timezone="UTC",
        project_revision=4,
        export_format="csv",
        locale="en",
    )
    data.update(overrides)
    return ReportSchedule(**data)


def test_compute_next_run_cadences_and_dst() -> None:
    assert compute_next_run(
        cadence="daily",
        run_time="09:00",
        timezone_name="UTC",
        after=datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc),
    ) == datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)

    assert compute_next_run(
        cadence="weekly",
        run_time="09:00",
        timezone_name="UTC",
        weekday=2,
        after=datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc),
    ) == datetime(2026, 3, 4, 9, 0, tzinfo=timezone.utc)

    assert compute_next_run(
        cadence="monthly",
        run_time="09:00",
        timezone_name="UTC",
        day_of_month=15,
        after=datetime(2026, 3, 20, 10, 0, tzinfo=timezone.utc),
    ) == datetime(2026, 4, 15, 9, 0, tzinfo=timezone.utc)

    # 2026-03-08 02:30 does not exist in New York; the gap maps forward to
    # 03:30 EDT (07:30Z), which is deterministic from the zone database.
    assert compute_next_run(
        cadence="daily",
        run_time="02:30",
        timezone_name="America/New_York",
        after=datetime(2026, 3, 7, 12, 0, tzinfo=timezone.utc),
    ) == datetime(2026, 3, 8, 7, 30, tzinfo=timezone.utc)

    # Ambiguous fall-back time uses fold=0 (EDT, 05:30Z).
    assert compute_next_run(
        cadence="daily",
        run_time="01:30",
        timezone_name="America/New_York",
        after=datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc),
    ) == datetime(2026, 11, 1, 5, 30, tzinfo=timezone.utc)


def test_schedule_crud_revision_and_audit(env) -> None:
    created = env.service.create(
        _schedule(), context=_context(), actor_id=USER, occurred_at=NOW
    )
    assert created.revision == 1
    assert created.project_revision == 4
    assert created.next_run_at == datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)
    assert created.parameters == ()

    listed = env.service.list(
        tenant_id=TENANT, project_id=PROJECT, report_id="RPT-1", context=_context()
    )
    assert [item.schedule_id for item in listed] == ["SCH-1"]

    updated = env.service.update(
        _schedule(run_time="10:15"),
        expected_revision=1,
        context=_context(),
        actor_id=USER,
        occurred_at=NOW + timedelta(minutes=1),
    )
    assert updated.revision == 2
    assert updated.run_time == "10:15"
    assert updated.next_run_at == datetime(2026, 3, 1, 10, 15, tzinfo=timezone.utc)

    with pytest.raises(ReportScheduleRevisionConflict):
        env.service.update(
            _schedule(run_time="11:00"),
            expected_revision=1,
            context=_context(),
            actor_id=USER,
            occurred_at=NOW,
        )

    with pytest.raises(Exception) as denied:
        env.service.create(
            _schedule(schedule_id="SCH-2"),
            context=_context("viewer"),
            actor_id=USER,
            occurred_at=NOW,
        )
    assert "PERMISSION_DENIED" in str(denied.value)

    events = env.service.history(
        tenant_id=TENANT,
        project_id=PROJECT,
        report_id="RPT-1",
        schedule_id="SCH-1",
        context=_context(),
    )
    assert [(item.revision, item.event_type) for item in events] == [
        (1, "created"),
        (2, "updated"),
    ]

    env.service.delete(
        tenant_id=TENANT,
        project_id=PROJECT,
        report_id="RPT-1",
        schedule_id="SCH-1",
        expected_revision=2,
        context=_context(),
        actor_id=USER,
        occurred_at=NOW + timedelta(minutes=2),
    )
    env.service.create(
        _schedule(), context=_context(), actor_id=USER, occurred_at=NOW + timedelta(minutes=3)
    )
    replay = env.service.history(
        tenant_id=TENANT,
        project_id=PROJECT,
        report_id="RPT-1",
        schedule_id="SCH-1",
        context=_context(),
    )
    assert [(item.revision, item.event_type) for item in replay] == [
        (1, "created"),
        (2, "updated"),
        (3, "deleted"),
        (4, "created"),
    ]


def test_runner_executes_once_and_reuses_saved_run(env) -> None:
    schedule = env.service.create(
        _schedule(), context=_context(), actor_id=USER, occurred_at=NOW
    )
    runner = ReportScheduleRunner(env.store, env.application, lease_seconds=60)

    due = schedule.next_run_at
    outcomes = runner.run_due(now=due, worker_id="worker-1")
    assert [item.state for item in outcomes] == ["succeeded"]
    run = env.reports.get_run(TENANT, PROJECT, "RPT-1", outcomes[0].run_id)
    assert run.project_revision == 4
    assert run.generated_at == due
    assert run.parameters == (("status", "Completed"),)
    assert dict(run.parameter_sources) == {"status": "default"}
    expected = build_report_export(run, "csv")
    assert outcomes[0].content_sha256 == expected.content_sha256

    completed = env.store.get(TENANT, PROJECT, "RPT-1", "SCH-1")
    assert completed.last_status == "succeeded"
    assert completed.last_run_at == due
    assert completed.attempts == 0
    assert completed.next_run_at == due + timedelta(days=1)

    assert runner.run_due(now=due, worker_id="worker-1") == ()

    # Simulate a crash after the run was saved but before the completion was
    # recorded: the deterministic run id is reused instead of duplicating it.
    env.connection.execute(
        """UPDATE project_report_schedule
           SET next_run_at = ?, claim_token = NULL, claimed_until = NULL
           WHERE tenant_id = ? AND project_id = ? AND schedule_id = ?""",
        (due.isoformat(), TENANT, PROJECT, "SCH-1"),
    )
    env.connection.commit()
    replay = runner.run_due(now=due, worker_id="worker-2")
    assert [item.state for item in replay] == ["succeeded"]
    assert replay[0].run_id == outcomes[0].run_id
    assert len(env.reports.list_runs(TENANT, PROJECT, "RPT-1")) == 1


def test_runner_records_metric_and_deterministic_correlation(env) -> None:
    from construction_pm.observability import OperationalMetrics
    from construction_pm.production_readiness import StructuredEventLogger

    schedule = env.service.create(
        _schedule(), context=_context(), actor_id=USER, occurred_at=NOW
    )
    stream = io.StringIO()
    metrics = OperationalMetrics()
    runner = ReportScheduleRunner(
        env.store,
        env.application,
        metrics=metrics,
        logger=StructuredEventLogger(stream=stream, clock=lambda: NOW),
    )
    due = schedule.next_run_at
    outcomes = runner.run_due(now=due, worker_id="worker-1")
    assert [item.state for item in outcomes] == ["succeeded"]
    event = json.loads(stream.getvalue().splitlines()[0])
    assert event["event"] == "report.schedule.run"
    assert event["correlation_id"] == "report-schedule:SCH-1:20260302T090000Z"
    assert event["run_id"] == outcomes[0].run_id
    counters = metrics.snapshot()["counters"]
    assert counters[0]["name"] == "report_schedule_runs_total"
    assert counters[0]["labels"] == {"state": "succeeded"}


def test_claim_lease_reclaim_and_disabled_schedule(env) -> None:
    disabled = env.service.create(
        _schedule(schedule_id="SCH-OFF", enabled=False),
        context=_context(),
        actor_id=USER,
        occurred_at=NOW,
    )
    assert disabled.next_run_at is None
    runner = ReportScheduleRunner(env.store, env.application)
    assert runner.run_due(now=NOW + timedelta(days=30), worker_id="worker-0") == ()

    env.service.create(_schedule(), context=_context(), actor_id=USER, occurred_at=NOW)
    due = datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)
    first = env.store.claim_due(
        now=due, worker_id="worker-1", lease_seconds=1, limit=10
    )
    assert len(first) == 1
    assert env.store.claim_due(now=due, worker_id="worker-2", lease_seconds=1, limit=10) == ()
    reclaimed = env.store.claim_due(
        now=due + timedelta(seconds=2), worker_id="worker-2", lease_seconds=1, limit=10
    )
    assert [claim.schedule.schedule_id for claim in reclaimed] == ["SCH-1"]

    # The first worker's lease was lost; it must not overwrite the new claim.
    with pytest.raises(ReportScheduleError) as lost:
        env.store.complete(
            first[0],
            run_id="RUN-STALE",
            content_sha256="0" * 64,
            completed_at=due + timedelta(seconds=3),
            next_run_at=due + timedelta(days=1),
        )
    assert str(lost.value) == "REPORT_SCHEDULE_CLAIM_LOST"


def test_failure_records_backoff_then_recovers(env, monkeypatch) -> None:
    schedule = env.service.create(
        _schedule(), context=_context(), actor_id=USER, occurred_at=NOW
    )
    runner = ReportScheduleRunner(
        env.store, env.application, retry_base_minutes=5, retry_max_minutes=30
    )
    due = schedule.next_run_at

    def boom(*args, **kwargs):
        raise RuntimeError("renderer unavailable")

    monkeypatch.setattr(
        "construction_pm.report_schedules.build_report_export", boom
    )
    failed = runner.run_due(now=due, worker_id="worker-1")
    assert [item.state for item in failed] == ["failed"]
    assert "renderer unavailable" in (failed[0].error or "")
    stored = env.store.get(TENANT, PROJECT, "RPT-1", "SCH-1")
    assert stored.last_status == "failed"
    assert stored.attempts == 1
    assert "renderer unavailable" in (stored.last_error or "")
    assert stored.next_run_at == due + timedelta(minutes=5)

    monkeypatch.undo()
    recovered = runner.run_due(now=stored.next_run_at, worker_id="worker-2")
    assert [item.state for item in recovered] == ["succeeded"]
    final = env.store.get(TENANT, PROJECT, "RPT-1", "SCH-1")
    assert final.last_status == "succeeded"
    assert final.attempts == 0
    assert final.last_error is None


def test_schedule_http_crud_and_authorization(tmp_path: Path) -> None:
    runtime = open_preview_runtime(tmp_path / "preview.sqlite3", reset=True)
    project = "preview-rps-01"
    base = f"/api/projects/{project}/reports"
    try:
        planner = runtime.sessions.create(DEMO_USERS_BY_ROLE["planner"])
        viewer = runtime.sessions.create(DEMO_USERS_BY_ROLE["viewer"])

        definition = {
            "report_id": "RPT-SCH",
            "name": "Scheduled activities",
            "subject": "activities",
            "columns": ["activity_id", "name"],
            "idempotency_key": "scheduled-key",
        }
        status, body = _request(
            runtime.app, "POST", base, body=definition, cookie=planner.session_id
        )
        assert status == 200, body[:400]

        payload = {
            "schedule_id": "SCH-HTTP",
            "cadence": "daily",
            "run_time": "06:30",
            "timezone": "Asia/Tehran",
            "export_format": "pdf",
            "locale": "fa",
        }
        status, body = _request(
            runtime.app,
            "POST",
            f"{base}/RPT-SCH/schedules",
            body=payload,
            cookie=planner.session_id,
        )
        assert status == 200, body[:400]
        created = json.loads(body)
        assert created["contract_version"] == "p6-report-api.v1"
        assert created["schedule_id"] == "SCH-HTTP"
        assert created["timezone"] == "Asia/Tehran"
        assert isinstance(created["project_revision"], int)
        assert created["revision"] == 1
        assert created["next_run_at"].endswith("+00:00")

        status, body = _request(
            runtime.app,
            "GET",
            f"{base}/RPT-SCH/schedules",
            cookie=viewer.session_id,
        )
        assert status == 200, body[:400]
        assert [item["schedule_id"] for item in json.loads(body)["schedules"]] == [
            "SCH-HTTP"
        ]

        status, body = _request(
            runtime.app,
            "PATCH",
            f"{base}/RPT-SCH/schedules/SCH-HTTP",
            body={**payload, "run_time": "07:00", "expected_revision": 1},
            cookie=planner.session_id,
        )
        assert status == 200, body[:400]
        updated = json.loads(body)
        assert updated["revision"] == 2
        assert updated["run_time"] == "07:00"

        status, body = _request(
            runtime.app,
            "GET",
            f"{base}/RPT-SCH/schedules/SCH-HTTP/history",
            cookie=viewer.session_id,
        )
        assert status == 200, body[:400]
        assert [
            (item["revision"], item["event_type"])
            for item in json.loads(body)["events"]
        ] == [(1, "created"), (2, "updated")]

        # Schedule audit events must not leak into report-definition history.
        status, body = _request(
            runtime.app, "GET", f"{base}/RPT-SCH/history", cookie=viewer.session_id
        )
        assert status == 200, body[:400]
        assert [
            (item["revision"], item["event_type"])
            for item in json.loads(body)["events"]
        ] == [(1, "created")]

        status, body = _request(
            runtime.app,
            "DELETE",
            f"{base}/RPT-SCH/schedules/SCH-HTTP?expected_revision=1",
            cookie=planner.session_id,
        )
        assert status == 409, body[:300]
        assert json.loads(body)["code"] == "REPORT_SCHEDULE_REVISION_CONFLICT"

        status, body = _request(
            runtime.app,
            "DELETE",
            f"{base}/RPT-SCH/schedules/SCH-HTTP?expected_revision=2",
            cookie=planner.session_id,
        )
        assert status == 200, body[:400]
        assert json.loads(body)["deleted"] is True

        status, body = _request(
            runtime.app,
            "GET",
            f"{base}/RPT-SCH/schedules/SCH-HTTP",
            cookie=planner.session_id,
        )
        assert status == 404, body[:300]

        status, body = _request(
            runtime.app,
            "POST",
            f"{base}/RPT-SCH/schedules",
            body={**payload, "schedule_id": "SCH-VIEWER"},
            cookie=viewer.session_id,
        )
        assert status == 403, body[:300]
        assert json.loads(body)["code"] == "REPORT_SCHEDULE_PERMISSION_DENIED"

        status, body = _request(
            runtime.app,
            "POST",
            f"{base}/RPT-SCH/schedules",
            body={**payload, "schedule_id": "SCH-TZ", "timezone": "Nowhere/Zone"},
            cookie=planner.session_id,
        )
        assert status == 400, body[:300]
        assert json.loads(body)["code"] == "INVALID_REPORT_SCHEDULE_TIMEZONE"
    finally:
        runtime.close()


def _request(app, method: str, path: str, *, body: dict | None = None, cookie=None):
    raw = b"" if body is None else json.dumps(body).encode()
    path_info, _, query = path.partition("?")
    environ: dict[str, object] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path_info,
        "QUERY_STRING": query,
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": BytesIO(raw),
    }
    if raw:
        environ["CONTENT_TYPE"] = "application/json"
    if cookie is not None:
        environ["HTTP_COOKIE"] = f"cp_session={cookie}"
    captured: dict[str, object] = {}

    def start_response(status, headers) -> None:
        captured["status"] = status

    chunks = b"".join(app(environ, start_response))
    return int(str(captured["status"]).split(" ", 1)[0]), chunks
