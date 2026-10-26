import assert from "node:assert/strict";
import test from "node:test";
import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import { AIActionClient, AI_ACTION_CONTRACT_VERSION } from "./ai-action-client.js";

class FakeTransport implements ApiTransport {
  calls: Array<{ method: string; path: string; request?: unknown }> = [];
  responses: ApiResult<unknown>[] = [];
  async get<T>(path: string, context: ProjectContext): Promise<ApiResult<T>> {
    this.calls.push({ method: "GET", path });
    return this.next<T>();
  }
  async post<I, O>(path: string, request: I, context: ProjectContext, idempotencyKey?: string): Promise<ApiResult<O>> {
    this.calls.push({ method: "POST", path, request });
    return this.next<O>();
  }
  private next<T>(): ApiResult<T> {
    const item = this.responses.shift();
    if (!item) throw new Error("TEST_RESPONSE_MISSING");
    return item as ApiResult<T>;
  }
}
const context = { tenant_id: "tenant-1", project_id: "project-1", revision: 7 };
const validProposal = {
  proposal_id: "prop-1", tool_name: "activity.create", action: "create",
  status: "proposed", requires_human_approval: true, requested_by: "user-1",
  evidence_refs: [], project_revision_id: "7", resource_domain: "activities",
  payload: { activity_id: "A-17", name: "Excavation", duration_value: "2", duration_unit: "working-day" },
  result: null, created_at: "2026-10-25T00:00:00Z", updated_at: "2026-10-25T00:00:00Z",
  decided_by: null, is_stale: false,
};

test("lists proposals for current project", async () => {
  const transport = new FakeTransport();
  transport.responses.push({ ok: true, data: { contract_version: AI_ACTION_CONTRACT_VERSION, proposals: [validProposal] } });
  const result = await new AIActionClient(transport).listProposals(context);
  assert.equal(result.ok, true);
  assert.equal(transport.calls[0]?.path, "/api/projects/project-1/ai/actions/proposals");
  if (result.ok) assert.equal(result.data.proposals[0]?.proposal_id, "prop-1");
});

test("creates activity proposal with expected revision and registered tool", async () => {
  const transport = new FakeTransport();
  transport.responses.push({ ok: true, data: {
    contract_version: AI_ACTION_CONTRACT_VERSION, status: "proposed",
    proposal: { ...validProposal, status: undefined },
  }});
  const result = await new AIActionClient(transport).proposeActivity(context, {
    activity_id: "A-17", name: "Excavation", duration_value: "2", duration_unit: "working-day",
  });
  assert.equal(result.ok, true);
  assert.equal(transport.calls[0]?.path, "/api/projects/project-1/ai/actions/proposals");
  assert.deepEqual(transport.calls[0]?.request, {
    expected_revision: 7, tool_name: "activity.create",
    payload: { activity_id: "A-17", name: "Excavation", duration_value: "2", duration_unit: "working-day" },
    evidence_refs: [],
  });
});

test("approval and execution use separate explicit requests", async () => {
  const transport = new FakeTransport();
  transport.responses.push(
    { ok: true, data: { contract_version: AI_ACTION_CONTRACT_VERSION, proposal_id: "prop-1", status: "approved", decided_by: "user-1" } },
    { ok: true, data: { contract_version: AI_ACTION_CONTRACT_VERSION, proposal_id: "prop-1", status: "executed", result: { activity_id: "A-17" } } },
  );
  const client = new AIActionClient(transport);
  const approved = await client.decide(context, "prop-1", true);
  const executed = await client.execute(context, "prop-1");
  assert.equal(approved.ok && approved.data.status, "approved");
  assert.equal(executed.ok && executed.data.status, "executed");
  assert.equal(transport.calls[0]?.path, "/api/projects/project-1/ai/actions/proposals/prop-1/decision");
  assert.equal(transport.calls[1]?.path, "/api/projects/project-1/ai/actions/proposals/prop-1/execute");
});

test("invalid action contract is rejected", async () => {
  const transport = new FakeTransport();
  transport.responses.push({ ok: true, data: { contract_version: "wrong", proposals: [] } });
  const result = await new AIActionClient(transport).listProposals(context);
  assert.equal(result.ok, false);
  if (!result.ok) assert.equal(result.error.code, "INVALID_AI_ACTION_RESPONSE");
});

test("execution sends the calculation timezone and parses a computed verification", async () => {
  const transport = new FakeTransport();
  transport.responses.push({ ok: true, data: {
    contract_version: AI_ACTION_CONTRACT_VERSION,
    proposal_id: "prop-1",
    status: "executed",
    result: { activity: { activity_id: "A-17" } },
    execution_verification: {
      contract_version: "ai-action-execution-verification.v1",
      status: "COMPUTED",
      reason_code: null,
      activity: {
        activity_id: "A-17", start: "2026-10-19", finish: "2026-10-20",
        duration: 2, duration_unit: "working-day", critical: true,
      },
      project_finish: "2026-10-20",
      calculation_run_identity: "run-identity-1",
      snapshot: {
        snapshot_id: "SNAP-1",
        snapshot_hash: "a".repeat(64),
        calculation_identity: "b".repeat(64),
      },
      query_id: "ai-action-execution:prop-1",
    },
  }});
  const result = await new AIActionClient(transport).execute(context, "prop-1", "Asia/Tehran");
  assert.deepEqual(transport.calls[0]?.request, {
    expected_revision: 7,
    timezone: "Asia/Tehran",
  });
  assert.equal(result.ok, true);
  if (result.ok) {
    const verification = result.data.execution_verification;
    assert.equal(verification?.status, "COMPUTED");
    assert.equal(verification?.activity?.start, "2026-10-19");
    assert.equal(verification?.snapshot?.snapshot_id, "SNAP-1");
  }
});

