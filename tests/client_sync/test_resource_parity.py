from construction_pm.client_sync import ClientMutationRequest, OfflineProjectContext
from construction_pm.client_sync.resource import parse_assignment

def test_resource_assignment_fixture_has_client_parity_semantics():
    payload={'contract_version':'resource.v1','activity_id':'A-100','resource_id':'R-1','planned_units':'10.00','actual_units':'2.00','remaining_units':'8.00','planned_cost':'100.00','actual_cost':'20.00','remaining_cost':'80.00','revision':7}
    first=parse_assignment(payload)
    second=parse_assignment(dict(payload))
    assert first == second
    request=ClientMutationRequest(OfflineProjectContext('tenant-1','company-1','project-1',1,'cal-1',1,1,1),'create_assignment','idem-resource-001',{'activity_id':'A-100','resource_id':'R-1'},7)
    assert request.to_payload()['expected_revision']==7
    assert request.to_payload()['idempotency_key']=='idem-resource-001'
