from __future__ import annotations

import sqlite3
from decimal import Decimal
from datetime import datetime, timezone

import pytest

from construction_pm.ai_action_activity_tools import (
    SQLiteAIActionExecutionIdempotencyStore,
)
from construction_pm.ai_action_boundary import (
    AIActionPermissionGrant,
    UserConfiguredAIActionPermissionAdapter,
)
from construction_pm.ai_action_resource_tools import build_resource_assignment_create_tool
from construction_pm.ai_action_runtime import (
    AIActionRuntime,
    AIActionRuntimeContext,
    AIActionRuntimeError,
    SQLiteAIActionRuntimeStore,
)
from construction_pm.activity_master_repository import (
    ActivityMaster,
    SQLiteActivityMasterRepository,
)
from construction_pm.application.authorization import default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.p6_activity_master_api import P6ActivityMasterAPI
from construction_pm.p6_resource_assignment_repository import (
    P6ResourceAssignmentApplicationService,
    P6ResourceAssignmentPeriodApplicationService,
    SQLiteP6ResourceAssignmentPeriodRepository,
    SQLiteP6ResourceAssignmentRepository,
)
from construction_pm.p6_resource_read_api import P6ResourceReadAPI
from construction_pm.p6_resource_spread_repository import (
    P6ResourceSpreadApplicationService,
    SQLiteP6ResourceSpreadRepository,
)
from construction_pm.p6_resource_write_api import P6ResourceWriteAPI
from construction_pm.scheduling.time_duration import DurationUnit


def setup_runtime(database_path):
    connection = sqlite3.connect(str(database_path))
    transaction_manager = SQLiteTransactionManager(connection)
    policy = default_project_policy()
    scope = BackendScope("tenant-1", "project-1", 12)
    activities = SQLiteActivityMasterRepository(connection)
    activities.save(
        ActivityMaster(
            scope=scope,
            activity_id="ACT-EXC-01",
            duration_value=Decimal("3"),
            duration_unit=DurationUnit.WORKING_DAY,
            name="Excavation",
        ),
        expected_revision=0,
    )
    assignment_repo = SQLiteP6ResourceAssignmentRepository(connection)
    period_repo = SQLiteP6ResourceAssignmentPeriodRepository(connection)
    spread_repo = SQLiteP6ResourceSpreadRepository(connection)
    assignment_service = P6ResourceAssignmentApplicationService(
        assignment_repo, transaction_manager
    )
    period_service = P6ResourceAssignmentPeriodApplicationService(
        period_repo, transaction_manager
    )
    spread_service = P6ResourceSpreadApplicationService(
        spread_repo, transaction_manager
    )
    resource_read_api = P6ResourceReadAPI(
        assignment_service, period_service, spread_service, policy
    )
    resource_write_api = P6ResourceWriteAPI(
        period_service, policy, assignment_service
    )
    action_store = SQLiteAIActionRuntimeStore(connection)
    idempotency = SQLiteAIActionExecutionIdempotencyStore(connection)
    grant = AIActionPermissionGrant(
        subject_id="user-1",
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision_id="12",
        resource_domain="resources",
        operation="create",
        tool_name="resource.assignment.create",
    )
    activity_api = P6ActivityMasterAPI(activities, policy)
    tool = build_resource_assignment_create_tool(
        activity_api=activity_api,
        resource_write_api=resource_write_api,
        resource_read_api=resource_read_api,
        idempotency_store=idempotency,
        transaction_manager=transaction_manager,
    )
    runtime = AIActionRuntime(
        store=action_store,
        permission_adapter=UserConfiguredAIActionPermissionAdapter(lambda: (grant,)),
        audit_sink=action_store,
        tools=(tool,),
        clock=lambda: datetime(2026, 10, 28, 12, tzinfo=timezone.utc),
        transaction_manager=transaction_manager,
    )
    context = AIActionRuntimeContext(
        subject_id="user-1",
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision_id="12",
        roles=frozenset({"project_admin"}),
    )
    return connection, scope, assignment_service, runtime, context


