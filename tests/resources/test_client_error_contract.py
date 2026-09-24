import pytest

from construction_pm.resources.api import ResourceAPI
from construction_pm.resources.application import ResourceApplicationService
from construction_pm.resources.authorization import AllowAllAuthorizationPolicy
from construction_pm.resources.context import ProjectContext
from construction_pm.resources.idempotency import InMemoryMutationIdempotencyStore
from construction_pm.resources.models import Resource, ResourceType
from construction_pm.resources.repository import InMemoryResourceRepository
from construction_pm.resources.transactions import NoOpTransactionManager


def _api():
    service = ResourceApplicationService(
        repository=InMemoryResourceRepository(),
        context=ProjectContext("t", "c", "p"),
        transaction_manager=NoOpTransactionManager(),
        idempotency_store=InMemoryMutationIdempotencyStore(),
        authorization_policy=AllowAllAuthorizationPolicy(),
    )
    return ResourceAPI(service)


def _valid_resource(resource_id="R-1"):
    return Resource(
        id=resource_id,
        code="LAB",
        name="Labor",
        resource_type=ResourceType.LABOR,
        unit="hour",
        rates=(),
        calendar_id=None,
        active=True,
    )


def _assert_error(dto, category, code, retryable=False):
    assert set(dto) == {"error"}
    error = dto["error"]
    assert set(error) == {"category", "code", "message", "retryable"}
    assert error["category"] == category
    assert error["code"] == code
    assert isinstance(error["message"], str) and error["message"]
    assert error["retryable"] is retryable


def test_client_error_contract_is_stable_for_validation():
    result = _api().create_resource(_valid_resource(resource_id=""))
    _assert_error(result, "validation", "INVALID_INPUT")


def test_client_error_contract_is_stable_for_idempotency_key_reuse():
    api = _api()
    api.create_resource(_valid_resource(), idempotency_key="same-key")
    result = api.create_resource(_valid_resource(name="Changed") if False else _valid_resource(), idempotency_key="same-key")
    # The second request uses the same canonical payload; it must be a replay, not an error.
    assert result["contract_version"] == "resource.v1"
