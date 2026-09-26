from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .application.authorization import AuthorizationContext, AuthorizationError, AuthorizationPolicy, Permission
from .control_intelligence.portfolio_decision import PortfolioDecisionBoundary, approve_portfolio_decision
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
        self._require(context, Permission.PROJECT_READ)
        return self.store.get(tenant_id, portfolio_id, decision_id)

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
