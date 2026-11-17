from __future__ import annotations

from datetime import datetime, timezone

import pytest

from construction_pm.control_intelligence.contracts import SourceReference
from construction_pm.portfolio_control_persistence import (
    PortfolioControlPersistenceError,
    PortfolioMembershipRecord,
    PortfolioProjectFacts,
    PortfolioRecord,
    PostgresPortfolioControlSnapshotProvider,
)

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)


class FakeRepository:
    def __init__(self):
        self.portfolio = PortfolioRecord("tenant-a", "portfolio-a", 2, NOW, NOW)
        self.memberships = (
            PortfolioMembershipRecord(
                "tenant-a", "portfolio-a", "project-a", "included", 7,
                (SourceReference("sched-a", "schedule", "schedule://project-a/7", 7),),
                1, NOW,
            ),
            PortfolioMembershipRecord(
                "tenant-a", "portfolio-a", "project-b", "on_hold", 4,
                (SourceReference("cost-b", "cost", "cost://project-b/4", 4),),
                1, NOW,
            ),
        )

    def get_portfolio(self, tenant_id, portfolio_id):
        if (tenant_id, portfolio_id) != ("tenant-a", "portfolio-a"):
            raise KeyError("PORTFOLIO_NOT_FOUND")
        return self.portfolio

    def list_memberships(self, tenant_id, portfolio_id):
        self.get_portfolio(tenant_id, portfolio_id)
        return self.memberships

    def get_snapshot_records(self, tenant_id, portfolio_id):
        return self.get_portfolio(tenant_id, portfolio_id), self.list_memberships(
            tenant_id, portfolio_id
        )


class FakeFactsReader:
    def __init__(self, facts):
        self.facts = facts
        self.calls = []

    def get_project_facts(self, tenant_id, project_id):
        self.calls.append((tenant_id, project_id))
        return self.facts[project_id]


def test_provider_uses_canonical_membership_and_authoritative_project_facts():
    repository = FakeRepository()
    reader = FakeFactsReader({
        "project-a": PortfolioProjectFacts("project-a", 7, "active", "project.a"),
        "project-b": PortfolioProjectFacts("project-b", 4, "on_hold", "project.b"),
    })
    provider = PostgresPortfolioControlSnapshotProvider(repository, reader)

    snapshot = provider.get_snapshot("portfolio-a", tenant_id="tenant-a")

    assert snapshot.portfolio_revision == 2
    assert [item.project_id for item in snapshot.projects] == ["project-a", "project-b"]
    assert [item.membership_status for item in snapshot.projects] == ["included", "on_hold"]
    assert [item.status for item in snapshot.projects] == ["active", "on_hold"]
    assert snapshot.projects[0].schedule_result_ref == "schedule://project-a/7"
    assert snapshot.projects[1].cost_result_ref == "cost://project-b/4"
    assert snapshot.summary == {
        "total_projects": 2, "included_projects": 1,
        "on_hold_projects": 1, "excluded_projects": 0,
    }
    assert reader.calls == [("tenant-a", "project-a"), ("tenant-a", "project-b")]


def test_snapshot_identity_and_time_are_stable_for_same_revision_inputs():
    repository = FakeRepository()
    reader = FakeFactsReader({
        "project-a": PortfolioProjectFacts("project-a", 7, "active"),
        "project-b": PortfolioProjectFacts("project-b", 4, "on_hold"),
    })
    provider = PostgresPortfolioControlSnapshotProvider(repository, reader)

    first = provider.get_snapshot("portfolio-a", tenant_id="tenant-a")
    second = provider.get_snapshot("portfolio-a", tenant_id="tenant-a")

    assert first.snapshot_id == second.snapshot_id
    assert first.generated_at == second.generated_at
    assert first.as_dict() == second.as_dict()


def test_provider_rejects_stale_engineering_revision():
    repository = FakeRepository()
    reader = FakeFactsReader({
        "project-a": PortfolioProjectFacts("project-a", 8, "active"),
        "project-b": PortfolioProjectFacts("project-b", 4, "on_hold"),
    })
    provider = PostgresPortfolioControlSnapshotProvider(repository, reader)

    with pytest.raises(PortfolioControlPersistenceError, match="PORTFOLIO_PROJECT_SOURCE_STALE"):
        provider.get_snapshot("portfolio-a", tenant_id="tenant-a")


def test_provider_does_not_leak_unknown_or_cross_tenant_portfolios():
    provider = PostgresPortfolioControlSnapshotProvider(FakeRepository(), FakeFactsReader({}))

    with pytest.raises(KeyError, match="PORTFOLIO_NOT_FOUND"):
        provider.get_snapshot("portfolio-a", tenant_id="tenant-b")

    with pytest.raises(PortfolioControlPersistenceError, match="INVALID_PORTFOLIO_TENANT_ID"):
        provider.get_snapshot("portfolio-a", tenant_id=" ")


def test_provider_rejects_missing_project_source_facts():
    repository = FakeRepository()
    reader = FakeFactsReader({
        "project-a": PortfolioProjectFacts("project-a", 7, "active"),
    })
    provider = PostgresPortfolioControlSnapshotProvider(repository, reader)

    with pytest.raises(KeyError):
        provider.get_snapshot("portfolio-a", tenant_id="tenant-a")
