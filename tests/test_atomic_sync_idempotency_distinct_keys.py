from construction_pm.client_sync.atomic_sync import AtomicSyncExecutor
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome


class Persistence:
    def __init__(self):
        self.locked = set()
        self.records = {}
        self.events = []

    def lock_idempotency(self, tenant_id, project_id, key):
        self.events.append(("lock", tenant_id, project_id, key))
        self.locked.add((tenant_id, project_id, key))

    def get_idempotency(self, tenant_id, project_id, key):
        self.events.append(("get", tenant_id, project_id, key))
        return self.records.get((tenant_id, project_id, key))

    def put_idempotency(self, record):
        self.events.append(("put", record.idempotency_key))
        self.records[(record.tenant_id, record.project_id, record.idempotency_key)] = record

    def save_conflict(self, *args):
        pass

    def get_conflict(self, *args):
        return None


class Transaction:
    def __init__(self):
        self.events = []

    def transaction(self):
        owner = self

        class Context:
            def __enter__(self):
                owner.events.append("begin")

            def __exit__(self, exc_type, exc, tb):
                owner.events.append("rollback" if exc_type else "commit")
                return False

        return Context()


class Delegate:
    def submit(self, mutation):
        return SyncOutcome(mutation.mutation_id, SyncDisposition.ACKNOWLEDGED)


def make_mutation(key):
    return OfflineMutation("m1-" + key, "tenant", "project", 3, "update_activity", {"id": "A1"}, key)


def test_distinct_idempotency_keys_use_distinct_lock_identities():
    persistence = Persistence()
    transaction = Transaction()
    executor = AtomicSyncExecutor(persistence, transaction, Delegate())

    executor.submit(make_mutation("key-a"))
    executor.submit(make_mutation("key-b"))

    assert persistence.events[0] == ("lock", "tenant", "project", "key-a")
    assert persistence.events[3] == ("lock", "tenant", "project", "key-b")
    assert len(persistence.locked) == 2
