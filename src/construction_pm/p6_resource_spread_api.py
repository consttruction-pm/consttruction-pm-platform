from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .p6_resource_spread_repository import (
    P6ResourceSpreadApplicationService,
    P6ResourceSpreadBucket,
)

P6_RESOURCE_SPREAD_API_VERSION = "p6-resource-spread-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _scope_dto(scope: BackendScope) -> dict[str, Any]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


@dataclass(frozen=True)
class P6ResourceSpreadAPI:
    """Versioned persistence boundary for P6 resource-spread buckets.

    Resource demand, leveling, rates, calendar conversion and cost semantics
    remain authoritative in Shared Core; this API only persists typed buckets.
    """

    spread_service: P6ResourceSpreadApplicationService
    authorization_policy: AuthorizationPolicy

    def list(
        self,
        scope: BackendScope,
        *,
        spread_id: str | None = None,
        auth_context: AuthorizationContext,
    ) -> list[dict[str, Any]]:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise AuthorizationError("RESOURCE_SPREAD_READ_NOT_AUTHORIZED")
        return [_bucket_dto(item) for item in self.spread_service.list(scope, spread_id)]

    def get(
        self,
        scope: BackendScope,
        spread_id: str,
        period_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise AuthorizationError("RESOURCE_SPREAD_READ_NOT_AUTHORIZED")
        item = self.spread_service.read(scope, spread_id, period_id)
        return None if item is None else _bucket_dto(item)

    def save(
        self,
        bucket: P6ResourceSpreadBucket,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(bucket.scope, auth_context)
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_WRITE):
            raise AuthorizationError("RESOURCE_SPREAD_WRITE_NOT_AUTHORIZED")
        return _bucket_dto(self.spread_service.save(bucket))


def _bucket_dto(item: P6ResourceSpreadBucket) -> dict[str, Any]:
    result: dict[str, Any] = {
        "contract_version": P6_RESOURCE_SPREAD_API_VERSION,
        "kind": "p6_resource_spread_bucket",
        "scope": _scope_dto(item.scope),
        "spread": {
            "spread_id": item.spread_id,
            "resource_id": item.resource_id,
            "period_id": item.period_id,
            "period_start": item.period_start,
            "period_end": item.period_end,
            "spread_type": item.spread_type,
            "metric": item.metric,
            "value": str(item.value),
            "unit": item.unit,
            "currency": item.currency,
        },
    }
    return result


__all__ = ["P6_RESOURCE_SPREAD_API_VERSION", "P6ResourceSpreadAPI"]
