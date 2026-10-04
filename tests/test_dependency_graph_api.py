from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    Permission,
    default_project_policy,
)
from construction_pm.dependency_graph_api import DependencyGraphAPI
from construction_pm.dependency_graph_application import DependencyGraphApplicationService
from construction_pm.dependency_graph_persistence import DependencyLink, StoredDependencyLink


def _context(*, tenant_id: str = "tenant-1", project_id: str = "project-1", roles=frozenset({"viewer"})):
    return AuthorizationContext(
        tenant_id=tenant_id,
        project_id=project_id,
        user_id="user-1",
        roles=roles,
    )


def _stored() -> StoredDependencyLink:
    return StoredDependencyLink(
        DependencyLink(
            resource_id="schedule:link-1",
            tenant_id="tenant-1",
            project_id="project-1",
            revision=0,
            source_resource_id="schedule:task-a",
            target_resource_id="schedule:task-b",
            dependency_type="depends_on",
            metadata={"origin": "p6"},
        ),
        graph_revision=3,
    )


@dataclass
class _ReadStore:
    value: StoredDependencyLink | None

    def get(self, tenant_id: str, project_id: str, resource_id: str):
        if self.value is None:
            return None
        link = self.value.link
        if (tenant_id, project_id, resource_id) != (link.tenant_id, link.project_id, link.resource_id):
            return None
        return self.value


class _NoopTransactions:
    def transaction(self):
        raise AssertionError("read path must not open a write transaction")


class _ReadService:
    def __init__(self, value):
        self.value = value

    def get(self, tenant_id, project_id, resource_id, *, context):
        return self.value


def test_get_returns_versioned_read_contract():
    api = DependencyGraphAPI(_ReadService(_stored()))
    result = api.get(
        tenant_id="tenant-1",
        project_id="project-1",
        resource_id="schedule:link-1",
        auth_context=_context(),
    )

    assert result["contract_version"] == "dependency-graph.v1"
    assert result["operation"] == "get"
    assert result["graph_revision"] == 3
    assert result["metadata"] == {"origin": "p6"}


def test_get_returns_none_for_missing_resource():
    api = DependencyGraphAPI(_ReadService(None))
    assert api.get(
        tenant_id="tenant-1",
        project_id="project-1",
        resource_id="schedule:missing",
        auth_context=_context(),
    ) is None


def test_get_rejects_cross_scope_before_service_call():
    class _FailIfCalled:
        def get(self, *args, **kwargs):
            raise AssertionError("service must not be called")

    api = DependencyGraphAPI(_FailIfCalled())
    with pytest.raises(AuthorizationError, match="CROSS_PROJECT_DEPENDENCY"):
        api.get(
            tenant_id="tenant-2",
            project_id="project-2",
            resource_id="schedule:link-1",
            auth_context=_context(),
        )


def test_get_requires_project_read_permission():
    api = DependencyGraphAPI(_ReadService(_stored()))
    with pytest.raises(AuthorizationError, match="DEPENDENCY_READ_NOT_AUTHORIZED"):
        api.get(
            tenant_id="tenant-1",
            project_id="project-1",
            resource_id="schedule:link-1",
            auth_context=_context(roles=frozenset()),
        )


def test_application_read_boundary_enforces_scope_and_permission():
    store = _ReadStore(_stored())
    service = DependencyGraphApplicationService(
        store=store,
        authorization_policy=default_project_policy(),
        transaction_manager=_NoopTransactions(),
    )

    result = service.get(
        "tenant-1",
        "project-1",
        "schedule:link-1",
        context=_context(),
    )
    assert result == _stored()

    with pytest.raises(AuthorizationError, match="CROSS_PROJECT_DEPENDENCY"):
        service.get("tenant-2", "project-2", "schedule:link-1", context=_context())

    with pytest.raises(AuthorizationError, match="DEPENDENCY_READ_NOT_AUTHORIZED"):
        service.get(
            "tenant-1",
            "project-1",
            "schedule:link-1",
            context=_context(roles=frozenset()),
        )
