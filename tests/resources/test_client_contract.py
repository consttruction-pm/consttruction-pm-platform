from construction_pm.resources.api import RESOURCE_CONTRACT_VERSION, ResourceAPI
from construction_pm.resources.application import ResourceApplicationService
from construction_pm.resources.context import ProjectContext
from construction_pm.resources.models import Resource, ResourceType
from construction_pm.resources.repository import InMemoryResourceRepository
from construction_pm.resources.transactions import NoOpTransactionManager


def test_resource_api_exposes_shared_contract_version_and_operation():
    service = ResourceApplicationService(
        repository=InMemoryResourceRepository(),
        context=ProjectContext("t", "c", "p"),
        transaction_manager=NoOpTransactionManager(),
    )
    result = ResourceAPI(service).create_resource(Resource(
        id="R-1", code="LAB", name="Labor", resource_type=ResourceType.LABOR,
        unit="hour", rates=(), calendar_id=None, active=True,
    ))
    assert result["contract_version"] == RESOURCE_CONTRACT_VERSION == "resource.v1"
    assert result["operation"] == "create_resource"


from datetime import date
from decimal import Decimal
from construction_pm.resources.models import CostBasis, ResourceRate


def test_resource_api_preserves_decimal_and_date_types_as_contract_values():
    service = ResourceApplicationService(
        repository=InMemoryResourceRepository(),
        context=ProjectContext("t", "c", "p"),
        transaction_manager=NoOpTransactionManager(),
    )
    resource = Resource(
        id="R-2", code="MAT", name="Material", resource_type=ResourceType.MATERIAL,
        unit="ton", rates=(ResourceRate(
            rate=Decimal("1250.5000"), basis=CostBasis.PER_UNIT, currency="USD",
            effective_from=date(2026, 9, 1), effective_to=date(2026, 12, 31), version=3,
        ),), calendar_id="CAL-1", active=True,
    )
    result = ResourceAPI(service).create_resource(resource)
    assert result["rates"][0] == {
        "rate": "1250.5000", "basis": "per_unit", "currency": "USD",
        "effective_from": "2026-09-01", "effective_to": "2026-12-31", "version": 3,
    }
    assert isinstance(result["rates"][0]["rate"], str)
    assert isinstance(result["rates"][0]["effective_from"], str)
