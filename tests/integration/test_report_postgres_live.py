"""Live PostgreSQL parity for the report register and report schedules.

These tests run only when ``CONSTRUCTION_PM_POSTGRES_DSN`` points at a real
PostgreSQL server; a skipped module is never a substitute for the SQLite suite
that already covers the same contracts.
"""

from __future__ import annotations

import os
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN") or os.getenv(
    "P6_TEST_POSTGRES_DSN"
)
if not DSN:
    pytest.skip(
        "CONSTRUCTION_PM_POSTGRES_DSN or P6_TEST_POSTGRES_DSN is not configured",
        allow_module_level=True,
    )

from construction_pm.application.authorization import (  # noqa: E402
    AuthorizationContext,
    Permission,
    RoleBasedAuthorizationPolicy,
)
from construction_pm.client_sync.postgres_transaction import (  # noqa: E402
    PostgresTransactionManager,
)
from construction_pm.report_application import (  # noqa: E402
    ReportApplicationService,
)
from construction_pm.report_parameters import ReportParameterBinding  # noqa: E402
from construction_pm.report_persistence import (  # noqa: E402
    PostgresReportStore,
    ReportDefinition,
    ReportIdempotencyReuse,
    ReportPersistenceError,
    ReportRevisionConflict,
    ReportRun,
    SQLiteReportStore,
)
from construction_pm.report_schedules import (  # noqa: E402
    PostgresReportScheduleStore,
    ReportSchedule,
    ReportScheduleError,
    ReportScheduleRevisionConflict,
    ReportScheduleRunner,
    ReportScheduleService,
    SQLiteReportScheduleStore,
)

NOW = datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc)
POLICY = RoleBasedAuthorizationPolicy(
    {
        "planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE}),
        "viewer": frozenset({Permission.PROJECT_READ}),
    }
)


class _Dataset:
    def __init__(self, rows) -> None:
        self.rows = rows

    def build(self, scope, subject, columns, parameters=None):
        return tuple(
            {column: row.get(column) for column in columns} for row in self.rows
        )


class _FailingDataset:
    def build(self, scope, subject, columns, parameters=None):
        raise RuntimeError("dataset unavailable")


def _tenant() -> tuple[str, str]:
    suffix = uuid.uuid4().hex[:10]
    return f"report-t-{suffix}", f"report-p-{suffix}"


def _definition(tenant: str, project: str, report_id: str) -> ReportDefinition:
    return ReportDefinition(
        tenant_id=tenant,
        project_id=project,
        report_id=report_id,
        name="Activities register",
        description="Schedule status",
        subject="activities",
        columns=("activity_id", "name", "status"),
        parameters=(
            ReportParameterBinding("status", required=False, default="Completed"),
        ),
    )


def _started(connection) -> SimpleNamespace:
    reports = PostgresReportStore(connection)
    reports.initialize()
    schedules = PostgresReportScheduleStore(connection)
    schedules.initialize()
    # This module is the only writer with the ``report-t-`` tenant prefix.
    # Removing its own earlier rows keeps claim_due assertions exact even when
    # a previous aborted test run left a due schedule behind in the shared DB.
    for table in (
        "project_report_schedule",
        "project_report_run",
        "project_report_audit",
        "project_report_idempotency",
        "project_report_definition",
    ):
        connection.execute(
            f"DELETE FROM {table} WHERE tenant_id LIKE 'report-t-%'"
        )
    connection.commit()
    return SimpleNamespace(reports=reports, schedules=schedules)


def _schedule(
    tenant: str,
    project: str,
    report_id: str,
    *,
    schedule_id: str = "SCH-1",
    next_run_at: datetime = NOW + timedelta(hours=1),
) -> ReportSchedule:
    return ReportSchedule(
        tenant_id=tenant,
        project_id=project,
        report_id=report_id,
        schedule_id=schedule_id,
        cadence="daily",
        run_time="09:00",
        timezone="UTC",
        parameters=(("status", "Completed"),),
        enabled=True,
        next_run_at=next_run_at,
        created_at=NOW,
        updated_at=NOW,
    )


