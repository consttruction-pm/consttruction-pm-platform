import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from construction_pm.application.authorization import (
    AuthorizationError,
    AuthorizationContext,
    Permission,
    RoleBasedAuthorizationPolicy,
)
from construction_pm.control_intelligence.contracts import SourceReference
from construction_pm.portfolio_control_actions import (
    PortfolioActionStatus,
    PortfolioActionType,
    PortfolioControlAction,
    PortfolioControlActionService,
)


def source() -> SourceReference:
    return SourceReference("source-1", "portfolio-control", "portfolio/P-1/snapshot", 12)


def action(**overrides: object) -> PortfolioControlAction:
    data: dict[str, object] = {
        "action_id": "action-1",
        "tenant_id": "tenant-1",
        "portfolio_id": "portfolio-1",
        "portfolio_revision": 12,
        "target_type": "project",
        "target_id": "project-1",
        "action_type": PortfolioActionType.HOLD_PROJECT,
        "source_snapshot_id": "snapshot-1",
        "expected_portfolio_revision": 12,
        "requested_by": "user-1",
        "requested_at": datetime(2026, 9, 27, 13, 0, tzinfo=timezone.utc),
        "idempotency_key": "idem-1",
        "evidence_refs": (source(),),
    }
    data.update(overrides)
    return PortfolioControlAction(**data)


def policy() -> RoleBasedAuthorizationPolicy:
    return RoleBasedAuthorizationPolicy(
        {
            "planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE}),
            "admin": frozenset(
                {Permission.PROJECT_READ, Permission.PROJECT_WRITE, Permission.PROJECT_ADMIN}
            ),
        }
    )


def test_action_contract_is_versioned_and_closed() -> None:
    contract = json.loads(
        (Path(__file__).parents[2] / "shared/contracts/portfolio-control-action.v1.schema.json").read_text()
    )
    assert contract["$schema"].endswith("/draft/2020-12/schema")
    assert "/v1/" in contract["$id"]
    assert contract["additionalProperties"] is False
    assert contract["properties"]["contract_version"]["const"] == "portfolio-control-action.v1"


def test_project_action_requires_project_target() -> None:
    with pytest.raises(ValueError, match="PROJECT_ACTION_REQUIRES_PROJECT_TARGET"):
        action(target_type="portfolio", target_id="portfolio-1").validate()


def test_portfolio_target_must_match_portfolio() -> None:
    with pytest.raises(ValueError, match="PORTFOLIO_TARGET_MUST_MATCH_PORTFOLIO"):
        action(target_type="portfolio", target_id="other-portfolio").validate()



def test_decision_requires_approval_and_decision_metadata() -> None:
    with pytest.raises(ValueError, match="DECISION_ACTION_MUST_REQUIRE_APPROVAL"):
        action(action_type=PortfolioActionType.APPROVE, requires_approval=False).validate()
    with pytest.raises(ValueError, match="DECISION_METADATA_REQUIRED"):
        action(status=PortfolioActionStatus.APPROVED).validate()


def test_evidence_is_required_for_approval_bound_actions() -> None:
    with pytest.raises(ValueError, match="PORTFOLIO_ACTION_EVIDENCE_REQUIRED"):
        action(evidence_refs=()).validate()


def test_scope_and_revision_are_enforced() -> None:
    service = PortfolioControlActionService(policy())
    with pytest.raises(ValueError, match="CROSS_TENANT_PORTFOLIO_ACTION"):
        service.authorize_request(
            action(),
            AuthorizationContext("tenant-2", "project-1", "user-1", frozenset({"planner"})),
        )
    with pytest.raises(ValueError, match="CROSS_PROJECT_PORTFOLIO_ACTION"):
        service.authorize_request(
            action(),
            AuthorizationContext("tenant-1", "project-2", "user-1", frozenset({"planner"})),
        )
    with pytest.raises(ValueError, match="INVALID_PORTFOLIO_ACTION_EXPECTED_REVISION"):
        action(expected_portfolio_revision=9_007_199_254_740_992).validate()


def test_request_and_decision_permissions_are_distinct() -> None:
    service = PortfolioControlActionService(policy())
    service.authorize_request(
        action(),
        AuthorizationContext("tenant-1", "project-1", "user-1", frozenset({"planner"})),
    )
    approved = action(
        action_type=PortfolioActionType.APPROVE,
        status=PortfolioActionStatus.APPROVED,
        decided_by="admin-1",
        decided_at=datetime(2026, 9, 27, 13, 5, tzinfo=timezone.utc),
    )
    service.authorize_decision(
        approved,
        AuthorizationContext("tenant-1", "project-1", "admin-1", frozenset({"admin"})),
    )
    with pytest.raises(AuthorizationError):
        service.authorize_decision(
            approved,
            AuthorizationContext("tenant-1", "project-1", "user-1", frozenset({"planner"})),
        )


def test_portfolio_level_request_requires_admin() -> None:
    service = PortfolioControlActionService(policy())
    portfolio_action = action(
        target_type="portfolio",
        target_id="portfolio-1",
        action_type=PortfolioActionType.REQUEST_REVIEW,
    )
    with pytest.raises(AuthorizationError):
        service.authorize_request(
            portfolio_action,
            AuthorizationContext("tenant-1", "project-1", "user-1", frozenset({"planner"})),
        )
    service.authorize_request(
        portfolio_action,
        AuthorizationContext("tenant-1", "project-1", "admin-1", frozenset({"admin"})),
    )



def test_as_dict_preserves_opaque_authoritative_references() -> None:
    payload = action().as_dict()
    assert payload["contract_version"] == "portfolio-control-action.v1"
    assert payload["source_snapshot_id"] == "snapshot-1"
    assert payload["target_id"] == "project-1"
    assert payload["expected_portfolio_revision"] == 12
    assert payload["evidence_refs"][0]["locator"] == "portfolio/P-1/snapshot"
