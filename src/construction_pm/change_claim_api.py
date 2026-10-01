from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .change_claims import ChangeClaim, ChangeClaimRepository, ChangeClaimService, ChangeClaimStatus, ChangeClaimType

P0_CHANGE_CLAIM_API_VERSION = "p0-change-claim.v1"

class ChangeClaimAPIError(ValueError):
    pass

@dataclass(frozen=True)
class ChangeClaimCreateRequest:
    contract_version: str
    tenant_id: str
    project_id: str
    resource_id: str
    revision: int
    resource_type: ChangeClaimType
    status: ChangeClaimStatus
    actor_id: str
    occurred_at: datetime
    payload: Mapping[str, object]
    evidence_refs: tuple[str, ...]
    expected_revision: int
    idempotency_key: str

    def validate(self) -> None:
        if self.contract_version != P0_CHANGE_CLAIM_API_VERSION:
            raise ChangeClaimAPIError("UNSUPPORTED_CHANGE_CLAIM_API_VERSION")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ChangeClaimAPIError("CHANGE_CLAIM_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
        if isinstance(self.expected_revision, bool) or not isinstance(self.expected_revision, int) or self.expected_revision < 0:
            raise ChangeClaimAPIError("INVALID_CHANGE_CLAIM_EXPECTED_REVISION")
        if not isinstance(self.idempotency_key, str) or not self.idempotency_key.strip():
            raise ChangeClaimAPIError("INVALID_CHANGE_CLAIM_IDEMPOTENCY_KEY")

@dataclass(frozen=True)
class ChangeClaimReadRequest:
    contract_version: str
    tenant_id: str
    project_id: str
    resource_id: str

    def validate(self) -> None:
        if self.contract_version != P0_CHANGE_CLAIM_API_VERSION:
            raise ChangeClaimAPIError("UNSUPPORTED_CHANGE_CLAIM_API_VERSION")

@dataclass(frozen=True)
class ChangeClaimAPI:
    service: ChangeClaimService
    repository: ChangeClaimRepository
    authorization: AuthorizationPolicy

    def create(self, request: ChangeClaimCreateRequest, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        request.validate()
        auth_context.validate()
        self._require_scope(auth_context, request.tenant_id, request.project_id)
        if request.actor_id != auth_context.user_id:
            raise AuthorizationError("CHANGE_CLAIM_ACTOR_MISMATCH")
        self.authorization.require(auth_context, Permission.PROJECT_WRITE)
        resource = ChangeClaim(
            tenant_id=request.tenant_id, project_id=request.project_id, resource_id=request.resource_id,
            revision=request.revision, resource_type=request.resource_type, status=request.status,
            actor_id=request.actor_id, occurred_at=request.occurred_at.isoformat(),
            payload=dict(request.payload), evidence_refs=tuple(request.evidence_refs),
        )
        stored = self.service.upsert(resource, expected_revision=request.expected_revision, idempotency_key=request.idempotency_key)
        return self._serialize(stored)

    def get(self, request: ChangeClaimReadRequest, *, auth_context: AuthorizationContext) -> dict[str, Any] | None:
        request.validate()
        auth_context.validate()
        self._require_scope(auth_context, request.tenant_id, request.project_id)
        self.authorization.require(auth_context, Permission.PROJECT_READ)
        resource = self.repository.get(request.tenant_id, request.project_id, request.resource_id)
        if resource is None:
            return None
        # PostgreSQL returns its atomic persistence envelope; the API exposes the domain resource.
        resource = getattr(resource, "resource", resource)
        return self._serialize(resource)

    @staticmethod
    def _require_scope(auth_context: AuthorizationContext, tenant_id: str, project_id: str) -> None:
        if auth_context.tenant_id != tenant_id or auth_context.project_id != project_id:
            raise AuthorizationError("CHANGE_CLAIM_SCOPE_MISMATCH")

    @staticmethod
    def _serialize(resource: ChangeClaim) -> dict[str, Any]:
        return {
            "contract_version": P0_CHANGE_CLAIM_API_VERSION,
            "tenant_id": resource.tenant_id, "project_id": resource.project_id,
            "resource_id": resource.resource_id, "revision": resource.revision,
            "resource_type": resource.resource_type.value, "status": resource.status.value,
            "actor_id": resource.actor_id, "occurred_at": resource.occurred_at,
            "payload": dict(resource.payload), "evidence_refs": list(resource.evidence_refs),
        }
