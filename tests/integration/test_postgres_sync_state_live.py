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
