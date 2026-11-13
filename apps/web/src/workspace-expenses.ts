import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import { bindRegisterContextMenus } from "./workspace-register-context-menu.js";

export const COST_API_VERSION = "p6-cost-api.v1";
export const EXPENSE_CATEGORIES = ["labor", "material", "equipment", "subcontract", "overhead", "other"] as const;
export type ExpenseCategory = (typeof EXPENSE_CATEGORIES)[number];

export type ExpenseRecord = {
  expenseId: string;
  name: string;
  category: string;
  activityId: string | null;
  wbsId: string | null;
  costAccountId: string | null;
  expenseDate: string | null;
  accrualDate: string | null;
  plannedCost: string | null;
  actualCost: string | null;
  remainingCost: string | null;
  currency: string;
  note: string | null;
  revision: number;
};

export type CostAccountRecord = {
  accountId: string;
  name: string;
  parentAccountId: string | null;
  description: string | null;
  isDefault: boolean;
  revision: number;
};

export type ExpenseInput = {
  expenseId: string;
  name: string;
  category: string;
  activityId: string | null;
  wbsId: string | null;
  costAccountId: string | null;
  expenseDate: string | null;
  accrualDate: string | null;
  plannedCost: string | null;
  actualCost: string | null;
  remainingCost: string | null;
  currency: string;
  note: string | null;
};

export type CostAccountInput = {
  accountId: string;
  name: string;
  parentAccountId: string | null;
  description: string | null;
  isDefault: boolean;
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
  canWrite: boolean;
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
  if (typeof value !== "string") throw new Error(code);
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (!/^\d+(\.\d{1,2})?$/.test(trimmed)) throw new Error(code);
  return trimmed;
}

function revision(value: unknown, code: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1) throw new Error(code);
  return value;
}

function expensePath(context: ProjectContext, expenseId?: string): string {
  const base = `/api/projects/${encodeURIComponent(context.project_id)}/cost/expenses`;
  return expenseId ? `${base}/${encodeURIComponent(expenseId)}` : base;
}

function costAccountPath(context: ProjectContext, accountId?: string, action?: string): string {
  const base = `/api/projects/${encodeURIComponent(context.project_id)}/cost/accounts`;
  if (!accountId) return base;
  return `${base}/${encodeURIComponent(accountId)}${action ? `/${action}` : ""}`;
}

export function parseExpense(value: unknown): ExpenseRecord {
  if (!isRecord(value)) throw new Error("INVALID_EXPENSE_RECORD");
  if (value.contract_version !== COST_API_VERSION) throw new Error("INVALID_EXPENSE_RESPONSE");
  const { expense_id, name, category, currency } = value;
  if (
    typeof expense_id !== "string" || !expense_id.trim() ||
    typeof name !== "string" || !name.trim() ||
    typeof category !== "string" || !EXPENSE_CATEGORIES.includes(category as ExpenseCategory) ||
    typeof currency !== "string" || !/^[A-Z]{3}$/.test(currency)
  ) {
    throw new Error("INVALID_EXPENSE_RECORD");
  }
  return {
    expenseId: expense_id,
    name,
    category,
    activityId: optionalText(value.activity_id, "INVALID_EXPENSE_RECORD"),
    wbsId: optionalText(value.wbs_id, "INVALID_EXPENSE_RECORD"),
    costAccountId: optionalText(value.cost_account_id, "INVALID_EXPENSE_RECORD"),
    expenseDate: optionalText(value.expense_date, "INVALID_EXPENSE_RECORD"),
    accrualDate: optionalText(value.accrual_date, "INVALID_EXPENSE_RECORD"),
    plannedCost: decimalText(value.planned_amount, "INVALID_EXPENSE_RECORD"),
    actualCost: decimalText(value.actual_amount, "INVALID_EXPENSE_RECORD"),
    remainingCost: decimalText(value.remaining_amount, "INVALID_EXPENSE_RECORD"),
    currency,
    note: optionalText(value.note, "INVALID_EXPENSE_RECORD"),
    revision: revision(value.revision, "INVALID_EXPENSE_RECORD"),
  };
}

export function parseCostAccount(value: unknown): CostAccountRecord {
  if (!isRecord(value)) throw new Error("INVALID_COST_ACCOUNT_RECORD");
  if (value.contract_version !== COST_API_VERSION) {
    throw new Error("INVALID_COST_ACCOUNT_RESPONSE");
  }
  const { account_id, name } = value;
  if (
    typeof account_id !== "string" || !account_id.trim() ||
    typeof name !== "string" || !name.trim()
  ) {
    throw new Error("INVALID_COST_ACCOUNT_RECORD");
  }
  if (typeof value.is_default !== "boolean") throw new Error("INVALID_COST_ACCOUNT_RECORD");
  return {
    accountId: account_id,
    name,
    parentAccountId: optionalText(value.parent_account_id, "INVALID_COST_ACCOUNT_RECORD"),
    description: optionalText(value.description, "INVALID_COST_ACCOUNT_RECORD"),
    isDefault: value.is_default,
    revision: revision(value.revision, "INVALID_COST_ACCOUNT_RECORD"),
  };
}

