from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol


class PortfolioDecisionQueryError(ValueError):
    pass


@dataclass(frozen=True)
class PortfolioDecisionRead:
    tenant_id: str
    portfolio_id: str
    project_id: str
    revision: int
    actor: str
    authorization_context: str
    lifecycle_state: str
    as_of: str
    audit_revision: int
    audit_event_id: str
    cross_domain_refs: Mapping[str, str]

    def validate(self) -> None:
        for name, value in (
            ("tenant_id", self.tenant_id),
            ("portfolio_id", self.portfolio_id),
            ("project_id", self.project_id),
            ("actor", self.actor),
            ("authorization_context", self.authorization_context),
            ("lifecycle_state", self.lifecycle_state),
            ("as_of", self.as_of),
            ("audit_event_id", self.audit_event_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise PortfolioDecisionQueryError(f"INVALID_PORTFOLIO_DECISION_{name.upper()}")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 1:
            raise PortfolioDecisionQueryError("INVALID_PORTFOLIO_DECISION_REVISION")
        if isinstance(self.audit_revision, bool) or not isinstance(self.audit_revision, int) or self.audit_revision < 1:
            raise PortfolioDecisionQueryError("INVALID_PORTFOLIO_DECISION_AUDIT_REVISION")
        if self.audit_revision > self.revision:
            raise PortfolioDecisionQueryError("INVALID_PORTFOLIO_DECISION_AUDIT_REVISION")
        if not isinstance(self.cross_domain_refs, Mapping) or any(
            not isinstance(k, str) or not k.strip() or not isinstance(v, str) or not v.strip()
            for k, v in self.cross_domain_refs.items()
        ):
            raise PortfolioDecisionQueryError("INVALID_PORTFOLIO_DECISION_CROSS_DOMAIN_REFS")


class PortfolioDecisionQueryAuthorization(Protocol):
    def authorize(self, *, tenant_id: str, portfolio_id: str, actor: str, authorization_context: str) -> None: ...


class RolePortfolioDecisionQueryAuthorization:
    """Application-layer read authorization; persistence and domain calculations remain independent."""

    def __init__(self, allowed_contexts: Mapping[str, frozenset[str]]) -> None:
        self._allowed_contexts = dict(allowed_contexts)

    def authorize(self, *, tenant_id: str, portfolio_id: str, actor: str, authorization_context: str) -> None:
        for name, value in (("tenant_id", tenant_id), ("portfolio_id", portfolio_id), ("actor", actor), ("authorization_context", authorization_context)):
            if not isinstance(value, str) or not value.strip():
                raise PortfolioDecisionQueryError(f"INVALID_PORTFOLIO_DECISION_{name.upper()}")
        if authorization_context not in self._allowed_contexts.get(actor, frozenset()):
            raise PortfolioDecisionQueryError("PORTFOLIO_DECISION_QUERY_FORBIDDEN")


class PortfolioDecisionQueryRepository(Protocol):
    def list(self, tenant_id: str, portfolio_id: str) -> tuple[PortfolioDecisionRead, ...]: ...


class InMemoryPortfolioDecisionQueryRepository:
    """Tenant-isolated deterministic reference repository; no domain recalculation."""

    def __init__(self, decisions: tuple[PortfolioDecisionRead, ...] = ()) -> None:
        self._decisions = decisions

    def list(self, tenant_id: str, portfolio_id: str) -> tuple[PortfolioDecisionRead, ...]:
        if not isinstance(tenant_id, str) or not tenant_id.strip():
            raise PortfolioDecisionQueryError("INVALID_PORTFOLIO_DECISION_TENANT_ID")
        if not isinstance(portfolio_id, str) or not portfolio_id.strip():
            raise PortfolioDecisionQueryError("INVALID_PORTFOLIO_DECISION_PORTFOLIO_ID")
        result = [
            item for item in self._decisions
            if item.tenant_id == tenant_id and item.portfolio_id == portfolio_id
        ]
        for item in result:
            item.validate()
        return tuple(sorted(result, key=lambda item: (item.revision, item.project_id, item.audit_event_id)))


class PortfolioDecisionQueryService:
    """Application/use-case boundary for authorized portfolio decision reads."""

    def __init__(
        self,
        repository: PortfolioDecisionQueryRepository,
        authorization: PortfolioDecisionQueryAuthorization,
    ) -> None:
        self._repository = repository
        self._authorization = authorization

    def list(
        self,
        *,
        tenant_id: str,
        portfolio_id: str,
        actor: str,
        authorization_context: str,
    ) -> tuple[PortfolioDecisionRead, ...]:
        self._authorization.authorize(
            tenant_id=tenant_id,
            portfolio_id=portfolio_id,
            actor=actor,
            authorization_context=authorization_context,
        )
        return self._repository.list(tenant_id, portfolio_id)
