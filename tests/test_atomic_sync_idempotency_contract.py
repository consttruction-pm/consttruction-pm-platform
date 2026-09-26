import pytest

from construction_pm.client_sync.atomic_sync import AtomicSyncExecutor
from construction_pm.client_sync.offline_mutation import OfflineMutation
from construction_pm.client_sync.server_idempotency import mutation_fingerprint
from construction_pm.client_sync.sync_outcome import SyncDisposition, SyncOutcome


class Transaction:
    def __init__(self):
        self.events = []

    def transaction(self):
        owner = self

        class Context:
            def __enter__(self):
                owner.events.append("BEGIN")
                return self

            def __exit__(self, exc_type, exc, tb):
                owner.events.append("ROLLBACK" if exc_type else "COMMIT")
                return False

        return Context()


class Store:
    def __init__(self):
        self.records = {}
        self.events = []

    def lock_idempotency(self, tenant, project, key):
        self.events.append(("lock", tenant, project, key))

    def get_idempotency(self, tenant, project, key):
        self.events.append(("get", tenant, project, key))
        return self.records.get((tenant, project, key))

    def put_idempotency(self, record):
        self.events.append(("put", record.idempotency_key))
        existing = self.records.get(
            (record.tenant_id, record.project_id, record.idempotency_key)
        )
        if existing and existing.fingerprint != record.fingerprint:
            raise ValueError("IDEMPOTENCY_KEY_REUSE")
        self.records[
            (record.tenant_id, record.project_id, record.idempotency_key)
        ] = record


class Delegate:
    def __init__(self, outcomes=None, errors=None):
        self.calls = 0
        self.outcomes = list(outcomes or [])
        self.errors = list(errors or [])

    def submit(self, mutation):
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        if self.outcomes:
            return self.outcomes.pop(0)
        return SyncOutcome(mutation.mutation_id, SyncDisposition.ACKNOWLEDGED)


def make_mutation(
    *,
    tenant="tenant-a",
    project="project-a",
    key="key-a",
    mutation_id="m1",
    revision=7,
    payload=None,
):
    return OfflineMutation(
        mutation_id,
        tenant,
        project,
        revision,
        "update_activity",
        payload or {"id": "A1"},
        key,
    )


def test_business_failure_rolls_back_without_idempotency_record():
    store = Store()
    tx = Transaction()
    delegate = Delegate(errors=[RuntimeError("boom")])
    executor = AtomicSyncExecutor(store, tx, delegate)

    with pytest.raises(RuntimeError, match="boom"):
        executor.submit(make_mutation())

    assert tx.events == ["BEGIN", "ROLLBACK"]
    assert store.records == {}
    assert delegate.calls == 1


def test_retry_after_failure_executes_again_and_persists():
    store = Store()
    tx = Transaction()
    delegate = Delegate(errors=[RuntimeError("temporary")])
    executor = AtomicSyncExecutor(store, tx, delegate)
    mutation = make_mutation()

    with pytest.raises(RuntimeError):
        executor.submit(mutation)

    result = executor.submit(mutation)

    assert result.disposition is SyncDisposition.ACKNOWLEDGED
    assert delegate.calls == 2
    assert len(store.records) == 1
    assert tx.events == ["BEGIN", "ROLLBACK", "BEGIN", "COMMIT"]


def test_identical_replay_does_not_execute_delegate_again():
    store = Store()
    tx = Transaction()
    delegate = Delegate()
    executor = AtomicSyncExecutor(store, tx, delegate)
    mutation = make_mutation()

    first = executor.submit(mutation)
    second = executor.submit(mutation)

    assert first == second
    assert delegate.calls == 1
    assert tx.events == ["BEGIN", "COMMIT", "BEGIN", "COMMIT"]


def test_same_key_different_payload_is_rejected_without_delegate():
    store = Store()
    tx = Transaction()
    delegate = Delegate()
    executor = AtomicSyncExecutor(store, tx, delegate)

    executor.submit(make_mutation(payload={"id": "A1", "value": 10}))

    with pytest.raises(ValueError, match="IDEMPOTENCY_KEY_REUSE"):
        executor.submit(make_mutation(payload={"id": "A1", "value": 11}))

    assert delegate.calls == 1
    assert tx.events == ["BEGIN", "COMMIT", "BEGIN", "ROLLBACK"]


def test_same_key_in_different_tenant_is_independent():
    store = Store()
    tx = Transaction()
    delegate = Delegate()
    executor = AtomicSyncExecutor(store, tx, delegate)

    first = executor.submit(make_mutation(tenant="tenant-a"))
    second = executor.submit(
        make_mutation(tenant="tenant-b", mutation_id="m2")
    )

    assert first.disposition is SyncDisposition.ACKNOWLEDGED
    assert second.disposition is SyncDisposition.ACKNOWLEDGED
    assert delegate.calls == 2
    assert len(store.records) == 2


def test_fingerprint_is_stable_for_equivalent_mapping_order():
    first = make_mutation(payload={"b": 2, "a": 1})
    second = make_mutation(payload={"a": 1, "b": 2})
    assert mutation_fingerprint(first) == mutation_fingerprint(second)


def test_replay_preserves_retry_metadata():
    store = Store()
    tx = Transaction()
    expected = SyncOutcome(
        "m1",
        SyncDisposition.RETRY,
        error_code="TEMPORARY",
        retry_after_seconds=12,
    )
    delegate = Delegate(outcomes=[expected])
    executor = AtomicSyncExecutor(store, tx, delegate)
    mutation = make_mutation()

    first = executor.submit(mutation)
    second = executor.submit(mutation)

    assert first == expected
    assert second == expected
    assert delegate.calls == 1
