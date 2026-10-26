import json
import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_layout_definition_repository import (
    LayoutColumn, PersistedP6Layout, P6LayoutPersistenceError, PostgresP6LayoutRepository, SQLiteP6LayoutRepository,
    layout_column_from_mapping,
)


def layout(revision=2, tenant="t1", project="p1", width=120):
    return PersistedP6Layout(
        BackendScope(tenant, project, 7),
        "project",
        "activity",
        revision,
        (LayoutColumn("activity_id", True, 0, None, width, "start", False, False),),
        {"future": {"enabled": True}},
    )


def test_layout_round_trip_and_scope_isolation():
    repo = SQLiteP6LayoutRepository(sqlite3.connect(":memory:"))
    value = layout()
    repo.upsert(value)
    assert repo.get(value.scope, "project", "activity") == value
    assert repo.get(BackendScope("other", "p1", 7), "project", "activity") is None


def test_layout_edits_append_immutable_revisions_and_survive_reload():
    connection = sqlite3.connect(":memory:")
    repo = SQLiteP6LayoutRepository(connection)
    repo.upsert(layout(revision=2))
    repo.upsert(layout(revision=3, width=180))
    assert repo.get(BackendScope("t1", "p1", 7), "project", "activity") == layout(revision=3, width=180)

    # Reopening the repository against the same database proves durable
    # persistence rather than in-memory presentation state.
    reopened = SQLiteP6LayoutRepository(connection)
    assert reopened.get(BackendScope("t1", "p1", 7), "project", "activity") == layout(revision=3, width=180)


def test_layout_revision_history_is_newest_first_and_scoped():
    repo = SQLiteP6LayoutRepository(sqlite3.connect(":memory:"))
    repo.upsert(layout(revision=2))
    repo.upsert(layout(revision=3, width=180))
    repo.upsert(layout(revision=4, width=240))

    revisions = repo.list_revisions(BackendScope("t1", "p1", 7), "project", "activity")
    assert [item.revision for item in revisions] == [4, 3, 2]
    assert [item.columns[0].width for item in revisions] == [240, 180, 120]
    assert revisions[0].metadata == {"future": {"enabled": True}}

    assert repo.list_revisions(BackendScope("t1", "p1", 7), "project", "activity", limit=2)[0].revision == 4
    assert len(repo.list_revisions(BackendScope("t1", "p1", 7), "project", "activity", limit=2)) == 2
    assert repo.list_revisions(BackendScope("t1", "p1", 8), "project", "activity") == ()
    assert repo.list_revisions(BackendScope("t1", "p1", 7), "user", "activity") == ()

    with pytest.raises(P6LayoutPersistenceError, match="INVALID_LAYOUT_HISTORY_LIMIT"):
        repo.list_revisions(BackendScope("t1", "p1", 7), "project", "activity", limit=0)
    with pytest.raises(P6LayoutPersistenceError, match="INVALID_LAYOUT_HISTORY_LIMIT"):
        repo.list_revisions(BackendScope("t1", "p1", 7), "project", "activity", limit=101)


def test_layout_save_is_committed_for_a_standalone_repository(tmp_path):
    database = tmp_path / "layout.sqlite3"
    writer = sqlite3.connect(database)
    SQLiteP6LayoutRepository(writer).upsert(layout(revision=1))
    writer.close()

    reader = sqlite3.connect(database)
    try:
        assert SQLiteP6LayoutRepository(reader).get(
            BackendScope("t1", "p1", 7), "project", "activity"
        ) == layout(revision=1)
    finally:
        reader.close()


def test_layout_revision_is_immutable_and_optimistic():
    repo = SQLiteP6LayoutRepository(sqlite3.connect(":memory:"))
    repo.upsert(layout(revision=2))
    repo.upsert(layout(revision=3, width=180))

    # A writer cannot publish different content under an existing revision.
    with pytest.raises(P6LayoutPersistenceError, match="IMMUTABLE_LAYOUT_REVISION"):
        repo.upsert(layout(revision=3, width=240))
    # A client behind the head is stale, not an attempt to rewrite history.
    with pytest.raises(P6LayoutPersistenceError, match="REVISION_CONFLICT"):
        repo.upsert(layout(revision=2, width=240))
    # Gaps are rejected so every persisted revision has a linear history.
    with pytest.raises(P6LayoutPersistenceError, match="REVISION_CONFLICT"):
        repo.upsert(layout(revision=5))
    with pytest.raises(P6LayoutPersistenceError, match="REVISION_CONFLICT"):
        repo.get(BackendScope("t1", "p1", 8), "project", "activity")

    # Rejected writes never rewrite or extend the published history.
    assert repo.get(BackendScope("t1", "p1", 7), "project", "activity") == layout(revision=3, width=180)
    assert [item.revision for item in repo.list_revisions(
        BackendScope("t1", "p1", 7), "project", "activity"
    )] == [3, 2]


