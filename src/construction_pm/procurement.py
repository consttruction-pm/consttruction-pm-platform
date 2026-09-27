from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Mapping, Protocol

class ProcurementResourceType(str, Enum):
    RFQ="rfq"; QUOTE="quote"; BID_COMPARISON="bid_comparison"
    PURCHASE_ORDER="purchase_order"; COMMITMENT="commitment"; DELIVERY="delivery"

class ProcurementStatus(str, Enum):
    DRAFT="draft"; ISSUED="issued"; RECEIVED="received"; EVALUATED="evaluated"
    APPROVED="approved"; CANCELLED="cancelled"; COMPLETED="completed"

class ProcurementError(ValueError): pass
class ProcurementConflict(ProcurementError): pass

@dataclass(frozen=True)
class ProcurementResource:
    tenant_id:str; project_id:str; resource_id:str; revision:int
    resource_type:ProcurementResourceType; status:ProcurementStatus
    actor_id:str; occurred_at:str; payload:Mapping[str,object]

    def fingerprint(self)->str:
        value=json.dumps({
            "tenant_id":self.tenant_id,"project_id":self.project_id,
            "resource_id":self.resource_id,"revision":self.revision,
            "resource_type":self.resource_type.value,"status":self.status.value,
            "actor_id":self.actor_id,"occurred_at":self.occurred_at,
            "payload":dict(self.payload)},sort_keys=True,separators=(",",":"))
        return sha256(value.encode()).hexdigest()

    def validate(self)->None:
        for name,value in (("tenant_id",self.tenant_id),("project_id",self.project_id),
                           ("resource_id",self.resource_id),("actor_id",self.actor_id),
                           ("occurred_at",self.occurred_at)):
            if not isinstance(value,str) or not value.strip():
                raise ProcurementError(f"INVALID_PROCUREMENT_{name.upper()}")
        if isinstance(self.revision,bool) or not isinstance(self.revision,int) or self.revision<0:
            raise ProcurementError("INVALID_PROCUREMENT_REVISION")
        if not isinstance(self.resource_type,ProcurementResourceType):
            raise ProcurementError("INVALID_PROCUREMENT_TYPE")
        if not isinstance(self.status,ProcurementStatus):
            raise ProcurementError("INVALID_PROCUREMENT_STATUS")
        if not isinstance(self.payload,Mapping):
            raise ProcurementError("INVALID_PROCUREMENT_PAYLOAD")

@dataclass(frozen=True)
class ProcurementAudit:
    tenant_id:str; project_id:str; resource_id:str; revision:int
    actor_id:str; status:ProcurementStatus; idempotency_key:str; fingerprint:str

class ProcurementRepository(Protocol):
    def get(self,tenant_id:str,project_id:str,resource_id:str)->ProcurementResource|None: ...
    def put(self,resource:ProcurementResource)->None: ...
    def append_audit(self,audit:ProcurementAudit)->None: ...
    def get_idempotency(self,tenant_id:str,project_id:str,key:str)->ProcurementAudit|None: ...
    def put_idempotency(self,audit:ProcurementAudit)->None: ...

class InMemoryProcurementRepository:
    def __init__(self)->None:
        self.resources={}; self.audits=[]; self.idempotency={}
    def get(self,tenant_id,project_id,resource_id):
        return self.resources.get((tenant_id,project_id,resource_id))
    def put(self,resource):
        resource.validate(); self.resources[(resource.tenant_id,resource.project_id,resource.resource_id)]=resource
    def append_audit(self,audit): self.audits.append(audit)
    def get_idempotency(self,tenant_id,project_id,key):
        return self.idempotency.get((tenant_id,project_id,key))
    def put_idempotency(self,audit):
        self.idempotency[(audit.tenant_id,audit.project_id,audit.idempotency_key)]=audit

class ProcurementService:
    def __init__(self,repository:ProcurementRepository)->None: self.repository=repository
    def upsert(self,resource:ProcurementResource,*,expected_revision:int,idempotency_key:str)->ProcurementResource:
        resource.validate()
        if resource.revision!=expected_revision: raise ProcurementConflict("PROCUREMENT_REVISION_CONFLICT")
        existing_key=self.repository.get_idempotency(resource.tenant_id,resource.project_id,idempotency_key)
        if existing_key is not None:
            if existing_key.fingerprint!=resource.fingerprint():
                raise ProcurementConflict("PROCUREMENT_IDEMPOTENCY_KEY_REUSE")
            existing=self.repository.get(resource.tenant_id,resource.project_id,resource.resource_id)
            if existing is None: raise ProcurementConflict("PROCUREMENT_IDEMPOTENCY_RECORD_MISSING")
            return existing
        current=self.repository.get(resource.tenant_id,resource.project_id,resource.resource_id)
        actual=0 if current is None else current.revision
        if actual!=expected_revision: raise ProcurementConflict("PROCUREMENT_REVISION_CONFLICT")
        self.repository.put(resource)
        audit=ProcurementAudit(resource.tenant_id,resource.project_id,resource.resource_id,
            resource.revision,resource.actor_id,resource.status,idempotency_key,resource.fingerprint())
        self.repository.append_audit(audit); self.repository.put_idempotency(audit)
        return resource


from typing import Any

@dataclass(frozen=True)
class StoredProcurementResource:
    resource: ProcurementResource
    project_revision: int

class ProcurementIdempotencyReuse(ProcurementConflict):
    pass

class ProcurementRevisionConflict(ProcurementConflict):
    pass

