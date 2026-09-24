from __future__ import annotations

from dataclasses import dataclass

from .mutation import OfflineMutation
from .result import ClientMutationResult

SYNC_UI_STATES = frozenset({'queued', 'applied', 'replayed', 'conflict', 'rejected'})

@dataclass(frozen=True)
class ClientSyncPresentation:
    """Framework-neutral offline/sync state for Web, Desktop, and Mobile."""
    operation: str
    idempotency_key: str
    state: str
    attempt: int
    error_code: str | None = None
    retryable: bool | None = None
    revision: int | None = None
    contract_version = 'client-sync-presentation.v1'

    @classmethod
    def from_queued(cls, mutation: OfflineMutation) -> 'ClientSyncPresentation':
        mutation.validate()
        return cls(mutation.operation, mutation.idempotency_key, 'queued', mutation.attempt)

    @classmethod
    def from_result(cls, mutation: OfflineMutation, result: ClientMutationResult) -> 'ClientSyncPresentation':
        mutation.validate()
        result.validate()
        if result.status not in {'applied','replayed','conflict','rejected'}:
            raise ValueError('sync presentation requires a client-sync outcome')
        if result.operation not in (None, mutation.operation):
            raise ValueError('sync result operation does not match mutation')
        if result.idempotency_key not in (None, mutation.idempotency_key):
            raise ValueError('sync result idempotency_key does not match mutation')
        return cls(mutation.operation, mutation.idempotency_key, result.status, mutation.attempt, result.error_code, result.retryable, result.revision)

    def validate(self) -> None:
        if not self.operation.strip(): raise ValueError('operation is required')
        if not self.idempotency_key.strip(): raise ValueError('idempotency_key is required')
        if self.state not in SYNC_UI_STATES: raise ValueError('unsupported sync presentation state')
        if self.attempt < 0: raise ValueError('attempt must be non-negative')
        if self.state in {'conflict','rejected'} and not self.error_code: raise ValueError('error_code is required')
        if self.state in {'applied','replayed'} and self.revision is None: raise ValueError('successful sync state requires revision')

    def to_payload(self) -> dict[str, object]:
        self.validate()
        return {'contract_version': self.contract_version,'operation':self.operation,'idempotency_key':self.idempotency_key,'state':self.state,'attempt':self.attempt,'error_code':self.error_code,'retryable':self.retryable,'revision':self.revision}
