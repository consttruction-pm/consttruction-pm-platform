import sqlite3

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_report_profile_repository import (
    P6ReportProfileFieldMapping,
    P6ReportProfilePersistenceError,
    SQLiteP6ReportProfileRepository,
)


def scope(revision=7):
    return BackendScope("tenant-a", "project-a", revision)


def mapping(s, field_id="activity_id", ordinal=0, **kwargs):
    return P6ReportProfileFieldMapping(
        s, "profile-1", "Activity Report", "ACTIVITY", field_id, ordinal, **kwargs
    )


def test_round_trip_and_deterministic_order():
    repo = SQLiteP6ReportProfileRepository(sqlite3.connect(":memory:"))
    repo.upsert(mapping(scope(), "finish", 2))
    repo.upsert(mapping(scope(), "activity_id", 0, metadata={"source": "P6"}))
    repo.upsert(mapping(scope(), "status", 1, exportable=False))
    rows = repo.list(scope(), "profile-1")
    assert [r.field_id for r in rows] == ["activity_id", "status", "finish"]
    assert rows[0].metadata == {"source": "P6"}
    assert rows[1].exportable is False


def test_scope_isolation_and_revision_conflict():
    repo = SQLiteP6ReportProfileRepository(sqlite3.connect(":memory:"))
    repo.upsert(mapping(scope(7)))
    assert repo.get(BackendScope("tenant-b", "project-a", 7), "profile-1", "activity_id") is None
    with pytest.raises(P6ReportProfilePersistenceError, match="REVISION_CONFLICT"):
        repo.get(scope(8), "profile-1", "activity_id")


def test_identical_replay_is_idempotent_but_changed_definition_is_immutable():
    repo = SQLiteP6ReportProfileRepository(sqlite3.connect(":memory:"))
    item = mapping(scope(), metadata={"source": "P6"})
    assert repo.upsert(item) == item
    assert repo.upsert(item) == item
    with pytest.raises(P6ReportProfilePersistenceError, match="IMMUTABLE_REPORT_PROFILE_MAPPING"):
        repo.upsert(mapping(scope(), metadata={"source": "OTHER"}))


def test_invalid_values_fail_closed():
    repo = SQLiteP6ReportProfileRepository(sqlite3.connect(":memory:"))
    with pytest.raises(P6ReportProfilePersistenceError, match="INVALID_ORDINAL"):
        repo.upsert(mapping(scope(), ordinal=-1))
    with pytest.raises(P6ReportProfilePersistenceError, match="INVALID_EXPORTABLE"):
        repo.upsert(mapping(scope(), exportable="yes"))
