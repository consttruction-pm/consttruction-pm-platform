from decimal import Decimal

import pytest

from construction_pm.resources.api import ResourceAPI
from construction_pm.resources.application import ResourceApplicationService
from construction_pm.resources.context import ProjectContext
from construction_pm.resources.errors import ApplicationError
from construction_pm.resources.models import Resource, ResourceAssignment, ResourceType
from construction_pm.resources.repository import InMemoryResourceRepository
from construction_pm.resources.transactions import NoOpTransactionManager

CONTEXT = ProjectContext("tenant-1", "company-1", "project-1")


def resource() -> Resource:
    return Resource(
        id="R-1", code="LAB-01", name="Labor", resource_type=ResourceType.LABOR,
        unit="hour", rates=(), calendar_id=None, active=True,
    )


def service(repo=None):
    return ResourceApplicationService(
        repository=repo or InMemoryResourceRepository(),
        context=CONTEXT,
        transaction_manager=NoOpTransactionManager(),
    )


def test_resource_revision_is_propagated_and_stale_update_is_rejected():
    repo = InMemoryResourceRepository()
    svc = service(repo)
    svc.register_resource(resource())
    assert repo.get_resource_revision(CONTEXT, "R-1") == 1

    updated = Resource(
        id="R-1", code="LAB-02", name="Updated", resource_type=ResourceType.LABOR,
        unit="hour", rates=(), calendar_id=None, active=True,
    )
    svc.register_resource(updated, expected_revision=1)
    assert repo.get_resource_revision(CONTEXT, "R-1") == 2

    with pytest.raises(ApplicationError) as exc_info:
        svc.register_resource(updated, expected_revision=1)
    assert exc_info.value.code == "STALE_REVISION"
    assert exc_info.value.category.value == "conflict"


def test_assignment_revision_is_propagated_and_stale_update_is_rejected():
    repo = InMemoryResourceRepository()
    svc = service(repo)
    svc.register_resource(resource())
    assignment = ResourceAssignment(
        activity_id="A-1", resource_id="R-1",
        planned_units=Decimal("10"), actual_units=Decimal("2"),
    )
    svc.assign_resource(assignment)
    assert repo.get_assignment_revision(CONTEXT, "A-1", "R-1") == 1

    updated = ResourceAssignment(
        activity_id="A-1", resource_id="R-1",
        planned_units=Decimal("12"), actual_units=Decimal("3"),
    )
    svc.assign_resource(updated, expected_revision=1)
    assert repo.get_assignment_revision(CONTEXT, "A-1", "R-1") == 2

    with pytest.raises(ApplicationError) as exc_info:
        svc.assign_resource(updated, expected_revision=1)
    assert exc_info.value.code == "STALE_REVISION"


def test_api_returns_current_revision_and_accepts_expected_revision():
    repo = InMemoryResourceRepository()
    api = ResourceAPI(service(repo))
    first = api.create_resource(resource())
    assert first["revision"] == 1

    updated = Resource(
        id="R-1", code="LAB-02", name="Updated", resource_type=ResourceType.LABOR,
        unit="hour", rates=(), calendar_id=None, active=True,
    )
    second = api.create_resource(updated, expected_revision=1)
    assert second["revision"] == 2


def test_api_returns_stable_stale_revision_error():
    repo = InMemoryResourceRepository()
    api = ResourceAPI(service(repo))
    api.create_resource(resource())
    dto = api.create_resource(resource(), expected_revision=0)
    assert dto["error"]["category"] == "conflict"
    assert dto["error"]["code"] == "STALE_REVISION"
