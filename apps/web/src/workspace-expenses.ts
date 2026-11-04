import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

export const EXPENSE_API_VERSION = "p6-expense-api.v1";
export const COST_ACCOUNT_API_VERSION = "p6-cost-account-api.v1";

export type ExpenseRecord = {
  expenseId: string;
  name: string;
  category: string;
  activityId: string | null;
  wbsId: string | null;
  expenseDate: string | null;
  plannedCost: string | null;
  actualCost: string | null;
  remainingCost: string | null;
  currency: string | null;
  note: string | null;
};

export type CostAccountRecord = {
  accountId: string;
  name: string;
  parentAccountId: string | null;
  description: string | null;
};

export type ExpenseInput = {
  expenseId: string;
  name: string;
  category: string;
  activityId: string | null;
  wbsId: string | null;
  expenseDate: string | null;
  plannedCost: string | null;
  actualCost: string | null;
  remainingCost: string | null;
  currency: string | null;
  note: string | null;
};

export type CostAccountInput = {
  accountId: string;
  name: string;
  parentAccountId: string | null;
  description: string | null;
};

export type ExpenseActivityOption = {
  id: string;
  code: string;
  name: string;
};

export type ExpenseWbsOption = {
  id: string;
  code: string;
  name: string;
};

export type ExpensePageOptions = {
  transport: ApiTransport;
  context: ProjectContext;
  locale: string;
  activities: readonly ExpenseActivityOption[];
  wbsNodes: readonly ExpenseWbsOption[];
};

