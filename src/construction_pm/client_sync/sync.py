from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .adapter import ClientMutationRequest
from .mutation import OfflineMutation
from .outcome import SyncMutationOutcome
from .queue import OfflineMutationQueue
from .result import ClientMutationResult, present_mutation_payload
from .session import ClientProjectSession


class MutationSender(Protocol):
    def send(self, request: ClientMutationRequest) -> object: ...


@dataclass(frozen=True)
class SyncAttempt:
    mutation: OfflineMutation
    outcome: SyncMutationOutcome | None
    removed: bool
    result: ClientMutationResult | None = None


class OfflineSyncCoordinator:
    """Drives queued mutations through the authoritative client contract.

    The coordinator never calculates business results. It only owns queue state,
    transport invocation, and the disposition of authoritative sync outcomes.
    Online and offline mutation handling share the same normalized result
    boundary before a session revision can advance.
    """

    def __init__(
        self,
        queue: OfflineMutationQueue,
        transport: MutationSender,
        session: ClientProjectSession | None = None,
    ) -> None:
        self.queue = queue
        self.transport = transport
        self.session = session
        if self.session is not None:
            self.session.validate()

    def sync_once(self, limit: int = 1) -> list[SyncAttempt]:
        results: list[SyncAttempt] = []
        for queued in self.queue.peek(limit):
            attempted = self.queue.increment_attempt(queued)
            if self.session is not None and attempted.context != self.session.context:
                raise ValueError("queued mutation context does not match client session")
            request = ClientMutationRequest(
                context=attempted.context,
                operation=attempted.operation,
                idempotency_key=attempted.idempotency_key,
                mutation=attempted.mutation,
                expected_revision=attempted.expected_revision,
            )
            payload = self.transport.send(request)
            result = present_mutation_payload(payload)
            if result is None:
                raise ValueError("invalid client mutation result")

            if result.error is not None:
                raise ValueError("offline sync requires client-sync outcome")

            outcome = SyncMutationOutcome(
                status=result.status,
                operation=result.operation,
                revision=result.revision,
                error_code=None,
                retryable=None,
                idempotency_key=result.idempotency_key,
            )
            outcome.validate()

            if outcome.idempotency_key not in (None, attempted.idempotency_key):
                raise ValueError("sync outcome idempotency_key does not match mutation")
            if outcome.operation not in (None, attempted.operation):
                raise ValueError("sync outcome operation does not match mutation")

            removed = result.successful
            if removed:
                self.queue.remove(attempted)
                if self.session is not None:
                    self.session = self.session.apply_mutation_result(result)

            results.append(SyncAttempt(attempted, outcome, removed, result))
        return results
