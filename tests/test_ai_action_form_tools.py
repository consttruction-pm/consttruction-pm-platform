from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from construction_pm.ai_action_activity_tools import SQLiteAIActionExecutionIdempotencyStore
from construction_pm.ai_action_boundary import (
    AIActionPermissionGrant,
    UserConfiguredAIActionPermissionAdapter,
)
from construction_pm.ai_action_form_tools import build_form_definition_create_tool
from construction_pm.ai_action_runtime import (
    AIActionRuntime,
    AIActionRuntimeContext,
    AIActionRuntimeError,
    SQLiteAIActionRuntimeStore,
)
from construction_pm.application.authorization import default_project_policy
from construction_pm.backend_p0.models import BackendScope
from construction_pm.backend_p0.transactions import SQLiteTransactionManager
from construction_pm.project_forms import (
    FormBuilderAPI,
    SQLiteFormBuilderRepository,
)


NOW = datetime(2026, 10, 28, 12, tzinfo=timezone.utc)


def setup_runtime(database_path):
    connection = sqlite3.connect(str(database_path))
    transaction_manager = SQLiteTransactionManager(connection)
    policy = default_project_policy()
    repository = SQLiteFormBuilderRepository(connection)
    form_api = FormBuilderAPI(
        repository,
        policy,
        transaction_manager,
        clock=lambda: NOW,
    )
    store = SQLiteAIActionRuntimeStore(connection)
    idempotency = SQLiteAIActionExecutionIdempotencyStore(connection)
    grant = AIActionPermissionGrant(
        subject_id="owner-1",
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision_id="12",
        resource_domain="forms",
        operation="create",
        tool_name="form.definition.create",
    )
    tool = build_form_definition_create_tool(
        form_api=form_api,
        idempotency_store=idempotency,
        transaction_manager=transaction_manager,
    )
    runtime = AIActionRuntime(
        store=store,
        permission_adapter=UserConfiguredAIActionPermissionAdapter(lambda: (grant,)),
        audit_sink=store,
        tools=(tool,),
        clock=lambda: NOW,
        transaction_manager=transaction_manager,
    )
    context = AIActionRuntimeContext(
        subject_id="owner-1",
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision_id="12",
        roles=frozenset({"project_admin"}),
    )
    scope = BackendScope("tenant-1", "project-1", 12)
    return connection, repository, form_api, runtime, context, scope


def form_payload(**overrides):
    payload = {
        "form_id": "DAILY-LOG-01",
        "name": "Daily site report",
        "description": "Record work completed and resources used during the shift.",
        "sections": [
            {
                "section_id": "WORK",
                "title": "Work completed",
                "localized_titles": {"fa": "کار انجام‌شده"},
            },
            {
                "section_id": "RESOURCES",
                "title": "Resources",
                "localized_titles": {"fa": "منابع"},
            },
        ],
        "fields": [
            {
                "field_id": "ACTIVITY-ID",
                "section_id": "WORK",
                "field_type": "text",
                "label": "Activity ID",
                "required": True,
                "options": [],
                "localized_labels": {"fa": "شناسه فعالیت"},
                "minimum": None,
                "maximum": None,
                "min_length": 3,
                "max_length": 64,
            },
            {
                "field_id": "QUANTITY",
                "section_id": "WORK",
                "field_type": "number",
                "label": "Quantity completed",
                "required": True,
                "options": [],
                "localized_labels": {"fa": "مقدار انجام‌شده"},
                "minimum": "0",
                "maximum": "1000000",
                "min_length": None,
                "max_length": None,
            },
            {
                "field_id": "WORK-DATE",
                "section_id": "WORK",
                "field_type": "date",
                "label": "Work date",
                "required": True,
                "options": [],
                "localized_labels": {"fa": "تاریخ کار"},
                "minimum": None,
                "maximum": None,
                "min_length": None,
                "max_length": None,
            },
            {
                "field_id": "EQUIPMENT-USED",
                "section_id": "RESOURCES",
                "field_type": "boolean",
                "label": "Equipment used",
                "required": False,
                "options": [],
                "localized_labels": {"fa": "استفاده از ماشین‌آلات"},
                "minimum": None,
                "maximum": None,
                "min_length": None,
                "max_length": None,
            },
        ],
        "shared_with_user_ids": ["worker-1"],
        "shared_with_roles": ["field_worker"],
        "approver_user_ids": ["owner-1"],
        "approver_roles": ["project_admin"],
        "output_mappings": [
            {
                "field_id": "QUANTITY",
                "target_domain": "daily_field_log",
                "target_field": "quantity_completed",
            }
        ],
        "requires_approval": True,
        "expected_latest_version": None,
    }
    payload.update(overrides)
    return payload


