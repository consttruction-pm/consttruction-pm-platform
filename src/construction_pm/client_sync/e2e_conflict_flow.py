from dataclasses import dataclass
from .offline_mutation import OfflineMutation
from .sync_outcome import SyncDisposition, SyncOutcome
from .sync_transport import SyncTransport


@dataclass(frozen=True)
class ConflictFlowResult:
    mutation_id: str
    outcome: SyncOutcome
    requires_refresh: bool
    preserved_expected_revision: int


class ConflictSyncFlow:
    def __init__(self, transport: SyncTransport):
        self._transport = transport

    def submit_once(self, mutation: OfflineMutation) -> ConflictFlowResult:
        outcome = self._transport.submit(mutation)
        return ConflictFlowResult(
            mutation_id=mutation.mutation_id,
            outcome=outcome,
            requires_refresh=outcome.disposition is SyncDisposition.CONFLICT,
            preserved_expected_revision=mutation.expected_revision,
        )
