import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  THRESHOLD_API_VERSION,
  buildThresholdPayload,
  deleteThreshold,
  loadThresholdHistory,
  loadThresholdRuns,
  loadThresholds,
  monitorThreshold,
  saveThreshold,
  type ThresholdInput,
} from "./workspace-thresholds.js";

const CONTEXT: ProjectContext = { tenant_id: "t1", project_id: "project-1", revision: 4 };

const THRESHOLD = {
  contract_version: THRESHOLD_API_VERSION,
  threshold_id: "TH-COST-1",
  name: "Expense ceiling",
  monitoring_subject: "cost",
  parameter: "expense_actual_total",
  currency: "USD",
  lower_threshold: null,
  upper_threshold: "100",
  warning_level: "10",
  issue_level: "50",
  responsible_manager: "preview-planner",
  status: "active",
  revision: 2,
};

const RUN = {
  contract_version: THRESHOLD_API_VERSION,
  threshold_id: "TH-COST-1",
  run_sequence: 2,
  observed_value: "900",
  level: "issue",
  currency: "USD",
  actor_id: "u-1",
  occurred_at: "2026-11-12T10:00:00+00:00",
  generated_issue_id: "THR-TH-COST-1-R2",
};

const EVENT = {
  contract_version: THRESHOLD_API_VERSION,
  entity_type: "threshold",
  entity_id: "TH-COST-1",
  revision: 2,
  event_type: "updated",
  actor_id: "u-1",
  occurred_at: "2026-11-12T10:00:00+00:00",
  reason: "",
};

type Calls = {
  gets: string[];
  posts: { path: string; request: unknown; idempotencyKey?: string }[];
  patches: { path: string; request: unknown }[];
  deletes: { path: string; request: unknown }[];
};

function calls(): Calls {
  return { gets: [], posts: [], patches: [], deletes: [] };
}

function transportWith(result: ApiResult<unknown>, log: Calls = calls()): ApiTransport {
  return {
    async get(path) {
      log.gets.push(path);
      return result as ApiResult<never>;
    },
    async post(path, request, _context, idempotencyKey) {
      log.posts.push({ path, request, idempotencyKey });
      return result as ApiResult<never>;
    },
    async patch(path, request) {
      log.patches.push({ path, request });
      return result as ApiResult<never>;
    },
    async delete(path, request) {
      log.deletes.push({ path, request });
      return result as ApiResult<never>;
    },
  };
}

function envelope(key: "thresholds" | "runs" | "events", items: readonly unknown[]) {
  return { contract_version: THRESHOLD_API_VERSION, [key]: items };
}

function input(overrides: Partial<ThresholdInput> = {}): ThresholdInput {
  return {
    thresholdId: "TH-COST-1",
    name: "Expense ceiling",
    monitoringSubject: "cost",
    parameter: "expense_actual_total",
    currency: "USD",
    lowerThreshold: null,
    upperThreshold: "100",
    warningLevel: "10",
    issueLevel: "50",
    responsibleManager: "preview-planner",
    status: "active",
    ...overrides,
  };
}

test("threshold list reads the p6-threshold-api contract and carries filters", async () => {
  const log = calls();
  const result = await loadThresholds(
    transportWith({ ok: true, data: envelope("thresholds", [THRESHOLD]) }, log),
    CONTEXT,
    { monitoringSubject: "cost", parameter: "expense_actual_total", status: "active", search: "ceiling" },
  );
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.deepEqual(result.data, [{
    thresholdId: "TH-COST-1",
    name: "Expense ceiling",
    monitoringSubject: "cost",
    parameter: "expense_actual_total",
    currency: "USD",
    lowerThreshold: null,
    upperThreshold: "100",
    warningLevel: "10",
    issueLevel: "50",
    responsibleManager: "preview-planner",
    status: "active",
    revision: 2,
  }]);
  assert.deepEqual(log.gets, [
    "/api/projects/project-1/thresholds?monitoring_subject=cost&parameter=expense_actual_total&status=active&search=ceiling",
  ]);
});

