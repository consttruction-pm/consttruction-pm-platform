import pytest

from construction_pm.client_sync.adapter import ClientMutationRequest, normalize_sync_outcome
from construction_pm.client_sync.context import OfflineProjectContext


def context():
    return OfflineProjectContext("tenant-1", "company-1", "project-1", 1, "calendar-1", 1, 1, 1)


@pytest.fixture
def mutation_payload():
    return ClientMutationRequest(
        context=context(),
        operation="update_activity",
        idempotency_key="idem-activity-001",
        mutation={"activity_id": "A-100", "name": "Foundation"},
        expected_revision=7,
    ).to_payload()


@pytest.mark.parametrize(
    "status,payload",
    [
        ("applied", {"revision": 8, "error_code": None, "retryable": False}),
        ("replayed", {"revision": 8, "error_code": None, "retryable": False}),
        ("conflict", {"error_code": "STALE_REVISION", "retryable": False}),
        ("rejected", {"error_code": "VALIDATION_ERROR", "retryable": False}),
    ],
)
def test_shared_fixture_outcomes_normalize(status, payload):
    outcome = normalize_sync_outcome({
        "contract_version": "client-sync-outcome.v1",
        "status": status,
        "operation": "update_activity",
        "idempotency_key": "idem-activity-001",
        **payload,
    })
    assert outcome.status == status
    assert outcome.operation == "update_activity"
    assert outcome.idempotency_key == "idem-activity-001"


def test_shared_fixture_mutation_identity(mutation_payload):
    assert mutation_payload["contract_version"] == "client-sync.v1"
    assert mutation_payload["context"] == {
        "tenant_id": "tenant-1",
        "company_id": "company-1",
        "project_id": "project-1",
    }
    assert mutation_payload["idempotency_key"] == "idem-activity-001"
    assert mutation_payload["expected_revision"] == 7
    assert mutation_payload["mutation"] == {
        "activity_id": "A-100",
        "name": "Foundation",
    }
