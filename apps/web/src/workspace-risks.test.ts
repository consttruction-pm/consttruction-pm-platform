import assert from "node:assert/strict";
import { test } from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  RISK_API_VERSION,
  buildRiskPayload,
  deleteRisk,
  loadRiskHistory,
  loadRisks,
  parseRisk,
  parseRiskHistoryEvent,
  riskExposureLevel,
  saveRisk,
  type RiskInput,
} from "./workspace-risks.js";

const context: ProjectContext = { tenant_id: "T-1", project_id: "P-1", revision: 3 };

type Call = { method: string; path: string; body?: unknown; key?: string };

function transport(
  handler: (call: Call) => ApiResult<unknown>,
): { transport: ApiTransport; calls: Call[] } {
  const calls: Call[] = [];
  const send = (method: string) => async (path: string, body?: unknown, _context?: ProjectContext, key?: string) => {
    const call = { method, path, body, key };
    calls.push(call);
    return handler(call);
  };
  return {
    calls,
    transport: {
      get: send("GET"),
      post: send("POST"),
      patch: send("PATCH"),
      delete: send("DELETE"),
    } as unknown as ApiTransport,
  };
}

function record(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  const base = {
    contract_version: RISK_API_VERSION,
    risk_id: "RK-1",
    title: "Supplier lead time slips",
    description: "Primary steel supplier may miss the framed date.",
    category: "schedule",
    status: "open",
    probability: 3,
    impact: 4,
    score: 12,
    exposure_level: "high",
    response_strategy: "mitigate",
    response_owner: "u-response",
    response_due_date: "2026-12-01",
    owner: "u-owner",
    responsible_manager: "u-manager",
    date_identified: "2026-11-01",
    closure_note: null,
    revision: 1,
  };
  return { ...base, ...overrides };
}

function input(overrides: Partial<RiskInput> = {}): RiskInput {
  return {
    riskId: "RK-1",
    title: "Supplier lead time slips",
    description: "Primary steel supplier may miss the framed date.",
    category: "schedule",
    status: "open",
    probability: 3,
    impact: 4,
    responseStrategy: "mitigate",
    responseOwner: "u-response",
    responseDueDate: "2026-12-01",
    owner: "u-owner",
    responsibleManager: "u-manager",
    dateIdentified: "2026-11-01",
    closureNote: null,
    ...overrides,
  };
}

test("exposure levels match the server scoring bands", () => {
  assert.equal(riskExposureLevel(1, 1), "low");
  assert.equal(riskExposureLevel(2, 2), "low");
  assert.equal(riskExposureLevel(3, 2), "medium");
  assert.equal(riskExposureLevel(4, 4), "high");
  assert.equal(riskExposureLevel(5, 4), "critical");
});

test("risk parser accepts a valid record and fails closed on drift", () => {
  const parsed = parseRisk(record());
  assert.equal(parsed.riskId, "RK-1");
  assert.equal(parsed.score, 12);
  assert.equal(parsed.exposureLevel, "high");
  assert.equal(parsed.revision, 1);

  for (const bad of [
    record({ contract_version: "p6-risk-api.v2" }),
    record({ probability: 0 }),
    record({ probability: 6 }),
    record({ score: 13 }),
    record({ exposure_level: "critical" }),
    record({ category: "bogus" }),
    record({ status: "closed" }),
    record({ status: "closed", closure_note: " " }),
    record({ response_due_date: "12/01/2026" }),
    record({ date_identified: "2026-13-01" }),
    record({ owner: "  " }),
    record({ revision: 0 }),
  ]) {
    assert.throws(() => parseRisk(bad));
  }
  assert.equal(parseRisk(record({ status: "closed", closure_note: "Delivered" })).closureNote, "Delivered");
});

test("history parser rejects unknown contracts and partial events", () => {
  const event = {
    contract_version: RISK_API_VERSION,
    entity_type: "risk",
    entity_id: "RK-1",
    revision: 2,
    event_type: "status_changed",
    actor_id: "u-1",
    occurred_at: "2026-11-12T10:00:00+00:00",
    reason: "Plan approved",
  };
  assert.equal(parseRiskHistoryEvent(event).eventType, "status_changed");
  assert.throws(() => parseRiskHistoryEvent({ ...event, contract_version: "v2" }));
  assert.throws(() => parseRiskHistoryEvent({ ...event, revision: 0 }));
  assert.throws(() => parseRiskHistoryEvent({ ...event, actor_id: "" }));
});

test("payload trims text, keeps authoritative ratings and drops empty optionals", () => {
  const payload = buildRiskPayload(
    input({
      riskId: " RK-1 ",
      title: " Supplier ",
      description: "  ",
      owner: " u-owner ",
      responseOwner: "  ",
      responseDueDate: "",
      responsibleManager: null,
      closureNote: "",
    }),
  );
  assert.deepEqual(payload, {
    risk_id: "RK-1",
    title: "Supplier",
    description: "",
    category: "schedule",
    status: "open",
    probability: 3,
    impact: 4,
    response_strategy: "mitigate",
    response_owner: null,
    response_due_date: null,
    owner: "u-owner",
    responsible_manager: null,
    date_identified: "2026-11-01",
    closure_note: null,
  });
});

