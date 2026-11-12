import assert from "node:assert/strict";
import { test } from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  REPORT_API_VERSION,
  deleteReport,
  loadReportRun,
  loadReportRuns,
  loadReports,
  parseCatalogue,
  parseReportDefinition,
  parseReportList,
  parseReportRun,
  runReport,
  saveReport,
  type ReportInput,
} from "./workspace-reports.js";

const context: ProjectContext = { tenant_id: "T-1", project_id: "P-1", revision: 3 };
const BASE = "/api/projects/P-1/reports";

type Call = { method: string; path: string; body?: unknown };

function transport(
  handler: (call: Call) => ApiResult<unknown>,
): { transport: ApiTransport; calls: Call[] } {
  const calls: Call[] = [];
  const send = (method: string) => async (path: string, body?: unknown, _context?: ProjectContext) => {
    const call = { method, path, body };
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

const catalogue = [
  {
    subject: "activities",
    label: "Activities",
    fields: [
      { key: "activity_id", label: "Activity ID", data_type: "string" },
      { key: "name", label: "Activity Name", data_type: "string" },
      { key: "duration", label: "Duration", data_type: "decimal" },
    ],
  },
  {
    subject: "resources",
    label: "Resources",
    fields: [
      { key: "resource_id", label: "Resource ID", data_type: "string" },
      { key: "is_active", label: "Active", data_type: "boolean" },
    ],
  },
  {
    subject: "risks",
    label: "Risks",
    fields: [
      { key: "risk_id", label: "Risk ID", data_type: "string" },
      { key: "score", label: "Score", data_type: "integer" },
    ],
  },
];

function definition(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    contract_version: REPORT_API_VERSION,
    report_id: "RPT-ACT",
    name: "Activity register",
    description: "Stored activities.",
    subject: "activities",
    columns: ["activity_id", "name", "duration"],
    record_revision: 1,
    ...overrides,
  };
}

function run(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    contract_version: REPORT_API_VERSION,
    run_id: "RUN-RPT-ACT-1",
    report_id: "RPT-ACT",
    report_revision: 1,
    project_revision: 3,
    subject: "activities",
    columns: ["activity_id", "name"],
    row_count: 2,
    generated_at: "2026-11-12T10:00:00+00:00",
    generated_by: "u-1",
    rows: [
      { activity_id: "A100", name: "Kickoff" },
      { activity_id: "A110", name: "Mobilization" },
    ],
    ...overrides,
  };
}

function input(overrides: Partial<ReportInput> = {}): ReportInput {
  return {
    reportId: "RPT-ACT",
    name: "Activity register",
    description: "Stored activities.",
    subject: "activities",
    columns: ["activity_id", "name", "duration"],
    ...overrides,
  };
}

test("catalogue parser accepts the three subjects and rejects drift", () => {
  const parsed = parseCatalogue(catalogue);
  assert.deepEqual(parsed.map((item) => item.subject), ["activities", "resources", "risks"]);
  assert.equal(parsed[0].fields[2].dataType, "decimal");

  assert.throws(() => parseCatalogue([{ ...catalogue[0], subject: "documents" }]));
  assert.throws(() => parseCatalogue([{ ...catalogue[0], fields: [] }]));
  assert.throws(() =>
    parseCatalogue([
      { ...catalogue[0], fields: [catalogue[0].fields[0], catalogue[0].fields[0]] },
    ]),
  );
  assert.throws(() => parseCatalogue([catalogue[0], catalogue[0]]));
});

test("definition parser fails closed on contract, subject and column drift", () => {
  const parsed = parseReportDefinition(definition(), parseCatalogue(catalogue));
  assert.equal(parsed.reportId, "RPT-ACT");
  assert.deepEqual(parsed.columns, ["activity_id", "name", "duration"]);
  assert.equal(parsed.revision, 1);

  for (const bad of [
    definition({ contract_version: "p6-report-api.v2" }),
    definition({ subject: "documents" }),
    definition({ columns: [] }),
    definition({ columns: ["activity_id", "activity_id"] }),
    definition({ columns: ["activity_id", "budget"] }),
    definition({ record_revision: 0 }),
    definition({ report_id: " " }),
  ]) {
    assert.throws(() => parseReportDefinition(bad, parseCatalogue(catalogue)));
  }
});

test("list parser carries the catalogue and rejects duplicate ids", () => {
  const parsed = parseReportList({
    contract_version: REPORT_API_VERSION,
    catalogue,
    reports: [definition()],
  });
  assert.equal(parsed.reports.length, 1);
  assert.equal(parsed.catalogue.length, 3);
  assert.throws(() =>
    parseReportList({
      contract_version: REPORT_API_VERSION,
      catalogue,
      reports: [definition(), definition()],
    }),
  );
});

