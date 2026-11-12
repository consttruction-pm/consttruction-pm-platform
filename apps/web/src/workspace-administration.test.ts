import assert from "node:assert/strict";
import { test } from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  ADMIN_API_VERSION,
  PERIOD_API_VERSION,
  createFinancialPeriod,
  deleteDictionary,
  loadDictionaries,
  loadFinancialPeriods,
  loadPermissionMatrix,
  loadPreferences,
  mountWorkspaceAdministrationPage,
  parseDictionaryEntry,
  parseDictionaryList,
  parseFinancialPeriodList,
  parsePermissionMatrix,
  parsePreferences,
  saveDictionary,
  savePreferences,
  type DictionaryDraft,
  type FinancialPeriodDraft,
} from "./workspace-administration.js";

const context: ProjectContext = { tenant_id: "T-1", project_id: "P-1", revision: 3 };
const BASE = "/api/projects/P-1/administration";
const PERIOD_BASE = "/api/projects/P-1/p6/financial-periods";

type Call = { method: string; path: string; body?: unknown; idempotencyKey?: string };

function transport(
  handler: (call: Call) => ApiResult<unknown>,
): { transport: ApiTransport; calls: Call[] } {
  const calls: Call[] = [];
  const send = (method: string) =>
    async (path: string, body?: unknown, _context?: ProjectContext, idempotencyKey?: string) => {
      const call = { method, path, body, idempotencyKey };
      calls.push(call);
      return handler(call);
    };
  return {
    calls,
    transport: {
      get: send("GET"),
      post: send("POST"),
      patch: send("PATCH"),
      put: send("PUT"),
      delete: send("DELETE"),
    } as unknown as ApiTransport,
  };
}

function preferences(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    contract_version: ADMIN_API_VERSION,
    currency: "USD",
    unit_of_measure: "day",
    date_display: "gregorian",
    decimal_places: 2,
    fiscal_year_start_month: 1,
    revision: 1,
    updated_at: "2026-11-12T08:00:00+00:00",
    updated_by: "preview-admin",
    ...overrides,
  };
}

const matrix = {
  contract_version: ADMIN_API_VERSION,
  permissions: ["project.read", "project.write", "form.read", "form.write"],
  roles: [
    { role: "viewer", permissions: ["project.read", "form.read"] },
    { role: "planner", permissions: ["project.read", "form.read", "form.write"] },
    {
      role: "project_admin",
      permissions: ["project.read", "project.write", "form.read", "form.write"],
    },
  ],
};

const entry = {
  contract_version: ADMIN_API_VERSION,
  dictionary_code: "cost_category",
  entry_id: "MAT",
  label: "Materials",
  sequence: 10,
  is_active: true,
  revision: 1,
  updated_at: null,
  updated_by: "preview-admin",
};

const dictionaryList = {
  contract_version: ADMIN_API_VERSION,
  dictionary_codes: [
    "cost_category",
    "risk_category",
    "issue_type",
    "document_type",
    "expense_category",
  ],
  entries: [entry],
};

const periodList = {
  contract_version: PERIOD_API_VERSION,
  financial_periods: [
    {
      contract_version: PERIOD_API_VERSION,
      kind: "p6_financial_period",
      scope: { tenant_id: "T-1", project_id: "P-1", project_revision: 3 },
      financial_period: {
        period_id: "2026-01",
        name: "January 2026",
        start_date: "2026-01-01",
        end_date: "2026-01-31",
        status: "OPEN",
      },
    },
  ],
};

const draft: DictionaryDraft = {
  dictionaryCode: "cost_category",
  entryId: "MAT",
  label: "Materials",
  sequence: 10,
  isActive: true,
};

const periodDraft: FinancialPeriodDraft = {
  periodId: "2026-02",
  name: "February 2026",
  startDate: "2026-02-01",
  endDate: "2026-02-28",
  status: "OPEN",
};

test("preference parser accepts the administrative defaults and fails closed", () => {
  const parsed = parsePreferences(preferences());
  assert.equal(parsed.currency, "USD");
  assert.equal(parsed.dateDisplay, "gregorian");
  assert.equal(parsed.revision, 1);

  for (const bad of [
    preferences({ contract_version: "p6-administration-api.v2" }),
    preferences({ currency: "usd" }),
    preferences({ currency: "US" }),
    preferences({ date_display: "hijri" }),
    preferences({ decimal_places: 5 }),
    preferences({ fiscal_year_start_month: 0 }),
    preferences({ fiscal_year_start_month: 13 }),
    preferences({ unit_of_measure: "" }),
    preferences({ revision: "1" }),
  ]) {
    assert.throws(() => parsePreferences(bad));
  }
});

