import os
from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_activity_step_repository import P6ActivityStep, PostgresP6ActivityStepRepository


pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)


def _connect():
    import psycopg
    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


def test_postgres_activity_step_round_trip_and_scope_isolation():
    with _connect() as connection:
        repo = PostgresP6ActivityStepRepository(connection)
        repo.initialize()
        connection.commit()
        scope = BackendScope("tenant-step", "project-step", 7)
        value = P6ActivityStep(
            scope=scope, step_id="STEP-1", activity_id="ACT-1", sequence=1,
            description="Inspect formwork", weight=Decimal("10.25"),
            start_date="2026-09-01", finish_date="2026-09-02",
            udf_values=(("crew", "C-01"),),
        )
        repo.upsert(value)
        connection.commit()
        assert repo.get(scope, "STEP-1") == value
        assert repo.get(BackendScope("tenant-other", "project-step", 7), "STEP-1") is None


def test_postgres_activity_step_revision_conflict_and_rollback():
    with _connect() as connection:
        repo = PostgresP6ActivityStepRepository(connection)
        repo.initialize()
        connection.commit()
        scope = BackendScope("tenant-step-rollback", "project-step", 3)
        value = P6ActivityStep(scope, "STEP-1", "ACT-1", 1, "Inspect")
        repo.upsert(value)
        connection.commit()
        with pytest.raises(Exception):
            with connection.transaction():
                repo.upsert(P6ActivityStep(scope, "STEP-1", "ACT-1", 2, "Changed"))
        assert repo.get(scope, "STEP-1") == value
        with pytest.raises(Exception, match="REVISION_CONFLICT"):
            repo.get(BackendScope("tenant-step-rollback", "project-step", 4), "STEP-1")