test("rejects a computed verification that omits calculated activity or snapshot", async () => {
  const transport = new FakeTransport();
  transport.responses.push({ ok: true, data: {
    contract_version: AI_ACTION_CONTRACT_VERSION,
    proposal_id: "prop-1",
    status: "executed",
    result: { activity: { activity_id: "A-17" } },
    execution_verification: {
      contract_version: "ai-action-execution-verification.v1",
      status: "COMPUTED",
      reason_code: null,
      activity: null,
      project_finish: "2026-10-20",
      calculation_run_identity: "run-identity-1",
      snapshot: null,
      query_id: "ai-action-execution:prop-1",
    },
  }});
  const result = await new AIActionClient(transport).execute(context, "prop-1", null);
  assert.equal(result.ok, false);
  if (!result.ok) assert.equal(result.error.code, "INVALID_AI_ACTION_RESPONSE");
});

test("accepts an explicit unavailable verification without fabricated dates", async () => {
  const transport = new FakeTransport();
  transport.responses.push({ ok: true, data: {
    contract_version: AI_ACTION_CONTRACT_VERSION,
    proposal_id: "prop-1",
    status: "executed",
    result: { activity: { activity_id: "A-17" } },
    execution_verification: {
      contract_version: "ai-action-execution-verification.v1",
      status: "UNAVAILABLE",
      reason_code: "CALCULATION_TIMEZONE_REQUIRED",
      activity: null,
      project_finish: null,
      calculation_run_identity: null,
      snapshot: null,
      query_id: null,
    },
  }});
  const result = await new AIActionClient(transport).execute(context, "prop-1", null);
  assert.equal(result.ok, true);
  if (result.ok) {
    assert.equal(result.data.execution_verification?.status, "UNAVAILABLE");
    assert.equal(result.data.execution_verification?.reason_code, "CALCULATION_TIMEZONE_REQUIRED");
    assert.equal(result.data.execution_verification?.activity, null);
  }
});


test("sends an assistant turn with bounded conversation history and current revision", async () => {
  const transport = new FakeTransport();
  transport.responses.push({ ok: true, data: {
    contract_version: "ai-assistant-turn.v1",
    kind: "clarification",
    message: "Please provide the missing duration.",
    proposal: null,
  }});
  const result = await new AIActionClient(transport).sendAssistantTurn(
    context,
    "Create an activity",
    "fa",
    [{ role: "user", content: "I need to add work" }, { role: "assistant", content: "What activity?" }],
  );
  assert.equal(result.ok, true);
  assert.equal(transport.calls[0]?.path, "/api/projects/project-1/ai/assistant/turn");
  assert.deepEqual(transport.calls[0]?.request, {
    expected_revision: 7,
    message: "Create an activity",
    language: "fa",
    history: [
      { role: "user", content: "I need to add work" },
      { role: "assistant", content: "What activity?" },
    ],
  });
  if (result.ok) {
    assert.equal(result.data.kind, "clarification");
    assert.equal(result.data.proposal, null);
  }
});

test("parses a server-created approval-gated proposal returned by the assistant", async () => {
  const transport = new FakeTransport();
  transport.responses.push({ ok: true, data: {
    contract_version: "ai-assistant-turn.v1",
    kind: "action_proposal",
    message: "Review the proposed activity.",
    proposal: validProposal,
  }});
  const result = await new AIActionClient(transport).sendAssistantTurn(
    context, "Create excavation", "en",
  );
  assert.equal(result.ok, true);
  if (result.ok) {
    assert.equal(result.data.kind, "action_proposal");
    assert.equal(result.data.proposal?.requires_human_approval, true);
    assert.equal(result.data.proposal?.proposal_id, "prop-1");
  }
});

test("rejects mismatched assistant turn kind and proposal state", async () => {
  const transport = new FakeTransport();
  transport.responses.push({ ok: true, data: {
    contract_version: "ai-assistant-turn.v1",
    kind: "message",
    message: "The proposal exists.",
    proposal: validProposal,
  }});
  const result = await new AIActionClient(transport).sendAssistantTurn(context, "hello", "en");
  assert.equal(result.ok, false);
  if (!result.ok) assert.equal(result.error.code, "INVALID_AI_ACTION_RESPONSE");
});


test("rejects assistant turn responses missing required proposal field or valid message", async () => {
  const transport = new FakeTransport();
  transport.responses.push({ ok: true, data: {
    contract_version: "ai-assistant-turn.v1",
    kind: "message",
    message: "Hello",
  }});
  const missingProposal = await new AIActionClient(transport).sendAssistantTurn(context, "hello", "en");
  assert.equal(missingProposal.ok, false);

  transport.responses.push({ ok: true, data: {
    contract_version: "ai-assistant-turn.v1",
    kind: "message",
    message: "   ",
    proposal: null,
  }});
  const emptyMessage = await new AIActionClient(transport).sendAssistantTurn(context, "hello", "en");
  assert.equal(emptyMessage.ok, false);
});