test("run parser requires one key per selected column and an exact row count", () => {
  const parsed = parseReportRun(run());
  assert.equal(parsed.runId, "RUN-RPT-ACT-1");
  assert.equal(parsed.rowCount, 2);
  assert.equal(parsed.rows[1].name, "Mobilization");

  for (const bad of [
    run({ rows: [{ activity_id: "A100", name: "Kickoff" }] }),
    run({ rows: [{ activity_id: "A100" }, { activity_id: "A110", name: "x" }] }),
    run({ rows: [{ activity_id: "A100", name: "x" }, { activity_id: "A110", name: "y", extra: 1 }] }),
    run({ row_count: -1 }),
    run({ columns: [] }),
  ]) {
    assert.throws(() => parseReportRun(bad));
  }
});

test("loadReports forwards subject and search filters", async () => {
  const stub = transport((call) => {
    assert.equal(call.method, "GET");
    assert.equal(call.path, `${BASE}?subject=risks&search=steel`);
    return {
      ok: true,
      data: { contract_version: REPORT_API_VERSION, catalogue, reports: [] },
    };
  });
  const result = await loadReports(stub.transport, context, {
    subject: "risks",
    search: "steel",
  });
  assert.equal(result.ok, true);
  assert.deepEqual(stub.calls[0].path, `${BASE}?subject=risks&search=steel`);
});

test("saveReport posts an idempotent create and re-reads the catalogue", async () => {
  const stub = transport((call) => {
    if (call.method === "POST") {
      assert.equal(call.path, BASE);
      const body = call.body as Record<string, unknown>;
      assert.equal(body.report_id, "RPT-ACT");
      assert.equal(body.subject, "activities");
      assert.deepEqual(body.columns, ["activity_id", "name", "duration"]);
      assert.match(String(body.idempotency_key), /^report-RPT-ACT-/);
      return { ok: true, data: definition() };
    }
    assert.equal(call.method, "GET");
    return {
      ok: true,
      data: { contract_version: REPORT_API_VERSION, catalogue, reports: [definition()] },
    };
  });
  const result = await saveReport(stub.transport, context, input());
  assert.equal(result.ok, true);
  if (result.ok) assert.equal(result.data.name, "Activity register");
  assert.equal(stub.calls.length, 2);
});

test("saveReport patches the expected revision", async () => {
  const stub = transport((call) => {
    if (call.method === "PATCH") {
      assert.equal(call.path, `${BASE}/RPT-ACT`);
      const body = call.body as Record<string, unknown>;
      assert.equal(body.expected_revision, 2);
      assert.deepEqual(body.columns, ["activity_id", "name"]);
      return { ok: true, data: definition({ columns: ["activity_id", "name"], record_revision: 3 }) };
    }
    return {
      ok: true,
      data: { contract_version: REPORT_API_VERSION, catalogue, reports: [definition()] },
    };
  });
  const result = await saveReport(
    stub.transport,
    context,
    input({ columns: ["activity_id", "name"] }),
    2,
  );
  assert.equal(result.ok, true);
  if (result.ok) assert.equal(result.data.revision, 3);
});

test("runReport posts to the run action and parses stored rows", async () => {
  const stub = transport((call) => {
    assert.equal(call.method, "POST");
    assert.equal(call.path, `${BASE}/RPT-ACT/run`);
    return { ok: true, data: run() };
  });
  const result = await runReport(stub.transport, context, "RPT-ACT");
  assert.equal(result.ok, true);
  if (result.ok) assert.equal(result.data.rows.length, 2);
});

test("run history and stored run loaders use the documented paths", async () => {
  const stub = transport((call) => {
    if (call.path === `${BASE}/RPT-ACT/runs)`) throw new Error("unreachable");
    if (call.path.endsWith("/runs")) {
      return {
        ok: true,
        data: {
          contract_version: REPORT_API_VERSION,
          report_id: "RPT-ACT",
          runs: [{ ...run(), rows: undefined }],
        },
      };
    }
    assert.equal(call.path, `${BASE}/RPT-ACT/runs/RUN-RPT-ACT-1`);
    return { ok: true, data: run() };
  });
  const history = await loadReportRuns(stub.transport, context, "RPT-ACT");
  assert.equal(history.ok, true);
  if (history.ok) assert.equal(history.data[0].runId, "RUN-RPT-ACT-1");
  const stored = await loadReportRun(stub.transport, context, "RPT-ACT", "RUN-RPT-ACT-1");
  assert.equal(stored.ok, true);
});

test("deleteReport sends the expected revision", async () => {
  const stub = transport((call) => {
    assert.equal(call.method, "DELETE");
    assert.equal(call.path, `${BASE}/RPT-ACT`);
    assert.deepEqual(call.body, { expected_revision: 4 });
    return { ok: true, data: { contract_version: REPORT_API_VERSION, deleted: true } };
  });
  const result = await deleteReport(stub.transport, context, "RPT-ACT", 4);
  assert.equal(result.ok, true);
  if (result.ok) assert.equal(result.data.deleted, true);
});