def payload(**overrides):
    value = {
        "assignment_id": "RA-EXC-01",
        "activity_id": "ACT-EXC-01",
        "resource_id": "EXCAVATOR-01",
        "units": "1",
        "unit": "machine",
        "planned_cost": "850.00",
        "currency": "EUR",
        "role_id": "earthworks-excavator",
        "calendar_id": "CAL-EQUIP-01",
        "calendar_version": "v1",
        "note": "User-selected equipment. Capacity review is still required.",
    }
    value.update(overrides)
    return value


def test_resource_assignment_is_proposed_then_approved_and_fresh_readback_verified(tmp_path):
    connection, scope, assignment_service, runtime, context = setup_runtime(
        tmp_path / "resource-action.sqlite3"
    )
    try:
        proposed = runtime.propose(
            context,
            tool_name="resource.assignment.create",
            payload=payload(),
        )
        assert proposed.status == "proposed"
        assert assignment_service.read(scope, "RA-EXC-01") is None

        approved = runtime.decide(context, proposed.proposal.proposal_id, approved=True)
        assert approved.status == "approved"

        executed = runtime.execute(context, proposed.proposal.proposal_id)
        assert executed.status == "executed"
        assert executed.result is not None
        assert executed.result["persisted_readback_verified"] is True
        assert executed.result["resource_reference_status"] == "unverified_reference"
        assert executed.result["capacity_check_status"] == "not_performed"
        assert executed.result["assignment"]["activity_id"] == "ACT-EXC-01"
        assert executed.result["assignment"]["resource_id"] == "EXCAVATOR-01"
        assert executed.result["assignment"]["units"] == "1"
        assert executed.result["assignment"]["planned_cost"] == "850.00"

        fresh = assignment_service.read(scope, "RA-EXC-01")
        assert fresh is not None
        assert fresh.activity_id == "ACT-EXC-01"
        assert fresh.resource_id == "EXCAVATOR-01"
        assert fresh.units == Decimal("1")
        assert fresh.planned_cost == Decimal("850.00")

        assert connection.execute(
            "SELECT COUNT(*) FROM ai_action_tool_idempotency "
            "WHERE tenant_id=? AND project_id=? AND tool_name=?",
            ("tenant-1", "project-1", "resource.assignment.create"),
        ).fetchone()[0] == 1
    finally:
        connection.close()


def test_resource_assignment_rejects_missing_activity_and_invalid_cost_currency(tmp_path):
    connection, scope, assignment_service, runtime, context = setup_runtime(
        tmp_path / "resource-invalid.sqlite3"
    )
    try:
        with pytest.raises(ValueError, match="AI_ACTION_TOOL_PAYLOAD_INVALID"):
            runtime.propose(
                context,
                tool_name="resource.assignment.create",
                payload=payload(currency=None),
            )
        proposed = runtime.propose(
            context,
            tool_name="resource.assignment.create",
            payload=payload(activity_id="ACT-DOES-NOT-EXIST", assignment_id="RA-MISSING-ACTIVITY"),
        )
        runtime.decide(context, proposed.proposal.proposal_id, approved=True)
        # The execution handler rechecks the live activity and records a non-replayable
        # uncertain result; no resource assignment may be written for an unknown activity.
        with pytest.raises(AIActionRuntimeError):
            runtime.execute(context, proposed.proposal.proposal_id)
        assert assignment_service.list(scope) == ()
        persisted = runtime.get_proposal(context, proposed.proposal.proposal_id)
        assert persisted.status == "uncertain"
    finally:
        connection.close()


def test_resource_assignment_rejects_unapproved_execution_and_does_not_write(tmp_path):
    connection, scope, assignment_service, runtime, context = setup_runtime(
        tmp_path / "resource-unapproved.sqlite3"
    )
    try:
        proposed = runtime.propose(
            context,
            tool_name="resource.assignment.create",
            payload=payload(),
        )
        with pytest.raises(Exception):
            runtime.execute(context, proposed.proposal.proposal_id)
        assert assignment_service.read(scope, "RA-EXC-01") is None
    finally:
        connection.close()
