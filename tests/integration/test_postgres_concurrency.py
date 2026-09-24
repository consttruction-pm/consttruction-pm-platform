import threading
from construction_pm.client_sync.postgres_sync_state import PostgresSyncStateStore
from construction_pm.client_sync.server_idempotency import IdempotencyRecord

class ConcurrentFakeConnection:
    def __init__(self):
        self.lock=threading.Lock()
        self.rows={}
        self.attempts=0
    def execute(self, sql, params=()):
        with self.lock:
            self.attempts += 1
        class Cursor:
            def fetchone(inner): return None
        return Cursor()

def test_concurrency_harness_has_deterministic_parallel_shape():
    c=ConcurrentFakeConnection()
    store=PostgresSyncStateStore(c)
    barrier=threading.Barrier(2)
    results=[]
    def worker():
        barrier.wait()
        results.append("submitted")
    threads=[threading.Thread(target=worker) for _ in range(2)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert sorted(results)==["submitted","submitted"]
    assert c.attempts==0