test("permission matrix rejects grants outside the known permission set and duplicate roles", () => {
  const parsed = parsePermissionMatrix(matrix);
  assert.deepEqual(parsed.roles.map((role) => role.role), [
    "viewer",
    "planner",
    "project_admin",
  ]);
  assert.equal(parsed.permissions.length, 4);

  for (const bad of [
    { ...matrix, contract_version: "v2" },
    { ...matrix, permissions: [] },
    { ...matrix, permissions: ["project.read", "project.read"] },
    { ...matrix, roles: [{ role: "viewer", permissions: ["project.delete"] }], permissions: ["project.read"] },
    {
      ...matrix,
      roles: [
        { role: "viewer", permissions: [] },
        { role: "viewer", permissions: [] },
      ],
    },
    { ...matrix, roles: [{ role: "", permissions: [] }] },
  ]) {
    assert.throws(() => parsePermissionMatrix(bad));
  }
});

test("dictionary parsers fail closed on code, sequence and duplicate identity drift", () => {
  const parsed = parseDictionaryEntry(entry);
  assert.equal(parsed.dictionaryCode, "cost_category");
  assert.equal(parsed.sequence, 10);
  assert.equal(parsed.isActive, true);

  for (const bad of [
    { ...entry, contract_version: "v2" },
    { ...entry, dictionary_code: "resource_type" },
    { ...entry, entry_id: "  " },
    { ...entry, sequence: 10000 },
    { ...entry, sequence: -1 },
    { ...entry, is_active: "true" },
  ]) {
    assert.throws(() => parseDictionaryEntry(bad));
  }

  const list = parseDictionaryList(dictionaryList);
  assert.equal(list.codes.length, 5);
  assert.equal(list.entries[0].entryId, "MAT");

  assert.throws(() =>
    parseDictionaryList({ ...dictionaryList, dictionary_codes: ["cost_category", "unknown_code"] }),
  );
  assert.throws(() =>
    parseDictionaryList({
      ...dictionaryList,
      entries: [entry, { ...entry, label: "Duplicate" }],
    }),
  );
  assert.throws(() => parseDictionaryList({ ...dictionaryList, entries: "none" }));
});

test("financial period parser requires the period contract and calendar dates", () => {
  const parsed = parseFinancialPeriodList(periodList);
  assert.equal(parsed[0].periodId, "2026-01");
  assert.equal(parsed[0].status, "OPEN");

  const shell = periodList.financial_periods[0];
  for (const bad of [
    { ...periodList, contract_version: "p6-financial-period-api.v2" },
    { ...periodList, financial_periods: [{ ...shell, financial_period: { ...shell.financial_period, start_date: "01/01/2026" } }] },
    { ...periodList, financial_periods: [{ ...shell, financial_period: { ...shell.financial_period, status: "DRAFT" } }] },
    { ...periodList, financial_periods: [{ ...shell, financial_period: undefined }] },
  ]) {
    assert.throws(() => parseFinancialPeriodList(bad));
  }
});

test("preferences are read per project and saved with an expected revision", async () => {
  const stub = transport((call) => {
    if (call.method === "GET") {
      assert.equal(call.path, `${BASE}/preferences`);
      return { ok: true, data: preferences() };
    }
    assert.equal(call.method, "PUT");
    assert.equal(call.path, `${BASE}/preferences`);
    const body = call.body as Record<string, unknown>;
    assert.deepEqual(body, {
      currency: "EUR",
      unit_of_measure: "hour",
      date_display: "jalali",
      decimal_places: 3,
      fiscal_year_start_month: 4,
      expected_revision: 7,
    });
    return { ok: true, data: preferences({ currency: "EUR", revision: 8 }) };
  });

  const read = await loadPreferences(stub.transport, context);
  assert.equal(read.ok, true);

  const saved = await savePreferences(
    stub.transport,
    context,
    {
      currency: "EUR",
      unitOfMeasure: "hour",
      dateDisplay: "jalali",
      decimalPlaces: 3,
      fiscalYearStartMonth: 4,
    },
    7,
  );
  assert.equal(saved.ok, true);
  assert.deepEqual(
    stub.calls.map((call) => call.method),
    ["GET", "PUT"],
  );
});

test("permission matrix and dictionary reads forward filters", async () => {
  const stub = transport((call) => {
    if (call.path.endsWith("/permission-matrix")) {
      return { ok: true, data: matrix };
    }
    assert.equal(call.path, `${BASE}/dictionaries?dictionary_code=risk_category&search=steel`);
    return { ok: true, data: dictionaryList };
  });

  assert.equal((await loadPermissionMatrix(stub.transport, context)).ok, true);
  const filtered = await loadDictionaries(stub.transport, context, {
    code: "risk_category",
    search: "steel",
  });
  assert.equal(filtered.ok, true);
  assert.deepEqual(
    stub.calls.map((call) => call.path),
    [
      `${BASE}/permission-matrix`,
      `${BASE}/dictionaries?dictionary_code=risk_category&search=steel`,
    ],
  );
});

