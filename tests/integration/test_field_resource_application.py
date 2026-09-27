from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    default_project_policy,
)
from construction_pm.field_resource_application import FieldResourceApplicationService
from construction_pm.field_resource_persistence import FieldResource


class Store:
    def __init__(self):
        self.calls = []

    def persist(self, resource, **kwargs):
        self.calls.append((resource, kwargs))
        return "stored"


def resource():
    return FieldResource(
        resource_id="field-1",
        tenant_id="T-1",
        project_id="P-1",
        resource_type="daily_log",
        revision=1,
        payload={"work_summary": "concrete pour"},
    )


def context(**overrides):
    values = dict(tenant_id="T-1", project_id="P-1", user_id="u-1", roles=frozenset({"planner"}))
    values.update(overrides)
    return AuthorizationContext(**values)


def test_create_requires_project_scope_and_actor_integrity():
    store = Store()
    service = FieldResourceApplicationService(store, default_project_policy())
    now = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)

    assert service.create(
        resource(),
        context=context(),
        expected_project_revision=0,
        idempotency_key="k-1",
        actor_id="u-1",
        occurred_at=now,
    ) == "stored"

    with pytest.raises(AuthorizationError, match="CROSS_PROJECT_FIELD_RESOURCE"):
        service.create(
            resource(),
            context=context(project_id="P-2"),
            expected_project_revision=0,
            idempotency_key="k-2",
            actor_id="u-1",
            occurred_at=now,
        )

    with pytest.raises(AuthorizationError, match="FIELD_RESOURCE_ACTOR_MISMATCH"):
        service.create(
            resource(),
            context=context(),
            expected_project_revision=0,
            idempotency_key="k-3",
            actor_id="u-2",
            occurred_at=now,
        )


def test_create_requires_write_permission():
    service = FieldResourceApplicationService(Store(), default_project_policy())
    now = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)

    with pytest.raises(AuthorizationError, match="FIELD_RESOURCE_WRITE_NOT_AUTHORIZED"):
        service.create(
            resource(),
            context=context(roles=frozenset({"viewer"})),
            expected_project_revision=0,
            idempotency_key="k-1",
            actor_id="u-1",
            occurred_at=now,
        )
