from construction_pm.client_sync.e2e_conflict_flow import ConflictSyncFlow
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome


class FakeTransport:
    def __init__(self, outcome):
        self.outcome = outcome
        self.received = None

    def submit(self, mutation):
        self.received = mutation
        return self.outcome


def test_conflict_flow_preserves_revision_and_requests_refresh() -> None:
    transport = FakeTransport(
        SyncOutcome(
            mutation_id="m1",
            disposition=SyncDisposition.CONFLICT,
            error_code="STALE_REVISION",
        )
    )
    mutation = OfflineMutation(
        mutation_id="m1",
        tenant_id="t1",
        project_id="p1",
        expected_revision=7,
        operation="update_activity",
        payload={"activity_id": "A1"},
        idempotency_key="idem-1",
    )
    result = ConflictSyncFlow(transport).submit_once(mutation)

    assert result.outcome.disposition is SyncDisposition.CONFLICT
    assert result.requires_refresh is True
    assert result.preserved_expected_revision == 7
    assert transport.received.expected_revision == 7


def test_acknowledged_flow_does_not_request_refresh() -> None:
    transport = FakeTransport(
        SyncOutcome(mutation_id="m1", disposition=SyncDisposition.ACKNOWLEDGED)
    )
    mutation = OfflineMutation(
        mutation_id="m1", tenant_id="t1", project_id="p1",
        expected_revision=3, operation="update_activity",
        payload={}, idempotency_key="idem-1",
    )
    result = ConflictSyncFlow(transport).submit_once(mutation)
    assert result.requires_refresh is False
