import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import { mountWorkspaceBudgetPanel } from "./workspace-budget.js";
import {
  loadCostAccounts,
  loadExpenses,
  type CostAccountRecord,
  type ExpenseRecord,
} from "./workspace-expenses.js";
import { translateUiString } from "./workspace-ui-translations.js";

export const FINANCIAL_PERIOD_API_VERSION = "p6-financial-period-api.v1";
export const BASELINE_API_VERSION = "p6-baseline-api.v1";
export const BASELINE_CAPTURE_API_VERSION = "p6-baseline-capture-api.v1";
export const BASELINE_ACTIVITY_API_VERSION = "p6-baseline-activity-api.v1";
export const EARNED_VALUE_API_VERSION = "p6-earned-value-read-model.v1";
export const SCHEDULE_SETTINGS_API_VERSION = "p6-project-schedule-settings-api.v1";

export const ETC_METHODS = ["REMAINING_COST", "PF_ONE", "PF_CPI", "PF_CPI_SPI", "USER_PF"] as const;
export type EtcMethod = (typeof ETC_METHODS)[number];

export const BASELINE_TYPES = ["PRIMARY", "SECONDARY", "TERTIARY", "USER_SELECTED"] as const;
export type BaselineType = (typeof BASELINE_TYPES)[number];

export const PERIOD_STATUSES = ["OPEN", "CLOSED"] as const;

export type FinancialPeriodRecord = {
  periodId: string;
  name: string;
  startDate: string;
  endDate: string;
  status: string;
};

export type BaselineRecord = {
  baselineId: string;
  name: string;
  baselineType: string;
  sourceRevision: number;
  createdAt: string;
};

export type BaselineCaptureInput = {
  baselineId: string;
  name: string;
  baselineType: BaselineType;
  notes: string;
  currency: string;
};

export type EarnedValueResult = {
  baselineId: string;
  dataDate: string;
  currency: string;
  pvMethod: string;
  plannedValue: string;
  earnedValue: string;
  actualCost: string;
  costVariance: string;
  scheduleVariance: string;
  costPerformanceIndex: string | null;
  schedulePerformanceIndex: string | null;
  etcMethod: string;
  budgetAtCompletion: string | null;
  estimateToComplete: string;
  estimateAtCompletion: string;
  varianceAtCompletion: string | null;
  performanceFactor: string | null;
};

export type EarnedValueInput = {
  baselineId: string;
  dataDate: string;
  currency: string;
  etcMethod: string;
  performanceFactor: string;
};

export type FinancialPeriodInput = {
  periodId: string;
  name: string;
  startDate: string;
  endDate: string;
  status: string;
};

export type CostPageOptions = {
  transport: ApiTransport;
  context: ProjectContext;
  locale: string;
  onNavigate?: (menu: "expenses" | "schedule") => void;
  /** Mirrors the server PROJECT_WRITE gate for the budget register. */
  canWrite: boolean;
  /** Mirrors the server project-admin approval gate for budget changes. */
  canApprove: boolean;
};

type CostState = {
  status: "idle" | "loading" | "loaded";
  expenses: readonly ExpenseRecord[];
  expensesError: string | null;
  accounts: readonly CostAccountRecord[];
  accountsError: string | null;
  periods: readonly FinancialPeriodRecord[];
  periodsStatus: "idle" | "loading" | "loaded" | "error";
  periodsError: string | null;
  baselines: readonly BaselineRecord[];
  baselinesStatus: "idle" | "loading" | "loaded" | "error";
  baselinesError: string | null;
  dataDate: string;
  baselineId: string;
  currency: string;
  etcMethod: EtcMethod;
  performanceFactor: string;
  measuring: boolean;
  measured: EarnedValueResult | null;
  measureError: string | null;
  periodDraft: FinancialPeriodInput;
  periodMode: "browse" | "create";
  captureMode: "browse" | "create";
  captureDraft: BaselineCaptureInput;
  capturing: boolean;
  busy: boolean;
  notice: { kind: "ok" | "error"; message: string } | null;
};

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

function say(locale: string, en: string, fa: string): string {
  const base = locale.split("-")[0];
  if (base === "fa") return fa;
  if (base === "de" || base === "zh") return translateUiString(locale, en) ?? en;
  return en;
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
  return value;
}

