from dataclasses import dataclass

from .offline_store import OfflineMutationStore
from .sync_outcome import SyncDisposition, SyncOutcome
from .sync_transport import SyncTransport


@dataclass
class SyncRunner:
    store: OfflineMutationStore
    transport: SyncTransport

    def run_once(self) -> tuple[SyncOutcome, ...]:
        outcomes: list[SyncOutcome] = []
        for mutation in self.store.pending():
            outcome = self.transport.submit(mutation)
            outcomes.append(outcome)
            if outcome.disposition == SyncDisposition.ACKNOWLEDGED:
                self.store.acknowledge(mutation.mutation_id)
            elif outcome.disposition in {
                SyncDisposition.CONFLICT,
                SyncDisposition.REJECTED,
            }:
                # Preserve the mutation for explicit conflict/rejection handling.
                continue
            elif outcome.disposition == SyncDisposition.RETRY:
                # Preserve it for a later retry.
                continue
        return tuple(outcomes)
