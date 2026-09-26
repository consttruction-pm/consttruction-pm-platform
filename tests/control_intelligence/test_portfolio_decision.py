from dataclasses import replace
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


@pytest.mark.parametrize("value", [1, "true", None])
def test_requires_approval_must_be_boolean(value):
    with pytest.raises(ValueError, match="REQUIRES_APPROVAL"):
        base_decision(requires_approval=value).validate()


@pytest.mark.parametrize("value", ["", 123, None])
def test_approval_actor_must_be_nonempty_string(value):
    with pytest.raises(ValueError, match="APPROVER_REQUIRED"):
        approve_portfolio_decision(
            base_decision(),
            approved_by=value,
            approved_at=datetime(2026, 9, 27, 14, 0, tzinfo=timezone.utc),
        )


@pytest.mark.parametrize("value", ["", 123, None])
def test_implementation_reference_must_be_nonempty_string(value):
    with pytest.raises(ValueError, match="IMPLEMENTATION_REFERENCE_REQUIRED"):
        mark_portfolio_decision_implemented(
            base_decision(requires_approval=False),
            implementation_reference=value,
            implemented_at=datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc),
        )


def test_evidence_refs_must_contain_source_references():
    with pytest.raises(ValueError, match="EVIDENCE_REFERENCE"):
        base_decision(evidence_refs=({"source_id": "snap-1"},)).validate()



def test_closed_decision_requires_complete_approval():
    with pytest.raises(ValueError, match="PORTFOLIO_DECISION_APPROVAL_REQUIRED"):
        base_decision(status="closed", approved_by="user-2").validate()


def test_closed_approved_decision_is_valid():
    approved = approve_portfolio_decision(
        base_decision(),
        approved_by="user-2",
        approved_at=datetime(2026, 9, 27, 14, 0, tzinfo=timezone.utc),
    )
    closed = base_decision(
        status="closed",
        approved_by=approved.approved_by,
        approved_at=approved.approved_at,
    )
    closed.validate()

def test_decision_rejects_invalid_scalar_and_timestamp_types():
    decision = base_decision()
    with pytest.raises(ValueError, match="INVALID_PORTFOLIO_DECISION_STATUS"):
        replace(decision, status=[]).validate()
    with pytest.raises(ValueError, match="INVALID_PORTFOLIO_DECISION_TYPE"):
        replace(decision, decision_type=[]).validate()
    with pytest.raises(ValueError, match="INVALID_PORTFOLIO_DECISION_APPROVAL_TIMESTAMP"):
        replace(decision, approved_at="2026-09-27T00:00:00Z").validate()
    with pytest.raises(ValueError, match="INVALID_PORTFOLIO_DECISION_IMPLEMENTATION_TIMESTAMP"):
        replace(decision, implemented_at="2026-09-27T00:00:00Z").validate()
