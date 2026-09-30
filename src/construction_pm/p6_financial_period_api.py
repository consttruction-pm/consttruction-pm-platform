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
from .p6_financial_period_repository import (
    P6FinancialPeriod,
    P6FinancialPeriodApplicationService,
)

P6_FINANCIAL_PERIOD_API_VERSION = "p6-financial-period-api.v1"


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


def _dto(period: P6FinancialPeriod) -> dict[str, Any]:
    return {
        "contract_version": P6_FINANCIAL_PERIOD_API_VERSION,
        "kind": "p6_financial_period",
        "scope": _scope_dto(period.scope),
        "financial_period": {
            "period_id": period.period_id,
            "name": period.name,
            "start_date": period.start_date,
            "end_date": period.end_date,
            "status": period.status,
        },
    }


@dataclass(frozen=True)
class P6FinancialPeriodAPI:
    """Typed transport boundary over authoritative financial-period persistence."""

    service: P6FinancialPeriodApplicationService
    authorization_policy: AuthorizationPolicy

    def create(
        self,
        period: P6FinancialPeriod,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(period.scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        return _dto(self.service.save(period))

    def get(
        self,
        scope: BackendScope,
        period_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        result = self.service.read(scope, period_id)
        return None if result is None else _dto(result)

    def list(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        return tuple(_dto(item) for item in self.service.list(scope))


__all__ = ["P6_FINANCIAL_PERIOD_API_VERSION", "P6FinancialPeriodAPI"]
