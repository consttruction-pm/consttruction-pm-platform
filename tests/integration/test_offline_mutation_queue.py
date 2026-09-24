from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.offline_queue import OfflineMutationQueue


def make_mutation(mutation_id: str = "m1", key: str = "k1") -> OfflineMutation:
    return OfflineMutation(
        mutation_id=mutation_id,
        tenant_id="t1",
        project_id="p1",
        expected_revision=7,
        operation="update_activity",
        payload={"activity_id": "A1", "name": "Activity"},
        idempotency_key=key,
    )


def test_queue_preserves_order_and_acknowledges() -> None:
    queue = OfflineMutationQueue()
    queue.enqueue(make_mutation("m1", "k1"))
    queue.enqueue(make_mutation("m2", "k2"))

    assert [item.mutation_id for item in queue.pending()] == ["m1", "m2"]

    queue.acknowledge("m1")
    assert [item.mutation_id for item in queue.pending()] == ["m2"]


def test_queue_rejects_duplicate_identity() -> None:
    queue = OfflineMutationQueue()
    queue.enqueue(make_mutation())
    try:
        queue.enqueue(make_mutation())
    except ValueError as exc:
        assert str(exc) == "DUPLICATE_MUTATION_ID"
    else:
        raise AssertionError("duplicate mutation must be rejected")


def test_queue_rejects_duplicate_idempotency_key() -> None:
    queue = OfflineMutationQueue()
    queue.enqueue(make_mutation("m1", "same"))
    try:
        queue.enqueue(make_mutation("m2", "same"))
    except ValueError as exc:
        assert str(exc) == "DUPLICATE_IDEMPOTENCY_KEY"
    else:
        raise AssertionError("duplicate idempotency key must be rejected")
