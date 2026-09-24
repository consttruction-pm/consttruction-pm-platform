from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .mutation import OfflineMutation
from .queue import OfflineMutationQueue


def build_refresh_retry_mutation(
    original: OfflineMutation,
    *,
    current_revision: int,
    idempotency_key: str,
    mutation: dict[str, object] | None = None,
) -> OfflineMutation:
    """Rebase a queued mutation onto authoritative revision state.

    The caller supplies the authoritative revision and a fresh idempotency key;
    this helper does not calculate or infer either value locally.
    """
    original.validate()
    if current_revision < 0:
        raise ValueError("current_revision must be non-negative")
    if not idempotency_key.strip():
        raise ValueError("idempotency_key is required")
    if idempotency_key == original.idempotency_key:
        raise ValueError("replacement mutation requires a new idempotency_key")
    return OfflineMutation(
        context=original.context,
        operation=original.operation,
        idempotency_key=idempotency_key,
        mutation=dict(original.mutation if mutation is None else mutation),
        expected_revision=current_revision,
        attempt=0,
    )


class ConflictResolutionAction(str, Enum):
    DISCARD = "discard"
    REFRESH_AND_RETRY = "refresh_and_retry"
    DEFER = "defer"


@dataclass(frozen=True)
class ConflictResolutionRequest:
    action: ConflictResolutionAction
    original: OfflineMutation
    replacement: OfflineMutation | None = None

    def validate(self) -> None:
        self.original.validate()
        if self.action is ConflictResolutionAction.REFRESH_AND_RETRY:
            if self.replacement is None:
                raise ValueError("refresh_and_retry requires a replacement mutation")
            self.replacement.validate()
            if self.replacement.idempotency_key == self.original.idempotency_key:
                raise ValueError("replacement mutation requires a new idempotency_key")
            if self.replacement.expected_revision is None:
                raise ValueError("replacement mutation requires current expected_revision")
        elif self.replacement is not None:
            raise ValueError("replacement mutation is only valid for refresh_and_retry")


class ConflictResolutionService:
    """Applies explicit client conflict actions without changing authority."""

    def __init__(self, queue: OfflineMutationQueue) -> None:
        self.queue = queue

    def resolve(self, request: ConflictResolutionRequest) -> OfflineMutation:
        request.validate()

        if request.action is ConflictResolutionAction.DISCARD:
            self.queue.remove(request.original)
            return request.original

        if request.action is ConflictResolutionAction.DEFER:
            self.queue.defer(request.original)
            return request.original

        replacement = request.replacement
        assert replacement is not None

        # The old mutation is removed only after the replacement is validated.
        # No local calculation or revision rewriting is performed here.
        self.queue.remove(request.original)
        self.queue.enqueue(replacement)
        return replacement
