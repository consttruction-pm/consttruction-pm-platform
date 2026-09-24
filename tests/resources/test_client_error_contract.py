import pytest

from construction_pm.resources.api import ResourceAPI
from construction_pm.resources.application import ResourceApplicationService
from construction_pm.resources.authorization import AllowAllAuthorizationPolicy, DenyAuthorizationPolicy
from construction_pm.resources.context import ProjectContext
from construction_pm.resources.idempotency import InMemoryMutationIdempotencyStore
from construction_pm.resources.models import Resource, ResourceAssignment, ResourceType
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


def _valid_resource(resource_id="R-1", code="LAB", name="Labor"):
    return Resource(
        id=resource_id,
        code=code,
        name=name,
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
    result = _api().create_resource(_valid_resource(code=""))
    _assert_error(result, "validation", "INVALID_INPUT")


def test_client_error_contract_is_stable_for_stale_revision():
    api = _api()
    api.create_resource(_valid_resource())
    result = api.create_resource(_valid_resource(name="Changed"), expected_revision=0)
    _assert_error(result, "conflict", "STALE_REVISION")


def test_client_error_contract_is_stable_for_idempotency_key_reuse():
    api = _api()
    api.create_resource(_valid_resource(), idempotency_key="same-key")
    result = api.create_resource(_valid_resource(name="Changed"), idempotency_key="same-key")
    _assert_error(result, "conflict", "IDEMPOTENCY_KEY_REUSE")


def test_client_error_contract_is_stable_for_authorization_denial():
    service = ResourceApplicationService(
        repository=InMemoryResourceRepository(),
        context=ProjectContext("t", "c", "p"),
        transaction_manager=NoOpTransactionManager(),
        idempotency_store=InMemoryMutationIdempotencyStore(),
        authorization_policy=DenyAuthorizationPolicy(),
    )
    result = ResourceAPI(service).create_resource(_valid_resource())
    _assert_error(result, "authorization", "FORBIDDEN")


def test_client_error_contract_is_stable_for_missing_assignment_resource():
    assignment = ResourceAssignment(activity_id="A-1", resource_id="missing", planned_units=None, actual_units=None)
    result = _api().create_assignment(assignment)
    _assert_error(result, "not_found", "RESOURCE_NOT_FOUND")


def test_application_error_exposes_stable_fields():
    from construction_pm.resources.errors import ApplicationError, ErrorCategory, conflict_error
    error = conflict_error("IDEMPOTENCY_KEY_REUSE", "duplicate mutation")
    assert isinstance(error, ApplicationError)
    assert error.category is ErrorCategory.CONFLICT
    assert error.code == "IDEMPOTENCY_KEY_REUSE"
    assert error.message == "duplicate mutation"
    assert error.retryable is False
    assert error.to_dto()["error"]["code"] == "IDEMPOTENCY_KEY_REUSE"
