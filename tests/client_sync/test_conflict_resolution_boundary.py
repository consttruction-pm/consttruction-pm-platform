from construction_pm.client_sync.context import OfflineProjectContext
from construction_pm.client_sync.mutation import OfflineMutation
from construction_pm.client_sync.outcome import SyncMutationOutcome


def test_conflict_preserves_original_identity_for_resolution():
    context = OfflineProjectContext("t", "c", "p", 1, None, None, 1, 1)
    mutation = OfflineMutation(
        context=context,
        operation="update_activity",
        idempotency_key="idem-original",
        mutation={"activity_id": "A-1", "name": "Foundation"},
        expected_revision=7,
    )
    outcome = SyncMutationOutcome(
        status="conflict",
        operation="update_activity",
        error_code="STALE_REVISION",
        retryable=False,
        idempotency_key="idem-original",
    )

    mutation.validate()
    outcome.validate()

    assert mutation.idempotency_key == outcome.idempotency_key
    assert mutation.expected_revision == 7
    assert outcome.error_code == "STALE_REVISION"


def test_conflict_does_not_provide_a_revision_to_advance_session():
    outcome = SyncMutationOutcome(
        status="conflict",
        operation="update_activity",
        error_code="STALE_REVISION",
        retryable=False,
        idempotency_key="idem-original",
    )

    assert outcome.revision is None
