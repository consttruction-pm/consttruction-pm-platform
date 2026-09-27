import pytest

from construction_pm.field_operations import (
    FieldOperation,
    FieldOperationIdempotencyReuse,
    FieldOperationRevisionConflict,
    FieldOperationType,
    PostgresFieldOperationStore,
)


class Cursor:
    def __init__(self, row=None):
        self.row = row

    def fetchone(self):
        return self.row


class Tx:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class Connection:
    def __init__(self):
        self.revision = {}
        self.rows = {}

    def transaction(self):
        return Tx()

    def execute(self, sql, params=()):
        if sql.startswith("CREATE TABLE"):
            return Cursor()
        if sql.startswith("INSERT INTO project_field_operation_revisions"):
            self.revision.setdefault((params[0], params[1]), 0)
            return Cursor()
        if sql.startswith("SELECT revision FROM project_field_operation_revisions"):
            return Cursor((self.revision.get((params[0], params[1])),))
        if sql.startswith("SELECT fingerprint, operation_json"):
            return Cursor(self.rows.get(("idem", *params)))
        if sql.startswith("UPDATE project_field_operation_revisions"):
            self.revision[(params[1], params[2])] = params[0]
            return Cursor()
        if sql.startswith("INSERT INTO project_field_operations"):
            key = (params[0], params[1], params[2])
            self.rows[("row", *key)] = (params[6], params[5])
            self.rows[("idem", params[0], params[1], params[3])] = (
                params[4], params[6], params[5]
            )
            return Cursor()
        if sql.startswith("SELECT operation_json, project_revision"):
            return Cursor(self.rows.get(("row", *params)))
        if sql.startswith("INSERT INTO project_field_operation_audit"):
            return Cursor()
        raise AssertionError(f"unexpected SQL: {sql}")


def operation(**overrides):
    values = dict(
        tenant_id="T-1",
        project_id="P-1",
        operation_id="op-1",
        revision=0,
        operation_type=FieldOperationType.DAILY_LOG,
        occurred_at="2026-09-27T08:00:00+00:00",
        actor_id="u-1",
        location_ref="site-zone-a",
        payload={"note": "site update"},
    )
    values.update(overrides)
    return FieldOperation(**values)


def store_for(*projects):
    connection = Connection()
    store = PostgresFieldOperationStore(connection)
    store.initialize()
    for tenant_id, project_id in projects:
        store.ensure_project(tenant_id, project_id)
    return store


def test_transactional_persist_and_replay():
    store = store_for(("T-1", "P-1"))

    first = store.persist(operation(), expected_project_revision=0, idempotency_key="k1")
    replay = store.persist(operation(), expected_project_revision=0, idempotency_key="k1")

    assert first.project_revision == 1
    assert replay == first
    assert store.get("T-1", "P-1", "op-1") == first


def test_stale_revision_and_key_reuse_are_rejected():
    store = store_for(("T-1", "P-1"))
    store.persist(operation(), expected_project_revision=0, idempotency_key="k1")

    with pytest.raises(FieldOperationRevisionConflict):
        store.persist(
            operation(operation_id="op-2"),
            expected_project_revision=0,
            idempotency_key="k2",
        )

    with pytest.raises(FieldOperationIdempotencyReuse):
        store.persist(
            operation(payload={"note": "different"}),
            expected_project_revision=1,
            idempotency_key="k1",
        )


def test_tenant_project_isolation():
    store = store_for(("T-1", "P-1"), ("T-2", "P-1"))

    first = store.persist(operation(), expected_project_revision=0, idempotency_key="k1")
    second = store.persist(
        operation(tenant_id="T-2"),
        expected_project_revision=0,
        idempotency_key="k1",
    )

    assert first.project_revision == second.project_revision == 1
    assert store.get("T-1", "P-1", "op-1") == first
    assert store.get("T-2", "P-1", "op-1") == second
