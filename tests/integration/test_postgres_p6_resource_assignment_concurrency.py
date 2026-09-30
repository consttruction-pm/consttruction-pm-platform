import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignment,
    PostgresP6ResourceAssignmentRepository,
)

DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")


def _assignment() -> P6ResourceAssignment:
    from decimal import Decimal

    return P6ResourceAssignment(
        scope=BackendScope("tenant-live", "project-live", 1),
        assignment_id="concurrent-assignment",
        activity_id="activity-1",
        resource_id="resource-1",
        units=Decimal("1.5"),
        planned_cost=Decimal("100.00"),
        unit="h",
        currency="USD",
    )


def test_postgres_resource_assignment_identical_concurrent_upsert_is_race_safe():
    if not DSN:
        pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is required for live PostgreSQL tests")

    assignment = _assignment()
    params = (
        assignment.scope.tenant_id,
        assignment.scope.project_id,
        assignment.assignment_id,
    )
    cleanup_sql = (
        "DELETE FROM p6_resource_assignment "
        "WHERE tenant_id=%s AND project_id=%s AND assignment_id=%s"
    )
    barrier = Barrier(2)

    try:
        with psycopg.connect(DSN) as connection:
            repository = PostgresP6ResourceAssignmentRepository(connection)
            repository.initialize()
            connection.commit()

        def run():
            with psycopg.connect(DSN) as connection:
                repository = PostgresP6ResourceAssignmentRepository(connection)
                barrier.wait()
                return repository.upsert(assignment)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: run(), range(2)))

        assert results == [assignment, assignment]

        with psycopg.connect(DSN) as connection:
            row = connection.execute(
                "SELECT count(*) FROM p6_resource_assignment "
                "WHERE tenant_id=%s AND project_id=%s AND assignment_id=%s",
                params,
            ).fetchone()
            assert row == (1,)
    finally:
        with psycopg.connect(DSN) as connection:
            connection.execute(cleanup_sql, params)
            connection.commit()
