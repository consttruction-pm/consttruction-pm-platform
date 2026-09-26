from dataclasses import dataclass

from .offline_mutation import OfflineMutation
from .server_idempotency import InMemoryServerIdempotencyStore
from .sync_outcome import SyncDisposition, SyncOutcome


@dataclass
class IdempotentMutationGateway:
    store: InMemoryServerIdempotencyStore

    def execute(self, mutation: OfflineMutation, outcome: SyncOutcome) -> SyncOutcome:
        return self.store.execute_once(mutation, lambda: outcome)

    def execute_lazy(self, mutation: OfflineMutation, producer) -> SyncOutcome:
        return self.store.execute_once(mutation, producer)

    def conflict(self, mutation: OfflineMutation, error_code: str) -> SyncOutcome:
        return self.execute(
            mutation,
            SyncOutcome(
                mutation.mutation_id,
                SyncDisposition.CONFLICT,
                error_code=error_code,
            ),
        )
