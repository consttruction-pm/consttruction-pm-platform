import pytest
from construction_pm.client_sync.resource import parse_assignment, parse_resource


def test_resource_dto_preserves_revision_and_decimal_boundary():
    dto=parse_resource({'contract_version':'resource.v1','id':'R1','code':'LAB-1','name':'Crew','type':'labor','unit':'hr','calendar_id':'cal-1','active':True,'revision':4})
    assert dto.revision==4
    assert dto.calendar_id=='cal-1'


def test_assignment_dto_keeps_decimal_values_as_strings():
    dto=parse_assignment({'contract_version':'resource.v1','activity_id':'A1','resource_id':'R1','planned_units':'10.50','actual_units':'2.25','remaining_units':'8.25','planned_cost':'100.00','actual_cost':'20.00','remaining_cost':'80.00','revision':5})
    assert dto.planned_units=='10.50'
    assert dto.remaining_cost=='80.00'


def test_resource_revision_is_required_and_positive():
    with pytest.raises(ValueError):
        parse_resource({'contract_version':'resource.v1','id':'R1','code':'R','name':'R','type':'labor','unit':'hr','active':True,'revision':0})


def test_assignment_rejects_numeric_decimal_payload():
    with pytest.raises(ValueError, match='decimal strings'):
        parse_assignment({'contract_version':'resource.v1','activity_id':'A1','resource_id':'R1','planned_units':10,'actual_units':'0','remaining_units':'10','revision':1})
