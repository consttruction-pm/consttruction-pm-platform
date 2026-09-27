from datetime import datetime, timezone

import pytest

from construction_pm.field_resource_persistence import (
    FieldResource,
    FieldResourceIdempotencyReuse,
    FieldResourceRevisionConflict,
    PostgresFieldResourceStore,
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
        self.revisions = {}
        self.resources = {}
        self.audit = []

    def execute(self, sql, params=()):
        if sql.startswith("INSERT INTO project_field_revisions"):
            self.revisions.setdefault((params[0], params[1]), 0)
            return Cursor()
        if sql.startswith("SELECT revision FROM project_field_revisions"):
            return Cursor((self.revisions.get((params[0], params[1])),))
        if sql.startswith("UPDATE project_field_revisions"):
            key = (params[1], params[2])
            if self.revisions.get(key) == params[3]:
                self.revisions[key] = params[0]
            return Cursor()
        if sql.startswith("SELECT fingerprint, resource_json"):
            return Cursor(self.resources.get(("idem", *params)))
        if sql.startswith("SELECT resource_json, project_revision"):
            return Cursor(self.resources.get(("resource", *params)))
        if sql.startswith("INSERT INTO project_field_resources"):
            key = (params[0], params[1], params[2])
            self.resources[("resource", *key)] = (params[6], params[5])
            self.resources[("idem", params[0], params[1], params[3])] = (
                params[4], params[6], params[5]
            )
            return Cursor()
        if sql.startswith("INSERT INTO project_field_audit"):
            self.audit.append(params)
            return Cursor()
        if sql.startswith("SELECT project_revision, event_type"):
            rows = [
                (a[3], a[4], a[5], a[6])
                for a in self.audit
                if a[:3] == params
            ]
            return Cursor(rows=rows)
        return Cursor()


def resource(**overrides):
    values = dict(
        resource_id="field-1",
        tenant_id="T-1",
        project_id="P-1",
        resource_type="daily_log",
        revision=1,
        payload={"work_summary": "concrete pour"},
    )
    values.update(overrides)
    return FieldResource(**values)


def test_persist_replay_readback_and_audit():
    connection = Connection()
    store = PostgresFieldResourceStore(connection)
    store.initialize()
    store.ensure_project("T-1", "P-1")
    now = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)

    created = store.persist(
        resource(),
        expected_project_revision=0,
        idempotency_key="k-1",
        actor_id="u-1",
        occurred_at=now,
    )
    replay = store.persist(
        resource(),
        expected_project_revision=0,
        idempotency_key="k-1",
        actor_id="u-1",
        occurred_at=now,
    )

    assert created.project_revision == 1
    assert replay == created
    assert store.get("T-1", "P-1", "field-1") == created
    assert store.history("T-1", "P-1", "field-1")[0][1] == "created"


def test_stale_revision_and_idempotency_reuse_are_rejected():
    connection = Connection()
    store = PostgresFieldResourceStore(connection)
    store.initialize()
    store.ensure_project("T-1", "P-1")
    now = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)
    store.persist(
        resource(),
        expected_project_revision=0,
        idempotency_key="k-1",
        actor_id="u-1",
        occurred_at=now,
    )

    with pytest.raises(FieldResourceRevisionConflict):
        store.persist(
            resource(resource_id="field-2"),
            expected_project_revision=0,
            idempotency_key="k-2",
            actor_id="u-1",
            occurred_at=now,
        )

    with pytest.raises(FieldResourceIdempotencyReuse):
        store.persist(
            resource(payload={"work_summary": "different"}),
            expected_project_revision=1,
            idempotency_key="k-1",
            actor_id="u-1",
            occurred_at=now,
        )


@pytest.mark.parametrize(
    "resource_type",
    [
        "daily_log",
        "issue",
        "observation",
        "inspection",
        "quality_record",
        "safety_record",
        "punch_item",
        "field_photo",
        "timecard",
        "equipment_status",
    ],
)
def test_all_contract_resource_types_are_accepted(resource_type):
    resource(resource_type=resource_type).validate()


def test_invalid_resource_type_is_rejected():
    with pytest.raises(ValueError, match="INVALID_FIELD_RESOURCE_TYPE"):
        resource(resource_type="unknown").validate()