def test_ai_form_tool_requires_approval_persists_draft_and_verifies_readback(tmp_path):
    connection, repository, form_api, runtime, context, scope = setup_runtime(
        tmp_path / "assistant-form.sqlite3"
    )
    try:
        proposed = runtime.propose(
            context, tool_name="form.definition.create", payload=form_payload()
        )
        assert proposed.status == "proposed"
        assert repository.latest_definition(
            scope.tenant_id, scope.project_id, "DAILY-LOG-01"
        ) is None

        approved = runtime.decide(
            context, proposed.proposal.proposal_id, approved=True
        )
        assert approved.status == "approved"

        executed = runtime.execute(context, proposed.proposal.proposal_id)
        assert executed.status == "executed"
        assert executed.result is not None
        assert executed.result["contract_version"] == "form-definition-proposal-result.v1"
        assert executed.result["persisted_readback_verified"] is True
        assert executed.result["published"] is False

        result_form = executed.result["form"]
        assert result_form["form_id"] == "DAILY-LOG-01"
        assert result_form["version"] == 1
        assert result_form["status"] == "draft"
        assert result_form["shared_with_user_ids"] == ["worker-1"]
        assert result_form["approver_roles"] == ["project_admin"]
        assert [item["field_type"] for item in result_form["fields"]] == [
            "text", "number", "date", "boolean"
        ]

        fresh = form_api.get_definition(
            scope, "DAILY-LOG-01", 1,
            auth_context=__import__(
                "construction_pm.application.authorization", fromlist=["AuthorizationContext"]
            ).AuthorizationContext(
                "tenant-1", "project-1", "owner-1", frozenset({"project_admin"})
            ),
        )
        assert fresh is not None
        assert fresh.to_payload() == result_form
        assert fresh.status == "draft"
        assert {
            event["event_type"]
            for event in repository.list_audit_events(scope.tenant_id, scope.project_id)
        } == {"form_definition_draft_created"}
        assert connection.execute(
            "SELECT COUNT(*) FROM ai_action_tool_idempotency "
            "WHERE tenant_id=? AND project_id=? AND tool_name=?",
            ("tenant-1", "project-1", "form.definition.create"),
        ).fetchone()[0] == 1
    finally:
        connection.close()


def test_ai_form_tool_rejects_invalid_fields_before_proposal_is_stored(tmp_path):
    connection, repository, _, runtime, context, scope = setup_runtime(
        tmp_path / "assistant-form-invalid.sqlite3"
    )
    try:
        invalid = form_payload()
        invalid["fields"] = [
            {
                **invalid["fields"][0],
                "section_id": "SECTION-DOES-NOT-EXIST",
            }
        ]
        with pytest.raises(AIActionRuntimeError, match="AI_ACTION_TOOL_PAYLOAD_INVALID"):
            runtime.propose(
                context, tool_name="form.definition.create", payload=invalid
            )
        assert repository.latest_definition(
            scope.tenant_id, scope.project_id, "DAILY-LOG-01"
        ) is None
        assert connection.execute(
            "SELECT COUNT(*) FROM ai_action_proposals"
        ).fetchone()[0] == 0
    finally:
        connection.close()


def test_ai_form_tool_rejects_unapproved_publish_and_unknown_payload_fields(tmp_path):
    connection, repository, _, runtime, context, scope = setup_runtime(
        tmp_path / "assistant-form-guard.sqlite3"
    )
    try:
        unknown = form_payload(automatically_publish=True)
        with pytest.raises(AIActionRuntimeError, match="AI_ACTION_TOOL_PAYLOAD_INVALID"):
            runtime.propose(
                context, tool_name="form.definition.create", payload=unknown
            )

        proposed = runtime.propose(
            context, tool_name="form.definition.create", payload=form_payload()
        )
        with pytest.raises(AIActionRuntimeError):
            runtime.execute(context, proposed.proposal.proposal_id)
        assert repository.latest_definition(
            scope.tenant_id, scope.project_id, "DAILY-LOG-01"
        ) is None
    finally:
        connection.close()