function text(locale: string, en: string, fa: string): string {
  return locale.split("-")[0] === "fa" ? fa : en;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function localError(code: string): ApiResult<never> {
  return {
    ok: false,
    error: { code, retryable: false, message_key: "error.request.invalid", available_actions: [] },
  };
}

function optionalText(value: unknown, code: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string") throw new Error(code);
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function decimalText(value: unknown, code: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string" && typeof value !== "number") throw new Error(code);
  const trimmed = String(value).trim();
  if (!trimmed) return null;
  if (!/^-?\d+(\.\d+)?$/.test(trimmed)) throw new Error(code);
  return trimmed;
}

function expensePath(context: ProjectContext, expenseId?: string): string {
  const base = `/api/projects/${encodeURIComponent(context.project_id)}/p6/expenses`;
  return expenseId ? `${base}/${encodeURIComponent(expenseId)}` : base;
}

function costAccountPath(context: ProjectContext): string {
  return `/api/projects/${encodeURIComponent(context.project_id)}/p6/cost-accounts`;
}

export function parseExpense(value: unknown): ExpenseRecord {
  if (!isRecord(value)) throw new Error("INVALID_EXPENSE_RECORD");
  if (value.contract_version !== EXPENSE_API_VERSION) throw new Error("INVALID_EXPENSE_RESPONSE");
  if (value.kind !== "p6_expense") throw new Error("INVALID_EXPENSE_RESPONSE");
  const payload = value.expense;
  if (!isRecord(payload)) throw new Error("INVALID_EXPENSE_RESPONSE");
  const { expense_id, name, category } = payload;
  if (
    typeof expense_id !== "string" || !expense_id.trim() ||
    typeof name !== "string" || !name.trim() ||
    typeof category !== "string" || !category.trim()
  ) {
    throw new Error("INVALID_EXPENSE_RECORD");
  }
  return {
    expenseId: expense_id,
    name,
    category,
    activityId: optionalText(payload.activity_id, "INVALID_EXPENSE_RECORD"),
    wbsId: optionalText(payload.wbs_id, "INVALID_EXPENSE_RECORD"),
    expenseDate: optionalText(payload.expense_date, "INVALID_EXPENSE_RECORD"),
    plannedCost: decimalText(payload.planned_cost, "INVALID_EXPENSE_RECORD"),
    actualCost: decimalText(payload.actual_cost, "INVALID_EXPENSE_RECORD"),
    remainingCost: decimalText(payload.remaining_cost, "INVALID_EXPENSE_RECORD"),
    currency: optionalText(payload.currency, "INVALID_EXPENSE_RECORD"),
    note: optionalText(payload.note, "INVALID_EXPENSE_RECORD"),
  };
}

export function parseCostAccount(value: unknown): CostAccountRecord {
  if (!isRecord(value)) throw new Error("INVALID_COST_ACCOUNT_RECORD");
  if (value.contract_version !== COST_ACCOUNT_API_VERSION) {
    throw new Error("INVALID_COST_ACCOUNT_RESPONSE");
  }
  if (value.kind !== "p6_cost_account") throw new Error("INVALID_COST_ACCOUNT_RESPONSE");
  const payload = value.cost_account;
  if (!isRecord(payload)) throw new Error("INVALID_COST_ACCOUNT_RESPONSE");
  const { account_id, name } = payload;
  if (
    typeof account_id !== "string" || !account_id.trim() ||
    typeof name !== "string" || !name.trim()
  ) {
    throw new Error("INVALID_COST_ACCOUNT_RECORD");
  }
  return {
    accountId: account_id,
    name,
    parentAccountId: optionalText(payload.parent_account_id, "INVALID_COST_ACCOUNT_RECORD"),
    description: optionalText(payload.description, "INVALID_COST_ACCOUNT_RECORD"),
  };
}

export async function loadExpenses(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<readonly ExpenseRecord[]>> {
  const result = await transport.get<unknown>(expensePath(context), context);
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || payload.contract_version !== EXPENSE_API_VERSION || !Array.isArray(payload.expenses)) {
    return localError("INVALID_EXPENSE_LIST");
  }
  try {
    return { ok: true, data: payload.expenses.map((item) => parseExpense(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_EXPENSE_LIST");
  }
}

export async function loadCostAccounts(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<readonly CostAccountRecord[]>> {
  const result = await transport.get<unknown>(costAccountPath(context), context);
  if (!result.ok) return result;
  const payload = result.data;
  if (
    !isRecord(payload) ||
    payload.contract_version !== COST_ACCOUNT_API_VERSION ||
    !Array.isArray(payload.cost_accounts)
  ) {
    return localError("INVALID_COST_ACCOUNT_LIST");
  }
  try {
    return { ok: true, data: payload.cost_accounts.map((item) => parseCostAccount(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_COST_ACCOUNT_LIST");
  }
}

function normalizedDecimal(raw: string | null, code: string): string | null {
  const trimmed = (raw ?? "").trim();
  if (!trimmed) return null;
  if (!/^-?\d+(\.\d+)?$/.test(trimmed)) throw new Error(code);
  return trimmed;
}

function trimmedOrNull(value: string | null): string | null {
  const trimmed = (value ?? "").trim();
  return trimmed ? trimmed : null;
}

export function buildExpensePayload(input: ExpenseInput): Record<string, unknown> {
  if (!input.expenseId.trim() || !input.name.trim() || !input.category.trim()) {
    throw new Error("EXPENSE_FIELDS_REQUIRED");
  }
  return {
    contract_version: EXPENSE_API_VERSION,
    expense_id: input.expenseId.trim(),
    name: input.name.trim(),
    category: input.category.trim(),
    activity_id: trimmedOrNull(input.activityId),
    wbs_id: trimmedOrNull(input.wbsId),
    expense_date: trimmedOrNull(input.expenseDate),
    planned_cost: normalizedDecimal(input.plannedCost, "INVALID_EXPENSE_NUMBER"),
    actual_cost: normalizedDecimal(input.actualCost, "INVALID_EXPENSE_NUMBER"),
    remaining_cost: normalizedDecimal(input.remainingCost, "INVALID_EXPENSE_NUMBER"),
    currency: trimmedOrNull(input.currency),
    note: trimmedOrNull(input.note),
  };
}

export function buildCostAccountPayload(input: CostAccountInput): Record<string, unknown> {
  if (!input.accountId.trim() || !input.name.trim()) {
    throw new Error("COST_ACCOUNT_FIELDS_REQUIRED");
  }
  const parent = trimmedOrNull(input.parentAccountId);
  if (parent === input.accountId.trim()) throw new Error("SELF_PARENT_ACCOUNT");
  return {
    contract_version: COST_ACCOUNT_API_VERSION,
    account_id: input.accountId.trim(),
    name: input.name.trim(),
    parent_account_id: parent,
    description: trimmedOrNull(input.description),
  };
}

export async function saveExpense(
  transport: ApiTransport,
  context: ProjectContext,
  input: ExpenseInput,
): Promise<ApiResult<ExpenseRecord>> {
  let payload: Record<string, unknown>;
  try {
    payload = buildExpensePayload(input);
  } catch (error) {
    return localError(error instanceof Error ? error.message : "EXPENSE_FIELDS_REQUIRED");
  }
  const result = await transport.post<Record<string, unknown>, unknown>(
    expensePath(context),
    payload,
    context,
    crypto.randomUUID(),
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseExpense(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_EXPENSE_RESPONSE");
  }
}

export async function saveCostAccount(
  transport: ApiTransport,
  context: ProjectContext,
  input: CostAccountInput,
): Promise<ApiResult<CostAccountRecord>> {
  let payload: Record<string, unknown>;
  try {
    payload = buildCostAccountPayload(input);
  } catch (error) {
    return localError(error instanceof Error ? error.message : "COST_ACCOUNT_FIELDS_REQUIRED");
  }
  const result = await transport.post<Record<string, unknown>, unknown>(
    costAccountPath(context),
    payload,
    context,
    crypto.randomUUID(),
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseCostAccount(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_COST_ACCOUNT_RESPONSE");
  }
}

type PageState = {
  status: "loading" | "loaded" | "error";
  errorCode: string | null;
  expenses: readonly ExpenseRecord[];
  selectedExpenseId: string | null;
  expenseMode: "browse" | "create";
  expenseDraft: ExpenseInput;
  accountsStatus: "loading" | "loaded" | "error";
  accountsErrorCode: string | null;
  accounts: readonly CostAccountRecord[];
  selectedAccountId: string | null;
  accountMode: "browse" | "create";
  accountDraft: CostAccountInput;
  busy: boolean;
  notice: { kind: "ok" | "error"; message: string } | null;
};

function emptyExpenseDraft(): ExpenseInput {
  return {
    expenseId: "",
    name: "",
    category: "",
    activityId: null,
    wbsId: null,
    expenseDate: null,
    plannedCost: null,
    actualCost: null,
    remainingCost: null,
    currency: null,
    note: null,
  };
}

function emptyAccountDraft(): CostAccountInput {
  return { accountId: "", name: "", parentAccountId: null, description: null };
}

export function mountWorkspaceExpensesPage(host: HTMLElement, options: ExpensePageOptions): void {
  if (host.dataset.expensesMounted === "true") return;
  host.dataset.expensesMounted = "true";
  const { transport, context, locale, activities, wbsNodes } = options;
  const state: PageState = {
    status: "loading",
    errorCode: null,
    expenses: [],
    selectedExpenseId: null,
    expenseMode: "browse",
    expenseDraft: emptyExpenseDraft(),
    accountsStatus: "loading",
    accountsErrorCode: null,
    accounts: [],
    selectedAccountId: null,
    accountMode: "browse",
    accountDraft: emptyAccountDraft(),
    busy: false,
    notice: null,
  };

  const say = (en: string, fa: string): string => text(locale, en, fa);
  const selectedExpense = (): ExpenseRecord | null =>
    state.expenses.find((item) => item.expenseId === state.selectedExpenseId) ?? null;
  const selectedAccount = (): CostAccountRecord | null =>
    state.accounts.find((item) => item.accountId === state.selectedAccountId) ?? null;
  const activityLabel = (id: string): string => {
    const activity = activities.find((item) => item.id === id);
    return activity ? `${activity.code} ${activity.name}` : id;
  };
  const wbsLabel = (id: string): string => {
    const node = wbsNodes.find((item) => item.id === id);
    return node ? `${node.code} ${node.name}` : id;
  };

  function renderExpenseRegister(): string {
    if (state.status === "loading") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading project expenses…", "در حال خواندن هزینه‌های پروژه…"))}</div>`;
    }
    if (state.status === "error") {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Project expenses could not be read", "خواندن هزینه‌های پروژه ناموفق بود"))} (${escapeHtml(state.errorCode ?? "unknown")})</div>`;
    }
    if (!state.expenses.length) {
      return `<div class="cp-calendar-empty">${escapeHtml(say("No project expenses are stored for this project.", "هیچ هزینه‌ای برای این پروژه ذخیره نشده است."))}</div>`;
    }
    const rows = state.expenses.map((item) => {
      const active = item.expenseId === state.selectedExpenseId;
      return `<tr data-expense-row data-expense-id="${escapeHtml(item.expenseId)}" tabindex="0" role="button" aria-selected="${active}" class="${active ? "is-selected" : ""}"><td><strong>${escapeHtml(item.expenseId)}</strong></td><td>${escapeHtml(item.name)}</td><td>${escapeHtml(item.category)}</td><td>${escapeHtml(item.activityId ? activityLabel(item.activityId) : "—")}</td><td>${escapeHtml(item.wbsId ? wbsLabel(item.wbsId) : "—")}</td><td>${escapeHtml(item.expenseDate ?? "—")}</td><td>${escapeHtml(item.plannedCost ?? "—")}</td><td>${escapeHtml(item.actualCost ?? "—")}</td><td>${escapeHtml(item.remainingCost ?? "—")}</td><td>${escapeHtml(item.currency ?? "—")}</td></tr>`;
    }).join("");
    return `<div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(say("Expense ID", "شناسه هزینه"))}</th><th>${escapeHtml(say("Expense Item", "شرح هزینه"))}</th><th>${escapeHtml(say("Category", "دسته"))}</th><th>${escapeHtml(say("Activity", "فعالیت"))}</th><th>${escapeHtml(say("WBS", "ساختار شکست"))}</th><th>${escapeHtml(say("Expense Date", "تاریخ هزینه"))}</th><th>${escapeHtml(say("Planned Cost", "هزینه برنامه‌ای"))}</th><th>${escapeHtml(say("Actual Cost", "هزینه واقعی"))}</th><th>${escapeHtml(say("Remaining Cost", "هزینه باقی‌مانده"))}</th><th>${escapeHtml(say("Currency", "ارز"))}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function selectOptions(
    current: string,
    items: readonly { id: string; label: string }[],
    placeholder: string,
  ): string {
    const known = items.some((item) => item.id === current);
    const first = current && !known
      ? `<option value="${escapeHtml(current)}" selected>${escapeHtml(current)}</option>`
      : `<option value="">${escapeHtml(placeholder)}</option>`;
    return first + items.map((item) =>
      `<option value="${escapeHtml(item.id)}"${item.id === current ? " selected" : ""}>${escapeHtml(item.label)}</option>`
    ).join("");
  }

  function renderExpenseForm(): string {
    const draft = state.expenseDraft;
    return `<form data-expense-form class="cp-expense-fields">
      <label>${escapeHtml(say("Expense ID", "شناسه هزینه"))}<input name="expense-id" value="${escapeHtml(draft.expenseId)}" required></label>
      <label>${escapeHtml(say("Expense Item", "شرح هزینه"))}<input name="expense-name" value="${escapeHtml(draft.name)}" required></label>
      <label>${escapeHtml(say("Category", "دسته"))}<input name="expense-category" value="${escapeHtml(draft.category)}" required></label>
      <label>${escapeHtml(say("Activity", "فعالیت"))}<select name="activity-id">${selectOptions(draft.activityId ?? "", activities.map((item) => ({ id: item.id, label: `${item.code} ${item.name}` })), say("No activity reference", "بدون ارجاع فعالیت"))}</select></label>
      <label>${escapeHtml(say("WBS", "ساختار شکست"))}<select name="wbs-id">${selectOptions(draft.wbsId ?? "", wbsNodes.map((item) => ({ id: item.id, label: `${item.code} ${item.name}` })), say("No WBS reference", "بدون ارجاع ساختار شکست"))}</select></label>
      <label>${escapeHtml(say("Expense Date", "تاریخ هزینه"))}<input name="expense-date" type="date" value="${escapeHtml(draft.expenseDate ?? "")}"></label>
      <label>${escapeHtml(say("Planned Cost", "هزینه برنامه‌ای"))}<input name="planned-cost" inputmode="decimal" value="${escapeHtml(draft.plannedCost ?? "")}"></label>
      <label>${escapeHtml(say("Actual Cost", "هزینه واقعی"))}<input name="actual-cost" inputmode="decimal" value="${escapeHtml(draft.actualCost ?? "")}"></label>
      <label>${escapeHtml(say("Remaining Cost", "هزینه باقی‌مانده"))}<input name="remaining-cost" inputmode="decimal" value="${escapeHtml(draft.remainingCost ?? "")}"></label>
      <label>${escapeHtml(say("Currency", "ارز"))}<input name="currency" value="${escapeHtml(draft.currency ?? "")}"></label>
      <label class="cp-expense-note">${escapeHtml(say("Note", "یادداشت"))}<input name="expense-note" value="${escapeHtml(draft.note ?? "")}"></label>
      <div class="cp-calendar-panel-actions"><button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Create expense", "ایجاد هزینه"))}</button><button type="button" data-expense-action="cancel">${escapeHtml(say("Cancel", "لغو"))}</button></div>
    </form>`;
  }

  function renderExpenseDetails(): string {
    const item = selectedExpense();
    if (state.expenseMode === "create") return renderExpenseForm();
    if (!item) {
      return `<p>${escapeHtml(say("Select an expense from the register to read its stored values.", "برای خواندن مقادیر ذخیره‌شده، یک هزینه را از فهرست انتخاب کنید."))}</p>`;
    }
    const row = (label: string, value: string | null): string =>
      `<label>${escapeHtml(label)}<input readonly value="${escapeHtml(value ?? say("Not provided", "ارائه نشده"))}"></label>`;
    return `<div class="cp-expense-fields">
      ${row(say("Expense ID", "شناسه هزینه"), item.expenseId)}
      ${row(say("Expense Item", "شرح هزینه"), item.name)}
      ${row(say("Category", "دسته"), item.category)}
      ${row(say("Activity", "فعالیت"), item.activityId ? activityLabel(item.activityId) : null)}
      ${row(say("WBS", "ساختار شکست"), item.wbsId ? wbsLabel(item.wbsId) : null)}
      ${row(say("Expense Date", "تاریخ هزینه"), item.expenseDate)}
      ${row(say("Planned Cost", "هزینه برنامه‌ای"), item.plannedCost)}
      ${row(say("Actual Cost", "هزینه واقعی"), item.actualCost)}
      ${row(say("Remaining Cost", "هزینه باقی‌مانده"), item.remainingCost)}
      ${row(say("Currency", "ارز"), item.currency)}
      ${row(say("Note", "یادداشت"), item.note)}
    </div>
    <p class="cp-register-notice">${escapeHtml(say("Stored expenses are immutable. Create a new expense ID to record a changed expense.", "هزینه‌های ذخیره‌شده تغییرناپذیرند. برای ثبت هزینهٔ تغییرکرده، شناسه هزینهٔ جدید ایجاد کنید."))}</p>`;
  }

  function renderCostAccountRegister(): string {
    if (state.accountsStatus === "loading") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading cost accounts…", "در حال خواندن حساب‌های هزینه…"))}</div>`;
    }
    if (state.accountsStatus === "error") {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Cost accounts could not be read", "خواندن حساب‌های هزینه ناموفق بود"))} (${escapeHtml(state.accountsErrorCode ?? "unknown")})</div>`;
    }
    if (!state.accounts.length) {
      return `<div class="cp-calendar-empty">${escapeHtml(say("No cost accounts are stored for this project.", "هیچ حساب هزینه‌ای برای این پروژه ذخیره نشده است."))}</div>`;
    }
    const rows = state.accounts.map((item) => {
      const active = item.accountId === state.selectedAccountId;
      return `<tr data-cost-account-row data-cost-account-id="${escapeHtml(item.accountId)}" tabindex="0" role="button" aria-selected="${active}" class="${active ? "is-selected" : ""}"><td><strong>${escapeHtml(item.accountId)}</strong></td><td>${escapeHtml(item.name)}</td><td>${escapeHtml(item.parentAccountId ?? "—")}</td><td>${escapeHtml(item.description ?? "—")}</td></tr>`;
    }).join("");
    return `<div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(say("Account ID", "شناسه حساب"))}</th><th>${escapeHtml(say("Account Name", "نام حساب"))}</th><th>${escapeHtml(say("Parent Account", "حساب والد"))}</th><th>${escapeHtml(say("Description", "شرح"))}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function renderCostAccountForm(): string {
    const draft = state.accountDraft;
    return `<form data-cost-account-form class="cp-expense-fields">
      <label>${escapeHtml(say("Account ID", "شناسه حساب"))}<input name="account-id" value="${escapeHtml(draft.accountId)}" required></label>
      <label>${escapeHtml(say("Account Name", "نام حساب"))}<input name="account-name" value="${escapeHtml(draft.name)}" required></label>
      <label>${escapeHtml(say("Parent Account", "حساب والد"))}<select name="parent-account-id">${selectOptions(draft.parentAccountId ?? "", state.accounts.map((item) => ({ id: item.accountId, label: `${item.accountId} ${item.name}` })), say("No parent account", "بدون حساب والد"))}</select></label>
      <label class="cp-expense-note">${escapeHtml(say("Description", "شرح"))}<input name="account-description" value="${escapeHtml(draft.description ?? "")}"></label>
      <div class="cp-calendar-panel-actions"><button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Create cost account", "ایجاد حساب هزینه"))}</button><button type="button" data-cost-account-action="cancel">${escapeHtml(say("Cancel", "لغو"))}</button></div>
    </form>`;
  }

  function renderCostAccountDetails(): string {
    const item = selectedAccount();
    if (state.accountMode === "create") return renderCostAccountForm();
    if (!item) {
      return `<p>${escapeHtml(say("Select a cost account from the register to read its stored values.", "برای خواندن مقادیر ذخیره‌شده، یک حساب هزینه را از فهرست انتخاب کنید."))}</p>`;
    }
    const row = (label: string, value: string | null): string =>
      `<label>${escapeHtml(label)}<input readonly value="${escapeHtml(value ?? say("Not provided", "ارائه نشده"))}"></label>`;
    return `<div class="cp-expense-fields">
      ${row(say("Account ID", "شناسه حساب"), item.accountId)}
      ${row(say("Account Name", "نام حساب"), item.name)}
      ${row(say("Parent Account", "حساب والد"), item.parentAccountId)}
      ${row(say("Description", "شرح"), item.description)}
    </div>
    <p class="cp-register-notice">${escapeHtml(say("Stored cost accounts are immutable; create a new account ID instead of re-defining one.", "حساب‌های هزینهٔ ذخیره‌شده تغییرناپذیرند؛ به‌جای بازتعریف، شناسه حساب جدید ایجاد کنید."))}</p>`;
  }

  function render(): void {
    host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(say("Project Expenses", "هزینه‌های پروژه"))}</strong><div><button type="button" data-expense-action="new" ${state.busy ? "disabled" : ""}>${escapeHtml(say("New Expense", "هزینهٔ جدید"))}</button><button type="button" data-expense-action="reload" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button></div></div>
      ${renderExpenseRegister()}
      <section class="cp-register-details"><header><strong>${escapeHtml(say("Expense Details", "جزئیات هزینه"))}</strong><span>${selectedExpense() ? escapeHtml(selectedExpense()?.expenseId ?? "") : escapeHtml(say("No selection", "بدون انتخاب"))}</span></header><div class="cp-register-detail-content">${renderExpenseDetails()}</div></section>
      <section class="cp-cost-account-panel" data-cost-accounts-panel>
        <div class="cp-register-toolbar"><strong>${escapeHtml(say("Cost Accounts", "حساب‌های هزینه"))}</strong><div><button type="button" data-cost-account-action="new" ${state.busy ? "disabled" : ""}>${escapeHtml(say("New Cost Account", "حساب هزینهٔ جدید"))}</button><button type="button" data-cost-account-action="reload" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button></div></div>
        ${renderCostAccountRegister()}
        <section class="cp-register-details"><header><strong>${escapeHtml(say("Cost Account Details", "جزئیات حساب هزینه"))}</strong><span>${selectedAccount() ? escapeHtml(selectedAccount()?.accountId ?? "") : escapeHtml(say("No selection", "بدون انتخاب"))}</span></header><div class="cp-register-detail-content">${renderCostAccountDetails()}</div></section>
      </section>
      ${state.notice ? `<p class="cp-calendar-notice" data-expense-notice data-state="${state.notice.kind}" role="status">${escapeHtml(state.notice.message)}</p>` : ""}`;
  }

  async function reloadExpenses(keepSelection: string | null): Promise<void> {
    state.status = "loading";
    render();
    const result = await loadExpenses(transport, context);
    if (result.ok) {
      state.status = "loaded";
      state.errorCode = null;
      state.expenses = result.data;
      state.selectedExpenseId =
        keepSelection && result.data.some((item) => item.expenseId === keepSelection)
          ? keepSelection
          : null;
    } else {
      state.status = "error";
      state.errorCode = result.error.code;
    }
    render();
  }

  async function reloadAccounts(keepSelection: string | null): Promise<void> {
    state.accountsStatus = "loading";
    render();
    const result = await loadCostAccounts(transport, context);
    if (result.ok) {
      state.accountsStatus = "loaded";
      state.accountsErrorCode = null;
      state.accounts = result.data;
      state.selectedAccountId =
        keepSelection && result.data.some((item) => item.accountId === keepSelection)
          ? keepSelection
          : null;
    } else {
      state.accountsStatus = "error";
      state.accountsErrorCode = result.error.code;
    }
    render();
  }

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    const expenseRow = target.closest<HTMLElement>("[data-expense-row]");
    if (expenseRow?.dataset.expenseId) {
      state.selectedExpenseId = expenseRow.dataset.expenseId;
      state.expenseMode = "browse";
      state.notice = null;
      render();
      return;
    }
    const accountRow = target.closest<HTMLElement>("[data-cost-account-row]");
    if (accountRow?.dataset.costAccountId) {
      state.selectedAccountId = accountRow.dataset.costAccountId;
      state.accountMode = "browse";
      state.notice = null;
      render();
      return;
    }
    const expenseAction = target.closest<HTMLElement>("[data-expense-action]")?.dataset.expenseAction;
    if (expenseAction) {
      if (expenseAction === "new") {
        state.expenseMode = "create";
        state.expenseDraft = emptyExpenseDraft();
        state.notice = null;
        render();
      } else if (expenseAction === "cancel") {
        state.expenseMode = "browse";
        state.notice = null;
        render();
      } else if (expenseAction === "reload") {
        void reloadExpenses(state.selectedExpenseId);
      }
      return;
    }
    const accountAction = target.closest<HTMLElement>("[data-cost-account-action]")?.dataset.costAccountAction;
    if (!accountAction) return;
    if (accountAction === "new") {
      state.accountMode = "create";
      state.accountDraft = emptyAccountDraft();
      state.notice = null;
      render();
    } else if (accountAction === "cancel") {
      state.accountMode = "browse";
      state.notice = null;
      render();
    } else if (accountAction === "reload") {
      void reloadAccounts(state.selectedAccountId);
    }
  });

  host.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const target = event.target as HTMLElement;
    const expenseRow = target.closest<HTMLElement>("[data-expense-row]");
    if (expenseRow?.dataset.expenseId) {
      event.preventDefault();
      state.selectedExpenseId = expenseRow.dataset.expenseId;
      state.expenseMode = "browse";
      state.notice = null;
      render();
      return;
    }
    const accountRow = target.closest<HTMLElement>("[data-cost-account-row]");
    if (accountRow?.dataset.costAccountId) {
      event.preventDefault();
      state.selectedAccountId = accountRow.dataset.costAccountId;
      state.accountMode = "browse";
      state.notice = null;
      render();
    }
  });

  host.addEventListener("input", (event) => {
    const target = event.target as HTMLInputElement;
    switch (target.name) {
      case "expense-id": state.expenseDraft.expenseId = target.value; break;
      case "expense-name": state.expenseDraft.name = target.value; break;
      case "expense-category": state.expenseDraft.category = target.value; break;
      case "expense-date": state.expenseDraft.expenseDate = target.value; break;
      case "planned-cost": state.expenseDraft.plannedCost = target.value; break;
      case "actual-cost": state.expenseDraft.actualCost = target.value; break;
      case "remaining-cost": state.expenseDraft.remainingCost = target.value; break;
      case "currency": state.expenseDraft.currency = target.value; break;
      case "expense-note": state.expenseDraft.note = target.value; break;
      case "account-id": state.accountDraft.accountId = target.value; break;
      case "account-name": state.accountDraft.name = target.value; break;
      case "account-description": state.accountDraft.description = target.value; break;
      default: break;
    }
  });

  host.addEventListener("change", (event) => {
    const target = event.target as HTMLSelectElement;
    if (target.name === "activity-id") state.expenseDraft.activityId = target.value;
    if (target.name === "wbs-id") state.expenseDraft.wbsId = target.value;
    if (target.name === "parent-account-id") state.accountDraft.parentAccountId = target.value;
  });

  host.addEventListener("submit", (event) => {
    const form = event.target as HTMLFormElement;
    if (!form.matches("[data-expense-form]") && !form.matches("[data-cost-account-form]")) return;
    event.preventDefault();
    if (state.busy) return;
    const isExpense = form.matches("[data-expense-form]");
    void (async () => {
      state.busy = true;
      render();
      if (isExpense) {
        const result = await saveExpense(transport, context, state.expenseDraft);
        state.busy = false;
        if (!result.ok) {
          state.notice = {
            kind: "error",
            message: `${say("Expense was not saved", "هزینه ذخیره نشد")} (${result.error.code})`,
          };
          render();
          return;
        }
        state.notice = { kind: "ok", message: say("Expense saved.", "هزینه ذخیره شد.") };
        state.expenseMode = "browse";
        await reloadExpenses(result.data.expenseId);
        return;
      }
      const result = await saveCostAccount(transport, context, state.accountDraft);
      state.busy = false;
      if (!result.ok) {
        state.notice = {
          kind: "error",
          message: `${say("Cost account was not saved", "حساب هزینه ذخیره نشد")} (${result.error.code})`,
        };
        render();
        return;
      }
      state.notice = { kind: "ok", message: say("Cost account saved.", "حساب هزینه ذخیره شد.") };
      state.accountMode = "browse";
      await reloadAccounts(result.data.accountId);
    })();
  });

  void reloadExpenses(null);
  void reloadAccounts(null);
}
