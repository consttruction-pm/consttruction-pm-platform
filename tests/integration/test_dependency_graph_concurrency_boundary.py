from copy import deepcopy
from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    Permission,
    RoleBasedAuthorizationPolicy,
)
from construction_pm.dependency_graph_application import DependencyGraphApplicationService
from construction_pm.dependency_graph_persistence import (
    DependencyIdempotencyReuse,
    DependencyLink,
    DependencyRevisionConflict,
    PostgresDependencyGraphStore,
)


class Connection:
    def __init__(self):
        self.revision = 0
        self.links = {}
        self.audit = []
        self.fail_audit = False

    class Transaction:
        def __init__(self, connection):
            self.connection = connection
            self.snapshot = None

        def __enter__(self):
            self.snapshot = (
                self.connection.revision,
                deepcopy(self.connection.links),
                deepcopy(self.connection.audit),
            )
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            if exc_type is not None:
                (
                    self.connection.revision,
                    self.connection.links,
                    self.connection.audit,
                ) = self.snapshot
            return False

    def transaction(self):
        return self.Transaction(self)

    def execute(self, sql, params=()):
        class Cursor:
            def __init__(self, row=None, rows=None):
                self.row = row
                self.rows = rows or []

            def fetchone(self):
                return self.row

            def fetchall(self):
                return self.rows

        if sql.startswith("SELECT revision"):
            return Cursor((self.revision,))
        if sql.startswith("SELECT fingerprint"):
            key = params[2]
            row = self.links.get(key)
            return Cursor(None if row is None else row)
        if sql.startswith("UPDATE project_dependency_revisions"):
            self.revision = params[0]
            return Cursor()
        if sql.startswith("INSERT INTO project_dependency_links"):
            self.links[params[3]] = (params[4], params[6], params[5])
            return Cursor()
        if sql.startswith("INSERT INTO project_dependency_audit"):
            if self.fail_audit:
                raise RuntimeError("AUDIT_WRITE_FAILED")
            self.audit.append(params)
            return Cursor()
        if sql.startswith("SELECT graph_revision, event_type, actor_id, occurred_at"):
            rows = [
                (event[3], event[4], event[5], event[6])
                for event in self.audit
                if event[0] == params[0] and event[1] == params[1] and event[2] == params[2]
            ]
            rows.sort(key=lambda row: row[0])
            return Cursor(rows=rows)
        return Cursor()


def make_service():
    connection = Connection()
    store = PostgresDependencyGraphStore(connection)
    policy = RoleBasedAuthorizationPolicy(
        {"planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE})}
    )
    store.ensure_project("tenant-a", "project-a")
    return DependencyGraphApplicationService(store, policy), connection


def make_link(resource_id="dependency-1", tenant_id="tenant-a", project_id="project-a", source_resource_id="schedule:task-1", target_resource_id="progress:task-1", dependency_type="schedule_to_progress"):
    return DependencyLink(
        resource_id=resource_id,
        tenant_id=tenant_id,
        project_id=project_id,
        revision=1,
        source_resource_id=source_resource_id,
        target_resource_id=target_resource_id,
        dependency_type=dependency_type,
        metadata={},
        source_revision=1,
        target_revision=1,
    )


def context(tenant_id="tenant-a", project_id="project-a", user_id="user-1"):
    return AuthorizationContext(
        tenant_id, project_id, user_id, frozenset({"planner"})
    )


def timestamp():
    return datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)


def test_stale_expected_graph_revision_is_rejected_without_advancing_revision():
    service, connection = make_service()
    service.create(
        make_link(),
        context=context(),
        expected_graph_revision=0,
        idempotency_key="idem-1",
        actor_id="user-1",
        occurred_at=timestamp(),
    )

    with pytest.raises(DependencyRevisionConflict, match="DEPENDENCY_REVISION_CONFLICT"):
        service.create(
            make_link(resource_id="dependency-2"),
            context=context(),
            expected_graph_revision=0,
            idempotency_key="idem-2",
            actor_id="user-1",
            occurred_at=timestamp(),
        )

    assert connection.revision == 1
    assert "idem-2" not in connection.links


def test_cross_tenant_or_project_context_cannot_reach_persistence():
    service, connection = make_service()

    with pytest.raises(AuthorizationError, match="CROSS_PROJECT_DEPENDENCY"):
        service.create(
            make_link(),
            context=context(tenant_id="tenant-b"),
            expected_graph_revision=0,
            idempotency_key="idem-cross-tenant",
            actor_id="user-1",
            occurred_at=timestamp(),
        )

    with pytest.raises(AuthorizationError, match="CROSS_PROJECT_DEPENDENCY"):
        service.create(
            make_link(),
            context=context(project_id="project-b"),
            expected_graph_revision=0,
            idempotency_key="idem-cross-project",
            actor_id="user-1",
            occurred_at=timestamp(),
        )

    assert connection.revision == 0
    assert connection.links == {}