class ProcurementConnection(Protocol):
    def execute(self, sql: str, params: tuple[Any, ...] = ()): ...
    def transaction(self): ...

@dataclass
class PostgresProcurementStore:
    connection: ProcurementConnection

    def initialize(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS project_procurement_revisions "
            "(tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, revision BIGINT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id))"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS project_procurement_resources "
            "(tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, resource_id TEXT NOT NULL, "
            "idempotency_key TEXT NOT NULL, fingerprint TEXT NOT NULL, project_revision BIGINT NOT NULL, "
            "resource_json TEXT NOT NULL, PRIMARY KEY (tenant_id, project_id, resource_id), "
            "UNIQUE (tenant_id, project_id, idempotency_key))"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS project_procurement_audit "
            "(tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, resource_id TEXT NOT NULL, "
            "project_revision BIGINT NOT NULL, actor_id TEXT NOT NULL, status TEXT NOT NULL, "
            "idempotency_key TEXT NOT NULL, occurred_at TEXT NOT NULL, "
            "PRIMARY KEY (tenant_id, project_id, resource_id, project_revision))"
        )

    def ensure_project(self, tenant_id: str, project_id: str) -> None:
        self.connection.execute(
            "INSERT INTO project_procurement_revisions (tenant_id, project_id, revision) "
            "VALUES (%s,%s,0) ON CONFLICT (tenant_id, project_id) DO NOTHING",
            (tenant_id, project_id),
        )

    def persist(self, resource: ProcurementResource, *, expected_project_revision: int, idempotency_key: str) -> StoredProcurementResource:
        resource.validate()
        if not isinstance(idempotency_key, str) or not idempotency_key.strip():
            raise ProcurementError("INVALID_PROCUREMENT_IDEMPOTENCY_KEY")
        with self.connection.transaction():
            row = self.connection.execute(
                "SELECT revision FROM project_procurement_revisions "
                "WHERE tenant_id=%s AND project_id=%s FOR UPDATE",
                (resource.tenant_id, resource.project_id),
            ).fetchone()
            if row is None:
                raise ProcurementError("PROCUREMENT_PROJECT_NOT_INITIALIZED")
            existing = self._find_idempotency(resource.tenant_id, resource.project_id, idempotency_key)
            fingerprint = resource.fingerprint()
            if existing is not None:
                old_fingerprint, old_json, old_revision = existing
                if old_fingerprint != fingerprint:
                    raise ProcurementIdempotencyReuse("PROCUREMENT_IDEMPOTENCY_KEY_REUSE")
                return StoredProcurementResource(_from_json(old_json), old_revision)
            current = row[0]
            if current != expected_project_revision:
                raise ProcurementRevisionConflict(
                    f"PROCUREMENT_REVISION_CONFLICT expected={expected_project_revision} actual={current}"
                )
            next_revision = current + 1
            payload = json.dumps({
                "tenant_id":resource.tenant_id,"project_id":resource.project_id,
                "resource_id":resource.resource_id,"revision":resource.revision,
                "resource_type":resource.resource_type.value,"status":resource.status.value,
                "actor_id":resource.actor_id,"occurred_at":resource.occurred_at,
                "payload":dict(resource.payload),
            },sort_keys=True,separators=(",",":"))
            self.connection.execute(
                "UPDATE project_procurement_revisions SET revision=%s "
                "WHERE tenant_id=%s AND project_id=%s AND revision=%s",
                (next_revision,resource.tenant_id,resource.project_id,current),
            )
            self.connection.execute(
                "INSERT INTO project_procurement_resources "
                "(tenant_id,project_id,resource_id,idempotency_key,fingerprint,project_revision,resource_json) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (resource.tenant_id,resource.project_id,resource.resource_id,idempotency_key,
                 fingerprint,next_revision,payload),
            )
            self.connection.execute(
                "INSERT INTO project_procurement_audit "
                "(tenant_id,project_id,resource_id,project_revision,actor_id,status,idempotency_key,occurred_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (resource.tenant_id,resource.project_id,resource.resource_id,next_revision,
                 resource.actor_id,resource.status.value,idempotency_key,resource.occurred_at),
            )
            return StoredProcurementResource(resource,next_revision)

    def get(self, tenant_id: str, project_id: str, resource_id: str) -> StoredProcurementResource | None:
        row = self.connection.execute(
            "SELECT resource_json, project_revision FROM project_procurement_resources "
            "WHERE tenant_id=%s AND project_id=%s AND resource_id=%s",
            (tenant_id,project_id,resource_id),
        ).fetchone()
        if row is None: return None
        return StoredProcurementResource(_from_json(row[0]),row[1])

    def _find_idempotency(self, tenant_id: str, project_id: str, key: str):
        row=self.connection.execute(
            "SELECT fingerprint, resource_json, project_revision FROM project_procurement_resources "
            "WHERE tenant_id=%s AND project_id=%s AND idempotency_key=%s",
            (tenant_id,project_id,key),
        ).fetchone()
        return None if row is None else (row[0],row[1],row[2])

def _from_json(payload: str) -> ProcurementResource:
    data=json.loads(payload)
    return ProcurementResource(
        tenant_id=data["tenant_id"],project_id=data["project_id"],resource_id=data["resource_id"],
        revision=int(data["revision"]),resource_type=ProcurementResourceType(data["resource_type"]),
        status=ProcurementStatus(data["status"]),actor_id=data["actor_id"],
        occurred_at=data["occurred_at"],payload=dict(data["payload"]),
    )
