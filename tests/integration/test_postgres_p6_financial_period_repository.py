import os
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.backend_p0.models import BackendScope
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.p6_financial_period_repository import (
    P6FinancialPeriod,
    P6FinancialPeriodPersistenceError,
    PostgresP6FinancialPeriodRepository,
)


def scope(revision=1):
    suffix = uuid.uuid4().hex
    return BackendScope(f"fp-{suffix}", f"project-{suffix}", revision)


def period(s):
    return P6FinancialPeriod(s, "2026-09", "September 2026", "2026-09-01", "2026-09-30")


def test_postgres_round_trip_isolation_revision_and_rollback():
    s = scope()
    with psycopg.connect(DSN) as connection:
        repo = PostgresP6FinancialPeriodRepository(connection)
        repo.initialize()
        connection.commit()
        with PostgresTransactionManager(connection).transaction():
            repo.upsert(period(s))
        assert repo.get(s, "2026-09") == period(s)
        assert repo.get(BackendScope(s.tenant_id + "-other", s.project_id, s.project_revision), "2026-09") is None
        with pytest.raises(P6FinancialPeriodPersistenceError, match="REVISION_CONFLICT"):
            repo.get(BackendScope(s.tenant_id, s.project_id, 2), "2026-09")
        with pytest.raises(RuntimeError, match="FORCED_ROLLBACK"):
            with PostgresTransactionManager(connection).transaction():
                repo.upsert(P6FinancialPeriod(s, "2026-10", "October 2026", "2026-10-01", "2026-10-31"))
                raise RuntimeError("FORCED_ROLLBACK")
        assert repo.get(s, "2026-10") is None
