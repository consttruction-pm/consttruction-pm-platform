"""Authorized read boundary for effective-dated resource rate facts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .p6_resource_rate_repository import (
    P6ResourceRateApplicationService,
    P6ResourceRateRecord,
)
from .resources.rate_facts import ResourceRateFactError, ResourceRateProfile

P6_RESOURCE_RATE_READ_API_VERSION = "p6-resource-rate-read-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _require_read(
    policy: AuthorizationPolicy, auth_context: AuthorizationContext
) -> None:
    if not policy.is_allowed(auth_context, Permission.PROJECT_READ):
        raise AuthorizationError("RESOURCE_RATE_READ_NOT_AUTHORIZED")


def _scope_dto(scope: BackendScope) -> dict[str, Any]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


def _rate_dto(record: P6ResourceRateRecord) -> dict[str, Any]:
    fact = record.fact
    return {
        "resource_id": fact.resource_id,
        "identity": fact.identity,
        "rate": fact.rate,
        "basis": fact.basis.value,
        "currency": fact.currency,
        "unit": fact.unit,
        "effective_from": fact.effective_from.isoformat(),
        "effective_to": None
        if fact.effective_to is None
        else fact.effective_to.isoformat(),
        "source": fact.source,
    }


@dataclass(frozen=True)
class P6ResourceRateReadAPI:
    service: P6ResourceRateApplicationService
    authorization_policy: AuthorizationPolicy

    def list_rates(
        self,
        scope: BackendScope,
        resource_id: str | None,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_read(self.authorization_policy, auth_context)
        return tuple(
            _rate_dto(record) for record in self.service.list(scope, resource_id)
        )

    def get_profile(
        self,
        scope: BackendScope,
        resource_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        _require_read(self.authorization_policy, auth_context)
        records = self.service.list(scope, resource_id)
        if not records:
            raise ResourceRateFactError("RESOURCE_RATE_NOT_REGISTERED")
        ResourceRateProfile(resource_id, tuple(record.fact for record in records))
        return {
            "contract_version": P6_RESOURCE_RATE_READ_API_VERSION,
            "kind": "resource_rate_profile",
            "scope": _scope_dto(scope),
            "resource_id": resource_id,
            "rates": [_rate_dto(record) for record in records],
            "status": "REGISTERED",
        }

    def rate_on(
        self,
        scope: BackendScope,
        resource_id: str,
        period: date,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        _require_read(self.authorization_policy, auth_context)
        records = self.service.list(scope, resource_id)
        if not records:
            raise ResourceRateFactError("RESOURCE_RATE_NOT_REGISTERED")
        profile = ResourceRateProfile(
            resource_id, tuple(record.fact for record in records)
        )
        fact = profile.fact_on(period)
        return {
            "contract_version": P6_RESOURCE_RATE_READ_API_VERSION,
            "kind": "resource_rate_value",
            "scope": _scope_dto(scope),
            "resource_id": resource_id,
            "period": period.isoformat(),
            "rate": fact.rate,
            "basis": fact.basis.value,
            "currency": fact.currency,
            "unit": fact.unit,
            "source": fact.source,
            "identity": fact.identity,
            "status": "RESOLVED",
        }


__all__ = [
    "P6_RESOURCE_RATE_READ_API_VERSION",
    "P6ResourceRateReadAPI",
]