def test_actor_identity_mismatch_cannot_write_dependency_graph():
    service, connection = make_service()

    with pytest.raises(AuthorizationError, match="DEPENDENCY_ACTOR_MISMATCH"):
        service.create(
            make_link(),
            context=context(user_id="user-1"),
            expected_graph_revision=0,
            idempotency_key="idem-actor",
            actor_id="user-2",
            occurred_at=timestamp(),
        )

    assert connection.revision == 0
    assert connection.links == {}


def test_idempotent_replay_does_not_advance_revision_or_duplicate_audit():
    service, connection = make_service()
    first = service.create(
        make_link(),
        context=context(),
        expected_graph_revision=0,
        idempotency_key="idem-replay",
        actor_id="user-1",
        occurred_at=timestamp(),
    )
    replay = service.create(
        make_link(),
        context=context(),
        expected_graph_revision=0,
        idempotency_key="idem-replay",
        actor_id="user-1",
        occurred_at=timestamp(),
    )

    assert replay == first
    assert connection.revision == 1
    assert len(connection.audit) == 1


def test_same_idempotency_key_with_different_payload_is_rejected_without_mutation():
    service, connection = make_service()
    service.create(
        make_link(),
        context=context(),
        expected_graph_revision=0,
        idempotency_key="idem-reuse",
        actor_id="user-1",
        occurred_at=timestamp(),
    )

    with pytest.raises(DependencyIdempotencyReuse, match="IDEMPOTENCY_KEY_REUSE"):
        service.create(
            make_link(resource_id="dependency-2"),
            context=context(),
            expected_graph_revision=1,
            idempotency_key="idem-reuse",
            actor_id="user-1",
            occurred_at=timestamp(),
        )

    assert connection.revision == 1
    assert len(connection.links) == 1
    assert len(connection.audit) == 1


def test_link_and_revision_are_rolled_back_when_audit_write_fails():
    service, connection = make_service()
    connection.fail_audit = True

    with pytest.raises(RuntimeError, match="AUDIT_WRITE_FAILED"):
        service.create(
            make_link(),
            context=context(),
            expected_graph_revision=0,
            idempotency_key="idem-atomic",
            actor_id="user-1",
            occurred_at=timestamp(),
        )

    assert connection.revision == 0
    assert connection.links == {}
    assert connection.audit == []

    connection.fail_audit = False
    stored = service.create(
        make_link(),
        context=context(),
        expected_graph_revision=0,
        idempotency_key="idem-atomic",
        actor_id="user-1",
        occurred_at=timestamp(),
    )

    assert stored.graph_revision == 1
    assert connection.revision == 1
    assert len(connection.links) == 1
    assert len(connection.audit) == 1


def test_audit_history_is_consistent_with_persisted_graph_revision():
    service, connection = make_service()
    service.create(
        make_link(),
        context=context(),
        expected_graph_revision=0,
        idempotency_key="idem-audit",
        actor_id="user-1",
        occurred_at=timestamp(),
    )

    history = service.store.history("tenant-a", "project-a", "dependency-1")

    assert len(history) == 1
    assert history[0].graph_revision == 1
    assert history[0].event_type == "created"
    assert history[0].actor_id == "user-1"
    assert history[0].occurred_at == timestamp()


@pytest.mark.parametrize(
    "overrides, error",
    [
        ({"source_resource_id": "unknown:task-1"}, "INVALID_DEPENDENCY_SOURCE_RESOURCE_ID"),
        ({"target_resource_id": "unknown:task-1"}, "INVALID_DEPENDENCY_TARGET_RESOURCE_ID"),
        ({"dependency_type": "invented_relation"}, "INVALID_DEPENDENCY_TYPE"),
    ],
)
def test_persistence_rejects_unknown_dependency_contract_values(overrides, error):
    service, connection = make_service()

    with pytest.raises(ValueError, match=error):
        service.create(
            make_link(**overrides),
            context=context(),
            expected_graph_revision=0,
            idempotency_key="idem-invalid",
            actor_id="user-1",
            occurred_at=timestamp(),
        )

    assert connection.revision == 0
    assert connection.links == {}
    assert connection.audit == []