def test_postgres_definition_lifecycle_idempotency_and_isolation():
    tenant, project = _tenant()
    other_tenant, other_project = f"{tenant}-b", f"{project}-b"
    with psycopg.connect(DSN) as connection:
        stores = _started(connection)

        created = stores.reports.create_definition(
            _definition(tenant, project, "RPT-1"),
            idempotency_key="key-1",
            actor_id="u1",
            occurred_at=NOW,
        )
        assert created.revision == 1
        loaded = stores.reports.get_definition(tenant, project, "RPT-1")
        assert loaded.definition.parameters[0].default == "Completed"

        replay = stores.reports.create_definition(
            _definition(tenant, project, "RPT-1"),
            idempotency_key="key-1",
            actor_id="u1",
            occurred_at=NOW,
        )
        assert replay.revision == 1
        assert len(stores.reports.definition_history(tenant, project, "RPT-1")) == 1

        with pytest.raises(ReportIdempotencyReuse, match="REPORT_IDEMPOTENCY_KEY_REUSE"):
            stores.reports.create_definition(
                ReportDefinition(
                    tenant_id=tenant,
                    project_id=project,
                    report_id="RPT-1",
                    name="Changed",
                    subject="activities",
                    columns=("activity_id",),
                ),
                idempotency_key="key-1",
                actor_id="u1",
                occurred_at=NOW,
            )
        with pytest.raises(ReportPersistenceError, match="REPORT_ID_ALREADY_EXISTS"):
            stores.reports.create_definition(
                _definition(tenant, project, "RPT-1"),
                idempotency_key="key-2",
                actor_id="u1",
                occurred_at=NOW,
            )

        updated = stores.reports.update_definition(
            ReportDefinition(
                tenant_id=tenant,
                project_id=project,
                report_id="RPT-1",
                name="Activities v2",
                description="Renamed",
                subject="activities",
                columns=("activity_id", "status"),
                parameters=(
                    ReportParameterBinding(
                        "status", required=False, default="In Progress"
                    ),
                ),
            ),
            expected_revision=1,
            actor_id="u2",
            occurred_at=NOW + timedelta(minutes=1),
            reason="rename",
        )
        assert updated.revision == 2
        with pytest.raises(ReportRevisionConflict, match="REPORT_REVISION_CONFLICT"):
            stores.reports.update_definition(
                _definition(tenant, project, "RPT-1"),
                expected_revision=1,
                actor_id="u3",
                occurred_at=NOW + timedelta(minutes=2),
            )

        # ILIKE keeps the case-insensitive search parity with SQLite LIKE.
        assert [item.definition.report_id for item in stores.reports.list_definitions(
            tenant, project, subject="activities", search="ACTIV"
        )] == ["RPT-1"]
        assert stores.reports.list_definitions(
            tenant, project, subject="risks"
        ) == ()

        # The same report id in another tenant is a different record.
        stores.reports.create_definition(
            _definition(other_tenant, other_project, "RPT-1"),
            idempotency_key="key-1",
            actor_id="u1",
            occurred_at=NOW,
        )
        assert (
            stores.reports.get_definition(other_tenant, other_project, "RPT-1")
            .definition.name
            == "Activities register"
        )
        assert stores.reports.get_definition(tenant, project, "RPT-1").definition.name == "Activities v2"

        with pytest.raises(ReportRevisionConflict):
            stores.reports.delete_definition(
                tenant_id=tenant,
                project_id=project,
                report_id="RPT-1",
                expected_revision=1,
                actor_id="u1",
                occurred_at=NOW + timedelta(minutes=3),
            )
        stores.reports.delete_definition(
            tenant_id=tenant,
            project_id=project,
            report_id="RPT-1",
            expected_revision=2,
            actor_id="u1",
            occurred_at=NOW + timedelta(minutes=4),
            reason="retired",
        )
        with pytest.raises(KeyError, match="REPORT_NOT_FOUND"):
            stores.reports.get_definition(tenant, project, "RPT-1")
        history = stores.reports.definition_history(tenant, project, "RPT-1")
        assert [(event.event_type, event.revision) for event in history] == [
            ("created", 1),
            ("updated", 2),
            ("deleted", 3),
        ]
        connection.commit()


