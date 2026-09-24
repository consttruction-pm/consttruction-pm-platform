from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .offline_mutation import OfflineMutation
from .sync_outcome import SyncDisposition, SyncOutcome


class ApplicationMutationHandler(Protocol):
    def handle(self, mutation: OfflineMutation) -> None: ...


@dataclass(frozen=True)
class ApplicationSyncGateway:
    """Adapts versioned client mutations to the application mutation boundary."""

    tenant_id: str
    project_id: str
    handler: ApplicationMutationHandler

    def submit_mutation(self, mutation: OfflineMutation) -> SyncOutcome:
        if mutation.tenant_id != self.tenant_id or mutation.project_id != self.project_id:
            return SyncOutcome(
                mutation.mutation_id,
                SyncDisposition.REJECTED,
                error_code="INVALID_PROJECT_CONTEXT",
            )
        try:
            self.handler.handle(mutation)
        except Exception as exc:
            if exc.__class__.__name__ == "OptimisticLockError":
                return SyncOutcome(
                    mutation.mutation_id,
                    SyncDisposition.CONFLICT,
                    error_code="STALE_REVISION",
                )
            raise
        return SyncOutcome(mutation.mutation_id, SyncDisposition.ACKNOWLEDGED)


@dataclass(frozen=True)
class AtomicApplicationSyncGateway:
    """Application gateway with one transaction covering mutation outcome persistence."""

    tenant_id: str
    project_id: str
    executor: object

    def submit_mutation(self, mutation: OfflineMutation) -> SyncOutcome:
        if mutation.tenant_id != self.tenant_id or mutation.project_id != self.project_id:
            return SyncOutcome(mutation.mutation_id, SyncDisposition.REJECTED, error_code="INVALID_PROJECT_CONTEXT")
        return self.executor.submit(mutation)


@dataclass
class TransactionalApplicationSyncGateway:
    """Binds the application mutation handler to atomic idempotency/conflict persistence."""

    tenant_id: str
    project_id: str
    persistence: object
    transaction_manager: object
    handler: ApplicationMutationHandler

    def __post_init__(self) -> None:
        from .atomic_conflict import AtomicConflictSyncExecutor

        # The atomic executor consumes a submit(mutation) delegate. Wrap the
        # application handler with the existing application boundary so stale
        # revisions are translated into a deterministic conflict outcome before
        # idempotency/conflict persistence occurs inside the transaction.
        self._application_gateway = ApplicationSyncGateway(
            self.tenant_id,
            self.project_id,
            self.handler,
        )
        self._executor = AtomicConflictSyncExecutor(
            self.persistence,
            self.transaction_manager,
            self._application_gateway,
        )

    def submit_mutation(self, mutation: OfflineMutation) -> SyncOutcome:
        if mutation.tenant_id != self.tenant_id or mutation.project_id != self.project_id:
            return SyncOutcome(mutation.mutation_id, SyncDisposition.REJECTED, error_code="INVALID_PROJECT_CONTEXT")
        return self._executor.submit(mutation)
