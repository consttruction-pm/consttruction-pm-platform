from dataclasses import dataclass
from .offline_mutation import OfflineMutation
from .persistence_contract import SyncStatePersistence
from .sync_outcome import SyncDisposition, SyncOutcome
from .server_idempotency import mutation_fingerprint
from .server_idempotency import IdempotencyRecord


class AtomicSyncExecutor:
    """Coordinates sync persistence through an injected transaction boundary."""

    def __init__(self, persistence: SyncStatePersistence, transaction_manager, delegate):
        self.persistence = persistence
        self.transaction_manager = transaction_manager
        self.delegate = delegate

    def submit(self, mutation: OfflineMutation) -> SyncOutcome:
        fingerprint = mutation_fingerprint(mutation)
        with self.transaction_manager.transaction():
            self.persistence.lock_idempotency(
                mutation.tenant_id, mutation.project_id, mutation.idempotency_key
            )
            existing = self.persistence.get_idempotency(
                mutation.tenant_id, mutation.project_id, mutation.idempotency_key
            )
            if existing is not None:
                if existing.fingerprint != fingerprint:
                    raise ValueError("IDEMPOTENCY_KEY_REUSE")
                return _outcome(existing)

            outcome = _submit_delegate(self.delegate, mutation)
            self.persistence.put_idempotency(
                IdempotencyRecord(
                    mutation.tenant_id,
                    mutation.project_id,
                    mutation.idempotency_key,
                    mutation.mutation_id,
                    fingerprint,
                    {
                        "mutation_id": outcome.mutation_id,
                        "disposition": outcome.disposition.value,
                        "error_code": outcome.error_code,
                        "retry_after_seconds": outcome.retry_after_seconds,
                    },
                )
            )
            self._after_outcome(mutation, outcome)
            return outcome

    def _after_outcome(self, mutation: OfflineMutation, outcome: SyncOutcome) -> None:
        """Hook for additional persistence that must share this transaction."""
        return None


def _submit_delegate(delegate, mutation: OfflineMutation) -> SyncOutcome:
    """Support both the low-level submit contract and application gateway contract."""
    submit_mutation = getattr(delegate, "submit_mutation", None)
    if submit_mutation is not None:
        return submit_mutation(mutation)
    return delegate.submit(mutation)


def _outcome(record: IdempotencyRecord) -> SyncOutcome:
    return SyncOutcome(
        mutation_id=record.mutation_id,
        disposition=SyncDisposition(record.outcome["disposition"]),
        error_code=record.outcome.get("error_code"),
        retry_after_seconds=record.outcome.get("retry_after_seconds"),
    )
