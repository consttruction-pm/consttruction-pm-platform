from __future__ import annotations

import os
import threading
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_baseline_repository import (
    P6Baseline,
    P6BaselinePersistenceError,
    PostgresP6BaselineRepository,
)
from construction_pm.p6_field_registry import get_field
from construction_pm.p6_field_registry_repository import (
    P6FieldRegistryPersistenceError,
    PersistedP6Field,
    PostgresP6FieldRegistryRepository,
)
from construction_pm.p6_financial_period_repository import (
    P6FinancialPeriod,
    P6FinancialPeriodPersistenceError,
    PostgresP6FinancialPeriodRepository,
)


@pytest.fixture(scope="module")
def postgres_dsn() -> str:
    dsn = os.getenv("P6_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("P6_TEST_POSTGRES_DSN is not configured")
    return dsn


@pytest.fixture()
def connection(postgres_dsn):
    conn = psycopg.connect(postgres_dsn)
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


def _scope() -> BackendScope:
    suffix = uuid.uuid4().hex
    return BackendScope(f"tenant-{suffix}", f"project-{suffix}", 7)


def test_postgres_baseline_is_scoped_immutable_and_rollback_safe(connection):
    repo = PostgresP6BaselineRepository(connection)
    repo.initialize()
    scope = _scope()
    item = P6Baseline(
        scope, "baseline-1", "Approved", "PRIMARY", 3,
        "2026-10-02T10:00:00Z", "metadata",
    )

    with connection.transaction():
        assert repo.upsert(item) == item

    assert repo.get(scope, "baseline-1") == item
    with pytest.raises(P6BaselinePersistenceError, match="REVISION_CONFLICT"):
        repo.get(BackendScope(scope.tenant_id, scope.project_id, 8), "baseline-1")
    with pytest.raises(P6BaselinePersistenceError, match="IMMUTABLE_BASELINE"):
        repo.upsert(
            P6Baseline(
                scope, "baseline-1", "Changed", "PRIMARY", 3,
                item.created_at, item.notes,
            )
        )

    rollback_id = "rollback-baseline"
    with pytest.raises(RuntimeError):
        with connection.transaction():
            repo.upsert(
                P6Baseline(
                    scope, rollback_id, "Rolled Back", "SECONDARY", 3,
                    item.created_at, item.notes,
                )
            )
            raise RuntimeError("force rollback")
    assert repo.get(scope, rollback_id) is None


def test_postgres_financial_period_is_scoped_immutable_and_idempotent(connection):
    repo = PostgresP6FinancialPeriodRepository(connection)
    repo.initialize()
    scope = _scope()
    item = P6FinancialPeriod(
        scope, "2026-10", "October 2026", "2026-10-01", "2026-10-31", "OPEN"
    )

    with connection.transaction():
        assert repo.upsert(item) == item
        assert repo.upsert(item) == item

    assert repo.get(scope, item.period_id) == item
    assert repo.list(scope) == (item,)
    with pytest.raises(P6FinancialPeriodPersistenceError, match="REVISION_CONFLICT"):
        repo.get(BackendScope(scope.tenant_id, scope.project_id, 8), item.period_id)
    with pytest.raises(P6FinancialPeriodPersistenceError, match="IMMUTABLE_FINANCIAL_PERIOD"):
        repo.upsert(
            P6FinancialPeriod(
                scope, item.period_id, "Changed", item.start_date,
                item.end_date, item.status,
            )
        )


def test_postgres_field_registry_persists_typed_metadata_and_scope(connection):
    repo = PostgresP6FieldRegistryRepository(connection)
    repo.initialize()
    scope = _scope()
    record = PersistedP6Field(scope, "p6-field-registry.v1", get_field("activity.activity_id"))

    with connection.transaction():
        assert repo.upsert_field(record) == record

    loaded = repo.get_field(scope, "p6-field-registry.v1", "activity.activity_id")
    assert loaded == record
    assert loaded is not None
    assert loaded.field.data_type.value == "string"

    other_scope = BackendScope("other-tenant", scope.project_id, scope.project_revision)
    assert repo.get_field(other_scope, "p6-field-registry.v1", "activity.activity_id") is None

    with pytest.raises(P6FieldRegistryPersistenceError, match="REVISION_CONFLICT"):
        repo.get_field(
            BackendScope(scope.tenant_id, scope.project_id, scope.project_revision + 1),
            "p6-field-registry.v1",
            "activity.activity_id",
        )


def test_postgres_baseline_concurrent_writers_report_conflict(postgres_dsn):
    scope = _scope()
    first = P6Baseline(
        scope, "baseline-race", "Writer 1", "PRIMARY", 3,
        "2026-10-02T10:00:00Z", "writer-1",
    )
    second = P6Baseline(
        scope, "baseline-race", "Writer 2", "PRIMARY", 3,
        "2026-10-02T10:00:00Z", "writer-2",
    )

    setup = psycopg.connect(postgres_dsn)
    conn1 = psycopg.connect(postgres_dsn)
    conn2 = psycopg.connect(postgres_dsn)
    try:
        PostgresP6BaselineRepository(setup).initialize()
        setup.commit()

        ready = threading.Barrier(2)
        inserted = threading.Event()
        outcomes: list[str] = []
        errors: list[BaseException] = []

        def writer(conn, item, hold_commit: bool) -> None:
            try:
                repo = PostgresP6BaselineRepository(conn)
                with conn.transaction():
                    ready.wait(timeout=5)
                    repo.upsert(item)
                    if hold_commit:
                        inserted.set()
                        assert not inserted.is_set() is False
                        # Keep the unique-key insert uncommitted while writer 2 reaches
                        # the same key. PostgreSQL then serializes the conflict check.
                        ready.wait(timeout=5)
                outcomes.append("committed")
            except BaseException as exc:
                errors.append(exc)

        # The first writer must reach the insert before the second writer is allowed
        # to attempt the same unique key.
        first_inserted = threading.Event()

        def writer1() -> None:
            try:
                with conn1.transaction():
                    PostgresP6BaselineRepository(conn1).upsert(first)
                    first_inserted.set()
                    ready.wait(timeout=5)
            except BaseException as exc:
                errors.append(exc)

        def writer2() -> None:
            try:
                first_inserted.wait(timeout=5)
                with conn2.transaction():
                    PostgresP6BaselineRepository(conn2).upsert(second)
                    outcomes.append("unexpected-success")
            except P6BaselinePersistenceError as exc:
                errors.append(exc)

        t1 = threading.Thread(target=writer1)
        t2 = threading.Thread(target=writer2)
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert not t1.is_alive()
        assert not t2.is_alive()
        assert not any(isinstance(exc, AssertionError) for exc in errors)
        assert any(
            isinstance(exc, P6BaselinePersistenceError)
            and str(exc) == "IMMUTABLE_BASELINE"
            for exc in errors
        )
        assert "unexpected-success" not in outcomes
    finally:
        conn1.rollback()
        conn2.rollback()
        setup.rollback()
        conn1.close()
        conn2.close()
        setup.close()
