from contextlib import contextmanager
from construction_pm.client_sync.atomic_sync import AtomicSyncExecutor
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.server_idempotency import IdempotencyRecord
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome

class Store:
    def __init__(self): self.record=None
    def lock_idempotency(self,t,p,k): pass
    def get_idempotency(self,t,p,k): return self.record
    def put_idempotency(self,r): self.record=r
    def save_conflict(self,*a): pass
    def get_conflict(self,*a): return None

class Tx:
    def __init__(self): self.commits=0; self.rollbacks=0
    @contextmanager
    def transaction(self):
        try:
            yield
            self.commits+=1
        except Exception:
            self.rollbacks+=1
            raise

class Delegate:
    def __init__(self,fail=False): self.calls=0; self.fail=fail
    def submit(self,m):
        self.calls+=1
        if self.fail: raise RuntimeError("delegate failure")
        return SyncOutcome(m.mutation_id,SyncDisposition.ACKNOWLEDGED)

def m():
    return OfflineMutation("m1","t1","p1",1,"update_activity",{"id":"A1"},"k1")

def test_atomic_success_commits():
    tx=Tx(); s=Store(); d=Delegate()
    result=AtomicSyncExecutor(s,tx,d).submit(m())
    assert result.disposition is SyncDisposition.ACKNOWLEDGED
    assert tx.commits==1 and tx.rollbacks==0 and d.calls==1

def test_atomic_failure_rolls_back_and_does_not_persist():
    tx=Tx(); s=Store(); d=Delegate(True)
    try: AtomicSyncExecutor(s,tx,d).submit(m())
    except RuntimeError: pass
    assert tx.commits==0 and tx.rollbacks==1 and s.record is None
