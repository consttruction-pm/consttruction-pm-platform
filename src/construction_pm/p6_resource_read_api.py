from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .backend_p0.models import BackendScope
from .p6_resource_assignment_repository import (
    P6ResourceAssignment,
    P6ResourceAssignmentApplicationService,
    P6ResourceAssignmentPeriodApplicationService,
    P6ResourceAssignmentPeriodValue,
)
from .p6_resource_spread_repository import P6ResourceSpreadApplicationService, P6ResourceSpreadBucket

P6_RESOURCE_READ_API_VERSION = "p6-resource-read-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _require_read(policy: AuthorizationPolicy, auth_context: AuthorizationContext) -> None:
    if not policy.is_allowed(auth_context, Permission.PROJECT_READ):
        raise AuthorizationError("RESOURCE_READ_NOT_AUTHORIZED")


@dataclass(frozen=True)
class P6ResourceReadAPI:
    """Read-only transport boundary over authoritative resource persistence."""

    assignment_service: P6ResourceAssignmentApplicationService
    period_service: P6ResourceAssignmentPeriodApplicationService
    spread_service: P6ResourceSpreadApplicationService
    authorization_policy: AuthorizationPolicy

    def get_assignment(self, scope: BackendScope, assignment_id: str, *, auth_context: AuthorizationContext) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        _require_read(self.authorization_policy, auth_context)
        item = self.assignment_service.read(scope, assignment_id)
        return None if item is None else _assignment_dto(item)

    def list_assignments(
        self, scope: BackendScope, *, activity_id: str | None = None,
        resource_id: str | None = None, auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_read(self.authorization_policy, auth_context)
        return tuple(_assignment_dto(item) for item in self.assignment_service.list(scope, activity_id, resource_id))

    def get_assignment_period(
        self, scope: BackendScope, assignment_id: str, period_start: str, *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        _require_read(self.authorization_policy, auth_context)
        item = self.period_service.read(scope, assignment_id, period_start)
        return None if item is None else _period_dto(item)

    def list_assignment_periods(
        self, scope: BackendScope, *, assignment_id: str | None = None,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_read(self.authorization_policy, auth_context)
        return tuple(_period_dto(item) for item in self.period_service.list(scope, assignment_id))

    def get_spread(
        self, scope: BackendScope, spread_id: str, period_id: str, *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        _require_read(self.authorization_policy, auth_context)
        item = self.spread_service.read(scope, spread_id, period_id)
        return None if item is None else _spread_dto(item)

    def list_spreads(
        self, scope: BackendScope, *, spread_id: str | None = None,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_read(self.authorization_policy, auth_context)
        return tuple(_spread_dto(item) for item in self.spread_service.list(scope, spread_id))


def _scope_dto(scope: BackendScope) -> dict[str, Any]:
    return {"tenant_id": scope.tenant_id, "project_id": scope.project_id, "project_revision": scope.project_revision}


def _assignment_dto(item: P6ResourceAssignment) -> dict[str, Any]:
    return {
        "contract_version": P6_RESOURCE_READ_API_VERSION,
        "kind": "resource_assignment",
        "scope": _scope_dto(item.scope),
        "assignment": {
            "assignment_id": item.assignment_id, "activity_id": item.activity_id,
            "resource_id": item.resource_id, "role_id": item.role_id,
            "units": item.units, "actual_units": item.actual_units, "remaining_units": item.remaining_units,
            "planned_cost": item.planned_cost, "actual_cost": item.actual_cost, "remaining_cost": item.remaining_cost,
            "unit": item.unit, "currency": item.currency, "calendar_id": item.calendar_id, "note": item.note,
        },
    }


def _period_dto(item: P6ResourceAssignmentPeriodValue) -> dict[str, Any]:
    return {
        "contract_version": P6_RESOURCE_READ_API_VERSION,
        "kind": "resource_assignment_period",
        "scope": _scope_dto(item.scope),
        "period": {
            "assignment_id": item.assignment_id, "activity_id": item.activity_id,
            "resource_id": item.resource_id, "period_start": item.period_start,
            "units": item.units, "cost": item.cost,
        },
    }


def _spread_dto(item: P6ResourceSpreadBucket) -> dict[str, Any]:
    return {
        "contract_version": P6_RESOURCE_READ_API_VERSION,
        "kind": "resource_spread_bucket",
        "scope": _scope_dto(item.scope),
        "spread": {
            "spread_id": item.spread_id, "resource_id": item.resource_id,
            "period_id": item.period_id, "period_start": item.period_start, "period_end": item.period_end,
            "spread_type": item.spread_type, "metric": item.metric, "value": item.value,
            "unit": item.unit, "currency": item.currency,
        },
    }


__all__ = ["P6_RESOURCE_READ_API_VERSION", "P6ResourceReadAPI"]
