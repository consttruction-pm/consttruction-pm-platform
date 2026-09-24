from construction_pm.client_sync.conflict import ConflictResolutionAction
from construction_pm.client_sync.conflict_presentation import ClientConflictPresentation
from construction_pm.client_sync.context import OfflineProjectContext
from construction_pm.client_sync.mutation import OfflineMutation


def make_mutation():
    return OfflineMutation(
        context=OfflineProjectContext("t", "c", "p", 1, None, None, 1, 1),
        operation="update_activity",
        idempotency_key="idem-001",
        mutation={"activity_id": "A-1", "name": "Foundation"},
        expected_revision=7,
    )


def test_conflict_presentation_has_shared_actions_and_stable_fields():
    presentation = ClientConflictPresentation.from_conflict(
        make_mutation(),
        error_code="STALE_REVISION",
        retryable=True,
    )

    assert presentation.contract_version == "client-conflict-presentation.v1"
    assert presentation.operation == "update_activity"
    assert presentation.idempotency_key == "idem-001"
    assert presentation.expected_revision == 7
    assert presentation.error_code == "STALE_REVISION"
    assert presentation.available_actions == (
        ConflictResolutionAction.DISCARD,
        ConflictResolutionAction.REFRESH_AND_RETRY,
        ConflictResolutionAction.DEFER,
    )


def test_conflict_presentation_payload_is_framework_neutral():
    presentation = ClientConflictPresentation.from_conflict(
        make_mutation(),
        error_code="STALE_REVISION",
        retryable=False,
    )

    assert presentation.to_payload() == {
        "contract_version": "client-conflict-presentation.v1",
        "operation": "update_activity",
        "idempotency_key": "idem-001",
        "expected_revision": 7,
        "error_code": "STALE_REVISION",
        "retryable": False,
        "available_actions": ["discard", "refresh_and_retry", "defer"],
    }


def test_conflict_presentation_rejects_invalid_error_code():
    try:
        ClientConflictPresentation.from_conflict(
            make_mutation(),
            error_code="",
            retryable=True,
        )
    except ValueError as exc:
        assert str(exc) == "error_code is required"
    else:
        raise AssertionError("expected ValueError")
