from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.retry import RetryPolicy
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome


def mutation() -> OfflineMutation:
    return OfflineMutation(
        mutation_id="m1",
        tenant_id="t1",
        project_id="p1",
        expected_revision=7,
        operation="update_activity",
        payload={"activity_id": "A1"},
        idempotency_key="idem-1",
    )


def test_sync_outcome_requires_retry_delay() -> None:
    try:
        SyncOutcome("m1", SyncDisposition.RETRY)
    except ValueError as exc:
        assert str(exc) == "RETRY_DELAY_REQUIRED"
    else:
        raise AssertionError("retry outcome must define delay")


def test_retry_policy_is_capped() -> None:
    policy = RetryPolicy(max_attempts=5, base_delay_seconds=2, max_delay_seconds=10)
    assert [policy.delay_seconds(i) for i in range(1, 6)] == [2, 4, 8, 10, 10]


def test_mutation_keeps_expected_revision_and_idempotency() -> None:
    m = mutation()
    assert m.expected_revision == 7
    assert m.idempotency_key == "idem-1"
