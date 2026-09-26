import sqlite3

import pytest

from construction_pm.client_sync.atomic_sync import AtomicSyncExecutor
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.sqlite_sync_state import SQLiteSyncStateStore
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome


class SQLiteTransactionManager:
    def __init__(self, connection):
        self.connection = connection

    def transaction(self):
        manager = self

        class Context:
            def __enter__(self):
                manager.connection.execute("BEGIN")

            def __exit__(self, exc_type, exc, tb):
                if exc_type:
                    manager.connection.rollback()
                else:
                    manager.connection.commit()
                return False

        return Context()


def _mutation():
    return OfflineMutation(
        "m1", "tenant", "project", 3, "update_activity", {"id": "A1"}, "key-1"
    )


def test_sqlite_atomic_rollback_removes_idempotency_and_conflict_state():
    connection = sqlite3.connect(":memory:")
    store = SQLiteSyncStateStore(connection)
    store.initialize()

    class FailingDelegate:
        def submit(self, mutation):
            raise RuntimeError("delegate failed")

    executor = AtomicSyncExecutor(
        store, SQLiteTransactionManager(connection), FailingDelegate()
    )

    with pytest.raises(RuntimeError, match="delegate failed"):
        executor.submit(_mutation())

    assert store.get_idempotency("tenant", "project", "key-1") is None
    lock_row = connection.execute(
        "SELECT 1 FROM sync_idempotency_locks WHERE tenant_id=? AND project_id=? AND idempotency_key=?",
        ("tenant", "project", "key-1"),
    ).fetchone()
    assert lock_row is None


def test_sqlite_atomic_success_commits_idempotency():
    connection = sqlite3.connect(":memory:")
    store = SQLiteSyncStateStore(connection)
    store.initialize()

    class Delegate:
        def submit(self, mutation):
            return SyncOutcome(mutation.mutation_id, SyncDisposition.ACKNOWLEDGED)

    executor = AtomicSyncExecutor(
        store, SQLiteTransactionManager(connection), Delegate()
    )

    outcome = executor.submit(_mutation())

    assert outcome.disposition is SyncDisposition.ACKNOWLEDGED
    assert store.get_idempotency("tenant", "project", "key-1") is not None
