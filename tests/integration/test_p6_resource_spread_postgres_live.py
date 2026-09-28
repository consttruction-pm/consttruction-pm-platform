import os
from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_resource_spread_repository import (
    P6ResourceSpreadBucket,
    P6ResourceSpreadPersistenceError,
    PostgresP6ResourceSpreadRepository,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)


def connect():
    import psycopg
    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


def make_bucket(scope, value="12.50"):
    return P6ResourceSpreadBucket(
        scope=scope, spread_id="spread-1", resource_id="resource-1",
        period_id="2026-10", period_start="2026-10-01", period_end="2026-10-31",
        spread_type="PLANNED", metric="UNITS", value=Decimal(value), unit="hours",
    )


def test_postgres_round_trip_scope_and_revision():
    with connect() as conn:
        repo = PostgresP6ResourceSpreadRepository(conn)
        repo.initialize()
        scope = BackendScope("tenant-pg", "project-pg", 1)
        record = make_bucket(scope)
        assert repo.upsert(record) == record
        assert repo.get(scope, "spread-1", "2026-10") == record
        assert repo.get(BackendScope("tenant-other", "project-pg", 1), "spread-1", "2026-10") is None
        with pytest.raises(P6ResourceSpreadPersistenceError, match="REVISION_CONFLICT"):
            repo.get(BackendScope("tenant-pg", "project-pg", 2), "spread-1", "2026-10")


def test_postgres_rollback():
    with connect() as conn:
        repo = PostgresP6ResourceSpreadRepository(conn)
        repo.initialize()
        scope = BackendScope("tenant-pg-rb", "project-pg-rb", 1)
        record = make_bucket(scope)
        try:
            repo.upsert(record)
            raise RuntimeError("force rollback")
        except RuntimeError:
            conn.rollback()
        assert repo.get(scope, "spread-1", "2026-10") is None
