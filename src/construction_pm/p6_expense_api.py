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
from .p6_expense_repository import P6Expense, P6ExpenseApplicationService

P6_EXPENSE_API_VERSION = "p6-expense-api.v1"


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


def _dto(expense: P6Expense) -> dict[str, Any]:
    def decimal(value: Any) -> str | None:
        return None if value is None else str(value)

    return {
        "contract_version": P6_EXPENSE_API_VERSION,
        "kind": "p6_expense",
        "scope": _scope_dto(expense.scope),
        "expense": {
            "expense_id": expense.expense_id,
            "name": expense.name,
            "category": expense.category,
            "activity_id": expense.activity_id,
            "wbs_id": expense.wbs_id,
            "expense_date": expense.expense_date,
            "planned_cost": decimal(expense.planned_cost),
            "actual_cost": decimal(expense.actual_cost),
            "remaining_cost": decimal(expense.remaining_cost),
            "currency": expense.currency,
            "note": expense.note,
        },
    }


@dataclass(frozen=True)
class P6ExpenseAPI:
    """Typed authorization/application boundary over authoritative P6 expense persistence."""

    service: P6ExpenseApplicationService
    authorization_policy: AuthorizationPolicy

    def create(self, expense: P6Expense, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        _require_scope(expense.scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_WRITE)
        return _dto(self.service.save(expense))

    def get(
        self,
        scope: BackendScope,
        expense_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, Any] | None:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        result = self.service.read(scope, expense_id)
        return None if result is None else _dto(result)

    def list(
        self,
        scope: BackendScope,
        *,
        activity_id: str | None = None,
        wbs_id: str | None = None,
        auth_context: AuthorizationContext,
    ) -> tuple[dict[str, Any], ...]:
        _require_scope(scope, auth_context)
        _require_permission(self.authorization_policy, auth_context, Permission.PROJECT_READ)
        return tuple(
            _dto(item)
            for item in self.service.list(scope, activity_id=activity_id, wbs_id=wbs_id)
        )


__all__ = ["P6_EXPENSE_API_VERSION", "P6ExpenseAPI"]
