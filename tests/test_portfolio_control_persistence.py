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
                (SourceReference("sched-a", "schedule", "schedule://project-a/7", 2),),
                1, NOW,
            ),
            PortfolioMembershipRecord(
                "tenant-a", "portfolio-a", "project-b", "on_hold", 4,
                (SourceReference("cost-b", "cost", "cost://project-b/4", 3),),
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


class FakeSourceReferenceReader:
    def __init__(self, memberships):
        self.current = {
            (item.tenant_id, item.project_id, source.source_id, source.locator): source.revision
            for item in memberships
            for source in item.source_refs
        }

    def is_current(self, tenant_id, project_id, source_ref):
        key = (tenant_id, project_id, source_ref.source_id, source_ref.locator)
        if key not in self.current:
            raise KeyError("PORTFOLIO_SOURCE_REFERENCE_NOT_FOUND")
        return self.current[key] == source_ref.revision


def provider(repository, facts):
    return PostgresPortfolioControlSnapshotProvider(
        repository, FakeFactsReader(facts), FakeSourceReferenceReader(repository.memberships)
    )


def test_provider_uses_canonical_membership_and_authoritative_project_facts():
    repository = FakeRepository()
    reader = FakeFactsReader({
        "project-a": PortfolioProjectFacts("project-a", 7, "active", "project.a"),
        "project-b": PortfolioProjectFacts("project-b", 4, "on_hold", "project.b"),
    })
    snapshot_provider = PostgresPortfolioControlSnapshotProvider(
        repository, reader, FakeSourceReferenceReader(repository.memberships)
    )

    snapshot = snapshot_provider.get_snapshot("portfolio-a", tenant_id="tenant-a")

    assert snapshot.portfolio_revision == 2
    assert snapshot.snapshot_id.startswith("pcs-r2-")
    assert [item.project_id for item in snapshot.projects] == ["project-a", "project-b"]
    assert [item.membership_status for item in snapshot.projects] == ["included", "on_hold"]
    assert [item.status for item in snapshot.projects] == ["active", "on_hold"]
    assert snapshot.projects[0].schedule_result_ref == "schedule://project-a/7"
    assert snapshot.projects[1].cost_result_ref == "cost://project-b/4"
    assert [source.revision for source in snapshot.source_refs] == [2, 3]
    assert snapshot.summary == {
        "total_projects": 2, "included_projects": 1,
        "on_hold_projects": 1, "excluded_projects": 0,
    }
    assert reader.calls == [("tenant-a", "project-a"), ("tenant-a", "project-b")]


def test_snapshot_identity_and_time_are_stable_for_same_revision_inputs():
    repository = FakeRepository()
    facts = {
        "project-a": PortfolioProjectFacts("project-a", 7, "active"),
        "project-b": PortfolioProjectFacts("project-b", 4, "on_hold"),
    }
    snapshot_provider = provider(repository, facts)

    first = snapshot_provider.get_snapshot("portfolio-a", tenant_id="tenant-a")
    second = snapshot_provider.get_snapshot("portfolio-a", tenant_id="tenant-a")

    assert first.snapshot_id == second.snapshot_id
    assert first.generated_at == second.generated_at
    assert first.as_dict() == second.as_dict()


def test_provider_rejects_stale_engineering_revision():
    repository = FakeRepository()
    facts = {
        "project-a": PortfolioProjectFacts("project-a", 8, "active"),
        "project-b": PortfolioProjectFacts("project-b", 4, "on_hold"),
    }
    snapshot_provider = provider(repository, facts)

    with pytest.raises(PortfolioControlPersistenceError, match="PORTFOLIO_PROJECT_SOURCE_STALE"):
        snapshot_provider.get_snapshot("portfolio-a", tenant_id="tenant-a")


def test_provider_rejects_stale_source_reference_revision_independently():
    repository = FakeRepository()
    facts = {
        "project-a": PortfolioProjectFacts("project-a", 7, "active"),
        "project-b": PortfolioProjectFacts("project-b", 4, "on_hold"),
    }
    source_reader = FakeSourceReferenceReader(repository.memberships)
    source_reader.current[("tenant-a", "project-a", "sched-a", "schedule://project-a/7")] = 1
    snapshot_provider = PostgresPortfolioControlSnapshotProvider(
        repository, FakeFactsReader(facts), source_reader
    )

    with pytest.raises(
        PortfolioControlPersistenceError, match="PORTFOLIO_SOURCE_REFERENCE_STALE"
    ):
        snapshot_provider.get_snapshot("portfolio-a", tenant_id="tenant-a")


def test_provider_does_not_leak_unknown_or_cross_tenant_portfolios():
    repository = FakeRepository()
    snapshot_provider = provider(repository, {})

    with pytest.raises(KeyError, match="PORTFOLIO_NOT_FOUND"):
        snapshot_provider.get_snapshot("portfolio-a", tenant_id="tenant-b")

    with pytest.raises(PortfolioControlPersistenceError, match="INVALID_PORTFOLIO_TENANT_ID"):
        snapshot_provider.get_snapshot("portfolio-a", tenant_id=" ")


def test_provider_rejects_missing_project_source_facts():
    repository = FakeRepository()
    facts = {"project-a": PortfolioProjectFacts("project-a", 7, "active")}
    snapshot_provider = provider(repository, facts)

    with pytest.raises(KeyError):
        snapshot_provider.get_snapshot("portfolio-a", tenant_id="tenant-a")


def test_provider_rejects_missing_source_reference():
    repository = FakeRepository()
    facts = {
        "project-a": PortfolioProjectFacts("project-a", 7, "active"),
        "project-b": PortfolioProjectFacts("project-b", 4, "on_hold"),
    }
    source_reader = FakeSourceReferenceReader(repository.memberships)
    del source_reader.current[
        ("tenant-a", "project-a", "sched-a", "schedule://project-a/7")
    ]
    snapshot_provider = PostgresPortfolioControlSnapshotProvider(
        repository, FakeFactsReader(facts), source_reader
    )

    with pytest.raises(
        PortfolioControlPersistenceError, match="PORTFOLIO_SOURCE_REFERENCE_MISSING"
    ):
        snapshot_provider.get_snapshot("portfolio-a", tenant_id="tenant-a")
