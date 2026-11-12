import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  COST_API_VERSION,
  buildCostAccountPayload,
  buildExpensePayload,
  copyCostAccount,
  deleteCostAccount,
  deleteExpense,
  loadCostAccounts,
  loadExpenses,
  saveCostAccount,
  saveExpense,
  setDefaultCostAccount,
} from "./workspace-expenses.js";

const CONTEXT: ProjectContext = { tenant_id: "t1", project_id: "project-1", revision: 4 };

const EXPENSE = {
  contract_version: COST_API_VERSION,
  expense_id: "EXP-100",
  name: "Concrete pump rental",
  category: "equipment",
  currency: "USD",
  activity_id: "A120",
  wbs_id: "WBS-2",
  cost_account_id: "CA-CIVIL",
  expense_date: "2026-10-01",
  accrual_date: "2026-09-30",
  planned_amount: "1250.50",
  actual_amount: null,
  remaining_amount: "1250.50",
  note: null,
  revision: 3,
};

const ACCOUNT = {
  contract_version: COST_API_VERSION,
  account_id: "CA-CIVIL",
  name: "Civil works",
  parent_account_id: null,
  description: "Civil cost account",
  is_default: true,
  revision: 2,
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

function listEnvelope(key: "expenses" | "cost_accounts", items: readonly unknown[]) {
  return { contract_version: COST_API_VERSION, [key]: items };
}

function expenseInput(overrides: Record<string, unknown> = {}) {
  return {
    expenseId: "EXP-100",
    name: "Concrete pump rental",
    category: "equipment",
    activityId: "A120",
    wbsId: null,
    costAccountId: "CA-CIVIL",
    expenseDate: "2026-10-01",
    accrualDate: "2026-09-30",
    plannedCost: "1250.50",
    actualCost: null,
    remainingCost: "1250.50",
    currency: "USD",
    note: null,
    ...overrides,
  };
}

function accountInput(overrides: Record<string, unknown> = {}) {
  return {
    accountId: "CA-CIVIL",
    name: "Civil works",
    parentAccountId: null,
    description: "Civil cost account",
    isDefault: true,
    ...overrides,
  };
}

test("expense list reads the p6-cost-api contract and preserves stored fields", async () => {
  const log = calls();
  const result = await loadExpenses(
    transportWith({ ok: true, data: listEnvelope("expenses", [EXPENSE]) }, log),
    CONTEXT,
  );
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.deepEqual(result.data, [{
    expenseId: "EXP-100",
    name: "Concrete pump rental",
    category: "equipment",
    activityId: "A120",
    wbsId: "WBS-2",
    costAccountId: "CA-CIVIL",
    expenseDate: "2026-10-01",
    accrualDate: "2026-09-30",
    plannedCost: "1250.50",
    actualCost: null,
    remainingCost: "1250.50",
    currency: "USD",
    note: null,
    revision: 3,
  }]);
  assert.deepEqual(log.gets, ["/api/projects/project-1/cost/expenses"]);
});

test("expense list carries register filters on the cost path", async () => {
  const log = calls();
  await loadExpenses(transportWith({ ok: true, data: listEnvelope("expenses", []) }, log), CONTEXT, {
    category: "labor",
    costAccountId: "CA-CIVIL",
    activityId: "A120",
    search: "pump",
  });
  assert.deepEqual(log.gets, [
    "/api/projects/project-1/cost/expenses?category=labor&cost_account_id=CA-CIVIL&activity_id=A120&search=pump",
  ]);
});

test("expense list fails closed on a foreign contract or malformed row", async () => {
  const wrongContract = await loadExpenses(
    transportWith({ ok: true, data: { contract_version: "p6-expense-api.v1", expenses: [EXPENSE] } }),
    CONTEXT,
  );
  assert.equal(wrongContract.ok, false);
  if (!wrongContract.ok) assert.equal(wrongContract.error.code, "INVALID_EXPENSE_LIST");

  const cases: [Record<string, unknown>, string][] = [
    [{ name: "" }, "INVALID_EXPENSE_RECORD"],
    [{ category: "Equipment" }, "INVALID_EXPENSE_RECORD"],
    [{ currency: "usd" }, "INVALID_EXPENSE_RECORD"],
    [{ planned_amount: "12,50" }, "INVALID_EXPENSE_RECORD"],
    [{ planned_amount: 12.5 }, "INVALID_EXPENSE_RECORD"],
    [{ revision: 0 }, "INVALID_EXPENSE_RECORD"],
    [{ revision: "3" }, "INVALID_EXPENSE_RECORD"],
  ];
  for (const [override, code] of cases) {
    const result = await loadExpenses(
      transportWith({ ok: true, data: listEnvelope("expenses", [{ ...EXPENSE, ...override }]) }),
      CONTEXT,
    );
    assert.equal(result.ok, false, `override ${JSON.stringify(override)} should fail`);
    if (!result.ok) assert.equal(result.error.code, code);
  }
});

test("expense create posts trimmed identity, references and decimal text", async () => {
  const log = calls();
  const result = await saveExpense(transportWith({ ok: true, data: EXPENSE }, log), CONTEXT, {
    expenseId: "  EXP-100 ",
    name: " Concrete pump rental ",
    category: " equipment ",
    activityId: " A120 ",
    wbsId: "  ",
    costAccountId: " CA-CIVIL ",
    expenseDate: "2026-10-01",
    accrualDate: "2026-09-30",
    plannedCost: " 1250.50 ",
    actualCost: null,
    remainingCost: "1250.50",
    currency: " USD ",
    note: null,
  });
  assert.equal(result.ok, true);
  assert.equal(log.posts.length, 1);
  assert.equal(log.posts[0].path, "/api/projects/project-1/cost/expenses");
  assert.deepEqual(log.posts[0].request, {
    expense_id: "EXP-100",
    name: "Concrete pump rental",
    category: "equipment",
    currency: "USD",
    activity_id: "A120",
    wbs_id: null,
    cost_account_id: "CA-CIVIL",
    expense_date: "2026-10-01",
    accrual_date: "2026-09-30",
    planned_amount: "1250.50",
    actual_amount: null,
    remaining_amount: "1250.50",
    note: null,
  });
  assert.equal(typeof log.posts[0].idempotencyKey, "string");
  assert.equal(log.patches.length, 0);
});

test("expense edit patches the record with the expected revision", async () => {
  const log = calls();
  const result = await saveExpense(
    transportWith({ ok: true, data: { ...EXPENSE, revision: 4 } }, log),
    CONTEXT,
    expenseInput({ name: "Pump rental" }),
    3,
  );
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.equal(result.data.revision, 4);
  assert.equal(log.patches.length, 1);
  assert.equal(log.patches[0].path, "/api/projects/project-1/cost/expenses/EXP-100");
  assert.deepEqual(log.patches[0].request, {
    expense_id: "EXP-100",
    name: "Pump rental",
    category: "equipment",
    currency: "USD",
    activity_id: "A120",
    wbs_id: null,
    cost_account_id: "CA-CIVIL",
    expense_date: "2026-10-01",
    accrual_date: "2026-09-30",
    planned_amount: "1250.50",
    actual_amount: null,
    remaining_amount: "1250.50",
    note: null,
    expected_revision: 3,
  });
});

test("expense create rejects invalid identity, category, currency and decimals without a write", async () => {
  const log = calls();
  const transport = transportWith({ ok: true, data: EXPENSE }, log);

  const missing = await saveExpense(transport, CONTEXT, expenseInput({ expenseId: " " }));
  assert.equal(missing.ok, false);
  if (!missing.ok) assert.equal(missing.error.code, "EXPENSE_FIELDS_REQUIRED");

  const category = await saveExpense(transport, CONTEXT, expenseInput({ category: "Equipment" }));
  assert.equal(category.ok, false);
  if (!category.ok) assert.equal(category.error.code, "INVALID_EXPENSE_CATEGORY");

  const currency = await saveExpense(transport, CONTEXT, expenseInput({ currency: "US" }));
  assert.equal(currency.ok, false);
  if (!currency.ok) assert.equal(currency.error.code, "INVALID_EXPENSE_CURRENCY");

  const badNumber = await saveExpense(transport, CONTEXT, expenseInput({ plannedCost: "1.2.3" }));
  assert.equal(badNumber.ok, false);
  if (!badNumber.ok) assert.equal(badNumber.error.code, "INVALID_EXPENSE_NUMBER");

  assert.throws(() => buildExpensePayload(expenseInput({ plannedCost: "not-a-number" })), /INVALID_EXPENSE_NUMBER/);
  assert.equal(log.posts.length, 0);
  assert.equal(log.patches.length, 0);
});

test("expense delete sends the expected revision", async () => {
  const log = calls();
  const result = await deleteExpense(
    transportWith({ ok: true, data: { deleted: true } }, log),
    CONTEXT,
    "EXP-100",
    3,
  );
  assert.equal(result.ok, true);
  assert.deepEqual(log.deletes, [{
    path: "/api/projects/project-1/cost/expenses/EXP-100",
    request: { expected_revision: 3 },
  }]);
});

test("cost account list reads the p6-cost-api contract", async () => {
  const log = calls();
  const result = await loadCostAccounts(
    transportWith({ ok: true, data: listEnvelope("cost_accounts", [ACCOUNT]) }, log),
    CONTEXT,
  );
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.deepEqual(result.data, [{
    accountId: "CA-CIVIL",
    name: "Civil works",
    parentAccountId: null,
    description: "Civil cost account",
    isDefault: true,
    revision: 2,
  }]);
  assert.deepEqual(log.gets, ["/api/projects/project-1/cost/accounts"]);

  const foreign = await loadCostAccounts(
    transportWith({ ok: true, data: listEnvelope("cost_accounts", [{ ...ACCOUNT, contract_version: "p6-cost-account-api.v1" }]) }),
    CONTEXT,
  );
  assert.equal(foreign.ok, false);
  if (!foreign.ok) assert.equal(foreign.error.code, "INVALID_COST_ACCOUNT_RESPONSE");

  const missingDefault = await loadCostAccounts(
    transportWith({ ok: true, data: listEnvelope("cost_accounts", [{ ...ACCOUNT, is_default: undefined }]) }),
    CONTEXT,
  );
  assert.equal(missingDefault.ok, false);
  if (!missingDefault.ok) assert.equal(missingDefault.error.code, "INVALID_COST_ACCOUNT_RECORD");
});

test("cost account create trims identity and carries the default flag", async () => {
  const log = calls();
  const result = await saveCostAccount(transportWith({ ok: true, data: ACCOUNT }, log), CONTEXT, {
    accountId: " CA-CIVIL ",
    name: " Civil works ",
    parentAccountId: "  ",
    description: " Civil cost account ",
    isDefault: true,
  });
  assert.equal(result.ok, true);
  assert.equal(log.posts.length, 1);
  assert.equal(log.posts[0].path, "/api/projects/project-1/cost/accounts");
  assert.deepEqual(log.posts[0].request, {
    account_id: "CA-CIVIL",
    name: "Civil works",
    parent_account_id: null,
    description: "Civil cost account",
    is_default: true,
  });
});

test("cost account edit patches with the expected revision", async () => {
  const log = calls();
  const result = await saveCostAccount(
    transportWith({ ok: true, data: { ...ACCOUNT, revision: 3 } }, log),
    CONTEXT,
    accountInput({ name: "Civil and earthworks" }),
    2,
  );
  assert.equal(result.ok, true);
  assert.equal(log.patches.length, 1);
  assert.equal(log.patches[0].path, "/api/projects/project-1/cost/accounts/CA-CIVIL");
  assert.deepEqual(log.patches[0].request, {
    account_id: "CA-CIVIL",
    name: "Civil and earthworks",
    parent_account_id: null,
    description: "Civil cost account",
    is_default: true,
    expected_revision: 2,
  });
});

test("cost account create refuses a self-parent and missing identity without a write", async () => {
  assert.throws(
    () => buildCostAccountPayload(accountInput({ parentAccountId: "CA-CIVIL" })),
    /SELF_PARENT_ACCOUNT/,
  );
  const log = calls();
  const transport = transportWith({ ok: true, data: ACCOUNT }, log);
  const missing = await saveCostAccount(transport, CONTEXT, accountInput({ accountId: " " }));
  assert.equal(missing.ok, false);
  if (!missing.ok) assert.equal(missing.error.code, "COST_ACCOUNT_FIELDS_REQUIRED");
  assert.equal(log.posts.length, 0);
});

test("cost account copy and default route through their actions", async () => {
  const log = calls();
  const copy = await copyCostAccount(
    transportWith({ ok: true, data: { ...ACCOUNT, account_id: "CA-CIVIL-2", is_default: false, revision: 1 } }, log),
    CONTEXT,
    "CA-CIVIL",
    "CA-CIVIL-2",
    "Civil works copy",
  );
  assert.equal(copy.ok, true);
  if (!copy.ok) return;
  assert.equal(copy.data.accountId, "CA-CIVIL-2");
  assert.equal(copy.data.isDefault, false);
  assert.equal(log.posts[0].path, "/api/projects/project-1/cost/accounts/CA-CIVIL/copy");
  assert.deepEqual(log.posts[0].request, { account_id: "CA-CIVIL-2", name: "Civil works copy" });

  const defaulted = await setDefaultCostAccount(
    transportWith({ ok: true, data: listEnvelope("cost_accounts", [{ ...ACCOUNT, is_default: false }]) }, log),
    CONTEXT,
    "CA-CIVIL",
    2,
  );
  assert.equal(defaulted.ok, true);
  assert.equal(log.posts[1].path, "/api/projects/project-1/cost/accounts/CA-CIVIL/default");
  assert.deepEqual(log.posts[1].request, { expected_revision: 2 });
});

test("cost account delete sends the expected revision", async () => {
  const log = calls();
  const result = await deleteCostAccount(
    transportWith({ ok: true, data: { deleted: true } }, log),
    CONTEXT,
    "CA-CIVIL",
    2,
  );
  assert.equal(result.ok, true);
  assert.deepEqual(log.deletes, [{
    path: "/api/projects/project-1/cost/accounts/CA-CIVIL",
    request: { expected_revision: 2 },
  }]);
});