test("dictionary writes create with an idempotency key and patch with an expected revision", async () => {
  const stub = transport((call) => {
    if (call.method === "POST") {
      assert.equal(call.path, `${BASE}/dictionaries`);
      assert.deepEqual(call.body, {
        dictionary_code: "cost_category",
        entry_id: "MAT",
        label: "Materials",
        sequence: 10,
        is_active: true,
      });
      assert.equal(call.idempotencyKey, "key-1");
      return { ok: true, data: entry };
    }
    assert.equal(call.method, "PATCH");
    assert.equal(call.path, `${BASE}/dictionaries/cost_category/MAT`);
    assert.deepEqual(call.body, {
      label: "Materials and supplies",
      sequence: 11,
      is_active: false,
      expected_revision: 2,
    });
    return {
      ok: true,
      data: { ...entry, label: "Materials and supplies", sequence: 11, is_active: false, revision: 3 },
    };
  });

  const created = await saveDictionary(stub.transport, context, draft, undefined, "key-1");
  assert.equal(created.ok, true);
  const updated = await saveDictionary(
    stub.transport,
    context,
    { ...draft, label: "Materials and supplies", sequence: 11, isActive: false },
    2,
  );
  assert.equal(updated.ok, true);
  assert.equal(stub.calls[0].idempotencyKey, "key-1");
});

test("dictionary delete carries the read revision and financial periods use the p6 register", async () => {
  const stub = transport((call) => {
    if (call.method === "DELETE") {
      assert.equal(call.path, `${BASE}/dictionaries/cost_category/MAT`);
      assert.deepEqual(call.body, { expected_revision: 4 });
      return { ok: true, data: { deleted: true } };
    }
    if (call.method === "POST") {
      assert.equal(call.path, PERIOD_BASE);
      assert.deepEqual(call.body, {
        period_id: "2026-02",
        name: "February 2026",
        start_date: "2026-02-01",
        end_date: "2026-02-28",
        status: "OPEN",
      });
      return { ok: true, data: periodList.financial_periods[0] };
    }
    assert.equal(call.path, PERIOD_BASE);
    return { ok: true, data: periodList };
  });

  const removed = await deleteDictionary(stub.transport, context, {
    ...parseDictionaryEntry(entry),
    revision: 4,
  });
  assert.equal(removed.ok, true);

  const periods = await loadFinancialPeriods(stub.transport, context);
  assert.equal(periods.ok, true);

  const created = await createFinancialPeriod(stub.transport, context, periodDraft);
  assert.equal(created.ok, true);
  if (created.ok) assert.equal(created.data.periodId, "2026-01");
});

function mountHost(): {
  host: HTMLElement;
  click: (tab: string) => void;
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
  };
  const click = (tab: string): void => {
    const target = {
      dataset: { adminTab: tab },
      closest: (selector: string) => (selector === "[data-admin-tab]" ? target : null),
    };
    listeners.get("click")?.({ target } as unknown as Event);
  };
  return { host: host as unknown as HTMLElement, click };
}

function mountTransport(): ApiTransport {
  return transport((call) => {
    if (call.path.endsWith("/preferences")) return { ok: true, data: preferences() };
    if (call.path.endsWith("/permission-matrix")) return { ok: true, data: matrix };
    if (call.path.includes("/dictionaries")) return { ok: true, data: dictionaryList };
    return { ok: true, data: periodList };
  }).transport;
}

test("viewer mode renders the authoritative tabs read-only", async () => {
  const { host, click } = mountHost();
  mountWorkspaceAdministrationPage(host, {
    transport: mountTransport(),
    context,
    locale: "en",
    canAdmin: false,
  });
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.match(host.innerHTML, /data-admin-tab="preferences"/);
  assert.match(host.innerHTML, /data-admin-tab="dictionaries"/);
  assert.match(host.innerHTML, /data-admin-tab="matrix"/);
  assert.match(host.innerHTML, /data-admin-tab="periods"/);
  assert.match(host.innerHTML, /data-admin-preferences-form/);
  assert.doesNotMatch(host.innerHTML, /Save preferences/);
  assert.match(host.innerHTML, /<input name="admin-currency"[^>]*disabled/);

  click("matrix");
  assert.match(host.innerHTML, /data-admin-matrix/);
  assert.match(host.innerHTML, /project_admin/);

  click("periods");
  assert.match(host.innerHTML, /data-admin-period-form/);
  assert.match(host.innerHTML, /data-admin-period-row/);
  assert.doesNotMatch(host.innerHTML, /Save period/);
});

test("administrator mode exposes write controls and the matrix keeps every policy grant", async () => {
  const { host, click } = mountHost();
  mountWorkspaceAdministrationPage(host, {
    transport: mountTransport(),
    context,
    locale: "fa",
    canAdmin: true,
  });
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.match(host.innerHTML, /مدیریت/);
  assert.match(host.innerHTML, /ذخیره ترجیحات/);
  assert.match(host.innerHTML, /<input name="admin-currency"[^>]*value="USD"/);

  click("dictionaries");
  assert.match(host.innerHTML, /data-admin-dict-form/);
  assert.match(host.innerHTML, /data-admin-dict-row/);
  assert.match(host.innerHTML, /ورودی جدید/);

  click("matrix");
  assert.match(host.innerHTML, /data-admin-permission="project.write"/);
  assert.match(host.innerHTML, /data-admin-grant="viewer"/);
});
