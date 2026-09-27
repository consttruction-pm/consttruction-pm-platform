from contextlib import contextmanager

import pytest
from construction_pm.change_claims import (
    ChangeClaim, ChangeClaimStatus, ChangeClaimType,
    PostgresChangeClaimStore, ChangeClaimIdempotencyReuse, ChangeClaimRevisionConflict,
)

class Cursor:
    def __init__(self,row=None): self.row=row
    def fetchone(self): return self.row

class Tx:
    def __enter__(self): return self
    def __exit__(self,*args): return False

class Connection:
    def __init__(self): self.revision={}; self.rows={}
    def transaction(self): return Tx()
    def execute(self,sql,params=()):
        if sql.startswith("INSERT INTO project_change_revisions"):
            self.revision.setdefault((params[0],params[1]),0); return Cursor()
        if sql.startswith("SELECT revision FROM project_change_revisions"):
            return Cursor((self.revision.get((params[0],params[1])),))
        if sql.startswith("SELECT fingerprint, resource_json"):
            return Cursor(self.rows.get(("idem",*params)))
        if sql.startswith("UPDATE project_change_revisions"):
            self.revision[(params[1],params[2])]=params[0]; return Cursor()
        if sql.startswith("INSERT INTO project_change_claims"):
            key=(params[0],params[1],params[2])
            self.rows[("row",*key)]=(params[6],params[5])
            self.rows[("idem",params[0],params[1],params[3])]=(params[4],params[6],params[5])
            return Cursor()
        if sql.startswith("SELECT resource_json, project_revision"):
            return Cursor(self.rows.get(("row",*params)))
        return Cursor()

def resource(**kw):
    v=dict(tenant_id="T-1",project_id="P-1",resource_id="chg-1",revision=0,
           resource_type=ChangeClaimType.CHANGE,status=ChangeClaimStatus.DRAFT,
           actor_id="u-1",occurred_at="2026-09-27T08:00:00+00:00",
           payload={"reason":"scope"},evidence_refs=("doc-1",))
    v.update(kw); return ChangeClaim(**v)

def test_transactional_persist_and_replay():
    c=Connection(); s=PostgresChangeClaimStore(c); s.initialize(); s.ensure_project("T-1","P-1")
    first=s.persist(resource(),expected_project_revision=0,idempotency_key="k1")
    replay=s.persist(resource(),expected_project_revision=0,idempotency_key="k1")
    assert first.project_revision==1 and replay==first
    assert s.get("T-1","P-1","chg-1")==first

def test_stale_revision_and_key_reuse():
    c=Connection(); s=PostgresChangeClaimStore(c); s.initialize(); s.ensure_project("T-1","P-1")
    s.persist(resource(),expected_project_revision=0,idempotency_key="k1")
    with pytest.raises(ChangeClaimRevisionConflict): s.persist(resource(resource_id="chg-2"),expected_project_revision=0,idempotency_key="k2")
    with pytest.raises(ChangeClaimIdempotencyReuse): s.persist(resource(payload={"reason":"different"}),expected_project_revision=1,idempotency_key="k1")

def test_tenant_project_isolation():
    c=Connection(); s=PostgresChangeClaimStore(c); s.initialize(); s.ensure_project("T-1","P-1"); s.ensure_project("T-2","P-1")
    a=s.persist(resource(),expected_project_revision=0,idempotency_key="k1")
    b=s.persist(resource(tenant_id="T-2"),expected_project_revision=0,idempotency_key="k1")
    assert a.project_revision==b.project_revision==1
