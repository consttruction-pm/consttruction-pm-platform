import pytest

from construction_pm.change_claims import (
    ChangeClaim, ChangeClaimConflict, ChangeClaimError, ChangeClaimService, ChangeClaimStatus,
    ChangeClaimType, InMemoryChangeClaimRepository,
)


def resource(revision=0, payload=None, tenant="t1", project="p1", status=ChangeClaimStatus.DRAFT):
    return ChangeClaim(
        tenant_id=tenant, project_id=project, resource_id="cc-1", revision=revision,
        resource_type=ChangeClaimType.CLAIM, status=status, actor_id="actor-1",
        occurred_at="2026-09-27T06:00:00Z", payload=payload or {"summary": "site impact"},
        evidence_refs=("doc-1",),
    )


def test_change_claim_persists_audit_and_evidence():
    repo = InMemoryChangeClaimRepository()
    stored = ChangeClaimService(repo).upsert(resource(), expected_revision=0, idempotency_key="k1")
    assert stored.evidence_refs == ("doc-1",)
    assert len(repo.audits) == 1
    assert repo.audits[0].status is ChangeClaimStatus.DRAFT


def test_same_key_replays_without_duplicate_audit():
    repo = InMemoryChangeClaimRepository()
    service = ChangeClaimService(repo)
    first = service.upsert(resource(), expected_revision=0, idempotency_key="k1")
    replay = service.upsert(resource(), expected_revision=0, idempotency_key="k1")
    assert replay == first
    assert len(repo.audits) == 1


def test_same_key_different_payload_is_rejected():
    repo = InMemoryChangeClaimRepository()
    service = ChangeClaimService(repo)
    service.upsert(resource(payload={"summary": "a"}), expected_revision=0, idempotency_key="k1")
    with pytest.raises(ChangeClaimConflict, match="IDEMPOTENCY_KEY_REUSE"):
        service.upsert(resource(payload={"summary": "b"}), expected_revision=0, idempotency_key="k1")


def test_stale_revision_is_rejected():
    repo = InMemoryChangeClaimRepository()
    service = ChangeClaimService(repo)
    service.upsert(resource(), expected_revision=0, idempotency_key="k1")
    with pytest.raises(ChangeClaimConflict, match="REVISION_CONFLICT"):
        service.upsert(resource(revision=1), expected_revision=0, idempotency_key="k2")


def test_tenant_isolation_is_preserved():
    repo = InMemoryChangeClaimRepository()
    service = ChangeClaimService(repo)
    service.upsert(resource(tenant="t1"), expected_revision=0, idempotency_key="k1")
    service.upsert(resource(tenant="t2"), expected_revision=0, idempotency_key="k1")
    assert len(repo.resources) == 2


def test_contract_version_is_preserved_and_validated():
    item = resource()
    assert item.contract_version == "1.0"
    item.validate()


def test_unsupported_contract_version_is_rejected():
    item = resource(contract_version="2.0")
    with pytest.raises(ChangeClaimError, match="UNSUPPORTED_CHANGE_CLAIM_CONTRACT_VERSION"):
        item.validate()
