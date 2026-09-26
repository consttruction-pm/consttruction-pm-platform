from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from .application.authorization import AuthorizationContext
from .portfolio_control_action_store import (
    PortfolioControlActionStore,
    StoredPortfolioControlAction,
)
from .portfolio_control_actions import (
    PortfolioActionStatus,
    PortfolioControlAction,
    PortfolioControlActionService,
)


@dataclass(frozen=True)
class PortfolioControlActionApplicationService:
    store: PortfolioControlActionStore
    authorization: PortfolioControlActionService

    def propose(
        self,
        action: PortfolioControlAction,
        *,
        auth_context: AuthorizationContext,
    ) -> StoredPortfolioControlAction:
        self.authorization.authorize_request(action, auth_context)
        return self.store.create(action)

    def decide(
        self,
        action: PortfolioControlAction,
        *,
        auth_context: AuthorizationContext,
        expected_action_revision: int,
        status: PortfolioActionStatus,
        actor_id: str,
        occurred_at: datetime,
    ) -> StoredPortfolioControlAction:
        current = self.store.get(
            action.tenant_id,
            action.portfolio_id,
            action.action_id,
        )
        if current is None:
            raise ValueError("PORTFOLIO_ACTION_NOT_FOUND")

        if status not in {
            PortfolioActionStatus.APPROVED,
            PortfolioActionStatus.REJECTED,
            PortfolioActionStatus.CANCELLED,
        }:
            raise ValueError("INVALID_PORTFOLIO_ACTION_DECISION_STATUS")

        candidate = replace(
            current.action,
            status=status,
            decided_by=actor_id if status in {
                PortfolioActionStatus.APPROVED,
                PortfolioActionStatus.REJECTED,
            } else None,
            decided_at=occurred_at if status in {
                PortfolioActionStatus.APPROVED,
                PortfolioActionStatus.REJECTED,
            } else None,
        )
        self.authorization.authorize_decision(candidate, auth_context)
        return self.store.transition(
            action=candidate,
            expected_action_revision=expected_action_revision,
            actor_id=actor_id,
            occurred_at=occurred_at,
            event_type=status.value,
        )
