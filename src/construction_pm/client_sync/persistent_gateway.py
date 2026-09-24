from dataclasses import dataclass
from .conflict import ConflictContext
from .offline_mutation import OfflineMutation
from .persistence_contract import SyncStatePersistence
from .server_idempotency import IdempotencyRecord
from .server_gateway import IdempotentMutationGateway
from .sync_outcome import SyncDisposition, SyncOutcome
from .server_idempotency import mutation_fingerprint

@dataclass
class PersistentMutationGateway:
    persistence: SyncStatePersistence
    delegate: IdempotentMutationGateway

    def submit(self, mutation: OfflineMutation) -> SyncOutcome:
        existing = self.persistence.get_idempotency(
            mutation.tenant_id, mutation.project_id, mutation.idempotency_key
        )
        fingerprint = mutation_fingerprint(mutation)
        if existing is not None:
            if existing.fingerprint != fingerprint:
                raise ValueError("IDEMPOTENCY_KEY_REUSE")
            return SyncOutcome(
                mutation_id=existing.mutation_id,
                disposition=SyncDisposition(existing.outcome["disposition"]),
                error_code=existing.outcome.get("error_code"),
                retry_after_seconds=existing.outcome.get("retry_after_seconds"),
            )

        outcome = self.delegate.submit(mutation)
        record = IdempotencyRecord(
            tenant_id=mutation.tenant_id,
            project_id=mutation.project_id,
            idempotency_key=mutation.idempotency_key,
            mutation_id=mutation.mutation_id,
            fingerprint=fingerprint,
            outcome={
                "mutation_id": outcome.mutation_id,
                "disposition": outcome.disposition.value,
                "error_code": outcome.error_code,
                "retry_after_seconds": outcome.retry_after_seconds,
            },
        )
        self.persistence.put_idempotency(record)
        if outcome.disposition.value == "conflict":
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
        return outcome
