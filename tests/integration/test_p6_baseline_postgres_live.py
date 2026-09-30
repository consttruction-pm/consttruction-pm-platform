from __future__ import annotations

import os

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_baseline_repository import (
    P6Baseline,
    P6BaselinePersistenceError,
    PostgresP6BaselineRepository,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)


def connect():
    import psycopg

    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


def baseline(scope: BackendScope, baseline_id: str = "b-1") -> P6Baseline:
    return P6Baseline(
        scope=scope,
        baseline_id=baseline_id,
        name="Approved Baseline",
        baseline_type="PRIMARY",
        source_revision=3,
        created_at="2026-09-28T10:00:00Z",
        notes="immutable metadata",
    )


def test_postgres_baseline_round_trip_list_isolation_and_revision():
    with connect() as conn:
        repo = PostgresP6BaselineRepository(conn)
        repo.initialize()
        scope = BackendScope("tenant-baseline-pg", "project-baseline-pg", 7)
        first = baseline(scope, "b-1")
        second = baseline(scope, "b-2")

        assert repo.upsert(first) == first
        assert repo.upsert(second) == second
        assert repo.get(scope, "b-1") == first
        assert [item.baseline_id for item in repo.list(scope)] == ["b-1", "b-2"]
        assert repo.get(
            BackendScope("other-tenant", scope.project_id, scope.project_revision),
            "b-1",
        ) is None
        with pytest.raises(P6BaselinePersistenceError, match="REVISION_CONFLICT"):
            repo.get(
                BackendScope(scope.tenant_id, scope.project_id, scope.project_revision + 1),
                "b-1",
            )


def test_postgres_baseline_is_immutable_and_identical_replay_is_idempotent():
    with connect() as conn:
        repo = PostgresP6BaselineRepository(conn)
        repo.initialize()
        scope = BackendScope("tenant-baseline-rb", "project-baseline-rb", 4)
        original = baseline(scope)
        assert repo.upsert(original) == original
        conn.commit()
        assert repo.upsert(original) == original

        changed = P6Baseline(
            scope=scope,
            baseline_id=original.baseline_id,
            name="Changed",
            baseline_type=original.baseline_type,
            source_revision=original.source_revision,
            created_at=original.created_at,
            notes=original.notes,
        )
        with pytest.raises(P6BaselinePersistenceError, match="IMMUTABLE_BASELINE"):
            repo.upsert(changed)
        conn.rollback()

        assert repo.get(scope, original.baseline_id) == original


def test_postgres_baseline_rollback_leaves_no_row():
    with connect() as conn:
        repo = PostgresP6BaselineRepository(conn)
        repo.initialize()
        scope = BackendScope("tenant-baseline-rollback", "project-baseline-rollback", 2)
        repo.upsert(baseline(scope))
        conn.rollback()
        assert repo.get(scope, "b-1") is None
