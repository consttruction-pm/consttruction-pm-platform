from dataclasses import replace
from datetime import datetime, timezone

import pytest

from construction_pm.application.authorization import (
    AuthorizationContext,
    Permission,
    RoleBasedAuthorizationPolicy,
)
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.control_intelligence.contracts import SourceReference
from construction_pm.portfolio_action_transitions import PortfolioActionTransitionService
from construction_pm.portfolio_control_actions import (
    PortfolioActionType,
    PortfolioControlAction,
)
from construction_pm.portfolio_action_persistence import (
    PortfolioActionIdempotencyReuse,
    PortfolioRevisionConflict,
    PortfolioActionRevisionConflict,
    PortfolioActionTransitionMismatch,
    PostgresPortfolioActionStore,
)


class Cursor:
    def __init__(self, row=None):
        self.row = row

    def fetchone(self):
        return self.row


class RecordingConnection:
    def __init__(self):
        self.sql = []
        self.rows = {}
        self.commits = 0
        self.rollbacks = 0

    def execute(self, sql, params=()):
        self.sql.append((sql, params))
        if sql.startswith("SELECT fingerprint"):
            return Cursor(self.rows.get(("idem",) + params))
        if sql.startswith("SELECT revision"):
            return Cursor(self.rows.get(("revision",) + params))
        if sql.startswith("SELECT action_json, action_revision"):
            return Cursor(self.rows.get(("action",) + params))
        return Cursor()

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def replace_action_for_test(action_value, **changes):
    return replace(action_value, **changes)


def source():
    return SourceReference("source-1", "portfolio-control", "portfolio/P-1/snapshot", 12)


def action(**overrides):
    data = {
        "action_id": "action-1",
        "tenant_id": "tenant-1",
        "portfolio_id": "portfolio-1",
        "portfolio_revision": 12,
        "target_type": "project",
        "target_id": "project-1",
        "action_type": PortfolioActionType.HOLD_PROJECT,
        "source_snapshot_id": "snapshot-1",
        "expected_portfolio_revision": 0,
        "requested_by": "user-1",
        "requested_at": datetime(2026, 9, 27, 13, 0, tzinfo=timezone.utc),
        "idempotency_key": "idem-1",
        "evidence_refs": (source(),),
    }
    data.update(overrides)
    return PortfolioControlAction(**data)


def test_initialize_is_repeatable_and_scoped():
    connection = RecordingConnection()
    PostgresPortfolioActionStore(connection).initialize()
    PostgresPortfolioActionStore(connection).initialize()

    assert connection.sql[0][0].startswith("CREATE TABLE IF NOT EXISTS portfolio_control_revisions")
    assert "PRIMARY KEY (tenant_id, portfolio_id)" in connection.sql[0][0]
    assert "UNIQUE (tenant_id, portfolio_id, idempotency_key)" in connection.sql[1][0]
    assert any(sql.startswith("CREATE TABLE IF NOT EXISTS portfolio_control_action_audit") for sql, _ in connection.sql)


def test_transition_persists_next_revision_atomically():
    connection = RecordingConnection()
    connection.rows[("revision", "tenant-1", "portfolio-1")] = (0,)
    store = PostgresPortfolioActionStore(connection)
    transition = PortfolioActionTransitionService(
        RoleBasedAuthorizationPolicy({
            "admin": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE, Permission.PROJECT_ADMIN})
        })
    )
    approved = transition.approve(
        action(),
        AuthorizationContext("tenant-1", "project-1", "admin-1", frozenset({"admin"})),
        decided_at=datetime(2026, 9, 27, 13, 5, tzinfo=timezone.utc),
    )

    persisted = store.persist_transition(approved)

    assert persisted.action.portfolio_revision == 1
    assert persisted.action.status.value == "approved"
    assert persisted.action_revision == 1
    assert any(sql.startswith("UPDATE portfolio_control_revisions") for sql, _ in connection.sql)
    assert any(sql.startswith("INSERT INTO portfolio_control_actions") for sql, _ in connection.sql)


def test_stale_revision_is_rejected_before_write():
    connection = RecordingConnection()
    connection.rows[("revision", "tenant-1", "portfolio-1")] = (2,)
    store = PostgresPortfolioActionStore(connection)

    with pytest.raises(PortfolioRevisionConflict, match="expected=0 actual=2"):
        store.persist_transition(action())

    assert not any(sql.startswith("INSERT INTO portfolio_control_actions") for sql, _ in connection.sql)


def test_same_idempotency_key_replays_without_revision_advance():
    connection = RecordingConnection()
    persisted = action(portfolio_revision=1).as_dict()
    import json
    from construction_pm.portfolio_action_persistence import action_fingerprint
    connection.rows[("idem", "tenant-1", "portfolio-1", "idem-1")] = (
        action_fingerprint(action()),
        json.dumps(persisted),
        1,
    )
    store = PostgresPortfolioActionStore(connection)

    replay = store.persist_transition(action())
    assert replay.action.portfolio_revision == 1
    assert replay.action_revision == 1
    assert not any(sql.startswith("SELECT revision") for sql, _ in connection.sql)


