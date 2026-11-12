"""PostgreSQL twin coverage for activity step child records."""

import os
import uuid
from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_activity_step_repository import (
    P6ActivityStep,
    P6ActivityStepPersistenceError,
    PostgresP6ActivityStepRepository,
)

pytestmark = pytest.mark.postgres


def _connection():
    dsn = os.getenv("P6_TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("P6_TEST_POSTGRES_DSN is not configured")
    psycopg = pytest.importorskip("psycopg")
    return psycopg.connect(dsn)


def _step(scope: BackendScope, step_id: str, sequence: int) -> P6ActivityStep:
    return P6ActivityStep(
        scope=scope,
        step_id=step_id,
        activity_id="A130",
        sequence=sequence,
        description=f"Step {sequence}",
        weight=Decimal("25"),
        udf_values=(("crew", "C-01"),),
    )


def test_postgres_steps_round_trip_in_sequence_order():
    tenant = f"tenant-step-{uuid.uuid4()}"
    scope = BackendScope(tenant, "step-pg", 4)
    with _connection() as connection:
        repo = PostgresP6ActivityStepRepository(connection)
        repo.initialize()
        try:
            repo.upsert(_step(scope, "S2", 2))
            repo.upsert(_step(scope, "S1", 1))
            stored = repo.list(scope, "A130")
            assert [item.step_id for item in stored] == ["S1", "S2"]
            assert stored[0].weight == Decimal("25")
            assert stored[0].udf_values == (("crew", "C-01"),)
            assert repo.get(scope, "S1") == _step(scope, "S1", 1)
        finally:
            connection.rollback()


def test_postgres_steps_are_scoped_and_reject_stale_revisions():
    tenant = f"tenant-step-{uuid.uuid4()}"
    scope = BackendScope(tenant, "step-pg", 4)
    with _connection() as connection:
        repo = PostgresP6ActivityStepRepository(connection)
        repo.initialize()
        try:
            repo.upsert(_step(scope, "S1", 1))
            assert repo.list(BackendScope(tenant, "other", 4), "A130") == ()
            assert repo.get(BackendScope("other-tenant", "step-pg", 4), "S1") is None
            with pytest.raises(P6ActivityStepPersistenceError, match="REVISION_CONFLICT"):
                repo.list(BackendScope(tenant, "step-pg", 5), "A130")
        finally:
            connection.rollback()
