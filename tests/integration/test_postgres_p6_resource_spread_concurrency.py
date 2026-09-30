import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_resource_spread_repository import (
    P6ResourceSpreadBucket,
    PostgresP6ResourceSpreadRepository,
)

DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")


def _bucket() -> P6ResourceSpreadBucket:
    from decimal import Decimal
    return P6ResourceSpreadBucket(
        scope=BackendScope("tenant-live", "project-live", 1),
        spread_id="concurrent-spread",
        resource_id="resource-1",
        period_id="2026-10",
        period_start="2026-10-01",
        period_end="2026-10-31",
        spread_type="PLANNED",
        metric="UNITS",
        value=Decimal("12.50"),
        unit="hours",
    )


def test_postgres_resource_spread_identical_concurrent_upsert_is_race_safe():
    if not DSN:
        pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is required for live PostgreSQL tests")
    bucket = _bucket()
    params = (bucket.scope.tenant_id, bucket.scope.project_id, bucket.spread_id, bucket.period_id)
    cleanup_sql = (
        "DELETE FROM p6_resource_spread_bucket "
        "WHERE tenant_id=%s AND project_id=%s AND spread_id=%s AND period_id=%s"
    )
    barrier = Barrier(2)
    try:
        with psycopg.connect(DSN) as connection:
            repository = PostgresP6ResourceSpreadRepository(connection)
            repository.initialize()
            connection.commit()

        def run():
            with psycopg.connect(DSN) as connection:
                repository = PostgresP6ResourceSpreadRepository(connection)
                barrier.wait()
                return repository.upsert(bucket)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: run(), range(2)))

        assert results == [bucket, bucket]
        with psycopg.connect(DSN) as connection:
            row = connection.execute(
                "SELECT count(*) FROM p6_resource_spread_bucket "
                "WHERE tenant_id=%s AND project_id=%s AND spread_id=%s AND period_id=%s",
                params,
            ).fetchone()
            assert row == (1,)
    finally:
        with psycopg.connect(DSN) as connection:
            connection.execute(cleanup_sql, params)
            connection.commit()
