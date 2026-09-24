import pytest

from construction_pm.client_sync.dispatch import OfflineMutationDispatcher
from construction_pm.client_sync.context import OfflineProjectContext
from construction_pm.client_sync.mutation import OfflineMutation
from construction_pm.client_sync.outcome import SyncMutationOutcome


class FakeTransport:
    def __init__(self, outcome):
        self.outcome = outcome

    def apply(self, mutation):
        return self.outcome


def make_mutation():
    return OfflineMutation(
        context=OfflineProjectContext(
            tenant_id="tenant-1",
            company_id="company-1",
            project_id="project-1",
            project_schema_version=1,
            calendar_id="calendar-1",
            calendar_version=1,
            scheduling_settings_version=1,
            calculation_settings_version=1,
        ),
        operation="register_resource",
        idempotency_key="req-1",
        mutation={"resource_id": "r-1"},
        expected_revision=3,
    )


def test_dispatch_accepts_matching_authoritative_outcome():
    mutation = make_mutation()
    outcome = SyncMutationOutcome(
        status="applied",
        operation=mutation.operation,
        revision=4,
        idempotency_key=mutation.idempotency_key,
    )

    result = OfflineMutationDispatcher().dispatch(mutation, FakeTransport(outcome))

    assert result is outcome


def test_dispatch_rejects_mismatched_operation():
    mutation = make_mutation()
    outcome = SyncMutationOutcome(
        status="applied",
        operation="other_operation",
        revision=4,
        idempotency_key=mutation.idempotency_key,
    )

    with pytest.raises(ValueError, match="operation"):
        OfflineMutationDispatcher().dispatch(mutation, FakeTransport(outcome))


def test_dispatch_rejects_mismatched_idempotency_key():
    mutation = make_mutation()
    outcome = SyncMutationOutcome(
        status="replayed",
        operation=mutation.operation,
        revision=4,
        idempotency_key="other-request",
    )

    with pytest.raises(ValueError, match="idempotency_key"):
        OfflineMutationDispatcher().dispatch(mutation, FakeTransport(outcome))


def test_dispatch_rejects_non_typed_transport_result():
    with pytest.raises(TypeError, match="SyncMutationOutcome"):
        OfflineMutationDispatcher().dispatch(make_mutation(), FakeTransport({"status": "applied"}))
