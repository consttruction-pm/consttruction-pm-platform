from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.ai_action_boundary import AIActionProposal
from construction_pm.ai_action_runtime import (
    AIActionStoredProposal,
    PostgresAIActionRuntimeStore,
)


@pytest.fixture()
def postgres_connection():
    dsn = os.getenv("P6_TEST_POSTGRES_DSN") or os.getenv("CONSTRUCTION_PM_POSTGRES_DSN")
    if not dsn:
        pytest.skip("P6_TEST_POSTGRES_DSN is not configured")
    connection = psycopg.connect(dsn)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def test_postgres_action_proposal_and_audit_round_trip(postgres_connection):
    suffix = uuid4().hex
    now = datetime.now(timezone.utc)
    proposal = AIActionProposal(
        tenant_id=f"tenant-{suffix}",
        project_id=f"project-{suffix}",
        proposal_id=f"proposal-{suffix}",
        tool_name="activity.create",
        action="create",
        requires_human_approval=True,
        requested_by="user-1",
        evidence_refs=("source-row-1",),
        project_revision_id="revision-12",
        resource_domain="activities",
    )
    store = PostgresAIActionRuntimeStore(postgres_connection)

    with postgres_connection.transaction():
        store.create(AIActionStoredProposal(
            proposal=proposal,
            payload={"name": "Excavation"},
            status="proposed",
            created_at=now,
            updated_at=now,
        ))
        stored = store.get(
            proposal.proposal_id,
            tenant_id=proposal.tenant_id,
            project_id=proposal.project_id,
        )
        assert stored is not None
        assert stored.proposal == proposal
        assert stored.payload == {"name": "Excavation"}

        store.record_event(
            proposal, "proposal_created", actor_id="user-1",
            metadata={"status": "proposed"}, happened_at=now,
        )
        assert store.transition(
            proposal,
            expected_status="proposed",
            next_status="approved",
            updated_at=now,
            decided_by="user-1",
        )
        assert not store.transition(
            proposal,
            expected_status="proposed",
            next_status="approved",
            updated_at=now,
            decided_by="user-1",
        )
