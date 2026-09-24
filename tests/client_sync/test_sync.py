from construction_pm.client_sync.adapter import ClientMutationRequest
from construction_pm.client_sync.context import OfflineProjectContext
from construction_pm.client_sync.mutation import OfflineMutation
from construction_pm.client_sync.outcome import SyncMutationOutcome
from construction_pm.client_sync.queue import InMemoryOfflineMutationQueue
from construction_pm.client_sync.sync import OfflineSyncCoordinator


CTX = OfflineProjectContext("t", "c", "p", 1, "cal", 1, 1, 1)


class FakeTransport:
    def __init__(self, payload):
        self.payload = payload
        self.requests = []

    def send(self, request: ClientMutationRequest):
        self.requests.append(request)
        return self.payload


def make_mutation():
    return OfflineMutation(
        CTX, "create_activity", "idem-1", {"activity_id": "A-1"}, 7
    )


def test_applied_outcome_removes_mutation_and_preserves_request_identity():
    queue = InMemoryOfflineMutationQueue()
    mutation = make_mutation()
    queue.enqueue(mutation)
    transport = FakeTransport({
        "contract_version": "client-sync-outcome.v1",
        "status": "applied",
        "operation": "create_activity",
        "revision": 8,
        "error_code": None,
        "retryable": False,
        "idempotency_key": "idem-1",
    })

    result = OfflineSyncCoordinator(queue, transport).sync_once()

    assert result[0].removed is True
    assert result[0].outcome.status == "applied"
    assert queue.peek() == []
    request = transport.requests[0]
    assert request.idempotency_key == "idem-1"
    assert request.expected_revision == 7


def test_replayed_outcome_is_success_and_removes_mutation():
    queue = InMemoryOfflineMutationQueue()
    mutation = make_mutation()
    queue.enqueue(mutation)
    transport = FakeTransport({
        "contract_version": "client-sync-outcome.v1",
        "status": "replayed",
        "operation": "create_activity",
        "revision": 8,
        "error_code": None,
        "retryable": False,
        "idempotency_key": "idem-1",
    })

    result = OfflineSyncCoordinator(queue, transport).sync_once()

    assert result[0].removed is True
    assert queue.peek() == []


def test_conflict_stays_queued_for_explicit_resolution():
    queue = InMemoryOfflineMutationQueue()
    mutation = make_mutation()
    queue.enqueue(mutation)
    transport = FakeTransport({
        "contract_version": "client-sync-outcome.v1",
        "status": "conflict",
        "operation": "create_activity",
        "revision": 9,
        "error_code": "STALE_REVISION",
        "retryable": False,
        "idempotency_key": "idem-1",
    })

    result = OfflineSyncCoordinator(queue, transport).sync_once()

    assert result[0].removed is False
    assert result[0].outcome.error_code == "STALE_REVISION"
    assert queue.peek()[0].attempt == 1


def test_rejected_stays_queued_for_explicit_resolution():
    queue = InMemoryOfflineMutationQueue()
    queue.enqueue(make_mutation())
    transport = FakeTransport({
        "contract_version": "client-sync-outcome.v1",
        "status": "rejected",
        "operation": "create_activity",
        "revision": None,
        "error_code": "FORBIDDEN",
        "retryable": False,
        "idempotency_key": "idem-1",
    })

    result = OfflineSyncCoordinator(queue, transport).sync_once()

    assert result[0].removed is False
    assert result[0].outcome.status == "rejected"
    assert queue.peek()[0].attempt == 1


def test_mismatched_idempotency_key_is_not_accepted():
    queue = InMemoryOfflineMutationQueue()
    queue.enqueue(make_mutation())
    transport = FakeTransport({
        "contract_version": "client-sync-outcome.v1",
        "status": "applied",
        "operation": "create_activity",
        "revision": 8,
        "error_code": None,
        "retryable": False,
        "idempotency_key": "wrong-key",
    })

    try:
        OfflineSyncCoordinator(queue, transport).sync_once()
    except ValueError as exc:
        assert "idempotency_key" in str(exc)
    else:
        raise AssertionError("mismatched idempotency key was accepted")
