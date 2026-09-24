import pytest
from construction_pm.client_sync.resource_control import parse_resource_control

def test_resource_control_preserves_decimal_strings():
    dto=parse_resource_control({'planned_units':'10.00','actual_units':'2.00','remaining_units':'8.00','planned_cost':'100.00','actual_cost':'20.00','remaining_cost':'80.00','unit_variance':'8.00','cost_variance':'80.00'})
    assert dto.cost_variance=='80.00'
    assert dto.to_payload()['contract_version']=='resource-control-presentation.v1'

def test_resource_control_rejects_numeric_values():
    with pytest.raises(ValueError, match='decimal strings'):
        parse_resource_control({'planned_units':10,'actual_units':'2','remaining_units':'8','planned_cost':'100','actual_cost':'20','remaining_cost':'80','unit_variance':'8','cost_variance':'80'})
