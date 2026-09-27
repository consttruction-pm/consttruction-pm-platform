from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import AuthorizationContext, AuthorizationError, Permission, RoleBasedAuthorizationPolicy
from construction_pm.dependency_graph_application import DependencyGraphApplicationService
from construction_pm.dependency_graph_persistence import DependencyLink, PostgresDependencyGraphStore


class Connection:
    def __init__(self):
        self.revision = 0
        self.link = None
        self.audit = []

    def execute(self, sql, params=()):
        class Cursor:
            def __init__(self, row=None, rows=None):
                self.row, self.rows = row, rows or []
            def fetchone(self): return self.row
            def fetchall(self): return self.rows

        if sql.startswith("INSERT INTO project_dependency_revisions"):
            return Cursor()
        if sql.startswith("SELECT revision"):
            return Cursor((self.revision,))
        if sql.startswith("UPDATE project_dependency_revisions"):
            self.revision = params[0]
            return Cursor()
        if sql.startswith("SELECT fingerprint"):
            return Cursor(None)
        if sql.startswith("INSERT INTO project_dependency_links"):
            self.link = (params[6], params[5])
            return Cursor()
        if sql.startswith("INSERT INTO project_dependency_audit"):
            self.audit.append(params)
            return Cursor()
        return Cursor()


def policy():
    return RoleBasedAuthorizationPolicy({
        "planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE}),
        "viewer": frozenset({Permission.PROJECT_READ}),
    })


def link(**overrides):
    values = dict(
        resource_id="dep-1", tenant_id="T-1", project_id="P-1", revision=1,
        source_resource_id="schedule:task-1", target_resource_id="rfi:rfi-1",
        dependency_type="schedule_to_rfi", metadata={"relation": "blocks"},
    )
    values.update(overrides)
    return DependencyLink(**values)


def ctx(**overrides):
    values = dict(tenant_id="T-1", project_id="P-1", user_id="u-1", roles=frozenset({"planner"}))
    values.update(overrides)
    return AuthorizationContext(**values)


def test_application_boundary_enforces_scope_and_actor():
    service = DependencyGraphApplicationService(PostgresDependencyGraphStore(Connection()), policy())
    now = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)
    service.store.initialize()
    service.store.ensure_project("T-1", "P-1")

    created = service.create(
        link(),
        context=ctx(),
        expected_graph_revision=0,
        idempotency_key="k-1",
        actor_id="u-1",
        occurred_at=now,
    )
    assert created.graph_revision == 1

    with pytest.raises(AuthorizationError, match="CROSS_PROJECT"):
        service.create(
            link(tenant_id="T-2"),
            context=ctx(),
            expected_graph_revision=1,
            idempotency_key="k-2",
            actor_id="u-1",
            occurred_at=now,
        )

    with pytest.raises(AuthorizationError, match="ACTOR_MISMATCH"):
        service.create(
            link(resource_id="dep-2"),
            context=ctx(),
            expected_graph_revision=1,
            idempotency_key="k-2",
            actor_id="other",
            occurred_at=now,
        )


def test_application_boundary_denies_viewer_before_store_mutation():
    service = DependencyGraphApplicationService(PostgresDependencyGraphStore(Connection()), policy())
    service.store.initialize()
    service.store.ensure_project("T-1", "P-1")
    now = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)

    with pytest.raises(AuthorizationError, match="DEPENDENCY_WRITE_NOT_AUTHORIZED"):
        service.create(
            link(),
            context=ctx(roles=frozenset({"viewer"})),
            expected_graph_revision=0,
            idempotency_key="viewer-1",
            actor_id="u-1",
            occurred_at=now,
        )

    assert service.store.connection.revision == 0


def test_application_boundary_preserves_expected_revision_and_idempotency_inputs():
    service = DependencyGraphApplicationService(PostgresDependencyGraphStore(Connection()), policy())
    service.store.initialize()
    service.store.ensure_project("T-1", "P-1")
    now = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)

    created = service.create(
        link(revision=7),
        context=ctx(),
        expected_graph_revision=0,
        idempotency_key="preserve-1",
        actor_id="u-1",
        occurred_at=now,
    )

    assert created.link.revision == 7
    assert created.graph_revision == 1
    assert service.store.connection.link[1] == 1
