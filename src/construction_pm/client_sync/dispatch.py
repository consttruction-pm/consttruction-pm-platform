from __future__ import annotations

from typing import Protocol

from .mutation import OfflineMutation
from .outcome import SyncMutationOutcome


class OfflineMutationTransport(Protocol):
    """Application/API transport boundary for applying one queued mutation."""

    def apply(self, mutation: OfflineMutation) -> SyncMutationOutcome: ...


class OfflineMutationDispatcher:
    """Validate and correlate a queued mutation with its authoritative outcome.

    Queue lifecycle decisions (remove, retry, or conflict resolution) remain
    outside this boundary. The dispatcher only enforces the shared typed
    transport contract and prevents a response for another operation or
    idempotency key from being accepted as the current mutation's outcome.
    """

    def dispatch(
        self,
        mutation: OfflineMutation,
        transport: OfflineMutationTransport,
    ) -> SyncMutationOutcome:
        mutation.validate()
        outcome = transport.apply(mutation)
        if not isinstance(outcome, SyncMutationOutcome):
            raise TypeError("offline mutation transport must return SyncMutationOutcome")
        outcome.validate()
        if outcome.operation != mutation.operation:
            raise ValueError("sync outcome operation does not match mutation")
        if outcome.idempotency_key != mutation.idempotency_key:
            raise ValueError("sync outcome idempotency_key does not match mutation")
        return outcome
