import sqlite3
import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_code_assignment_repository import (
    P6CodeAssignment,
    P6CodeAssignmentPersistenceError,
    SQLiteP6CodeAssignmentRepository,
)


def scope(revision: int = 1) -> BackendScope:
    return BackendScope("tenant-code-assignment", "project-code-assignment", revision)


def assignment(metadata: str | None = "source=xer") -> P6CodeAssignment:
    return P6CodeAssignment(scope(), "ACTIVITY_TYPE", "a", "ACTIVITY", "activity-1", metadata)


def test_round_trip_scope_isolation_and_deterministic_list() -> None:
    repo = SQLiteP6CodeAssignmentRepository(sqlite3.connect(":memory:"))
    first = assignment()
    assert repo.upsert(first) == first
    assert repo.upsert(first) == first
    assert repo.get(scope(), "ACTIVITY_TYPE", "a", "ACTIVITY", "activity-1") == first
    repo.upsert(P6CodeAssignment(scope(), "STATUS", "open", "ACTIVITY", "activity-1"))
    assert [x.code_id for x in repo.list(scope())] == ["ACTIVITY_TYPE", "STATUS"]
    assert repo.get(BackendScope("other", "project-code-assignment", 1), "ACTIVITY_TYPE", "a", "ACTIVITY", "activity-1") is None


def test_immutable_assignment_and_revision_isolation() -> None:
    repo = SQLiteP6CodeAssignmentRepository(sqlite3.connect(":memory:"))
    repo.upsert(assignment())
    with pytest.raises(P6CodeAssignmentPersistenceError, match="IMMUTABLE_ASSIGNMENT"):
        repo.upsert(assignment("changed"))
    assert repo.list(BackendScope("tenant-code-assignment", "project-code-assignment", 2)) == ()


def test_invalid_assignment_fails_closed() -> None:
    repo = SQLiteP6CodeAssignmentRepository(sqlite3.connect(":memory:"))
    bad = P6CodeAssignment(scope(), "", "a", "ACTIVITY", "activity-1")
    with pytest.raises(P6CodeAssignmentPersistenceError, match="INVALID_CODE_ID"):
        repo.upsert(bad)
