from construction_pm.client_sync.adapter import ClientMutationRequest
from construction_pm.client_sync.context import OfflineProjectContext
from construction_pm.client_sync.session import ClientProjectSession


def test_request_from_session_carries_revision_and_context():
    context = OfflineProjectContext("t", "c", "p", 1, None, None, 1, 1)
    session = ClientProjectSession(context, "api.v1", revision=12)

    request = ClientMutationRequest.from_session(
        session,
        operation="update_activity",
        idempotency_key="idem-1",
        mutation={"activity_id": "A-1"},
    )

    assert request.context == context
    assert request.expected_revision == 12
    assert request.to_payload()["expected_revision"] == 12


def test_request_from_session_allows_initial_revision_absence():
    context = OfflineProjectContext("t", "c", "p", 1, None, None, 1, 1)
    session = ClientProjectSession(context, "api.v1")

    request = ClientMutationRequest.from_session(
        session,
        operation="create_activity",
        idempotency_key="idem-2",
        mutation={"activity_id": "A-2"},
    )

    assert request.expected_revision is None
