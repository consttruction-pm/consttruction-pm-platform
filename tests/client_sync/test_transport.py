from construction_pm.client_sync.adapter import ClientMutationRequest
from construction_pm.client_sync.context import OfflineProjectContext
from construction_pm.client_sync.transport import CallableMutationTransport


def test_callable_transport_sends_authoritative_payload():
    received = []

    transport = CallableMutationTransport(received.append)
    request = ClientMutationRequest(
        context=OfflineProjectContext("t", "c", "p", 1, "cal", 1, 1, 1),
        operation="create_activity",
        idempotency_key="idem-1",
        mutation={"activity_id": "A-1"},
        expected_revision=4,
    )

    result = transport.send(request)

    assert result is None
    assert received == [{
        "contract_version": "client-sync.v1",
        "operation": "create_activity",
        "context": {
            "tenant_id": "t",
            "company_id": "c",
            "project_id": "p",
        },
        "idempotency_key": "idem-1",
        "expected_revision": 4,
        "mutation": {"activity_id": "A-1"},
    }]
