import pytest
from construction_pm.client_sync import ClientMutationRequest, OfflineProjectContext, ClientResourceMutationFactory

def req(operation):
    return ClientMutationRequest(OfflineProjectContext('t','c','p',1,'cal',1,1,1),operation,'idem-1',{'id':'R1'})

def test_resource_workflow_preserves_session_revision_and_context():
    r=ClientResourceMutationFactory.create_resource(req('create_resource'))
    assert r.expected_revision is None
    assert r.to_payload()['context']['project_id']=='p'

def test_assignment_workflow_requires_matching_operation():
    with pytest.raises(ValueError): ClientResourceMutationFactory.create_assignment(req('create_resource'))
