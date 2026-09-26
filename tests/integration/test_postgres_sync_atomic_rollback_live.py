import os

import pytest

psycopg = pytest.importorskip("psycopg")

DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.client_sync.atomic_sync import AtomicSyncExecutor
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.postgres_sync_state import PostgresSyncStateStore
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.client_sync.server_idempotency import IdempotencyRecord
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome


class FailingPersistence(PostgresSyncStateStore):
    def put_idempotency(self, record: IdempotencyRecord) -> None:
        super().put_idempotency(record)
        raise RuntimeError("downstream persistence failure")


class Delegate:
    def submit(self, mutation: OfflineMutation) -> SyncOutcome:
        return SyncOutcome(mutation.mutation_id, SyncDisposition.ACKNOWLEDGED)


def test_real_postgres_rolls_back_idempotency_write_after_downstream_failure() -> None:
    tenant = "live-rollback-tenant"
    project = "live-rollback-project"
    key = "live-rollback-key"

    with psycopg.connect(DSN) as setup:
        store = PostgresSyncStateStore(setup)
        store.initialize()
        setup.commit()
        with setup.cursor() as cursor:
            cursor.execute(
                "DELETE FROM sync_idempotency WHERE tenant_id=%s AND project_id=%s AND idempotency_key=%s",
                (tenant, project, key),
            )
            setup.commit()

    mutation = OfflineMutation(
        mutation_id="live-rollback-mutation",
        tenant_id=tenant,
        project_id=project,
        expected_revision=1,
        operation="update_activity",
        payload={"id": "A1"},
        idempotency_key=key,
    )

    with pytest.raises(RuntimeError, match="downstream persistence failure"):
        with psycopg.connect(DSN) as connection:
            executor = AtomicSyncExecutor(
                FailingPersistence(connection),
                PostgresTransactionManager(connection),
                Delegate(),
            )
            executor.submit(mutation)

    with psycopg.connect(DSN) as connection:
        store = PostgresSyncStateStore(connection)
        assert store.get_idempotency(tenant, project, key) is None
