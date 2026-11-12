from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .api_errors import APIError
from .application.authorization import AuthorizationContext
from .budget_application import BudgetApplicationService, CurrencyBudgetSummary
from .budget_persistence import (
    BudgetAuditEvent,
    BudgetChange,
    BudgetLine,
    FundingSource,
    StoredBudgetChange,
    StoredBudgetLine,
    StoredFundingSource,
    money_text,
)

BUDGET_API_VERSION = "p6-budget-api.v1"


@dataclass(frozen=True)
class BudgetAPI:
    """Thin versioned transport adapter over the budget application boundary."""

    service: BudgetApplicationService

    def list_lines(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
        currency: str | None = None,
        cost_account_id: str | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        try:
            return {
                "contract_version": BUDGET_API_VERSION,
                "budget_lines": [
                    _line(item)
                    for item in self.service.list_lines(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        context=context,
                        currency=currency,
                        cost_account_id=cost_account_id,
                        search=search,
                    )
                ],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def read_line(
        self,
        *,
        tenant_id: str,
        project_id: str,
        budget_line_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return _line(
                self.service.read_line(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    budget_line_id=budget_line_id,
                    context=context,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def create_line(
        self,
        line: BudgetLine,
        *,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            return _line(
                self.service.create_line(
                    line,
                    idempotency_key=idempotency_key,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def update_line(
        self,
        line: BudgetLine,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        audit_reason: str = "",
    ) -> dict[str, Any]:
        try:
            return _line(
                self.service.update_line(
                    line,
                    expected_revision=expected_revision,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                    audit_reason=audit_reason,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def list_changes(
        self,
        *,
        tenant_id: str,
        project_id: str,
        budget_line_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return {
                "contract_version": BUDGET_API_VERSION,
                "budget_line_id": budget_line_id,
                "changes": [
                    _change(item)
                    for item in self.service.list_changes(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        budget_line_id=budget_line_id,
                        context=context,
                    )
                ],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def create_change(
        self,
        change: BudgetChange,
        *,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            return _change(
                self.service.create_change(
                    change,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def transition_change(
        self,
        *,
        tenant_id: str,
        project_id: str,
        change_id: str,
        status: str,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        reason: str = "",
    ) -> dict[str, Any]:
        try:
            return _change(
                self.service.transition_change(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    change_id=change_id,
                    status=status,
                    expected_revision=expected_revision,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                    reason=reason,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def list_funding(
        self, *, tenant_id: str, project_id: str, context: AuthorizationContext
    ) -> dict[str, Any]:
        try:
            return {
                "contract_version": BUDGET_API_VERSION,
                "funding_sources": [
                    _funding(item)
                    for item in self.service.list_funding(
                        tenant_id=tenant_id, project_id=project_id, context=context
                    )
                ],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def create_funding(
        self,
        funding: FundingSource,
        *,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> dict[str, Any]:
        try:
            return _funding(
                self.service.create_funding(
                    funding,
                    idempotency_key=idempotency_key,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def update_funding(
        self,
        funding: FundingSource,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        audit_reason: str = "",
    ) -> dict[str, Any]:
        try:
            return _funding(
                self.service.update_funding(
                    funding,
                    expected_revision=expected_revision,
                    context=context,
                    actor_id=actor_id,
                    occurred_at=occurred_at,
                    audit_reason=audit_reason,
                )
            )
        except Exception as exc:
            return _error(self.service.error_dto(exc))

    def line_history(
        self,
        *,
        tenant_id: str,
        project_id: str,
        budget_line_id: str,
        context: AuthorizationContext,
    ) -> dict[str, Any]:
        try:
            return {
                "contract_version": BUDGET_API_VERSION,
                "budget_line_id": budget_line_id,
                "events": [
                    _event(item)
                    for item in self.service.line_history(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        budget_line_id=budget_line_id,
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
                "contract_version": BUDGET_API_VERSION,
                "currencies": [
                    _summary(item)
                    for item in self.service.summary(
                        tenant_id=tenant_id, project_id=project_id, context=context
                    )
                ],
            }
        except Exception as exc:
            return _error(self.service.error_dto(exc))


def _line(stored: StoredBudgetLine) -> dict[str, Any]:
    return {
        "contract_version": BUDGET_API_VERSION,
        "budget_line_id": stored.line.budget_line_id,
        "description": stored.line.description,
        "currency": stored.line.currency,
        "original_amount": money_text(stored.line.original_amount),
        "cost_account_id": stored.line.cost_account_id,
        "period_id": stored.line.period_id,
        "revision": stored.revision,
    }


def _change(stored: StoredBudgetChange) -> dict[str, Any]:
    return {
        "contract_version": BUDGET_API_VERSION,
        "change_id": stored.change.change_id,
        "budget_line_id": stored.change.budget_line_id,
        "amount": money_text(stored.change.amount),
        "reason": stored.change.reason,
        "status": stored.change.status,
        "revision": stored.revision,
    }


def _funding(stored: StoredFundingSource) -> dict[str, Any]:
    return {
        "contract_version": BUDGET_API_VERSION,
        "funding_id": stored.funding.funding_id,
        "name": stored.funding.name,
        "source_type": stored.funding.source_type,
        "currency": stored.funding.currency,
        "amount": money_text(stored.funding.amount),
        "period_id": stored.funding.period_id,
        "revision": stored.revision,
    }


def _summary(row: CurrencyBudgetSummary) -> dict[str, Any]:
    return {
        "currency": row.currency,
        "original_budget": money_text(row.original_budget),
        "approved_changes": money_text(row.approved_changes),
        "current_budget": money_text(row.current_budget),
        "pending_changes": money_text(row.pending_changes),
        "funding": money_text(row.funding),
        "funding_balance": money_text(row.funding_balance),
    }


def _event(event: BudgetAuditEvent) -> dict[str, Any]:
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
        "contract_version": BUDGET_API_VERSION,
        "category": error.category.value,
        "code": error.code,
        "message": error.message,
        "retryable": error.retryable,
    }
