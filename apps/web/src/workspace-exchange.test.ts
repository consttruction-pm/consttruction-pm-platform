import assert from "node:assert/strict";
import { test } from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  EXCHANGE_API_VERSION,
  applyImport,
  exportDataset,
  loadCatalogue,
  loadImportRuns,
  mountWorkspaceExchangePage,
  parseCatalogue,
  parseExport,
  parseImportResult,
  parseImportRuns,
  previewImport,
} from "./workspace-exchange.js";

const context: ProjectContext = { tenant_id: "T-1", project_id: "P-1", revision: 3 };
const BASE = "/api/projects/P-1/exchange";

type Call = { method: string; path: string; body?: unknown };

function transport(
  handler: (call: Call) => ApiResult<unknown>,
): { transport: ApiTransport; calls: Call[] } {
  const calls: Call[] = [];
  const send =
    (method: string) =>
    async (path: string, body?: unknown, _context?: ProjectContext) => {
      const call = { method, path, body };
      calls.push(call);
      return handler(call);
    };
  return {
    calls,
    transport: {
      get: send("GET"),
      post: send("POST"),
    } as unknown as ApiTransport,
  };
}

const catalogue = {
  contract_version: EXCHANGE_API_VERSION,
  datasets: [
    {
      dataset: "activities",
      columns: ["activity_id", "name"],
      importable: false,
    },
    {
      dataset: "resources",
      columns: ["resource_id", "name", "resource_type"],
      importable: true,
    },
  ],
  max_import_chars: 1000000,
};

const exported = {
  contract_version: EXCHANGE_API_VERSION,
  dataset: "resources",
  columns: ["resource_id", "name", "resource_type"],
  rows: [{ resource_id: "R-1", name: "Crew", resource_type: "labor" }],
  row_count: 1,
  content: "resource_id,name,resource_type\nR-1,Crew,labor\n",
  project_revision: 3,
  generated_at: "2026-11-12T08:00:00+00:00",
};

function importResult(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    contract_version: EXCHANGE_API_VERSION,
    dataset: "resources",
    columns: ["resource_id", "name", "resource_type"],
    row_count: 1,
    accepted: 1,
    rejected: 0,
    valid: true,
    errors: [],
    rows: [{ resource_id: "E2E-1", name: "Crew", resource_type: "labor" }],
    created: [],
    ...overrides,
  };
}

const runs = {
  contract_version: EXCHANGE_API_VERSION,
  runs: [
    {
      run_id: "EXR-resources-1",
      dataset: "resources",
      mode: "apply",
      row_count: 1,
      accepted: 1,
      rejected: 0,
      occurred_at: "2026-11-12T08:00:00+00:00",
      actor_id: "preview-admin",
      idempotency_key: "key-1",
    },
  ],
};

test("catalogue and export parsers fail closed on a drifted contract", () => {
  assert.equal(parseCatalogue(catalogue).datasets.length, 2);
  for (const bad of [
    { ...catalogue, contract_version: "p6-exchange-api.v2" },
    { ...catalogue, datasets: [{}] },
    { ...catalogue, datasets: [{ dataset: "resources", columns: [], importable: "yes" }] },
    { ...catalogue, datasets: [catalogue.datasets[0], catalogue.datasets[0]] },
    { ...catalogue, max_import_chars: -1 },
  ]) {
    assert.throws(() => parseCatalogue(bad));
  }

  assert.equal(parseExport(exported).rowCount, 1);
  for (const bad of [
    { ...exported, contract_version: "x" },
    { ...exported, rows: [null] },
    { ...exported, row_count: 0 },
    { ...exported, project_revision: -1 },
    { ...exported, content: "" },
  ]) {
    assert.throws(() => parseExport(bad));
  }
});

test("import result and run parsers fail closed and preserve row errors", () => {
  const result = parseImportResult(importResult());
  assert.equal(result.valid, true);
  assert.equal(result.created.length, 0);
  assert.equal(result.runId, null);

  const invalid = parseImportResult(
    importResult({
      valid: false,
      accepted: 0,
      rejected: 1,
      errors: [{ row: 2, field: "calendar_id", code: "RESOURCE_CALENDAR_NOT_FOUND" }],
      rows: [],
    }),
  );
  assert.equal(invalid.errors[0].code, "RESOURCE_CALENDAR_NOT_FOUND");
  for (const bad of [
    { ...importResult(), contract_version: "x" },
    { ...importResult(), valid: "yes" },
    { ...importResult(), errors: [{}] },
    { ...importResult(), accepted: -1 },
    { ...importResult(), created: [1] },
  ]) {
    assert.throws(() => parseImportResult(bad));
  }

  const parsedRuns = parseImportRuns(runs);
  assert.equal(parsedRuns[0].runId, "EXR-resources-1");
  assert.equal(parsedRuns[0].idempotencyKey, "key-1");
  assert.throws(() => parseImportRuns({ ...runs, runs: [{}] }));
  assert.throws(() => parseImportRuns({ ...runs, contract_version: "x" }));
});

test("requests carry the dataset query and the idempotency key", async () => {
  const stub = transport((call) => {
    if (call.path.endsWith("/datasets")) return { ok: true, data: catalogue };
    if (call.path.includes("/export?")) return { ok: true, data: exported };
    if (call.path.endsWith("/import/preview")) return { ok: true, data: importResult() };
    if (call.path.endsWith("/import")) return { ok: true, data: importResult({ created: ["E2E-1"] }) };
    return { ok: true, data: runs };
  });

  await loadCatalogue(stub.transport, context);
  await exportDataset(stub.transport, context, "resources");
  await previewImport(stub.transport, context, "resources", "csv");
  await applyImport(stub.transport, context, "resources", "csv", "key-1");
  await loadImportRuns(stub.transport, context);

  assert.equal(stub.calls[0].path, `${BASE}/datasets`);
  assert.equal(stub.calls[1].path, `${BASE}/export?dataset=resources`);
  assert.deepEqual(stub.calls[2].body, { dataset: "resources", content: "csv" });
  assert.deepEqual(stub.calls[3].body, {
    dataset: "resources",
    content: "csv",
    idempotency_key: "key-1",
  });
  assert.equal(stub.calls[4].path, `${BASE}/imports`);
});