def test_postgres_runs_are_immutable_and_tenant_scoped():
    tenant, project = _tenant()
    other_tenant, other_project = f"{tenant}-b", f"{project}-b"
    with psycopg.connect(DSN) as connection:
        stores = _started(connection)
        stores.reports.create_definition(
            _definition(tenant, project, "RPT-2"),
            idempotency_key="run-key",
            actor_id="u1",
            occurred_at=NOW,
        )

        assert stores.reports.next_run_id(tenant, project, "RPT-2") == "RUN-RPT-2-1"
        run = ReportRun(
            run_id="RUN-RPT-2-1",
            tenant_id=tenant,
            project_id=project,
            report_id="RPT-2",
            report_revision=1,
            project_revision=7,
            subject="activities",
            columns=("activity_id", "name", "status"),
            rows=(
                {"activity_id": "A1", "name": "Dig — 挖掘", "status": "Completed"},
                {"activity_id": "A2", "name": "Pour", "status": "In Progress"},
            ),
            generated_at=NOW,
            generated_by="u1",
            parameters=(("status", "Completed"),),
            parameter_sources=(("status", "explicit"),),
        )
        stores.reports.save_run(run)
        with pytest.raises(
            ReportPersistenceError, match="REPORT_RUN_ID_ALREADY_EXISTS"
        ):
            stores.reports.save_run(run)

        stores.reports.update_definition(
            ReportDefinition(
                tenant_id=tenant,
                project_id=project,
                report_id="RPT-2",
                name="Rewritten",
                subject="activities",
                columns=("activity_id",),
            ),
            expected_revision=1,
            actor_id="u1",
            occurred_at=NOW + timedelta(minutes=1),
        )
        frozen = stores.reports.get_run(tenant, project, "RPT-2", "RUN-RPT-2-1")
        assert frozen.columns == ("activity_id", "name", "status")
        assert frozen.rows[0]["name"] == "Dig — 挖掘"
        assert frozen.report_revision == 1
        assert dict(frozen.parameters) == {"status": "Completed"}
        assert dict(frozen.parameter_sources) == {"status": "explicit"}

        # Same run id in another tenant is independent.
        stores.reports.create_definition(
            _definition(other_tenant, other_project, "RPT-2"),
            idempotency_key="run-key-b",
            actor_id="u1",
            occurred_at=NOW,
        )
        stores.reports.save_run(
            ReportRun(
                run_id="RUN-RPT-2-1",
                tenant_id=other_tenant,
                project_id=other_project,
                report_id="RPT-2",
                report_revision=1,
                project_revision=1,
                subject="activities",
                columns=("activity_id",),
                rows=({"activity_id": "B1"},),
                generated_at=NOW,
                generated_by="u1",
            )
        )
        assert len(stores.reports.list_runs(tenant, project, "RPT-2")) == 1
        assert len(
            stores.reports.list_runs(other_tenant, other_project, "RPT-2")
        ) == 1
        with pytest.raises(KeyError, match="REPORT_RUN_NOT_FOUND"):
            stores.reports.get_run(tenant, project, "RPT-2", "RUN-MISSING")
        connection.commit()


def test_postgres_schedule_crud_conflict_and_history():
    tenant, project = _tenant()
    with psycopg.connect(DSN) as connection:
        stores = _started(connection)
        stores.reports.create_definition(
            _definition(tenant, project, "RPT-3"),
            idempotency_key="sched-key",
            actor_id="u1",
            occurred_at=NOW,
        )

        created = stores.schedules.create(
            _schedule(tenant, project, "RPT-3"), actor_id="u1", occurred_at=NOW
        )
        assert created.revision == 1
        assert created.next_run_at == NOW + timedelta(hours=1)
        assert [item.schedule_id for item in stores.schedules.list(tenant, project, "RPT-3")] == ["SCH-1"]

        with pytest.raises(ReportScheduleError, match="REPORT_SCHEDULE_ALREADY_EXISTS"):
            stores.schedules.create(
                _schedule(tenant, project, "RPT-3"), actor_id="u1", occurred_at=NOW
            )

        updated = stores.schedules.update(
            _schedule(
                tenant,
                project,
                "RPT-3",
                next_run_at=NOW + timedelta(hours=2),
            ),
            expected_revision=1,
            actor_id="u1",
            occurred_at=NOW + timedelta(minutes=1),
        )
        assert updated.revision == 2
        assert updated.next_run_at == NOW + timedelta(hours=2)
        with pytest.raises(
            ReportScheduleRevisionConflict, match="REPORT_SCHEDULE_REVISION_CONFLICT"
        ):
            stores.schedules.update(
                _schedule(tenant, project, "RPT-3"),
                expected_revision=1,
                actor_id="u1",
                occurred_at=NOW + timedelta(minutes=2),
            )

        assert [event.event_type for event in stores.schedules.history(
            tenant, project, "RPT-3", "SCH-1"
        )] == ["created", "updated"]

        with pytest.raises(ReportScheduleRevisionConflict):
            stores.schedules.delete(
                tenant_id=tenant,
                project_id=project,
                report_id="RPT-3",
                schedule_id="SCH-1",
                expected_revision=1,
                actor_id="u1",
                occurred_at=NOW + timedelta(minutes=3),
            )
        stores.schedules.delete(
            tenant_id=tenant,
            project_id=project,
            report_id="RPT-3",
            schedule_id="SCH-1",
            expected_revision=2,
            actor_id="u1",
            occurred_at=NOW + timedelta(minutes=4),
        )
        with pytest.raises(KeyError, match="REPORT_SCHEDULE_NOT_FOUND"):
            stores.schedules.get(tenant, project, "RPT-3", "SCH-1")
        assert [event.event_type for event in stores.schedules.history(
            tenant, project, "RPT-3", "SCH-1"
        )] == ["created", "updated", "deleted"]
        connection.commit()


