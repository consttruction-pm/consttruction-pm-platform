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