function optionalText(value: unknown, code: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string") throw new Error(code);
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function requiredDecimalText(value: unknown, code: string): string {
  if (value === null || value === undefined) throw new Error(code);
  if (typeof value !== "string" && typeof value !== "number") throw new Error(code);
  const trimmed = String(value).trim();
  if (!/^-?\d+(\.\d+)?$/.test(trimmed)) throw new Error(code);
  return trimmed;
}

function optionalDecimalText(value: unknown, code: string): string | null {
  if (value === null || value === undefined) return null;
  return requiredDecimalText(value, code);
}

function isIsoDate(value: string): boolean {
  if (!ISO_DATE.test(value)) return false;
  const [year, month, day] = value.split("-").map((part) => Number.parseInt(part, 10));
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return (
    parsed.getUTCFullYear() === year &&
    parsed.getUTCMonth() === month - 1 &&
    parsed.getUTCDate() === day
  );
}

function projectPath(context: ProjectContext, suffix: string): string {
  return `/api/projects/${encodeURIComponent(context.project_id)}${suffix}`;
}

export function parseFinancialPeriod(value: unknown): FinancialPeriodRecord {
  if (!isRecord(value)) throw new Error("INVALID_FINANCIAL_PERIOD_RECORD");
  if (value.contract_version !== FINANCIAL_PERIOD_API_VERSION) {
    throw new Error("INVALID_FINANCIAL_PERIOD_RESPONSE");
  }
  if (value.kind !== "p6_financial_period") throw new Error("INVALID_FINANCIAL_PERIOD_RESPONSE");
  const payload = value.financial_period;
  if (!isRecord(payload)) throw new Error("INVALID_FINANCIAL_PERIOD_RESPONSE");
  const periodId = requiredText(payload.period_id, "INVALID_FINANCIAL_PERIOD_RECORD");
  const name = requiredText(payload.name, "INVALID_FINANCIAL_PERIOD_RECORD");
  const startDate = requiredText(payload.start_date, "INVALID_FINANCIAL_PERIOD_RECORD");
  const endDate = requiredText(payload.end_date, "INVALID_FINANCIAL_PERIOD_RECORD");
  const status = requiredText(payload.status, "INVALID_FINANCIAL_PERIOD_RECORD");
  if (status !== "OPEN" && status !== "CLOSED") {
    throw new Error("INVALID_FINANCIAL_PERIOD_RECORD");
  }
  return { periodId, name, startDate, endDate, status };
}

export async function loadFinancialPeriods(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<readonly FinancialPeriodRecord[]>> {
  const result = await transport.get<unknown>(
    projectPath(context, "/p6/financial-periods"),
    context,
  );
  if (!result.ok) return result;
  const payload = result.data;
  if (
    !isRecord(payload) ||
    payload.contract_version !== FINANCIAL_PERIOD_API_VERSION ||
    !Array.isArray(payload.financial_periods)
  ) {
    return localError("INVALID_FINANCIAL_PERIOD_LIST");
  }
  try {
    return {
      ok: true,
      data: payload.financial_periods.map((item) => parseFinancialPeriod(item)),
    };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_FINANCIAL_PERIOD_LIST");
  }
}

export function buildFinancialPeriodPayload(input: FinancialPeriodInput): Record<string, unknown> {
  const periodId = input.periodId.trim();
  const name = input.name.trim();
  const startDate = input.startDate.trim();
  const endDate = input.endDate.trim();
  if (!periodId) throw new Error("PERIOD_ID_REQUIRED");
  if (!name) throw new Error("PERIOD_NAME_REQUIRED");
  if (!isIsoDate(startDate)) throw new Error("INVALID_PERIOD_START");
  if (!isIsoDate(endDate)) throw new Error("INVALID_PERIOD_END");
  if (endDate < startDate) throw new Error("PERIOD_END_BEFORE_START");
  if (input.status !== "OPEN" && input.status !== "CLOSED") {
    throw new Error("INVALID_PERIOD_STATUS");
  }
  return {
    period_id: periodId,
    name,
    start_date: startDate,
    end_date: endDate,
    status: input.status,
  };
}

export async function createFinancialPeriod(
  transport: ApiTransport,
  context: ProjectContext,
  input: FinancialPeriodInput,
): Promise<ApiResult<FinancialPeriodRecord>> {
  let payload: Record<string, unknown>;
  try {
    payload = buildFinancialPeriodPayload(input);
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_FINANCIAL_PERIOD");
  }
  const result = await transport.post<Record<string, unknown>, unknown>(
    projectPath(context, "/p6/financial-periods"),
    payload,
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseFinancialPeriod(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_FINANCIAL_PERIOD_RESPONSE");
  }
}

export function parseBaseline(value: unknown): BaselineRecord {
  if (!isRecord(value)) throw new Error("INVALID_BASELINE_RECORD");
  if (value.contract_version !== BASELINE_API_VERSION) throw new Error("INVALID_BASELINE_RESPONSE");
  if (value.kind !== "p6_baseline") throw new Error("INVALID_BASELINE_RESPONSE");
  return parseBaselineMetadata(value.baseline);
}

function parseBaselineMetadata(value: unknown): BaselineRecord {
  if (!isRecord(value)) throw new Error("INVALID_BASELINE_RESPONSE");
  const payload = value;
  const baselineId = requiredText(payload.baseline_id, "INVALID_BASELINE_RECORD");
  const name = requiredText(payload.name, "INVALID_BASELINE_RECORD");
  const baselineType = requiredText(payload.baseline_type, "INVALID_BASELINE_RECORD");
  const createdAt = requiredText(payload.created_at, "INVALID_BASELINE_RECORD");
  const sourceRevision = payload.source_revision;
  if (typeof sourceRevision !== "number" || !Number.isInteger(sourceRevision) || sourceRevision < 0) {
    throw new Error("INVALID_BASELINE_RECORD");
  }
  return { baselineId, name, baselineType, sourceRevision, createdAt };
}

export async function loadBaselines(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<readonly BaselineRecord[]>> {
  const result = await transport.get<unknown>(projectPath(context, "/p6/baselines"), context);
  if (!result.ok) return result;
  const payload = result.data;
  if (
    !isRecord(payload) ||
    payload.contract_version !== BASELINE_API_VERSION ||
    !Array.isArray(payload.baselines)
  ) {
    return localError("INVALID_BASELINE_LIST");
  }
  try {
    return { ok: true, data: payload.baselines.map((item) => parseBaseline(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_BASELINE_LIST");
  }
}

/** One stored baseline activity window, read from the baseline activity endpoint. */
export type BaselineActivityDate = {
  activityId: string;
  plannedStart: string;
  plannedFinish: string;
};

function baselineIsoDate(value: unknown, code: string): string {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value) || !Number.isFinite(Date.parse(value))) {
    throw new Error(code);
  }
  return value;
}

/**
 * Parses the stored baseline windows of one baseline. The browser only
 * projects the dates the server returned; it never derives a window.
 */
export function parseBaselineActivities(value: unknown): readonly BaselineActivityDate[] {
  if (!isRecord(value)) throw new Error("INVALID_BASELINE_ACTIVITY_RESPONSE");
  if (value.contract_version !== BASELINE_ACTIVITY_API_VERSION) throw new Error("INVALID_BASELINE_ACTIVITY_RESPONSE");
  if (value.kind !== "p6_baseline_activity_list" || !Array.isArray(value.activities)) {
    throw new Error("INVALID_BASELINE_ACTIVITY_RESPONSE");
  }
  const rows: BaselineActivityDate[] = [];
  for (const activity of value.activities) {
    if (!isRecord(activity) || typeof activity.activity_id !== "string" || !activity.activity_id) {
      throw new Error("INVALID_BASELINE_ACTIVITY_ROW");
    }
    const plannedStart = baselineIsoDate(activity.planned_start, "INVALID_BASELINE_ACTIVITY_ROW");
    const plannedFinish = baselineIsoDate(activity.planned_finish, "INVALID_BASELINE_ACTIVITY_ROW");
    if (Date.parse(plannedFinish) < Date.parse(plannedStart)) {
      throw new Error("INVALID_BASELINE_ACTIVITY_ROW");
    }
    rows.push({ activityId: activity.activity_id, plannedStart, plannedFinish });
  }
  return rows;
}

export async function loadBaselineActivityDates(
  transport: ApiTransport,
  context: ProjectContext,
  baselineId: string,
): Promise<ApiResult<readonly BaselineActivityDate[]>> {
  if (!baselineId) return localError("BASELINE_ID_REQUIRED");
  const result = await transport.get<unknown>(
    projectPath(context, `/p6/baselines/${encodeURIComponent(baselineId)}/activities`),
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseBaselineActivities(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_BASELINE_ACTIVITY_RESPONSE");
  }
}

export function parseScheduleDataDate(value: unknown): string | null {  if (!isRecord(value)) throw new Error("INVALID_SCHEDULE_SETTINGS_RECORD");
  if (value.contract_version !== SCHEDULE_SETTINGS_API_VERSION) {
    throw new Error("INVALID_SCHEDULE_SETTINGS_RESPONSE");
  }
  if (value.kind !== "project_schedule_settings") {
    throw new Error("INVALID_SCHEDULE_SETTINGS_RESPONSE");
  }
  if (!isRecord(value.schedule_options)) return null;
  const raw = value.schedule_options.data_date;
  if (raw === null || raw === undefined) return null;
  if (typeof raw !== "string" || !isIsoDate(raw)) {
    throw new Error("INVALID_SCHEDULE_DATA_DATE");
  }
  return raw;
}

export async function loadScheduleDataDate(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<string | null>> {
  const result = await transport.get<unknown>(
    projectPath(context, "/p6/schedule/settings"),
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseScheduleDataDate(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_SCHEDULE_SETTINGS_RESPONSE");
  }
}

export function parseEarnedValue(value: unknown): EarnedValueResult {
  if (!isRecord(value)) throw new Error("INVALID_EARNED_VALUE_RECORD");
  if (value.contract_version !== EARNED_VALUE_API_VERSION) {
    throw new Error("INVALID_EARNED_VALUE_RESPONSE");
  }
  if (value.kind !== "p6_earned_value_read_model") {
    throw new Error("INVALID_EARNED_VALUE_RESPONSE");
  }
  const earned = value.earned_value;
  if (!isRecord(earned)) throw new Error("INVALID_EARNED_VALUE_RESPONSE");
  return {
    baselineId: requiredText(value.baseline_id, "INVALID_EARNED_VALUE_RECORD"),
    dataDate: requiredText(value.data_date, "INVALID_EARNED_VALUE_RECORD"),
    currency: requiredText(value.currency, "INVALID_EARNED_VALUE_RECORD"),
    pvMethod: requiredText(value.pv_method, "INVALID_EARNED_VALUE_RECORD"),
    plannedValue: requiredDecimalText(earned.planned_value, "INVALID_EARNED_VALUE_RECORD"),
    earnedValue: requiredDecimalText(earned.earned_value, "INVALID_EARNED_VALUE_RECORD"),
    actualCost: requiredDecimalText(earned.actual_cost, "INVALID_EARNED_VALUE_RECORD"),
    costVariance: requiredDecimalText(earned.cost_variance, "INVALID_EARNED_VALUE_RECORD"),
    scheduleVariance: requiredDecimalText(earned.schedule_variance, "INVALID_EARNED_VALUE_RECORD"),
    costPerformanceIndex: optionalDecimalText(
      earned.cost_performance_index,
      "INVALID_EARNED_VALUE_RECORD",
    ),
    schedulePerformanceIndex: optionalDecimalText(
      earned.schedule_performance_index,
      "INVALID_EARNED_VALUE_RECORD",
    ),
    etcMethod: requiredText(earned.etc_method, "INVALID_EARNED_VALUE_RECORD"),
    budgetAtCompletion: optionalDecimalText(
      earned.budget_at_completion,
      "INVALID_EARNED_VALUE_RECORD",
    ),
    estimateToComplete: requiredDecimalText(
      earned.estimate_to_complete,
      "INVALID_EARNED_VALUE_RECORD",
    ),
    estimateAtCompletion: requiredDecimalText(
      earned.estimate_at_completion,
      "INVALID_EARNED_VALUE_RECORD",
    ),
    varianceAtCompletion: optionalDecimalText(
      earned.variance_at_completion,
      "INVALID_EARNED_VALUE_RECORD",
    ),
    performanceFactor: optionalDecimalText(
      earned.performance_factor,
      "INVALID_EARNED_VALUE_RECORD",
    ),
  };
}

export function buildEarnedValuePayload(input: EarnedValueInput): Record<string, unknown> {
  const baselineId = input.baselineId.trim();
  const dataDate = input.dataDate.trim();
  const currency = input.currency.trim();
  if (!baselineId) throw new Error("BASELINE_REQUIRED");
  if (!dataDate) throw new Error("DATA_DATE_REQUIRED");
  if (!isIsoDate(dataDate)) throw new Error("INVALID_DATA_DATE");
  if (!currency) throw new Error("CURRENCY_REQUIRED");
  if (!ETC_METHODS.includes(input.etcMethod as EtcMethod)) {
    throw new Error("INVALID_ETC_METHOD");
  }
  const payload: Record<string, unknown> = {
    contract_version: EARNED_VALUE_API_VERSION,
    baseline_id: baselineId,
    data_date: dataDate,
    currency,
    etc_method: input.etcMethod,
  };
  if (input.etcMethod === "USER_PF") {
    const factor = input.performanceFactor.trim();
    if (!factor) throw new Error("PERFORMANCE_FACTOR_REQUIRED");
    if (!/^\d+(\.\d+)?$/.test(factor) || Number(factor) <= 0) {
      throw new Error("INVALID_PERFORMANCE_FACTOR");
    }
    payload.performance_factor = factor;
  }
  return payload;
}

export async function measureEarnedValue(
  transport: ApiTransport,
  context: ProjectContext,
  input: EarnedValueInput,
): Promise<ApiResult<EarnedValueResult>> {
  let payload: Record<string, unknown>;
  try {
    payload = buildEarnedValuePayload(input);
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_EARNED_VALUE_REQUEST");
  }
  const result = await transport.post<Record<string, unknown>, unknown>(
    projectPath(context, "/p6/earned-value"),
    payload,
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseEarnedValue(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_EARNED_VALUE_RESPONSE");
  }
}

function emptyPeriodDraft(): FinancialPeriodInput {
  return { periodId: "", name: "", startDate: "", endDate: "", status: "OPEN" };
}

function emptyCaptureDraft(): BaselineCaptureInput {
  return { baselineId: "", name: "", baselineType: "PRIMARY", notes: "", currency: "" };
}

export function buildBaselineCapturePayload(
  input: BaselineCaptureInput,
  expectedRevision: number,
): Record<string, unknown> {
  const baselineId = input.baselineId.trim();
  const name = input.name.trim();
  if (!baselineId) throw new Error("BASELINE_ID_REQUIRED");
  if (!name) throw new Error("BASELINE_NAME_REQUIRED");
  if (!BASELINE_TYPES.includes(input.baselineType)) throw new Error("INVALID_BASELINE_TYPE");
  if (!Number.isInteger(expectedRevision) || expectedRevision < 0) {
    throw new Error("INVALID_EXPECTED_REVISION");
  }
  const payload: Record<string, unknown> = {
    contract_version: BASELINE_CAPTURE_API_VERSION,
    expected_revision: expectedRevision,
    baseline_id: baselineId,
    name,
    baseline_type: input.baselineType,
  };
  const notes = input.notes.trim();
  if (notes) payload.notes = notes;
  const currency = input.currency.trim();
  if (currency) payload.currency = currency;
  return payload;
}

export async function captureBaseline(
  transport: ApiTransport,
  context: ProjectContext,
  input: BaselineCaptureInput,
): Promise<ApiResult<BaselineRecord>> {
  let payload: Record<string, unknown>;
  try {
    payload = buildBaselineCapturePayload(input, context.revision);
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_BASELINE_CAPTURE");
  }
  const result = await transport.post<Record<string, unknown>, unknown>(
    projectPath(context, "/p6/baselines/capture"),
    payload,
    context,
  );
  if (!result.ok) return result;
  try {
    const value = result.data;
    if (
      !isRecord(value) ||
      value.contract_version !== BASELINE_CAPTURE_API_VERSION ||
      value.kind !== "p6_baseline_capture"
    ) {
      throw new Error("INVALID_BASELINE_CAPTURE_RESPONSE");
    }
    return { ok: true, data: parseBaselineMetadata(value.baseline) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_BASELINE_CAPTURE_RESPONSE");
  }
}

/** Read-only Cost overview bound to the authoritative cost and EVM read models. */
export function mountWorkspaceCostPage(host: HTMLElement, options: CostPageOptions): void {
  if (host.dataset.costMounted === "true") return;
  host.dataset.costMounted = "true";

  const { transport, context, locale, onNavigate, canWrite, canApprove } = options;
  const state: CostState = {
    status: "idle",
    expenses: [],
    expensesError: null,
    accounts: [],
    accountsError: null,
    periods: [],
    periodsStatus: "idle",
    periodsError: null,
    baselines: [],
    baselinesStatus: "idle",
    baselinesError: null,
    dataDate: "",
    baselineId: "",
    currency: "",
    etcMethod: "REMAINING_COST",
    performanceFactor: "",
    measuring: false,
    measured: null,
    measureError: null,
    periodDraft: emptyPeriodDraft(),
    periodMode: "browse",
    captureMode: "browse",
    captureDraft: emptyCaptureDraft(),
    capturing: false,
    busy: false,
    notice: null,
  };

  const t = (en: string, fa: string): string => say(locale, en, fa);

  function currencyOptions(): string[] {
    return [...new Set(state.expenses.map((item) => item.currency).filter((value): value is string => Boolean(value)))].sort();
  }

  function selectedBaseline(): BaselineRecord | null {
    return state.baselines.find((item) => item.baselineId === state.baselineId) ?? null;
  }

  function renderExpenses(): string {
    if (state.status === "loading") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(t("Reading stored expenses…", "در حال خواندن هزینه‌های ذخیره‌شده…"))}</div>`;
    }
    if (state.expensesError) {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(t("Expenses could not be read", "خواندن هزینه‌ها ناموفق بود"))} (${escapeHtml(state.expensesError)})</div>`;
    }
    if (!state.expenses.length) {
      return `<div class="cp-calendar-empty">${escapeHtml(t("No expenses are stored for this project.", "هیچ هزینه‌ای برای این پروژه ذخیره نشده است."))}</div>`;
    }
    const rows = state.expenses.map((item) => `<tr><td><strong>${escapeHtml(item.expenseId)}</strong></td><td>${escapeHtml(item.name)}</td><td>${escapeHtml(item.category)}</td><td>${escapeHtml(item.activityId ?? "—")}</td><td>${escapeHtml(item.expenseDate ?? "—")}</td><td>${escapeHtml(item.plannedCost ?? "—")}</td><td>${escapeHtml(item.actualCost ?? "—")}</td><td>${escapeHtml(item.remainingCost ?? "—")}</td><td>${escapeHtml(item.currency ?? "—")}</td></tr>`).join("");
    return `<div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(t("Expense ID", "شناسه هزینه"))}</th><th>${escapeHtml(t("Name", "نام"))}</th><th>${escapeHtml(t("Category", "دسته"))}</th><th>${escapeHtml(t("Activity", "فعالیت"))}</th><th>${escapeHtml(t("Expense Date", "تاریخ هزینه"))}</th><th>${escapeHtml(t("Planned", "برنامه‌ای"))}</th><th>${escapeHtml(t("Actual", "واقعی"))}</th><th>${escapeHtml(t("Remaining", "باقی‌مانده"))}</th><th>${escapeHtml(t("Currency", "ارز"))}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function renderAccounts(): string {
    if (state.status === "loading") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(t("Reading cost accounts…", "در حال خواندن حساب‌های هزینه…"))}</div>`;
    }
    if (state.accountsError) {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(t("Cost accounts could not be read", "خواندن حساب‌های هزینه ناموفق بود"))} (${escapeHtml(state.accountsError)})</div>`;
    }
    if (!state.accounts.length) {
      return `<div class="cp-calendar-empty">${escapeHtml(t("No cost accounts are stored for this project.", "هیچ حساب هزینه‌ای برای این پروژه ذخیره نشده است."))}</div>`;
    }
    const rows = state.accounts.map((item) => `<tr><td><strong>${escapeHtml(item.accountId)}</strong></td><td>${escapeHtml(item.name)}</td><td>${escapeHtml(item.parentAccountId ?? "—")}</td><td>${escapeHtml(item.description ?? "—")}</td></tr>`).join("");
    return `<div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(t("Account ID", "شناسه حساب"))}</th><th>${escapeHtml(t("Account Name", "نام حساب"))}</th><th>${escapeHtml(t("Parent Account", "حساب والد"))}</th><th>${escapeHtml(t("Description", "شرح"))}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function renderPeriodForm(): string {
    const draft = state.periodDraft;
    return `<form data-cost-period-form class="cp-expense-fields">
      <label>${escapeHtml(t("Period ID", "شناسه دوره"))}<input name="period-id" value="${escapeHtml(draft.periodId)}" required></label>
      <label>${escapeHtml(t("Period Name", "نام دوره"))}<input name="period-name" value="${escapeHtml(draft.name)}" required></label>
      <label>${escapeHtml(t("Start Date", "تاریخ شروع"))}<input name="period-start" type="date" value="${escapeHtml(draft.startDate)}" required></label>
      <label>${escapeHtml(t("End Date", "تاریخ پایان"))}<input name="period-end" type="date" value="${escapeHtml(draft.endDate)}" required></label>
      <label>${escapeHtml(t("Status", "وضعیت"))}<select name="period-status">${PERIOD_STATUSES.map((status) => `<option value="${status}" ${draft.status === status ? "selected" : ""}>${escapeHtml(status === "OPEN" ? t("Open", "باز") : t("Closed", "بسته"))}</option>`).join("")}</select></label>
      <div class="cp-calendar-panel-actions"><button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(t("Create financial period", "ایجاد دورهٔ مالی"))}</button><button type="button" data-cost-period-action="cancel">${escapeHtml(t("Cancel", "لغو"))}</button></div>
    </form>`;
  }

  function renderPeriods(): string {
    if (state.periodsStatus === "loading") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(t("Reading financial periods…", "در حال خواندن دوره‌های مالی…"))}</div>`;
    }
    if (state.periodsError) {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(t("Financial periods could not be read", "خواندن دوره‌های مالی ناموفق بود"))} (${escapeHtml(state.periodsError)})</div>`;
    }
    if (state.periodMode === "create") return renderPeriodForm();
    if (!state.periods.length) {
      return `<div class="cp-calendar-empty">${escapeHtml(t("No financial periods are stored for this project.", "هیچ دورهٔ مالی برای این پروژه ذخیره نشده است."))}</div>`;
    }
    const rows = state.periods.map((item) => `<tr><td><strong>${escapeHtml(item.periodId)}</strong></td><td>${escapeHtml(item.name)}</td><td>${escapeHtml(item.startDate)}</td><td>${escapeHtml(item.endDate)}</td><td>${escapeHtml(item.status)}</td></tr>`).join("");
    return `<div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(t("Period ID", "شناسه دوره"))}</th><th>${escapeHtml(t("Period Name", "نام دوره"))}</th><th>${escapeHtml(t("Start Date", "تاریخ شروع"))}</th><th>${escapeHtml(t("End Date", "تاریخ پایان"))}</th><th>${escapeHtml(t("Status", "وضعیت"))}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function renderEarnedValue(): string {
    const measured = state.measured;
    let result = "";
    if (state.measureError) {
      result = `<div class="cp-calendar-notice" data-cost-evm-notice data-state="error" role="alert">${escapeHtml(t("Earned value was not measured", "ارزش کسب‌شده محاسبه نشد"))} (${escapeHtml(state.measureError)})</div>`;
    } else if (measured) {
      const cell = (label: string, value: string | null): string => `<label>${escapeHtml(label)}<input readonly value="${escapeHtml(value ?? t("Not available", "در دسترس نیست"))}"></label>`;
      result = `<div class="cp-expense-fields" data-cost-evm-result>
        ${cell(t("Baseline", "مبنا"), measured.baselineId)}
        ${cell(t("Data Date", "تاریخ داده"), measured.dataDate)}
        ${cell(t("Currency", "ارز"), measured.currency)}
        ${cell(t("Planned Value", "ارزش برنامه‌ای"), measured.plannedValue)}
        ${cell(t("Earned Value", "ارزش کسب‌شده"), measured.earnedValue)}
        ${cell(t("Actual Cost", "هزینهٔ واقعی"), measured.actualCost)}
        ${cell(t("Cost Variance", "انحراف هزینه"), measured.costVariance)}
        ${cell(t("Schedule Variance", "انحراف زمان‌بندی"), measured.scheduleVariance)}
        ${cell(t("Cost Performance Index", "شاخص عملکرد هزینه"), measured.costPerformanceIndex)}
        ${cell(t("Schedule Performance Index", "شاخص عملکرد زمان‌بندی"), measured.schedulePerformanceIndex)}
        ${cell(t("Budget at Completion", "بودجه در تکمیل"), measured.budgetAtCompletion)}
        ${cell(t("Estimate to Complete", "برآورد تا تکمیل"), measured.estimateToComplete)}
        ${cell(t("Estimate at Completion", "برآورد در تکمیل"), measured.estimateAtCompletion)}
        ${cell(t("Variance at Completion", "انحراف در تکمیل"), measured.varianceAtCompletion)}
        ${cell(t("ETC Method", "روش برآورد تا تکمیل"), measured.etcMethod)}
        ${cell(t("Performance Factor", "ضریب عملکرد"), measured.performanceFactor)}
        ${cell(t("Planned Value Method", "روش ارزش برنامه‌ای"), measured.pvMethod)}
      </div>`;
    }
    const baselineSelect = state.baselines.length
      ? `<select name="evm-baseline">${state.baselines.map((item) => `<option value="${escapeHtml(item.baselineId)}" ${item.baselineId === state.baselineId ? "selected" : ""}>${escapeHtml(`${item.baselineId} — ${item.name}`)}</option>`).join("")}</select>`
      : `<span class="cp-muted">${escapeHtml(t("No baseline is stored.", "هیچ مبنایی ذخیره نشده است."))}</span>`;
    const currencies = currencyOptions();
    const capturePanel = !canWrite
      ? ""
      : state.captureMode === "create"
        ? `<form data-cost-capture-form class="cp-expense-fields">
      <label>${escapeHtml(t("Baseline ID", "شناسه مبنا"))}<input name="capture-baseline-id" value="${escapeHtml(state.captureDraft.baselineId)}" required></label>
      <label>${escapeHtml(t("Baseline Name", "نام مبنا"))}<input name="capture-name" value="${escapeHtml(state.captureDraft.name)}" required></label>
      <label>${escapeHtml(t("Baseline Type", "نوع مبنا"))}<select name="capture-type">${BASELINE_TYPES.map((type) => `<option value="${type}" ${state.captureDraft.baselineType === type ? "selected" : ""}>${type}</option>`).join("")}</select></label>
      <label>${escapeHtml(t("Currency", "ارز"))}<input name="capture-currency" value="${escapeHtml(state.captureDraft.currency)}" list="cp-cost-currencies" placeholder="${escapeHtml(currencies[0] ?? "")}"></label>
      <label>${escapeHtml(t("Notes", "یادداشت"))}<input name="capture-notes" value="${escapeHtml(state.captureDraft.notes)}"></label>
      <div class="cp-calendar-panel-actions"><button type="submit" ${state.capturing ? "disabled" : ""}>${escapeHtml(t("Capture current schedule", "ثبت زمان‌بندی جاری"))}</button><button type="button" data-cost-capture-action="cancel" ${state.capturing ? "disabled" : ""}>${escapeHtml(t("Cancel", "انصراف"))}</button></div>
    </form>`
        : `<div class="cp-register-toolbar"><span class="cp-muted">${escapeHtml(t("Capture the calculated schedule as an immutable baseline.", "زمان‌بندی محاسبه‌شده را به‌عنوان یک مبنای تغییرناپذیر ثبت کنید."))}</span><button type="button" data-cost-capture-action="new" ${state.busy || state.capturing ? "disabled" : ""}>${escapeHtml(t("Capture baseline", "ثبت مبنا"))}</button></div>`;
    const canMeasure = state.baselines.length > 0 && !state.measuring;
    const datalist = currencies.length
      ? `<datalist id="cp-cost-currencies">${currencies.map((currency) => `<option value="${escapeHtml(currency)}"></option>`).join("")}</datalist>`
      : "";
    return `<form data-cost-evm-form class="cp-expense-fields">
      <label>${escapeHtml(t("Baseline", "مبنا"))}${baselineSelect}</label>
      <label>${escapeHtml(t("Data Date", "تاریخ داده"))}<input name="evm-data-date" type="date" value="${escapeHtml(state.dataDate)}" required></label>
      <label>${escapeHtml(t("Currency", "ارز"))}<input name="evm-currency" value="${escapeHtml(state.currency)}" list="cp-cost-currencies" placeholder="${escapeHtml(currencies[0] ?? "")}" required></label>
      <label>${escapeHtml(t("ETC Method", "روش برآورد تا تکمیل"))}<select name="evm-etc-method">${ETC_METHODS.map((method) => `<option value="${method}" ${state.etcMethod === method ? "selected" : ""}>${escapeHtml(method)}</option>`).join("")}</select></label>
      <label>${escapeHtml(t("Performance Factor", "ضریب عملکرد"))}<input name="evm-performance-factor" value="${escapeHtml(state.performanceFactor)}" ${state.etcMethod === "USER_PF" ? "required" : "disabled"} placeholder="${escapeHtml(t("Required for USER_PF", "برای USER_PF لازم است"))}"></label>
      <div class="cp-calendar-panel-actions"><button type="submit" ${canMeasure ? "" : "disabled"}>${escapeHtml(t("Measure earned value", "محاسبهٔ ارزش کسب‌شده"))}</button></div>
      ${datalist}
    </form>
    ${capturePanel}
    ${state.baselinesStatus === "loading" ? `<p class="cp-muted">${escapeHtml(t("Reading baselines…", "در حال خواندن مبناها…"))}</p>` : ""}
    ${state.baselinesError ? `<p class="cp-calendar-notice" role="alert">${escapeHtml(t("Baselines could not be read", "خواندن مبناها ناموفق بود"))} (${escapeHtml(state.baselinesError)})</p>` : ""}
    ${!state.baselinesStatus.match(/^(idle|loading)$/) && !state.baselines.length ? `<p class="cp-register-notice">${escapeHtml(t("Earned-value measurement needs a stored baseline with baseline activities. This project has none, so no values are computed or displayed.", "محاسبهٔ ارزش کسب‌شده به یک مبنای ذخیره‌شده با فعالیت‌های مبنا نیاز دارد. این پروژه هیچ مبنایی ندارد؛ بنابراین هیچ مقداری محاسبه یا نمایش داده نمی‌شود."))}</p>` : ""}
    ${result}`;
  }

  function render(): void {
    const baseline = selectedBaseline();
    host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(t("Cost Overview", "نمای کلی هزینه"))}</strong><div><button type="button" data-cost-action="refresh" ${state.busy ? "disabled" : ""}>${escapeHtml(t("Refresh", "به‌روزرسانی"))}</button><button type="button" data-cost-action="expenses">${escapeHtml(t("Expenses register", "فهرست هزینه‌ها"))}</button><button type="button" data-cost-action="schedule">${escapeHtml(t("Schedule", "زمان‌بندی"))}</button></div></div>
      <p class="cp-register-notice">${escapeHtml(t("Every amount on this page is read from stored expenses, cost accounts, financial periods, baselines and the shared earned-value read model. This page performs no financial or earned-value calculation itself.", "همهٔ مبالغ این صفحه از هزینه‌ها، حساب‌های هزینه، دوره‌های مالی، مبناها و مدل خواندن مشترک ارزش کسب‌شده خوانده می‌شوند. این صفحه خودش هیچ محاسبهٔ مالی یا ارزش کسب‌شده انجام نمی‌دهد."))}</p>
      <section id="cp-cost-overview" class="cp-cost-panel" data-cost-section="earned-value">
        <div class="cp-register-toolbar"><strong>${escapeHtml(t("Earned Value", "ارزش کسب‌شده"))}</strong><span>${escapeHtml(baseline ? `${baseline.baselineId} — ${baseline.name}` : t("No baseline", "بدون مبنا"))}</span></div>
        ${renderEarnedValue()}
      </section>
      <section id="cp-cost-registers" class="cp-cost-panel" data-cost-section="expenses">
        <div class="cp-register-toolbar"><strong>${escapeHtml(t("Stored Expenses", "هزینه‌های ذخیره‌شده"))}</strong><span>${escapeHtml(String(state.expenses.length))}</span></div>
        ${renderExpenses()}
      </section>
      <section class="cp-cost-panel" data-cost-section="accounts">
        <div class="cp-register-toolbar"><strong>${escapeHtml(t("Cost Accounts", "حساب‌های هزینه"))}</strong><span>${escapeHtml(String(state.accounts.length))}</span></div>
        ${renderAccounts()}
      </section>
      <section class="cp-cost-panel" data-cost-section="periods">
        <div class="cp-register-toolbar"><strong>${escapeHtml(t("Financial Periods", "دوره‌های مالی"))}</strong><div>${state.periodMode === "create" ? "" : `<button type="button" data-cost-period-action="new" ${state.busy ? "disabled" : ""}>${escapeHtml(t("New Financial Period", "دورهٔ مالی جدید"))}</button>`}</div></div>
        ${renderPeriods()}
      </section>
      <section class="cp-cost-panel" data-cost-section="budget">
        <div data-budget-panel></div>
      </section>
      ${state.notice ? `<p class="cp-calendar-notice" data-cost-notice data-state="${state.notice.kind}" role="status">${escapeHtml(state.notice.message)}</p>` : ""}`;
    const budgetHost = host.querySelector<HTMLElement>("[data-budget-panel]");
    if (budgetHost) {
      mountWorkspaceBudgetPanel(budgetHost, {
        transport,
        context,
        locale,
        canWrite,
        canApprove,
      });
    }
  }

  function readEarnedValueInput(form: HTMLFormElement): EarnedValueInput {
    const data = new FormData(form);
    return {
      baselineId: String(data.get("evm-baseline") ?? state.baselineId),
      dataDate: String(data.get("evm-data-date") ?? ""),
      currency: String(data.get("evm-currency") ?? ""),
      etcMethod: String(data.get("evm-etc-method") ?? "REMAINING_COST"),
      performanceFactor: String(data.get("evm-performance-factor") ?? ""),
    };
  }

  function readPeriodInput(form: HTMLFormElement): FinancialPeriodInput {
    const data = new FormData(form);
    return {
      periodId: String(data.get("period-id") ?? ""),
      name: String(data.get("period-name") ?? ""),
      startDate: String(data.get("period-start") ?? ""),
      endDate: String(data.get("period-end") ?? ""),
      status: String(data.get("period-status") ?? "OPEN"),
    };
  }

  function readCaptureInput(form: HTMLFormElement): BaselineCaptureInput {
    const data = new FormData(form);
    const type = String(data.get("capture-type") ?? "USER_SELECTED");
    return {
      baselineId: String(data.get("capture-baseline-id") ?? ""),
      name: String(data.get("capture-name") ?? ""),
      baselineType: (BASELINE_TYPES as readonly string[]).includes(type)
        ? (type as BaselineType)
        : "USER_SELECTED",
      notes: String(data.get("capture-notes") ?? ""),
      currency: String(data.get("capture-currency") ?? ""),
    };
  }

  async function reloadAll(): Promise<void> {
    state.status = "loading";
    state.periodsStatus = "loading";
    state.baselinesStatus = "loading";
    state.busy = true;
    state.expensesError = null;
    state.accountsError = null;
    state.periodsError = null;
    state.baselinesError = null;
    render();
    const [expenses, accounts, periods, baselines, dataDate] = await Promise.all([
      loadExpenses(transport, context),
      loadCostAccounts(transport, context),
      loadFinancialPeriods(transport, context),
      loadBaselines(transport, context),
      loadScheduleDataDate(transport, context),
    ]);
    state.status = "loaded";
    state.busy = false;
    if (expenses.ok) state.expenses = expenses.data;
    else state.expensesError = expenses.error.code;
    if (accounts.ok) state.accounts = accounts.data;
    else state.accountsError = accounts.error.code;
    if (periods.ok) {
      state.periods = periods.data;
      state.periodsStatus = "loaded";
    } else {
      state.periodsStatus = "error";
      state.periodsError = periods.error.code;
    }
    if (baselines.ok) {
      state.baselines = baselines.data;
      state.baselinesStatus = "loaded";
      if (!state.baselines.some((item) => item.baselineId === state.baselineId)) {
        state.baselineId = state.baselines[0]?.baselineId ?? "";
      }
    } else {
      state.baselinesStatus = "error";
      state.baselinesError = baselines.error.code;
    }
    if (dataDate.ok && dataDate.data) state.dataDate = dataDate.data;
    if (!state.currency) {
      const currencies = currencyOptions();
      if (currencies.length === 1) state.currency = currencies[0];
    }
    render();
  }

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    const action = target.closest<HTMLElement>("[data-cost-action]")?.dataset.costAction;
    if (action === "refresh") {
      void reloadAll();
      return;
    }
    if (action === "expenses") {
      onNavigate?.("expenses");
      return;
    }
    if (action === "schedule") {
      onNavigate?.("schedule");
      return;
    }
    const periodAction = target.closest<HTMLElement>("[data-cost-period-action]")?.dataset.costPeriodAction;
    if (periodAction === "new") {
      state.periodDraft = emptyPeriodDraft();
      state.periodMode = "create";
      render();
      return;
    }
    if (periodAction === "cancel") {
      state.periodDraft = emptyPeriodDraft();
      state.periodMode = "browse";
      render();
      return;
    }
    const captureAction = target.closest<HTMLElement>("[data-cost-capture-action]")?.dataset.costCaptureAction;
    if (captureAction === "new") {
      state.captureDraft = emptyCaptureDraft();
      state.captureDraft.currency = currencyOptions()[0] ?? "";
      state.captureMode = "create";
      render();
      return;
    }
    if (captureAction === "cancel") {
      state.captureDraft = emptyCaptureDraft();
      state.captureMode = "browse";
      render();
    }
  });

  host.addEventListener("change", (event) => {
    const target = event.target as HTMLInputElement | HTMLSelectElement;
    if (target.name === "evm-baseline") {
      state.baselineId = target.value;
      state.measured = null;
      state.measureError = null;
      render();
      return;
    }
    if (target.name === "evm-etc-method") {
      state.etcMethod = target.value as EtcMethod;
      const form = target.closest("form");
      const factor = form?.querySelector<HTMLInputElement>("[name='evm-performance-factor']");
      if (factor) factor.disabled = state.etcMethod !== "USER_PF";
      return;
    }
    if (target.name === "evm-currency") state.currency = target.value;
    if (target.name === "evm-data-date") state.dataDate = target.value;
    if (target.name === "evm-performance-factor") state.performanceFactor = target.value;
  });

  host.addEventListener("submit", (event) => {
    const form = event.target as HTMLFormElement;
    if (form.matches("[data-cost-period-form]")) {
      event.preventDefault();
      if (state.busy) return;
      const input = readPeriodInput(form);
      state.periodDraft = input;
      void (async () => {
        state.busy = true;
        state.notice = null;
        render();
        const result = await createFinancialPeriod(transport, context, input);
        state.busy = false;
        if (!result.ok) {
          state.notice = {
            kind: "error",
            message: `${t("Financial period was not created", "دورهٔ مالی ایجاد نشد")} (${result.error.code})`,
          };
          state.periodMode = "create";
          render();
          return;
        }
        state.notice = { kind: "ok", message: t("Financial period created.", "دورهٔ مالی ایجاد شد.") };
        state.periodMode = "browse";
        state.periodDraft = emptyPeriodDraft();
        const periods = await loadFinancialPeriods(transport, context);
        if (periods.ok) {
          state.periods = periods.data;
          state.periodsStatus = "loaded";
          state.periodsError = null;
        }
        render();
      })();
      return;
    }
    if (form.matches("[data-cost-capture-form]")) {
      event.preventDefault();
      if (state.capturing) return;
      const input = readCaptureInput(form);
      state.captureDraft = input;
      void (async () => {
        state.capturing = true;
        state.notice = null;
        render();
        const result = await captureBaseline(transport, context, input);
        state.capturing = false;
        if (!result.ok) {
          state.notice = {
            kind: "error",
            message: `${t("Baseline was not captured", "ثبت مبنا انجام نشد")} (${result.error.code})`,
          };
          state.captureMode = "create";
          render();
          return;
        }
        state.notice = {
          kind: "ok",
          message: t("Baseline captured from the calculated schedule.", "مبنا از زمان‌بندی محاسبه‌شده ثبت شد."),
        };
        state.captureMode = "browse";
        state.captureDraft = emptyCaptureDraft();
        state.baselineId = result.data.baselineId;
        state.measured = null;
        state.measureError = null;
        const baselines = await loadBaselines(transport, context);
        if (baselines.ok) {
          state.baselines = baselines.data;
          state.baselinesStatus = "loaded";
          state.baselinesError = null;
        }
        render();
      })();
      return;
    }
    if (!form.matches("[data-cost-evm-form]")) return;
    event.preventDefault();
    if (state.measuring) return;
    const input = readEarnedValueInput(form);
    state.measuring = true;
    state.measureError = null;
    state.measured = null;
    render();
    void (async () => {
      const result = await measureEarnedValue(transport, context, input);
      state.measuring = false;
      state.baselineId = input.baselineId;
      state.dataDate = input.dataDate;
      state.currency = input.currency;
      state.etcMethod = input.etcMethod as EtcMethod;
      state.performanceFactor = input.performanceFactor;
      if (!result.ok) {
        state.measureError = result.error.code;
      } else {
        state.measured = result.data;
      }
      render();
    })();
  });

  render();
  void reloadAll();
}
