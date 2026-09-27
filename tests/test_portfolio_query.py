import pytest

from construction_pm.portfolio_query import (
    InMemoryPortfolioQueryAdapter,
    PortfolioProjectSnapshot,
    PortfolioQueryError,
)


def test_portfolio_query_is_tenant_scoped_and_does_not_recalculate_metrics():
    snapshots = (
        PortfolioProjectSnapshot("tenant-1", "project-1", "2026-09-27T00:00:00Z", "active", {"evm": {"spi": "1.02"}}),
        PortfolioProjectSnapshot("tenant-2", "project-2", "2026-09-27T00:00:00Z", "active", {"evm": {"spi": "0.91"}}),
    )
    result = InMemoryPortfolioQueryAdapter(snapshots).list_projects("tenant-1")
    assert result == (snapshots[0],)
    assert result[0].metrics == {"evm": {"spi": "1.02"}}


def test_portfolio_query_rejects_blank_tenant():
    with pytest.raises(PortfolioQueryError, match="INVALID_PORTFOLIO_TENANT_ID"):
        InMemoryPortfolioQueryAdapter().list_projects(" ")


def test_portfolio_snapshot_requires_mapping_metrics():
    snapshot = PortfolioProjectSnapshot("tenant-1", "project-1", "now", "active", [])
    with pytest.raises(PortfolioQueryError, match="INVALID_PORTFOLIO_METRICS"):
        InMemoryPortfolioQueryAdapter((snapshot,)).list_projects("tenant-1")
