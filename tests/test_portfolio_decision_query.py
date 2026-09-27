import pytest

from construction_pm.portfolio_decision_query import (
    InMemoryPortfolioDecisionQueryRepository,
    PortfolioDecisionQueryError,
    PortfolioDecisionRead,
)


def item(tenant="t1", portfolio="p1", project="a", revision=2, audit=2):
    return PortfolioDecisionRead(
        "1.0", tenant, portfolio, project, revision, "actor-1", "role:portfolio-reader",
        "approved", "2026-09-27T00:00:00Z", audit, f"event-{project}",
        {"schedule": f"schedule:{project}", "change": f"change:{project}"},
    )


def test_query_is_tenant_and_portfolio_scoped_and_deterministically_ordered():
    repo = InMemoryPortfolioDecisionQueryRepository((item(project="b"), item(project="a"), item(tenant="t2")))
    result = repo.list("t1", "p1")
    assert [x.project_id for x in result] == ["a", "b"]


def test_query_empty_result_is_explicit():
    assert InMemoryPortfolioDecisionQueryRepository().list("t1", "p1") == ()


def test_revision_and_audit_revision_are_coherent():
    with pytest.raises(PortfolioDecisionQueryError, match="INVALID_PORTFOLIO_DECISION_AUDIT_REVISION"):
        item(revision=1, audit=2).validate()


def test_cross_domain_refs_are_opaque():
    value = item()
    value.validate()
    assert value.cross_domain_refs["schedule"] == "schedule:a"


from construction_pm.portfolio_decision_query import (
    PortfolioDecisionQueryService,
    RolePortfolioDecisionQueryAuthorization,
)


def test_application_query_requires_explicit_authorization():
    repository = InMemoryPortfolioDecisionQueryRepository((item(),))
    service = PortfolioDecisionQueryService(
        repository,
        RolePortfolioDecisionQueryAuthorization(
            {"actor-1": frozenset({"portfolio.read"})}
        ),
    )
    assert len(
        service.list(
            tenant_id="t1",
            portfolio_id="p1",
            actor="actor-1",
            authorization_context="portfolio.read",
        )
    ) == 1


def test_application_query_denies_wrong_actor_or_context():
    repository = InMemoryPortfolioDecisionQueryRepository((item(),))
    service = PortfolioDecisionQueryService(
        repository,
        RolePortfolioDecisionQueryAuthorization(
            {"actor-1": frozenset({"portfolio.read"})}
        ),
    )
    with pytest.raises(PortfolioDecisionQueryError, match="PORTFOLIO_DECISION_QUERY_FORBIDDEN"):
        service.list(
            tenant_id="t1",
            portfolio_id="p1",
            actor="actor-2",
            authorization_context="portfolio.read",
        )


def test_authorization_denial_precedes_repository_read():
    class FailingRepository:
        def list(self, tenant_id, portfolio_id):
            raise AssertionError("repository must not be reached after authorization denial")

    service = PortfolioDecisionQueryService(
        FailingRepository(),
        RolePortfolioDecisionQueryAuthorization(
            {"actor-1": frozenset({"portfolio.read"})}
        ),
    )
    with pytest.raises(PortfolioDecisionQueryError, match="PORTFOLIO_DECISION_QUERY_FORBIDDEN"):
        service.list(
            tenant_id="t1",
            portfolio_id="p1",
            actor="actor-2",
            authorization_context="portfolio.read",
        )


def test_query_contract_version_is_preserved_and_fail_closed():
    value = item()
    assert value.contract_version == "1.0"
    value = PortfolioDecisionRead("portfolio-decision.v2", *tuple(value)[1:])
    with pytest.raises(PortfolioDecisionQueryError, match="UNSUPPORTED_PORTFOLIO_DECISION_CONTRACT_VERSION"):
        value.validate()
