import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  BUDGET_API_VERSION,
  buildBudgetChangePayload,
  buildBudgetLinePayload,
  buildFundingPayload,
  createBudgetChange,
  createBudgetLine,
  createFundingSource,
  isMoneyText,
  loadBudgetChanges,
  loadBudgetHistory,
  loadBudgetLines,
  loadBudgetSummary,
  loadFundingSources,
  parseBudgetChange,
  parseBudgetLine,
  parseBudgetSummary,
  parseFundingSource,
  transitionBudgetChange,
  updateBudgetLine,
  updateFundingSource,
} from "./workspace-budget.js";

const CONTEXT: ProjectContext = { tenant_id: "t1", project_id: "project-1", revision: 3 };

const LINE = {
  contract_version: BUDGET_API_VERSION,
  budget_line_id: "BL-1",
  description: "Concrete works",
  currency: "USD",
  original_amount: "1000.00",
  cost_account_id: "CA-1",
  period_id: "2026",
  revision: 2,
};

const CHANGE = {
  contract_version: BUDGET_API_VERSION,
  change_id: "BC-1",
  budget_line_id: "BL-1",
  amount: "-100.00",
  reason: "Reduced scope",
  status: "pending",
  revision: 1,
};

const FUNDING = {
  contract_version: BUDGET_API_VERSION,
  funding_id: "FS-1",
  name: "Owner equity",
  source_type: "internal",
  currency: "USD",
  amount: "400.00",
  period_id: null,
  revision: 1,
};

type Calls = {
  gets: string[];
  posts: { path: string; request: unknown; idempotencyKey?: string }[];
  patches: { path: string; request: unknown }[];
};

function calls(): Calls {
  return { gets: [], posts: [], patches: [] };
}

function transportWith(result: ApiResult<unknown>, log: Calls): ApiTransport {
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
  };
}

test("parsers accept the versioned budget contract and reject drift", () => {
  assert.deepEqual(parseBudgetLine(LINE), {
    budgetLineId: "BL-1",
    description: "Concrete works",
    currency: "USD",
    originalAmount: "1000.00",
    costAccountId: "CA-1",
    periodId: "2026",
    revision: 2,
  });
  assert.equal(parseBudgetChange(CHANGE).status, "pending");
  assert.equal(parseFundingSource(FUNDING).amount, "400.00");
  assert.equal(parseBudgetSummary({
    currency: "USD",
    original_budget: "1000.00",
    approved_changes: "-100.00",
    current_budget: "900.00",
    pending_changes: "0.00",
    funding: "400.00",
    funding_balance: "500.00",
  }).fundingBalance, "500.00");

  assert.throws(() => parseBudgetLine({ ...LINE, contract_version: "1.0" }), /INVALID_BUDGET_LINE/);
  assert.throws(() => parseBudgetLine({ ...LINE, revision: 0 }), /INVALID_BUDGET_LINE/);
  assert.throws(() => parseBudgetChange({ ...CHANGE, status: "draft" }), /INVALID_BUDGET_CHANGE/);
  assert.throws(() => parseFundingSource({ ...FUNDING, source_type: "barter" }), /INVALID_BUDGET_FUNDING/);
  assert.throws(() => parseBudgetSummary({ currency: "" }), /INVALID_BUDGET_SUMMARY/);
});

