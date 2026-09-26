from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    AuthorizationError,
    Permission,
    RoleBasedAuthorizationPolicy,
)
from construction_pm.portfolio_action_transitions import PortfolioActionTransitionService
from construction_pm.portfolio_control_actions import (
    PortfolioActionStatus,
    PortfolioActionType,
    PortfolioControlAction,
)
from construction_pm.control_intelligence.contracts import SourceReference


def source() -> SourceReference:
    return SourceReference("source-1", "portfolio-control", "snapshot/1", 12)


def policy() -> RoleBasedAuthorizationPolicy:
    return RoleBasedAuthorizationPolicy(
        {
            "planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE}),
            "admin": frozenset(
                {Permission.PROJECT_READ, Permission.PROJECT_WRITE, Permission.PROJECT_ADMIN}
            ),
        }
    )


def pending(**overrides: object) -> PortfolioControlAction:
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
        "requested_by": "planner-1",
        "requested_at": datetime(2026, 9, 27, 13, 0, tzinfo=timezone.utc),
        "idempotency_key": "idem-1",
        "evidence_refs": (source(),),
    }
    data.update(overrides)
    return PortfolioControlAction(**data)


def admin_context() -> AuthorizationContext:
    return AuthorizationContext(
        "tenant-1", "project-1", "admin-1", frozenset({"admin"})
    )


def planner_context() -> AuthorizationContext:
    return AuthorizationContext(
        "tenant-1", "project-1", "planner-1", frozenset({"planner"})
    )


def test_approve_transitions_pending_action_with_decision_audit() -> None:
    decided_at = datetime(2026, 9, 27, 13, 5, tzinfo=timezone.utc)
    result = PortfolioActionTransitionService(policy()).approve(
        pending(), admin_context(), decided_at=decided_at
    )
    assert result.status is PortfolioActionStatus.APPROVED
    assert result.action_type is PortfolioActionType.APPROVE
    assert result.decided_by == "admin-1"
    assert result.decided_at == decided_at
    assert result.expected_portfolio_revision == 12


def test_reject_transitions_pending_action() -> None:
    result = PortfolioActionTransitionService(policy()).reject(
        pending(), admin_context(), decided_at=datetime.now(timezone.utc)
    )
    assert result.status is PortfolioActionStatus.REJECTED
    assert result.action_type is PortfolioActionType.REJECT
    assert result.decided_by == "admin-1"


def test_cancel_is_request_scope_and_keeps_audit_actor() -> None:
    result = PortfolioActionTransitionService(policy()).cancel(
        pending(), planner_context(), cancelled_at=datetime.now(timezone.utc)
    )
    assert result.status is PortfolioActionStatus.CANCELLED
    assert result.decided_by == "planner-1"


def test_non_pending_action_cannot_be_decided_twice() -> None:
    approved = pending(
        status=PortfolioActionStatus.APPROVED,
        action_type=PortfolioActionType.APPROVE,
        decided_by="admin-1",
        decided_at=datetime(2026, 9, 27, 13, 5, tzinfo=timezone.utc),
    )
    with pytest.raises(ValueError, match="PORTFOLIO_ACTION_NOT_PENDING"):
        PortfolioActionTransitionService(policy()).reject(
            approved, admin_context(), decided_at=datetime.now(timezone.utc)
        )


def test_planner_cannot_approve() -> None:
    with pytest.raises(AuthorizationError):
        PortfolioActionTransitionService(policy()).approve(
            pending(), planner_context(), decided_at=datetime.now(timezone.utc)
        )


def test_decision_timestamp_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="DECISION_TIMESTAMP_MUST_BE_TIMEZONE_AWARE"):
        PortfolioActionTransitionService(policy()).approve(
            pending(), admin_context(), decided_at=datetime(2026, 9, 27, 13, 5)
        )


def test_cancel_timestamp_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="PORTFOLIO_ACTION_TIMESTAMP_MUST_BE_TIMEZONE_AWARE"):
        PortfolioActionTransitionService(policy()).cancel(
            pending(), planner_context(), cancelled_at=datetime(2026, 9, 27, 13, 5)
        )
