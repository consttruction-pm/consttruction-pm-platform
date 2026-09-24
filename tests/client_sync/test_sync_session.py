from construction_pm.client_sync.context import OfflineProjectContext
from construction_pm.client_sync.outcome import SyncMutationOutcome
from construction_pm.client_sync.queue import InMemoryOfflineMutationQueue
from construction_pm.client_sync.session import ClientProjectSession
from construction_pm.client_sync.sync import OfflineSyncCoordinator


class Transport:
    def __init__(self, outcome):
        self.outcome = outcome

    def send(self, request):
        return {
            "contract_version": "client-sync-outcome.v1",
            "status": self.outcome,
            "operation": request.operation,
            "revision": 8 if self.outcome in {"applied", "replayed"} else None,
            "error_code": None if self.outcome in {"applied", "replayed"} else "STALE_REVISION",
            "retryable": None if self.outcome in {"applied", "replayed"} else False,
            "idempotency_key": request.idempotency_key,
        }


def make_session():
    return ClientProjectSession(
        OfflineProjectContext("t", "c", "p", 1, None, None, 1, 1),
        "api.v1",
        revision=7,
    )


def test_sync_advances_session_from_authoritative_revision():
    session = make_session()
    queue = InMemoryOfflineMutationQueue()
    from construction_pm.client_sync.mutation import OfflineMutation
    queue.enqueue(OfflineMutation(
        context=session.context,
        operation="update_activity",
        idempotency_key="idem-1",
        mutation={"activity_id": "A-1"},
        expected_revision=7,
    ))

    coordinator = OfflineSyncCoordinator(queue, Transport("applied"), session=session)
    attempts = coordinator.sync_once()

    assert attempts[0].removed is True
    assert coordinator.session.revision == 8


def test_sync_does_not_advance_session_on_conflict():
    session = make_session()
    queue = InMemoryOfflineMutationQueue()
    from construction_pm.client_sync.mutation import OfflineMutation
    queue.enqueue(OfflineMutation(
        context=session.context,
        operation="update_activity",
        idempotency_key="idem-2",
        mutation={"activity_id": "A-2"},
        expected_revision=7,
    ))

    coordinator = OfflineSyncCoordinator(queue, Transport("conflict"), session=session)
    attempts = coordinator.sync_once()

    assert attempts[0].removed is False
    assert coordinator.session.revision == 7


def test_sync_rejects_context_mismatch_before_transport():
    session = make_session()
    queue = InMemoryOfflineMutationQueue()
    from construction_pm.client_sync.mutation import OfflineMutation
    queue.enqueue(OfflineMutation(
        context=OfflineProjectContext("t", "c", "other", 1, None, None, 1, 1),
        operation="update_activity",
        idempotency_key="idem-3",
        mutation={"activity_id": "A-3"},
        expected_revision=7,
    ))

    coordinator = OfflineSyncCoordinator(queue, Transport("applied"), session=session)

    try:
        coordinator.sync_once()
    except ValueError as exc:
        assert str(exc) == "queued mutation context does not match client session"
    else:
        raise AssertionError("expected ValueError")
