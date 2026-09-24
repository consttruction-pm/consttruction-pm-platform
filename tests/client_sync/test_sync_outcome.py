import pytest

from construction_pm.client_sync.outcome import SyncMutationOutcome


def test_sync_outcome_is_deterministic_and_versioned():
    outcome = SyncMutationOutcome(
        status="replayed",
        operation="register_resource",
        revision=3,
        idempotency_key="req-1",
    )
    assert outcome.fingerprint_payload() == outcome.fingerprint_payload()
    assert outcome.contract_version == "client-sync-outcome.v1"


@pytest.mark.parametrize("status", ["applied", "replayed"])
def test_success_outcomes_reject_error_code(status):
    with pytest.raises(ValueError, match="successful outcomes"):
        SyncMutationOutcome(status=status, error_code="STALE_REVISION").validate()


def test_conflict_requires_stable_error_code():
    with pytest.raises(ValueError, match="error_code is required"):
        SyncMutationOutcome(status="conflict").validate()


def test_invalid_revision_is_rejected():
    with pytest.raises(ValueError, match="revision"):
        SyncMutationOutcome(status="applied", revision=0).validate()
