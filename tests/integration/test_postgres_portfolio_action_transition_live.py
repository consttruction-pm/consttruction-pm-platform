import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")
DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.application.authorization import AuthorizationContext, Permission, RoleBasedAuthorizationPolicy
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.control_intelligence.contracts import SourceReference
from construction_pm.portfolio_action_persistence import PostgresPortfolioActionStore, PortfolioActionTransitionMismatch
from construction_pm.portfolio_action_transitions import PortfolioActionTransitionService
from construction_pm.portfolio_control_actions import PortfolioActionType, PortfolioControlAction


def make_action(tenant: str, portfolio: str) -> PortfolioControlAction:
    token = uuid4().hex
    return PortfolioControlAction(
        action_id="action-" + token,
        tenant_id=tenant,
        portfolio_id=portfolio,
        portfolio_revision=0,
        target_type="project",
        target_id="project-live-1",
        action_type=PortfolioActionType.HOLD_PROJECT,
        source_snapshot_id="snapshot-live-1",
        expected_portfolio_revision=0,
        requested_by="requester-live",
        requested_at=datetime.now(timezone.utc),
        idempotency_key="idem-" + token,
        evidence_refs=(SourceReference("source-live", "portfolio-control", "portfolio/live/snapshot", 1),),
    )


def policy() -> RoleBasedAuthorizationPolicy:
    return RoleBasedAuthorizationPolicy({
        "admin": frozenset({Permission.PROJECT_READ, Permission.PROJECT_WRITE, Permission.PROJECT_ADMIN})
    })


def test_real_postgres_persists_transition_and_audit_atomically() -> None:
    tenant = "live-transition-" + uuid4().hex
    portfolio = "portfolio-" + uuid4().hex
    action = make_action(tenant, portfolio)
    transition = PortfolioActionTransitionService(policy())
    context = AuthorizationContext(tenant, "project-live-1", "admin-live", frozenset({"admin"}))

    with psycopg.connect(DSN) as connection:
        store = PostgresPortfolioActionStore(connection)
        store.initialize()
        store.ensure_portfolio(tenant, portfolio)
        connection.commit()

        with PostgresTransactionManager(connection).transaction():
            proposed = store.persist_transition(action)
            decided_at = datetime.now(timezone.utc)
            approved = transition.approve(
                proposed.action,
                context,
                decided_at=decided_at,
            )
            persisted = store.transition(
                approved,
                expected_action_revision=proposed.action_revision,
                actor_id="admin-live",
                occurred_at=decided_at,
                event_type="approved",
            )

        assert persisted.action_revision == 2
        assert persisted.action.status.value == "approved"
        assert persisted.action.decided_by == "admin-live"

        history = store.history(tenant, portfolio, action.action_id)
        assert [event.action_revision for event in history] == [1, 2]
        assert [event.event_type for event in history] == ["proposed", "approved"]
        assert history[-1].actor_id == "admin-live"

        stored = store.get(tenant, portfolio, action.action_id)
        assert stored is not None
        assert stored.action_revision == 2
        assert stored.action.status.value == "approved"

        mismatched = PortfolioControlAction(
            action_id=approved.action_id,
            tenant_id=approved.tenant_id,
            portfolio_id=approved.portfolio_id,
            portfolio_revision=approved.portfolio_revision,
            target_type=approved.target_type,
            target_id="different-project",
            action_type=approved.action_type,
            source_snapshot_id=approved.source_snapshot_id,
            expected_portfolio_revision=approved.expected_portfolio_revision,
            requested_by=approved.requested_by,
            requested_at=approved.requested_at,
            status=approved.status,
            requires_approval=approved.requires_approval,
            idempotency_key=approved.idempotency_key,
            rationale_key=approved.rationale_key,
            evidence_refs=approved.evidence_refs,
            decided_by=approved.decided_by,
            decided_at=approved.decided_at,
        )
        with pytest.raises(PortfolioActionTransitionMismatch):
            store.transition(
                mismatched,
                expected_action_revision=2,
                actor_id="admin-live",
                occurred_at=datetime.now(timezone.utc),
                event_type="approved",
            )