def test_idempotency_key_reuse_is_rejected():
    connection = RecordingConnection()
    import json
    connection.rows[("idem", "tenant-1", "portfolio-1", "idem-1")] = (
        "different-fingerprint",
        json.dumps(action(portfolio_revision=1).as_dict()),
        1,
    )
    store = PostgresPortfolioActionStore(connection)

    with pytest.raises(PortfolioActionIdempotencyReuse, match="IDEMPOTENCY_KEY_REUSE"):
        store.persist_transition(action())


def test_transaction_rolls_back_on_revision_conflict():
    connection = RecordingConnection()
    connection.rows[("revision", "tenant-1", "portfolio-1")] = (3,)
    store = PostgresPortfolioActionStore(connection)

    with pytest.raises(PortfolioRevisionConflict):
        with PostgresTransactionManager(connection).transaction():
            store.persist_transition(action())

    assert connection.commits == 0
    assert connection.rollbacks == 1


def test_action_transition_increments_action_revision_and_appends_audit():
    connection = RecordingConnection()
    connection.rows[("revision", "tenant-1", "portfolio-1")] = (0,)
    store = PostgresPortfolioActionStore(connection)
    proposed = store.persist_transition(action())
    import json
    connection.rows[("action", "tenant-1", "portfolio-1", "action-1")] = (
        json.dumps(proposed.action.as_dict()),
        1,
    )
    approved = transition.approve(
        proposed.action,
        AuthorizationContext("tenant-1", "project-1", "admin-1", frozenset({"admin"})),
        decided_at=datetime(2026, 9, 27, 13, 5, tzinfo=timezone.utc),
    )
    transitioned = store.transition(
        approved,
        expected_action_revision=1,
        actor_id="admin-1",
        occurred_at=datetime(2026, 9, 27, 13, 5, tzinfo=timezone.utc),
        event_type="approved",
    )
    assert transitioned.action_revision == 2
    assert transitioned.action.status.value == "approved"
    assert transitioned.action.decided_by == "admin-1"
    assert any(sql.startswith("INSERT INTO portfolio_control_action_audit") for sql, _ in connection.sql)

def test_stale_action_revision_is_rejected():
    connection = RecordingConnection()
    connection.rows[("revision", "tenant-1", "portfolio-1")] = (0,)
    store = PostgresPortfolioActionStore(connection)
    proposed = store.persist_transition(action())
    connection.rows[("action", "tenant-1", "portfolio-1", "action-1")] = (1,)
    with pytest.raises(PortfolioActionRevisionConflict, match="expected=0 actual=1"):
        store.transition(
            proposed.action,
            expected_action_revision=0,
            actor_id="admin-1",
            occurred_at=datetime(2026, 9, 27, 13, 5, tzinfo=timezone.utc),
            event_type="approved",
        )

def test_transition_rejects_identity_mismatch():
    connection = RecordingConnection()
    connection.rows[("revision", "tenant-1", "portfolio-1")] = (0,)
    store = PostgresPortfolioActionStore(connection)
    proposed = store.persist_transition(action())
    import json
    connection.rows[("action", "tenant-1", "portfolio-1", "action-1")] = (
        json.dumps(proposed.action.as_dict()),
        1,
    )
    changed_target = replace_action_for_test(proposed.action, target_id="project-2")
    with pytest.raises(PortfolioActionTransitionMismatch, match="PORTFOLIO_ACTION_TRANSITION_MISMATCH"):
        store.transition(
            changed_target,
            expected_action_revision=1,
            actor_id="admin-1",
            occurred_at=datetime(2026, 9, 27, 13, 5, tzinfo=timezone.utc),
            event_type="approved",
        )


def test_transition_rejects_event_status_mismatch():
    connection = RecordingConnection()
    connection.rows[("revision", "tenant-1", "portfolio-1")] = (0,)
    store = PostgresPortfolioActionStore(connection)
    proposed = store.persist_transition(action())
    import json
    connection.rows[("action", "tenant-1", "portfolio-1", "action-1")] = (
        json.dumps(proposed.action.as_dict()),
        1,
    )
    policy = RoleBasedAuthorizationPolicy({
        "admin": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE, Permission.PROJECT_ADMIN})
    })
    transition = PortfolioActionTransitionService(policy)
    approved = transition.approve(
        proposed.action,
        AuthorizationContext("tenant-1", "project-1", "admin-1", frozenset({"admin"})),
        decided_at=datetime(2026, 9, 27, 13, 5, tzinfo=timezone.utc),
    )
    with pytest.raises(PortfolioActionTransitionMismatch, match="PORTFOLIO_ACTION_EVENT_MISMATCH"):
        store.transition(
            approved,
            expected_action_revision=1,
            actor_id="admin-1",
            occurred_at=datetime(2026, 9, 27, 13, 5, tzinfo=timezone.utc),
            event_type="rejected",
        )
