import os
import threading
import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.client_sync.postgres_sync_state import PostgresSyncStateStore
from construction_pm.client_sync.server_idempotency import IdempotencyRecord

def _connect():
    return psycopg.connect(DSN)

def test_real_sync_state_round_trip():
    with _connect() as conn:
        store = PostgresSyncStateStore(conn)
        store.initialize()
        record = IdempotencyRecord("ci-t1","ci-p1","ci-k1","ci-m1","ci-f1",{"disposition":"acknowledged"})
        store.put_idempotency(record)
        assert store.get_idempotency("ci-t1","ci-p1","ci-k1") == record

def test_real_idempotency_race_allows_only_one_identity():
    def worker(suffix, results):
        try:
            with _connect() as conn:
                store=PostgresSyncStateStore(conn)
                store.initialize()
                store.put_idempotency(IdempotencyRecord("race-t","race-p","race-k",f"m-{suffix}",f"f-{suffix}",{"ok":True}))
                conn.commit()
                results.append("ok")
        except Exception as exc:
            results.append(type(exc).__name__)

    results=[]
    threads=[threading.Thread(target=worker,args=(i,results)) for i in range(2)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert len(results)==2
    assert results.count("ok") == 1
    assert results.count("ValueError") == 1


def test_real_same_mutation_key_serializes_delegate_execution():
    from construction_pm.client_sync.atomic_sync import AtomicSyncExecutor
    from construction_pm.client_sync.offline_mutation import OfflineMutation
    from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
    from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome

    calls = []
    entered = threading.Event()
    release = threading.Event()

    def delegate(mutation):
        calls.append(mutation.mutation_id)
        entered.set()
        assert release.wait(timeout=10)
        return SyncOutcome(mutation.mutation_id, SyncDisposition.ACKNOWLEDGED)

    def worker(results):
        try:
            with _connect() as conn:
                store = PostgresSyncStateStore(conn)
                store.initialize()
                executor = AtomicSyncExecutor(
                    store,
                    PostgresTransactionManager(conn),
                    delegate,
                )
                mutation = OfflineMutation(
                    "race-mutation",
                    "race-exec-t",
                    "race-exec-p",
                    1,
                    "update_activity",
                    {"activity_id": "A1"},
                    "race-exec-key",
                )
                results.append(executor.submit(mutation).disposition.value)
        except Exception as exc:
            results.append(type(exc).__name__)

    results = []
    first = threading.Thread(target=worker, args=(results,))
    second = threading.Thread(target=worker, args=(results,))
    first.start()
    assert entered.wait(timeout=10)
    second.start()

    # The advisory transaction lock must prevent the second delegate execution
    # while the first transaction is still open.
    assert not release.wait(timeout=0.5)
    assert calls == ["race-mutation"]

    release.set()
    first.join(timeout=20)
    second.join(timeout=20)

    assert not first.is_alive()
    assert not second.is_alive()
    assert len(results) == 2
    assert sorted(results) == ["acknowledged", "acknowledged"]
    assert calls == ["race-mutation"]
