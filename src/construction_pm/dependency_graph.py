from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Protocol

class DependencyType(str,Enum):
    FINISH_TO_START="finish_to_start"; START_TO_START="start_to_start"
    FINISH_TO_FINISH="finish_to_finish"; START_TO_FINISH="start_to_finish"

class DependencyGraphError(ValueError): pass
class DependencyGraphConflict(DependencyGraphError): pass

@dataclass(frozen=True)
class DependencyEdge:
    tenant_id:str; project_id:str; edge_id:str; revision:int
    source_ref:str; target_ref:str; dependency_type:DependencyType; actor_id:str
    def fingerprint(self)->str:
        value=json.dumps(self.__dict__|{"dependency_type":self.dependency_type.value},sort_keys=True,separators=(",",":"))
        return sha256(value.encode()).hexdigest()
    def validate(self)->None:
        for n,v in (("tenant_id",self.tenant_id),("project_id",self.project_id),
                    ("edge_id",self.edge_id),("source_ref",self.source_ref),
                    ("target_ref",self.target_ref),("actor_id",self.actor_id)):
            if not isinstance(v,str) or not v.strip(): raise DependencyGraphError(f"INVALID_DEPENDENCY_{n.upper()}")
        if self.source_ref==self.target_ref: raise DependencyGraphError("INVALID_DEPENDENCY_SELF_REFERENCE")
        if isinstance(self.revision,bool) or not isinstance(self.revision,int) or self.revision<0:
            raise DependencyGraphError("INVALID_DEPENDENCY_REVISION")
        if not isinstance(self.dependency_type,DependencyType): raise DependencyGraphError("INVALID_DEPENDENCY_TYPE")

@dataclass(frozen=True)
class DependencyAudit:
    tenant_id:str; project_id:str; edge_id:str; revision:int; actor_id:str
    idempotency_key:str; fingerprint:str

class DependencyRepository(Protocol):
    def get(self,tenant_id:str,project_id:str,edge_id:str)->DependencyEdge|None: ...
    def put(self,edge:DependencyEdge)->None: ...
    def append_audit(self,audit:DependencyAudit)->None: ...
    def get_idempotency(self,tenant_id:str,project_id:str,key:str)->DependencyAudit|None: ...
    def put_idempotency(self,audit:DependencyAudit)->None: ...

class InMemoryDependencyRepository:
    def __init__(self): self.edges={}; self.audits=[]; self.idempotency={}
    def get(self,t,p,e): return self.edges.get((t,p,e))
    def put(self,e): e.validate(); self.edges[(e.tenant_id,e.project_id,e.edge_id)]=e
    def append_audit(self,a): self.audits.append(a)
    def get_idempotency(self,t,p,k): return self.idempotency.get((t,p,k))
    def put_idempotency(self,a): self.idempotency[(a.tenant_id,a.project_id,a.idempotency_key)]=a

class DependencyGraphService:
    def __init__(self,repository:DependencyRepository): self.repository=repository
    def upsert(self,edge:DependencyEdge,*,expected_revision:int,idempotency_key:str)->DependencyEdge:
        edge.validate()
        if edge.revision!=expected_revision: raise DependencyGraphConflict("DEPENDENCY_REVISION_CONFLICT")
        existing=self.repository.get_idempotency(edge.tenant_id,edge.project_id,idempotency_key)
        if existing:
            if existing.fingerprint!=edge.fingerprint(): raise DependencyGraphConflict("DEPENDENCY_IDEMPOTENCY_KEY_REUSE")
            current=self.repository.get(edge.tenant_id,edge.project_id,edge.edge_id)
            if current is None: raise DependencyGraphConflict("DEPENDENCY_IDEMPOTENCY_RECORD_MISSING")
            return current
        current=self.repository.get(edge.tenant_id,edge.project_id,edge.edge_id)
        actual=0 if current is None else current.revision
        if actual!=expected_revision: raise DependencyGraphConflict("DEPENDENCY_REVISION_CONFLICT")
        self.repository.put(edge)
        audit=DependencyAudit(edge.tenant_id,edge.project_id,edge.edge_id,edge.revision,edge.actor_id,idempotency_key,edge.fingerprint())
        self.repository.append_audit(audit); self.repository.put_idempotency(audit)
        return edge
