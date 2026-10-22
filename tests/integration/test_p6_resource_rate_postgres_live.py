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
