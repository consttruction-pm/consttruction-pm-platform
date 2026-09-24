from construction_pm.client_sync.adapter import (
    ClientMutationRequest,
    normalize_stable_error,
    normalize_sync_outcome,
)
from construction_pm.client_sync.context import OfflineProjectContext


def _context():
    return OfflineProjectContext(
        "tenant-1", "company-1", "project-1", 4,
        "cal-1", 7, 3, 2,
    )


def _request():
    return ClientMutationRequest(
        context=_context(),
        operation="create_activity",
        idempotency_key="idem-1",
        expected_revision=12,
        mutation={"activity_id": "A-1"},
    )


def test_client_mutation_request_emits_authoritative_envelope():
    assert _request().to_payload() == {
        "contract_version": "client-sync.v1",
        "operation": "create_activity",
        "context": {
            "tenant_id": "tenant-1",
            "company_id": "project-1",
            "project_id": "project-1",
        },
        "idempotency_key": "idem-1",
        "expected_revision": 12,
        "mutation": {"activity_id": "A-1"},
    }


def test_client_mutation_request_rejects_invalid_revision():
    request = _request()
    request = ClientMutationRequest(
        request.context, request.operation, request.idempotency_key, request.mutation, 0
    )
    try:
        request.validate()
    except ValueError as exc:
        assert str(exc) == "expected_revision must be positive when provided"
    else:
        raise AssertionError("invalid revision was accepted")


def test_client_mutation_request_can_enter_offline_queue_without_rewriting_identity():
    queued = _request().to_offline_mutation()
    assert queued.contract_version == "offline-mutation.v1"
    assert queued.idempotency_key == "idem-1"
    assert queued.expected_revision == 12
    assert queued.mutation == {"activity_id": "A-1"}


def test_sync_outcome_normalization_preserves_authoritative_fields():
    payload = {
        "contract_version": "client-sync-outcome.v1",
        "status": "conflict",
        "operation": "create_activity",
        "revision": 12,
        "error_code": "STALE_REVISION",
        "retryable": False,
        "idempotency_key": "idem-1",
    }
    outcome = normalize_sync_outcome(payload)
    assert outcome is not None
    assert outcome.status == "conflict"
    assert outcome.error_code == "STALE_REVISION"
    assert outcome.revision == 12


def test_sync_outcome_normalization_rejects_unknown_contract_fields():
    payload = {
        "contract_version": "client-sync-outcome.v1",
        "status": "applied",
        "operation": "create_activity",
        "revision": 13,
        "error_code": None,
        "retryable": False,
        "idempotency_key": "idem-1",
        "server_message": "do not branch on this",
    }
    assert normalize_sync_outcome(payload) is None


def test_stable_error_normalization_does_not_accept_extra_fields():
    payload = {
        "error": {
            "category": "conflict",
            "code": "STALE_REVISION",
            "message": "stale",
            "retryable": False,
            "details": {"server_revision": 13},
        }
    }
    assert normalize_stable_error(payload) is None


def test_stable_error_normalization_preserves_contract_fields():
    payload = {
        "error": {
            "category": "conflict",
            "code": "STALE_REVISION",
            "message": "stale",
            "retryable": False,
        }
    }
    assert normalize_stable_error(payload) == payload["error"]
