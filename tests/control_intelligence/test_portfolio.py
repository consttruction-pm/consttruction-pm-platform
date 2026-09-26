from datetime import datetime, timezone
import json

import pytest

from construction_pm.control_intelligence import (
    PortfolioControlSnapshot,
    PortfolioProjectControlInput,
    SourceReference,
    build_portfolio_control_snapshot,
)


def source(revision: int = 12) -> SourceReference:
    return SourceReference(
        "source-1",
        "project-control",
        "projects/P-1/snapshot",
        revision,
    )


def project(project_id: str, membership_status: str, revision: int = 12):
    return PortfolioProjectControlInput(
        project_id=project_id,
        project_revision=revision,
        membership_status=membership_status,
        status="active",
        name_key=f"project.{project_id}",
        schedule_result_ref=f"schedule-{project_id}",
        progress_result_ref=f"progress-{project_id}",
        cost_result_ref=f"cost-{project_id}",
        resource_result_ref=f"resource-{project_id}",
        risk_result_ref=f"risk-{project_id}",
        claim_result_ref=f"claim-{project_id}",
        procurement_result_ref=f"procurement-{project_id}",
    )


def test_portfolio_snapshot_is_cross_project_and_read_only():
    snapshot = PortfolioControlSnapshot(
        snapshot_id="snap-1",
        portfolio_id="portfolio-1",
        tenant_id="tenant-1",
        generated_at=datetime(2026, 9, 27, 13, 0, tzinfo=timezone.utc),
        projects=(
            project("P-1", "included"),
            project("P-2", "included", revision=13),
            project("P-3", "on_hold"),
            project("P-4", "excluded"),
        ),
        source_refs=(source(),),
    )

    data = snapshot.as_dict()

    assert data["summary"] == {
        "total_projects": 4,
        "included_projects": 2,
        "on_hold_projects": 1,
        "excluded_projects": 1,
    }
    assert data["projects"][1]["project_revision"] == 13
    assert data["projects"][1]["schedule_result_ref"] == "schedule-P-2"
    assert "resource" not in data["projects"][1]


def test_duplicate_projects_are_rejected():
    with pytest.raises(ValueError, match="DUPLICATE_PORTFOLIO_PROJECT"):
        PortfolioControlSnapshot(
            "snap-1",
            "portfolio-1",
            "tenant-1",
            datetime(2026, 9, 27, 13, 0, tzinfo=timezone.utc),
            (project("P-1", "included"), project("P-1", "included")),
            (source(),),
        ).validate()


def test_unsafe_project_revision_is_rejected():
    with pytest.raises(ValueError, match="INVALID_PORTFOLIO_PROJECT_REVISION"):
        project("P-1", "included", 9_007_199_254_740_992).validate()


def test_source_revision_is_not_forced_to_equal_project_revision():
    snapshot = PortfolioControlSnapshot(
        "snap-2",
        "portfolio-1",
        "tenant-1",
        datetime(2026, 9, 27, 13, 0, tzinfo=timezone.utc),
        (project("P-1", "included", revision=20),),
        (source(revision=4),),
    )
    snapshot.validate()


def test_builder_returns_contract_safe_json():
    data = build_portfolio_control_snapshot(
        snapshot_id="snap-3",
        portfolio_id="portfolio-1",
        tenant_id="tenant-1",
        generated_at=datetime(2026, 9, 27, 13, 0, tzinfo=timezone.utc),
        projects=[project("P-1", "included")],
        source_refs=[source()],
    )
    assert data["contract_version"] == "portfolio-control-snapshot.v1"
    assert json.dumps(data, sort_keys=True)
