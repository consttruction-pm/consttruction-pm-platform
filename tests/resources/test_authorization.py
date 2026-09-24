from decimal import Decimal

import pytest

from construction_pm.resources.application import ResourceApplicationService
from construction_pm.resources.authorization import DenyAuthorizationPolicy
from construction_pm.resources.context import ProjectContext
from construction_pm.resources.errors import ApplicationError
from construction_pm.resources.models import Resource, ResourceType
from construction_pm.resources.repository import InMemoryResourceRepository
from construction_pm.resources.transactions import NoOpTransactionManager


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


def test_authorization_policy_blocks_resource_mutation_before_persistence():
    repo = InMemoryResourceRepository()
    service = ResourceApplicationService(
        repository=repo,
        context=ProjectContext("tenant-1", "company-1", "project-1"),
        transaction_manager=NoOpTransactionManager(),
        authorization_policy=DenyAuthorizationPolicy(),
    )

    with pytest.raises(ApplicationError) as exc_info:
        service.register_resource(make_resource())

    assert exc_info.value.category.value == "authorization"
    assert exc_info.value.code == "FORBIDDEN"
    assert repo.list_resources(service.context) == []


def test_authorization_is_scoped_to_mutation_operation():
    class RecordingPolicy:
        def __init__(self):
            self.operations = []

        def authorize(self, context, operation):
            context.validate()
            self.operations.append(operation)

    policy = RecordingPolicy()
    service = ResourceApplicationService(
        repository=InMemoryResourceRepository(),
        context=ProjectContext("tenant-1", "company-1", "project-1"),
        transaction_manager=NoOpTransactionManager(),
        authorization_policy=policy,
    )

    service.register_resource(make_resource())
    assert policy.operations == ["register_resource"]
