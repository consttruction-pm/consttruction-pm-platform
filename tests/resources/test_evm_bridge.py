from decimal import Decimal
from construction_pm.resources.evm_bridge import ResourceEVMInput, build_resource_evm_result

def test_resource_evm_bridge_derives_etc_eac_and_variances():
    result = build_resource_evm_result(ResourceEVMInput(
        pv=Decimal("100"), ev=Decimal("90"), ac=Decimal("110"),
        remaining_resource_cost=Decimal("40"), bac=Decimal("150"),
    ))
    assert result.etc == Decimal("40")
    assert result.eac == Decimal("150")
    assert result.vac == Decimal("0")
    assert result.cv == Decimal("-20")
    assert result.sv == Decimal("-10")
