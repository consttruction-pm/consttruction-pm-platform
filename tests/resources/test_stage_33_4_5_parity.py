from decimal import Decimal

from construction_pm.resources.api import RESOURCE_CONTRACT_VERSION, ResourceAPI
from construction_pm.resources.application import ResourceApplicationService
from construction_pm.resources.context import ProjectContext
from construction_pm.resources.models import Resource, ResourceAssignment, ResourceType
from construction_pm.resources.repository import InMemoryResourceRepository
from construction_pm.resources.transactions import NoOpTransactionManager


def _api():
    return ResourceAPI(
        ResourceApplicationService(
            repository=InMemoryResourceRepository(),
            context=ProjectContext("tenant-1", "company-1", "project-1"),
            transaction_manager=NoOpTransactionManager(),
        )
    )


def _resource():
    return Resource(
        id="R-1",
        code="LAB-01",
        name="Labor",
        resource_type=ResourceType.LABOR,
        unit="hour",
        rates=(),
        calendar_id=None,
        active=True,
    )


def test_resource_mutation_contract_parity_across_create_operations():
    api = _api()
    resource = api.create_resource(_resource())
    assignment = api.create_assignment(
        ResourceAssignment(
            activity_id="A-1",
            resource_id="R-1",
            planned_units=Decimal("10"),
            actual_units=Decimal("2"),
        )
    )

    assert resource["contract_version"] == assignment["contract_version"] == RESOURCE_CONTRACT_VERSION
    assert resource["operation"] == "create_resource"
    assert assignment["operation"] == "create_assignment"
    assert isinstance(resource["revision"], int) and resource["revision"] >= 1
    assert isinstance(assignment["revision"], int) and assignment["revision"] >= 1


def test_resource_decimal_boundary_is_canonical_and_platform_neutral():
    # Decimal values are represented as canonical strings at the API boundary.
    api = _api()
    api.create_resource(_resource())
    result = api.create_assignment(
        ResourceAssignment(
            activity_id="A-1",
            resource_id="R-1",
            planned_units=Decimal("10.50"),
            actual_units=Decimal("2.25"),
        )
    )
    assert result["planned_units"] == "10.50"
    assert result["actual_units"] == "2.25"
    assert result["remaining_units"] == "8.25"
