from .atomic_sync import AtomicSyncExecutor
from .conflict import ConflictContext
from .offline_mutation import OfflineMutation
from .server_idempotency import IdempotencyRecord
from .server_idempotency import mutation_fingerprint

class AtomicConflictSyncExecutor(AtomicSyncExecutor):
    def _after_outcome(self, mutation: OfflineMutation, outcome) -> None:
        if outcome.disposition.value != "conflict":
            return
        self.persistence.save_conflict(
            mutation.mutation_id,
            mutation.tenant_id,
            mutation.project_id,
            ConflictContext(
                error_code=outcome.error_code or "SYNC_CONFLICT",
                expected_revision=mutation.expected_revision,
                actual_revision=None,
                available_actions=("discard", "refresh_and_retry", "defer"),
                details={},
            ),
        )
