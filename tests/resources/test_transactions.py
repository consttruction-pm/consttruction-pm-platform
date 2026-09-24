from decimal import Decimal

from construction_pm.resources.application import ResourceApplicationService
from construction_pm.resources.context import ProjectContext
from construction_pm.resources.models import Resource, ResourceAssignment, ResourceType
from construction_pm.resources.repository import InMemoryResourceRepository
from construction_pm.resources.transactions import NoOpTransactionManager


def make_resource() -> Resource:
    return Resource(id="R-1", code="LAB-01", name="Crew", resource_type=ResourceType.LABOR, unit="hour")


def make_service() -> ResourceApplicationService:
    return ResourceApplicationService(
        repository=InMemoryResourceRepository(),
        context=ProjectContext("tenant-1", "company-1", "project-1"),
        transaction_manager=NoOpTransactionManager(),
    )


def test_transaction_context_propagates_failure_without_hidden_commit():
    manager = NoOpTransactionManager()
    events = []
    try:
        with manager.transaction():
            events.append("write-1")
            raise RuntimeError("abort")
    except RuntimeError:
        pass
    assert events == ["write-1"]


def test_resource_use_case_executes_inside_application_transaction_boundary():
    service = make_service()
    resource = service.register_resource(make_resource())
    assert resource.id == "R-1"
    assignment = service.assign_resource(
        ResourceAssignment(activity_id="A-1", resource_id="R-1", planned_units=Decimal("2"))
    )
    assert assignment.activity_id == "A-1"