def test_layout_identical_retry_is_idempotent_and_does_not_append():
    repo = SQLiteP6LayoutRepository(sqlite3.connect(":memory:"))
    repo.upsert(layout(revision=2))
    repo.upsert(layout(revision=3, width=180))

    # Retrying the exact same write must succeed without a second revision.
    assert repo.upsert(layout(revision=3, width=180)) == layout(revision=3, width=180)
    revisions = repo.list_revisions(BackendScope("t1", "p1", 7), "project", "activity")
    assert [item.revision for item in revisions] == [3, 2]
    assert [item.columns[0].width for item in revisions] == [180, 120]

    # The same content under a different revision is not that retry: the
    # client's base disagrees with the head and must reload.
    with pytest.raises(P6LayoutPersistenceError, match="REVISION_CONFLICT"):
        repo.upsert(layout(revision=2, width=180))

    # The legitimate next revision is appended even when it happens to repeat
    # the head's content, for example when restoring a revision as a new head.
    repo.upsert(layout(revision=4, width=180))
    assert [item.revision for item in repo.list_revisions(
        BackendScope("t1", "p1", 7), "project", "activity"
    )] == [4, 3, 2]


def test_layout_rejects_non_normalized_columns():
    bad = layout()
    bad = PersistedP6Layout(bad.scope, bad.layout_scope, bad.view_id, bad.revision,
        (LayoutColumn("activity_id", True, 4, None, 120, "start", False, False),), bad.metadata)
    with pytest.raises(P6LayoutPersistenceError, match="NON_NORMALIZED_LAYOUT"):
        bad.validate()


def test_layout_column_mapping_allows_optional_label():
    column = layout_column_from_mapping({
        "field_id": "activity.type",
        "visible": True,
        "order": 10,
        "width": 130,
        "alignment": "start",
        "pinned": False,
        "frozen": False,
    })
    assert column.label is None
    assert column.field_id == "activity.type"


def test_layout_column_mapping_rejects_malformed_columns():
    with pytest.raises(P6LayoutPersistenceError, match="INVALID_LAYOUT_COLUMNS"):
        layout_column_from_mapping(["not", "a", "mapping"])
    with pytest.raises(P6LayoutPersistenceError, match="INVALID_LAYOUT_COLUMNS"):
        layout_column_from_mapping({"field_id": "activity.id"})


def test_layout_stored_column_without_label_is_readable():
    column = {
        "field_id": "activity.type",
        "visible": True,
        "order": 0,
        "width": 130,
        "alignment": "start",
        "pinned": False,
        "frozen": False,
    }
    repo = SQLiteP6LayoutRepository(sqlite3.connect(":memory:"))
    value = PersistedP6Layout(
        BackendScope("t1", "p1", 7), "project", "activity", 2,
        (layout_column_from_mapping(column),), {},
    )
    repo.upsert(value)
    read_back = repo.get(value.scope, "project", "activity")
    assert read_back == value
    assert read_back.columns[0].label is None


def test_layout_migrates_legacy_single_revision_table_without_deleting_it():
    connection = sqlite3.connect(":memory:")
    connection.execute(
        "CREATE TABLE p6_layout_definitions ("
        "tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, project_revision INTEGER NOT NULL, "
        "layout_scope TEXT NOT NULL, view_id TEXT NOT NULL, revision INTEGER NOT NULL, "
        "columns_json TEXT NOT NULL, metadata_json TEXT NOT NULL, "
        "PRIMARY KEY (tenant_id, project_id, layout_scope, view_id))"
    )
    legacy = layout(revision=4)
    connection.execute(
        "INSERT INTO p6_layout_definitions VALUES (?,?,?,?,?,?,?,?)",
        (
            legacy.scope.tenant_id,
            legacy.scope.project_id,
            legacy.scope.project_revision,
            legacy.layout_scope,
            legacy.view_id,
            legacy.revision,
            json.dumps([c.__dict__ for c in legacy.columns], sort_keys=True, separators=(",", ":")),
            json.dumps(dict(legacy.metadata), sort_keys=True, separators=(",", ":")),
        ),
    )
    repo = SQLiteP6LayoutRepository(connection)
    assert repo.get(legacy.scope, "project", "activity") == legacy
    assert connection.execute("SELECT COUNT(*) FROM p6_layout_definitions").fetchone()[0] == 1


class _FakePostgresConnection:
    def __init__(self, value):
        self.value = value

    def execute(self, sql, params):
        return self

    def fetchone(self):
        value = self.value
        columns_json = '[{"alignment":"start","field_id":"activity_id","frozen":false,"label":null,"order":0,"pinned":false,"visible":true,"width":120}]'
        return (value.revision, columns_json, '{"future":{"enabled":true}}')


def test_postgres_get_decodes_latest_layout_revision():
    value = layout()
    repo = PostgresP6LayoutRepository(_FakePostgresConnection(value))
    assert repo.get(value.scope, "project", "activity") == value
