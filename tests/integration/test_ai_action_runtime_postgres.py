from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest

psycopg = pytest.importorskip("psycopg")

from construction_pm.ai_action_activity_tools import build_activity_create_runtime
from construction_pm.ai_action_boundary import (
    AIActionPermissionGrant,
    AIActionProposal,
    UserConfiguredAIActionPermissionAdapter,
)
from construction_pm.application.authorization import default_project_policy
from construction_pm.activity_master_repository import PostgresActivityMasterRepository
from construction_pm.backend_p0.models import BackendScope
from construction_pm.client_sync.postgres_transaction import PostgresTransactionManager
from construction_pm.quantity_takeoff import PostgresQuantityTakeoffRepository
from construction_pm.ai_action_runtime import (
    AIActionRuntimeContext,
    AIActionRuntimeError,
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



def test_postgres_authenticated_activity_create_uses_shared_transaction_and_fresh_readback(postgres_connection):
    suffix = uuid4().hex
    tenant_id = f"tenant-ai-act-{suffix}"
    project_id = f"project-ai-act-{suffix}"
    scope = BackendScope(tenant_id, project_id, 12)
    transaction_manager = PostgresTransactionManager(postgres_connection)
    activity_repository = PostgresActivityMasterRepository(postgres_connection)
    activity_repository.initialize()

    grant = AIActionPermissionGrant(
        subject_id="user-1",
        tenant_id=tenant_id,
        project_id=project_id,
        project_revision_id="12",
        resource_domain="activities",
        operation="create",
        tool_name="activity.create",
    )
    runtime = build_activity_create_runtime(
        activity_master_repository=activity_repository,
        authorization_policy=default_project_policy(),
        permission_adapter=UserConfiguredAIActionPermissionAdapter(lambda: (grant,)),
        transaction_manager=transaction_manager,
    )
    # Commit schema initialization before the request-level transaction lifecycle.
    postgres_connection.commit()

    context = AIActionRuntimeContext(
        subject_id="user-1",
        tenant_id=tenant_id,
        project_id=project_id,
        project_revision_id="12",
        roles=frozenset({"project_admin"}),
    )
    proposal = runtime.propose(
        context,
        tool_name="activity.create",
        payload={
            "activity_id": "A-POSTGRES-1",
            "name": "Foundation excavation",
            "duration_value": "2.5",
            "duration_unit": "working-day",
        },
        evidence_refs=("import-row-3",),
    )
    assert proposal.status == "proposed"

    approved = runtime.decide(context, proposal.proposal.proposal_id, approved=True)
    assert approved.status == "approved"
    result = runtime.execute(context, proposal.proposal.proposal_id)
    assert result.status == "executed"
    assert result.result is not None
    assert result.result["activity"]["activity_id"] == "A-POSTGRES-1"

    fresh_connection = psycopg.connect(
        os.getenv("P6_TEST_POSTGRES_DSN") or os.environ["CONSTRUCTION_PM_POSTGRES_DSN"]
    )
    try:
        fresh_activity_repository = PostgresActivityMasterRepository(fresh_connection)
        persisted_activity = fresh_activity_repository.get(scope, "A-POSTGRES-1")
        assert persisted_activity is not None
        assert str(persisted_activity.duration_value) == "2.5"
        assert persisted_activity.name == "Foundation excavation"

        fresh_store = PostgresAIActionRuntimeStore(fresh_connection)
        persisted_proposal = fresh_store.get(
            proposal.proposal.proposal_id,
            tenant_id=tenant_id,
            project_id=project_id,
        )
        assert persisted_proposal is not None
        assert persisted_proposal.status == "executed"
        assert persisted_proposal.result == result.result

        idem = fresh_connection.execute(
            "SELECT fingerprint, result_json FROM ai_action_tool_idempotency "
            "WHERE tenant_id=%s AND project_id=%s AND tool_name=%s AND idempotency_key=%s",
            (tenant_id, project_id, "activity.create", proposal.proposal.proposal_id),
        ).fetchone()
        assert idem is not None
        assert json.loads(idem[1]) == result.result
    finally:
        fresh_connection.close()

    with transaction_manager.transaction():
        postgres_connection.execute(
            "DELETE FROM activity_master WHERE tenant_id=%s AND project_id=%s",
            (tenant_id, project_id),
        )
        postgres_connection.execute(
            "DELETE FROM ai_action_tool_idempotency WHERE tenant_id=%s AND project_id=%s",
            (tenant_id, project_id),
        )
        postgres_connection.execute(
            "DELETE FROM ai_action_audit_events WHERE tenant_id=%s AND project_id=%s",
            (tenant_id, project_id),
        )
        postgres_connection.execute(
            "DELETE FROM ai_action_proposals WHERE tenant_id=%s AND project_id=%s",
            (tenant_id, project_id),
        )


def test_postgres_takeoff_action_requires_approval_and_reads_back_from_fresh_connection(postgres_connection):
    suffix = uuid4().hex
    tenant_id = f"tenant-ai-boq-{suffix}"
    project_id = f"project-ai-boq-{suffix}"
    scope = BackendScope(tenant_id, project_id, 12)
    transaction_manager = PostgresTransactionManager(postgres_connection)
    activity_repository = PostgresActivityMasterRepository(postgres_connection)
    activity_repository.initialize()

    grants = (
        AIActionPermissionGrant(
            subject_id="user-1", tenant_id=tenant_id, project_id=project_id,
            project_revision_id="12", resource_domain="activities", operation="create",
            tool_name="activity.create",
        ),
        AIActionPermissionGrant(
            subject_id="user-1", tenant_id=tenant_id, project_id=project_id,
            project_revision_id="12", resource_domain="quantity_takeoff", operation="create",
            tool_name="quantity.takeoff.create",
        ),
    )
    runtime = build_activity_create_runtime(
        activity_master_repository=activity_repository,
        authorization_policy=default_project_policy(),
        permission_adapter=UserConfiguredAIActionPermissionAdapter(lambda: grants),
        transaction_manager=transaction_manager,
    )
    postgres_connection.commit()

    context = AIActionRuntimeContext(
        subject_id="user-1", tenant_id=tenant_id, project_id=project_id,
        project_revision_id="12", roles=frozenset({"project_admin"}),
    )
    payload = {
        "estimate_id": "BOQ-PG-01",
        "name": "Concrete foundation estimate",
        "lines": [{
            "line_id": "CONC-01",
            "description": "Pile cap concrete",
            "unit": "m3",
            "base_quantity": 10,
            "waste_percent": 5,
            "measurement_status": "measured",
            "measurement_basis": "Length × width × depth from controlled drawing",
            "source_ref": "drawing:S-101/pile-cap-PC01",
            "classification_code": "03.30.00",
            "unit_rate": 100,
            "currency": "EUR",
            "currency_minor_units": 2,
            "rate_basis": "quotation:approved-Q-2026-104",
        }],
    }
    proposal = runtime.propose(
        context, tool_name="quantity.takeoff.create", payload=payload,
        evidence_refs=("drawing:S-101/pile-cap-PC01",),
    )
    assert proposal.status == "proposed"
    takeoff_repository = PostgresQuantityTakeoffRepository(postgres_connection)
    assert takeoff_repository.get(scope, "BOQ-PG-01") is None

    approved = runtime.decide(context, proposal.proposal.proposal_id, approved=True)
    assert approved.status == "approved"
    result = runtime.execute(context, proposal.proposal.proposal_id)
    assert result.status == "executed"
    assert result.result is not None
    assert result.result["summary"]["totals_by_currency"] == [
        {"currency": "EUR", "minor_units": 2, "subtotal": "1050.00"}
    ]

    fresh_connection = psycopg.connect(
        os.getenv("P6_TEST_POSTGRES_DSN") or os.environ["CONSTRUCTION_PM_POSTGRES_DSN"]
    )
    try:
        fresh_takeoff_repository = PostgresQuantityTakeoffRepository(fresh_connection)
        persisted = fresh_takeoff_repository.get(scope, "BOQ-PG-01")
        assert persisted is not None
        assert persisted.to_payload() == result.result

        fresh_store = PostgresAIActionRuntimeStore(fresh_connection)
        stored_proposal = fresh_store.get(
            proposal.proposal.proposal_id,
            tenant_id=tenant_id,
            project_id=project_id,
        )
        assert stored_proposal is not None
        assert stored_proposal.status == "executed"
        assert stored_proposal.result == result.result

        idem = fresh_connection.execute(
            "SELECT fingerprint, result_json FROM ai_action_tool_idempotency "
            "WHERE tenant_id=%s AND project_id=%s AND tool_name=%s AND idempotency_key=%s",
            (tenant_id, project_id, "quantity.takeoff.create", proposal.proposal.proposal_id),
        ).fetchone()
        assert idem is not None
        assert json.loads(idem[1]) == result.result
    finally:
        fresh_connection.close()

    with transaction_manager.transaction():
        postgres_connection.execute(
            "DELETE FROM quantity_takeoff_estimates WHERE tenant_id=%s AND project_id=%s",
            (tenant_id, project_id),
        )
        postgres_connection.execute(
            "DELETE FROM ai_action_tool_idempotency WHERE tenant_id=%s AND project_id=%s",
            (tenant_id, project_id),
        )
        postgres_connection.execute(
            "DELETE FROM ai_action_audit_events WHERE tenant_id=%s AND project_id=%s",
            (tenant_id, project_id),
        )
        postgres_connection.execute(
            "DELETE FROM ai_action_proposals WHERE tenant_id=%s AND project_id=%s",
            (tenant_id, project_id),
        )