test("threshold list fails closed on foreign contracts and malformed rows", async () => {
  const foreign = await loadThresholds(
    transportWith({ ok: true, data: { contract_version: "p6-threshold-api.v0", thresholds: [THRESHOLD] } }),
    CONTEXT,
  );
  assert.equal(foreign.ok, false);
  if (!foreign.ok) assert.equal(foreign.error.code, "INVALID_THRESHOLD_LIST");

  const cases: [Record<string, unknown>, string][] = [
    [{ name: "" }, "INVALID_THRESHOLD_RECORD"],
    [{ monitoring_subject: "bogus" }, "INVALID_THRESHOLD_RECORD"],
    [{ parameter: "bogus" }, "INVALID_THRESHOLD_RECORD"],
    [{ currency: null }, "INVALID_THRESHOLD_RECORD"],
    [{ currency: "usd" }, "INVALID_THRESHOLD_RECORD"],
    [{ lower_threshold: "200" }, "INVALID_THRESHOLD_RECORD"],
    [{ warning_level: null, issue_level: "50", upper_threshold: null }, "INVALID_THRESHOLD_RECORD"],
    [{ issue_level: "5" }, "INVALID_THRESHOLD_RECORD"],
    [{ upper_threshold: 100 }, "INVALID_THRESHOLD_RECORD"],
    [{ revision: 0 }, "INVALID_THRESHOLD_RECORD"],
  ];
  for (const [override, code] of cases) {
    const result = await loadThresholds(
      transportWith({ ok: true, data: envelope("thresholds", [{ ...THRESHOLD, ...override }]) }),
      CONTEXT,
    );
    assert.equal(result.ok, false, `override ${JSON.stringify(override)} should fail`);
    if (!result.ok) assert.equal(result.error.code, code);
  }
});

test("threshold payload trims fields and serializes decimal text", () => {
  assert.deepEqual(
    buildThresholdPayload({
      thresholdId: " TH-COST-1 ",
      name: " Expense ceiling ",
      monitoringSubject: " cost ",
      parameter: " expense_actual_total ",
      currency: " USD ",
      lowerThreshold: " -5.5 ",
      upperThreshold: " 100 ",
      warningLevel: " 10 ",
      issueLevel: " 50 ",
      responsibleManager: " preview-planner ",
      status: " active ",
    }),
    {
      threshold_id: "TH-COST-1",
      name: "Expense ceiling",
      monitoring_subject: "cost",
      parameter: "expense_actual_total",
      currency: "USD",
      lower_threshold: "-5.5",
      upper_threshold: "100",
      warning_level: "10",
      issue_level: "50",
      responsible_manager: "preview-planner",
      status: "active",
    },
  );
  assert.deepEqual(
    buildThresholdPayload(input({
      parameter: "open_issue_count",
      currency: null,
      lowerThreshold: null,
      upperThreshold: "5",
      warningLevel: "1",
      issueLevel: "3",
    })),
    {
      threshold_id: "TH-COST-1",
      name: "Expense ceiling",
      monitoring_subject: "cost",
      parameter: "open_issue_count",
      currency: null,
      lower_threshold: null,
      upper_threshold: "5",
      warning_level: "1",
      issue_level: "3",
      responsible_manager: "preview-planner",
      status: "active",
    },
  );
});

test("threshold payload refuses missing, invalid and inconsistent definitions", () => {
  assert.throws(() => buildThresholdPayload(input({ thresholdId: " " })), /THRESHOLD_FIELDS_REQUIRED/);
  assert.throws(() => buildThresholdPayload(input({ monitoringSubject: "bogus" })), /INVALID_THRESHOLD_SUBJECT/);
  assert.throws(() => buildThresholdPayload(input({ parameter: "bogus" })), /INVALID_THRESHOLD_PARAMETER/);
  assert.throws(() => buildThresholdPayload(input({ currency: "US" })), /INVALID_THRESHOLD_CURRENCY/);
  assert.throws(
    () => buildThresholdPayload(input({ parameter: "open_issue_count" })),
    /THRESHOLD_CURRENCY_NOT_ALLOWED/,
  );
  assert.throws(
    () => buildThresholdPayload(input({ lowerThreshold: "200" })),
    /INVALID_THRESHOLD_BOUNDS/,
  );
  assert.throws(
    () => buildThresholdPayload(input({ lowerThreshold: null, upperThreshold: null })),
    /THRESHOLD_BOUND_REQUIRED/,
  );
  assert.throws(
    () => buildThresholdPayload(input({ warningLevel: "50", issueLevel: "10" })),
    /INVALID_THRESHOLD_LEVELS/,
  );
  assert.throws(
    () => buildThresholdPayload(input({ upperThreshold: "1.23456" })),
    /INVALID_THRESHOLD_NUMBER/,
  );
});

test("threshold create posts the definition with an idempotency key", async () => {
  const log = calls();
  const result = await saveThreshold(
    transportWith({ ok: true, data: THRESHOLD }, log),
    CONTEXT,
    input({ thresholdId: " TH-COST-1 ", name: " Expense ceiling " }),
  );
  assert.equal(result.ok, true);
  assert.equal(log.posts.length, 1);
  assert.equal(log.posts[0].path, "/api/projects/project-1/thresholds");
  assert.equal(
    (log.posts[0].request as Record<string, unknown>).threshold_id,
    "TH-COST-1",
  );
  assert.equal(typeof log.posts[0].idempotencyKey, "string");
  assert.equal(log.patches.length, 0);
});

