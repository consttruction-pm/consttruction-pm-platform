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
from .p6_activity_period_actual_repository import (
    P6ActivityPeriodActual,
    P6ActivityPeriodActualApplicationService,
)

P6_ACTIVITY_PERIOD_ACTUAL_API_VERSION = "p6-activity-period-actual-api.v1"


def _require_scope(scope: BackendScope, auth_context: AuthorizationContext) -> None:
    scope.validate()
    auth_context.validate()
    if scope.tenant_id != auth_context.tenant_id or scope.project_id != auth_context.project_id:
        raise AuthorizationError("CROSS_SCOPE_ACCESS")


def _require_permission(
    policy: AuthorizationPolicy,
    auth_context: AuthorizationContext,
    permission: Permission,
) -> None:
    if not policy.is_allowed(auth_context, permission):
        raise AuthorizationError(f"authorization denied for permission={permission.value}")


def _scope_dto(scope: BackendScope) -> dict[str, Any]:
    return {
        "tenant_id": scope.tenant_id,
        "project_id": scope.project_id,
        "project_revision": scope.project_revision,
    }


def _dto(actual: P6ActivityPeriodActual) -> dict[str, Any]:
    return {
        "contract_version": P6_ACTIVITY_PERIOD_ACTUAL_API_VERSION,
        "kind": "p6_activity_period_actual",
        "scope": _scope_dto(actual.scope),
        "activity_period_actual": {
            "actual_id": actual.actual_id,
            "activity_id": actual.activity_id,
            "period_id": actual.period_id,
            "actual_units": None if actual.actual_units is None else str(actual.actual_units),
            "actual_cost": None if actual.actual_cost is None else str(actual.actual_cost),
            "unit": actual.unit,
            "currency": actual.currency,
            "note": actual.note,
        },
    }


@dataclass(frozen=True)
class P6ActivityPeriodActualAPI:
    """Typed transport boundary over authoritative activity-period actual persistence."""

    service: P6ActivityPeriodActualApplicationService
    authorization_policy: AuthorizationPolicy

    def create(
        self,
        actual: P6ActivityPeriodActual,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(actual.scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        return _dto(self.service.save(actual))

    def get(
        self,
        scope: BackendScope,
        actual_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        result = self.service.read(scope, actual_id)
        return None if result is None else _dto(result)

    def list(
        self,
        scope: BackendScope,
        *,
        activity_id: str | None = None,
        period_id: str | None = None,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        return tuple(
            _dto(item)
            for item in self.service.list(
                scope,
                activity_id=activity_id,
                period_id=period_id,
            )
        )


__all__ = ["P6_ACTIVITY_PERIOD_ACTUAL_API_VERSION", "P6ActivityPeriodActualAPI"]
