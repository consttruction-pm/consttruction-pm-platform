from decimal import Decimal

import pytest

from construction_pm.resources.api import ResourceAPI
from construction_pm.resources.application import ResourceApplicationService
from construction_pm.resources.context import ProjectContext
from construction_pm.resources.models import Resource, ResourceAssignment, ResourceType
from construction_pm.resources.repository import InMemoryResourceRepository
from construction_pm.resources.transactions import NoOpTransactionManager


CONTEXT = ProjectContext("tenant-1", "company-1", "project-1")


def make_resource() -> Resource:
    return Resource(
        id="R-1", code="LAB-01", name="Labor", resource_type=ResourceType.LABOR,
        unit="hour", rates=(), calendar_id=None, active=True,
    )


def make_service(repo: InMemoryResourceRepository) -> ResourceApplicationService:
    return ResourceApplicationService(
        repository=repo,
        context=CONTEXT,
        transaction_manager=NoOpTransactionManager(),
    )


def test_repository_is_deterministic_and_defensive():
    repo = InMemoryResourceRepository()
    resource = make_resource()
    repo.save_resource(CONTEXT, resource)
    assert repo.get_resource(CONTEXT, "R-1") == resource
    assert repo.list_resources(CONTEXT) == [resource]


def test_application_rejects_unknown_resource_assignment():
    service = make_service(InMemoryResourceRepository())
    assignment = ResourceAssignment(
        activity_id="A-1", resource_id="R-X",
        planned_units=Decimal("2"), actual_units=Decimal("0"),
    )
    with pytest.raises(ValueError, match="Unknown resource"):
        service.assign_resource(assignment)


def test_api_keeps_decimal_values_typed_as_strings_at_contract_boundary():
    service = make_service(InMemoryResourceRepository())
    api = ResourceAPI(service)
    dto = api.create_resource(make_resource())
    assert dto["id"] == "R-1"

    dto = api.create_assignment(ResourceAssignment(
        activity_id="A-1", resource_id="R-1",
        planned_units=Decimal("2.50"), actual_units=Decimal("1.25"),
    ))
    assert dto["planned_units"] == "2.50"
    assert dto["remaining_units"] == "1.25"


def test_api_calls_normalized_remaining_units_method():
    service = make_service(InMemoryResourceRepository())
    api = ResourceAPI(service)
    api.create_resource(make_resource())
    dto = api.create_assignment(ResourceAssignment(
        activity_id="A-2", resource_id="R-1",
        planned_units=Decimal("10"), actual_units=Decimal("4"),
    ))
    assert dto["remaining_units"] == "6"


def test_repository_context_isolation_for_resources_and_assignments():
    repo = InMemoryResourceRepository()
    project_a = ProjectContext("tenant-1", "company-1", "project-a")
    project_b = ProjectContext("tenant-1", "company-1", "project-b")
    repo.save_resource(project_a, make_resource())
    repo.save_assignment(
        project_a,
        ResourceAssignment(
            activity_id="A-1",
            resource_id="R-1",
            planned_units=Decimal("2"),
            actual_units=Decimal("1"),
        ),
    )
    assert repo.get_resource(project_b, "R-1") is None
    assert repo.list_assignments(project_b) == []


def test_repository_rejects_invalid_project_context():
    repo = InMemoryResourceRepository()
    invalid = ProjectContext("tenant-1", "company-1", "")
    with pytest.raises(ValueError, match="project_id"):
        repo.get_resource(invalid, "R-1")


def test_application_validation_uses_stable_error_category():
    service = make_service(InMemoryResourceRepository())
    with pytest.raises(Exception) as exc_info:
        service.register_resource(
            Resource(
                id="", code="LAB-01", name="Labor",
                resource_type=ResourceType.LABOR, unit="hour",
                rates=(), calendar_id=None, active=True,
            )
        )
    assert exc_info.value.category.value == "validation"
    assert exc_info.value.code == "INVALID_INPUT"


def test_api_serializes_unknown_resource_as_stable_error():
    service = make_service(InMemoryResourceRepository())
    api = ResourceAPI(service)
    dto = api.create_assignment(
        ResourceAssignment(
            activity_id="A-3", resource_id="R-MISSING",
            planned_units=Decimal("1"), actual_units=Decimal("0"),
        )
    )
    assert dto["error"]["category"] == "not_found"
    assert dto["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert dto["error"]["retryable"] is False


def test_api_serializes_invalid_context_as_stable_error():
    service = ResourceApplicationService(
        repository=InMemoryResourceRepository(),
        context=ProjectContext("tenant-1", "company-1", ""),
        transaction_manager=NoOpTransactionManager(),
    )
    dto = ResourceAPI(service).create_resource(make_resource())
    assert dto["error"]["category"] == "context"
    assert dto["error"]["code"] == "INVALID_PROJECT_CONTEXT"
