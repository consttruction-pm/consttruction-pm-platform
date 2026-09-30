import os
import pytest
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_cost_account_repository import P6CostAccount, PostgresP6CostAccountRepository

@pytest.mark.skipif(not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"), reason="PostgreSQL DSN not configured")
def test_postgres_cost_account_round_trip_and_revision():
    import psycopg
    connection = psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])
    try:
        connection.autocommit = False
        repo = PostgresP6CostAccountRepository(connection); repo.initialize()
        scope = BackendScope("integration-tenant", "integration-project", 1)
        item = P6CostAccount(scope, "01", "Root", None, "Root cost account")
        repo.upsert(item)
        repo.upsert(P6CostAccount(scope, "02", "Child", "01", "Child cost account"))
        assert repo.get(scope, "01") == item
        assert [x.account_id for x in repo.list(scope)] == ["01", "02"]
        connection.commit()
        with pytest.raises(Exception, match="REVISION_CONFLICT"): repo.get(BackendScope(scope.tenant_id, scope.project_id, 2), "01")
    finally:
        connection.rollback(); connection.close()


@pytest.mark.skipif(not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"), reason="PostgreSQL DSN not configured")
def test_postgres_cost_account_concurrent_identical_upsert_is_idempotent():
    import threading
    import uuid
    from concurrent.futures import ThreadPoolExecutor
    import psycopg
    suffix = uuid.uuid4().hex
    scope = BackendScope(f"tenant-cost-concurrent-{suffix}", f"project-cost-concurrent-{suffix}", 1)
    item = P6CostAccount(scope, "01", "Root", None, "Root cost account")
    barrier = threading.Barrier(2)
    def save():
        with psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"]) as connection:
            repo = PostgresP6CostAccountRepository(connection); repo.initialize(); connection.commit()
            barrier.wait(timeout=5)
            return repo.upsert(item)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [f.result(timeout=10) for f in [pool.submit(save), pool.submit(save)]]
    assert results == [item, item]
