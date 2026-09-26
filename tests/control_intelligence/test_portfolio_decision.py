from datetime import datetime, timezone

import pytest

from construction_pm.control_intelligence import (
    PortfolioDecisionBoundary,
    SourceReference,
    approve_portfolio_decision,
    mark_portfolio_decision_implemented,
)


def source() -> SourceReference:
    return SourceReference("snap-1", "portfolio-snapshot", "portfolio/1", 30)


def base_decision(**kwargs):
    values = {
        "decision_id": "D-1",
        "portfolio_id": "P-1",
        "tenant_id": "tenant-1",
        "status": "proposed",
        "decision_type": "prioritize",
        "title_key": "decision.prioritize",
        "affected_project_ids": ("PR-1", "PR-2"),
        "source_snapshot_id": "snap-1",
        "proposed_action_ids": ("action-1",),
        "evidence_refs": (source(),),
    }
    values.update(kwargs)
    return PortfolioDecisionBoundary(**values)


def test_proposed_decision_defaults_to_approval_required():
    decision = base_decision()
    decision.validate()
    assert decision.requires_approval is True


def test_approval_requires_actor_and_timestamp():
    decision = base_decision(status="approved")
    with pytest.raises(ValueError, match="APPROVAL_REQUIRED"):
        decision.validate()


def test_approve_transition_creates_explicit_approved_state():
    decision = base_decision()
    approved = approve_portfolio_decision(
        decision,
        approved_by="user-2",
        approved_at=datetime(2026, 9, 27, 14, 0, tzinfo=timezone.utc),
    )
    assert approved.status == "approved"
    assert approved.approved_by == "user-2"


def test_implementation_requires_prior_approval():
    decision = base_decision()
    with pytest.raises(ValueError, match="MUST_BE_APPROVED"):
        mark_portfolio_decision_implemented(
            decision,
            implementation_reference="mutation-1",
            implemented_at=datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc),
        )


def test_approved_decision_can_be_marked_implemented_without_executing_mutation():
    approved = approve_portfolio_decision(
        base_decision(),
        approved_by="user-2",
        approved_at=datetime(2026, 9, 27, 14, 0, tzinfo=timezone.utc),
    )
    implemented = mark_portfolio_decision_implemented(
        approved,
        implementation_reference="application-mutation-42",
        implemented_at=datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc),
    )
    assert implemented.status == "implemented"
    assert implemented.implementation_reference == "application-mutation-42"


def test_decision_contract_is_json_ready():
    payload = base_decision().as_dict()
    assert payload["contract_version"] == "portfolio-decision.v1"
    assert payload["requires_approval"] is True
    assert payload["affected_project_ids"] == ["PR-1", "PR-2"]
