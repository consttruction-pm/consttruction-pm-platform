import os
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.backend_p0.models import BackendScope
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.p6_baseline_repository import (
    P6Baseline,
    P6BaselinePersistenceError,
    PostgresP6BaselineRepository,
)


def scope(revision=7):
    suffix = uuid.uuid4().hex
    return BackendScope(f"baseline-{suffix}", f"project-{suffix}", revision)


def baseline(s, baseline_id="b-1"):
    return P6Baseline(
        s, baseline_id, "Approved Baseline", "PRIMARY", 3,
        "2026-09-28T10:00:00Z", "immutable metadata",
    )


def test_postgres_round_trip_isolation_revision_and_rollback():
    s = scope()
    with psycopg.connect(DSN) as connection:
        repo = PostgresP6BaselineRepository(connection)
        repo.initialize()
        connection.commit()

        with PostgresTransactionManager(connection).transaction():
            repo.upsert(baseline(s))

        assert repo.get(s, "b-1") == baseline(s)
        assert repo.get(BackendScope(s.tenant_id + "-other", s.project_id, s.project_revision), "b-1") is None

        with pytest.raises(P6BaselinePersistenceError, match="REVISION_CONFLICT"):
            repo.get(BackendScope(s.tenant_id, s.project_id, 8), "b-1")

        with pytest.raises(RuntimeError, match="FORCED_ROLLBACK"):
            with PostgresTransactionManager(connection).transaction():
                repo.upsert(baseline(s, "b-2"))
                raise RuntimeError("FORCED_ROLLBACK")

        assert repo.get(s, "b-2") is None