export async function loadExpenses(
  transport: ApiTransport,
  context: ProjectContext,
  filters?: { category?: string; costAccountId?: string; activityId?: string; search?: string },
): Promise<ApiResult<readonly ExpenseRecord[]>> {
  const query = new URLSearchParams();
  if (filters?.category) query.set("category", filters.category);
  if (filters?.costAccountId) query.set("cost_account_id", filters.costAccountId);
  if (filters?.activityId) query.set("activity_id", filters.activityId);
  if (filters?.search) query.set("search", filters.search);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  const result = await transport.get<unknown>(`${expensePath(context)}${suffix}`, context);
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || payload.contract_version !== COST_API_VERSION || !Array.isArray(payload.expenses)) {
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
  if (!isRecord(payload) || payload.contract_version !== COST_API_VERSION || !Array.isArray(payload.cost_accounts)) {
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
  if (!/^\d+(\.\d{1,2})?$/.test(trimmed)) throw new Error(code);
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
  if (!EXPENSE_CATEGORIES.includes(input.category.trim() as ExpenseCategory)) {
    throw new Error("INVALID_EXPENSE_CATEGORY");
  }
  if (!/^[A-Z]{3}$/.test(input.currency.trim())) throw new Error("INVALID_EXPENSE_CURRENCY");
  return {
    expense_id: input.expenseId.trim(),
    name: input.name.trim(),
    category: input.category.trim(),
    currency: input.currency.trim(),
    activity_id: trimmedOrNull(input.activityId),
    wbs_id: trimmedOrNull(input.wbsId),
    cost_account_id: trimmedOrNull(input.costAccountId),
    expense_date: trimmedOrNull(input.expenseDate),
    accrual_date: trimmedOrNull(input.accrualDate),
    planned_amount: normalizedDecimal(input.plannedCost, "INVALID_EXPENSE_NUMBER"),
    actual_amount: normalizedDecimal(input.actualCost, "INVALID_EXPENSE_NUMBER"),
    remaining_amount: normalizedDecimal(input.remainingCost, "INVALID_EXPENSE_NUMBER"),
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
    account_id: input.accountId.trim(),
    name: input.name.trim(),
    parent_account_id: parent,
    description: trimmedOrNull(input.description),
    is_default: input.isDefault,
  };
}

export async function saveExpense(
  transport: ApiTransport,
  context: ProjectContext,
  input: ExpenseInput,
  expectedRevision?: number,
): Promise<ApiResult<ExpenseRecord>> {
  let payload: Record<string, unknown>;
  try {
    payload = buildExpensePayload(input);
  } catch (error) {
    return localError(error instanceof Error ? error.message : "EXPENSE_FIELDS_REQUIRED");
  }
  const result = expectedRevision === undefined
    ? await transport.post<Record<string, unknown>, unknown>(
        expensePath(context),
        payload,
        context,
        crypto.randomUUID(),
      )
    : transport.patch && (await transport.patch<Record<string, unknown>, unknown>(
        expensePath(context, input.expenseId.trim()),
        { ...payload, expected_revision: expectedRevision },
        context,
      ));
  if (!result) return localError("TRANSPORT_UNAVAILABLE");
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
  expectedRevision?: number,
): Promise<ApiResult<CostAccountRecord>> {
  let payload: Record<string, unknown>;
  try {
    payload = buildCostAccountPayload(input);
  } catch (error) {
    return localError(error instanceof Error ? error.message : "COST_ACCOUNT_FIELDS_REQUIRED");
  }
  const result = expectedRevision === undefined
    ? await transport.post<Record<string, unknown>, unknown>(
        costAccountPath(context),
        payload,
        context,
        crypto.randomUUID(),
      )
    : transport.patch && (await transport.patch<Record<string, unknown>, unknown>(
        costAccountPath(context, input.accountId.trim()),
        { ...payload, expected_revision: expectedRevision },
        context,
      ));
  if (!result) return localError("TRANSPORT_UNAVAILABLE");
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseCostAccount(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_COST_ACCOUNT_RESPONSE");
  }
}

function deletedResult(result: ApiResult<unknown> | undefined): ApiResult<{ deleted: true }> {
  if (!result) return localError("TRANSPORT_UNAVAILABLE");
  if (!result.ok) return result;
  return { ok: true, data: { deleted: true } };
}

export async function deleteExpense(
  transport: ApiTransport,
  context: ProjectContext,
  expenseId: string,
  expectedRevision: number,
): Promise<ApiResult<{ deleted: true }>> {
  if (!transport.delete) return localError("TRANSPORT_UNAVAILABLE");
  return deletedResult(
    await transport.delete<Record<string, unknown>, unknown>(
      expensePath(context, expenseId),
      { expected_revision: expectedRevision },
      context,
    ),
  );
}

export async function deleteCostAccount(
  transport: ApiTransport,
  context: ProjectContext,
  accountId: string,
  expectedRevision: number,
): Promise<ApiResult<{ deleted: true }>> {
  if (!transport.delete) return localError("TRANSPORT_UNAVAILABLE");
  return deletedResult(
    await transport.delete<Record<string, unknown>, unknown>(
      costAccountPath(context, accountId),
      { expected_revision: expectedRevision },
      context,
    ),
  );
}

export async function copyCostAccount(
  transport: ApiTransport,
  context: ProjectContext,
  sourceAccountId: string,
  accountId: string,
  name: string,
): Promise<ApiResult<CostAccountRecord>> {
  const result = await transport.post<Record<string, unknown>, unknown>(
    costAccountPath(context, sourceAccountId, "copy"),
    { account_id: accountId, name },
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

export async function setDefaultCostAccount(
  transport: ApiTransport,
  context: ProjectContext,
  accountId: string,
  expectedRevision: number,
): Promise<ApiResult<readonly CostAccountRecord[]>> {
  const result = await transport.post<Record<string, unknown>, unknown>(
    costAccountPath(context, accountId, "default"),
    { expected_revision: expectedRevision },
    context,
    crypto.randomUUID(),
  );
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || !Array.isArray(payload.cost_accounts)) {
    return localError("INVALID_COST_ACCOUNT_LIST");
  }
  try {
    return { ok: true, data: payload.cost_accounts.map((item) => parseCostAccount(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_COST_ACCOUNT_LIST");
  }
}

type PageState = {
  status: "loading" | "loaded" | "error";
  errorCode: string | null;
  expenses: readonly ExpenseRecord[];
  selectedExpenseId: string | null;
  expenseMode: "browse" | "create" | "edit";
  editingExpenseRevision: number | null;
  expenseDraft: ExpenseInput;
  accountsStatus: "loading" | "loaded" | "error";
  accountsErrorCode: string | null;
  accounts: readonly CostAccountRecord[];
  selectedAccountId: string | null;
  accountMode: "browse" | "create" | "edit";
  editingAccountRevision: number | null;
  accountDraft: CostAccountInput;
  busy: boolean;
  notice: { kind: "ok" | "error"; message: string } | null;
};

function emptyExpenseDraft(): ExpenseInput {
  return {
    expenseId: "",
    name: "",
    category: "material",
    activityId: null,
    wbsId: null,
    costAccountId: null,
    expenseDate: null,
    accrualDate: null,
    plannedCost: null,
    actualCost: null,
    remainingCost: null,
    currency: "USD",
    note: null,
  };
}

function emptyAccountDraft(): CostAccountInput {
  return {
    accountId: "",
    name: "",
    parentAccountId: null,
    description: null,
    isDefault: false,
  };
}

function draftFromExpense(item: ExpenseRecord): ExpenseInput {
  return {
    expenseId: item.expenseId,
    name: item.name,
    category: item.category,
    activityId: item.activityId,
    wbsId: item.wbsId,
    costAccountId: item.costAccountId,
    expenseDate: item.expenseDate,
    accrualDate: item.accrualDate,
    plannedCost: item.plannedCost,
    actualCost: item.actualCost,
    remainingCost: item.remainingCost,
    currency: item.currency,
    note: item.note,
  };
}

function draftFromAccount(item: CostAccountRecord): CostAccountInput {
  return {
    accountId: item.accountId,
    name: item.name,
    parentAccountId: item.parentAccountId,
    description: item.description,
    isDefault: item.isDefault,
  };
}

export function mountWorkspaceExpensesPage(host: HTMLElement, options: ExpensePageOptions): void {
  if (host.dataset.expensesMounted === "true") return;
  host.dataset.expensesMounted = "true";
  const { transport, context, locale, canWrite, activities, wbsNodes } = options;
  const state: PageState = {
    status: "loading",
    errorCode: null,
    expenses: [],
    selectedExpenseId: null,
    expenseMode: "browse",
    editingExpenseRevision: null,
    expenseDraft: emptyExpenseDraft(),
    accountsStatus: "loading",
    accountsErrorCode: null,
    accounts: [],
    selectedAccountId: null,
    accountMode: "browse",
    editingAccountRevision: null,
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
  const accountLabel = (id: string): string => {
    const account = state.accounts.find((item) => item.accountId === id);
    return account ? `${account.accountId} ${account.name}` : id;
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
      const actions = canWrite
        ? `<button type="button" data-expense-edit="${escapeHtml(item.expenseId)}">${escapeHtml(say("Edit", "ویرایش"))}</button><button type="button" data-expense-delete="${escapeHtml(item.expenseId)}" data-expense-revision="${item.revision}">${escapeHtml(say("Delete", "حذف"))}</button>`
        : "—";
      return `<tr data-expense-row data-expense-id="${escapeHtml(item.expenseId)}" tabindex="0" role="button" aria-selected="${active}" class="${active ? "is-selected" : ""}"><td><strong>${escapeHtml(item.expenseId)}</strong></td><td>${escapeHtml(item.name)}</td><td>${escapeHtml(item.category)}</td><td>${escapeHtml(item.activityId ? activityLabel(item.activityId) : "—")}</td><td>${escapeHtml(item.costAccountId ? accountLabel(item.costAccountId) : "—")}</td><td>${escapeHtml(item.expenseDate ?? "—")}</td><td>${escapeHtml(item.plannedCost ?? "—")}</td><td>${escapeHtml(item.actualCost ?? "—")}</td><td>${escapeHtml(item.remainingCost ?? "—")}</td><td>${escapeHtml(item.currency)}</td><td class="cp-register-actions">${actions}</td></tr>`;
    }).join("");
    return `<div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(say("Expense ID", "شناسه هزینه"))}</th><th>${escapeHtml(say("Expense Item", "شرح هزینه"))}</th><th>${escapeHtml(say("Category", "دسته"))}</th><th>${escapeHtml(say("Activity", "فعالیت"))}</th><th>${escapeHtml(say("Cost Account", "حساب هزینه"))}</th><th>${escapeHtml(say("Expense Date", "تاریخ هزینه"))}</th><th>${escapeHtml(say("Planned Cost", "هزینه برنامه‌ای"))}</th><th>${escapeHtml(say("Actual Cost", "هزینه واقعی"))}</th><th>${escapeHtml(say("Remaining Cost", "هزینه باقی‌مانده"))}</th><th>${escapeHtml(say("Currency", "ارز"))}</th><th>${escapeHtml(say("Actions", "عملیات"))}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function selectOptions(
    current: string,
    items: readonly { id: string; label: string }[],
    placeholder: string,
    disabled = false,
  ): string {
    const known = items.some((item) => item.id === current);
    const first = current && !known
      ? `<option value="${escapeHtml(current)}" selected>${escapeHtml(current)}</option>`
      : `<option value="">${escapeHtml(placeholder)}</option>`;
    return first + items.map((item) =>
      `<option value="${escapeHtml(item.id)}"${item.id === current ? " selected" : ""}${disabled && item.id === current ? " disabled" : ""}>${escapeHtml(item.label)}</option>`
    ).join("");
  }

  function renderExpenseForm(): string {
    const draft = state.expenseDraft;
    const editing = state.expenseMode === "edit";
    return `<form data-expense-form class="cp-expense-fields">
      <label>${escapeHtml(say("Expense ID", "شناسه هزینه"))}<input name="expense-id" value="${escapeHtml(draft.expenseId)}" ${editing ? "readonly" : ""} required></label>
      <label>${escapeHtml(say("Expense Item", "شرح هزینه"))}<input name="expense-name" value="${escapeHtml(draft.name)}" required></label>
      <label>${escapeHtml(say("Category", "دسته"))}<select name="expense-category">${EXPENSE_CATEGORIES.map((category) => `<option value="${category}"${category === draft.category ? " selected" : ""}>${escapeHtml(category)}</option>`).join("")}</select></label>
      <label>${escapeHtml(say("Activity", "فعالیت"))}<select name="activity-id">${selectOptions(draft.activityId ?? "", activities.map((item) => ({ id: item.id, label: `${item.code} ${item.name}` })), say("No activity reference", "بدون ارجاع فعالیت"))}</select></label>
      <label>${escapeHtml(say("WBS", "ساختار شکست"))}<select name="wbs-id">${selectOptions(draft.wbsId ?? "", wbsNodes.map((item) => ({ id: item.id, label: `${item.code} ${item.name}` })), say("No WBS reference", "بدون ارجاع ساختار شکست"))}</select></label>
      <label>${escapeHtml(say("Cost Account", "حساب هزینه"))}<select name="cost-account-id">${selectOptions(draft.costAccountId ?? "", state.accounts.map((item) => ({ id: item.accountId, label: `${item.accountId} ${item.name}` })), say("No cost account", "بدون حساب هزینه"))}</select></label>
      <label>${escapeHtml(say("Expense Date", "تاریخ هزینه"))}<input name="expense-date" type="date" value="${escapeHtml(draft.expenseDate ?? "")}"></label>
      <label>${escapeHtml(say("Accrual Date", "تاریخ تعهد"))}<input name="accrual-date" type="date" value="${escapeHtml(draft.accrualDate ?? "")}"></label>
      <label>${escapeHtml(say("Planned Cost", "هزینه برنامه‌ای"))}<input name="planned-cost" inputmode="decimal" value="${escapeHtml(draft.plannedCost ?? "")}"></label>
      <label>${escapeHtml(say("Actual Cost", "هزینه واقعی"))}<input name="actual-cost" inputmode="decimal" value="${escapeHtml(draft.actualCost ?? "")}"></label>
      <label>${escapeHtml(say("Remaining Cost", "هزینه باقی‌مانده"))}<input name="remaining-cost" inputmode="decimal" value="${escapeHtml(draft.remainingCost ?? "")}"></label>
      <label>${escapeHtml(say("Currency", "ارز"))}<input name="currency" value="${escapeHtml(draft.currency)}" maxlength="3" required></label>
      <label class="cp-expense-note">${escapeHtml(say("Note", "یادداشت"))}<input name="expense-note" value="${escapeHtml(draft.note ?? "")}"></label>
      <div class="cp-calendar-panel-actions"><button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(editing ? say("Save expense", "ذخیره هزینه") : say("Create expense", "ایجاد هزینه"))}</button><button type="button" data-expense-action="cancel">${escapeHtml(say("Cancel", "لغو"))}</button></div>
    </form>`;
  }

  function renderExpenseDetails(): string {
    const item = selectedExpense();
    if (state.expenseMode !== "browse") return renderExpenseForm();
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
      ${row(say("Cost Account", "حساب هزینه"), item.costAccountId ? accountLabel(item.costAccountId) : null)}
      ${row(say("Expense Date", "تاریخ هزینه"), item.expenseDate)}
      ${row(say("Accrual Date", "تاریخ تعهد"), item.accrualDate)}
      ${row(say("Planned Cost", "هزینه برنامه‌ای"), item.plannedCost)}
      ${row(say("Actual Cost", "هزینه واقعی"), item.actualCost)}
      ${row(say("Remaining Cost", "هزینه باقی‌مانده"), item.remainingCost)}
      ${row(say("Currency", "ارز"), item.currency)}
      ${row(say("Note", "یادداشت"), item.note)}
      ${row(say("Revision", "نسخه"), String(item.revision))}
    </div>`;
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
      const actions = canWrite
        ? `<button type="button" data-cost-account-edit="${escapeHtml(item.accountId)}">${escapeHtml(say("Edit", "ویرایش"))}</button><button type="button" data-cost-account-copy="${escapeHtml(item.accountId)}">${escapeHtml(say("Copy", "کپی"))}</button>${item.isDefault ? "" : `<button type="button" data-cost-account-default="${escapeHtml(item.accountId)}" data-cost-account-revision="${item.revision}">${escapeHtml(say("Set default", "تعیین پیش‌فرض"))}</button>`}<button type="button" data-cost-account-delete="${escapeHtml(item.accountId)}" data-cost-account-revision="${item.revision}">${escapeHtml(say("Delete", "حذف"))}</button>`
        : "—";
      return `<tr data-cost-account-row data-cost-account-id="${escapeHtml(item.accountId)}" tabindex="0" role="button" aria-selected="${active}" class="${active ? "is-selected" : ""}"><td><strong>${escapeHtml(item.accountId)}</strong>${item.isDefault ? ` <span class="cp-budget-status" data-cost-account-default-badge>${escapeHtml(say("Default", "پیش‌فرض"))}</span>` : ""}</td><td>${escapeHtml(item.name)}</td><td>${escapeHtml(item.parentAccountId ?? "—")}</td><td>${escapeHtml(item.description ?? "—")}</td><td>${escapeHtml(String(item.revision))}</td><td class="cp-register-actions">${actions}</td></tr>`;
    }).join("");
    return `<div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(say("Account ID", "شناسه حساب"))}</th><th>${escapeHtml(say("Account Name", "نام حساب"))}</th><th>${escapeHtml(say("Parent Account", "حساب والد"))}</th><th>${escapeHtml(say("Description", "شرح"))}</th><th>${escapeHtml(say("Revision", "نسخه"))}</th><th>${escapeHtml(say("Actions", "عملیات"))}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function renderCostAccountForm(): string {
    const draft = state.accountDraft;
    const editing = state.accountMode === "edit";
    const parents = state.accounts
      .filter((item) => item.accountId !== draft.accountId)
      .map((item) => ({ id: item.accountId, label: `${item.accountId} ${item.name}` }));
    return `<form data-cost-account-form class="cp-expense-fields">
      <label>${escapeHtml(say("Account ID", "شناسه حساب"))}<input name="account-id" value="${escapeHtml(draft.accountId)}" ${editing ? "readonly" : ""} required></label>
      <label>${escapeHtml(say("Account Name", "نام حساب"))}<input name="account-name" value="${escapeHtml(draft.name)}" required></label>
      <label>${escapeHtml(say("Parent Account", "حساب والد"))}<select name="parent-account-id">${selectOptions(draft.parentAccountId ?? "", parents, say("No parent account", "بدون حساب والد"))}</select></label>
      <label class="cp-expense-note">${escapeHtml(say("Description", "شرح"))}<input name="account-description" value="${escapeHtml(draft.description ?? "")}"></label>
      <label class="cp-expense-note"><span>${escapeHtml(say("Project default account", "حساب پیش‌فرض پروژه"))}</span><input type="checkbox" name="account-default" ${draft.isDefault ? "checked" : ""}></label>
      <div class="cp-calendar-panel-actions"><button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(editing ? say("Save cost account", "ذخیره حساب هزینه") : say("Create cost account", "ایجاد حساب هزینه"))}</button><button type="button" data-cost-account-action="cancel">${escapeHtml(say("Cancel", "لغو"))}</button></div>
    </form>`;
  }

  function renderCostAccountDetails(): string {
    const item = selectedAccount();
    if (state.accountMode !== "browse") return renderCostAccountForm();
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
      ${row(say("Default", "پیش‌فرض"), item.isDefault ? say("Yes", "بله") : say("No", "خیر"))}
      ${row(say("Revision", "نسخه"), String(item.revision))}
    </div>`;
  }

  function render(): void {
    host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(say("Project Expenses", "هزینه‌های پروژه"))}</strong><div>${canWrite ? `<button type="button" data-expense-action="new" ${state.busy ? "disabled" : ""}>${escapeHtml(say("New Expense", "هزینهٔ جدید"))}</button>` : ""}<button type="button" data-expense-action="reload" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button></div></div>
      ${renderExpenseRegister()}
      <section class="cp-register-details"><header><strong>${escapeHtml(say("Expense Details", "جزئیات هزینه"))}</strong><span>${selectedExpense() ? escapeHtml(selectedExpense()?.expenseId ?? "") : escapeHtml(say("No selection", "بدون انتخاب"))}</span></header><div class="cp-register-detail-content">${renderExpenseDetails()}</div></section>
      <section class="cp-cost-account-panel" data-cost-accounts-panel>
        <div class="cp-register-toolbar"><strong>${escapeHtml(say("Cost Accounts", "حساب‌های هزینه"))}</strong><div>${canWrite ? `<button type="button" data-cost-account-action="new" ${state.busy ? "disabled" : ""}>${escapeHtml(say("New Cost Account", "حساب هزینهٔ جدید"))}</button>` : ""}<button type="button" data-cost-account-action="reload" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button></div></div>
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

  function beginEditExpense(item: ExpenseRecord): void {
    state.selectedExpenseId = item.expenseId;
    state.expenseMode = "edit";
    state.editingExpenseRevision = item.revision;
    state.expenseDraft = draftFromExpense(item);
    state.notice = null;
    render();
  }

  function beginEditAccount(item: CostAccountRecord): void {
    state.selectedAccountId = item.accountId;
    state.accountMode = "edit";
    state.editingAccountRevision = item.revision;
    state.accountDraft = draftFromAccount(item);
    state.notice = null;
    render();
  }

  async function runExpenseDelete(id: string, expectedRevision: number): Promise<void> {
    state.busy = true;
    render();
    const result = await deleteExpense(transport, context, id, expectedRevision);
    state.busy = false;
    if (!result.ok) {
      state.notice = {
        kind: "error",
        message: `${say("Expense was not deleted", "هزینه حذف نشد")} (${result.error.code})`,
      };
      await reloadExpenses(id);
      return;
    }
    state.notice = { kind: "ok", message: say("Expense deleted.", "هزینه حذف شد.") };
    state.selectedExpenseId = null;
    state.expenseMode = "browse";
    await reloadExpenses(null);
  }

  async function runAccountDelete(id: string, expectedRevision: number): Promise<void> {
    state.busy = true;
    render();
    const result = await deleteCostAccount(transport, context, id, expectedRevision);
    state.busy = false;
    if (!result.ok) {
      state.notice = {
        kind: "error",
        message: `${say("Cost account was not deleted", "حساب هزینه حذف نشد")} (${result.error.code})`,
      };
      await reloadAccounts(id);
      return;
    }
    state.notice = { kind: "ok", message: say("Cost account deleted.", "حساب هزینه حذف شد.") };
    state.selectedAccountId = null;
    state.accountMode = "browse";
    await reloadAccounts(null);
  }

  async function runAccountCopy(id: string): Promise<void> {
    const suffix = `-COPY-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;
    const source = state.accounts.find((item) => item.accountId === id);
    if (!source) return;
    state.busy = true;
    render();
    const result = await copyCostAccount(
      transport,
      context,
      id,
      `${id}${suffix}`.slice(0, 40),
      `${source.name} copy`,
    );
    state.busy = false;
    if (!result.ok) {
      state.notice = {
        kind: "error",
        message: `${say("Cost account was not copied", "حساب هزینه کپی نشد")} (${result.error.code})`,
      };
      render();
      return;
    }
    state.notice = { kind: "ok", message: say("Cost account copied.", "حساب هزینه کپی شد.") };
    await reloadAccounts(result.data.accountId);
  }

  async function runAccountDefault(id: string, expectedRevision: number): Promise<void> {
    state.busy = true;
    render();
    const result = await setDefaultCostAccount(transport, context, id, expectedRevision);
    state.busy = false;
    if (!result.ok) {
      state.notice = {
        kind: "error",
        message: `${say("Default account was not changed", "حساب پیش‌فرض تغییر نکرد")} (${result.error.code})`,
      };
      await reloadAccounts(id);
      return;
    }
    state.notice = { kind: "ok", message: say("Default cost account updated.", "حساب هزینهٔ پیش‌فرض به‌روزرسانی شد.") };
    await reloadAccounts(id);
  }

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    if (!canWrite && target.closest<HTMLElement>(
      "[data-expense-edit],[data-expense-delete],[data-cost-account-edit],[data-cost-account-delete],[data-cost-account-copy],button[data-cost-account-default]",
    )) return;
    const expenseEdit = target.closest<HTMLElement>("[data-expense-edit]")?.dataset.expenseEdit;
    if (expenseEdit) {
      const item = state.expenses.find((row) => row.expenseId === expenseEdit);
      if (item) beginEditExpense(item);
      return;
    }
    const expenseDelete = target.closest<HTMLElement>("[data-expense-delete]");
    if (expenseDelete?.dataset.expenseDelete) {
      const rev = Number(expenseDelete.dataset.expenseRevision);
      void runExpenseDelete(expenseDelete.dataset.expenseDelete, rev);
      return;
    }
    const accountEdit = target.closest<HTMLElement>("[data-cost-account-edit]")?.dataset.costAccountEdit;
    if (accountEdit) {
      const item = state.accounts.find((row) => row.accountId === accountEdit);
      if (item) beginEditAccount(item);
      return;
    }
    const accountDelete = target.closest<HTMLElement>("[data-cost-account-delete]");
    if (accountDelete?.dataset.costAccountDelete) {
      void runAccountDelete(
        accountDelete.dataset.costAccountDelete,
        Number(accountDelete.dataset.costAccountRevision),
      );
      return;
    }
    const accountCopy = target.closest<HTMLElement>("[data-cost-account-copy]")?.dataset.costAccountCopy;
    if (accountCopy) {
      void runAccountCopy(accountCopy);
      return;
    }
    const accountDefault = target.closest<HTMLElement>("button[data-cost-account-default]");
    if (accountDefault?.dataset.costAccountDefault) {
      void runAccountDefault(
        accountDefault.dataset.costAccountDefault,
        Number(accountDefault.dataset.costAccountRevision),
      );
      return;
    }
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
        if (!canWrite) return;
        state.expenseMode = "create";
        state.editingExpenseRevision = null;
        state.expenseDraft = emptyExpenseDraft();
        state.notice = null;
        render();
      } else if (expenseAction === "cancel") {
        state.expenseMode = "browse";
        state.editingExpenseRevision = null;
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
      if (!canWrite) return;
      state.accountMode = "create";
      state.editingAccountRevision = null;
      state.accountDraft = emptyAccountDraft();
      state.notice = null;
      render();
    } else if (accountAction === "cancel") {
      state.accountMode = "browse";
      state.editingAccountRevision = null;
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
      case "accrual-date": state.expenseDraft.accrualDate = target.value; break;
      case "planned-cost": state.expenseDraft.plannedCost = target.value; break;
      case "actual-cost": state.expenseDraft.actualCost = target.value; break;
      case "remaining-cost": state.expenseDraft.remainingCost = target.value; break;
      case "currency": state.expenseDraft.currency = target.value; break;
      case "expense-note": state.expenseDraft.note = target.value; break;
      case "account-id": state.accountDraft.accountId = target.value; break;
      case "account-name": state.accountDraft.name = target.value; break;
      case "account-description": state.accountDraft.description = target.value; break;
      case "account-default": state.accountDraft.isDefault = target.checked; break;
      default: break;
    }
  });

  host.addEventListener("change", (event) => {
    const target = event.target as HTMLSelectElement;
    if (target.name === "activity-id") state.expenseDraft.activityId = target.value || null;
    if (target.name === "wbs-id") state.expenseDraft.wbsId = target.value || null;
    if (target.name === "cost-account-id") state.expenseDraft.costAccountId = target.value || null;
    if (target.name === "parent-account-id") state.accountDraft.parentAccountId = target.value || null;
  });

  host.addEventListener("submit", (event) => {
    const form = event.target as HTMLFormElement;
    if (!form.matches("[data-expense-form]") && !form.matches("[data-cost-account-form]")) return;
    event.preventDefault();
    if (state.busy || !canWrite) return;
    const isExpense = form.matches("[data-expense-form]");
    void (async () => {
      state.busy = true;
      render();
      if (isExpense) {
        const editing = state.expenseMode === "edit";
        const result = await saveExpense(
          transport,
          context,
          state.expenseDraft,
          editing ? state.editingExpenseRevision ?? undefined : undefined,
        );
        state.busy = false;
        if (!result.ok) {
          state.notice = {
            kind: "error",
            message: `${say("Expense was not saved", "هزینه ذخیره نشد")} (${result.error.code})`,
          };
          if (result.error.code === "COST_REVISION_CONFLICT") {
            await reloadExpenses(state.expenseDraft.expenseId);
            return;
          }
          render();
          return;
        }
        state.notice = { kind: "ok", message: say("Expense saved.", "هزینه ذخیره شد.") };
        state.expenseMode = "browse";
        state.editingExpenseRevision = null;
        await reloadExpenses(result.data.expenseId);
        return;
      }
      const editing = state.accountMode === "edit";
      const result = await saveCostAccount(
        transport,
        context,
        state.accountDraft,
        editing ? state.editingAccountRevision ?? undefined : undefined,
      );
      state.busy = false;
      if (!result.ok) {
        state.notice = {
          kind: "error",
          message: `${say("Cost account was not saved", "حساب هزینه ذخیره نشد")} (${result.error.code})`,
        };
        if (result.error.code === "COST_REVISION_CONFLICT") {
          await reloadAccounts(state.accountDraft.accountId);
          return;
        }
        render();
        return;
      }
      state.notice = { kind: "ok", message: say("Cost account saved.", "حساب هزینه ذخیره شد.") };
      state.accountMode = "browse";
      state.editingAccountRevision = null;
      await reloadAccounts(result.data.accountId);
    })();
  });

  bindRegisterContextMenus(host, {
    locale,
    canWrite,
    menus: [
      {
        kind: "expense-register",
        label: { en: "Expense", fa: "هزینه" },
        rowSelector: "[data-expense-row]",
        rowIdAttribute: "data-expense-id",
        commands: [
          {
            command: "expense-edit",
            label: { en: "Edit Expense", fa: "ویرایش هزینه" },
            icon: "edit",
            control: "[data-expense-edit]",
            requiresWrite: true,
          },
          {
            command: "expense-delete",
            label: { en: "Delete Expense", fa: "حذف هزینه" },
            icon: "delete",
            control: "[data-expense-delete]",
            requiresWrite: true,
            separatorBefore: true,
          },
        ],
      },
      {
        kind: "cost-account-register",
        label: { en: "Cost Account", fa: "حساب هزینه" },
        rowSelector: "[data-cost-account-row]",
        rowIdAttribute: "data-cost-account-id",
        commands: [
          {
            command: "cost-account-edit",
            label: { en: "Edit Cost Account", fa: "ویرایش حساب هزینه" },
            icon: "edit",
            control: "[data-cost-account-edit]",
            requiresWrite: true,
          },
          {
            command: "cost-account-copy",
            label: { en: "Copy Cost Account", fa: "رونوشت حساب هزینه" },
            icon: "copy",
            control: "[data-cost-account-copy]",
            requiresWrite: true,
          },
          {
            command: "cost-account-default",
            label: { en: "Set as Default", fa: "تعیین به‌عنوان پیش‌فرض" },
            icon: "check",
            control: "[data-cost-account-default]",
            requiresWrite: true,
          },
          {
            command: "cost-account-delete",
            label: { en: "Delete Cost Account", fa: "حذف حساب هزینه" },
            icon: "delete",
            control: "[data-cost-account-delete]",
            requiresWrite: true,
            separatorBefore: true,
          },
        ],
      },
    ],
  });

  void reloadExpenses(null);
  void reloadAccounts(null);
}
