from datetime import datetime, timezone
import sqlite3

import pytest

from construction_pm.application.authorization import (
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
from construction_pm.portfolio_control_action_application import (
    PortfolioControlActionApplicationService,
)
from construction_pm.portfolio_control_action_store import (
    SQLitePortfolioControlActionStore,
)


def source() -> SourceReference:
    return SourceReference("snapshot-1", "portfolio-control", "portfolio/1/snapshot", 30)


def action(**overrides: object) -> PortfolioControlAction:
    values: dict[str, object] = {
        "action_id": "A-1",
        "tenant_id": "tenant-1",
        "portfolio_id": "portfolio-1",
        "portfolio_revision": 30,
        "target_type": "project",
        "target_id": "project-1",
        "action_type": PortfolioActionType.HOLD_PROJECT,
        "source_snapshot_id": "snapshot-1",
        "expected_portfolio_revision": 30,
        "requested_by": "planner-1",
        "requested_at": datetime(2026, 9, 27, 16, 0, tzinfo=timezone.utc),
        "idempotency_key": "idem-A-1",
        "evidence_refs": (source(),),
    }
    values.update(overrides)
    return PortfolioControlAction(**values)


def auth(roles=frozenset({"planner"}), project="project-1"):
    return AuthorizationContext("tenant-1", project, "user-1", roles)


def policy():
    return RoleBasedAuthorizationPolicy(
        {
            "planner": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE}),
            "admin": frozenset(
                {Permission.PROJECT_READ, Permission.PROJECT_WRITE, Permission.PROJECT_ADMIN}
            ),
        }
    )


def stack():
    connection = sqlite3.connect(":memory:")
    store = SQLitePortfolioControlActionStore(connection)
    authorization = PortfolioControlActionService(policy())
    service = PortfolioControlActionApplicationService(store, authorization)
    return connection, store, service


def test_create_is_idempotent_and_replays_same_authoritative_action():
    connection, store, _ = stack()
    first = store.create(action())
    replay = store.create(action())

    assert first.action == replay.action
    assert first.action_revision == replay.action_revision == 1

    approved = service.decide(
        first.action,
        auth_context=auth(frozenset({"admin"})),
        expected_action_revision=1,
        status=PortfolioActionStatus.APPROVED,
        actor_id="admin-1",
        occurred_at=datetime(2026, 9, 27, 16, 5, tzinfo=timezone.utc),
    )
    replay_after_decision = store.create(action())
    assert approved.action_revision == 2
    assert replay_after_decision.action_revision == 1
    assert replay_after_decision.action.status is PortfolioActionStatus.PROPOSED

    changed = action(idempotency_key="idem-A-1", target_id="project-2")
    with pytest.raises(ValueError, match="IDEMPOTENCY_KEY_REUSE"):
        store.create(changed)
    connection.close()


def test_audit_is_append_only_and_revisioned():
    connection, store, service = stack()
    proposed = service.propose(action(), auth_context=auth())
    approved = service.decide(
        proposed.action,
        auth_context=auth(frozenset({"admin"})),
        expected_action_revision=proposed.action_revision,
        status=PortfolioActionStatus.APPROVED,
        actor_id="admin-1",
        occurred_at=datetime(2026, 9, 27, 16, 5, tzinfo=timezone.utc),
    )

    assert approved.action_revision == 2
    history = store.history("tenant-1", "portfolio-1", "A-1")
    assert [item.action_revision for item in history] == [1, 2]
    assert [item.event_type for item in history] == ["proposed", "approved"]
    assert history[0].actor_id == "planner-1"
    assert history[1].actor_id == "admin-1"
    connection.close()


def test_stale_action_revision_is_rejected():
    connection, store, service = stack()
    proposed = service.propose(action(), auth_context=auth())
    service.decide(
        proposed.action,
        auth_context=auth(frozenset({"admin"})),
        expected_action_revision=1,
        status=PortfolioActionStatus.REJECTED,
        actor_id="admin-1",
        occurred_at=datetime(2026, 9, 27, 16, 5, tzinfo=timezone.utc),
    )

    with pytest.raises(ValueError, match="STALE_REVISION"):
        service.decide(
            proposed.action,
            auth_context=auth(frozenset({"admin"})),
            expected_action_revision=1,
            status=PortfolioActionStatus.APPROVED,
            actor_id="admin-2",
            occurred_at=datetime(2026, 9, 27, 16, 6, tzinfo=timezone.utc),
        )
    connection.close()


def test_project_request_and_portfolio_decision_authorization():
    connection, _, service = stack()
    service.propose(action(), auth_context=auth())
    portfolio_action = action(
        action_id="A-2",
        target_type="portfolio",
        target_id="portfolio-1",
        action_type=PortfolioActionType.REQUEST_REVIEW,
        idempotency_key="idem-A-2",
    )
    with pytest.raises(Exception):
        service.propose(portfolio_action, auth_context=auth())
    service.propose(portfolio_action, auth_context=auth(frozenset({"admin"})))
    connection.close()


def test_transition_failure_rolls_back_action_and_audit():
    connection, store, _ = stack()
    proposed = store.create(action())
    with pytest.raises(ValueError, match="not-found"):
        store.transition(
            action=action(action_id="missing"),
            expected_action_revision=1,
            actor_id="admin-1",
            occurred_at=datetime(2026, 9, 27, 16, 5, tzinfo=timezone.utc),
            event_type="approved",
        )
    assert store.get("tenant-1", "portfolio-1", "A-1") == proposed
    assert len(store.history("tenant-1", "portfolio-1", "A-1")) == 1
    connection.close()


def test_nested_transaction_uses_distinct_savepoints():
    connection, store, _ = stack()
    action_one = action()
    action_two = action(action_id="A-2", idempotency_key="idem-A-2")
    with store._transaction():
        store.create(action_one)
        with store._transaction():
            store.create(action_two)
    assert store.get("tenant-1", "portfolio-1", "A-1") is not None
    assert store.get("tenant-1", "portfolio-1", "A-2") is not None
    connection.close()
