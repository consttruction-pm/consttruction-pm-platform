from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

import pytest

from construction_pm.ai_action_boundary import (
    AIActionPermissionGrant,
    UserConfiguredAIActionPermissionAdapter,
)
from construction_pm.ai_action_runtime import (
    AIActionRuntime,
    AIActionRuntimeContext,
    AIActionRuntimeError,
    AIActionToolDefinition,
    SQLiteAIActionRuntimeStore,
)
from construction_pm.ai_assistant_orchestration import (
    AIAssistantProviderError,
    AIAssistantTurnOrchestrator,
    OpenAICompatibleChatProvider,
)


class FakeProvider:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def complete_json(self, *, system_prompt, user_message, language, history=()):
        self.calls.append({
            "system_prompt": system_prompt,
            "user_message": user_message,
            "language": language,
            "history": history,
        })
        return self.result


def build_runtime():
    connection = sqlite3.connect(":memory:")
    store = SQLiteAIActionRuntimeStore(connection)
    executed = []
    grant = AIActionPermissionGrant(
        subject_id="user-1",
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision_id="12",
        resource_domain="activities",
        operation="create",
        tool_name="activity.create",
    )

    def validate_payload(payload):
        if set(payload) != {"activity_id", "name", "duration_value", "duration_unit"}:
            raise ValueError("invalid activity payload")
        if not isinstance(payload["activity_id"], str) or not payload["activity_id"].strip():
            raise ValueError("invalid activity id")
        if not isinstance(payload["name"], str) or not payload["name"].strip():
            raise ValueError("invalid activity name")
        if isinstance(payload["duration_value"], bool) or float(payload["duration_value"]) < 0:
            raise ValueError("invalid duration")
        if payload["duration_unit"] not in {"working-day", "working-hour"}:
            raise ValueError("invalid unit")
        return {
            "activity_id": payload["activity_id"].strip(),
            "name": payload["name"].strip(),
            "duration_value": str(payload["duration_value"]),
            "duration_unit": payload["duration_unit"],
        }

    def execute(payload, proposal, idempotency_key, context):
        executed.append(dict(payload))
        return {"activity_id": payload["activity_id"]}

    tool = AIActionToolDefinition(
        tool_name="activity.create",
        action="create",
        resource_domain="activities",
        requires_human_approval=True,
        validate_payload=validate_payload,
        execute=execute,
        description="Create one activity after explicit user approval.",
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["activity_id", "name", "duration_value", "duration_unit"],
            "properties": {
                "activity_id": {"type": "string", "minLength": 1},
                "name": {"type": "string", "minLength": 1},
                "duration_value": {"type": "number", "minimum": 0},
                "duration_unit": {"type": "string", "enum": ["working-day", "working-hour"]},
            },
        },
    )
    runtime = AIActionRuntime(
        store=store,
        permission_adapter=UserConfiguredAIActionPermissionAdapter(lambda: (grant,)),
        audit_sink=store,
        tools=(tool,),
        clock=lambda: datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc),
    )
    context = AIActionRuntimeContext(
        subject_id="user-1",
        tenant_id="tenant-1",
        project_id="project-1",
        project_revision_id="12",
        roles=frozenset({"project_admin"}),
    )
    return connection, runtime, context, executed


def proposal_payload():
    return {
        "activity_id": "A-100",
        "name": "Excavation",
        "duration_value": 3.5,
        "duration_unit": "working-day",
    }


def test_assistant_message_does_not_create_or_execute_a_project_action():
    connection, runtime, context, executed = build_runtime()
    provider = FakeProvider({
        "kind": "clarification",
        "message": "Please provide the missing activity duration.",
        "tool_name": None,
        "payload": {},
    })
    try:
        turn = AIAssistantTurnOrchestrator(
            provider=provider, action_runtime=runtime
        ).turn(context, user_message="Create an activity", language="en")

        assert turn.kind == "clarification"
        assert turn.proposal is None
        assert executed == []
        assert connection.execute("SELECT COUNT(*) FROM ai_action_proposals").fetchone()[0] == 0
        assert provider.calls[0]["user_message"] == "Create an activity"
        assert '"activity.create"' in provider.calls[0]["system_prompt"]
    finally:
        connection.close()


