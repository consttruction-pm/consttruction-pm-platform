import sqlite3
import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_layout_definition_repository import (
    LayoutColumn, PersistedP6Layout, P6LayoutPersistenceError, SQLiteP6LayoutRepository,
)


def layout(revision=2, tenant="t1", project="p1"):
    return PersistedP6Layout(
        BackendScope(tenant, project, 7),
        "project",
        "activity",
        revision,
        (LayoutColumn("activity_id", True, 0, None, 120, "start", False, False),),
        {"future": {"enabled": True}},
    )


def test_layout_round_trip_and_scope_isolation():
    repo = SQLiteP6LayoutRepository(sqlite3.connect(":memory:"))
    value = layout()
    repo.upsert(value)
    assert repo.get(value.scope, "project", "activity") == value
    assert repo.get(BackendScope("other", "p1", 7), "project", "activity") is None


def test_layout_revision_is_immutable_and_project_revision_checked():
    repo = SQLiteP6LayoutRepository(sqlite3.connect(":memory:"))
    value = layout()
    repo.upsert(value)
    with pytest.raises(P6LayoutPersistenceError, match="IMMUTABLE_LAYOUT_REVISION"):
        repo.upsert(layout(revision=3))
    with pytest.raises(P6LayoutPersistenceError, match="REVISION_CONFLICT"):
        repo.get(BackendScope("t1", "p1", 8), "project", "activity")


def test_layout_rejects_non_normalized_columns():
    bad = layout()
    bad = PersistedP6Layout(bad.scope, bad.layout_scope, bad.view_id, bad.revision,
        (LayoutColumn("activity_id", True, 4, None, 120, "start", False, False),), bad.metadata)
    with pytest.raises(P6LayoutPersistenceError, match="NON_NORMALIZED_LAYOUT"):
        bad.validate()


class _FakePostgresConnection:
    def __init__(self, row):
        self.row = row

    def execute(self, query, params):
        class Result:
            def __init__(self, row):
                self.row = row

            def fetchone(self):
                return self.row

        return Result(self.row)


def test_postgres_layout_get_decodes_without_project_revision_as_layout_revision():
    from construction_pm.p6_layout_definition_repository import PostgresP6LayoutRepository

    value = layout()
    columns_json = '[{"alignment":"start","field_id":"activity_id","frozen":false,"label":null,"order":0,"pinned":false,"visible":true,"width":120}]'
    metadata_json = '{"future":{"enabled":true}}'
    connection = _FakePostgresConnection(
        (value.scope.project_revision, value.revision, columns_json, metadata_json)
    )

    loaded = PostgresP6LayoutRepository(connection).get(
        value.scope, value.layout_scope, value.view_id
    )

    assert loaded == value
