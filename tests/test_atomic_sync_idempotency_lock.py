from construction_pm.client_sync.atomic_sync import AtomicSyncExecutor
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.server_idempotency import IdempotencyRecord, mutation_fingerprint
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


def test_atomic_executor_requires_locking_persistence():
    class LegacyPersistence:
        def get_idempotency(self, *args):
            return None

        def put_idempotency(self, *args):
            raise AssertionError("delegate must not execute without an idempotency lock")

    transaction = RecordingTransaction()

    try:
        AtomicSyncExecutor(LegacyPersistence(), transaction, Delegate()).submit(mutation())
    except AttributeError as exc:
        assert "lock_idempotency" in str(exc)
    else:
        raise AssertionError("non-locking persistence must be rejected")


def test_atomic_executor_replays_existing_idempotent_outcome_without_delegate_execution():
    persistence = RecordingPersistence()
    transaction = RecordingTransaction()
    existing = mutation()
    persistence.record = IdempotencyRecord(
        existing.tenant_id,
        existing.project_id,
        existing.idempotency_key,
        existing.mutation_id,
        mutation_fingerprint(existing),
        {
            "mutation_id": existing.mutation_id,
            "disposition": SyncDisposition.ACKNOWLEDGED.value,
            "error_code": None,
            "retry_after_seconds": None,
        },
    )

    class FailingDelegate:
        def submit(self, _mutation):
            raise AssertionError("delegate must not run on an idempotent replay")

    outcome = AtomicSyncExecutor(persistence, transaction, FailingDelegate()).submit(existing)

    assert outcome.mutation_id == "m1"
    assert outcome.disposition is SyncDisposition.ACKNOWLEDGED
    assert transaction.events == ["begin", "commit"]
    assert persistence.events == [
        ("lock", "tenant", "project", "key-1"),
        ("get", "tenant", "project", "key-1"),
    ]


def test_atomic_executor_rejects_reused_key_with_different_fingerprint_inside_transaction():
    persistence = RecordingPersistence()
    transaction = RecordingTransaction()
    existing = mutation()
    persistence.record = IdempotencyRecord(
        existing.tenant_id,
        existing.project_id,
        existing.idempotency_key,
        existing.mutation_id,
        "different-fingerprint",
        {
            "mutation_id": existing.mutation_id,
            "disposition": SyncDisposition.ACKNOWLEDGED.value,
            "error_code": None,
            "retry_after_seconds": None,
        },
    )

    class FailingDelegate:
        def submit(self, _mutation):
            raise AssertionError("delegate must not run for a reused idempotency key")

    try:
        AtomicSyncExecutor(persistence, transaction, FailingDelegate()).submit(existing)
    except ValueError as exc:
        assert str(exc) == "IDEMPOTENCY_KEY_REUSE"
    else:
        raise AssertionError("reused idempotency key must be rejected")

    assert transaction.events == ["begin", "rollback"]
    assert persistence.events == [
        ("lock", "tenant", "project", "key-1"),
        ("get", "tenant", "project", "key-1"),
    ]
