from datetime import datetime, timezone
import os
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")

DSN = os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
if not DSN:
    pytest.skip("CONSTRUCTION_PM_POSTGRES_DSN is not configured", allow_module_level=True)

from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.control_intelligence.contracts import SourceReference
from construction_pm.control_intelligence.portfolio_decision import approve_portfolio_decision
from construction_pm.portfolio_decision_persistence import PostgresPortfolioDecisionStore
from construction_pm.control_intelligence.portfolio_decision import PortfolioDecisionBoundary


def test_portfolio_decision_round_trip_persists_revision_and_audit() -> None:
    suffix = uuid.uuid4().hex
    tenant_id = f"live-tenant-{suffix}"
    portfolio_id = f"live-portfolio-{suffix}"
    decision_id = f"live-decision-{suffix}"
    idempotency_key = f"live-idem-{suffix}"
    proposed_at = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)
    approved_at = datetime(2026, 9, 27, 15, 5, tzinfo=timezone.utc)

    decision = PortfolioDecisionBoundary(
        decision_id=decision_id,
        portfolio_id=portfolio_id,
        tenant_id=tenant_id,
        status="proposed",
        decision_type="review",
        title_key="decision.review",
        evidence_refs=(
            SourceReference("live-source", "snapshot", "$.portfolio", 1),
        ),
    )

    with psycopg.connect(DSN) as connection:
        store = PostgresPortfolioDecisionStore(connection)
        store.initialize()
        connection.commit()

        with PostgresTransactionManager(connection).transaction():
            persisted = store.persist(
                decision,
                idempotency_key=idempotency_key,
                actor_id="requester-1",
                occurred_at=proposed_at,
            )

        assert persisted.decision_revision == 1
        loaded = store.get(tenant_id, portfolio_id, decision_id)
        assert loaded.decision == decision
        assert loaded.decision_revision == 1

        approved = approve_portfolio_decision(
            decision,
            approved_by="approver-1",
            approved_at=approved_at,
        )
        with PostgresTransactionManager(connection).transaction():
            transitioned = store.transition(
                approved,
                expected_decision_revision=1,
                actor_id="approver-1",
                occurred_at=approved_at,
                event_type="approved",
            )

        assert transitioned.decision_revision == 2
        assert transitioned.decision.status == "approved"
        history = store.history(tenant_id, portfolio_id, decision_id)
        assert [(event.decision_revision, event.event_type, event.actor_id) for event in history] == [
            (1, "proposed", "requester-1"),
            (2, "approved", "approver-1"),
        ]
