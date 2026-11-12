from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .api_errors import APIError
from .application.authorization import AuthorizationContext
from .cost_application import CostApplicationService, CurrencyExpenseSummary
from .cost_persistence import (
    CostAccount,
    CostAuditEvent,
    Expense,
    StoredCostAccount,
    StoredExpense,
    money_text,
)

COST_API_VERSION = "p6-cost-api.v1"


@dataclass(frozen=True)
class CostAPI:
    """Thin versioned transport adapter over the cost application boundary."""

    service: CostApplicationService

    # -- accounts ---------------------------------------------------------
    def list_accounts(
        self, *, tenant_id: str, project_id: str, context: AuthorizationContext
    ) -> dict[str, Any]:
        try:
            return {
                "contract_version": COST_API_VERSION,
                "cost_accounts": [
                    _account(item)
                    for item in self.service.list_accounts(
                        tenant_id=tenant_id, project_id=project_id, context=context
                    )
                ],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def read_account(
        self,
        *,
        tenant_id: str,
        project_id: str,
        account_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return _account(
                self.service.read_account(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    account_id=account_id,
                    context=context,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def create_account(
        self,
        account: CostAccount,
        *,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            return _account(
                self.service.create_account(
                    account,
                    idempotency_key=idempotency_key,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def update_account(
        self,
        account: CostAccount,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            return _account(
                self.service.update_account(
                    account,
                    expected_revision=expected_revision,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

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
    ) -> dict[str, Any]:
        try:
            self.service.delete_account(
                tenant_id=tenant_id,
                project_id=project_id,
                account_id=account_id,
                expected_revision=expected_revision,
                context=context,
                actor_id=actor_id,
                occurred_at=occurred_at,
                reason=reason,
            )
            return {
                "contract_version": COST_API_VERSION,
                "account_id": account_id,
                "deleted": True,
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

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
    ) -> dict[str, Any]:
        try:
            return {
                "contract_version": COST_API_VERSION,
                "cost_accounts": [
                    _account(item)
                    for item in self.service.set_default_account(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        account_id=account_id,
                        expected_revision=expected_revision,
                        context=context,
                        actor_id=actor_id,
                        occurred_at=occurred_at,
                    )
                ],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

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
    ) -> dict[str, Any]:
        try:
            return _account(
                self.service.copy_account(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    source_account_id=source_account_id,
                    account_id=account_id,
                    name=name,
                    idempotency_key=idempotency_key,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def account_history(
        self,
        *,
        tenant_id: str,
        project_id: str,
        account_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return {
                "contract_version": COST_API_VERSION,
                "account_id": account_id,
                "events": [
                    _event(item)
                    for item in self.service.account_history(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        account_id=account_id,
                        context=context,
                    )
                ],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    # -- expenses ---------------------------------------------------------
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
    ) -> dict[str, Any]:
        try:
            return {
                "contract_version": COST_API_VERSION,
                "expenses": [
                    _expense(item)
                    for item in self.service.list_expenses(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        context=context,
                        category=category,
                        cost_account_id=cost_account_id,
                        activity_id=activity_id,
                        search=search,
                    )
                ],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def read_expense(
        self,
        *,
        tenant_id: str,
        project_id: str,
        expense_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return _expense(
                self.service.read_expense(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    expense_id=expense_id,
                    context=context,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def create_expense(
        self,
        expense: Expense,
        *,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            return _expense(
                self.service.create_expense(
                    expense,
                    idempotency_key=idempotency_key,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def update_expense(
        self,
        expense: Expense,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            return _expense(
                self.service.update_expense(
                    expense,
                    expected_revision=expected_revision,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

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
    ) -> dict[str, Any]:
        try:
            self.service.delete_expense(
                tenant_id=tenant_id,
                project_id=project_id,
                expense_id=expense_id,
                expected_revision=expected_revision,
                context=context,
                actor_id=actor_id,
                occurred_at=occurred_at,
                reason=reason,
            )
            return {
                "contract_version": COST_API_VERSION,
                "expense_id": expense_id,
                "deleted": True,
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def expense_history(
        self,
        *,
        tenant_id: str,
        project_id: str,
        expense_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return {
                "contract_version": COST_API_VERSION,
                "expense_id": expense_id,
                "events": [
                    _event(item)
                    for item in self.service.expense_history(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        expense_id=expense_id,
                        context=context,
                    )
                ],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def summary(
        self, *, tenant_id: str, project_id: str, context: AuthorizationContext
    ) -> dict[str, Any]:
        try:
            return {
                "contract_version": COST_API_VERSION,
                "currencies": [
                    _summary(item)
                    for item in self.service.summary(
                        tenant_id=tenant_id, project_id=project_id, context=context
                    )
                ],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))


def _account(stored: StoredCostAccount) -> dict[str, Any]:
    return {
        "contract_version": COST_API_VERSION,
        "account_id": stored.account.account_id,
        "name": stored.account.name,
        "parent_account_id": stored.account.parent_account_id,
        "description": stored.account.description,
        "is_default": stored.account.is_default,
        "revision": stored.revision,
    }


def _expense(stored: StoredExpense) -> dict[str, Any]:
    expense = stored.expense
    return {
        "contract_version": COST_API_VERSION,
        "expense_id": expense.expense_id,
        "name": expense.name,
        "category": expense.category,
        "currency": expense.currency,
        "activity_id": expense.activity_id,
        "wbs_id": expense.wbs_id,
        "cost_account_id": expense.cost_account_id,
        "expense_date": expense.expense_date,
        "accrual_date": expense.accrual_date,
        "planned_amount": None
        if expense.planned_amount is None
        else money_text(expense.planned_amount),
        "actual_amount": None
        if expense.actual_amount is None
        else money_text(expense.actual_amount),
        "remaining_amount": None
        if expense.remaining_amount is None
        else money_text(expense.remaining_amount),
        "note": expense.note,
        "revision": stored.revision,
    }


def _summary(row: CurrencyExpenseSummary) -> dict[str, Any]:
    return {
        "currency": row.currency,
        "planned_amount": money_text(row.planned_amount),
        "actual_amount": money_text(row.actual_amount),
        "remaining_amount": money_text(row.remaining_amount),
        "expense_count": row.expense_count,
    }


def _event(event: CostAuditEvent) -> dict[str, Any]:
    return {
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "revision": event.revision,
        "event_type": event.event_type,
        "actor_id": event.actor_id,
        "occurred_at": event.occurred_at.isoformat(),
        "reason": event.reason,
    }


def _error(error: APIError) -> dict[str, Any]:
    error.validate()
    return {
        "contract_version": COST_API_VERSION,
        "category": error.category.value,
        "code": error.code,
        "message": error.message,
        "retryable": error.retryable,
    }