def test_postgres_claim_is_exclusive_and_lease_is_reclaimable():
    tenant, project = _tenant()
    with psycopg.connect(DSN) as connection:
        stores = _started(connection)
        stores.reports.create_definition(
            _definition(tenant, project, "RPT-4"),
            idempotency_key="claim-key",
            actor_id="u1",
            occurred_at=NOW,
        )
        stores.schedules.create(
            _schedule(
                tenant,
                project,
                "RPT-4",
                next_run_at=NOW - timedelta(minutes=5),
            ),
            actor_id="u1",
            occurred_at=NOW,
        )
        connection.commit()

        barrier = threading.Barrier(2)
        claimed: list[tuple] = []
        errors: list[BaseException] = []

        def worker(name: str) -> None:
            try:
                with psycopg.connect(DSN) as thread_connection:
                    store = PostgresReportScheduleStore(thread_connection)
                    barrier.wait(timeout=10)
                    claims = store.claim_due(
                        now=NOW, worker_id=name, lease_seconds=300, limit=5
                    )
                    thread_connection.commit()
                    claimed.extend(claims)
            except BaseException as exc:  # noqa: BLE001 - surfaced below
                errors.append(exc)

        threads = [
            threading.Thread(target=worker, args=(f"worker-{index}",))
            for index in range(2)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        assert not errors
        assert len(claimed) == 1

        first = claimed[0]
        assert first.scheduled_for == NOW - timedelta(minutes=5)
        assert stores.schedules.claim_due(
            now=NOW, worker_id="worker-late", lease_seconds=300, limit=5
        ) == ()

        reclaimed = stores.schedules.claim_due(
            now=NOW + timedelta(seconds=301),
            worker_id="worker-reclaim",
            lease_seconds=300,
            limit=5,
        )
        assert len(reclaimed) == 1
        assert reclaimed[0].claim_token != first.claim_token
        with pytest.raises(ReportScheduleError, match="REPORT_SCHEDULE_CLAIM_LOST"):
            stores.schedules.complete(
                first,
                run_id="RUN-SCH-SCH-1-20260501T085500Z",
                content_sha256="a" * 64,
                completed_at=NOW + timedelta(seconds=302),
                next_run_at=NOW + timedelta(days=1),
            )
        done = stores.schedules.complete(
            reclaimed[0],
            run_id="RUN-SCH-SCH-1-20260501T085500Z",
            content_sha256="a" * 64,
            completed_at=NOW + timedelta(seconds=302),
            next_run_at=NOW + timedelta(days=1),
        )
        assert done.last_status == "succeeded"
        assert done.attempts == 0
        assert done.next_run_at == NOW + timedelta(days=1)
        connection.commit()


def test_postgres_failure_backoff_and_error_truncation():
    tenant, project = _tenant()
    with psycopg.connect(DSN) as connection:
        stores = _started(connection)
        stores.reports.create_definition(
            _definition(tenant, project, "RPT-5"),
            idempotency_key="fail-key",
            actor_id="u1",
            occurred_at=NOW,
        )
        stores.schedules.create(
            _schedule(
                tenant,
                project,
                "RPT-5",
                next_run_at=NOW - timedelta(minutes=1),
            ),
            actor_id="u1",
            occurred_at=NOW,
        )
        claim = stores.schedules.claim_due(
            now=NOW, worker_id="worker", lease_seconds=300, limit=1
        )[0]
        failed = stores.schedules.fail(
            claim,
            error="X" * 900,
            failed_at=NOW,
            next_run_at=NOW + timedelta(minutes=5),
        )
        assert failed.last_status == "failed"
        assert failed.attempts == 1
        assert len(failed.last_error or "") == 500
        assert failed.next_run_at == NOW + timedelta(minutes=5)
        connection.commit()


def test_postgres_transaction_rollback_leaves_no_partial_state():
    tenant, project = _tenant()
    with psycopg.connect(DSN) as connection:
        stores = _started(connection)
        with pytest.raises(RuntimeError, match="injected"):
            with PostgresTransactionManager(connection).transaction():
                stores.reports.create_definition(
                    _definition(tenant, project, "RPT-ROLLBACK"),
                    idempotency_key="rollback-key",
                    actor_id="u1",
                    occurred_at=NOW,
                )
                stores.schedules.create(
                    _schedule(tenant, project, "RPT-ROLLBACK"),
                    actor_id="u1",
                    occurred_at=NOW,
                )
                raise RuntimeError("injected")

        with pytest.raises(KeyError, match="REPORT_NOT_FOUND"):
            stores.reports.get_definition(tenant, project, "RPT-ROLLBACK")
        assert stores.schedules.list(tenant, project, "RPT-ROLLBACK") == ()
        assert stores.reports.definition_history(
            tenant, project, "RPT-ROLLBACK"
        ) == ()
        # The idempotency key was not burned by the rolled-back attempt.
        created = stores.reports.create_definition(
            _definition(tenant, project, "RPT-ROLLBACK"),
            idempotency_key="rollback-key",
            actor_id="u1",
            occurred_at=NOW,
        )
        assert created.revision == 1
        connection.commit()


def test_postgres_runner_executes_replays_and_retries():
    tenant, project = _tenant()
    context = AuthorizationContext(
        tenant, project, "u1", frozenset({"planner"})
    )
    with psycopg.connect(DSN) as connection:
        stores = _started(connection)
        transactions = PostgresTransactionManager(connection)
        reports = ReportApplicationService(
            stores.reports,
            _Dataset(
                [
                    {"activity_id": "A1", "name": "Dig", "status": "Completed"},
                    {"activity_id": "A2", "name": "Pour", "status": "In Progress"},
                ]
            ),
            POLICY,
            transactions,
        )
        schedules = ReportScheduleService(
            stores.schedules, stores.reports, POLICY, transactions
        )
        reports.create_definition(
            _definition(tenant, project, "RPT-6"),
            idempotency_key="runner-def",
            context=context,
            actor_id="u1",
            occurred_at=NOW,
        )
        schedule = schedules.create(
            _schedule(tenant, project, "RPT-6", next_run_at=NOW),
            context=context,
            actor_id="u1",
            # Daily 09:00 UTC one day earlier resolves to exactly NOW.
            occurred_at=NOW - timedelta(days=1),
        )
        runner = ReportScheduleRunner(stores.schedules, reports, lease_seconds=120)

        outcomes = runner.run_due(now=NOW, worker_id="runner-1", limit=5)
        connection.commit()
        assert [outcome.state for outcome in outcomes] == ["succeeded"]
        run_id = f"RUN-SCH-SCH-1-{NOW:%Y%m%dT%H%M%SZ}"
        assert outcomes[0].run_id == run_id
        assert len(stores.reports.list_runs(tenant, project, "RPT-6")) == 1
        after = stores.schedules.get(tenant, project, "RPT-6", "SCH-1")
        assert after.last_status == "succeeded"
        assert after.next_run_at > schedule.next_run_at

        # Same occurrence replayed: the deterministic run id already exists,
        # so the runner reuses the stored immutable run instead of duplicating.
        stores.schedules.update(
            _schedule(
                tenant,
                project,
                "RPT-6",
                next_run_at=NOW,
            ),
            expected_revision=after.revision,
            actor_id="u1",
            occurred_at=NOW,
        )
        replay = runner.run_due(
            now=NOW + timedelta(minutes=1), worker_id="runner-2", limit=5
        )
        connection.commit()
        assert [outcome.state for outcome in replay] == ["succeeded"], replay[0].error
        assert replay[0].run_id == run_id
        assert len(stores.reports.list_runs(tenant, project, "RPT-6")) == 1

        # A failing execution records the attempt and backs off.
        failing = ReportApplicationService(
            stores.reports, _FailingDataset(), POLICY, transactions
        )
        schedules.create(
            _schedule(
                tenant,
                project,
                "RPT-6",
                schedule_id="SCH-FAIL",
                next_run_at=NOW,
            ),
            context=context,
            actor_id="u1",
            occurred_at=NOW - timedelta(days=1),
        )
        failing_runner = ReportScheduleRunner(
            stores.schedules, failing, lease_seconds=120, retry_base_minutes=5
        )
        failed_outcomes = failing_runner.run_due(
            now=NOW + timedelta(minutes=2), worker_id="runner-fail", limit=5
        )
        connection.commit()
        assert [outcome.state for outcome in failed_outcomes] == ["failed"]
        retrying = stores.schedules.get(tenant, project, "RPT-6", "SCH-FAIL")
        assert retrying.attempts == 1
        assert retrying.next_run_at == NOW + timedelta(minutes=7)
        assert failing_runner.run_due(
            now=NOW + timedelta(minutes=3), worker_id="runner-early", limit=5
        ) == ()
        connection.commit()
        failed_again = failing_runner.run_due(
            now=NOW + timedelta(minutes=8), worker_id="runner-retry", limit=5
        )
        connection.commit()
        assert [outcome.state for outcome in failed_again] == ["failed"]
        retried = stores.schedules.get(tenant, project, "RPT-6", "SCH-FAIL")
        assert retried.attempts == 2
        assert retried.next_run_at == NOW + timedelta(minutes=18)


def test_sqlite_and_postgres_agree_on_the_same_sequence():
    tenant, project = _tenant()
    derived = _definition(tenant, project, "RPT-PARITY")
    run = ReportRun(
        run_id="RUN-RPT-PARITY-1",
        tenant_id=tenant,
        project_id=project,
        report_id="RPT-PARITY",
        report_revision=1,
        project_revision=3,
        subject="activities",
        columns=("activity_id", "name"),
        rows=({"activity_id": "A1", "name": "Dig"},),
        generated_at=NOW,
        generated_by="u1",
        parameters=(("status", "Completed"),),
        parameter_sources=(("status", "default"),),
    )
    schedule = _schedule(tenant, project, "RPT-PARITY")

    sqlite_connection = sqlite3.connect(":memory:")
    try:
        sqlite_reports = SQLiteReportStore(sqlite_connection)
        sqlite_reports.initialize()
        sqlite_schedules = SQLiteReportScheduleStore(sqlite_connection)
        sqlite_schedules.initialize()
        sqlite_definition = sqlite_reports.create_definition(
            derived, idempotency_key="parity", actor_id="u1", occurred_at=NOW
        )
        sqlite_reports.save_run(run)
        sqlite_schedule = sqlite_schedules.create(
            schedule, actor_id="u1", occurred_at=NOW
        )
        sqlite_run = sqlite_reports.get_run(
            tenant, project, "RPT-PARITY", run.run_id
        )
    finally:
        sqlite_connection.close()

    with psycopg.connect(DSN) as connection:
        stores = _started(connection)
        postgres_definition = stores.reports.create_definition(
            derived, idempotency_key="parity", actor_id="u1", occurred_at=NOW
        )
        stores.reports.save_run(run)
        postgres_schedule = stores.schedules.create(
            schedule, actor_id="u1", occurred_at=NOW
        )
        postgres_run = stores.reports.get_run(
            tenant, project, "RPT-PARITY", run.run_id
        )
        connection.commit()

    assert postgres_definition.as_dict() == sqlite_definition.as_dict()
    assert postgres_run.as_dict() == sqlite_run.as_dict()
    assert postgres_schedule.as_dict() == sqlite_schedule.as_dict()
