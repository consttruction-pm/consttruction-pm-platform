from construction_pm.client_sync.result import (
    ClientMutationResult,
    present_mutation_payload,
)


def sync_payload(status="applied"):
    return {
        "contract_version": "client-sync-outcome.v1",
        "status": status,
        "operation": "update_activity",
        "revision": 8 if status in {"applied", "replayed"} else None,
        "error_code": None if status in {"applied", "replayed"} else "STALE_REVISION",
        "retryable": False,
        "idempotency_key": "idem-activity-001",
    }


def error_payload(message="Revision conflict"):
    return {
        "error": {
            "category": "conflict",
            "code": "STALE_REVISION",
            "message": message,
            "retryable": False,
        }
    }


def test_applied_outcome_is_successful():
    result = present_mutation_payload(sync_payload())

    assert result == ClientMutationResult(
        status="applied",
        operation="update_activity",
        revision=8,
        idempotency_key="idem-activity-001",
    )
    assert result.successful is True
    assert result.conflicted is False


def test_replayed_outcome_is_successful():
    result = present_mutation_payload(sync_payload("replayed"))

    assert result is not None
    assert result.successful is True
    assert result.revision == 8


def test_conflict_outcome_is_not_successful():
    result = present_mutation_payload(sync_payload("conflict"))

    assert result is not None
    assert result.successful is False
    assert result.conflicted is True
    assert result.revision is None


def test_application_error_becomes_presentable_error():
    result = present_mutation_payload(error_payload("Revision conflict"))

    assert result is not None
    assert result.status == "error"
    assert result.error is not None
    assert result.error.identity == ("conflict", "STALE_REVISION")
    assert result.successful is False


def test_error_message_does_not_change_error_identity():
    first = present_mutation_payload(error_payload("Revision conflict"))
    second = present_mutation_payload(error_payload("تعارض نسخه"))

    assert first is not None and second is not None
    assert first.error is not None and second.error is not None
    assert first.error.identity == second.error.identity


def test_conflict_result_projects_into_shared_presentation():
    from construction_pm.client_sync.context import OfflineProjectContext
    from construction_pm.client_sync.mutation import OfflineMutation

    mutation = OfflineMutation(
        context=OfflineProjectContext("t", "c", "p", 1, None, None, 1, 1),
        operation="update_activity",
        idempotency_key="idem-activity-001",
        mutation={"activity_id": "A-100", "name": "Foundation"},
        expected_revision=7,
    )
    result = present_mutation_payload(sync_payload("conflict"))

    assert result is not None
    presentation = result.to_conflict_presentation(mutation)

    assert presentation.error_code == "STALE_REVISION"
    assert presentation.expected_revision == 7
    assert presentation.idempotency_key == "idem-activity-001"
