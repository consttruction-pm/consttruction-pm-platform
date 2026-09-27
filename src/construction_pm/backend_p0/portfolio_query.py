from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from construction_pm.application.authorization import AuthorizationContext, AuthorizationPolicy, Permission
from construction_pm.backend_p0.errors import BackendApplicationError, ErrorCategory
from construction_pm.control_intelligence.portfolio import PortfolioControlSnapshot

PORTFOLIO_CONTROL_SNAPSHOT_VERSION = "portfolio-control-snapshot.v1"


class PortfolioQueryProvider(Protocol):
    """Adapter to an authoritative portfolio read model.

    Portfolio aggregation/calculation semantics remain outside this API boundary.
    """

    def get_snapshot(self, portfolio_id: str, *, tenant_id: str) -> PortfolioControlSnapshot: ...


@dataclass(frozen=True)
class PortfolioQueryApplicationService:
    provider: PortfolioQueryProvider
    authorization_policy: AuthorizationPolicy

    def get_snapshot(
        self,
        portfolio_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> PortfolioControlSnapshot:
        if not isinstance(portfolio_id, str) or not portfolio_id.strip():
            raise BackendApplicationError(
                ErrorCategory.VALIDATION,
                "INVALID_PORTFOLIO_ID",
                "Portfolio id is required",
            )
        snapshot = self.provider.get_snapshot(portfolio_id, tenant_id=auth_context.tenant_id)
        if not isinstance(snapshot, PortfolioControlSnapshot):
            raise BackendApplicationError(
                ErrorCategory.VALIDATION,
                "INVALID_PORTFOLIO_QUERY_RESULT",
                "Portfolio query provider returned an invalid result",
            )
        snapshot.validate()
        if snapshot.tenant_id != auth_context.tenant_id:
            raise BackendApplicationError(
                ErrorCategory.AUTHORIZATION,
                "CROSS_SCOPE_ACCESS",
                "Portfolio snapshot tenant does not match authorization context",
            )
        if not self.authorization_policy.is_allowed(auth_context, Permission.PROJECT_READ):
            raise BackendApplicationError(
                ErrorCategory.AUTHORIZATION,
                "FORBIDDEN",
                "Operation is not authorized",
            )
        return snapshot


@dataclass(frozen=True)
class PortfolioQueryAPI:
    service: PortfolioQueryApplicationService

    def get_snapshot(
        self,
        portfolio_id: str,
        *,
        auth_context: AuthorizationContext,
    ) -> dict[str, object]:
        try:
            return self.service.get_snapshot(portfolio_id, auth_context=auth_context).as_dict()
        except BackendApplicationError as exc:
            return exc.to_dto()


__all__ = [
    "PORTFOLIO_CONTROL_SNAPSHOT_VERSION",
    "PortfolioQueryAPI",
    "PortfolioQueryApplicationService",
    "PortfolioQueryProvider",
]