test("payload rejects invalid ratings, dates, enums and missing closure notes", () => {
  for (const bad of [
    input({ riskId: "" }),
    input({ title: " " }),
    input({ owner: "" }),
    input({ category: "bogus" }),
    input({ status: "archived" }),
    input({ responseStrategy: "ignore" }),
    input({ probability: 0 }),
    input({ impact: 6 }),
    input({ probability: 2.5 }),
    input({ dateIdentified: "2026-13-01" }),
    input({ responseDueDate: "2026-10-01" }),
    input({ status: "closed" }),
  ]) {
    assert.throws(() => buildRiskPayload(bad));
  }
  assert.equal(
    buildRiskPayload(input({ status: "closed", closureNote: " Delivered " })).closure_note,
    "Delivered",
  );
});

test("loadRisks sends server-side filters and parses the envelope", async () => {
  const { transport: api, calls } = transport(() => ({
    ok: true,
    data: { contract_version: RISK_API_VERSION, risks: [record()] },
  }));
  const result = await loadRisks(api, context, {
    category: "schedule",
    status: "open",
    responseStrategy: "mitigate",
    exposure: "high",
    search: "supplier",
  });
  assert.equal(result.ok, true);
  assert.equal(calls[0].path, "/api/projects/P-1/risks?category=schedule&status=open&response_strategy=mitigate&exposure=high&search=supplier");
  assert.equal((result as ApiResult<readonly unknown[]>).ok && (result as { data: readonly unknown[] }).data.length, 1);
});

test("loadRisks fails closed on contract drift", async () => {
  const { transport: api } = transport(() => ({
    ok: true,
    data: { contract_version: "p6-risk-api.v2", risks: [] },
  }));
  const result = await loadRisks(api, context);
  assert.equal(result.ok, false);
  assert.equal((result as { error: { code: string } }).error.code, "INVALID_RISK_LIST");
});

test("loadRiskHistory reads the history route", async () => {
  const { transport: api, calls } = transport(() => ({
    ok: true,
    data: {
      contract_version: RISK_API_VERSION,
      events: [
        {
          contract_version: RISK_API_VERSION,
          entity_type: "risk",
          entity_id: "RK-1",
          revision: 1,
          event_type: "created",
          actor_id: "u-1",
          occurred_at: "2026-11-12T10:00:00+00:00",
          reason: "",
        },
      ],
    },
  }));
  const result = await loadRiskHistory(api, context, "RK-1");
  assert.equal(calls[0].path, "/api/projects/P-1/risks/RK-1/history");
  assert.equal(result.ok && result.data[0].eventType, "created");
});

test("saveRisk posts a new risk with an idempotency key and patches edits", async () => {
  const { transport: api, calls } = transport(() => ({ ok: true, data: record() }));
  const created = await saveRisk(api, context, input());
  assert.equal(created.ok, true);
  assert.equal(calls[0].method, "POST");
  assert.equal(calls[0].path, "/api/projects/P-1/risks");
  assert.ok(calls[0].key);

  const updated = await saveRisk(api, context, input({ title: "Revised" }), 4);
  assert.equal(updated.ok, true);
  assert.equal(calls[1].method, "PATCH");
  assert.equal(calls[1].path, "/api/projects/P-1/risks/RK-1");
  assert.equal((calls[1].body as Record<string, unknown>).expected_revision, 4);
});

test("saveRisk surfaces server errors and local validation without a request", async () => {
  const { transport: api, calls } = transport(() => ({
    ok: false,
    error: {
      code: "RISK_REVISION_CONFLICT",
      retryable: true,
      message_key: "error.risk.conflict",
      available_actions: [],
    },
  }));
  const conflict = await saveRisk(api, context, input(), 2);
  assert.equal(conflict.ok, false);
  assert.equal((conflict as { error: { code: string } }).error.code, "RISK_REVISION_CONFLICT");

  const before = calls.length;
  const invalid = await saveRisk(api, context, input({ probability: 0 }));
  assert.equal(invalid.ok, false);
  assert.equal((invalid as { error: { code: string } }).error.code, "INVALID_RISK_PROBABILITY");
  assert.equal(calls.length, before);
});

test("deleteRisk sends the expected revision", async () => {
  const { transport: api, calls } = transport(() => ({ ok: true, data: { deleted: true } }));
  const result = await deleteRisk(api, context, "RK-1", 3);
  assert.equal(result.ok, true);
  assert.equal(calls[0].method, "DELETE");
  assert.deepEqual(calls[0].body, { expected_revision: 3 });
});
