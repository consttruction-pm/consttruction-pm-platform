from decimal import Decimal

import pytest

from construction_pm.backend_p0.idempotency import InMemoryScopedIdempotencyStore\nfrom construction_pm.resources.application import ResourceApplicationService
from construction_pm.resources.context import ProjectContext
from construction_pm.resources.errors import ApplicationError
from construction_pm.resources.idempotency import (
    InMemoryMutationIdempotencyStore,
    assignment_fingerprint,
)
from construction_pm.resources.models import Resource, ResourceAssignment, ResourceType
from construction_pm.resources.repository import InMemoryResourceRepository
from construction_pm.resources.transactions import NoOpTransactionManager


CONTEXT = ProjectContext("tenant-1", "company-1", "project-1")


def make_resource() -> Resource:
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


def make_service(store: InMemoryScopedIdempotencyStore) -> ResourceApplicationService:
    return ResourceApplicationService(
        repository=InMemoryResourceRepository(),
        context=CONTEXT,
        transaction_manager=NoOpTransactionManager(),
        idempotency_store=store,
    )


def test_store_replays_same_result_without_running_mutation_twice():
    store = InMemoryMutationIdempotencyStore()
    calls = 0

    def mutation() -> str:
        nonlocal calls
        calls += 1
        return "created"

    first = store.execute(
        CONTEXT,
        "key-1",
        "create_resource",
        "fingerprint-1",
        mutation,
    )
    second = store.execute(
        CONTEXT,
        "key-1",
        "create_resource",
        "fingerprint-1",
        mutation,
    )

    assert first == second == "created"
    assert calls == 1


def test_store_rejects_same_key_with_different_fingerprint():
    store = InMemoryMutationIdempotencyStore()

    store.execute(CONTEXT, "key-1", "create_resource", "fingerprint-1", lambda: "created")

    with pytest.raises(ApplicationError) as exc_info:
        store.execute(CONTEXT, "key-1", "create_resource", "fingerprint-2", lambda: "wrong")

    assert exc_info.value.category.value == "conflict"
    assert exc_info.value.code == "IDEMPOTENCY_KEY_REUSE"


def test_store_isolated_by_project_context():
    store = InMemoryMutationIdempotencyStore()
    other = ProjectContext("tenant-1", "company-1", "project-2")
    calls = 0

    def mutation() -> str:
        nonlocal calls
        calls += 1
        return str(calls)

    assert store.execute(CONTEXT, "key-1", "op", "fp", mutation) == "1"
    assert store.execute(other, "key-1", "op", "fp", mutation) == "2"


def test_application_resource_mutation_replays_with_same_idempotency_key():
    store = InMemoryMutationIdempotencyStore()
    service = make_service(store)
    resource = make_resource()

    first = service.register_resource(resource, idempotency_key="req-1")
    second = service.register_resource(resource, idempotency_key="req-1")

    assert first == second
    assert service.get_resource("R-1") == resource


def test_assignment_fingerprint_is_deterministic():
    assignment = ResourceAssignment(
        activity_id="A-1",
        resource_id="R-1",
        planned_units=Decimal("10"),
        actual_units=Decimal("2"),
    )
    assert assignment_fingerprint(assignment) == assignment_fingerprint(assignment)
