from dataclasses import dataclass

from .offline_mutation import OfflineMutation
from .server_idempotency import InMemoryServerIdempotencyStore
from .sync_outcome import SyncDisposition, SyncOutcome


@dataclass
class IdempotentMutationGateway:
    store: InMemoryServerIdempotencyStore

    def execute(self, mutation: OfflineMutation, outcome: SyncOutcome) -> SyncOutcome:
        existing = self.store.lookup(mutation)
        if existing is not None:
            if existing.outcome.mutation_id != mutation.mutation_id:
                raise ValueError("IDEMPOTENCY_KEY_REUSE")
            return existing.outcome

        self.store.remember(mutation, outcome)
        return outcome

    def conflict(self, mutation: OfflineMutation, error_code: str) -> SyncOutcome:
        return self.execute(
            mutation,
            SyncOutcome(mutation.mutation_id, SyncDisposition.CONFLICT, error_code=error_code),
        )
