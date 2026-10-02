from __future__ import annotations

import os
import threading
import uuid
from decimal import Decimal

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_resource_spread_repository import (
    P6ResourceSpreadBucket,
    P6ResourceSpreadPersistenceError,
    PostgresP6ResourceSpreadRepository,
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


def _scope(revision: int = 7) -> BackendScope:
    suffix = uuid.uuid4().hex
    return BackendScope(f"tenant-{suffix}", f"project-{suffix}", revision)


def _bucket(scope: BackendScope, value: str = "12.50") -> P6ResourceSpreadBucket:
    return P6ResourceSpreadBucket(
        scope=scope,
        spread_id="spread-1",
        resource_id="resource-1",
        period_id="2026-10",
        period_start="2026-10-01",
        period_end="2026-10-31",
        spread_type="PLANNED",
        metric="UNITS",
        value=Decimal(value),
        unit="hours",
    )


def test_postgres_resource_spread_is_scoped_idempotent_and_immutable(connection):
    repo = PostgresP6ResourceSpreadRepository(connection)
    repo.initialize()
    scope = _scope()
    item = _bucket(scope)

    with connection.transaction():
        assert repo.upsert(item) == item
        assert repo.upsert(item) == item

    assert repo.get(scope, item.spread_id, item.period_id) == item
    assert repo.list(scope) == (item,)

    other_scope = BackendScope("other-tenant", scope.project_id, scope.project_revision)
    assert repo.get(other_scope, item.spread_id, item.period_id) is None

    with pytest.raises(P6ResourceSpreadPersistenceError, match="REVISION_CONFLICT"):
        repo.get(
            BackendScope(scope.tenant_id, scope.project_id, scope.project_revision + 1),
            item.spread_id,
            item.period_id,
        )

    with pytest.raises(P6ResourceSpreadPersistenceError, match="IMMUTABLE_RESOURCE_SPREAD_BUCKET"):
        repo.upsert(_bucket(scope, value="13.50"))


def test_postgres_resource_spread_rollback_is_safe(connection):
    repo = PostgresP6ResourceSpreadRepository(connection)
    repo.initialize()
    scope = _scope()
    item = _bucket(scope)

    with pytest.raises(RuntimeError):
        with connection.transaction():
            repo.upsert(item)
            raise RuntimeError("force rollback")

    assert repo.get(scope, item.spread_id, item.period_id) is None


def test_postgres_resource_spread_concurrent_writers_report_conflict(postgres_dsn):
    scope = _scope()
    first = _bucket(scope, value="12.50")
    second = _bucket(scope, value="13.50")

    setup = psycopg.connect(postgres_dsn)
    conn1 = psycopg.connect(postgres_dsn)
    conn2 = psycopg.connect(postgres_dsn)
    try:
        PostgresP6ResourceSpreadRepository(setup).initialize()
        setup.commit()

        start = threading.Barrier(2)
        outcomes: list[str] = []
        errors: list[BaseException] = []
        lock = threading.Lock()

        def writer(conn, item) -> None:
            try:
                with conn.transaction():
                    start.wait(timeout=5)
                    PostgresP6ResourceSpreadRepository(conn).upsert(item)
                with lock:
                    outcomes.append("committed")
            except BaseException as exc:
                with lock:
                    errors.append(exc)

        t1 = threading.Thread(target=writer, args=(conn1, first))
        t2 = threading.Thread(target=writer, args=(conn2, second))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert not t1.is_alive()
        assert not t2.is_alive()
        assert outcomes.count("committed") == 1
        assert len(errors) == 1
        assert isinstance(errors[0], P6ResourceSpreadPersistenceError)
        assert str(errors[0]) == "IMMUTABLE_RESOURCE_SPREAD_BUCKET"
    finally:
        conn1.rollback()
        conn2.rollback()
        setup.rollback()
        conn1.close()
        conn2.close()
        setup.close()
