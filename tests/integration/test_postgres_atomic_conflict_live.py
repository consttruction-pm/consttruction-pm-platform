import os
import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.client_sync.atomic_conflict import AtomicConflictSyncExecutor
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.postgres_sync_state import PostgresSyncStateStore
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome


class ConflictDelegate:
    def __init__(self):
        self.calls = 0

    def submit(self, mutation):
        self.calls += 1
        return SyncOutcome(
            mutation.mutation_id,
            SyncDisposition.CONFLICT,
            error_code="REVISION_CONFLICT",
        )


def _connect():
    return psycopg.connect(DSN)


def _mutation(key="live-conflict-key", mutation_id="live-conflict-m1"):
    return OfflineMutation(
        mutation_id,
        "live-ci-tenant",
        "live-ci-project",
        7,
        "update_activity",
        {"id": "A1"},
        key,
    )


def test_real_postgres_atomic_conflict_persists_and_replays():
    mutation = _mutation()
    with _connect() as conn:
        store = PostgresSyncStateStore(conn)
        store.initialize()
        delegate = ConflictDelegate()
        executor = AtomicConflictSyncExecutor(
            store,
            PostgresTransactionManager(conn),
            delegate,
        )

        first = executor.submit(mutation)
        conflict = store.get_conflict(
            mutation.mutation_id, mutation.tenant_id, mutation.project_id
        )

        assert first.disposition is SyncDisposition.CONFLICT
        assert first.error_code == "REVISION_CONFLICT"
        assert conflict is not None
        assert conflict.expected_revision == 7
        assert conflict.error_code == "REVISION_CONFLICT"

        second = executor.submit(mutation)
        assert second == first
        assert delegate.calls == 1


def test_real_postgres_same_key_executes_delegate_once_across_connections():
    mutation = _mutation(key="live-race-key", mutation_id="live-race-m1")
    import threading
    import concurrent.futures

    delegate_started = threading.Event()
    release_delegate = threading.Event()
    call_lock = threading.Lock()
    call_count = [0]

    class RaceDelegate:
        def submit(self, item):
            with call_lock:
                call_count[0] += 1
            delegate_started.set()
            release_delegate.wait(timeout=5)
            return SyncOutcome(item.mutation_id, SyncDisposition.CONFLICT, error_code="REVISION_CONFLICT")

    def worker():
        with _connect() as conn:
            store = PostgresSyncStateStore(conn)
            store.initialize()
            executor = AtomicConflictSyncExecutor(store, PostgresTransactionManager(conn), RaceDelegate())
            return executor.submit(mutation)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(worker)
        assert delegate_started.wait(timeout=5)
        second = pool.submit(worker)
        import time
        time.sleep(0.2)
        assert call_count[0] == 1
        release_delegate.set()
        first_result = first.result(timeout=10)
        second_result = second.result(timeout=10)

    assert first_result == second_result
    assert call_count[0] == 1
