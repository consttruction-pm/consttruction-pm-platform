from __future__ import annotations

import os
import uuid
from decimal import Decimal

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_baseline_activity_repository import (
    P6BaselineActivity,
    P6BaselineActivityPersistenceError,
    PostgresP6BaselineActivityRepository,
)
from construction_pm.p6_baseline_repository import (
    P6Baseline,
    PostgresP6BaselineRepository,
)


@pytest.fixture(scope="module")
def postgres_dsn() -> str:
    dsn = os.getenv("P6_TEST_POSTGRES_DSN") or os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
    if not dsn:
        pytest.skip("PostgreSQL DSN is not configured")
    return dsn


@pytest.fixture()
def connection(postgres_dsn):
    conn = psycopg.connect(postgres_dsn)
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


def _scope(revision: int = 7) -> BackendScope:
    suffix = uuid.uuid4().hex
    return BackendScope(f"tenant-{suffix}", f"project-{suffix}", revision)


def _baseline(scope: BackendScope) -> P6Baseline:
    return P6Baseline(
        scope,
        "baseline-1",
        "Approved Baseline",
        "PRIMARY",
        scope.project_revision,
        "2026-11-02T10:00:00Z",
        "immutable metadata",
    )


def _activity(
    scope: BackendScope,
    activity_id: str = "A-1",
    budget: str = "1000.00",
    wbs_id: str | None = "W-1",
) -> P6BaselineActivity:
    return P6BaselineActivity(
        scope,
        "baseline-1",
        activity_id,
        "2026-11-02",
        "2026-11-06",
        Decimal(budget),
        "USD",
        wbs_id,
        "ACTIVITY_PERCENT_COMPLETE",
    )


def _repositories(connection):
    baselines = PostgresP6BaselineRepository(connection)
    baselines.initialize()
    activities = PostgresP6BaselineActivityRepository(connection)
    activities.initialize()
    return baselines, activities


def test_postgres_baseline_activities_round_trip_and_are_immutable(connection):
    baselines, repository = _repositories(connection)
    scope = _scope()
    with connection.transaction():
        baselines.upsert(_baseline(scope))
        first = repository.save_many((_activity(scope, "B", "500"), _activity(scope, "A")))
        assert [item.activity_id for item in first] == ["A", "B"]
        assert repository.save_many((_activity(scope, "A"), _activity(scope, "B", "500"))) == first

    stored = repository.list(scope, "baseline-1")
    assert stored == first

    with pytest.raises(
        P6BaselineActivityPersistenceError, match="IMMUTABLE_BASELINE_ACTIVITIES"
    ):
        repository.save_many((_activity(scope, "A", "1200"),))


def test_postgres_baseline_activity_scope_and_revision_are_enforced(connection):
    baselines, repository = _repositories(connection)
    scope = _scope()
    with connection.transaction():
        baselines.upsert(_baseline(scope))
        repository.save_many((_activity(scope),))

    assert repository.list(BackendScope("tenant-other", scope.project_id, 7), "baseline-1") == ()
    assert (
        repository.list(BackendScope(scope.tenant_id, "project-other", 7), "baseline-1")
        == ()
    )
    with pytest.raises(P6BaselineActivityPersistenceError, match="REVISION_CONFLICT"):
        repository.list(BackendScope(scope.tenant_id, scope.project_id, 8), "baseline-1")


def test_postgres_baseline_activity_requires_the_parent_baseline(connection):
    _, repository = _repositories(connection)
    scope = _scope()

    with pytest.raises(
        P6BaselineActivityPersistenceError,
        match="BASELINE_ACTIVITY_PARENT_BASELINE_REQUIRED",
    ):
        repository.save_many((_activity(scope),))
