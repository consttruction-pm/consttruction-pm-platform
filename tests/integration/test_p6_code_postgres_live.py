import os
import threading
from concurrent.futures import ThreadPoolExecutor
import uuid
import pytest
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_code_repository import P6CodeDefinition, P6CodeValue, P6CodePersistenceError, PostgresP6CodeRepository

pytestmark=pytest.mark.skipif(not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"), reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured")

def connect():
    import psycopg
    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])

def definition(scope):
    return P6CodeDefinition(scope,"ACTIVITY_TYPE","Activity Type","Activity","PROJECT","project-1",
        (P6CodeValue("a","Task"),P6CodeValue("b","Milestone")))

def test_postgres_round_trip_isolation_and_revision():
    with connect() as conn:
        repo=PostgresP6CodeRepository(conn); repo.initialize()
        s=BackendScope("tenant-code-pg","project-code-pg",1); item=definition(s)
        assert repo.upsert(item)==item
        assert repo.get(s,"ACTIVITY_TYPE")==item
        assert repo.get(BackendScope("other","project-code-pg",1),"ACTIVITY_TYPE") is None
        with pytest.raises(P6CodePersistenceError, match="REVISION_CONFLICT"):
            repo.get(BackendScope("tenant-code-pg","project-code-pg",2),"ACTIVITY_TYPE")

def test_postgres_rollback():
    with connect() as conn:
        repo=PostgresP6CodeRepository(conn); repo.initialize()
        s=BackendScope("tenant-code-rb","project-code-rb",1)
        try:
            repo.upsert(definition(s))
            raise RuntimeError("force rollback")
        except RuntimeError:
            conn.rollback()
        assert repo.get(s,"ACTIVITY_TYPE") is None

def test_postgres_concurrent_identical_upsert_is_idempotent():
    suffix = uuid.uuid4().hex
    scope = BackendScope(f"tenant-code-concurrent-{suffix}", f"project-code-concurrent-{suffix}", 1)
    item = definition(scope)
    barrier = threading.Barrier(2)

    def save():
        with connect() as conn:
            repo = PostgresP6CodeRepository(conn)
            repo.initialize()
            conn.commit()
            barrier.wait(timeout=5)
            return repo.upsert(item)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(save) for _ in range(2)]
        results = [future.result(timeout=10) for future in futures]

    assert results == [item, item]
