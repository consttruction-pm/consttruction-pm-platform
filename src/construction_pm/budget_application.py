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
from .budget_persistence import (
    BudgetAuditEvent,
    BudgetChange,
    BudgetIdempotencyReuse,
    BudgetLine,
    BudgetRevisionConflict,
    BudgetStore,
    FundingSource,
    StoredBudgetChange,
    StoredBudgetLine,
    StoredFundingSource,
)


class BudgetAuthorizationError(ValueError):
    pass


@dataclass(frozen=True)
class CurrencyBudgetSummary:
    currency: str
    original_budget: Decimal
    approved_changes: Decimal
    current_budget: Decimal
    pending_changes: Decimal
    funding: Decimal
    funding_balance: Decimal


@dataclass(frozen=True)
class BudgetApplicationService:
    """Authorization and derived-value boundary over stored budget facts."""

    store: BudgetStore
    authorization_policy: AuthorizationPolicy
    transaction_manager: object
    approver_roles: frozenset[str] = frozenset({"project_admin"})

    # -- reads ------------------------------------------------------------
    def list_lines(
        self,
        *,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
        currency: str | None = None,
        cost_account_id: str | None = None,
        search: str | None = None,
    ) -> tuple[StoredBudgetLine, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.list_lines(
            tenant_id,
            project_id,
            currency=currency,
            cost_account_id=cost_account_id,
            search=search,
        )

    def read_line(
        self, *, tenant_id: str, project_id: str, budget_line_id: str, context: AuthorizationContext
    ) -> StoredBudgetLine:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.get_line(tenant_id, project_id, budget_line_id)

    def list_changes(
        self,
        *,
        tenant_id: str,
        project_id: str,
        budget_line_id: str,
        context: AuthorizationContext,
    ) -> tuple[StoredBudgetChange, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        self.store.get_line(tenant_id, project_id, budget_line_id)
        return self.store.list_changes(tenant_id, project_id, budget_line_id)

    def list_funding(
        self, *, tenant_id: str, project_id: str, context: AuthorizationContext
    ) -> tuple[StoredFundingSource, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.list_funding(tenant_id, project_id)

    def line_history(
        self,
        *,
        tenant_id: str,
        project_id: str,
        budget_line_id: str,
        context: AuthorizationContext,
    ) -> tuple[BudgetAuditEvent, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        return self.store.line_history(tenant_id, project_id, budget_line_id)

    def summary(
        self, *, tenant_id: str, project_id: str, context: AuthorizationContext
    ) -> tuple[CurrencyBudgetSummary, ...]:
        self._check(context, tenant_id, project_id, Permission.PROJECT_READ)
        lines = self.store.list_lines(tenant_id, project_id)
        grouped: dict[str, dict[str, Decimal]] = {}
        for stored in lines:
            bucket = grouped.setdefault(
                stored.line.currency,
                {
                    "original": Decimal("0"),
                    "approved": Decimal("0"),
                    "pending": Decimal("0"),
                    "funding": Decimal("0"),
                },
            )
            bucket["original"] += stored.line.original_amount
            for change in self.store.list_changes(
                tenant_id, project_id, stored.line.budget_line_id
            ):
                if change.change.status == "approved":
                    bucket["approved"] += change.change.amount
                elif change.change.status == "pending":
                    bucket["pending"] += change.change.amount
        for funding in self.store.list_funding(tenant_id, project_id):
            bucket = grouped.setdefault(
                funding.funding.currency,
                {
                    "original": Decimal("0"),
                    "approved": Decimal("0"),
                    "pending": Decimal("0"),
                    "funding": Decimal("0"),
                },
            )
            bucket["funding"] += funding.funding.amount
        rows = []
        for currency in sorted(grouped):
            bucket = grouped[currency]
            current = bucket["original"] + bucket["approved"]
            rows.append(
                CurrencyBudgetSummary(
                    currency=currency,
                    original_budget=bucket["original"],
                    approved_changes=bucket["approved"],
                    current_budget=current,
                    pending_changes=bucket["pending"],
                    funding=bucket["funding"],
                    funding_balance=current - bucket["funding"],
                )
            )
        return tuple(rows)

    # -- writes -----------------------------------------------------------
    def create_line(
        self,
        line: BudgetLine,
        *,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredBudgetLine:
        self._authorize_write(line.tenant_id, line.project_id, context, actor_id)
        with self.transaction_manager.transaction():
            return self.store.persist_line(
                line,
                idempotency_key=idempotency_key,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )

    def update_line(
        self,
        line: BudgetLine,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        audit_reason: str = "",
    ) -> StoredBudgetLine:
        self._authorize_write(line.tenant_id, line.project_id, context, actor_id)
        with self.transaction_manager.transaction():
            current = self.store.get_line(
                line.tenant_id, line.project_id, line.budget_line_id
            )
            if current.line.currency != line.currency and self.store.list_changes(
                line.tenant_id, line.project_id, line.budget_line_id
            ):
                # Changes are denominated in the line currency. Re-denominating
                # a line with recorded changes would silently restate them.
                raise ValueError("BUDGET_CURRENCY_LOCKED_BY_CHANGES")
            return self.store.update_line(
                line,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
                audit_reason=audit_reason,
            )

    def create_change(
        self,
        change: BudgetChange,
        *,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredBudgetChange:
        self._authorize_write(change.tenant_id, change.project_id, context, actor_id)
        if change.status != "pending":
            raise ValueError("BUDGET_CHANGE_MUST_START_PENDING")
        with self.transaction_manager.transaction():
            return self.store.create_change(
                change, actor_id=actor_id, occurred_at=occurred_at
            )

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
    ) -> StoredBudgetChange:
        self._authorize_write(tenant_id, project_id, context, actor_id)
        if not (self.approver_roles & frozenset(context.roles)):
            raise BudgetAuthorizationError("BUDGET_APPROVAL_REQUIRES_ADMIN")
        if status not in ("approved", "rejected"):
            raise ValueError("INVALID_BUDGET_CHANGE_STATUS")
        with self.transaction_manager.transaction():
            return self.store.transition_change(
                tenant_id=tenant_id,
                project_id=project_id,
                change_id=change_id,
                status=status,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
                reason=reason,
            )

    def create_funding(
        self,
        funding: FundingSource,
        *,
        idempotency_key: str,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredFundingSource:
        self._authorize_write(funding.tenant_id, funding.project_id, context, actor_id)
        with self.transaction_manager.transaction():
            return self.store.persist_funding(
                funding,
                idempotency_key=idempotency_key,
                actor_id=actor_id,
                occurred_at=occurred_at,
            )

    def update_funding(
        self,
        funding: FundingSource,
        *,
        expected_revision: int,
        context: AuthorizationContext,
        actor_id: str,
        occurred_at: datetime,
        audit_reason: str = "",
    ) -> StoredFundingSource:
        self._authorize_write(funding.tenant_id, funding.project_id, context, actor_id)
        with self.transaction_manager.transaction():
            return self.store.update_funding(
                funding,
                expected_revision=expected_revision,
                actor_id=actor_id,
                occurred_at=occurred_at,
                audit_reason=audit_reason,
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
            raise BudgetAuthorizationError("BUDGET_CROSS_SCOPE_ACCESS")
        if not self.authorization_policy.is_allowed(context, permission):
            raise BudgetAuthorizationError("BUDGET_PERMISSION_DENIED")

    def _authorize_write(
        self,
        tenant_id: str,
        project_id: str,
        context: AuthorizationContext,
        actor_id: str,
    ) -> None:
        if actor_id != context.user_id:
            raise BudgetAuthorizationError("BUDGET_ACTOR_MISMATCH")
        self._check(context, tenant_id, project_id, Permission.PROJECT_WRITE)

    @staticmethod
    def error_dto(exc: Exception) -> APIError:
        if isinstance(exc, KeyError):
            code = str(exc.args[0]) if exc.args else "BUDGET_LINE_NOT_FOUND"
            return validation_error(code, code)
        if isinstance(exc, BudgetRevisionConflict):
            return conflict_error("BUDGET_REVISION_CONFLICT", str(exc), retryable=True)
        if isinstance(exc, BudgetIdempotencyReuse):
            return conflict_error("BUDGET_IDEMPOTENCY_KEY_REUSE", str(exc))
        if isinstance(exc, BudgetAuthorizationError):
            return authorization_error(str(exc), str(exc))
        if isinstance(exc, ValueError):
            code = str(exc) or type(exc).__name__
            if code.endswith("_ALREADY_EXISTS"):
                return conflict_error(code, code)
            return validation_error(code, code)
        return validation_error(type(exc).__name__, str(exc))
