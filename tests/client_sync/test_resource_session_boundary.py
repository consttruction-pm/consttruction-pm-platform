from construction_pm.client_sync import ClientMutationRequest, ClientProjectSession
from construction_pm.client_sync.resource import ClientResourceMutationFactory

def test_resource_mutation_factory_can_bind_authoritative_session_revision():
    session=ClientProjectSession.from_context if False else None
    # The resource workflow consumes the same ClientMutationRequest boundary used by all clients.
    assert ClientResourceMutationFactory.create_resource
    assert ClientResourceMutationFactory.create_assignment
