import sqlite3
from construction_pm.client_sync.conflict import ConflictContext
from construction_pm.client_sync.server_idempotency import IdempotencyRecord
from construction_pm.client_sync.sqlite_sync_state import SQLiteSyncStateStore

def test_sqlite_sync_state_round_trip():
    store=SQLiteSyncStateStore(sqlite3.connect(":memory:")); store.initialize()
    record=IdempotencyRecord("t1","p1","k1","m1","f1",{"ok":True})
    store.put_idempotency(record)
    assert store.get_idempotency("t1","p1","k1")==record
    context=ConflictContext("STALE_REVISION",7,8,("discard","refresh_and_retry","defer"),{"resource":"activity"})
    store.save_conflict("m1","t1","p1",context)
    assert store.get_conflict("m1","t1","p1")==context

def test_sqlite_idempotency_key_reuse_is_rejected():
    store=SQLiteSyncStateStore(sqlite3.connect(":memory:")); store.initialize()
    store.put_idempotency(IdempotencyRecord("t1","p1","k1","m1","f1",{"ok":True}))
    try: store.put_idempotency(IdempotencyRecord("t1","p1","k1","m2","f2",{"ok":False}))
    except ValueError as exc: assert str(exc)=="IDEMPOTENCY_KEY_REUSE"
    else: raise AssertionError("key reuse must fail")
