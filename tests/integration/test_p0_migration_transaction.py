from __future__ import annotations

import pytest

from construction_pm.client_sync.atomic_sync import AtomicSyncExecutor
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.postgres_sync_state import PostgresSyncStateStore
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome


class RecordingCursor:
    def __init__(self, row=None):
        self.row = row

    def fetchone(self):
        return self.row


class RecordingConnection:
    def __init__(self):
        self.sql: list[tuple[str, tuple[object, ...]]] = []
        self.commits = 0
        self.rollbacks = 0

    def execute(self, sql: str, params: tuple[object, ...] = ()):
        self.sql.append((sql, params))
        return RecordingCursor()

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_sync_state_schema_initialization_is_repeatable_and_scoped() -> None:
    connection = RecordingConnection()
    store = PostgresSyncStateStore(connection)

    store.initialize()
    store.initialize()

    assert len(connection.sql) == 4
    idempotency_sql = connection.sql[0][0]
    conflict_sql = connection.sql[1][0]

    assert idempotency_sql.startswith("CREATE TABLE IF NOT EXISTS sync_idempotency")
    assert "tenant_id TEXT NOT NULL" in idempotency_sql
    assert "project_id TEXT NOT NULL" in idempotency_sql
    assert "idempotency_key TEXT NOT NULL" in idempotency_sql
    assert "mutation_id TEXT NOT NULL" in idempotency_sql
    assert "fingerprint TEXT NOT NULL" in idempotency_sql
    assert "outcome_json TEXT NOT NULL" in idempotency_sql
    assert "PRIMARY KEY (tenant_id, project_id, idempotency_key)" in idempotency_sql

    assert conflict_sql.startswith("CREATE TABLE IF NOT EXISTS sync_conflicts")
    assert "tenant_id TEXT NOT NULL" in conflict_sql
    assert "project_id TEXT NOT NULL" in conflict_sql
    assert "mutation_id TEXT NOT NULL" in conflict_sql
    assert "expected_revision INTEGER NOT NULL" in conflict_sql
    assert "available_actions_json TEXT NOT NULL" in conflict_sql
    assert "details_json TEXT NOT NULL" in conflict_sql
    assert "PRIMARY KEY (tenant_id, project_id, mutation_id)" in conflict_sql


class Persistence:
    def __init__(self, fail=False):
        self.fail = fail
        self.saved = []

    def get_idempotency(self, tenant_id, project_id, key):
        return None

    def put_idempotency(self, record):
        if self.fail:
            raise RuntimeError("persistence failure")
        self.saved.append(record)

    def lock_idempotency(self, tenant_id, project_id, key):
        return None


class Delegate:
    def submit(self, mutation):
        return SyncOutcome(mutation.mutation_id, SyncDisposition.ACKNOWLEDGED)


def _mutation() -> OfflineMutation:
    return OfflineMutation(
        mutation_id="mutation-1",
        tenant_id="tenant",
        project_id="project",
        expected_revision=1,
        operation="update_activity",
        payload={"id": "A1"},
        idempotency_key="key-1",
    )


def test_atomic_persistence_failure_rolls_back_transaction() -> None:
    connection = RecordingConnection()
    persistence = Persistence(fail=True)
    executor = AtomicSyncExecutor(
        persistence,
        PostgresTransactionManager(connection),
        Delegate(),
    )

    with pytest.raises(RuntimeError, match="persistence failure"):
        executor.submit(_mutation())

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert persistence.saved == []


def test_atomic_success_commits_transaction() -> None:
    connection = RecordingConnection()
    persistence = Persistence()
    executor = AtomicSyncExecutor(
        persistence,
        PostgresTransactionManager(connection),
        Delegate(),
    )

    outcome = executor.submit(_mutation())

    assert outcome.disposition is SyncDisposition.ACKNOWLEDGED
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert len(persistence.saved) == 1
