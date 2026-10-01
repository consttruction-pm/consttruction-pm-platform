from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .control_intelligence.portfolio_decision import (
    PortfolioDecisionBoundary,
    approve_portfolio_decision,
    cancel_portfolio_decision,
    close_portfolio_decision,
    mark_portfolio_decision_implemented,
    reject_portfolio_decision,
)
from .portfolio_decision_persistence import PostgresPortfolioDecisionStore, StoredPortfolioDecision


@dataclass(frozen=True)
class PortfolioDecisionApplicationService:
    """Application boundary for persisted portfolio decisions.

    The service owns authorization, tenant/portfolio scope and persistence orchestration.
    Portfolio decision semantics remain in the control-intelligence domain boundary.
    """

    store: PostgresPortfolioDecisionStore
    authorization_policy: AuthorizationPolicy

    def create(
        self,
        decision: PortfolioDecisionBoundary,
        *,
        context: AuthorizationContext,
        idempotency_key: str,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredPortfolioDecision:
        self._authorize_scope(decision, context)
        self._require(context, Permission.PROJECT_ADMIN)
        if actor_id != context.user_id:
            raise AuthorizationError("PORTFOLIO_DECISION_ACTOR_MISMATCH")
        return self.store.persist(
            decision,
            idempotency_key=idempotency_key,
            actor_id=actor_id,
            occurred_at=occurred_at,
        )

    def get(
        self,
        *,
        tenant_id: str,
        portfolio_id: str,
        decision_id: str,
        context: AuthorizationContext,
    ) -> StoredPortfolioDecision:
        if context.tenant_id != tenant_id:
            raise AuthorizationError("CROSS_TENANT_PORTFOLIO_DECISION")
        if not portfolio_id.strip():
            raise ValueError("INVALID_PORTFOLIO_DECISION_PORTFOLIO_ID")
        self._require(context, Permission.PROJECT_READ)
        return self.store.get(tenant_id, portfolio_id, decision_id)

    def approve(
        self,
        decision: PortfolioDecisionBoundary,
        *,
        context: AuthorizationContext,
        expected_decision_revision: int,
        approved_at: datetime,
    ) -> StoredPortfolioDecision:
        self._authorize_scope(decision, context)
        self._require(context, Permission.PROJECT_ADMIN)
        approved = approve_portfolio_decision(
            decision,
            approved_by=context.user_id,
            approved_at=approved_at,
        )
        return self.store.transition(
            approved,
            expected_decision_revision=expected_decision_revision,
            actor_id=context.user_id,
            occurred_at=approved_at,
            event_type="approved",
        )


    def reject(self, decision, *, context, expected_decision_revision, occurred_at):
        return self._transition(
            reject_portfolio_decision(decision),
            context=context,
            expected_decision_revision=expected_decision_revision,
            occurred_at=occurred_at,
            event_type="rejected",
        )

    def cancel(self, decision, *, context, expected_decision_revision, occurred_at):
        return self._transition(
            cancel_portfolio_decision(decision),
            context=context,
            expected_decision_revision=expected_decision_revision,
            occurred_at=occurred_at,
            event_type="cancelled",
        )

    def implement(
        self,
        decision,
        *,
        context,
        expected_decision_revision,
        implementation_reference,
        implemented_at,
    ):
        return self._transition(
            mark_portfolio_decision_implemented(
                decision,
                implementation_reference=implementation_reference,
                implemented_at=implemented_at,
            ),
            context=context,
            expected_decision_revision=expected_decision_revision,
            occurred_at=implemented_at,
            event_type="implemented",
        )

    def close(self, decision, *, context, expected_decision_revision, occurred_at):
        return self._transition(
            close_portfolio_decision(decision),
            context=context,
            expected_decision_revision=expected_decision_revision,
            occurred_at=occurred_at,
            event_type="closed",
        )

    def _transition(
        self,
        decision,
        *,
        context,
        expected_decision_revision,
        occurred_at,
        event_type,
    ):
        self._authorize_scope(decision, context)
        self._require(context, Permission.PROJECT_ADMIN)
        return self.store.transition(
            decision,
            expected_decision_revision=expected_decision_revision,
            actor_id=context.user_id,
            occurred_at=occurred_at,
            event_type=event_type,
        )

    @staticmethod
    def _authorize_scope(
        decision: PortfolioDecisionBoundary,
        context: AuthorizationContext,
    ) -> None:
        if context.tenant_id != decision.tenant_id:
            raise AuthorizationError("CROSS_TENANT_PORTFOLIO_DECISION")
        if not decision.portfolio_id.strip():
            raise ValueError("INVALID_PORTFOLIO_DECISION_PORTFOLIO_ID")

    def _require(self, context: AuthorizationContext, permission: Permission) -> None:
        if not self.authorization_policy.is_allowed(context, permission):
            raise AuthorizationError(f"authorization denied for permission={permission.value}")
