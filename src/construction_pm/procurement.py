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
