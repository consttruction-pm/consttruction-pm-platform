from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import AuthorizationContext, Permission, RoleBasedAuthorizationPolicy
from construction_pm.dependency_graph_api import DependencyGraphAPI, DependencyGraphCreateRequest
from construction_pm.dependency_graph_application import DependencyGraphApplicationService
from construction_pm.dependency_graph_persistence import DependencyLink, StoredDependencyLink


class Store:
    def persist(self, link, *, expected_graph_revision, idempotency_key, actor_id, occurred_at):
        return StoredDependencyLink(link, expected_graph_revision + 1)


def api():
    policy = RoleBasedAuthorizationPolicy({"planner": frozenset({Permission.PROJECT_WRITE})})
    return DependencyGraphAPI(DependencyGraphApplicationService(Store(), policy))


def request(**overrides):
    values = dict(
        contract_version="dependency-graph.v1",
        resource_id="dep-1",
        tenant_id="T-1",
        project_id="P-1",
        revision=7,
        source_resource_id="schedule:task-1",
        target_resource_id="progress:task-1",
        dependency_type="schedule_to_progress",
        metadata={"source": "test"},
        expected_graph_revision=6,
        idempotency_key="idem-1",
        actor_id="u-1",
        occurred_at=datetime(2026, 9, 27, 6, 0, tzinfo=timezone.utc),
    )
    values.update(overrides)
    return DependencyGraphCreateRequest(**values)


def context():
    return AuthorizationContext("T-1", "P-1", "u-1", frozenset({"planner"}))


def test_api_returns_versioned_transport_envelope_without_calculating_control_logic():
    result = api().create(request(), auth_context=context())

    assert result == {
        "contract_version": "dependency-graph.v1",
        "operation": "create",
        "resource_id": "dep-1",
        "tenant_id": "T-1",
        "project_id": "P-1",
        "revision": 7,
        "graph_revision": 7,
        "source_resource_id": "schedule:task-1",
        "target_resource_id": "progress:task-1",
        "dependency_type": "schedule_to_progress",
        "metadata": {"source": "test"},
    }


def test_api_rejects_unknown_contract_version_before_application():
    with pytest.raises(ValueError, match="UNSUPPORTED_DEPENDENCY_CONTRACT_VERSION"):
        api().create(request(contract_version="dependency-graph.v2"), auth_context=context())


def test_api_requires_timezone_aware_audit_timestamp():
    with pytest.raises(ValueError, match="DEPENDENCY_AUDIT_TIMESTAMP_MUST_BE_TIMEZONE_AWARE"):
        api().create(
            request(occurred_at=datetime(2026, 9, 27, 6, 0)),
            auth_context=context(),
        )


def test_api_preserves_distinct_project_and_graph_revision_fields():
    class RevisionStore:
        def persist(self, link, **kwargs):
            return StoredDependencyLink(link, 99)

    service = DependencyGraphApplicationService(
        RevisionStore(),
        RoleBasedAuthorizationPolicy({"planner": frozenset({Permission.PROJECT_WRITE})}),
    )
    result = DependencyGraphAPI(service).create(request(revision=7, expected_graph_revision=98), auth_context=context())

    assert result["revision"] == 7
    assert result["graph_revision"] == 99
