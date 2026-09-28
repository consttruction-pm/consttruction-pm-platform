import os

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_code_assignment_repository import (
    P6CodeAssignment,
    P6CodeAssignmentPersistenceError,
    PostgresP6CodeAssignmentRepository,
)


pytestmark = pytest.mark.postgres


def _connection():
    dsn = os.getenv("P6_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("P6_TEST_POSTGRES_DSN is not configured")
    psycopg = pytest.importorskip("psycopg")
    return psycopg.connect(dsn)


def _scope(revision: int = 1) -> BackendScope:
    return BackendScope("tenant-pg", "project-pg", revision)


def _assignment(metadata: str | None = "source=xer") -> P6CodeAssignment:
    return P6CodeAssignment(
        _scope(), "ACTIVITY_TYPE", "a", "ACTIVITY", "activity-1", metadata
    )


def test_postgres_round_trip_scope_isolation_and_idempotent_replay():
    with _connection() as connection:
        repo = PostgresP6CodeAssignmentRepository(connection)
        repo.initialize()

        item = _assignment()
        assert repo.upsert(item) == item
        assert repo.upsert(item) == item
        assert repo.get(_scope(), "ACTIVITY_TYPE", "a", "ACTIVITY", "activity-1") == item
        assert repo.get(
            BackendScope("other-tenant", "project-pg", 1),
            "ACTIVITY_TYPE",
            "a",
            "ACTIVITY",
            "activity-1",
        ) is None
        connection.rollback()


def test_postgres_immutable_metadata_and_revision_isolation():
    with _connection() as connection:
        repo = PostgresP6CodeAssignmentRepository(connection)
        repo.initialize()
        repo.upsert(_assignment())

        with pytest.raises(P6CodeAssignmentPersistenceError, match="IMMUTABLE_ASSIGNMENT"):
            repo.upsert(_assignment("changed"))
        assert repo.list(BackendScope("tenant-pg", "project-pg", 2)) == ()
        connection.rollback()


def test_postgres_atomic_replay_from_independent_connections():
    first = _connection()
    second = _connection()
    try:
        first_repo = PostgresP6CodeAssignmentRepository(first)
        second_repo = PostgresP6CodeAssignmentRepository(second)
        first_repo.initialize()
        first.commit()

        item = _assignment("concurrent")
        assert first_repo.upsert(item) == item
        first.commit()

        assert second_repo.upsert(item) == item
        second.rollback()
    finally:
        first.close()
        second.close()
