"""Authorized read boundary for typed effective-dated resource capacity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from .application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    AuthorizationPolicy,
    Permission,
)
from .backend_p0.models import BackendScope
from .p6_resource_capacity_repository import (
    P6ResourceCapacityApplicationService,
    P6ResourceCapacityRecord,
)
from .resources.max_units_time import (
    ResourceCapacityBasis,
    ResourceCapacityError,
    ResourceMaxUnitsTimeProfile,
)

P6_RESOURCE_CAPACITY_READ_API_VERSION = "p6-resource-capacity-read-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _require_read(
    policy: AuthorizationPolicy, auth_context: AuthorizationContext
) -> None:
    if not policy.is_allowed(auth_context, Permission.PROJECT_READ):
        raise AuthorizationError("RESOURCE_CAPACITY_READ_NOT_AUTHORIZED")


def _scope_dto(scope: BackendScope) -> dict[str, Any]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


def _segment_dto(record: P6ResourceCapacityRecord) -> dict[str, Any]:
    segment = record.segment
    return {
        "contract_version": P6_RESOURCE_CAPACITY_READ_API_VERSION,
        "kind": "resource_capacity_segment",
        "scope": _scope_dto(record.scope),
        "capacity": {
            "resource_id": segment.resource_id,
            "identity": segment.identity,
            "max_units": segment.max_units,
            "unit_basis": segment.unit_basis.value,
            "hours_per_time_period": segment.hours_per_time_period,
            "units_per_hour": segment.units_per_hour,
            "effective_from": segment.effective_from.isoformat(),
            "effective_to": None
            if segment.effective_to is None
            else segment.effective_to.isoformat(),
            "source": segment.source,
        },
    }


@dataclass(frozen=True)
class P6ResourceCapacityReadAPI:
    service: P6ResourceCapacityApplicationService
    authorization_policy: AuthorizationPolicy

    def list_segments(
        self,
        scope: BackendScope,
        resource_id: str | None,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_read(self.authorization_policy, auth_context)
        return tuple(
            _segment_dto(record)
            for record in self.service.list(scope, resource_id)
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
            raise ResourceCapacityError("RESOURCE_CAPACITY_NOT_REGISTERED")
        profile = ResourceMaxUnitsTimeProfile(
            resource_id, tuple(record.segment for record in records)
        )
        return {
            "contract_version": P6_RESOURCE_CAPACITY_READ_API_VERSION,
            "kind": "resource_capacity_profile",
            "scope": _scope_dto(scope),
            "resource_id": resource_id,
            "segments": [_segment_dto(record)["capacity"] for record in records],
            "status": "REGISTERED",
        }

    def capacity_on(
        self,
        scope: BackendScope,
        resource_id: str,
        period: date,
        *,
        basis: ResourceCapacityBasis | None = None,
        hours_per_time_period: Decimal | None = None,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(scope, auth_context)
        _require_read(self.authorization_policy, auth_context)
        records = self.service.list(scope, resource_id)
        if not records:
            raise ResourceCapacityError("RESOURCE_CAPACITY_NOT_REGISTERED")
        profile = ResourceMaxUnitsTimeProfile(
            resource_id, tuple(record.segment for record in records)
        )
        segment = profile.segment_on(period)
        converted = profile.capacity_on(
            period,
            basis=basis,
            hours_per_time_period=hours_per_time_period,
        )
        return {
            "contract_version": P6_RESOURCE_CAPACITY_READ_API_VERSION,
            "kind": "resource_capacity_value",
            "scope": _scope_dto(scope),
            "resource_id": resource_id,
            "period": period.isoformat(),
            "capacity": converted,
            "basis": None if basis is None else basis.value,
            "source": segment.source,
            "identity": segment.identity,
            "status": "RESOLVED",
        }


__all__ = [
    "P6_RESOURCE_CAPACITY_READ_API_VERSION",
    "P6ResourceCapacityReadAPI",
]
