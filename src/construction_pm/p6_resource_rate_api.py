from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .p6_resource_rate_repository import (
    P6ResourceRatePersistenceError,
    P6ResourceRateRepository,
)
from .scheduling.resource_leveling_input import ResourceCapacityRate

P6_RESOURCE_RATE_API_VERSION = "p6-resource-rate-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _rate_dto(scope: BackendScope, rate: ResourceCapacityRate) -> dict[str, Any]:
    return {
        "contract_version": P6_RESOURCE_RATE_API_VERSION,
        "kind": "resource_capacity_rate",
        "scope": {
            "tenant_id": scope.tenant_id,
            "project_id": scope.project_id,
            "project_revision": scope.project_revision,
        },
        "rate": rate.canonical_payload(),
        "profile_hash": rate.profile_hash,
    }


@dataclass(frozen=True)
class P6ResourceRateAPI:
    """Authenticated read/write boundary for immutable, revision-scoped Max Units/Time facts."""

    repository: P6ResourceRateRepository
    authorization_policy: AuthorizationPolicy

    def list_rates(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
        resource_id: str | None = None,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise AuthorizationError("RESOURCE_RATE_READ_NOT_AUTHORIZED")
        rates = self.repository.list(scope, resource_id)
        return {
            "contract_version": P6_RESOURCE_RATE_API_VERSION,
            "kind": "resource_capacity_rate_collection",
            "scope": {
                "tenant_id": scope.tenant_id,
                "project_id": scope.project_id,
                "project_revision": scope.project_revision,
            },
            "items": [_rate_dto(scope, rate) for rate in rates],
        }

    def save_rate(
        self,
        scope: BackendScope,
        rate: ResourceCapacityRate,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_WRITE):
            raise AuthorizationError("RESOURCE_RATE_WRITE_NOT_AUTHORIZED")
        if not isinstance(rate, ResourceCapacityRate):
            raise P6ResourceRatePersistenceError("INVALID_RESOURCE_RATE")
        rate.validate()
        stored = self.repository.save(scope, rate)
        return _rate_dto(scope, stored)


__all__ = ["P6_RESOURCE_RATE_API_VERSION", "P6ResourceRateAPI"]
