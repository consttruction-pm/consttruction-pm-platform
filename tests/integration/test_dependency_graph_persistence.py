from datetime import datetime, timezone

import pytest

from construction_pm.dependency_graph_persistence import (
    DependencyIdempotencyReuse,
    DependencyRevisionConflict,
    DependencyLink,
    PostgresDependencyGraphStore,
)


class Cursor:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class Connection:
    def __init__(self):
        self.revisions = {}
        self.links = {}
        self.audit = []

    def execute(self, sql, params=()):
        if sql.startswith("INSERT INTO project_dependency_revisions"):
            self.revisions.setdefault((params[0], params[1]), 0)
            return Cursor()
        if sql.startswith("SELECT revision FROM project_dependency_revisions"):
            return Cursor((self.revisions.get((params[0], params[1])),))
        if sql.startswith("UPDATE project_dependency_revisions"):
            key = (params[1], params[2])
            if self.revisions.get(key) == params[3]:
                self.revisions[key] = params[0]
            return Cursor()
        if sql.startswith("SELECT fingerprint, link_json"):
            return Cursor(self.links.get(("idem", *params)))
        if sql.startswith("SELECT link_json, graph_revision"):
            return Cursor(self.links.get(("link", *params)))
        if sql.startswith("INSERT INTO project_dependency_links"):
            key = (params[0], params[1], params[2])
            value = (params[6], params[5])
            self.links[("link", *key)] = value
            self.links[("idem", params[0], params[1], params[3])] = (params[4], params[6], params[5])
            return Cursor()
        if sql.startswith("INSERT INTO project_dependency_audit"):
            self.audit.append((params[0], params[1], params[2], params[3], params[4], params[5], params[6]))
            return Cursor()
        if sql.startswith("SELECT graph_revision, event_type"):
            rows=[(a[3],a[4],a[5],a[6]) for a in self.audit if a[:3]==params]
            return Cursor(rows=rows)
        return Cursor()


def link(**overrides):
    values = dict(
        resource_id="dep-1",
        tenant_id="T-1",
        project_id="P-1",
        revision=1,
        source_resource_id="schedule:task-1",
        target_resource_id="change:chg-1",
        dependency_type="schedule_to_change",
        metadata={"relation": "blocks"},
    )
    values.update(overrides)
    return DependencyLink(**values)


def test_persist_replay_and_readback():
    connection = Connection()
    store = PostgresDependencyGraphStore(connection)
    store.initialize()
    store.ensure_project("T-1", "P-1")
    now = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)

    created = store.persist(link(), expected_graph_revision=0, idempotency_key="k-1", actor_id="u-1", occurred_at=now)
    replay = store.persist(link(), expected_graph_revision=0, idempotency_key="k-1", actor_id="u-1", occurred_at=now)

    assert created.graph_revision == 1
    assert replay == created
    assert store.get("T-1", "P-1", "dep-1") == created
    assert store.history("T-1", "P-1", "dep-1")[0].event_type == "created"


def test_stale_revision_and_idempotency_reuse_are_rejected():
    connection = Connection()
    store = PostgresDependencyGraphStore(connection)
    store.initialize()
    store.ensure_project("T-1", "P-1")
    now = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)
    store.persist(link(), expected_graph_revision=0, idempotency_key="k-1", actor_id="u-1", occurred_at=now)

    with pytest.raises(DependencyRevisionConflict):
        store.persist(link(resource_id="dep-2"), expected_graph_revision=0, idempotency_key="k-2", actor_id="u-1", occurred_at=now)

    with pytest.raises(DependencyIdempotencyReuse):
        store.persist(link(metadata={"relation": "depends_on"}), expected_graph_revision=1, idempotency_key="k-1", actor_id="u-1", occurred_at=now)


def test_self_reference_is_rejected():
    with pytest.raises(ValueError, match="SELF_REFERENCE"):
        link(target_resource_id="schedule:task-1").validate()


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"expected_graph_revision": True}, "INVALID_DEPENDENCY_EXPECTED_GRAPH_REVISION"),
        ({"expected_graph_revision": -1}, "INVALID_DEPENDENCY_EXPECTED_GRAPH_REVISION"),
        ({"idempotency_key": ""}, "INVALID_DEPENDENCY_IDEMPOTENCY_KEY"),
        ({"idempotency_key": None}, "INVALID_DEPENDENCY_IDEMPOTENCY_KEY"),
        ({"actor_id": ""}, "INVALID_DEPENDENCY_ACTOR_ID"),
        ({"actor_id": None}, "INVALID_DEPENDENCY_ACTOR_ID"),
    ],
)
def test_mutation_metadata_is_rejected_before_database_mutation(kwargs, message):
    connection = Connection()
    store = PostgresDependencyGraphStore(connection)
    store.initialize()
    store.ensure_project("T-1", "P-1")
    now = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)

    params = {
        "expected_graph_revision": 0,
        "idempotency_key": "valid-key",
        "actor_id": "u-1",
        "occurred_at": now,
    }
    params.update(kwargs)

    with pytest.raises(ValueError, match=message):
        store.persist(link(), **params)

    assert connection.revisions[("T-1", "P-1")] == 0
    assert connection.audit == []
