from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .adapter import ClientMutationRequest, ClientMutationTransport, normalize_sync_outcome
from .mutation import OfflineMutation
from .outcome import SyncMutationOutcome
from .queue import OfflineMutationQueue


class MutationSender(Protocol):
    def send(self, request: ClientMutationRequest) -> object: ...


@dataclass(frozen=True)
class SyncAttempt:
    mutation: OfflineMutation
    outcome: SyncMutationOutcome | None
    removed: bool


class OfflineSyncCoordinator:
    """Drives queued mutations through the authoritative client contract.

    The coordinator never calculates business results. It only owns queue state,
    transport invocation, and the disposition of authoritative sync outcomes.
    """

    def __init__(self, queue: OfflineMutationQueue, transport: MutationSender) -> None:
        self.queue = queue
        self.transport = transport

    def sync_once(self, limit: int = 1) -> list[SyncAttempt]:
        results: list[SyncAttempt] = []
        for queued in self.queue.peek(limit):
            attempted = self.queue.increment_attempt(queued)
            request = ClientMutationRequest(
                context=attempted.context,
                operation=attempted.operation,
                idempotency_key=attempted.idempotency_key,
                mutation=attempted.mutation,
                expected_revision=attempted.expected_revision,
            )
            payload = self.transport.send(request)
            outcome = normalize_sync_outcome(payload)
            if outcome is None:
                raise ValueError("invalid client-sync outcome")
            if outcome.idempotency_key not in (None, attempted.idempotency_key):
                raise ValueError("sync outcome idempotency_key does not match mutation")
            if outcome.operation not in (None, attempted.operation):
                raise ValueError("sync outcome operation does not match mutation")

            removed = outcome.status in {"applied", "replayed"}
            if removed:
                self.queue.remove(attempted)

            results.append(SyncAttempt(attempted, outcome, removed))
        return results
