from construction_pm.client_sync import ClientMutationRequest, ClientProjectSession, OfflineProjectContext
from construction_pm.client_sync.resource import ClientResourceMutationFactory


def test_resource_mutation_factory_preserves_session_revision_and_context():
    session = ClientProjectSession(
        OfflineProjectContext('t','c','p',1,'cal',1,1,1),
        'application.v1',
        revision=7,
    )
    request = ClientMutationRequest.from_session(session, 'create_resource', 'idem-resource-002', {'id':'R-2'})
    result = ClientResourceMutationFactory.create_resource(request)
    assert result.expected_revision == 7
    assert result.context == session.context
    assert result.idempotency_key == 'idem-resource-002'


def test_assignment_factory_preserves_authoritative_session_revision():
    session = ClientProjectSession(
        OfflineProjectContext('t','c','p',1,'cal',1,1,1),
        'application.v1',
        revision=11,
    )
    request = ClientMutationRequest.from_session(session, 'create_assignment', 'idem-assignment-002', {'activity_id':'A-1','resource_id':'R-2'})
    result = ClientResourceMutationFactory.create_assignment(request)
    assert result.expected_revision == 11
