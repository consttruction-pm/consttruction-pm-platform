from construction_pm.client_sync.adapter import (
    ClientMutationRequest,
    normalize_stable_error,
)
from construction_pm.client_sync.context import OfflineProjectContext


def _context():
    return OfflineProjectContext(
        "tenant-1", "company-1", "project-1", 4,
        "cal-1", 7, 3, 2,
    )


def test_client_mutation_request_emits_authoritative_envelope():
    request = ClientMutationRequest(
        context=_context(),
        operation="create_activity",
        idempotency_key="idem-1",
        expected_revision=12,
        mutation={"activity_id": "A-1"},
    )
    assert request.to_payload() == {
        "contract_version": "client-sync.v1",
        "operation": "create_activity",
        "context": {
            "tenant_id": "tenant-1",
            "company_id": "company-1",
            "project_id": "project-1",
        },
        "idempotency_key": "idem-1",
        "expected_revision": 12,
        "mutation": {"activity_id": "A-1"},
    }


def test_client_mutation_request_rejects_invalid_revision():
    request = ClientMutationRequest(
        context=_context(),
        operation="create_activity",
        idempotency_key="idem-1",
        expected_revision=0,
        mutation={},
    )
    try:
        request.validate()
    except ValueError as exc:
        assert str(exc) == "expected_revision must be positive when provided"
    else:
        raise AssertionError("invalid revision was accepted")


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
