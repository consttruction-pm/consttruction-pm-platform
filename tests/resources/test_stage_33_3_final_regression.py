from decimal import Decimal

from construction_pm.resources.api import ResourceAPI
from construction_pm.resources.application import ResourceApplicationService
from construction_pm.resources.authorization import AllowAllAuthorizationPolicy
from construction_pm.resources.context import ProjectContext
from construction_pm.resources.idempotency import InMemoryMutationIdempotencyStore
from construction_pm.resources.models import Resource, ResourceAssignment, ResourceType
from construction_pm.resources.repository import InMemoryResourceRepository
from construction_pm.resources.transactions import NoOpTransactionManager


def test_resource_backend_contracts_work_together():
    context = ProjectContext("tenant-1", "company-1", "project-1")
    repository = InMemoryResourceRepository()
    service = ResourceApplicationService(
        repository=repository,
        context=context,
        transaction_manager=NoOpTransactionManager(),
        idempotency_store=InMemoryMutationIdempotencyStore(),
        authorization_policy=AllowAllAuthorizationPolicy(),
    )
    api = ResourceAPI(service)

    resource = Resource(
        id="R-1",
        code="LAB-01",
        name="Labor",
        resource_type=ResourceType.LABOR,
        unit="hour",
        rates=(),
        calendar_id=None,
        active=True,
    )
    first = api.create_resource(resource, idempotency_key="resource-create-1")
    replay = api.create_resource(resource, idempotency_key="resource-create-1")
    assert first["id"] == replay["id"] == "R-1"
    assert first["revision"] == replay["revision"] == 1

    assignment = ResourceAssignment(
        activity_id="A-1",
        resource_id="R-1",
        planned_units=Decimal("10"),
        actual_units=Decimal("3"),
    )
    created = api.create_assignment(assignment, idempotency_key="assignment-create-1")
    repeated = api.create_assignment(assignment, idempotency_key="assignment-create-1")
    assert created["revision"] == repeated["revision"] == 1
    assert repeated["remaining_units"] == "7"


def test_revision_and_idempotency_contracts_remain_context_scoped():
    repository = InMemoryResourceRepository()
    store = InMemoryMutationIdempotencyStore()
    context_a = ProjectContext("tenant-1", "company-1", "project-a")
    context_b = ProjectContext("tenant-1", "company-1", "project-b")
    calls = []

    def mutation():
        calls.append("a")
        return "ok"

    assert store.execute(context_a, "k", "op", "fp", mutation) == "ok"
    assert store.execute(context_a, "k", "op", "fp", mutation) == "ok"
    assert store.execute(context_b, "k", "op", "fp", mutation) == "ok"
    assert calls == ["a", "a"]

    resource = Resource(
        id="R-1", code="LAB", name="Labor", resource_type=ResourceType.LABOR,
        unit="hour", rates=(), calendar_id=None, active=True,
    )
    repository.save_resource(context_a, resource)
    assert repository.get_resource_revision(context_a, "R-1") == 1
    assert repository.get_resource(context_b, "R-1") is None
