from construction_pm.client_sync.adapter import ClientMutationRequest
from construction_pm.client_sync.conflict_presentation import ClientConflictPresentation
from construction_pm.client_sync.context import OfflineProjectContext
from construction_pm.client_sync.mutation import OfflineMutation
from construction_pm.client_sync.outcome import SyncMutationOutcome


CONTEXT = OfflineProjectContext("tenant-1", "company-1", "project-1", 1, None, None, 1, 1)


def test_fixture_request_serialization_is_stable():
    request = ClientMutationRequest(
        context=CONTEXT,
        operation="update_activity",
        idempotency_key="idem-activity-001",
        expected_revision=7,
        mutation={"activity_id": "A-100", "name": "Foundation"},
    )

    assert request.to_payload() == {
        "contract_version": "client-sync.v1",
        "operation": "update_activity",
        "context": {
            "tenant_id": "tenant-1",
            "company_id": "company-1",
            "project_id": "project-1",
        },
        "idempotency_key": "idem-activity-001",
        "expected_revision": 7,
        "mutation": {"activity_id": "A-100", "name": "Foundation"},
    }


def test_fixture_outcomes_normalize_identically():
    for status, revision, error_code, retryable in (
        ("applied", 8, None, None),
        ("replayed", 8, None, None),
        ("conflict", None, "STALE_REVISION", False),
        ("rejected", None, "VALIDATION_ERROR", False),
    ):
        outcome = SyncMutationOutcome(
            status=status,
            operation="update_activity",
            revision=revision,
            error_code=error_code,
            retryable=retryable,
            idempotency_key="idem-activity-001",
        )
        outcome.validate()

        assert outcome.contract_version == "client-sync-outcome.v1"
        assert outcome.operation == "update_activity"
        assert outcome.idempotency_key == "idem-activity-001"


def test_conflict_fixture_maps_to_shared_presentation_without_recalculation():
    mutation = OfflineMutation(
        context=CONTEXT,
        operation="update_activity",
        idempotency_key="idem-activity-001",
        mutation={"activity_id": "A-100", "name": "Foundation"},
        expected_revision=7,
    )

    presentation = ClientConflictPresentation.from_conflict(
        mutation,
        error_code="STALE_REVISION",
        retryable=False,
    )

    assert presentation.to_payload() == {
        "contract_version": "client-conflict-presentation.v1",
        "operation": "update_activity",
        "idempotency_key": "idem-activity-001",
        "expected_revision": 7,
        "error_code": "STALE_REVISION",
        "retryable": False,
        "available_actions": ["discard", "refresh_and_retry", "defer"],
    }
