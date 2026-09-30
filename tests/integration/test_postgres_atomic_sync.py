import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.client_sync.atomic_sync import AtomicSyncExecutor
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.postgres_sync_state import PostgresSyncStateStore
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome


DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")


class ConnectionTransaction:
    def __init__(self, connection):
        self.connection = connection

    def transaction(self):
        return self.connection.transaction()


class CountingDelegate:
    def __init__(self, entered=None, release=None):
        self.calls = 0
        self._lock = threading.Lock()
        self.entered = entered
        self.release = release

    def submit(self, mutation):
        with self._lock:
            self.calls += 1
        if self.entered is not None:
            self.entered.set()
        if self.release is not None:
            assert self.release.wait(5)
        return SyncOutcome(mutation.mutation_id, SyncDisposition.ACKNOWLEDGED)


def _mutation(key="live-postgres-idempotency"):
    return OfflineMutation(
        "mutation-1",
        "tenant-live",
        "project-live",
        1,
        "update_activity",
        {"id": "A1"},
        key,
    )


@pytest.fixture
def postgres():
    if not DSN:
        pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is required for live PostgreSQL tests")
    with psycopg.connect(DSN) as connection:
        PostgresSyncStateStore(connection).initialize()
        connection.commit()
        yield connection


def _cleanup(key):
    with psycopg.connect(DSN) as connection:
        connection.execute(
            "DELETE FROM sync_idempotency WHERE tenant_id=%s AND project_id=%s AND idempotency_key=%s",
            ("tenant-live", "project-live", key),
        )
        connection.commit()


def test_postgres_same_key_is_replayed_across_connections(postgres):
    key = "live-postgres-replay"
    try:
        first_delegate = CountingDelegate()
        with psycopg.connect(DSN) as connection:
            executor = AtomicSyncExecutor(
                PostgresSyncStateStore(connection),
                ConnectionTransaction(connection),
                first_delegate,
            )
            first = executor.submit(_mutation(key))

        second_delegate = CountingDelegate()
        with psycopg.connect(DSN) as connection:
            executor = AtomicSyncExecutor(
                PostgresSyncStateStore(connection),
                ConnectionTransaction(connection),
                second_delegate,
            )
            second = executor.submit(_mutation(key))

        assert first.disposition is SyncDisposition.ACKNOWLEDGED
        assert second == first
        assert first_delegate.calls == 1
        assert second_delegate.calls == 0
    finally:
        _cleanup(key)


def test_postgres_same_key_concurrent_execution_runs_delegate_once(postgres):
    key = f"live-postgres-concurrent-{uuid.uuid4()}"
    entered = threading.Event()
    release = threading.Event()
    delegates = [
        CountingDelegate(entered=entered, release=release),
        CountingDelegate(),
    ]

    try:
        def run(delegate):
            with psycopg.connect(DSN) as connection:
                executor = AtomicSyncExecutor(
                    PostgresSyncStateStore(connection),
                    ConnectionTransaction(connection),
                    delegate,
                )
                return executor.submit(_mutation(key))

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run, delegate) for delegate in delegates]
            assert entered.wait(5)
            time.sleep(0.2)
            assert sum(delegate.calls for delegate in delegates) == 1
            release.set()
            outcomes = [future.result(timeout=5) for future in futures]

        assert all(outcome.disposition is SyncDisposition.ACKNOWLEDGED for outcome in outcomes)
        assert sum(delegate.calls for delegate in delegates) == 1
    finally:
        release.set()
        _cleanup(key)


def test_postgres_same_key_with_different_mutation_is_rejected(postgres):
    key = "live-postgres-key-reuse"
    try:
        with psycopg.connect(DSN) as connection:
            executor = AtomicSyncExecutor(
                PostgresSyncStateStore(connection),
                ConnectionTransaction(connection),
                CountingDelegate(),
            )
            executor.submit(_mutation(key))

        changed = OfflineMutation(
            "mutation-2",
            "tenant-live",
            "project-live",
            1,
            "update_activity",
            {"id": "A2"},
            key,
        )
        with psycopg.connect(DSN) as connection:
            executor = AtomicSyncExecutor(
                PostgresSyncStateStore(connection),
                ConnectionTransaction(connection),
                CountingDelegate(),
            )
            with pytest.raises(ValueError, match="IDEMPOTENCY_KEY_REUSE"):
                executor.submit(changed)
    finally:
        _cleanup(key)
