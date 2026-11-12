from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .api_errors import (
    APIError,
    authorization_error,
    conflict_error,
    validation_error,
)
from .application.authorization import (
    AuthorizationContext,
    AuthorizationPolicy,
    Permission,
)
from .cost_persistence import (
    CostAccount,
    CostAuditEvent,
    CostIdempotencyReuse,
    CostPersistenceError,
    CostRevisionConflict,
    CostStore,
    Expense,
    StoredCostAccount,
    StoredExpense,
)


class CostAuthorizationError(ValueError):
    pass


@dataclass(frozen=True)
class CurrencyExpenseSummary:
    currency: str
    planned_amount: Decimal
    actual_amount: Decimal
    remaining_amount: Decimal
    expense_count: int


@dataclass(frozen=True)
class CostApplicationService:
    """Authorization and derived-value boundary over stored cost facts."""

    store: CostStore
    authorization_policy: AuthorizationPolicy
    transaction_manager: object

    # -- reads ------------------------------------------------------------
    def list_accounts(
        self, *, tenant_id: str, project_id: str, context: AuthorizationContext
    ) -> tuple[StoredCostAccount, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.list_accounts(tenant_id, project_id)

    def read_account(
        self,
        *,
        tenant_id: str,
        project_id: str,
        account_id: str,
        context: AuthorizationContext,
    ) -> StoredCostAccount:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.get_account(tenant_id, project_id, account_id)

    def account_history(
        self,
        *,
        tenant_id: str,
        project_id: str,
        account_id: str,
        context: AuthorizationContext,
    ) -> tuple[CostAuditEvent, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.account_history(tenant_id, project_id, account_id)

    def list_expenses(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
        category: str | None = None,
        cost_account_id: str | None = None,
        activity_id: str | None = None,
        search: str | None = None,
    ) -> tuple[StoredExpense, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.list_expenses(
            tenant_id,
            project_id,
            category=category,
            cost_account_id=cost_account_id,
            activity_id=activity_id,
            search=search,
        )

    def read_expense(
        self,
        *,
        tenant_id: str,
        project_id: str,
        expense_id: str,
        context: AuthorizationContext,
    ) -> StoredExpense:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.get_expense(tenant_id, project_id, expense_id)

    def expense_history(
        self,
        *,
        tenant_id: str,
        project_id: str,
        expense_id: str,
        context: AuthorizationContext,
    ) -> tuple[CostAuditEvent, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.expense_history(tenant_id, project_id, expense_id)

    def summary(
        self, *, tenant_id: str, project_id: str, context: AuthorizationContext
    ) -> tuple[CurrencyExpenseSummary, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        grouped: dict[str, dict[str, Decimal | int]] = {}
        for stored in self.store.list_expenses(tenant_id, project_id):
            expense = stored.expense
            bucket = grouped.setdefault(
                expense.currency,
                {
                    "planned": Decimal("0"),
                    "actual": Decimal("0"),
                    "remaining": Decimal("0"),
                    "count": 0,
                },
            )
            bucket["planned"] = bucket["planned"] + (expense.planned_amount or Decimal("0"))
            bucket["actual"] = bucket["actual"] + (expense.actual_amount or Decimal("0"))
            bucket["remaining"] = bucket["remaining"] + (
                expense.remaining_amount or Decimal("0")
            )
            bucket["count"] = int(bucket["count"]) + 1
        return tuple(
            CurrencyExpenseSummary(
                currency=currency,
                planned_amount=grouped[currency]["planned"],  # type: ignore[arg-type]
                actual_amount=grouped[currency]["actual"],  # type: ignore[arg-type]
                remaining_amount=grouped[currency]["remaining"],  # type: ignore[arg-type]
                expense_count=int(grouped[currency]["count"]),
            )
            for currency in sorted(grouped)
        )

    # -- account writes ---------------------------------------------------
    def create_account(
        self,
        account: CostAccount,
        *,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredCostAccount:
        self._authorize_write(account.tenant_id, account.project_id, context, actor_id)
        with self.transaction_manager.transaction():
            return self.store.create_account(
                account,
                idempotency_key=idempotency_key,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )

    def update_account(
        self,
        account: CostAccount,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredCostAccount:
        self._authorize_write(account.tenant_id, account.project_id, context, actor_id)
        with self.transaction_manager.transaction():
            return self.store.update_account(
                account,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )

    def delete_account(
        self,
        *,
        tenant_id: str,
        project_id: str,
        account_id: str,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> None:
        self._authorize_write(tenant_id, project_id, context, actor_id)
        with self.transaction_manager.transaction():
            self.store.delete_account(
                tenant_id=tenant_id,
                project_id=project_id,
                account_id=account_id,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
                reason=reason,
            )

    def set_default_account(
        self,
        *,
        tenant_id: str,
        project_id: str,
        account_id: str,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> tuple[StoredCostAccount, ...]:
        self._authorize_write(tenant_id, project_id, context, actor_id)
        with self.transaction_manager.transaction():
            return self.store.set_default_account(
                tenant_id=tenant_id,
                project_id=project_id,
                account_id=account_id,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )

    def copy_account(
        self,
        *,
        tenant_id: str,
        project_id: str,
        source_account_id: str,
        account_id: str,
        name: str,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredCostAccount:
        self._authorize_write(tenant_id, project_id, context, actor_id)
        with self.transaction_manager.transaction():
            source = self.store.get_account(tenant_id, project_id, source_account_id)
            copy = CostAccount(
                tenant_id=tenant_id,
                project_id=project_id,
                account_id=account_id,
                name=name,
                parent_account_id=source.account.parent_account_id,
                description=source.account.description,
                is_default=False,
            )
            return self.store.create_account(
                copy,
                idempotency_key=idempotency_key,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )

    # -- expense writes ---------------------------------------------------
    def create_expense(
        self,
        expense: Expense,
        *,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredExpense:
        self._authorize_write(expense.tenant_id, expense.project_id, context, actor_id)
        with self.transaction_manager.transaction():
            return self.store.create_expense(
                expense,
                idempotency_key=idempotency_key,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )

    def update_expense(
        self,
        expense: Expense,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredExpense:
        self._authorize_write(expense.tenant_id, expense.project_id, context, actor_id)
        with self.transaction_manager.transaction():
            return self.store.update_expense(
                expense,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )

    def delete_expense(
        self,
        *,
        tenant_id: str,
        project_id: str,
        expense_id: str,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> None:
        self._authorize_write(tenant_id, project_id, context, actor_id)
        with self.transaction_manager.transaction():
            self.store.delete_expense(
                tenant_id=tenant_id,
                project_id=project_id,
                expense_id=expense_id,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
                reason=reason,
            )

    # -- helpers ----------------------------------------------------------
    def _check(
        self,
        context: AuthorizationContext,
        tenant_id: str,
        project_id: str,
        permission: Permission,
    ) -> None:
        if tenant_id != context.tenant_id or project_id != context.project_id:
            raise CostAuthorizationError("COST_CROSS_SCOPE_ACCESS")
        if not self.authorization_policy.is_allowed(context, permission):
            raise CostAuthorizationError("COST_PERMISSION_DENIED")

    def _authorize_write(
        self,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
        actor_id: str,
    ) -> None:
        if actor_id != context.user_id:
            raise CostAuthorizationError("COST_ACTOR_MISMATCH")
        self._check(context, tenant_id, project_id, Permission.PROJECT_WRITE)

    @staticmethod
    def error_dto(exc: Exception) -> APIError:
        if isinstance(exc, KeyError):
            code = str(exc.args[0]) if exc.args else "COST_NOT_FOUND"
            return validation_error(code, code)
        if isinstance(exc, CostRevisionConflict):
            return conflict_error("COST_REVISION_CONFLICT", str(exc), retryable=True)
        if isinstance(exc, CostIdempotencyReuse):
            return conflict_error("COST_IDEMPOTENCY_KEY_REUSE", str(exc))
        if isinstance(exc, CostAuthorizationError):
            return authorization_error(str(exc), str(exc))
        if isinstance(exc, CostPersistenceError):
            return validation_error(str(exc), str(exc))
        if isinstance(exc, ValueError):
            code = str(exc) or type(exc).__name__
            if code.endswith("_ALREADY_EXISTS") or code in {
                "COST_ACCOUNT_HAS_CHILDREN",
                "COST_ACCOUNT_IN_USE",
            }:
                return conflict_error(code, code)
            return validation_error(code, code)
        return validation_error(type(exc).__name__, str(exc))