test("payload builders enforce two-decimal money and currency shape", () => {
  assert.deepEqual(buildBudgetLinePayload({
    budgetLineId: "BL-1",
    description: "Concrete",
    currency: "usd",
    originalAmount: "1000",
    costAccountId: "",
    periodId: "",
  }), {
    budget_line_id: "BL-1",
    description: "Concrete",
    currency: "USD",
    original_amount: "1000",
    cost_account_id: null,
    period_id: null,
  });
  assert.deepEqual(buildBudgetChangePayload({ changeId: "BC-1", amount: "-100.00", reason: "Scope" }), {
    change_id: "BC-1",
    amount: "-100.00",
    reason: "Scope",
  });
  assert.equal(buildFundingPayload({
    fundingId: "FS-1",
    name: "Grant",
    sourceType: "grant",
    currency: "EUR",
    amount: "0.00",
    periodId: "2026",
  }).source_type, "grant");

  assert.throws(() => buildBudgetLinePayload({
    budgetLineId: "BL-1",
    description: "Concrete",
    currency: "US",
    originalAmount: "1.00",
    costAccountId: "",
    periodId: "",
  }), /INVALID_BUDGET_CURRENCY/);
  assert.throws(() => buildBudgetLinePayload({
    budgetLineId: "BL-1",
    description: "Concrete",
    currency: "USD",
    originalAmount: "1.005",
    costAccountId: "",
    periodId: "",
  }), /INVALID_BUDGET_ORIGINAL_AMOUNT/);
  assert.throws(() => buildBudgetChangePayload({ changeId: "BC-1", amount: "0.00", reason: "Zero" }), /INVALID_BUDGET_CHANGE_AMOUNT/);
  assert.throws(() => buildBudgetChangePayload({ changeId: "BC-1", amount: "1e3", reason: "Exponent" }), /INVALID_BUDGET_CHANGE_AMOUNT/);
  assert.throws(() => buildFundingPayload({
    fundingId: "FS-1",
    name: "Barter",
    sourceType: "barter",
    currency: "USD",
    amount: "1.00",
    periodId: "",
  }), /INVALID_BUDGET_FUNDING_TYPE/);
});

test("money text accepts only plain two-decimal values", () => {
  assert.equal(isMoneyText("1000", { allowZero: true }), true);
  assert.equal(isMoneyText("1000.50", { allowZero: true }), true);
  assert.equal(isMoneyText("-12.30", { allowNegative: true }), true);
  assert.equal(isMoneyText("10.5", { allowZero: true }), false);
  assert.equal(isMoneyText("10.505", { allowZero: true }), false);
  assert.equal(isMoneyText("1e3", { allowZero: true }), false);
  assert.equal(isMoneyText("0.00"), false);
});

test("reads use project-scoped budget paths with query filters", async () => {
  const log = calls();
  const list = transportWith({ ok: true, data: { contract_version: BUDGET_API_VERSION, budget_lines: [LINE] } }, log);
  assert.deepEqual(await loadBudgetLines(list, CONTEXT, { currency: "USD", search: "concrete" }), {
    ok: true,
    data: [{
      budgetLineId: "BL-1",
      description: "Concrete works",
      currency: "USD",
      originalAmount: "1000.00",
      costAccountId: "CA-1",
      periodId: "2026",
      revision: 2,
    }],
  });
  assert.deepEqual(log.gets, ["/api/projects/project-1/budget/lines?currency=USD&search=concrete"]);

  const empty = (key: string) => {
    const endpointLog = calls();
    const endpointTransport = transportWith({
      ok: true,
      data: { contract_version: BUDGET_API_VERSION, [key]: [] },
    }, endpointLog);
    return { endpointLog, endpointTransport };
  };
  const changes = empty("changes");
  assert.equal((await loadBudgetChanges(changes.endpointTransport, CONTEXT, "BL-1")).ok, true);
  const history = empty("events");
  assert.equal((await loadBudgetHistory(history.endpointTransport, CONTEXT, "BL-1")).ok, true);
  const funding = empty("funding_sources");
  assert.equal((await loadFundingSources(funding.endpointTransport, CONTEXT)).ok, true);
  const summary = empty("currencies");
  assert.equal((await loadBudgetSummary(summary.endpointTransport, CONTEXT)).ok, true);
  assert.deepEqual(changes.endpointLog.gets, [
    "/api/projects/project-1/budget/lines/BL-1/changes",
  ]);
  assert.deepEqual(history.endpointLog.gets, [
    "/api/projects/project-1/budget/lines/BL-1/history",
  ]);
  assert.deepEqual(funding.endpointLog.gets, ["/api/projects/project-1/budget/funding"]);
  assert.deepEqual(summary.endpointLog.gets, ["/api/projects/project-1/budget/summary"]);
});

