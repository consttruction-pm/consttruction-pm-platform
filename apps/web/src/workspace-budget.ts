import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

/**
 * Project budget register client.
 *
 * Original budget, approved changes and funding are distinct stored facts.
 * The server derives the current budget from original + approved changes and
 * keeps pending changes separate; this panel only displays what it reads and
 * never invents a currency total or an approval.
 */

export const BUDGET_API_VERSION = "p6-budget-api.v1";
export const BUDGET_CHANGE_STATUSES = ["pending", "approved", "rejected"] as const;
export const FUNDING_SOURCE_TYPES = ["internal", "external", "grant", "loan", "equity"] as const;

export type BudgetLineRecord = {
  budgetLineId: string;
  description: string;
  currency: string;
  originalAmount: string;
  costAccountId: string | null;
  periodId: string | null;
  revision: number;
};

export type BudgetChangeRecord = {
  changeId: string;
  budgetLineId: string;
  amount: string;
  reason: string;
  status: string;
  revision: number;
};

export type FundingSourceRecord = {
  fundingId: string;
  name: string;
  sourceType: string;
  currency: string;
  amount: string;
  periodId: string | null;
  revision: number;
};

export type CurrencyBudgetSummaryRecord = {
  currency: string;
  originalBudget: string;
  approvedChanges: string;
  currentBudget: string;
  pendingChanges: string;
  funding: string;
  fundingBalance: string;
};

export type BudgetLineInput = {
  budgetLineId: string;
  description: string;
  currency: string;
  originalAmount: string;
  costAccountId: string;
  periodId: string;
};

export type BudgetChangeInput = {
  changeId: string;
  amount: string;
  reason: string;
};

export type FundingSourceInput = {
  fundingId: string;
  name: string;
  sourceType: string;
  currency: string;
  amount: string;
  periodId: string;
};

export type BudgetPanelOptions = {
  transport: ApiTransport;
  context: ProjectContext;
  locale: string;
  canWrite: boolean;
  canApprove: boolean;
};

type BudgetPanelState = {
  status: "idle" | "loading" | "loaded" | "error";
  error: string | null;
  lines: readonly BudgetLineRecord[];
  funding: readonly FundingSourceRecord[];
  summary: readonly CurrencyBudgetSummaryRecord[];
  selectedLineId: string | null;
  changes: readonly BudgetChangeRecord[];
  history: readonly {
    revision: number;
    eventType: string;
    actorId: string;
    occurredAt: string;
    reason: string;
  }[];
  mode:
    | { kind: "none" }
    | { kind: "create-line" }
    | { kind: "edit-line"; line: BudgetLineRecord }
    | { kind: "create-change"; line: BudgetLineRecord }
    | { kind: "create-funding" }
    | { kind: "edit-funding"; funding: FundingSourceRecord };
  busy: boolean;
  notice: { kind: "ok" | "error"; message: string } | null;
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

function requiredText(value: unknown, code: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(code);
  return value.trim();
}

function nullableText(value: unknown, code: string): string | null {
  if (value === undefined || value === null) return null;
  if (typeof value !== "string") throw new Error(code);
  return value;
}

function revisionValue(value: unknown, code: string): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 1) throw new Error(code);
  return value;
}

export function isMoneyText(value: string, options: { allowNegative?: boolean; allowZero?: boolean } = {}): boolean {
  const pattern = options.allowNegative ? /^-?\d+(\.\d{2})?$/ : /^\d+(\.\d{2})?$/;
  if (!pattern.test(value.trim())) return false;
  const number = Number(value);
  if (!Number.isFinite(number)) return false;
  if (!options.allowZero && number === 0) return false;
  return true;
}

export function parseBudgetLine(value: unknown): BudgetLineRecord {
  if (!isRecord(value) || value.contract_version !== BUDGET_API_VERSION) {
    throw new Error("INVALID_BUDGET_LINE");
  }
  return {
    budgetLineId: requiredText(value.budget_line_id, "INVALID_BUDGET_LINE"),
    description: requiredText(value.description, "INVALID_BUDGET_LINE"),
    currency: requiredText(value.currency, "INVALID_BUDGET_LINE"),
    originalAmount: requiredText(value.original_amount, "INVALID_BUDGET_LINE"),
    costAccountId: nullableText(value.cost_account_id, "INVALID_BUDGET_LINE"),
    periodId: nullableText(value.period_id, "INVALID_BUDGET_LINE"),
    revision: revisionValue(value.revision, "INVALID_BUDGET_LINE"),
  };
}

export function parseBudgetChange(value: unknown): BudgetChangeRecord {
  if (!isRecord(value) || value.contract_version !== BUDGET_API_VERSION) {
    throw new Error("INVALID_BUDGET_CHANGE");
  }
  const status = requiredText(value.status, "INVALID_BUDGET_CHANGE");
  if (!(BUDGET_CHANGE_STATUSES as readonly string[]).includes(status)) {
    throw new Error("INVALID_BUDGET_CHANGE");
  }
  return {
    changeId: requiredText(value.change_id, "INVALID_BUDGET_CHANGE"),
    budgetLineId: requiredText(value.budget_line_id, "INVALID_BUDGET_CHANGE"),
    amount: requiredText(value.amount, "INVALID_BUDGET_CHANGE"),
    reason: requiredText(value.reason, "INVALID_BUDGET_CHANGE"),
    status,
    revision: revisionValue(value.revision, "INVALID_BUDGET_CHANGE"),
  };
}

