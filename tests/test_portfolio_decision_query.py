import pytest

from construction_pm.portfolio_decision_query import (
    InMemoryPortfolioDecisionQueryRepository,
    PortfolioDecisionQueryError,
    PortfolioDecisionRead,
)


def item(tenant="t1", portfolio="p1", project="a", revision=2, audit=2):
    return PortfolioDecisionRead(
        tenant, portfolio, project, revision, "actor-1", "role:portfolio-reader",
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
