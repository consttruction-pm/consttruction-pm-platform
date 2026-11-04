import assert from "node:assert/strict";
import test from "node:test";

import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import {
  buildCostAccountPayload,
  buildExpensePayload,
  loadCostAccounts,
  loadExpenses,
  saveCostAccount,
  saveExpense,
} from "./workspace-expenses.js";

const CONTEXT: ProjectContext = { tenant_id: "t1", project_id: "project-1", revision: 4 };

const EXPENSE = {
  expense_id: "EXP-100",
  name: "Concrete pump rental",
  category: "Equipment",
  activity_id: "A120",
  wbs_id: "WBS-2",
  expense_date: "2026-10-01",
  planned_cost: "1250.50",
  actual_cost: null,
  remaining_cost: "1250.50",
  currency: "USD",
  note: null,
};

const ACCOUNT = {
  account_id: "CA-CIVIL",
  name: "Civil works",
  parent_account_id: null,
  description: "Civil cost account",
};

function expenseEnvelope(expense: unknown = EXPENSE) {
  return {
    contract_version: "p6-expense-api.v1",
    kind: "p6_expense",
    scope: { tenant_id: "t1", project_id: "project-1", project_revision: 4 },
    expense,
  };
}

function accountEnvelope(account: unknown = ACCOUNT) {
  return {
    contract_version: "p6-cost-account-api.v1",
    kind: "p6_cost_account",
    scope: { tenant_id: "t1", project_id: "project-1", project_revision: 4 },
    cost_account: account,
  };
}

type Calls = {
  gets: { path: string }[];
  posts: { path: string; request: unknown; idempotencyKey?: string }[];
};

function transportWith(
  result: ApiResult<unknown>,
  calls: Calls = { gets: [], posts: [] },
): ApiTransport {
  return {
    async get(path) {
      calls.gets.push({ path });
      return result as ApiResult<never>;
    },
    async post(path, request, _context, idempotencyKey) {
      calls.posts.push({ path, request, idempotencyKey });
      return result as ApiResult<never>;
    },
  };
}

test("expense list reads the p6-expense-api contract and preserves stored fields", async () => {
  const calls: Calls = { gets: [], posts: [] };
  const result = await loadExpenses(
    transportWith({ ok: true, data: { contract_version: "p6-expense-api.v1", expenses: [expenseEnvelope()] } }, calls),
    CONTEXT,
  );
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.deepEqual(result.data, [{
    expenseId: "EXP-100",
    name: "Concrete pump rental",
    category: "Equipment",
    activityId: "A120",
    wbsId: "WBS-2",
    expenseDate: "2026-10-01",
    plannedCost: "1250.50",
    actualCost: null,
    remainingCost: "1250.50",
    currency: "USD",
    note: null,
  }]);
  assert.deepEqual(calls.gets, [{ path: "/api/projects/project-1/p6/expenses" }]);
});

test("expense list fails closed on a foreign contract or malformed row", async () => {
  const wrongContract = await loadExpenses(
    transportWith({ ok: true, data: { contract_version: "other", expenses: [expenseEnvelope()] } }),
    CONTEXT,
  );
  assert.equal(wrongContract.ok, false);
  if (!wrongContract.ok) assert.equal(wrongContract.error.code, "INVALID_EXPENSE_LIST");

  const missingName = await loadExpenses(
    transportWith({ ok: true, data: { contract_version: "p6-expense-api.v1", expenses: [expenseEnvelope({ ...EXPENSE, name: "" })] } }),
    CONTEXT,
  );
  assert.equal(missingName.ok, false);
  if (!missingName.ok) assert.equal(missingName.error.code, "INVALID_EXPENSE_RECORD");

  const badMoney = await loadExpenses(
    transportWith({ ok: true, data: { contract_version: "p6-expense-api.v1", expenses: [expenseEnvelope({ ...EXPENSE, planned_cost: "12,50" })] } }),
    CONTEXT,
  );
  assert.equal(badMoney.ok, false);
  if (!badMoney.ok) assert.equal(badMoney.error.code, "INVALID_EXPENSE_RECORD");
});

test("expense create posts trimmed identity, references and decimal text", async () => {
  const calls: Calls = { gets: [], posts: [] };
  const result = await saveExpense(
    transportWith({ ok: true, data: expenseEnvelope() }, calls),
    CONTEXT,
    {
      expenseId: "  EXP-100 ",
      name: " Concrete pump rental ",
      category: " Equipment ",
      activityId: " A120 ",
      wbsId: "  ",
      expenseDate: "2026-10-01",
      plannedCost: " 1250.50 ",
      actualCost: null,
      remainingCost: "1250.50",
      currency: " USD ",
      note: null,
    },
  );
  assert.equal(result.ok, true);
  assert.deepEqual(calls.posts, [{
    path: "/api/projects/project-1/p6/expenses",
    request: {
      contract_version: "p6-expense-api.v1",
      expense_id: "EXP-100",
      name: "Concrete pump rental",
      category: "Equipment",
      activity_id: "A120",
      wbs_id: null,
      expense_date: "2026-10-01",
      planned_cost: "1250.50",
      actual_cost: null,
      remaining_cost: "1250.50",
      currency: "USD",
      note: null,
    },
    idempotencyKey: calls.posts[0].idempotencyKey,
  }]);
  assert.equal(typeof calls.posts[0].idempotencyKey, "string");
});

