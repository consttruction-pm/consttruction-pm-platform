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
from .p6_cost_account_repository import P6CostAccount, P6CostAccountApplicationService

P6_COST_ACCOUNT_API_VERSION = "p6-cost-account-api.v1"


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


def _dto(account: P6CostAccount) -> dict[str, Any]:
    return {
        "contract_version": P6_COST_ACCOUNT_API_VERSION,
        "kind": "p6_cost_account",
        "scope": {
            "tenant_id": account.scope.tenant_id,
            "project_id": account.scope.project_id,
            "project_revision": account.scope.project_revision,
        },
        "cost_account": {
            "account_id": account.account_id,
            "name": account.name,
            "parent_account_id": account.parent_account_id,
            "description": account.description,
        },
    }


@dataclass(frozen=True)
class P6CostAccountAPI:
    """Versioned, scoped API over authoritative P6 cost-account persistence."""

    service: P6CostAccountApplicationService
    authorization_policy: AuthorizationPolicy

    def create(
        self,
        account: P6CostAccount,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any]:
        _require_scope(account.scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        return _dto(self.service.save(account))

    def get(
        self,
        scope: BackendScope,
        account_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        account = self.service.read(scope, account_id)
        return None if account is None else _dto(account)

    def list(
        self,
        scope: BackendScope,
        *,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        return tuple(_dto(account) for account in self.service.list(scope))


__all__ = ["P6_COST_ACCOUNT_API_VERSION", "P6CostAccountAPI"]
