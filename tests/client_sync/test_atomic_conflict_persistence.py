from contextlib import contextmanager

from construction_pm.client_sync.atomic_conflict import AtomicConflictSyncExecutor
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome


class FakePersistence:
    def __init__(self):
        self.idempotency = {}
        self.conflicts = {}

    def get_idempotency(self, tenant_id, project_id, key):
        return self.idempotency.get((tenant_id, project_id, key))

    def put_idempotency(self, record):
        self.idempotency[(record.tenant_id, record.project_id, record.idempotency_key)] = record

    def save_conflict(self, mutation_id, tenant_id, project_id, context):
        self.conflicts[(tenant_id, project_id, mutation_id)] = context

    def get_conflict(self, mutation_id, tenant_id, project_id):
        return self.conflicts.get((tenant_id, project_id, mutation_id))


class TransactionProbe:
    def __init__(self):
        self.depth = 0

    @contextmanager
    def transaction(self):
        self.depth += 1
        try:
            yield
        finally:
            self.depth -= 1


class ConflictDelegate:
    def submit(self, mutation):
        return SyncOutcome(
            mutation_id=mutation.mutation_id,
            disposition=SyncDisposition.CONFLICT,
            error_code="REVISION_CONFLICT",
        )


def test_conflict_is_persisted_inside_atomic_transaction():
    persistence = FakePersistence()
    transaction = TransactionProbe()
    mutation = OfflineMutation(
        mutation_id="m-1",
        tenant_id="t-1",
        project_id="p-1",
        expected_revision=7,
        operation="update_activity",
        payload={"activity_id": "A"},
        idempotency_key="key-1",
    )

    executor = AtomicConflictSyncExecutor(persistence, transaction, ConflictDelegate())
    outcome = executor.submit(mutation)

    assert outcome.disposition == SyncDisposition.CONFLICT
    conflict = persistence.get_conflict("m-1", "t-1", "p-1")
    assert conflict is not None
    assert conflict.error_code == "REVISION_CONFLICT"
    assert conflict.expected_revision == 7
    assert transaction.depth == 0


def test_conflict_persistence_is_not_repeated_on_idempotent_replay():
    persistence = FakePersistence()
    transaction = TransactionProbe()
    mutation = OfflineMutation(
        mutation_id="m-2",
        tenant_id="t-1",
        project_id="p-1",
        expected_revision=3,
        operation="update_activity",
        payload={"activity_id": "B"},
        idempotency_key="key-2",
    )
    delegate = ConflictDelegate()
    executor = AtomicConflictSyncExecutor(persistence, transaction, delegate)

    first = executor.submit(mutation)
    first_conflict = persistence.get_conflict("m-2", "t-1", "p-1")
    second = executor.submit(mutation)

    assert first == second
    assert first_conflict == persistence.get_conflict("m-2", "t-1", "p-1")
