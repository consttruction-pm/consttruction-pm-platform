from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.persistent_gateway import PersistentMutationGateway
from construction_pm.client_sync.idempotency_store import InMemoryDurableIdempotencyStore
from construction_pm.client_sync.server_gateway import IdempotentMutationGateway
from construction_pm.client_sync.server_idempotency import InMemoryServerIdempotencyStore
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome

class Delegate:
    def __init__(self): self.calls=0
    def submit(self, mutation):
        self.calls += 1
        return SyncOutcome(mutation.mutation_id, SyncDisposition.ACKNOWLEDGED)

def mutation():
    return OfflineMutation("m1","t1","p1",7,"update_activity",{"id":"A1"},"k1")

def test_persistent_gateway_replays_without_delegate_call():
    delegate=Delegate()
    gateway=PersistentMutationGateway(
        InMemoryDurableIdempotencyStore(),
        delegate,
    )
    first=gateway.submit(mutation())
    second=gateway.submit(mutation())
    assert first.disposition is SyncDisposition.ACKNOWLEDGED
    assert second.disposition is SyncDisposition.ACKNOWLEDGED
    assert delegate.calls == 1
