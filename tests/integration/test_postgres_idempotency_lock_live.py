import os
import threading
import time
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")

DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.client_sync.atomic_sync import AtomicSyncExecutor
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.postgres_sync_state import PostgresSyncStateStore
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome


def _mutation(key: str) -> OfflineMutation:
    return OfflineMutation(
        mutation_id="mutation-1",
        tenant_id="tenant",
        project_id="project",
        expected_revision=7,
        operation="update_activity",
        payload={"id": "A1"},
        idempotency_key=key,
    )


class CountingDelegate:
    def __init__(self, counter: list[int], counter_lock: threading.Lock, barrier=None):
        self.counter = counter
        self.counter_lock = counter_lock
        self.barrier = barrier

    def submit(self, mutation: OfflineMutation) -> SyncOutcome:
        with self.counter_lock:
            self.counter[0] += 1
        if self.barrier is not None:
            self.barrier.wait(timeout=5)
        else:
            time.sleep(0.1)
        return SyncOutcome(mutation.mutation_id, SyncDisposition.ACKNOWLEDGED)


def _submit(connection, mutation, counter, counter_lock, barrier=None):
    store = PostgresSyncStateStore(connection)
    executor = AtomicSyncExecutor(
        store,
        PostgresTransactionManager(connection),
        CountingDelegate(counter, counter_lock, barrier),
    )
    return executor.submit(mutation)


def test_same_idempotency_key_executes_delegate_exactly_once():
    with psycopg.connect(DSN) as setup_connection:
        PostgresSyncStateStore(setup_connection).initialize()
        setup_connection.commit()

    key = f"same-key-{uuid.uuid4().hex}"
    counter = [0]
    counter_lock = threading.Lock()
    results = []
    errors = []
    start = threading.Barrier(2)

    def worker():
        try:
            with psycopg.connect(DSN) as connection:
                start.wait(timeout=5)
                results.append(_submit(connection, _mutation(key), counter, counter_lock))
        except Exception as exc:  # pragma: no cover - failure is reported below
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not errors
    assert not any(thread.is_alive() for thread in threads)
    assert len(results) == 2
    assert all(result.disposition is SyncDisposition.ACKNOWLEDGED for result in results)
    assert all(result.mutation_id == "mutation-1" for result in results)
    assert counter[0] == 1


def test_distinct_idempotency_keys_can_execute_concurrently():
    with psycopg.connect(DSN) as setup_connection:
        PostgresSyncStateStore(setup_connection).initialize()
        setup_connection.commit()

    key_a = f"key-a-{uuid.uuid4().hex}"
    key_b = f"key-b-{uuid.uuid4().hex}"
    counter = [0]
    counter_lock = threading.Lock()
    delegate_barrier = threading.Barrier(2)
    results = []
    errors = []
    start = threading.Barrier(2)

    def worker(key):
        try:
            with psycopg.connect(DSN) as connection:
                start.wait(timeout=5)
                results.append(
                    _submit(
                        connection,
                        _mutation(key),
                        counter,
                        counter_lock,
                        delegate_barrier,
                    )
                )
        except Exception as exc:  # pragma: no cover - failure is reported below
            errors.append(exc)

    threads = [
        threading.Thread(target=worker, args=(key_a,)),
        threading.Thread(target=worker, args=(key_b,)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not errors
    assert not any(thread.is_alive() for thread in threads)
    assert len(results) == 2
    assert all(result.disposition is SyncDisposition.ACKNOWLEDGED for result in results)
    assert counter[0] == 2
