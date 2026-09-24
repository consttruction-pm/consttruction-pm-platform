import os
import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.client_sync.atomic_conflict import AtomicConflictSyncExecutor
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.postgres_sync_state import PostgresSyncStateStore
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome


class ConflictDelegate:
    def __init__(self):
        self.calls = 0

    def submit(self, mutation):
        self.calls += 1
        return SyncOutcome(
            mutation.mutation_id,
            SyncDisposition.CONFLICT,
            error_code="REVISION_CONFLICT",
        )


def _connect():
    return psycopg.connect(DSN)


def _mutation(key="live-conflict-key", mutation_id="live-conflict-m1"):
    return OfflineMutation(
        mutation_id,
        "live-ci-tenant",
        "live-ci-project",
        7,
        "update_activity",
        {"id": "A1"},
        key,
    )


def test_real_postgres_atomic_conflict_persists_and_replays():
    mutation = _mutation()
    with _connect() as conn:
        store = PostgresSyncStateStore(conn)
        store.initialize()
        delegate = ConflictDelegate()
        executor = AtomicConflictSyncExecutor(
            store,
            PostgresTransactionManager(conn),
            delegate,
        )

        first = executor.submit(mutation)
        conflict = store.get_conflict(
            mutation.mutation_id, mutation.tenant_id, mutation.project_id
        )

        assert first.disposition is SyncDisposition.CONFLICT
        assert first.error_code == "REVISION_CONFLICT"
        assert conflict is not None
        assert conflict.expected_revision == 7
        assert conflict.error_code == "REVISION_CONFLICT"

        second = executor.submit(mutation)
        assert second == first
        assert delegate.calls == 1
