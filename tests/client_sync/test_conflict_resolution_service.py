from construction_pm.client_sync.conflict import (
    ConflictResolutionAction,
    ConflictResolutionRequest,
    ConflictResolutionService,
)
from construction_pm.client_sync.context import OfflineProjectContext
from construction_pm.client_sync.mutation import OfflineMutation
from construction_pm.client_sync.queue import InMemoryOfflineMutationQueue


def make_mutation(key="old", revision=7, activity="A-1"):
    return OfflineMutation(
        context=OfflineProjectContext("t", "c", "p", 1, None, None, 1, 1),
        operation="update_activity",
        idempotency_key=key,
        mutation={"activity_id": activity, "name": "Foundation"},
        expected_revision=revision,
    )


def test_discard_removes_conflict_after_explicit_action():
    queue = InMemoryOfflineMutationQueue()
    original = make_mutation()
    queue.enqueue(original)

    result = ConflictResolutionService(queue).resolve(
        ConflictResolutionRequest(ConflictResolutionAction.DISCARD, original)
    )

    assert result == original
    assert queue.peek() == []


def test_defer_preserves_conflict_without_making_it_retryable():
    queue = InMemoryOfflineMutationQueue()
    original = make_mutation()
    queue.enqueue(original)

    ConflictResolutionService(queue).resolve(
        ConflictResolutionRequest(ConflictResolutionAction.DEFER, original)
    )

    assert queue.peek() == []


def test_refresh_and_retry_requires_new_key_and_current_revision():
    queue = InMemoryOfflineMutationQueue()
    original = make_mutation()
    queue.enqueue(original)
    replacement = make_mutation(key="new", revision=8, activity="A-1")

    result = ConflictResolutionService(queue).resolve(
        ConflictResolutionRequest(
            ConflictResolutionAction.REFRESH_AND_RETRY,
            original,
            replacement,
        )
    )

    assert result == replacement
    assert queue.peek() == [replacement]


def test_refresh_and_retry_rejects_reused_idempotency_key():
    original = make_mutation()
    replacement = make_mutation(key=original.idempotency_key, revision=8)

    try:
        ConflictResolutionRequest(
            ConflictResolutionAction.REFRESH_AND_RETRY,
            original,
            replacement,
        ).validate()
    except ValueError as exc:
        assert str(exc) == "replacement mutation requires a new idempotency_key"
    else:
        raise AssertionError("expected ValueError")


def test_refresh_retry_builder_uses_authoritative_revision_and_new_key():
    from construction_pm.client_sync.conflict import build_refresh_retry_mutation

    original = make_mutation()
    replacement = build_refresh_retry_mutation(
        original,
        current_revision=12,
        idempotency_key="fresh-key",
    )

    assert replacement.context == original.context
    assert replacement.operation == original.operation
    assert replacement.mutation == original.mutation
    assert replacement.expected_revision == 12
    assert replacement.idempotency_key == "fresh-key"
    assert replacement.attempt == 0


def test_refresh_retry_builder_rejects_reused_key():
    from construction_pm.client_sync.conflict import build_refresh_retry_mutation

    original = make_mutation()
    try:
        build_refresh_retry_mutation(
            original,
            current_revision=12,
            idempotency_key=original.idempotency_key,
        )
    except ValueError as exc:
        assert str(exc) == "replacement mutation requires a new idempotency_key"
    else:
        raise AssertionError("expected ValueError")