test("expense create rejects missing fields and malformed decimals without a write", async () => {
  const calls: Calls = { gets: [], posts: [] };
  const missing = await saveExpense(transportWith({ ok: true, data: expenseEnvelope() }, calls), CONTEXT, {
    expenseId: "",
    name: "Pump",
    category: "Equipment",
    activityId: null,
    wbsId: null,
    expenseDate: null,
    plannedCost: null,
    actualCost: null,
    remainingCost: null,
    currency: null,
    note: null,
  });
  assert.equal(missing.ok, false);
  if (!missing.ok) assert.equal(missing.error.code, "EXPENSE_FIELDS_REQUIRED");

  assert.throws(
    () => buildExpensePayload({
      expenseId: "EXP-200",
      name: "Pump",
      category: "Equipment",
      activityId: null,
      wbsId: null,
      expenseDate: null,
      plannedCost: "not-a-number",
      actualCost: null,
      remainingCost: null,
      currency: null,
      note: null,
    }),
    /INVALID_EXPENSE_NUMBER/,
  );
  const badNumber = await saveExpense(transportWith({ ok: true, data: expenseEnvelope() }, calls), CONTEXT, {
    expenseId: "EXP-200",
    name: "Pump",
    category: "Equipment",
    activityId: null,
    wbsId: null,
    expenseDate: null,
    plannedCost: "1.2.3",
    actualCost: null,
    remainingCost: null,
    currency: null,
    note: null,
  });
  assert.equal(badNumber.ok, false);
  if (!badNumber.ok) assert.equal(badNumber.error.code, "INVALID_EXPENSE_NUMBER");
  assert.equal(calls.posts.length, 0);
});

test("cost account list reads the p6-cost-account-api contract", async () => {
  const calls: Calls = { gets: [], posts: [] };
  const result = await loadCostAccounts(
    transportWith({ ok: true, data: { contract_version: "p6-cost-account-api.v1", cost_accounts: [accountEnvelope()] } }, calls),
    CONTEXT,
  );
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.deepEqual(result.data, [{
    accountId: "CA-CIVIL",
    name: "Civil works",
    parentAccountId: null,
    description: "Civil cost account",
  }]);
  assert.deepEqual(calls.gets, [{ path: "/api/projects/project-1/p6/cost-accounts" }]);

  const foreign = await loadCostAccounts(
    transportWith({ ok: true, data: { contract_version: "p6-expense-api.v1", cost_accounts: [accountEnvelope()] } }),
    CONTEXT,
  );
  assert.equal(foreign.ok, false);
  if (!foreign.ok) assert.equal(foreign.error.code, "INVALID_COST_ACCOUNT_LIST");
});

test("cost account create trims identity and nulls empty parent/description", async () => {
  const calls: Calls = { gets: [], posts: [] };
  const result = await saveCostAccount(
    transportWith({ ok: true, data: accountEnvelope() }, calls),
    CONTEXT,
    { accountId: " CA-CIVIL ", name: " Civil works ", parentAccountId: "  ", description: " Civil cost account " },
  );
  assert.equal(result.ok, true);
  assert.deepEqual(calls.posts, [{
    path: "/api/projects/project-1/p6/cost-accounts",
    request: {
      contract_version: "p6-cost-account-api.v1",
      account_id: "CA-CIVIL",
      name: "Civil works",
      parent_account_id: null,
      description: "Civil cost account",
    },
    idempotencyKey: calls.posts[0].idempotencyKey,
  }]);
});

test("cost account create refuses a self-parent and missing identity without a write", async () => {
  assert.throws(
    () => buildCostAccountPayload({ accountId: "CA-CIVIL", name: "Civil", parentAccountId: "CA-CIVIL", description: null }),
    /SELF_PARENT_ACCOUNT/,
  );
  const calls: Calls = { gets: [], posts: [] };
  const missing = await saveCostAccount(
    transportWith({ ok: true, data: accountEnvelope() }, calls),
    CONTEXT,
    { accountId: " ", name: "Civil", parentAccountId: null, description: null },
  );
  assert.equal(missing.ok, false);
  if (!missing.ok) assert.equal(missing.error.code, "COST_ACCOUNT_FIELDS_REQUIRED");
  assert.equal(calls.posts.length, 0);
});