def test_assistant_creates_only_an_approval_gated_proposal():
    connection, runtime, context, executed = build_runtime()
    provider = FakeProvider({
        "kind": "action_proposal",
        "message": "Review this activity proposal before approving it.",
        "tool_name": "activity.create",
        "payload": proposal_payload(),
    })
    try:
        turn = AIAssistantTurnOrchestrator(
            provider=provider, action_runtime=runtime
        ).turn(context, user_message="Create excavation, duration 3.5 working days", language="en")

        assert turn.kind == "action_proposal"
        assert turn.proposal is not None
        assert turn.proposal.status == "proposed"
        assert turn.proposal.proposal.requires_human_approval is True
        assert turn.proposal.proposal.requested_by == context.subject_id
        assert turn.proposal.proposal.evidence_refs == ()
        assert turn.proposal.payload == {
            "activity_id": "A-100",
            "name": "Excavation",
            "duration_value": "3.5",
            "duration_unit": "working-day",
        }
        assert executed == []
        assert connection.execute("SELECT COUNT(*) FROM ai_action_proposals").fetchone()[0] == 1
    finally:
        connection.close()


def test_assistant_rejects_invalid_model_payload_without_persisting_a_proposal():
    connection, runtime, context, executed = build_runtime()
    provider = FakeProvider({
        "kind": "action_proposal",
        "message": "I will create the activity.",
        "tool_name": "activity.create",
        "payload": {"activity_id": "A-101", "name": "Excavation"},
    })
    try:
        with pytest.raises(AIAssistantProviderError, match="AI_ASSISTANT_PROPOSAL_INVALID"):
            AIAssistantTurnOrchestrator(
                provider=provider, action_runtime=runtime
            ).turn(context, user_message="Create an activity", language="en")
        assert executed == []
        assert connection.execute("SELECT COUNT(*) FROM ai_action_proposals").fetchone()[0] == 0
    finally:
        connection.close()


def test_assistant_rejects_unregistered_or_schema_less_tools():
    connection, runtime, context, executed = build_runtime()
    provider = FakeProvider({
        "kind": "action_proposal",
        "message": "Do something else.",
        "tool_name": "project.delete",
        "payload": {},
    })
    try:
        with pytest.raises(AIAssistantProviderError, match="AI_ASSISTANT_PROVIDER_RESPONSE_INVALID"):
            AIAssistantTurnOrchestrator(
                provider=provider, action_runtime=runtime
            ).turn(context, user_message="Delete project", language="en")
        assert executed == []
        assert connection.execute("SELECT COUNT(*) FROM ai_action_proposals").fetchone()[0] == 0
    finally:
        connection.close()


class FakeResponse:
    def __init__(self, raw: bytes):
        self.raw = raw

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, limit=-1):
        return self.raw if limit < 0 else self.raw[:limit]


def test_openai_compatible_provider_uses_server_authorization_and_json_contract():
    content = json.dumps({
        "kind": "message", "message": "Hello", "tool_name": None, "payload": {}
    })
    response = FakeResponse(json.dumps({
        "choices": [{"message": {"content": content}}]
    }).encode("utf-8"))
    seen = {}

    def opener(request, *, timeout):
        seen["url"] = request.full_url
        seen["authorization"] = request.get_header("Authorization")
        seen["timeout"] = timeout
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return response

    provider = OpenAICompatibleChatProvider(
        base_url="https://provider.example/v1",
        api_key="server-secret",
        model="model-test",
        timeout_seconds=8,
        opener=opener,
    )
    result = provider.complete_json(
        system_prompt="system contract",
        user_message="question",
        language="fa",
    )
    assert result["kind"] == "message"
    assert seen["url"] == "https://provider.example/v1/chat/completions"
    assert seen["authorization"] == "Bearer server-secret"
    assert seen["timeout"] == 8
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert seen["body"]["messages"][0] == {"role": "system", "content": "system contract"}
    assert json.loads(seen["body"]["messages"][1]["content"]) == {
        "language": "fa", "request": "question"
    }


def test_provider_rejects_http_endpoints_and_missing_environment_configuration(monkeypatch):
    with pytest.raises(AIAssistantProviderError, match="AI_ASSISTANT_PROVIDER_CONFIGURATION_INVALID"):
        OpenAICompatibleChatProvider(base_url="http://provider.example/v1", api_key="key", model="m")

    for key in ("CUBI_AI_API_KEY", "CUBI_AI_BASE_URL", "CUBI_AI_MODEL"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(AIAssistantProviderError, match="AI_ASSISTANT_PROVIDER_CONFIGURATION_INVALID"):
        OpenAICompatibleChatProvider.from_environment()


def test_provider_rejects_oversized_and_malformed_json_responses():
    provider = OpenAICompatibleChatProvider(
        base_url="https://provider.example/v1",
        api_key="server-secret",
        model="model-test",
        opener=lambda request, *, timeout: FakeResponse(b"not-json"),
    )
    with pytest.raises(AIAssistantProviderError, match="AI_ASSISTANT_PROVIDER_RESPONSE_INVALID"):
        provider.complete_json(system_prompt="system", user_message="hello", language="en")
