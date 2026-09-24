from dataclasses import dataclass
from typing import Protocol

from .offline_mutation import OfflineMutation
from .sync_outcome import SyncDisposition, SyncOutcome
from .sync_transport import SyncTransport


class ApplicationMutationGateway(Protocol):
    def submit_mutation(self, mutation: OfflineMutation) -> SyncOutcome: ...


@dataclass(frozen=True)
class ApplicationSyncAdapter:
    gateway: ApplicationMutationGateway

    def submit(self, mutation: OfflineMutation) -> SyncOutcome:
        outcome = self.gateway.submit_mutation(mutation)
        if outcome.mutation_id != mutation.mutation_id:
            raise ValueError("MUTATION_ID_MISMATCH")
        return outcome

    def as_transport(self) -> SyncTransport:
        return self
