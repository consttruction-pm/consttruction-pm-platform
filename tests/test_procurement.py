import pytest
from construction_pm.procurement import ProcurementResource,ProcurementResourceType,ProcurementStatus,ProcurementService,ProcurementConflict,InMemoryProcurementRepository

def resource(revision=0,payload=None,tenant="t1",project="p1"):
    return ProcurementResource(tenant,project,"proc-1",revision,ProcurementResourceType.RFQ,
        ProcurementStatus.DRAFT,"actor-1","2026-09-27T06:00:00Z",payload or {"summary":"materials"})

def test_persists_audit():
    r=InMemoryProcurementRepository()
    saved=ProcurementService(r).upsert(resource(),expected_revision=0,idempotency_key="k1")
    assert saved.resource_type is ProcurementResourceType.RFQ
    assert len(r.audits)==1

def test_replay_is_idempotent():
    r=InMemoryProcurementRepository(); s=ProcurementService(r)
    first=s.upsert(resource(),expected_revision=0,idempotency_key="k1")
    replay=s.upsert(resource(),expected_revision=0,idempotency_key="k1")
    assert replay==first and len(r.audits)==1

def test_key_reuse_is_rejected():
    r=InMemoryProcurementRepository(); s=ProcurementService(r)
    s.upsert(resource(payload={"x":"a"}),expected_revision=0,idempotency_key="k1")
    with pytest.raises(ProcurementConflict,match="IDEMPOTENCY_KEY_REUSE"):
        s.upsert(resource(payload={"x":"b"}),expected_revision=0,idempotency_key="k1")

def test_stale_revision_is_rejected():
    r=InMemoryProcurementRepository(); s=ProcurementService(r)
    s.upsert(resource(),expected_revision=0,idempotency_key="k1")
    with pytest.raises(ProcurementConflict,match="REVISION_CONFLICT"):
        s.upsert(resource(revision=1),expected_revision=0,idempotency_key="k2")

def test_tenant_isolation():
    r=InMemoryProcurementRepository(); s=ProcurementService(r)
    s.upsert(resource(tenant="t1"),expected_revision=0,idempotency_key="k1")
    s.upsert(resource(tenant="t2"),expected_revision=0,idempotency_key="k1")
    assert len(r.resources)==2
