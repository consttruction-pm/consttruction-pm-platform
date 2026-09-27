from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Mapping, Protocol


class ChangeClaimType(str, Enum):
    CHANGE = "change"
    VARIATION = "variation"
    NOTICE = "notice"
    CLAIM = "claim"


class ChangeClaimStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ChangeClaimError(ValueError):
    pass


class ChangeClaimConflict(ChangeClaimError):
    pass


@dataclass(frozen=True)
class ChangeClaim:
    tenant_id: str
    project_id: str
    resource_id: str
    revision: int
    resource_type: ChangeClaimType
    status: ChangeClaimStatus
    actor_id: str
    occurred_at: str
    payload: Mapping[str, object]
    evidence_refs: tuple[str, ...] = ()

    def fingerprint(self) -> str:
        canonical = json.dumps({
            "tenant_id": self.tenant_id, "project_id": self.project_id,
            "resource_id": self.resource_id, "revision": self.revision,
            "resource_type": self.resource_type.value, "status": self.status.value,
            "actor_id": self.actor_id, "occurred_at": self.occurred_at,
            "payload": dict(self.payload), "evidence_refs": list(self.evidence_refs),
        }, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()

    def validate(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id), ("project_id", self.project_id),
            ("resource_id", self.resource_id), ("actor_id", self.actor_id),
            ("occurred_at", self.occurred_at),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ChangeClaimError(f"INVALID_CHANGE_CLAIM_{name.upper()}")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 0:
            raise ChangeClaimError("INVALID_CHANGE_CLAIM_REVISION")
        if not isinstance(self.resource_type, ChangeClaimType):
            raise ChangeClaimError("INVALID_CHANGE_CLAIM_TYPE")
        if not isinstance(self.status, ChangeClaimStatus):
            raise ChangeClaimError("INVALID_CHANGE_CLAIM_STATUS")
        if not isinstance(self.payload, Mapping):
            raise ChangeClaimError("INVALID_CHANGE_CLAIM_PAYLOAD")
        if not isinstance(self.evidence_refs, tuple) or any(
            not isinstance(ref, str) or not ref.strip() for ref in self.evidence_refs
        ):
            raise ChangeClaimError("INVALID_CHANGE_CLAIM_EVIDENCE_REFS")


@dataclass(frozen=True)
class ChangeClaimAudit:
    tenant_id: str
    project_id: str
    resource_id: str
    revision: int
    actor_id: str
    status: ChangeClaimStatus
    idempotency_key: str
    fingerprint: str


class ChangeClaimRepository(Protocol):
    def get(self, tenant_id: str, project_id: str, resource_id: str) -> ChangeClaim | None: ...
    def put(self, resource: ChangeClaim) -> None: ...
    def append_audit(self, audit: ChangeClaimAudit) -> None: ...
    def get_idempotency(self, tenant_id: str, project_id: str, key: str) -> ChangeClaimAudit | None: ...
    def put_idempotency(self, audit: ChangeClaimAudit) -> None: ...


class InMemoryChangeClaimRepository:
    def __init__(self) -> None:
        self.resources: dict[tuple[str, str, str], ChangeClaim] = {}
        self.audits: list[ChangeClaimAudit] = []
        self.idempotency: dict[tuple[str, str, str], ChangeClaimAudit] = {}

    def get(self, tenant_id, project_id, resource_id):
        return self.resources.get((tenant_id, project_id, resource_id))

    def put(self, resource):
        resource.validate()
        self.resources[(resource.tenant_id, resource.project_id, resource.resource_id)] = resource

    def append_audit(self, audit):
        self.audits.append(audit)

    def get_idempotency(self, tenant_id, project_id, key):
        return self.idempotency.get((tenant_id, project_id, key))

    def put_idempotency(self, audit):
        self.idempotency[(audit.tenant_id, audit.project_id, audit.idempotency_key)] = audit


class ChangeClaimService:
    def __init__(self, repository: ChangeClaimRepository) -> None:
        self.repository = repository

    def upsert(
        self,
        resource: ChangeClaim,
        *,
        expected_revision: int,
        idempotency_key: str,
    ) -> ChangeClaim:
        resource.validate()
        if resource.revision != expected_revision:
            raise ChangeClaimConflict("CHANGE_CLAIM_REVISION_CONFLICT")
        existing_key = self.repository.get_idempotency(
            resource.tenant_id, resource.project_id, idempotency_key
        )
        if existing_key is not None:
            if existing_key.fingerprint != resource.fingerprint():
                raise ChangeClaimConflict("CHANGE_CLAIM_IDEMPOTENCY_KEY_REUSE")
            existing = self.repository.get(
                resource.tenant_id, resource.project_id, resource.resource_id
            )
            if existing is None:
                raise ChangeClaimConflict("CHANGE_CLAIM_IDEMPOTENCY_RECORD_MISSING")
            return existing
        current = self.repository.get(
            resource.tenant_id, resource.project_id, resource.resource_id
        )
        actual_revision = 0 if current is None else current.revision
        if actual_revision != expected_revision:
            raise ChangeClaimConflict("CHANGE_CLAIM_REVISION_CONFLICT")
        self.repository.put(resource)
        audit = ChangeClaimAudit(
            resource.tenant_id, resource.project_id, resource.resource_id,
            resource.revision, resource.actor_id, resource.status,
            idempotency_key, resource.fingerprint(),
        )
        self.repository.append_audit(audit)
        self.repository.put_idempotency(audit)
        return resource