test("transport failures and malformed envelopes stay explicit", async () => {
  const log = calls();
  const denied = transportWith({
    ok: false,
    error: { code: "BUDGET_PERMISSION_DENIED", retryable: false, message_key: "error.authorization.denied", available_actions: [] },
  }, log);
  const result = await loadBudgetLines(denied, CONTEXT);
  assert.equal(result.ok, false);
  if (result.ok) return;
  assert.equal(result.error.code, "BUDGET_PERMISSION_DENIED");

  const malformed = transportWith({
    ok: true,
    data: { contract_version: "1.0", budget_lines: [LINE] },
  }, log);
  const invalid = await loadBudgetLines(malformed, CONTEXT);
  assert.equal(invalid.ok, false);
  if (!invalid.ok) assert.equal(invalid.error.code, "INVALID_BUDGET_LINE_LIST");
});

test("writes carry expected revisions and idempotency keys", async () => {
  const lineLog = calls();
  const lineTransport = transportWith({ ok: true, data: LINE }, lineLog);
  const created = await createBudgetLine(lineTransport, CONTEXT, {
    budgetLineId: "BL-1",
    description: "Concrete works",
    currency: "USD",
    originalAmount: "1000.00",
    costAccountId: "CA-1",
    periodId: "2026",
  }, "idem-line-1");
  assert.equal(created.ok, true);
  assert.equal(lineLog.posts[0].path, "/api/projects/project-1/budget/lines");
  assert.equal(lineLog.posts[0].idempotencyKey, "idem-line-1");

  assert.equal((await updateBudgetLine(lineTransport, CONTEXT, {
    budgetLineId: "BL-1",
    description: "Concrete works revised",
    currency: "USD",
    originalAmount: "1000.00",
    costAccountId: "CA-1",
    periodId: "2026",
  }, 2)).ok, true);
  assert.equal(lineLog.patches[0].path, "/api/projects/project-1/budget/lines/BL-1");
  assert.equal((lineLog.patches[0].request as Record<string, unknown>).expected_revision, 2);

  const changeLog = calls();
  const changeTransport = transportWith({ ok: true, data: CHANGE }, changeLog);
  assert.equal((await createBudgetChange(changeTransport, CONTEXT, "BL-1", {
    changeId: "BC-1", amount: "-100.00", reason: "Reduced scope",
  })).ok, true);
  assert.equal(changeLog.posts[0].path, "/api/projects/project-1/budget/lines/BL-1/changes");

  assert.equal((await transitionBudgetChange(changeTransport, CONTEXT, "BC-1", "approved", 1)).ok, true);
  assert.equal(changeLog.posts[1].path, "/api/projects/project-1/budget/changes/BC-1/status");
  assert.equal((changeLog.posts[1].request as Record<string, unknown>).expected_revision, 1);

  const fundingLog = calls();
  const fundingTransport = transportWith({ ok: true, data: FUNDING }, fundingLog);
  assert.equal((await createFundingSource(fundingTransport, CONTEXT, {
    fundingId: "FS-1", name: "Owner equity", sourceType: "internal", currency: "USD", amount: "400.00", periodId: "",
  }, "idem-funding-1")).ok, true);
  assert.equal(fundingLog.posts[0].path, "/api/projects/project-1/budget/funding");
  assert.equal((await updateFundingSource(fundingTransport, CONTEXT, {
    fundingId: "FS-1", name: "Owner equity", sourceType: "internal", currency: "USD", amount: "450.00", periodId: "",
  }, 1)).ok, true);
  assert.equal(fundingLog.patches[0].path, "/api/projects/project-1/budget/funding/FS-1");
});