test("threshold edit patches the record with the expected revision", async () => {
  const log = calls();
  const result = await saveThreshold(
    transportWith({ ok: true, data: { ...THRESHOLD, revision: 3 } }, log),
    CONTEXT,
    input({ upperThreshold: "250" }),
    2,
  );
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.equal(result.data.revision, 3);
  assert.equal(log.patches.length, 1);
  assert.equal(log.patches[0].path, "/api/projects/project-1/thresholds/TH-COST-1");
  assert.equal(
    (log.patches[0].request as Record<string, unknown>).expected_revision,
    2,
  );
  assert.equal(
    (log.patches[0].request as Record<string, unknown>).upper_threshold,
    "250",
  );
});

test("threshold save does not write invalid definitions", async () => {
  const log = calls();
  const transport = transportWith({ ok: true, data: THRESHOLD }, log);
  const invalid = await saveThreshold(transport, CONTEXT, input({ issueLevel: "5" }));
  assert.equal(invalid.ok, false);
  if (!invalid.ok) assert.equal(invalid.error.code, "INVALID_THRESHOLD_LEVELS");
  assert.equal(log.posts.length, 0);
});

test("threshold delete sends the expected revision", async () => {
  const log = calls();
  const result = await deleteThreshold(
    transportWith({ ok: true, data: { deleted: true } }, log),
    CONTEXT,
    "TH-COST-1",
    2,
  );
  assert.equal(result.ok, true);
  assert.deepEqual(log.deletes, [{
    path: "/api/projects/project-1/thresholds/TH-COST-1",
    request: { expected_revision: 2 },
  }]);
});

test("threshold runs and history read their versioned envelopes", async () => {
  const runLog = calls();
  const runs = await loadThresholdRuns(
    transportWith({ ok: true, data: envelope("runs", [RUN]) }, runLog),
    CONTEXT,
    "TH-COST-1",
  );
  assert.equal(runs.ok, true);
  if (runs.ok) {
    assert.equal(runs.data[0].runSequence, 2);
    assert.equal(runs.data[0].observedValue, "900");
    assert.equal(runs.data[0].generatedIssueId, "THR-TH-COST-1-R2");
  }
  assert.deepEqual(runLog.gets, ["/api/projects/project-1/thresholds/TH-COST-1/runs"]);

  const historyLog = calls();
  const history = await loadThresholdHistory(
    transportWith({ ok: true, data: envelope("events", [EVENT]) }, historyLog),
    CONTEXT,
    "TH-COST-1",
  );
  assert.equal(history.ok, true);
  if (history.ok) {
    assert.equal(history.data[0].eventType, "updated");
    assert.equal(history.data[0].revision, 2);
  }
  assert.deepEqual(historyLog.gets, ["/api/projects/project-1/thresholds/TH-COST-1/history"]);

  const malformed = await loadThresholdRuns(
    transportWith({ ok: true, data: envelope("runs", [{ ...RUN, observed_value: 900 }]) }),
    CONTEXT,
    "TH-COST-1",
  );
  assert.equal(malformed.ok, false);
  if (!malformed.ok) assert.equal(malformed.error.code, "INVALID_THRESHOLD_RUN");
});

test("monitoring posts to the monitor action and parses the stored result", async () => {
  const log = calls();
  const result = await monitorThreshold(
    transportWith({
      ok: true,
      data: { contract_version: THRESHOLD_API_VERSION, threshold: THRESHOLD, run: RUN },
    }, log),
    CONTEXT,
    "TH-COST-1",
  );
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.equal(result.data.threshold.thresholdId, "TH-COST-1");
  assert.equal(result.data.run.level, "issue");
  assert.deepEqual(log.posts.map((entry) => entry.path), [
    "/api/projects/project-1/thresholds/TH-COST-1/monitor",
  ]);
  assert.deepEqual(log.posts[0].request, {});

  const malformed = await monitorThreshold(
    transportWith({
      ok: true,
      data: { contract_version: THRESHOLD_API_VERSION, threshold: THRESHOLD, run: { ...RUN, level: "critical" } },
    }),
    CONTEXT,
    "TH-COST-1",
  );
  assert.equal(malformed.ok, false);
  if (!malformed.ok) assert.equal(malformed.error.code, "INVALID_THRESHOLD_RUN");
});
