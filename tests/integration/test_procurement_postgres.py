import pytest
from construction_pm.procurement import (
 ProcurementResource,ProcurementResourceType,ProcurementStatus,PostgresProcurementStore,
 ProcurementRevisionConflict,ProcurementIdempotencyReuse,
)
class Cursor:
 def __init__(self,row=None): self.row=row
 def fetchone(self): return self.row
class Tx:
 def __enter__(self): return self
 def __exit__(self,*a): return False
class Connection:
 def __init__(self): self.rev={}; self.rows={}
 def transaction(self): return Tx()
 def execute(self,sql,params=()):
  if sql.startswith("INSERT INTO project_procurement_revisions"): self.rev.setdefault((params[0],params[1]),0); return Cursor()
  if sql.startswith("SELECT revision FROM project_procurement_revisions"): return Cursor((self.rev.get((params[0],params[1])),))
  if sql.startswith("SELECT fingerprint, resource_json"): return Cursor(self.rows.get(("idem",*params)))
  if sql.startswith("UPDATE project_procurement_revisions"): self.rev[(params[1],params[2])]=params[0]; return Cursor()
  if sql.startswith("INSERT INTO project_procurement_resources"):
   self.rows[("row",params[0],params[1],params[2])]=(params[6],params[5])
   self.rows[("idem",params[0],params[1],params[3])]=(params[4],params[6],params[5]); return Cursor()
  if sql.startswith("SELECT resource_json, project_revision"): return Cursor(self.rows.get(("row",*params)))
  return Cursor()
def resource(**kw):
 v=dict(tenant_id="T-1",project_id="P-1",resource_id="po-1",revision=0,resource_type=ProcurementResourceType.PURCHASE_ORDER,status=ProcurementStatus.DRAFT,actor_id="u-1",occurred_at="2026-09-27T08:00:00+00:00",payload={"vendor_ref":"v1"}); v.update(kw); return ProcurementResource(**v)
def test_transactional_persist_and_replay():
 c=Connection(); s=PostgresProcurementStore(c); s.initialize(); s.ensure_project("T-1","P-1")
 a=s.persist(resource(),expected_project_revision=0,idempotency_key="k1"); b=s.persist(resource(),expected_project_revision=0,idempotency_key="k1")
 assert a==b and a.project_revision==1 and s.get("T-1","P-1","po-1")==a
def test_stale_revision_and_key_reuse():
 c=Connection(); s=PostgresProcurementStore(c); s.initialize(); s.ensure_project("T-1","P-1"); s.persist(resource(),expected_project_revision=0,idempotency_key="k1")
 with pytest.raises(ProcurementRevisionConflict): s.persist(resource(resource_id="po-2"),expected_project_revision=0,idempotency_key="k2")
 with pytest.raises(ProcurementIdempotencyReuse): s.persist(resource(payload={"vendor_ref":"other"}),expected_project_revision=1,idempotency_key="k1")
def test_tenant_isolation():
 c=Connection(); s=PostgresProcurementStore(c); s.initialize(); s.ensure_project("T-1","P-1"); s.ensure_project("T-2","P-1")
 assert s.persist(resource(),expected_project_revision=0,idempotency_key="k1").project_revision==1
 assert s.persist(resource(tenant_id="T-2"),expected_project_revision=0,idempotency_key="k1").project_revision==1