export function parseFundingSource(value: unknown): FundingSourceRecord {
  if (!isRecord(value) || value.contract_version !== BUDGET_API_VERSION) {
    throw new Error("INVALID_BUDGET_FUNDING");
  }
  const sourceType = requiredText(value.source_type, "INVALID_BUDGET_FUNDING");
  if (!(FUNDING_SOURCE_TYPES as readonly string[]).includes(sourceType)) {
    throw new Error("INVALID_BUDGET_FUNDING");
  }
  return {
    fundingId: requiredText(value.funding_id, "INVALID_BUDGET_FUNDING"),
    name: requiredText(value.name, "INVALID_BUDGET_FUNDING"),
    sourceType,
    currency: requiredText(value.currency, "INVALID_BUDGET_FUNDING"),
    amount: requiredText(value.amount, "INVALID_BUDGET_FUNDING"),
    periodId: nullableText(value.period_id, "INVALID_BUDGET_FUNDING"),
    revision: revisionValue(value.revision, "INVALID_BUDGET_FUNDING"),
  };
}

export function parseBudgetSummary(value: unknown): CurrencyBudgetSummaryRecord {
  if (!isRecord(value)) throw new Error("INVALID_BUDGET_SUMMARY");
  return {
    currency: requiredText(value.currency, "INVALID_BUDGET_SUMMARY"),
    originalBudget: requiredText(value.original_budget, "INVALID_BUDGET_SUMMARY"),
    approvedChanges: requiredText(value.approved_changes, "INVALID_BUDGET_SUMMARY"),
    currentBudget: requiredText(value.current_budget, "INVALID_BUDGET_SUMMARY"),
    pendingChanges: requiredText(value.pending_changes, "INVALID_BUDGET_SUMMARY"),
    funding: requiredText(value.funding, "INVALID_BUDGET_SUMMARY"),
    fundingBalance: requiredText(value.funding_balance, "INVALID_BUDGET_SUMMARY"),
  };
}

export function buildBudgetLinePayload(input: BudgetLineInput): Record<string, unknown> {
  const payload = {
    budget_line_id: input.budgetLineId.trim(),
    description: input.description.trim(),
    currency: input.currency.trim().toUpperCase(),
    original_amount: input.originalAmount.trim(),
    cost_account_id: input.costAccountId.trim() || null,
    period_id: input.periodId.trim() || null,
  };
  if (!payload.budget_line_id || !payload.description) throw new Error("BUDGET_FIELDS_REQUIRED");
  if (!/^[A-Z]{3}$/.test(payload.currency)) throw new Error("INVALID_BUDGET_CURRENCY");
  if (!isMoneyText(payload.original_amount, { allowZero: true })) throw new Error("INVALID_BUDGET_ORIGINAL_AMOUNT");
  return payload;
}

export function buildBudgetChangePayload(input: BudgetChangeInput): Record<string, unknown> {
  const payload = {
    change_id: input.changeId.trim(),
    amount: input.amount.trim(),
    reason: input.reason.trim(),
  };
  if (!payload.change_id || !payload.reason) throw new Error("BUDGET_FIELDS_REQUIRED");
  if (!isMoneyText(payload.amount, { allowNegative: true })) throw new Error("INVALID_BUDGET_CHANGE_AMOUNT");
  return payload;
}

export function buildFundingPayload(input: FundingSourceInput): Record<string, unknown> {
  const payload = {
    funding_id: input.fundingId.trim(),
    name: input.name.trim(),
    source_type: input.sourceType,
    currency: input.currency.trim().toUpperCase(),
    amount: input.amount.trim(),
    period_id: input.periodId.trim() || null,
  };
  if (!payload.funding_id || !payload.name) throw new Error("BUDGET_FIELDS_REQUIRED");
  if (!(FUNDING_SOURCE_TYPES as readonly string[]).includes(payload.source_type)) {
    throw new Error("INVALID_BUDGET_FUNDING_TYPE");
  }
  if (!/^[A-Z]{3}$/.test(payload.currency)) throw new Error("INVALID_BUDGET_CURRENCY");
  if (!isMoneyText(payload.amount, { allowZero: true })) throw new Error("INVALID_BUDGET_FUNDING_AMOUNT");
  return payload;
}

function budgetPath(context: ProjectContext, suffix: string): string {
  return `/api/projects/${encodeURIComponent(context.project_id)}/budget/${suffix}`;
}

