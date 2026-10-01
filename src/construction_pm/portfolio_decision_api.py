from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from .application.authorization import AuthorizationContext
from .portfolio_decision_application import PortfolioDecisionApplicationService
from .control_intelligence.portfolio_decision import PortfolioDecisionBoundary

PORTFOLIO_DECISION_API_VERSION = "portfolio-decision.v1"

class PortfolioDecisionAPIError(ValueError):
    pass

@dataclass(frozen=True)
class PortfolioDecisionCreateRequest:
    contract_version: str
    decision: PortfolioDecisionBoundary
    idempotency_key: str
    actor_id: str
    occurred_at: datetime
    def validate(self) -> None:
        if self.contract_version != PORTFOLIO_DECISION_API_VERSION:
            raise PortfolioDecisionAPIError("UNSUPPORTED_PORTFOLIO_DECISION_CONTRACT_VERSION")
        if not isinstance(self.idempotency_key, str) or not self.idempotency_key.strip():
            raise PortfolioDecisionAPIError("INVALID_PORTFOLIO_DECISION_IDEMPOTENCY_KEY")
        if not isinstance(self.actor_id, str) or not self.actor_id.strip():
            raise PortfolioDecisionAPIError("INVALID_PORTFOLIO_DECISION_ACTOR")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise PortfolioDecisionAPIError("PORTFOLIO_DECISION_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")

@dataclass(frozen=True)
class PortfolioDecisionReadRequest:
    contract_version: str
    tenant_id: str
    portfolio_id: str
    decision_id: str
    def validate(self) -> None:
        if self.contract_version != PORTFOLIO_DECISION_API_VERSION:
            raise PortfolioDecisionAPIError("UNSUPPORTED_PORTFOLIO_DECISION_CONTRACT_VERSION")
        for name, value in (("tenant_id", self.tenant_id), ("portfolio_id", self.portfolio_id), ("decision_id", self.decision_id)):
            if not isinstance(value, str) or not value.strip():
                raise PortfolioDecisionAPIError(f"INVALID_PORTFOLIO_DECISION_{name.upper()}")

@dataclass(frozen=True)
class PortfolioDecisionAPI:
    service: PortfolioDecisionApplicationService
    def create(self, request: PortfolioDecisionCreateRequest, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        request.validate()
        auth_context.validate()
        self._scope(auth_context, request.decision.tenant_id)
        stored = self.service.create(request.decision, context=auth_context, idempotency_key=request.idempotency_key, actor_id=request.actor_id, occurred_at=request.occurred_at)
        return self._serialize(stored)
    def get(self, request: PortfolioDecisionReadRequest, *, auth_context: AuthorizationContext) -> dict[str, Any]:
        request.validate()
        auth_context.validate()
        self._scope(auth_context, request.tenant_id)
        stored = self.service.store.get(request.tenant_id, request.portfolio_id, request.decision_id)
        return self._serialize(stored)
    @staticmethod
    def _scope(auth_context: AuthorizationContext, tenant_id: str) -> None:
        if auth_context.tenant_id != tenant_id:
            raise PortfolioDecisionAPIError("PORTFOLIO_DECISION_SCOPE_MISMATCH")
    @staticmethod
    def _serialize(stored) -> dict[str, Any]:
        payload = stored.decision.as_dict()
        payload.update({"contract_version": PORTFOLIO_DECISION_API_VERSION, "revision": stored.decision_revision})
        return payload
