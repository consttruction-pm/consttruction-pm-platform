from construction_pm.client_sync.conflict import ConflictContext
from construction_pm.client_sync.conflict_store import InMemoryConflictStore
from construction_pm.client_sync.idempotency_store import InMemoryDurableIdempotencyStore
from construction_pm.client_sync.server_idempotency import IdempotencyRecord


def test_idempotency_store_is_tenant_project_scoped() -> None:
    store = InMemoryDurableIdempotencyStore()
    record = IdempotencyRecord(
        tenant_id="t1", project_id="p1", idempotency_key="k1",
        mutation_id="m1", fingerprint="f1",
        outcome={"mutation_id": "m1", "disposition": "acknowledged"},
    )
    store.put(record)
    assert store.get("t1", "p1", "k1") == record
    assert store.get("t2", "p1", "k1") is None


def test_conflict_store_is_tenant_project_scoped() -> None:
    store = InMemoryConflictStore()
    context = ConflictContext(
        error_code="STALE_REVISION",
        expected_revision=7,
        actual_revision=8,
        available_actions=("discard", "refresh_and_retry", "defer"),
        details={"resource": "activity"},
    )
    store.save("m1", "t1", "p1", context)
    assert store.get("m1", "t1", "p1") == context
    assert store.get("m1", "t2", "p1") is None