export async function loadBudgetLines(
  transport: ApiTransport,
  context: ProjectContext,
  filters: { currency?: string; costAccountId?: string; search?: string } = {},
): Promise<ApiResult<readonly BudgetLineRecord[]>> {
  const params = new URLSearchParams();
  if (filters.currency?.trim()) params.set("currency", filters.currency.trim());
  if (filters.costAccountId?.trim()) params.set("cost_account_id", filters.costAccountId.trim());
  if (filters.search?.trim()) params.set("search", filters.search.trim());
  const query = params.toString();
  const result = await transport.get<unknown>(budgetPath(context, `lines${query ? `?${query}` : ""}`), context);
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || payload.contract_version !== BUDGET_API_VERSION || !Array.isArray(payload.budget_lines)) {
    return localError("INVALID_BUDGET_LINE_LIST");
  }
  try {
    return { ok: true, data: payload.budget_lines.map((item) => parseBudgetLine(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_BUDGET_LINE_LIST");
  }
}

export async function loadBudgetChanges(
  transport: ApiTransport,
  context: ProjectContext,
  budgetLineId: string,
): Promise<ApiResult<readonly BudgetChangeRecord[]>> {
  const result = await transport.get<unknown>(
    budgetPath(context, `lines/${encodeURIComponent(budgetLineId)}/changes`),
    context,
  );
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || payload.contract_version !== BUDGET_API_VERSION || !Array.isArray(payload.changes)) {
    return localError("INVALID_BUDGET_CHANGE_LIST");
  }
  try {
    return { ok: true, data: payload.changes.map((item) => parseBudgetChange(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_BUDGET_CHANGE_LIST");
  }
}

export async function loadBudgetHistory(
  transport: ApiTransport,
  context: ProjectContext,
  budgetLineId: string,
): Promise<ApiResult<readonly BudgetPanelState["history"][number][]>> {
  const result = await transport.get<unknown>(
    budgetPath(context, `lines/${encodeURIComponent(budgetLineId)}/history`),
    context,
  );
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || payload.contract_version !== BUDGET_API_VERSION || !Array.isArray(payload.events)) {
    return localError("INVALID_BUDGET_HISTORY");
  }
  try {
    return {
      ok: true,
      data: payload.events.map((entry) => {
        if (!isRecord(entry)) throw new Error("INVALID_BUDGET_HISTORY");
        return {
          revision: revisionValue(entry.revision, "INVALID_BUDGET_HISTORY"),
          eventType: requiredText(entry.event_type, "INVALID_BUDGET_HISTORY"),
          actorId: requiredText(entry.actor_id, "INVALID_BUDGET_HISTORY"),
          occurredAt: requiredText(entry.occurred_at, "INVALID_BUDGET_HISTORY"),
          reason: typeof entry.reason === "string" ? entry.reason : "",
        };
      }),
    };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_BUDGET_HISTORY");
  }
}

export async function loadFundingSources(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<readonly FundingSourceRecord[]>> {
  const result = await transport.get<unknown>(budgetPath(context, "funding"), context);
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || payload.contract_version !== BUDGET_API_VERSION || !Array.isArray(payload.funding_sources)) {
    return localError("INVALID_BUDGET_FUNDING_LIST");
  }
  try {
    return { ok: true, data: payload.funding_sources.map((item) => parseFundingSource(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_BUDGET_FUNDING_LIST");
  }
}

export async function loadBudgetSummary(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<readonly CurrencyBudgetSummaryRecord[]>> {
  const result = await transport.get<unknown>(budgetPath(context, "summary"), context);
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || payload.contract_version !== BUDGET_API_VERSION || !Array.isArray(payload.currencies)) {
    return localError("INVALID_BUDGET_SUMMARY");
  }
  try {
    return { ok: true, data: payload.currencies.map((item) => parseBudgetSummary(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_BUDGET_SUMMARY");
  }
}

export async function createBudgetLine(
  transport: ApiTransport,
  context: ProjectContext,
  input: BudgetLineInput,
  idempotencyKey: string,
): Promise<ApiResult<BudgetLineRecord>> {
  let payload: Record<string, unknown>;
  try {
    payload = buildBudgetLinePayload(input);
  } catch (error) {
    return localError(error instanceof Error ? error.message : "BUDGET_FIELDS_REQUIRED");
  }
  const result = await transport.post<Record<string, unknown>, unknown>(budgetPath(context, "lines"), payload, context, idempotencyKey);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseBudgetLine(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_BUDGET_LINE");
  }
}

export async function updateBudgetLine(
  transport: ApiTransport,
  context: ProjectContext,
  input: BudgetLineInput,
  expectedRevision: number,
): Promise<ApiResult<BudgetLineRecord>> {
  if (!transport.patch) return localError("PATCH_NOT_SUPPORTED");
  let payload: Record<string, unknown>;
  try {
    payload = { ...buildBudgetLinePayload(input), expected_revision: expectedRevision };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "BUDGET_FIELDS_REQUIRED");
  }
  const result = await transport.patch<Record<string, unknown>, unknown>(
    budgetPath(context, `lines/${encodeURIComponent(input.budgetLineId.trim())}`),
    payload,
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseBudgetLine(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_BUDGET_LINE");
  }
}

export async function createBudgetChange(
  transport: ApiTransport,
  context: ProjectContext,
  budgetLineId: string,
  input: BudgetChangeInput,
): Promise<ApiResult<BudgetChangeRecord>> {
  let payload: Record<string, unknown>;
  try {
    payload = buildBudgetChangePayload(input);
  } catch (error) {
    return localError(error instanceof Error ? error.message : "BUDGET_FIELDS_REQUIRED");
  }
  const result = await transport.post<Record<string, unknown>, unknown>(
    budgetPath(context, `lines/${encodeURIComponent(budgetLineId)}/changes`),
    payload,
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseBudgetChange(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_BUDGET_CHANGE");
  }
}

export async function transitionBudgetChange(
  transport: ApiTransport,
  context: ProjectContext,
  changeId: string,
  status: "approved" | "rejected",
  expectedRevision: number,
  reason = "",
): Promise<ApiResult<BudgetChangeRecord>> {
  if (!(BUDGET_CHANGE_STATUSES as readonly string[]).includes(status)) {
    return localError("INVALID_BUDGET_CHANGE_STATUS");
  }
  const result = await transport.post<Record<string, unknown>, unknown>(
    budgetPath(context, `changes/${encodeURIComponent(changeId)}/status`),
    { status, expected_revision: expectedRevision, reason },
    context,
    `budget-change-${changeId}-${status}-${expectedRevision}`,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseBudgetChange(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_BUDGET_CHANGE");
  }
}

export async function createFundingSource(
  transport: ApiTransport,
  context: ProjectContext,
  input: FundingSourceInput,
  idempotencyKey: string,
): Promise<ApiResult<FundingSourceRecord>> {
  let payload: Record<string, unknown>;
  try {
    payload = buildFundingPayload(input);
  } catch (error) {
    return localError(error instanceof Error ? error.message : "BUDGET_FIELDS_REQUIRED");
  }
  const result = await transport.post<Record<string, unknown>, unknown>(budgetPath(context, "funding"), payload, context, idempotencyKey);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseFundingSource(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_BUDGET_FUNDING");
  }
}

export async function updateFundingSource(
  transport: ApiTransport,
  context: ProjectContext,
  input: FundingSourceInput,
  expectedRevision: number,
): Promise<ApiResult<FundingSourceRecord>> {
  if (!transport.patch) return localError("PATCH_NOT_SUPPORTED");
  let payload: Record<string, unknown>;
  try {
    payload = { ...buildFundingPayload(input), expected_revision: expectedRevision };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "BUDGET_FIELDS_REQUIRED");
  }
  const result = await transport.patch<Record<string, unknown>, unknown>(
    budgetPath(context, `funding/${encodeURIComponent(input.fundingId.trim())}`),
    payload,
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseFundingSource(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_BUDGET_FUNDING");
  }
}

function optionList(values: readonly string[], selected: string): string {
  return values
    .map((value) => `<option value="${escapeHtml(value)}"${value === selected ? " selected" : ""}>${escapeHtml(value)}</option>`)
    .join("");
}

export function mountWorkspaceBudgetPanel(host: HTMLElement, options: BudgetPanelOptions): void {
  const { transport, context, locale, canWrite, canApprove } = options;
  const t = (en: string, fa: string): string => text(locale, en, fa);
  const state: BudgetPanelState = {
    status: "idle",
    error: null,
    lines: [],
    funding: [],
    summary: [],
    selectedLineId: null,
    changes: [],
    history: [],
    mode: { kind: "none" },
    busy: false,
    notice: null,
  };

  const selectedLine = (): BudgetLineRecord | null =>
    state.lines.find((line) => line.budgetLineId === state.selectedLineId) ?? null;

  function renderSummary(): string {
    if (state.status === "loading") {
      return `<p class="cp-muted">${escapeHtml(t("Reading the stored budget…", "در حال خواندن بودجهٔ ذخیره‌شده…"))}</p>`;
    }
    if (state.status === "error") {
      return `<p class="cp-calendar-notice" role="alert">${escapeHtml(t("The budget could not be read", "خواندن بودجه ناموفق بود"))} (${escapeHtml(state.error ?? "ERROR")})</p>`;
    }
    if (!state.summary.length) {
      return `<p class="cp-register-notice">${escapeHtml(t("No budget or funding is stored for this project yet.", "هنوز هیچ بودجه یا تأمین مالی برای این پروژه ذخیره نشده است."))}</p>`;
    }
    return `<div class="cp-activity-detail-table-wrap"><table class="cp-activity-detail-table" data-budget-summary>
      <thead><tr>
        <th>${escapeHtml(t("Currency", "ارز"))}</th>
        <th>${escapeHtml(t("Original budget", "بودجهٔ اولیه"))}</th>
        <th>${escapeHtml(t("Approved changes", "تغییرات تأییدشده"))}</th>
        <th>${escapeHtml(t("Current budget", "بودجهٔ جاری"))}</th>
        <th>${escapeHtml(t("Pending changes", "تغییرات در انتظار"))}</th>
        <th>${escapeHtml(t("Funding", "تأمین مالی"))}</th>
        <th>${escapeHtml(t("Funding balance", "ماندهٔ تأمین مالی"))}</th>
      </tr></thead>
      <tbody>${state.summary.map((row) => `<tr data-budget-summary-currency="${escapeHtml(row.currency)}">
        <td>${escapeHtml(row.currency)}</td>
        <td>${escapeHtml(row.originalBudget)}</td>
        <td>${escapeHtml(row.approvedChanges)}</td>
        <td>${escapeHtml(row.currentBudget)}</td>
        <td>${escapeHtml(row.pendingChanges)}</td>
        <td>${escapeHtml(row.funding)}</td>
        <td>${escapeHtml(row.fundingBalance)}</td>
      </tr>`).join("")}</tbody>
    </table></div>
    <p class="cp-activity-detail-note">${escapeHtml(t("Current budget is the stored original amount plus approved changes only. Pending changes remain visible but are not added, and funding balance is current budget minus funding.", "بودجهٔ جاری فقط از مبلغ اولیهٔ ذخیره‌شده به‌علاوهٔ تغییرات تأییدشده ساخته می‌شود. تغییرات در انتظار دیده می‌شوند ولی اضافه نمی‌شوند و ماندهٔ تأمین مالی برابر بودجهٔ جاری منهای تأمین مالی است."))}</p>`;
  }

  function renderLineForm(line: BudgetLineRecord | null): string {
    const editing = line !== null;
    return `<form data-budget-line-form class="cp-expense-fields">
      <label>${escapeHtml(t("Budget line ID", "شناسهٔ ردیف بودجه"))}<input name="budget-line-id" value="${escapeHtml(line?.budgetLineId ?? "")}" ${editing ? "readonly" : ""} required></label>
      <label>${escapeHtml(t("Description", "شرح"))}<input name="budget-description" value="${escapeHtml(line?.description ?? "")}" required></label>
      <label>${escapeHtml(t("Currency", "ارز"))}<input name="budget-currency" value="${escapeHtml(line?.currency ?? "")}" maxlength="3" placeholder="USD" required></label>
      <label>${escapeHtml(t("Original amount", "مبلغ اولیه"))}<input name="budget-original" value="${escapeHtml(line?.originalAmount ?? "")}" inputmode="decimal" placeholder="0.00" required></label>
      <label>${escapeHtml(t("Cost account", "حساب هزینه"))}<input name="budget-cost-account" value="${escapeHtml(line?.costAccountId ?? "")}"></label>
      <label>${escapeHtml(t("Period", "دوره"))}<input name="budget-period" value="${escapeHtml(line?.periodId ?? "")}"></label>
      <div class="cp-calendar-panel-actions">
        <button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(editing ? t("Save budget line", "ذخیرهٔ ردیف بودجه") : t("Create budget line", "ایجاد ردیف بودجه"))}</button>
        <button type="button" data-budget-action="cancel">${escapeHtml(t("Cancel", "لغو"))}</button>
      </div>
    </form>`;
  }

  function renderChangeForm(line: BudgetLineRecord): string {
    return `<form data-budget-change-form class="cp-expense-fields">
      <p class="cp-register-notice">${escapeHtml(t(`Budget line ${line.budgetLineId} (${line.currency})`, `ردیف بودجهٔ ${line.budgetLineId} (${line.currency})`))}</p>
      <label>${escapeHtml(t("Change ID", "شناسهٔ تغییر"))}<input name="budget-change-id" required></label>
      <label>${escapeHtml(t("Amount", "مبلغ"))}<input name="budget-change-amount" inputmode="decimal" placeholder="-100.00" required></label>
      <label>${escapeHtml(t("Reason", "دلیل"))}<input name="budget-change-reason" required></label>
      <div class="cp-calendar-panel-actions">
        <button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(t("Submit change for approval", "ثبت تغییر برای تأیید"))}</button>
        <button type="button" data-budget-action="cancel">${escapeHtml(t("Cancel", "لغو"))}</button>
      </div>
      <p class="cp-activity-detail-note">${escapeHtml(t("A new change always starts pending. Only a project administrator can approve or reject it.", "هر تغییر جدید همیشه در وضعیت در انتظار ثبت می‌شود. تنها مدیر پروژه می‌تواند آن را تأیید یا رد کند."))}</p>
    </form>`;
  }

  function renderFundingForm(funding: FundingSourceRecord | null): string {
    const editing = funding !== null;
    return `<form data-budget-funding-form class="cp-expense-fields">
      <label>${escapeHtml(t("Funding ID", "شناسهٔ تأمین مالی"))}<input name="budget-funding-id" value="${escapeHtml(funding?.fundingId ?? "")}" ${editing ? "readonly" : ""} required></label>
      <label>${escapeHtml(t("Name", "نام"))}<input name="budget-funding-name" value="${escapeHtml(funding?.name ?? "")}" required></label>
      <label>${escapeHtml(t("Source type", "نوع منبع"))}<select name="budget-funding-type">${optionList(FUNDING_SOURCE_TYPES, funding?.sourceType ?? "internal")}</select></label>
      <label>${escapeHtml(t("Currency", "ارز"))}<input name="budget-funding-currency" value="${escapeHtml(funding?.currency ?? "")}" maxlength="3" placeholder="USD" required></label>
      <label>${escapeHtml(t("Amount", "مبلغ"))}<input name="budget-funding-amount" value="${escapeHtml(funding?.amount ?? "")}" inputmode="decimal" placeholder="0.00" required></label>
      <label>${escapeHtml(t("Period", "دوره"))}<input name="budget-funding-period" value="${escapeHtml(funding?.periodId ?? "")}"></label>
      <div class="cp-calendar-panel-actions">
        <button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(editing ? t("Save funding", "ذخیرهٔ تأمین مالی") : t("Create funding", "ایجاد تأمین مالی"))}</button>
        <button type="button" data-budget-action="cancel">${escapeHtml(t("Cancel", "لغو"))}</button>
      </div>
    </form>`;
  }

  function renderLines(): string {
    if (!state.lines.length) {
      return `<p class="cp-register-notice">${escapeHtml(t("No budget lines are stored for this project.", "هیچ ردیف بودجه‌ای برای این پروژه ذخیره نشده است."))}</p>`;
    }
    return `<div class="cp-activity-detail-table-wrap"><table class="cp-activity-detail-table" data-budget-lines>
      <thead><tr>
        <th>${escapeHtml(t("Budget line", "ردیف بودجه"))}</th>
        <th>${escapeHtml(t("Description", "شرح"))}</th>
        <th>${escapeHtml(t("Currency", "ارز"))}</th>
        <th>${escapeHtml(t("Original amount", "مبلغ اولیه"))}</th>
        <th>${escapeHtml(t("Cost account", "حساب هزینه"))}</th>
        <th>${escapeHtml(t("Revision", "ویرایش"))}</th>
        <th>${escapeHtml(t("Actions", "اقدام‌ها"))}</th>
      </tr></thead>
      <tbody>${state.lines.map((line) => `<tr data-budget-line="${escapeHtml(line.budgetLineId)}" class="${line.budgetLineId === state.selectedLineId ? "is-selected" : ""}">
        <td>${escapeHtml(line.budgetLineId)}</td>
        <td>${escapeHtml(line.description)}</td>
        <td>${escapeHtml(line.currency)}</td>
        <td>${escapeHtml(line.originalAmount)}</td>
        <td>${escapeHtml(line.costAccountId ?? "—")}</td>
        <td>R${line.revision}</td>
        <td>
          <button type="button" data-budget-action="select-line" data-budget-line-id="${escapeHtml(line.budgetLineId)}">${escapeHtml(t("Changes", "تغییرات"))}</button>
          ${canWrite ? `<button type="button" data-budget-action="edit-line" data-budget-line-id="${escapeHtml(line.budgetLineId)}" ${state.busy ? "disabled" : ""}>${escapeHtml(t("Edit", "ویرایش"))}</button>` : ""}
          ${canWrite ? `<button type="button" data-budget-action="new-change" data-budget-line-id="${escapeHtml(line.budgetLineId)}" ${state.busy ? "disabled" : ""}>${escapeHtml(t("Add change", "افزودن تغییر"))}</button>` : ""}
        </td>
      </tr>`).join("")}</tbody>
    </table></div>`;
  }

  function renderChanges(): string {
    const line = selectedLine();
    if (!line) return "";
    const changes = state.changes.length
      ? `<div class="cp-activity-detail-table-wrap"><table class="cp-activity-detail-table" data-budget-changes>
          <thead><tr><th>${escapeHtml(t("Change", "تغییر"))}</th><th>${escapeHtml(t("Amount", "مبلغ"))}</th><th>${escapeHtml(t("Reason", "دلیل"))}</th><th>${escapeHtml(t("Status", "وضعیت"))}</th><th>${escapeHtml(t("Revision", "ویرایش"))}</th><th>${escapeHtml(t("Decision", "تصمیم"))}</th></tr></thead>
          <tbody>${state.changes.map((change) => `<tr data-budget-change="${escapeHtml(change.changeId)}">
            <td>${escapeHtml(change.changeId)}</td>
            <td>${escapeHtml(change.amount)}</td>
            <td>${escapeHtml(change.reason)}</td>
            <td><span class="cp-budget-status" data-budget-change-status="${escapeHtml(change.status)}">${escapeHtml(change.status)}</span></td>
            <td>R${change.revision}</td>
            <td>${canApprove && change.status === "pending" ? `
              <button type="button" data-budget-action="approve" data-budget-change-id="${escapeHtml(change.changeId)}" data-budget-change-revision="${change.revision}">${escapeHtml(t("Approve", "تأیید"))}</button>
              <button type="button" data-budget-action="reject" data-budget-change-id="${escapeHtml(change.changeId)}" data-budget-change-revision="${change.revision}">${escapeHtml(t("Reject", "رد"))}</button>` : "—"}</td>
          </tr>`).join("")}</tbody></table></div>`
      : `<p class="cp-register-notice">${escapeHtml(t("No change is recorded on this budget line.", "هیچ تغییری روی این ردیف بودجه ثبت نشده است."))}</p>`;
    const history = state.history.length
      ? `<div class="cp-activity-detail-table-wrap"><table class="cp-activity-detail-table" data-budget-history>
          <thead><tr><th>${escapeHtml(t("Revision", "ویرایش"))}</th><th>${escapeHtml(t("Event", "رویداد"))}</th><th>${escapeHtml(t("Actor", "کاربر"))}</th><th>${escapeHtml(t("Occurred", "زمان"))}</th><th>${escapeHtml(t("Reason", "دلیل"))}</th></tr></thead>
          <tbody>${state.history.map((event) => `<tr><td>R${event.revision}</td><td>${escapeHtml(event.eventType)}</td><td>${escapeHtml(event.actorId)}</td><td>${escapeHtml(event.occurredAt)}</td><td>${escapeHtml(event.reason || "—")}</td></tr>`).join("")}</tbody>
        </table></div>`
      : "";
    return `<div data-budget-line-detail="${escapeHtml(line.budgetLineId)}">
      <div class="cp-register-toolbar"><strong>${escapeHtml(t(`Changes on ${line.budgetLineId}`, `تغییرات ${line.budgetLineId}`))}</strong><span>${escapeHtml(line.currency)}</span></div>
      ${changes}
      ${history}
      ${state.mode.kind === "create-change" ? renderChangeForm(line) : ""}
    </div>`;
  }

  function renderFunding(): string {
    const rows = state.funding.length
      ? `<div class="cp-activity-detail-table-wrap"><table class="cp-activity-detail-table" data-budget-funding>
          <thead><tr><th>${escapeHtml(t("Funding", "تأمین مالی"))}</th><th>${escapeHtml(t("Name", "نام"))}</th><th>${escapeHtml(t("Type", "نوع"))}</th><th>${escapeHtml(t("Currency", "ارز"))}</th><th>${escapeHtml(t("Amount", "مبلغ"))}</th><th>${escapeHtml(t("Period", "دوره"))}</th><th>${escapeHtml(t("Revision", "ویرایش"))}</th><th>${escapeHtml(t("Actions", "اقدام‌ها"))}</th></tr></thead>
          <tbody>${state.funding.map((item) => `<tr data-budget-funding-id="${escapeHtml(item.fundingId)}">
            <td>${escapeHtml(item.fundingId)}</td>
            <td>${escapeHtml(item.name)}</td>
            <td>${escapeHtml(item.sourceType)}</td>
            <td>${escapeHtml(item.currency)}</td>
            <td>${escapeHtml(item.amount)}</td>
            <td>${escapeHtml(item.periodId ?? "—")}</td>
            <td>R${item.revision}</td>
            <td>${canWrite ? `<button type="button" data-budget-action="edit-funding" data-budget-funding-id="${escapeHtml(item.fundingId)}" ${state.busy ? "disabled" : ""}>${escapeHtml(t("Edit", "ویرایش"))}</button>` : "—"}</td>
          </tr>`).join("")}</tbody></table></div>`
      : `<p class="cp-register-notice">${escapeHtml(t("No funding source is stored for this project.", "هیچ منبع تأمین مالی برای این پروژه ذخیره نشده است."))}</p>`;
    const form = state.mode.kind === "create-funding"
      ? renderFundingForm(null)
      : state.mode.kind === "edit-funding" ? renderFundingForm(state.mode.funding) : "";
    return `<div class="cp-register-toolbar"><strong>${escapeHtml(t("Funding Sources", "منابع تأمین مالی"))}</strong><div>${canWrite && state.mode.kind === "none" ? `<button type="button" data-budget-action="new-funding" ${state.busy ? "disabled" : ""}>${escapeHtml(t("New funding", "تأمین مالی جدید"))}</button>` : ""}</div></div>
      ${rows}${form}`;
  }

  function render(): void {
    const lineMode =
      state.mode.kind === "create-line" ? renderLineForm(null)
        : state.mode.kind === "edit-line" ? renderLineForm(state.mode.line) : "";
    host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(t("Project Budget", "بودجهٔ پروژه"))}</strong><div><button type="button" data-budget-action="refresh" ${state.busy ? "disabled" : ""}>${escapeHtml(t("Refresh", "به‌روزرسانی"))}</button>${canWrite && state.mode.kind === "none" ? `<button type="button" data-budget-action="new-line" ${state.busy ? "disabled" : ""}>${escapeHtml(t("New budget line", "ردیف بودجهٔ جدید"))}</button>` : ""}</div></div>
      <p class="cp-register-notice">${escapeHtml(t("All amounts on this panel are read from stored budget lines, changes, funding and the server's per-currency summary. The panel performs no financial calculation of its own.", "همهٔ مبالغ این بخش از ردیف‌های بودجه، تغییرات، تأمین مالی و خلاصهٔ ارزی سرور خوانده می‌شوند. این بخش خودش هیچ محاسبهٔ مالی انجام نمی‌دهد."))}</p>
      <section class="cp-cost-panel" data-budget-section="summary"><div class="cp-register-toolbar"><strong>${escapeHtml(t("Budget Summary", "خلاصهٔ بودجه"))}</strong><span>${escapeHtml(String(state.summary.length))}</span></div>${renderSummary()}</section>
      <section class="cp-cost-panel" data-budget-section="lines"><div class="cp-register-toolbar"><strong>${escapeHtml(t("Budget Lines", "ردیف‌های بودجه"))}</strong><span>${escapeHtml(String(state.lines.length))}</span></div>${lineMode}${renderLines()}${renderChanges()}</section>
      <section class="cp-cost-panel" data-budget-section="funding">${renderFunding()}</section>
      ${state.notice ? `<p class="cp-calendar-notice" data-budget-notice data-state="${state.notice.kind}" role="status">${escapeHtml(state.notice.message)}</p>` : ""}`;
  }

  async function loadSelected(lineId: string): Promise<void> {
    state.selectedLineId = lineId;
    const [changes, history] = await Promise.all([
      loadBudgetChanges(transport, context, lineId),
      loadBudgetHistory(transport, context, lineId),
    ]);
    if (changes.ok) state.changes = changes.data;
    else state.notice = { kind: "error", message: changes.error.code };
    if (history.ok) state.history = history.data;
    else state.notice = { kind: "error", message: history.error.code };
  }

  async function reload(): Promise<void> {
    state.status = "loading";
    state.busy = true;
    state.error = null;
    render();
    const [lines, funding, summary] = await Promise.all([
      loadBudgetLines(transport, context),
      loadFundingSources(transport, context),
      loadBudgetSummary(transport, context),
    ]);
    state.busy = false;
    state.status = "loaded";
    if (lines.ok) state.lines = lines.data;
    else {
      state.status = "error";
      state.error = lines.error.code;
    }
    if (funding.ok) state.funding = funding.data;
    if (summary.ok) state.summary = summary.data;
    else if (state.status !== "error") {
      state.status = "error";
      state.error = summary.error.code;
    }
    if (state.selectedLineId && !state.lines.some((line) => line.budgetLineId === state.selectedLineId)) {
      state.selectedLineId = null;
      state.changes = [];
      state.history = [];
    }
    if (state.selectedLineId) await loadSelected(state.selectedLineId);
    render();
  }

  async function submitLine(form: HTMLFormElement): Promise<void> {
    const data = new FormData(form);
    const input: BudgetLineInput = {
      budgetLineId: String(data.get("budget-line-id") ?? ""),
      description: String(data.get("budget-description") ?? ""),
      currency: String(data.get("budget-currency") ?? ""),
      originalAmount: String(data.get("budget-original") ?? ""),
      costAccountId: String(data.get("budget-cost-account") ?? ""),
      periodId: String(data.get("budget-period") ?? ""),
    };
    state.busy = true;
    render();
    const result = state.mode.kind === "edit-line"
      ? await updateBudgetLine(transport, context, input, state.mode.line.revision)
      : await createBudgetLine(transport, context, input, `budget-line-${input.budgetLineId.trim()}-${Date.now()}`);
    state.busy = false;
    if (!result.ok) {
      state.notice = { kind: "error", message: result.error.code };
    } else {
      state.notice = { kind: "ok", message: t("The budget line was saved.", "ردیف بودجه ذخیره شد.") };
      state.mode = { kind: "none" };
      await reload();
      return;
    }
    render();
  }

  async function submitChange(form: HTMLFormElement): Promise<void> {
    const line = selectedLine();
    if (!line) return;
    const data = new FormData(form);
    state.busy = true;
    render();
    const result = await createBudgetChange(transport, context, line.budgetLineId, {
      changeId: String(data.get("budget-change-id") ?? ""),
      amount: String(data.get("budget-change-amount") ?? ""),
      reason: String(data.get("budget-change-reason") ?? ""),
    });
    state.busy = false;
    if (!result.ok) state.notice = { kind: "error", message: result.error.code };
    else {
      state.notice = { kind: "ok", message: t("The change was submitted as pending.", "تغییر در وضعیت در انتظار ثبت شد.") };
      state.mode = { kind: "none" };
      await reload();
      return;
    }
    render();
  }

  async function submitFunding(form: HTMLFormElement): Promise<void> {
    const data = new FormData(form);
    const input: FundingSourceInput = {
      fundingId: String(data.get("budget-funding-id") ?? ""),
      name: String(data.get("budget-funding-name") ?? ""),
      sourceType: String(data.get("budget-funding-type") ?? ""),
      currency: String(data.get("budget-funding-currency") ?? ""),
      amount: String(data.get("budget-funding-amount") ?? ""),
      periodId: String(data.get("budget-funding-period") ?? ""),
    };
    state.busy = true;
    render();
    const result = state.mode.kind === "edit-funding"
      ? await updateFundingSource(transport, context, input, state.mode.funding.revision)
      : await createFundingSource(transport, context, input, `budget-funding-${input.fundingId.trim()}-${Date.now()}`);
    state.busy = false;
    if (!result.ok) state.notice = { kind: "error", message: result.error.code };
    else {
      state.notice = { kind: "ok", message: t("The funding source was saved.", "منبع تأمین مالی ذخیره شد.") };
      state.mode = { kind: "none" };
      await reload();
      return;
    }
    render();
  }

  async function decide(changeId: string, revision: number, status: "approved" | "rejected"): Promise<void> {
    state.busy = true;
    render();
    const result = await transitionBudgetChange(
      transport,
      context,
      changeId,
      status,
      revision,
      t("Decision recorded in the budget panel", "تصمیم در بخش بودجه ثبت شد"),
    );
    state.busy = false;
    if (!result.ok) state.notice = { kind: "error", message: result.error.code };
    else state.notice = { kind: "ok", message: t(`The change is now ${status}.`, `وضعیت تغییر اکنون ${status} است.`) };
    await reload();
  }

  host.addEventListener("click", (event) => {
    const target = (event.target as HTMLElement).closest<HTMLElement>("[data-budget-action]");
    if (!target) return;
    const action = target.dataset.budgetAction;
    const lineId = target.dataset.budgetLineId ?? "";
    if (action === "refresh") {
      void reload();
      return;
    }
    if (action === "cancel") {
      state.mode = { kind: "none" };
      state.notice = null;
      render();
      return;
    }
    if (action === "new-line") {
      state.mode = { kind: "create-line" };
      render();
      return;
    }
    if (action === "edit-line") {
      const line = state.lines.find((item) => item.budgetLineId === lineId);
      if (line) {
        state.mode = { kind: "edit-line", line };
        render();
      }
      return;
    }
    if (action === "select-line") {
      void loadSelected(lineId).then(render);
      return;
    }
    if (action === "new-change") {
      const line = state.lines.find((item) => item.budgetLineId === lineId);
      if (line) {
        state.selectedLineId = line.budgetLineId;
        async function start(): Promise<void> {
          await loadSelected(line!.budgetLineId);
          state.mode = { kind: "create-change", line: line! };
          render();
        }
        void start();
      }
      return;
    }
    if (action === "new-funding") {
      state.mode = { kind: "create-funding" };
      render();
      return;
    }
    if (action === "edit-funding") {
      const funding = state.funding.find((item) => item.fundingId === (target.dataset.budgetFundingId ?? ""));
      if (funding) {
        state.mode = { kind: "edit-funding", funding };
        render();
      }
      return;
    }
    if (action === "approve" || action === "reject") {
      const changeId = target.dataset.budgetChangeId ?? "";
      const revision = Number(target.dataset.budgetChangeRevision);
      if (changeId && Number.isSafeInteger(revision)) {
        void decide(changeId, revision, action === "approve" ? "approved" : "rejected");
      }
    }
  });

  host.addEventListener("submit", (event) => {
    const form = event.target as HTMLFormElement;
    if (!(form instanceof HTMLFormElement)) return;
    if (form.matches("[data-budget-line-form]")) {
      event.preventDefault();
      void submitLine(form);
      return;
    }
    if (form.matches("[data-budget-change-form]")) {
      event.preventDefault();
      void submitChange(form);
      return;
    }
    if (form.matches("[data-budget-funding-form]")) {
      event.preventDefault();
      void submitFunding(form);
    }
  });

  render();
  void reload();
}
