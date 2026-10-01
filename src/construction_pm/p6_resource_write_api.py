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
from .p6_resource_assignment_repository import (
    P6ResourceAssignmentPeriodApplicationService,
    P6ResourceAssignmentPeriodValue,
)

P6_RESOURCE_WRITE_API_VERSION = "p6-resource-write-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _require_write(policy: AuthorizationPolicy, auth_context: AuthorizationContext) -> None:
    if not policy.is_allowed(auth_context, Permission.PROJECT_WRITE):
        raise AuthorizationError("RESOURCE_WRITE_NOT_AUTHORIZED")


def _scope_dto(scope: BackendScope) -> dict[str, Any]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


@dataclass(frozen=True)
class P6ResourceWriteAPI:
    """Versioned write boundary over authoritative resource persistence."""

    period_service: P6ResourceAssignmentPeriodApplicationService
    authorization_policy: AuthorizationPolicy

    def save_assignment_period(
        self,
        value: P6ResourceAssignmentPeriodValue,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(value.scope, auth_context)
        _require_write(self.authorization_policy, auth_context)
        stored = self.period_service.save(value)
        return _period_dto(stored)


def _period_dto(item: P6ResourceAssignmentPeriodValue) -> dict[str, Any]:
    return {
        "contract_version": P6_RESOURCE_WRITE_API_VERSION,
        "kind": "resource_assignment_period",
        "scope": _scope_dto(item.scope),
        "period": {
            "assignment_id": item.assignment_id,
            "activity_id": item.activity_id,
            "resource_id": item.resource_id,
            "period_start": item.period_start,
            "units": item.units,
            "cost": item.cost,
        },
    }


__all__ = ["P6_RESOURCE_WRITE_API_VERSION", "P6ResourceWriteAPI"]
