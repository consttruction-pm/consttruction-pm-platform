from construction_pm.client_sync.context import OfflineProjectContext
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


def enqueue(session, key):
    from construction_pm.client_sync.mutation import OfflineMutation

    queue = InMemoryOfflineMutationQueue()
    queue.enqueue(OfflineMutation(
        context=session.context,
        operation="update_activity",
        idempotency_key=key,
        mutation={"activity_id": "A-1"},
        expected_revision=7,
    ))
    return queue


def test_sync_advances_session_from_shared_result_boundary():
    session = make_session()
    coordinator = OfflineSyncCoordinator(
        enqueue(session, "idem-1"), Transport("applied"), session=session
    )

    attempts = coordinator.sync_once()

    assert attempts[0].removed is True
    assert attempts[0].result is not None
    assert attempts[0].result.successful is True
    assert coordinator.session.revision == 8


def test_sync_preserves_conflict_result_and_does_not_advance_session():
    session = make_session()
    coordinator = OfflineSyncCoordinator(
        enqueue(session, "idem-2"), Transport("conflict"), session=session
    )

    attempts = coordinator.sync_once()

    assert attempts[0].removed is False
    assert attempts[0].result is not None
    assert attempts[0].result.error_code == "STALE_REVISION"
    assert coordinator.session.revision == 7


def test_sync_rejects_context_mismatch_before_transport():
    session = make_session()
    from construction_pm.client_sync.mutation import OfflineMutation

    queue = InMemoryOfflineMutationQueue()
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


def test_conflict_refresh_retry_applied_advances_session_end_to_end():
    from construction_pm.client_sync.conflict import ConflictResolutionService
    from construction_pm.client_sync.mutation import OfflineMutation

    session = make_session()
    queue = enqueue(session, "idem-conflict")
    conflict_coordinator = OfflineSyncCoordinator(
        queue, Transport("conflict"), session=session
    )

    conflict_attempt = conflict_coordinator.sync_once()[0]
    assert conflict_attempt.result is not None
    assert conflict_attempt.result.conflicted is True
    assert conflict_coordinator.session.revision == 7

    replacement = ConflictResolutionService(queue).refresh_and_retry_from_session(
        conflict_attempt.mutation,
        session,
        idempotency_key="idem-retry",
        mutation={"activity_id": "A-1", "name": "Foundation Updated"},
    )
    assert replacement.expected_revision == 7

    class AppliedTransport:
        def send(self, request):
            return {
                "contract_version": "client-sync-outcome.v1",
                "status": "applied",
                "operation": request.operation,
                "revision": 8,
                "error_code": None,
                "retryable": None,
                "idempotency_key": request.idempotency_key,
            }

    retry_coordinator = OfflineSyncCoordinator(
        queue, AppliedTransport(), session=conflict_coordinator.session
    )
    applied_attempt = retry_coordinator.sync_once()[0]

    assert applied_attempt.result is not None
    assert applied_attempt.result.successful is True
    assert applied_attempt.result.revision == 8
    assert retry_coordinator.session.revision == 8
