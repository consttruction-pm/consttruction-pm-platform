from construction_pm.client_sync.atomic_sync import AtomicSyncExecutor
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome


class RecordingPersistence:
    def __init__(self):
        self.events = []
        self.record = None

    def lock_idempotency(self, tenant_id, project_id, key):
        self.events.append(("lock", tenant_id, project_id, key))

    def get_idempotency(self, tenant_id, project_id, key):
        self.events.append(("get", tenant_id, project_id, key))
        return self.record

    def put_idempotency(self, record):
        self.events.append(("put", record.idempotency_key))
        self.record = record

    def save_conflict(self, *args):
        pass

    def get_conflict(self, *args):
        return None


class RecordingTransaction:
    def __init__(self):
        self.events = []

    def transaction(self):
        manager = self

        class Context:
            def __enter__(self):
                manager.events.append("begin")

            def __exit__(self, exc_type, exc, tb):
                manager.events.append("rollback" if exc_type else "commit")
                return False

        return Context()


class Delegate:
    def submit(self, mutation):
        return SyncOutcome(mutation.mutation_id, SyncDisposition.ACKNOWLEDGED)


def mutation():
    return OfflineMutation(
        "m1", "tenant", "project", 3, "update_activity", {"id": "A1"}, "key-1"
    )


def test_atomic_executor_acquires_idempotency_lock_before_lookup_and_commit():
    persistence = RecordingPersistence()
    transaction = RecordingTransaction()

    outcome = AtomicSyncExecutor(persistence, transaction, Delegate()).submit(mutation())

    assert outcome.disposition is SyncDisposition.ACKNOWLEDGED
    assert transaction.events == ["begin", "commit"]
    assert persistence.events == [
        ("lock", "tenant", "project", "key-1"),
        ("get", "tenant", "project", "key-1"),
        ("put", "key-1"),
    ]


def test_atomic_executor_does_not_require_lock_hook_for_legacy_persistence():
    class LegacyPersistence(RecordingPersistence):
        lock_idempotency = None

    persistence = LegacyPersistence()
    transaction = RecordingTransaction()

    outcome = AtomicSyncExecutor(persistence, transaction, Delegate()).submit(mutation())

    assert outcome.disposition is SyncDisposition.ACKNOWLEDGED
    assert persistence.events == [
        ("get", "tenant", "project", "key-1"),
        ("put", "key-1"),
    ]
