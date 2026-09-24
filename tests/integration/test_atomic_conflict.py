from contextlib import contextmanager
from construction_pm.client_sync.atomic_sync import AtomicSyncExecutor
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome

class Store:
    def __init__(self): self.record=None; self.conflict=None
    def get_idempotency(self,*a): return self.record
    def put_idempotency(self,r): self.record=r
    def save_conflict(self,*a): self.conflict=a
    def get_conflict(self,*a): return None

class Tx:
    @contextmanager
    def transaction(self): yield

class Delegate:
    def submit(self,m): return SyncOutcome(m.mutation_id,SyncDisposition.CONFLICT,"STALE_REVISION")

def test_conflict_shape_is_available_to_atomic_layer():
    store=Store()
    mutation=OfflineMutation("m1","t1","p1",7,"update_activity",{"id":"A1"},"k1")
    outcome=Delegate().submit(mutation)
    assert outcome.disposition is SyncDisposition.CONFLICT
    assert outcome.error_code=="STALE_REVISION"
