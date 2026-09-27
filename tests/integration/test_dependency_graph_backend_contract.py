from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import AuthorizationContext, Permission, RoleBasedAuthorizationPolicy
from construction_pm.dependency_graph_api import DependencyGraphAPI, DependencyGraphCreateRequest
from construction_pm.dependency_graph_application import DependencyGraphApplicationService
from construction_pm.dependency_graph_conformance import project_dependency_link
from construction_pm.dependency_graph_persistence import (
    DependencyIdempotencyReuse,
    PostgresDependencyGraphStore,
)


class Connection:
    def __init__(self):
        self.revision = 0
        self.links = {}
        self.audit = []

    def execute(self, sql, params=()):
        class Cursor:
            def __init__(self, row=None, rows=None):
                self.row = row
                self.rows = rows or []

            def fetchone(self):
                return self.row

            def fetchall(self):
                return self.rows

        if sql.startswith("INSERT INTO project_dependency_revisions"):
            return Cursor()
        if sql.startswith("SELECT revision"):
            return Cursor((self.revision,))
        if sql.startswith("UPDATE project_dependency_revisions"):
            self.revision = params[0]
            return Cursor()
        if sql.startswith("SELECT fingerprint"):
            key = params[2]
            row = self.links.get(key)
            return Cursor(None if row is None else (row[0], row[1], row[2]))
        if sql.startswith("INSERT INTO project_dependency_links"):
            self.links[params[3]] = (params[4], params[6], params[5])
            return Cursor()
        if sql.startswith("INSERT INTO project_dependency_audit"):
            self.audit.append(params)
            return Cursor()
        return Cursor()


def service():
    store = PostgresDependencyGraphStore(Connection())
    store.initialize()
    store.ensure_project("T-1", "P-1")
    policy = RoleBasedAuthorizationPolicy(
        {"planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE})}
    )
    return DependencyGraphApplicationService(store, policy)


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
        metadata={"relation": "impacts"},
        expected_graph_revision=0,
        idempotency_key="idem-1",
        actor_id="u-1",
        occurred_at=datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc),
        source_revision=7,
        target_revision=8,
    )
    values.update(overrides)
    return DependencyGraphCreateRequest(**values)


def context():
    return AuthorizationContext("T-1", "P-1", "u-1", frozenset({"planner"}))


def test_backend_contract_round_trip_preserves_revisions_and_typed_projection():
    svc = service()
    response = DependencyGraphAPI(svc).create(request(), auth_context=context())

    assert response["revision"] == 7
    assert response["graph_revision"] == 1
    assert response["source_revision"] == 7
    assert response["target_revision"] == 8

    stored = svc.store.get("T-1", "P-1", "dep-1")
    assert stored is not None
    projection = project_dependency_link(stored.link, graph_revision=stored.graph_revision)
    assert projection.graph.scope.project_revision == 7
    assert projection.graph.nodes["schedule:task-1"].revision == 7
    assert projection.graph.nodes["progress:task-1"].revision == 8


def test_backend_contract_replay_is_idempotent_and_does_not_advance_graph_revision():
    svc = service()
    api = DependencyGraphAPI(svc)
    first = api.create(request(), auth_context=context())
    replay = api.create(request(), auth_context=context())

    assert first == replay
    assert svc.store.connection.revision == 1
    assert len(svc.store.connection.audit) == 1


def test_backend_contract_rejects_same_key_with_different_payload():
    svc = service()
    api = DependencyGraphAPI(svc)
    api.create(request(), auth_context=context())

    with pytest.raises(DependencyIdempotencyReuse, match="IDEMPOTENCY_KEY_REUSE"):
        api.create(
            request(target_resource_id="progress:other"),
            auth_context=context(),
        )
