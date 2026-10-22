import os
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_resource_rate_repository import (
    P6ResourceRatePersistenceError,
    PostgresP6ResourceRateRepository,
)
from construction_pm.scheduling.resource_leveling_input import ResourceCapacityRate

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)


def connect():
    import psycopg
    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


def profile(max_units="8"):
    return ResourceCapacityRate(
        resource_id="R-RATE-PG",
        effective_from=datetime(2026, 10, 19, tzinfo=timezone.utc),
        max_units_per_time=Decimal(max_units),
        time_period_unit="day",
        hours_per_time_period=Decimal("8"),
        unit_of_measure="h",
        time_period_source="calendar",
        record_revision=1,
    )


def test_postgres_resource_capacity_rate_round_trip_scope_and_immutability():
    scope = BackendScope("tenant-resource-rate-pg", "project-resource-rate-pg", 1)
    with connect() as connection:
        repository = PostgresP6ResourceRateRepository(connection)
        repository.initialize()
        connection.execute(
            "DELETE FROM p6_resource_rate_capacity WHERE tenant_id=%s AND project_id=%s",
            (scope.tenant_id, scope.project_id),
        )
        connection.commit()

        item = profile()
        assert repository.save(scope, item) == item
        connection.commit()
        assert repository.get(scope, item.resource_id, item.effective_from) == item
        assert repository.list(scope) == (item,)
        assert repository.list(BackendScope("other-tenant", scope.project_id, 1)) == ()

        with pytest.raises(P6ResourceRatePersistenceError, match="IMMUTABLE_RESOURCE_RATE_CONFLICT"):
            repository.save(scope, profile(max_units="10"))

        connection.execute(
            "DELETE FROM p6_resource_rate_capacity WHERE tenant_id=%s AND project_id=%s",
            (scope.tenant_id, scope.project_id),
        )
        connection.commit()



def test_postgres_resource_capacity_rate_conflicting_concurrent_writes_are_race_safe():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    scope = BackendScope(
        "tenant-resource-rate-concurrency",
        "project-resource-rate-concurrency",
        1,
    )
    params = (scope.tenant_id, scope.project_id)
    cleanup_sql = (
        "DELETE FROM p6_resource_rate_capacity WHERE tenant_id=%s AND project_id=%s"
    )
    barrier = Barrier(2)

    class FirstSelectBarrierConnection:
        def __init__(self, connection):
            self._connection = connection
            self._waited = False

        def execute(self, statement, parameters=()):
            if (
                not self._waited
                and statement.lstrip().startswith("INSERT INTO p6_resource_rate_capacity")
            ):
                self._waited = True
                barrier.wait(timeout=10)
            return self._connection.execute(statement, parameters)

        def __getattr__(self, name):
            return getattr(self._connection, name)

    try:
        with connect() as connection:
            repository = PostgresP6ResourceRateRepository(connection)
            repository.initialize()
            connection.execute(cleanup_sql, params)
            connection.commit()

        def write(max_units: str) -> str:
            with connect() as connection:
                repository = PostgresP6ResourceRateRepository(
                    FirstSelectBarrierConnection(connection)
                )
                try:
                    repository.save(scope, profile(max_units=max_units))
                    connection.commit()
                    return "saved"
                except P6ResourceRatePersistenceError as exc:
                    connection.rollback()
                    return str(exc)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(write, "8"), executor.submit(write, "10")]
            results = sorted(future.result() for future in futures)
        assert results == ["IMMUTABLE_RESOURCE_RATE_CONFLICT", "saved"]

        with connect() as connection:
            row = connection.execute(
                "SELECT count(*) FROM p6_resource_rate_capacity "
                "WHERE tenant_id=%s AND project_id=%s AND resource_id=%s",
                (*params, "R-RATE-PG"),
            ).fetchone()
            assert row == (1,)
    finally:
        with connect() as connection:
            connection.execute(cleanup_sql, params)
            connection.commit()
