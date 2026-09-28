from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.field_operations import (
    FieldOperationService,
    FieldOperationType,
    InMemoryFieldOperationRepository,
)
from construction_pm.field_operations_api import (
    FieldOperationAPI,
    FieldOperationAPIError,
    FieldOperationCreateRequest,
    FieldOperationReadRequest,
)


def api():
    repository = InMemoryFieldOperationRepository()
    return FieldOperationAPI(
        service=FieldOperationService(repository),
        repository=repository,
        authorization=default_project_policy(),
    )


def planner():
    return AuthorizationContext(
        tenant_id="tenant-1",
        project_id="project-1",
        user_id="user-1",
        roles=frozenset({"planner"}),
    )


def viewer():
    return AuthorizationContext(
        tenant_id="tenant-1",
        project_id="project-1",
        user_id="user-2",
        roles=frozenset({"viewer"}),
    )


def request(**overrides):
    values = dict(
        contract_version="field-operation.v1",
        tenant_id="tenant-1",
        project_id="project-1",
        operation_id="op-1",
        revision=0,
        operation_type=FieldOperationType.DAILY_LOG,
        occurred_at=datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc),
        actor_id="user-1",
        payload={"weather": "clear", "crew_count": 4},
        expected_revision=0,
        idempotency_key="idem-1",
        location_ref="site-a",
    )
    values.update(overrides)
    return FieldOperationCreateRequest(**values)


def test_create_returns_versioned_typed_envelope():
    result = api().create(request(), auth_context=planner())

    assert result["contract_version"] == "field-operation.v1"
    assert result["operation_type"] == "daily_log"
    assert result["payload"] == {"weather": "clear", "crew_count": 4}
    assert result["occurred_at"] == "2026-09-28T12:00:00+00:00"


def test_create_requires_timezone_aware_timestamp():
    with pytest.raises(FieldOperationAPIError, match="TIMEZONE_AWARE"):
        api().create(
            request(occurred_at=datetime(2026, 9, 28, 12, 0)),
            auth_context=planner(),
        )


def test_create_rejects_cross_scope_context():
    with pytest.raises(AuthorizationError, match="SCOPE_MISMATCH"):
        api().create(
            request(project_id="project-2"),
            auth_context=planner(),
        )


def test_create_requires_actor_to_match_authenticated_user():
    with pytest.raises(AuthorizationError, match="ACTOR_MISMATCH"):
        api().create(
            request(actor_id="different-user"),
            auth_context=planner(),
        )


def test_viewer_can_read_but_cannot_create():
    service_api = api()
    service_api.create(request(), auth_context=planner())

    result = service_api.get(
        FieldOperationReadRequest(
            contract_version="field-operation.v1",
            tenant_id="tenant-1",
            project_id="project-1",
            operation_id="op-1",
        ),
        auth_context=viewer(),
    )
    assert result is not None
    assert result["operation_id"] == "op-1"

    with pytest.raises(AuthorizationError, match="authorization denied"):
        service_api.create(
            request(operation_id="op-2", idempotency_key="idem-2", actor_id="user-2"),
            auth_context=viewer(),
        )


def test_get_is_scope_checked():
    service_api = api()
    service_api.create(request(), auth_context=planner())

    with pytest.raises(AuthorizationError, match="SCOPE_MISMATCH"):
        service_api.get(
            FieldOperationReadRequest(
                contract_version="field-operation.v1",
                tenant_id="tenant-1",
                project_id="project-2",
                operation_id="op-1",
            ),
            auth_context=planner(),
        )
