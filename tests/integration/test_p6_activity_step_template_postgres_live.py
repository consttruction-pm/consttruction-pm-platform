import os
import threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from construction_pm.backend_p0.models import BackendScope
from construction_pm.p6_activity_step_template_repository import P6ActivityStepTemplate, PostgresP6ActivityStepTemplateRepository

pytestmark=pytest.mark.skipif(not os.getenv("CONSTRUCTION_PM_POSTGRES_DSN"),reason="CONSTRUCTION_PM_POSTGRES_DSN is not configured")

def _connect():
    import psycopg
    return psycopg.connect(os.environ["CONSTRUCTION_PM_POSTGRES_DSN"])

def test_postgres_activity_step_template_round_trip_and_scope_isolation():
    with _connect() as connection:
        repo=PostgresP6ActivityStepTemplateRepository(connection); repo.initialize(); connection.commit()
        scope=BackendScope("tenant-template","project-template",7)
        value=P6ActivityStepTemplate(scope,"TPL-1","Formwork Inspection","Standard inspection steps",(("discipline","STRUCT"),))
        repo.upsert(value); connection.commit()
        assert repo.get(scope,"TPL-1")==value
        assert repo.get(BackendScope("tenant-other","project-template",7),"TPL-1") is None

def test_postgres_activity_step_template_revision_conflict_and_rollback():
    with _connect() as connection:
        repo=PostgresP6ActivityStepTemplateRepository(connection); repo.initialize(); connection.commit()
        scope=BackendScope("tenant-template-rollback","project-template",3); value=P6ActivityStepTemplate(scope,"TPL-1","Formwork Inspection")
        repo.upsert(value); connection.commit()
        with pytest.raises(Exception):
            with connection.transaction(): repo.upsert(P6ActivityStepTemplate(scope,"TPL-1","Changed"))
        assert repo.get(scope,"TPL-1")==value
        with pytest.raises(Exception,match="REVISION_CONFLICT"): repo.get(BackendScope("tenant-template-rollback","project-template",4),"TPL-1")


def test_postgres_activity_step_template_concurrent_identical_upsert_is_idempotent():
    scope = BackendScope("tenant-template-concurrent", "project-template", 5)
    value = P6ActivityStepTemplate(
        scope=scope,
        template_id="TPL-CONCURRENT",
        name="Concurrent template",
        description="Concurrent insert",
        udf_metadata=(("crew", "text"),),
    )
    barrier = threading.Barrier(2)

    def save():
        with _connect() as connection:
            repo = PostgresP6ActivityStepTemplateRepository(connection)
            repo.initialize()
            connection.commit()
            barrier.wait(timeout=5)
            with connection.transaction():
                return repo.upsert(value)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(save) for _ in range(2)]
        results = [future.result(timeout=10) for future in futures]

    assert results == [value, value]
