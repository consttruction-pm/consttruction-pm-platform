import pytest
from construction_pm.dependency_graph import DependencyEdge,DependencyType,DependencyGraphService,DependencyGraphConflict,DependencyGraphError,InMemoryDependencyRepository

def edge(revision=0,source="task-a",target="task-b",tenant="t1",project="p1"):
    return DependencyEdge(tenant,project,"edge-1",revision,source,target,DependencyType.FINISH_TO_START,"actor-1")

def test_persists_audit():
    r=InMemoryDependencyRepository(); saved=DependencyGraphService(r).upsert(edge(),expected_revision=0,idempotency_key="k1")
    assert saved.edge_id=="edge-1" and len(r.audits)==1

def test_replay_without_duplicate_audit():
    r=InMemoryDependencyRepository(); s=DependencyGraphService(r)
    a=s.upsert(edge(),expected_revision=0,idempotency_key="k1"); b=s.upsert(edge(),expected_revision=0,idempotency_key="k1")
    assert a==b and len(r.audits)==1

def test_key_reuse_rejected():
    r=InMemoryDependencyRepository(); s=DependencyGraphService(r)
    s.upsert(edge(),expected_revision=0,idempotency_key="k1")
    with pytest.raises(DependencyGraphConflict,match="IDEMPOTENCY_KEY_REUSE"):
        s.upsert(edge(source="task-x"),expected_revision=0,idempotency_key="k1")

def test_stale_revision_rejected():
    r=InMemoryDependencyRepository(); s=DependencyGraphService(r); s.upsert(edge(),expected_revision=0,idempotency_key="k1")
    with pytest.raises(DependencyGraphConflict,match="REVISION_CONFLICT"): s.upsert(edge(revision=1),expected_revision=0,idempotency_key="k2")

def test_self_reference_rejected():
    with pytest.raises(DependencyGraphError,match="SELF_REFERENCE"): edge(source="task-a",target="task-a").validate()

def test_tenant_isolation():
    r=InMemoryDependencyRepository(); s=DependencyGraphService(r)
    s.upsert(edge(tenant="t1"),expected_revision=0,idempotency_key="k1"); s.upsert(edge(tenant="t2"),expected_revision=0,idempotency_key="k1")
    assert len(r.edges)==2
