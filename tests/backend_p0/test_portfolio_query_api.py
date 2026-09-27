from __future__ import annotations

from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import AuthorizationContext, Permission, RoleBasedAuthorizationPolicy
from construction_pm.backend_p0.errors import ErrorCategory
from construction_pm.backend_p0.portfolio_query import PortfolioQueryAPI, PortfolioQueryApplicationService
from construction_pm.control_intelligence.contracts import SourceReference
from construction_pm.control_intelligence.portfolio import PortfolioControlSnapshot, PortfolioProjectControlInput


def policy() -> RoleBasedAuthorizationPolicy:
    return RoleBasedAuthorizationPolicy({"viewer": frozenset({Permission.PROJECT_READ})})


def auth(tenant_id: str = "tenant-1", role: str = "viewer") -> AuthorizationContext:
    return AuthorizationContext(tenant_id, "portfolio-context", "user-1", frozenset({role}))


def snapshot(tenant_id: str = "tenant-1") -> PortfolioControlSnapshot:
    return PortfolioControlSnapshot(
        snapshot_id="snapshot-1",
        portfolio_id="portfolio-1",
        tenant_id=tenant_id,
        generated_at=datetime(2026, 9, 27, 18, 0, tzinfo=timezone.utc),
        projects=(PortfolioProjectControlInput("project-1", 7, "included", "active"),),
        source_refs=(SourceReference("source-1", "portfolio", "/portfolio/project-1", 7),),
    )


class Provider:
    def __init__(self, result: PortfolioControlSnapshot) -> None:
        self.result = result
        self.calls: list[tuple[str, str]] = []

    def get_snapshot(self, portfolio_id: str, *, tenant_id: str) -> PortfolioControlSnapshot:
        self.calls.append((portfolio_id, tenant_id))
        return self.result


def test_application_delegates_and_preserves_tenant_scope() -> None:
    provider = Provider(snapshot())
    service = PortfolioQueryApplicationService(provider, policy())

    result = service.get_snapshot("portfolio-1", auth_context=auth())

    assert result.portfolio_id == "portfolio-1"
    assert result.tenant_id == "tenant-1"
    assert provider.calls == [("portfolio-1", "tenant-1")]


def test_application_rejects_cross_tenant_snapshot_and_forbidden_access() -> None:
    service = PortfolioQueryApplicationService(Provider(snapshot("tenant-2")), policy())
    with pytest.raises(Exception) as cross:
        service.get_snapshot("portfolio-1", auth_context=auth())
    assert cross.value.category == ErrorCategory.AUTHORIZATION
    assert cross.value.code == "CROSS_SCOPE_ACCESS"

    with pytest.raises(Exception) as forbidden:
        PortfolioQueryApplicationService(Provider(snapshot()), policy()).get_snapshot(
            "portfolio-1", auth_context=auth(role="unknown")
        )
    assert forbidden.value.category == ErrorCategory.AUTHORIZATION
    assert forbidden.value.code == "FORBIDDEN"


def test_api_returns_versioned_snapshot() -> None:
    result = PortfolioQueryAPI(
        PortfolioQueryApplicationService(Provider(snapshot()), policy())
    ).get_snapshot("portfolio-1", auth_context=auth())

    assert result["contract_version"] == "portfolio-control-snapshot.v1"
    assert result["portfolio_id"] == "portfolio-1"
    assert result["summary"]["included_projects"] == 1
    assert result["projects"][0]["project_revision"] == 7


def test_api_maps_invalid_portfolio_and_provider_result() -> None:
    api = PortfolioQueryAPI(
        PortfolioQueryApplicationService(Provider(snapshot()), policy())
    )
    invalid = api.get_snapshot(" ", auth_context=auth())
    assert invalid["error"]["code"] == "INVALID_PORTFOLIO_ID"

    class InvalidProvider:
        def get_snapshot(self, portfolio_id: str, *, tenant_id: str) -> object:
            return object()

    invalid_result = PortfolioQueryAPI(
        PortfolioQueryApplicationService(InvalidProvider(), policy())  # type: ignore[arg-type]
    ).get_snapshot("portfolio-1", auth_context=auth())
    assert invalid_result["error"]["code"] == "INVALID_PORTFOLIO_QUERY_RESULT"
