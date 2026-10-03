from __future__ import annotations

import os

import pytest

from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_baseline_repository import (
    P6Baseline,
    PostgresP6BaselineRepository,
)
from construction_pm.p6_financial_period_repository import (
    P6FinancialPeriod,
    PostgresP6FinancialPeriodRepository,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),
    reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured",
)


def connect():
    import psycopg

    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])


@pytest.mark.parametrize(
    ("repo_cls", "item", "key"),
    [
        (
            PostgresP6FinancialPeriodRepository,
            P6FinancialPeriod(
                BackendScope("tenant-core-rollback", "project-core-rollback", 101),
                "period-rollback",
                "October 2026",
                "2026-10-01",
                "2026-10-31",
                "OPEN",
            ),
            "period-rollback",
        ),
        (
            PostgresP6BaselineRepository,
            P6Baseline(
                BackendScope("tenant-core-rollback", "project-core-rollback", 102),
                "baseline-rollback",
                "Primary",
                "PRIMARY",
                6,
                "2026-10-03T00:00:00Z",
                "baseline",
            ),
            "baseline-rollback",
        ),
    ],
)
def test_postgres_rollback_does_not_persist_transaction(repo_cls, item, key):
    with connect() as connection:
        repo = repo_cls(connection)
        repo.initialize()

        with pytest.raises(RuntimeError, match="force rollback"):
            with connection.transaction():
                repo.upsert(item)
                raise RuntimeError("force rollback")

        assert repo.get(item.scope, key) is None
