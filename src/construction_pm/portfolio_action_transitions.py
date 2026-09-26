from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from .application.authorization import AuthorizationContext, AuthorizationPolicy, Permission
from .portfolio_control_actions import (
    PortfolioActionStatus,
    PortfolioActionType,
    PortfolioControlAction,
    PortfolioControlActionService,
)


@dataclass(frozen=True)
class PortfolioActionTransitionService:
    """Application boundary for auditable portfolio-action state transitions.

    Persistence, revision compare-and-swap, and idempotency storage remain
    repository concerns; this service only validates an allowed transition
    before an application transaction persists the returned action.
    """

    authorization_policy: AuthorizationPolicy

    def approve(
        self,
        action: PortfolioControlAction,
        context: AuthorizationContext,
        *,
        decided_at: datetime,
    ) -> PortfolioControlAction:
        return self._decide(
            action,
            context,
            action_type=PortfolioActionType.APPROVE,
            status=PortfolioActionStatus.APPROVED,
            decided_at=decided_at,
        )

    def reject(
        self,
        action: PortfolioControlAction,
        context: AuthorizationContext,
        *,
        decided_at: datetime,
    ) -> PortfolioControlAction:
        return self._decide(
            action,
            context,
            action_type=PortfolioActionType.REJECT,
            status=PortfolioActionStatus.REJECTED,
            decided_at=decided_at,
        )

    def cancel(
        self,
        action: PortfolioControlAction,
        context: AuthorizationContext,
        *,
        cancelled_at: datetime,
    ) -> PortfolioControlAction:
        if action.status is not PortfolioActionStatus.PROPOSED:
            raise ValueError("PORTFOLIO_ACTION_NOT_PENDING")
        if cancelled_at.tzinfo is None or cancelled_at.utcoffset() is None:
            raise ValueError("PORTFOLIO_ACTION_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")

        PortfolioControlActionService(self.authorization_policy).authorize_request(action, context)
        return replace(
            action,
            status=PortfolioActionStatus.CANCELLED,
            decided_by=context.user_id,
            decided_at=cancelled_at,
        )

    def _decide(
        self,
        action: PortfolioControlAction,
        context: AuthorizationContext,
        *,
        action_type: PortfolioActionType,
        status: PortfolioActionStatus,
        decided_at: datetime,
    ) -> PortfolioControlAction:
        if action.status is not PortfolioActionStatus.PROPOSED:
            raise ValueError("PORTFOLIO_ACTION_NOT_PENDING")
        if decided_at.tzinfo is None or decided_at.utcoffset() is None:
            raise ValueError("DECISION_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")

        PortfolioControlActionService(self.authorization_policy).authorize_decision(action, context)
        decided = replace(
            action,
            action_type=action_type,
            status=status,
            decided_by=context.user_id,
            decided_at=decided_at,
        )
        decided.validate()
        return decided
