from copy import deepcopy
from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    Permission,
    RoleBasedAuthorizationPolicy,
)
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.dependency_graph_application import DependencyGraphApplicationService
from construction_pm.dependency_graph_persistence import (
    DependencyIdempotencyReuse,
    DependencyLink,
    DependencyRevisionConflict,
    PostgresDependencyGraphStore,
)


class Cursor:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class Connection:
    def __init__(self):
        self.revision = 0
        self.links = {}
        self.audit = []
        self.commits = 0
        self.rollbacks = 0
        self.fail_on_audit = False
        self._snapshot = None

    def execute(self, sql, params=()):
        if sql.startswith("INSERT INTO project_dependency_revisions"):
            return Cursor()
        if sql.startswith("SELECT revision FROM project_dependency_revisions"):
            return Cursor((self.revision,))
        if sql.startswith("SELECT fingerprint"):
            key = params[2]
            row = self.links.get(key)
            return Cursor(None if row is None else row)
        if sql.startswith("UPDATE project_dependency_revisions"):
            if self._snapshot is None:
                self._snapshot = (
                    self.revision,
                    deepcopy(self.links),
                    deepcopy(self.audit),
                )
            self.revision = params[0]
            return Cursor()
        if sql.startswith("INSERT INTO project_dependency_links"):
            self.links[params[3]] = (params[4], params[6], params[5])
            return Cursor()
        if sql.startswith("INSERT INTO project_dependency_audit"):
            if self.fail_on_audit:
                raise RuntimeError("AUDIT_WRITE_FAILED")
            self.audit.append(params)
            return Cursor()
        if sql.startswith("SELECT graph_revision, event_type, actor_id, occurred_at"):
            rows = [
                (event[3], event[4], event[5], event[6])
                for event in self.audit
                if event[:3] == params
            ]
            rows.sort(key=lambda row: row[0])
            return Cursor(rows=rows)
        return Cursor()

    def commit(self):
        self.commits += 1
        self._snapshot = None

    def rollback(self):
        self.rollbacks += 1
        if self._snapshot is not None:
            self.revision, self.links, self.audit = self._snapshot
        self._snapshot = None


def make_service():
    connection = Connection()
    store = PostgresDependencyGraphStore(connection)
    store.ensure_project("tenant-a", "project-a")
    policy = RoleBasedAuthorizationPolicy(
        {"planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE})}
    )
    service = DependencyGraphApplicationService(
        store,
        policy,
        PostgresTransactionManager(connection),
    )
    return service, connection


def link(**overrides):
    values = dict(
        resource_id="dependency-1",
        tenant_id="tenant-a",
        project_id="project-a",
        revision=1,
        source_resource_id="schedule:task-1",
        target_resource_id="progress:task-1",
        dependency_type="schedule_to_progress",
        metadata={},
        source_revision=2,
        target_revision=3,
    )
    values.update(overrides)
    return DependencyLink(**values)


def context(tenant_id="tenant-a", project_id="project-a", user_id="user-1"):
    return AuthorizationContext(
        tenant_id,
        project_id,
        user_id,
        frozenset({"planner"}),
    )


def timestamp():
    return datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)


def create(service, dependency, *, expected=0, key="idem-1"):
    return service.create(
        dependency,
        context=context(),
        expected_graph_revision=expected,
        idempotency_key=key,
        actor_id="user-1",
        occurred_at=timestamp(),
    )


def test_stale_revision_does_not_mutate_graph():
    service, connection = make_service()
    create(service, link(), expected=0, key="first")

    with pytest.raises(DependencyRevisionConflict, match="DEPENDENCY_REVISION_CONFLICT"):
        create(service, link(resource_id="dependency-2"), expected=0, key="stale")

    assert connection.revision == 1
    assert "stale" not in connection.links


def test_same_key_replay_is_idempotent():
    service, connection = make_service()
    first = create(service, link(), expected=0, key="replay")
    replay = create(service, link(), expected=0, key="replay")

    assert replay == first
    assert connection.revision == 1
    assert len(connection.audit) == 1


def test_same_key_different_payload_is_rejected_without_mutation():
    service, connection = make_service()
    create(service, link(), expected=0, key="reuse")

    with pytest.raises(DependencyIdempotencyReuse, match="IDEMPOTENCY_KEY_REUSE"):
        create(
            service,
            link(target_resource_id="progress:other"),
            expected=1,
            key="reuse",
        )

    assert connection.revision == 1
    assert len(connection.links) == 1
    assert len(connection.audit) == 1


def test_failed_audit_rolls_back_and_allows_retry():
    service, connection = make_service()
    connection.fail_on_audit = True

    with pytest.raises(RuntimeError, match="AUDIT_WRITE_FAILED"):
        create(service, link(), expected=0, key="atomic")

    assert connection.revision == 0
    assert connection.links == {}
    assert connection.audit == []
    assert connection.rollbacks == 1

    connection.fail_on_audit = False
    stored = create(service, link(), expected=0, key="atomic")

    assert stored.graph_revision == 1
    assert connection.commits == 1
    assert len(connection.links) == 1
    assert len(connection.audit) == 1


@pytest.mark.parametrize(
    ("ctx", "error"),
    [
        (context(tenant_id="tenant-b"), "CROSS_PROJECT_DEPENDENCY"),
        (context(project_id="project-b"), "CROSS_PROJECT_DEPENDENCY"),
    ],
)
def test_scope_isolation_rejects_cross_context_writes(ctx, error):
    service, connection = make_service()

    with pytest.raises(AuthorizationError, match=error):
        service.create(
            link(),
            context=ctx,
            expected_graph_revision=0,
            idempotency_key="cross",
            actor_id="user-1",
            occurred_at=timestamp(),
        )

    assert connection.revision == 0
    assert connection.links == {}


def test_actor_identity_is_bound_to_authorization_context():
    service, connection = make_service()

    with pytest.raises(AuthorizationError, match="DEPENDENCY_ACTOR_MISMATCH"):
        service.create(
            link(),
            context=context(),
            expected_graph_revision=0,
            idempotency_key="actor",
            actor_id="user-2",
            occurred_at=timestamp(),
        )

    assert connection.revision == 0
    assert connection.links == {}


def test_audit_history_matches_committed_revision():
    service, _ = make_service()
    create(service, link(), expected=0, key="audit")

    history = service.store.history("tenant-a", "project-a", "dependency-1")

    assert len(history) == 1
    assert history[0].graph_revision == 1
    assert history[0].event_type == "created"
    assert history[0].actor_id == "user-1"
    assert history[0].occurred_at == timestamp()
