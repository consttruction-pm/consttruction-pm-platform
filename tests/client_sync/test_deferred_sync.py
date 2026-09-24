from construction_pm.client_sync.context import OfflineProjectContext
from construction_pm.client_sync.mutation import OfflineMutation
from construction_pm.client_sync.queue import InMemoryOfflineMutationQueue, SQLiteOfflineMutationQueue
from construction_pm.client_sync.sync import OfflineSyncCoordinator


class ConflictTransport:
    def send(self, request):
        return {
            "contract_version": "client-sync-outcome.v1",
            "status": "conflict",
            "operation": request.operation,
            "revision": None,
            "error_code": "STALE_REVISION",
            "retryable": False,
            "idempotency_key": request.idempotency_key,
        }


def mutation(key="idem-1"):
    return OfflineMutation(
        context=OfflineProjectContext("t", "c", "p", 1, None, None, 1, 1),
        operation="update_activity",
        idempotency_key=key,
        mutation={"activity_id": "A-1"},
        expected_revision=7,
    )


def test_conflict_is_deferred_and_not_retried_by_next_sync():
    queue = InMemoryOfflineMutationQueue()
    queue.enqueue(mutation())
    coordinator = OfflineSyncCoordinator(queue, ConflictTransport())

    first = coordinator.sync_once()
    second = coordinator.sync_once()

    assert first[0].result.status == "conflict"
    assert first[0].removed is False
    assert second == []
    assert queue.peek() == []


def test_deferred_mutation_can_be_removed_and_replaced_with_new_idempotency_key():
    queue = InMemoryOfflineMutationQueue()
    queue.enqueue(mutation())
    queue.defer(mutation())

    assert queue.peek() == []

    queue.remove(mutation())
    replacement = mutation("idem-2")
    queue.enqueue(replacement)

    assert queue.peek() == [replacement]


def test_sqlite_deferred_state_survives_new_queue_instance():
    import sqlite3

    connection = sqlite3.connect(":memory:")
    queue = SQLiteOfflineMutationQueue(connection)
    item = mutation()
    queue.enqueue(item)
    queue.defer(item)

    reopened = SQLiteOfflineMutationQueue(connection)
    assert reopened.peek() == []
    try:
        reopened.increment_attempt(item)
    except ValueError as exc:
        assert str(exc) == "offline mutation is deferred"
    else:
        raise AssertionError("expected deferred mutation to remain blocked")
