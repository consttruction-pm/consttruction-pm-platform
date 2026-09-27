import pytest

from construction_pm.field_operations import (
    FieldOperation,
    FieldOperationConflict,
    FieldOperationService,
    FieldOperationType,
    InMemoryFieldOperationRepository,
)


def op(revision=0, payload=None, tenant="t1", project="p1"):
    return FieldOperation(
        tenant_id=tenant,
        project_id=project,
        operation_id="op-1",
        revision=revision,
        operation_type=FieldOperationType.DAILY_LOG,
        occurred_at="2026-09-27T06:00:00Z",
        actor_id="actor-1",
        payload=payload or {"note": "site update"},
    )


def test_field_operation_persists_with_audit_and_idempotency():
    repo = InMemoryFieldOperationRepository()
    service = FieldOperationService(repo)

    stored = service.upsert(op(), expected_revision=0, idempotency_key="k1")

    assert stored.revision == 0
    assert len(repo.audits) == 1
    assert repo.audits[0].idempotency_key == "k1"


def test_same_key_replays_without_duplicate_audit():
    repo = InMemoryFieldOperationRepository()
    service = FieldOperationService(repo)
    first = service.upsert(op(), expected_revision=0, idempotency_key="k1")
    replay = service.upsert(op(), expected_revision=0, idempotency_key="k1")

    assert replay == first
    assert len(repo.audits) == 1


def test_same_key_with_different_payload_is_rejected():
    repo = InMemoryFieldOperationRepository()
    service = FieldOperationService(repo)
    service.upsert(op(payload={"note": "a"}), expected_revision=0, idempotency_key="k1")

    with pytest.raises(FieldOperationConflict, match="IDEMPOTENCY_KEY_REUSE"):
        service.upsert(op(payload={"note": "b"}), expected_revision=0, idempotency_key="k1")


def test_stale_revision_is_rejected_before_write():
    repo = InMemoryFieldOperationRepository()
    service = FieldOperationService(repo)
    service.upsert(op(), expected_revision=0, idempotency_key="k1")

    with pytest.raises(FieldOperationConflict, match="REVISION_CONFLICT"):
        service.upsert(op(revision=1), expected_revision=0, idempotency_key="k2")


def test_tenant_isolation_is_preserved():
    repo = InMemoryFieldOperationRepository()
    service = FieldOperationService(repo)
    service.upsert(op(tenant="t1"), expected_revision=0, idempotency_key="k1")
    service.upsert(op(tenant="t2"), expected_revision=0, idempotency_key="k1")

    assert len(repo.operations) == 2
    assert len(repo.audits) == 2