function mountHost(): {
  host: HTMLElement;
  click: (target: Record<string, unknown>) => void;
  change: (target: Record<string, unknown>) => void;
  setContent: (value: string) => void;
} {
  const listeners = new Map<string, (event: Event) => void>();
  const host = {
    dataset: {} as Record<string, string>,
    innerHTML: "",
    addEventListener: (type: string, listener: (event: Event) => void) =>
      listeners.set(type, listener),
    querySelectorAll: () => [],
    querySelector: () => null,
    contains: () => true,
    appendChild: () => undefined,
  };
  const fire = (type: string, target: Record<string, unknown>): void => {
    const withClosest = {
      ...target,
      closest: (selector: string) => {
        const dataset = (target.dataset ?? {}) as Record<string, string>;
        if (selector === "[data-exchange-tab]" && dataset.exchangeTab) return withClosest;
        if (selector === "[data-exchange-action]" && dataset.exchangeAction) return withClosest;
        return null;
      },
    };
    listeners.get(type)?.({ target: withClosest } as unknown as Event);
  };
  return {
    host: host as unknown as HTMLElement,
    click: (target) => fire("click", target),
    change: (target) => fire("change", target),
    setContent: (value) => fire("input", { matches: () => true, value }),
  };
}

function mountTransport(valid = true): ApiTransport {
  return transport((call) => {
    if (call.path.endsWith("/datasets")) return { ok: true, data: catalogue };
    if (call.path.includes("/export?")) return { ok: true, data: exported };
    if (call.path.endsWith("/import/preview")) {
      return {
        ok: true,
        data: valid
          ? importResult()
          : importResult({
              valid: false,
              accepted: 0,
              rejected: 1,
              errors: [
                { row: 2, field: "resource_type", code: "INVALID_RESOURCE_TYPE" },
              ],
              rows: [],
            }),
      };
    }
    if (call.path.endsWith("/import")) {
      return { ok: true, data: importResult({ created: ["E2E-1"] }) };
    }
    return { ok: true, data: runs };
  }).transport;
}

test("viewer mode exports and validates but cannot apply", async () => {
  const { host, click } = mountHost();
  mountWorkspaceExchangePage(host, {
    transport: mountTransport(),
    context,
    locale: "en",
    canWrite: false,
  });
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.match(host.innerHTML, /data-exchange-tab="export"/);
  assert.match(host.innerHTML, /data-exchange-tab="import"/);
  assert.match(host.innerHTML, /data-exchange-tab="history"/);
  assert.match(host.innerHTML, /data-exchange-dataset/);
  assert.match(host.innerHTML, /<option value="activities"/);

  click({ dataset: { exchangeAction: "export" } });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.match(host.innerHTML, /data-exchange-export-table/);
  assert.match(host.innerHTML, /Crew/);
  assert.match(host.innerHTML, /data-exchange-export-meta/);

  click({ dataset: { exchangeTab: "import" } });
  assert.match(host.innerHTML, /data-exchange-content[^>]*disabled/);
  assert.match(host.innerHTML, /data-exchange-action="apply"[^>]*disabled/);

  click({ dataset: { exchangeTab: "history" } });
  assert.match(host.innerHTML, /data-exchange-run-row/);
  assert.match(host.innerHTML, /EXR-resources-1/);
});

test("writer mode validates a file, shows row errors, and applies a valid import", async () => {
  const { host, click, change, setContent } = mountHost();
  mountWorkspaceExchangePage(host, {
    transport: mountTransport(false),
    context,
    locale: "fa",
    canWrite: true,
  });
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.match(host.innerHTML, /ورود \/ خروجی/);
  click({ dataset: { exchangeTab: "import" } });
  change({ dataset: {}, matches: (selector: string) => selector === "[data-exchange-import-dataset]", value: "resources" });
  setContent("resource_id,name,resource_type\nE2E-1,Crew,robot\n");
  click({ dataset: { exchangeAction: "validate" } });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.match(host.innerHTML, /data-exchange-import-summary[^>]*data-valid="false"/);
  assert.match(host.innerHTML, /INVALID_RESOURCE_TYPE/);
  assert.match(host.innerHTML, /data-exchange-action="apply"[^>]*disabled/);
});

test("writer mode applies a valid preview and reports created rows", async () => {
  const { host, click, change, setContent } = mountHost();
  mountWorkspaceExchangePage(host, {
    transport: mountTransport(true),
    context,
    locale: "en",
    canWrite: true,
  });
  await new Promise((resolve) => setTimeout(resolve, 0));

  click({ dataset: { exchangeTab: "import" } });
  change({ dataset: {}, matches: (selector: string) => selector === "[data-exchange-import-dataset]", value: "resources" });
  setContent("resource_id,name,resource_type\nE2E-1,Crew,labor\n");
  click({ dataset: { exchangeAction: "validate" } });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.match(host.innerHTML, /data-valid="true"/);
  assert.doesNotMatch(host.innerHTML, /data-exchange-action="apply"[^>]*disabled/);

  click({ dataset: { exchangeAction: "apply" } });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.match(host.innerHTML, /data-exchange-created/);
  assert.match(host.innerHTML, /E2E-1/);
});
