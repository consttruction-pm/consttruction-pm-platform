import pytest
from construction_pm.client_sync.mutation import OfflineMutation
from construction_pm.client_sync.context import OfflineProjectContext
from construction_pm.client_sync.result import ClientMutationResult
from construction_pm.client_sync.sync_presentation import ClientSyncPresentation


def mutation():
    return OfflineMutation(OfflineProjectContext('t','c','p',1,None,None,1,1),'update_activity','idem-1',{'activity_id':'A-1'},7,2)


def test_queued_state_preserves_identity_and_attempt():
    view = ClientSyncPresentation.from_queued(mutation())
    assert view.to_payload() == {'contract_version':'client-sync-presentation.v1','operation':'update_activity','idempotency_key':'idem-1','state':'queued','attempt':2,'error_code':None,'retryable':None,'revision':None}


def test_conflict_state_preserves_authoritative_error_without_retry_calculation():
    result = ClientMutationResult('conflict','update_activity',None,'STALE_REVISION',False,'idem-1')
    view = ClientSyncPresentation.from_result(mutation(), result)
    assert view.state == 'conflict'
    assert view.error_code == 'STALE_REVISION'
    assert view.retryable is False
    assert view.revision is None


def test_applied_state_requires_authoritative_revision():
    result = ClientMutationResult('applied','update_activity',8,None,None,'idem-1')
    assert ClientSyncPresentation.from_result(mutation(), result).revision == 8
    with pytest.raises(ValueError):
        ClientSyncPresentation('update_activity','idem-1','applied',2).validate()
