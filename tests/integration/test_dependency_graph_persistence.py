from datetime import datetime, timezone

import pytest

from construction_pm.dependency_graph_persistence import (
    DependencyIdempotencyReuse,
    DependencyRevisionConflict,
    DependencyLink,
    PostgresDependencyGraphStore,
    dependency_fingerprint,
)


class Cursor:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class Transaction:
    def __init__(self, connection):
        self.connection = connection
        self.snapshot = None

    def __enter__(self):
        self.snapshot = (
            dict(self.connection.revisions),
            dict(self.connection.links),
            list(self.connection.audit),
        )
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            self.connection.revisions, self.connection.links, self.connection.audit = self.snapshot
        return False


class Connection:
    def __init__(self):
        self.revisions = {}
        self.links = {}
        self.audit = []

    def transaction(self):
        return Transaction(self)

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



@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"source_resource_id": "unknown:task-1"}, "INVALID_DEPENDENCY_SOURCE_RESOURCE_ID"),
        ({"target_resource_id": "unknown:task-1"}, "INVALID_DEPENDENCY_TARGET_RESOURCE_ID"),
        ({"dependency_type": "invented_relation"}, "INVALID_DEPENDENCY_TYPE"),
    ],
)
def test_unknown_dependency_contract_values_are_rejected(overrides, error):
    with pytest.raises(ValueError, match=error):
        link(**overrides).validate()


def test_rfi_resource_identifier_is_valid():
    link(
        target_resource_id="rfi:rfi-1",
        dependency_type="schedule_to_rfi",
    ).validate()


@pytest.mark.parametrize(
    "occurred_at",
    [
        datetime(2026, 9, 27, 15, 0),
        None,
        "2026-09-27T15:00:00Z",
    ],
)
def test_audit_timestamp_validation_happens_before_mutation(occurred_at):
    connection = Connection()
    store = PostgresDependencyGraphStore(connection)
    store.initialize()
    store.ensure_project("T-1", "P-1")

    with pytest.raises(ValueError, match="DEPENDENCY_AUDIT_TIMESTAMP_MUST_BE_TIMEZONE_AWARE"):
        store.persist(
            link(),
            expected_graph_revision=0,
            idempotency_key="timestamp-invalid",
            actor_id="u-1",
            occurred_at=occurred_at,
        )

    assert connection.revisions[("T-1", "P-1")] == 0
    assert connection.audit == []


def test_dependency_fingerprint_is_stable_for_metadata_key_order() -> None:
    first = link(metadata={"b": 2, "a": {"y": 1, "x": 0}})
    second = link(metadata={"a": {"x": 0, "y": 1}, "b": 2})

    assert dependency_fingerprint(first) == dependency_fingerprint(second)


def test_dependency_fingerprint_preserves_metadata_array_order() -> None:
    first = link(metadata={"items": ["alpha", "beta"]})
    second = link(metadata={"items": ["beta", "alpha"]})

    assert dependency_fingerprint(first) != dependency_fingerprint(second)


@pytest.mark.parametrize("metadata", [{"value": float("nan")}, {"value": float("inf")}, {"value": float("-inf")}])
def test_dependency_metadata_rejects_non_standard_json_numbers(metadata):
    connection = Connection()
    store = PostgresDependencyGraphStore(connection)
    store.initialize()
    store.ensure_project("T-1", "P-1")
    now = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="INVALID_DEPENDENCY_METADATA"):
        store.persist(
            link(metadata=metadata),
            expected_graph_revision=0,
            idempotency_key="non-standard-json-number",
            actor_id="u-1",
            occurred_at=now,
        )

    assert connection.revisions[("T-1", "P-1")] == 0
    assert connection.audit == []


def test_dependency_metadata_nested_structures_are_canonicalized_without_reordering_arrays() -> None:
    first = link(metadata={"outer": {"z": [{"b": 2, "a": 1}], "a": {"nested": True}}})
    second = link(metadata={"a": {"nested": True}, "outer": {"z": [{"a": 1, "b": 2}]}})
    assert dependency_fingerprint(first) == dependency_fingerprint(second)


def test_dependency_metadata_nested_array_order_changes_fingerprint() -> None:
    first = link(metadata={"outer": {"items": [{"id": 1}, {"id": 2}]}})
    second = link(metadata={"outer": {"items": [{"id": 2}, {"id": 1}]}})
    assert dependency_fingerprint(first) != dependency_fingerprint(second)


def test_persistence_rolls_back_revision_and_resource_on_audit_failure():
    connection = Connection()
    store = PostgresDependencyGraphStore(connection)
    store.initialize()
    store.ensure_project("T-1", "P-1")
    original_execute = connection.execute

    def failing_execute(sql, params=()):
        if sql.startswith("INSERT INTO project_dependency_audit"):
            raise RuntimeError("audit write failed")
        return original_execute(sql, params)

    connection.execute = failing_execute
    now = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)

    with pytest.raises(RuntimeError, match="audit write failed"):
        store.persist(link(), expected_graph_revision=0, idempotency_key="rollback", actor_id="u-1", occurred_at=now)

    assert connection.revisions[("T-1", "P-1")] == 0
    assert connection.links == {}
    assert connection.audit == []
