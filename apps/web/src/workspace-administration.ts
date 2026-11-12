import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

/**
 * Project administration client.
 *
 * Preferences and dictionary entries are project-scoped administration facts
 * stored by the server with revision guards and an audit trail. The permission
 * matrix is read from the single authorization policy, and financial periods
 * come from the existing authoritative period register.
 */

export const ADMIN_API_VERSION = "p6-administration-api.v1";
export const PERIOD_API_VERSION = "p6-financial-period-api.v1";

export const ADMIN_DICTIONARY_CODES = [
  "cost_category",
  "risk_category",
  "issue_type",
  "document_type",
  "expense_category",
] as const;

export type AdminDictionaryCode = (typeof ADMIN_DICTIONARY_CODES)[number];

export type AdminTab = "preferences" | "dictionaries" | "matrix" | "periods";

export type AdminPreferences = {
  currency: string;
  unitOfMeasure: string;
  dateDisplay: "gregorian" | "jalali";
  decimalPlaces: number;
  fiscalYearStartMonth: number;
  revision: number;
  updatedAt: string | null;
  updatedBy: string | null;
};

export type AdminPreferencesInput = {
  currency: string;
  unitOfMeasure: string;
  dateDisplay: string;
  decimalPlaces: number;
  fiscalYearStartMonth: number;
};

export type PermissionRole = {
  role: string;
  permissions: string[];
};

export type PermissionMatrix = {
  roles: PermissionRole[];
  permissions: string[];
};

export type DictionaryEntry = {
  dictionaryCode: AdminDictionaryCode;
  entryId: string;
  label: string;
  sequence: number;
  isActive: boolean;
  revision: number;
  updatedAt: string | null;
  updatedBy: string | null;
};

export type DictionaryDraft = {
  dictionaryCode: AdminDictionaryCode;
  entryId: string;
  label: string;
  sequence: number;
  isActive: boolean;
};

export type FinancialPeriod = {
  periodId: string;
  name: string;
  startDate: string;
  endDate: string;
  status: "OPEN" | "CLOSED";
};

export type FinancialPeriodDraft = {
  periodId: string;
  name: string;
  startDate: string;
  endDate: string;
  status: "OPEN" | "CLOSED";
};

export type AdministrationPageOptions = {
  transport: ApiTransport;
  context: ProjectContext;
  locale: string;
  canAdmin: boolean;
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
    error: {
      code,
      retryable: false,
      message_key: "error.request.invalid",
      available_actions: [],
    },
  };
}

function requiredText(value: unknown, code: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(code);
  return value;
}

function integer(value: unknown, code: string): number {
  if (typeof value !== "number" || !Number.isInteger(value)) throw new Error(code);
  return value;
}

function adminPath(context: ProjectContext, suffix: string): string {
  return `/api/projects/${encodeURIComponent(context.project_id)}/administration${suffix}`;
}

function periodPath(context: ProjectContext): string {
  return `/api/projects/${encodeURIComponent(context.project_id)}/p6/financial-periods`;
}

function dictionaryCodeOf(value: unknown): AdminDictionaryCode {
  if (
    typeof value !== "string" ||
    !ADMIN_DICTIONARY_CODES.includes(value as AdminDictionaryCode)
  ) {
    throw new Error("INVALID_ADMIN_DICTIONARY_CODE");
  }
  return value as AdminDictionaryCode;
}

export function parsePreferences(value: unknown): AdminPreferences {
  if (!isRecord(value) || value.contract_version !== ADMIN_API_VERSION) {
    throw new Error("INVALID_ADMIN_PREFERENCES");
  }
  const dateDisplay = value.date_display;
  if (dateDisplay !== "gregorian" && dateDisplay !== "jalali") {
    throw new Error("INVALID_ADMIN_PREFERENCES");
  }
  const currency = requiredText(value.currency, "INVALID_ADMIN_PREFERENCES");
  if (currency.length !== 3 || !/^[A-Z]{3}$/.test(currency)) {
    throw new Error("INVALID_ADMIN_PREFERENCES");
  }
  const decimalPlaces = integer(value.decimal_places, "INVALID_ADMIN_PREFERENCES");
  if (decimalPlaces < 0 || decimalPlaces > 4) throw new Error("INVALID_ADMIN_PREFERENCES");
  const fiscalYearStartMonth = integer(
    value.fiscal_year_start_month,
    "INVALID_ADMIN_PREFERENCES",
  );
  if (fiscalYearStartMonth < 1 || fiscalYearStartMonth > 12) {
    throw new Error("INVALID_ADMIN_PREFERENCES");
  }
  return {
    currency,
    unitOfMeasure: requiredText(value.unit_of_measure, "INVALID_ADMIN_PREFERENCES"),
    dateDisplay,
    decimalPlaces,
    fiscalYearStartMonth,
    revision: integer(value.revision, "INVALID_ADMIN_PREFERENCES"),
    updatedAt: typeof value.updated_at === "string" ? value.updated_at : null,
    updatedBy: typeof value.updated_by === "string" ? value.updated_by : null,
  };
}

export function parsePermissionMatrix(value: unknown): PermissionMatrix {
  if (!isRecord(value) || value.contract_version !== ADMIN_API_VERSION) {
    throw new Error("INVALID_ADMIN_MATRIX");
  }
  if (!Array.isArray(value.permissions) || !value.permissions.length) {
    throw new Error("INVALID_ADMIN_MATRIX");
  }
  const permissions = value.permissions.map((permission) =>
    requiredText(permission, "INVALID_ADMIN_MATRIX"),
  );
  if (new Set(permissions).size !== permissions.length) throw new Error("INVALID_ADMIN_MATRIX");
  if (!Array.isArray(value.roles) || !value.roles.length) throw new Error("INVALID_ADMIN_MATRIX");
  const roles: PermissionRole[] = [];
  for (const entry of value.roles) {
    if (!isRecord(entry)) throw new Error("INVALID_ADMIN_MATRIX");
    if (!Array.isArray(entry.permissions)) throw new Error("INVALID_ADMIN_MATRIX");
    const granted = entry.permissions.map((permission) =>
      requiredText(permission, "INVALID_ADMIN_MATRIX"),
    );
    if (granted.some((permission) => !permissions.includes(permission))) {
      throw new Error("INVALID_ADMIN_MATRIX");
    }
    roles.push({
      role: requiredText(entry.role, "INVALID_ADMIN_MATRIX"),
      permissions: [...new Set(granted)],
    });
  }
  if (new Set(roles.map((role) => role.role)).size !== roles.length) {
    throw new Error("INVALID_ADMIN_MATRIX");
  }
  return { roles, permissions };
}

export function parseDictionaryEntry(value: unknown): DictionaryEntry {
  if (!isRecord(value) || value.contract_version !== ADMIN_API_VERSION) {
    throw new Error("INVALID_ADMIN_DICTIONARY");
  }
  if (typeof value.is_active !== "boolean") throw new Error("INVALID_ADMIN_DICTIONARY");
  const sequence = integer(value.sequence, "INVALID_ADMIN_DICTIONARY");
  if (sequence < 0 || sequence > 9999) throw new Error("INVALID_ADMIN_DICTIONARY");
  return {
    dictionaryCode: dictionaryCodeOf(value.dictionary_code),
    entryId: requiredText(value.entry_id, "INVALID_ADMIN_DICTIONARY"),
    label: requiredText(value.label, "INVALID_ADMIN_DICTIONARY"),
    sequence,
    isActive: value.is_active,
    revision: integer(value.revision, "INVALID_ADMIN_DICTIONARY"),
    updatedAt: typeof value.updated_at === "string" ? value.updated_at : null,
    updatedBy: typeof value.updated_by === "string" ? value.updated_by : null,
  };
}

export function parseDictionaryList(value: unknown): {
  codes: AdminDictionaryCode[];
  entries: DictionaryEntry[];
} {
  if (!isRecord(value) || value.contract_version !== ADMIN_API_VERSION) {
    throw new Error("INVALID_ADMIN_DICTIONARY_LIST");
  }
  if (!Array.isArray(value.dictionary_codes)) throw new Error("INVALID_ADMIN_DICTIONARY_LIST");
  const codes = value.dictionary_codes.map((code) => dictionaryCodeOf(code));
  if (!Array.isArray(value.entries)) throw new Error("INVALID_ADMIN_DICTIONARY_LIST");
  const entries = value.entries.map((entry) => parseDictionaryEntry(entry));
  const keys = new Set(entries.map((entry) => `${entry.dictionaryCode}/${entry.entryId}`));
  if (keys.size !== entries.length) throw new Error("INVALID_ADMIN_DICTIONARY_LIST");
  return { codes, entries };
}

export function parseFinancialPeriodList(value: unknown): FinancialPeriod[] {
  if (!isRecord(value) || value.contract_version !== PERIOD_API_VERSION) {
    throw new Error("INVALID_FINANCIAL_PERIOD_LIST");
  }
  if (!Array.isArray(value.financial_periods)) throw new Error("INVALID_FINANCIAL_PERIOD_LIST");
  return value.financial_periods.map((entry) => {
    if (!isRecord(entry)) throw new Error("INVALID_FINANCIAL_PERIOD_LIST");
    const period = entry.financial_period;
    if (!isRecord(period)) throw new Error("INVALID_FINANCIAL_PERIOD_LIST");
    const status = period.status;
    if (status !== "OPEN" && status !== "CLOSED") throw new Error("INVALID_FINANCIAL_PERIOD_LIST");
    const startDate = requiredText(period.start_date, "INVALID_FINANCIAL_PERIOD_LIST");
    const endDate = requiredText(period.end_date, "INVALID_FINANCIAL_PERIOD_LIST");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(startDate) || !/^\d{4}-\d{2}-\d{2}$/.test(endDate)) {
      throw new Error("INVALID_FINANCIAL_PERIOD_LIST");
    }
    return {
      periodId: requiredText(period.period_id, "INVALID_FINANCIAL_PERIOD_LIST"),
      name: requiredText(period.name, "INVALID_FINANCIAL_PERIOD_LIST"),
      startDate,
      endDate,
      status,
    };
  });
}

export async function loadPreferences(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<AdminPreferences>> {
  const result = await transport.get<unknown>(adminPath(context, "/preferences"), context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parsePreferences(result.data) };
  } catch {
    return localError("INVALID_ADMIN_PREFERENCES");
  }
}

export async function savePreferences(
  transport: ApiTransport,
  context: ProjectContext,
  input: AdminPreferencesInput,
  expectedRevision: number,
): Promise<ApiResult<AdminPreferences>> {
  if (!transport.put) return localError("TRANSPORT_UNAVAILABLE");
  const result = await transport.put<Record<string, unknown>, unknown>(
    adminPath(context, "/preferences"),
    {
      currency: input.currency,
      unit_of_measure: input.unitOfMeasure,
      date_display: input.dateDisplay,
      decimal_places: input.decimalPlaces,
      fiscal_year_start_month: input.fiscalYearStartMonth,
      expected_revision: expectedRevision,
    },
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parsePreferences(result.data) };
  } catch {
    return localError("INVALID_ADMIN_PREFERENCES");
  }
}

export async function loadPermissionMatrix(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<PermissionMatrix>> {
  const result = await transport.get<unknown>(
    adminPath(context, "/permission-matrix"),
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parsePermissionMatrix(result.data) };
  } catch {
    return localError("INVALID_ADMIN_MATRIX");
  }
}

export async function loadDictionaries(
  transport: ApiTransport,
  context: ProjectContext,
  filters: { code: string; search: string },
): Promise<ApiResult<{ codes: AdminDictionaryCode[]; entries: DictionaryEntry[] }>> {
  const params = new URLSearchParams();
  if (filters.code) params.set("dictionary_code", filters.code);
  if (filters.search) params.set("search", filters.search);
  const query = params.toString();
  const result = await transport.get<unknown>(
    `${adminPath(context, "/dictionaries")}${query ? `?${query}` : ""}`,
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseDictionaryList(result.data) };
  } catch {
    return localError("INVALID_ADMIN_DICTIONARY_LIST");
  }
}

export async function saveDictionary(
  transport: ApiTransport,
  context: ProjectContext,
  input: DictionaryDraft,
  editingRevision?: number,
  idempotencyKey?: string,
): Promise<ApiResult<DictionaryEntry>> {
  if (editingRevision === undefined) {
    if (!transport.post) return localError("TRANSPORT_UNAVAILABLE");
    const result = await transport.post<Record<string, unknown>, unknown>(
      adminPath(context, "/dictionaries"),
      {
        dictionary_code: input.dictionaryCode,
        entry_id: input.entryId,
        label: input.label,
        sequence: input.sequence,
        is_active: input.isActive,
      },
      context,
      idempotencyKey,
    );
    if (!result.ok) return result;
    try {
      return { ok: true, data: parseDictionaryEntry(result.data) };
    } catch {
      return localError("INVALID_ADMIN_DICTIONARY");
    }
  }
  if (!transport.patch) return localError("TRANSPORT_UNAVAILABLE");
  const result = await transport.patch<Record<string, unknown>, unknown>(
    adminPath(
      context,
      `/dictionaries/${encodeURIComponent(input.dictionaryCode)}/${encodeURIComponent(input.entryId)}`,
    ),
    {
      label: input.label,
      sequence: input.sequence,
      is_active: input.isActive,
      expected_revision: editingRevision,
    },
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseDictionaryEntry(result.data) };
  } catch {
    return localError("INVALID_ADMIN_DICTIONARY");
  }
}

export async function deleteDictionary(
  transport: ApiTransport,
  context: ProjectContext,
  entry: DictionaryEntry,
): Promise<ApiResult<{ deleted: boolean }>> {
  if (!transport.delete) return localError("TRANSPORT_UNAVAILABLE");
  const result = await transport.delete<Record<string, unknown>, unknown>(
    adminPath(
      context,
      `/dictionaries/${encodeURIComponent(entry.dictionaryCode)}/${encodeURIComponent(entry.entryId)}`,
    ),
    { expected_revision: entry.revision },
    context,
  );
  if (!result.ok) return result;
  return { ok: true, data: { deleted: isRecord(result.data) && result.data.deleted === true } };
}

export async function loadFinancialPeriods(
  transport: ApiTransport,
  context: ProjectContext,
): Promise<ApiResult<FinancialPeriod[]>> {
  const result = await transport.get<unknown>(periodPath(context), context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseFinancialPeriodList(result.data) };
  } catch {
    return localError("INVALID_FINANCIAL_PERIOD_LIST");
  }
}

export async function createFinancialPeriod(
  transport: ApiTransport,
  context: ProjectContext,
  input: FinancialPeriodDraft,
): Promise<ApiResult<FinancialPeriod>> {
  if (!transport.post) return localError("TRANSPORT_UNAVAILABLE");
  const result = await transport.post<Record<string, unknown>, unknown>(
    periodPath(context),
    {
      period_id: input.periodId,
      name: input.name,
      start_date: input.startDate,
      end_date: input.endDate,
      status: input.status,
    },
    context,
  );
  if (!result.ok) return result;
  try {
    const parsed = parseFinancialPeriodList({ contract_version: PERIOD_API_VERSION, financial_periods: [result.data] });
    return { ok: true, data: parsed[0] };
  } catch {
    return localError("INVALID_FINANCIAL_PERIOD");
  }
}

type PageState = {
  tab: AdminTab;
  status: "loading" | "loaded" | "error";
  errorCode: string | null;
  preferences: AdminPreferences | null;
  matrix: PermissionMatrix | null;
  entries: DictionaryEntry[];
  codes: AdminDictionaryCode[];
  filters: { code: string; search: string };
  dictionaryMode: "browse" | "create" | "edit";
  editingRevision: number | null;
  draft: DictionaryDraft;
  periods: FinancialPeriod[];
  periodDraft: FinancialPeriodDraft;
  busy: boolean;
  notice: { kind: "ok" | "error"; message: string } | null;
};

function defaultDraft(): DictionaryDraft {
  return {
    dictionaryCode: "cost_category",
    entryId: "",
    label: "",
    sequence: 0,
    isActive: true,
  };
}

function defaultPeriod(): FinancialPeriodDraft {
  return { periodId: "", name: "", startDate: "", endDate: "", status: "OPEN" };
}

function inputFrom(preferences: AdminPreferences): AdminPreferencesInput {
  return {
    currency: preferences.currency,
    unitOfMeasure: preferences.unitOfMeasure,
    dateDisplay: preferences.dateDisplay,
    decimalPlaces: preferences.decimalPlaces,
    fiscalYearStartMonth: preferences.fiscalYearStartMonth,
  };
}

export function mountWorkspaceAdministrationPage(
  host: HTMLElement,
  options: AdministrationPageOptions,
): void {
  if (host.dataset.administrationMounted === "true") return;
  host.dataset.administrationMounted = "true";
  const { transport, context, locale, canAdmin } = options;
  const say = (en: string, fa: string): string => text(locale, en, fa);
  const state: PageState = {
    tab: "preferences",
    status: "loading",
    errorCode: null,
    preferences: null,
    matrix: null,
    entries: [],
    codes: [...ADMIN_DICTIONARY_CODES],
    filters: { code: "", search: "" },
    dictionaryMode: "browse",
    editingRevision: null,
    draft: defaultDraft(),
    periods: [],
    periodDraft: defaultPeriod(),
    busy: false,
    notice: null,
  };
  let preferenceDraft: AdminPreferencesInput = {
    currency: "USD",
    unitOfMeasure: "day",
    dateDisplay: "gregorian",
    decimalPlaces: 2,
    fiscalYearStartMonth: 1,
  };

  function notice(kind: "ok" | "error", message: string): void {
    state.notice = { kind, message };
  }

  async function reloadAll(): Promise<void> {
    state.status = "loading";
    render();
    const [prefs, matrix, dictionaries, periods] = await Promise.all([
      loadPreferences(transport, context),
      loadPermissionMatrix(transport, context),
      loadDictionaries(transport, context, state.filters),
      loadFinancialPeriods(transport, context),
    ]);
    if (prefs.ok) {
      state.preferences = prefs.data;
      preferenceDraft = inputFrom(prefs.data);
    }
    if (matrix.ok) state.matrix = matrix.data;
    if (dictionaries.ok) {
      state.entries = dictionaries.data.entries;
      state.codes = dictionaries.data.codes;
    }
    if (periods.ok) state.periods = periods.data;
    const failure = [prefs, matrix, dictionaries, periods].find((result) => !result.ok);
    if (failure && !failure.ok) {
      state.status = "error";
      state.errorCode = failure.error.code;
    } else {
      state.status = "loaded";
      state.errorCode = null;
    }
    render();
  }

  async function reloadDictionaries(): Promise<void> {
    const result = await loadDictionaries(transport, context, state.filters);
    if (result.ok) {
      state.entries = result.data.entries;
      state.codes = result.data.codes;
    } else {
      notice("error", `${say("Dictionaries were not read", "فهرست‌ها خوانده نشد")} (${result.error.code})`);
    }
    render();
  }

  async function reloadPeriods(): Promise<void> {
    const result = await loadFinancialPeriods(transport, context);
    if (result.ok) {
      state.periods = result.data;
    } else {
      notice("error", `${say("Financial periods were not read", "دوره‌های مالی خوانده نشد")} (${result.error.code})`);
    }
    render();
  }

  function renderTabs(): string {
    const tabs: Array<[AdminTab, string, string]> = [
      ["preferences", "Preferences", "ترجیحات"],
      ["dictionaries", "Dictionaries", "فهرست‌ها"],
      ["matrix", "Permission Matrix", "ماتریس دسترسی"],
      ["periods", "Financial Periods", "دوره‌های مالی"],
    ];
    return `<div class="cp-register-tabs" role="tablist">${tabs
      .map(
        ([key, en, fa]) =>
          `<button type="button" role="tab" data-admin-tab="${key}" aria-selected="${state.tab === key}" class="${state.tab === key ? "is-active" : ""}">${escapeHtml(say(en, fa))}</button>`,
      )
      .join("")}</div>`;
  }

  function renderPreferences(): string {
    const prefs = state.preferences;
    if (!prefs) {
      return `<p class="cp-register-notice" role="alert">${escapeHtml(say("Administration preferences are not available.", "ترجیحات مدیریت در دسترس نیست."))}</p>`;
    }
    const disabled = canAdmin ? "" : "disabled";
    const months = Array.from({ length: 12 }, (_, index) => index + 1);
    return `<form data-admin-preferences-form class="cp-expense-fields">
      <label>${escapeHtml(say("Currency", "ارز"))}<input name="admin-currency" maxlength="3" value="${escapeHtml(preferenceDraft.currency)}" ${disabled}></label>
      <label>${escapeHtml(say("Unit of measure", "واحد اندازه‌گیری"))}<input name="admin-unit" maxlength="20" value="${escapeHtml(preferenceDraft.unitOfMeasure)}" ${disabled}></label>
      <label>${escapeHtml(say("Date display", "نمایش تاریخ"))}<select name="admin-date-display" ${disabled}><option value="gregorian" ${preferenceDraft.dateDisplay === "gregorian" ? "selected" : ""}>${escapeHtml(say("Gregorian", "میلادی"))}</option><option value="jalali" ${preferenceDraft.dateDisplay === "jalali" ? "selected" : ""}>${escapeHtml(say("Jalali", "شمسی"))}</option></select></label>
      <label>${escapeHtml(say("Decimal places", "رقم اعشار"))}<select name="admin-decimals" ${disabled}>${[0, 1, 2, 3, 4].map((value) => `<option value="${value}" ${preferenceDraft.decimalPlaces === value ? "selected" : ""}>${value}</option>`).join("")}</select></label>
      <label>${escapeHtml(say("Fiscal year starts", "آغاز سال مالی"))}<select name="admin-fiscal-month" ${disabled}>${months.map((value) => `<option value="${value}" ${preferenceDraft.fiscalYearStartMonth === value ? "selected" : ""}>${escapeHtml(say(`Month ${value}`, `ماه ${value}`))}</option>`).join("")}</select></label>
      <div class="cp-calendar-panel-actions">${canAdmin ? `<button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Save preferences", "ذخیره ترجیحات"))}</button>` : ""}<span data-admin-preferences-meta>${escapeHtml(say("Revision", "نسخه"))} ${prefs.revision}${prefs.updatedBy ? ` · ${escapeHtml(prefs.updatedBy)}` : ""}</span></div>
    </form>
    <p class="cp-register-notice">${escapeHtml(say("Preferences are project facts used by financial and calendar presentation. Only a project administrator can change them.", "ترجیحات، واقعیت‌های پروژه برای نمایش مالی و تقویمی هستند و فقط مدیر پروژه می‌تواند آن‌ها را تغییر دهد."))}</p>`;
  }

  function renderDictionaryForm(): string {
    const editing = state.dictionaryMode === "edit";
    return `<form data-admin-dict-form class="cp-expense-fields">
      <label>${escapeHtml(say("Dictionary", "فهرست"))}<select name="admin-dict-code" ${editing ? "disabled" : ""}>${state.codes.map((code) => `<option value="${code}" ${state.draft.dictionaryCode === code ? "selected" : ""}>${escapeHtml(code)}</option>`).join("")}</select></label>
      <label>${escapeHtml(say("Entry ID", "شناسه ورودی"))}<input name="admin-dict-entry" value="${escapeHtml(state.draft.entryId)}" ${editing ? "readonly" : ""}></label>
      <label>${escapeHtml(say("Label", "برچسب"))}<input name="admin-dict-label" value="${escapeHtml(state.draft.label)}"></label>
      <label>${escapeHtml(say("Sequence", "ترتیب"))}<input name="admin-dict-sequence" type="number" min="0" max="9999" value="${state.draft.sequence}"></label>
      <label class="cp-report-field"><input type="checkbox" name="admin-dict-active" data-admin-dict-active ${state.draft.isActive ? "checked" : ""}> ${escapeHtml(say("Active", "فعال"))}</label>
      <div class="cp-calendar-panel-actions"><button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(editing ? say("Save entry", "ذخیره ورودی") : say("Create entry", "ایجاد ورودی"))}</button><button type="button" data-admin-action="cancel-dict">${escapeHtml(say("Cancel", "لغو"))}</button></div>
    </form>`;
  }

  function renderDictionaries(): string {
    const rows = state.entries
      .map(
        (entry) =>
          `<tr data-admin-dict-row data-code="${escapeHtml(entry.dictionaryCode)}" data-entry="${escapeHtml(entry.entryId)}"><td><strong>${escapeHtml(entry.entryId)}</strong><br><span>${escapeHtml(entry.label)}</span></td><td>${escapeHtml(entry.dictionaryCode)}</td><td>${entry.sequence}</td><td>${entry.isActive ? escapeHtml(say("Yes", "بله")) : escapeHtml(say("No", "خیر"))}</td><td>${entry.revision}</td><td>${canAdmin ? `<button type="button" data-admin-dict-edit="${escapeHtml(entry.entryId)}" data-admin-dict-code="${escapeHtml(entry.dictionaryCode)}">${escapeHtml(say("Edit", "ویرایش"))}</button><button type="button" data-admin-dict-delete="${escapeHtml(entry.entryId)}" data-admin-dict-code="${escapeHtml(entry.dictionaryCode)}" data-admin-dict-revision="${entry.revision}">${escapeHtml(say("Delete", "حذف"))}</button>` : ""}</td></tr>`,
      )
      .join("");
    const body = state.entries.length
      ? `<div class="cp-table-scroll"><table class="cp-register-table"><thead><tr><th>${escapeHtml(say("Entry", "ورودی"))}</th><th>${escapeHtml(say("Dictionary", "فهرست"))}</th><th>${escapeHtml(say("Sequence", "ترتیب"))}</th><th>${escapeHtml(say("Active", "فعال"))}</th><th>${escapeHtml(say("Revision", "نسخه"))}</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>`
      : `<div class="cp-calendar-empty" data-admin-dict-empty>${escapeHtml(say("No dictionary entries match the current filters.", "هیچ ورودی فهرستی با پالایه‌های جاری مطابقت ندارد."))}</div>`;
    return `${renderDictionaryForm()}${body}`;
  }

  function renderMatrix(): string {
    if (!state.matrix) {
      return `<p class="cp-register-notice" role="alert">${escapeHtml(say("The permission matrix is not available.", "ماتریس دسترسی در دسترس نیست."))}</p>`;
    }
    const matrix = state.matrix;
    const head = matrix.roles.map((role) => `<th scope="col">${escapeHtml(role.role)}</th>`).join("");
    const rows = matrix.permissions
      .map((permission) => {
        const cells = matrix.roles
          .map(
            (role) =>
              `<td data-admin-grant="${escapeHtml(role.role)}">${role.permissions.includes(permission) ? "✓" : "—"}</td>`,
          )
          .join("");
        return `<tr data-admin-permission="${escapeHtml(permission)}"><th scope="row">${escapeHtml(permission)}</th>${cells}</tr>`;
      })
      .join("");
    return `<p class="cp-register-notice">${escapeHtml(say("The matrix is generated from the same authorization policy that enforces every API call; it is not a separate editable copy.", "این ماتریس از همان سیاست دسترسی که هر فراخوانی API را اعمال می‌کند تولید می‌شود و نسخهٔ قابل ویرایش جداگانه نیست."))}</p>
      <div class="cp-table-scroll"><table class="cp-register-table" data-admin-matrix><thead><tr><th>${escapeHtml(say("Permission", "دسترسی"))}</th>${head}</tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function renderPeriods(): string {
    const rows = state.periods
      .map(
        (period) =>
          `<tr data-admin-period-row data-period-id="${escapeHtml(period.periodId)}"><td><strong>${escapeHtml(period.periodId)}</strong><br><span>${escapeHtml(period.name)}</span></td><td>${escapeHtml(period.startDate)}</td><td>${escapeHtml(period.endDate)}</td><td>${escapeHtml(period.status)}</td></tr>`,
      )
      .join("");
    const body = state.periods.length
      ? `<div class="cp-table-scroll"><table class="cp-register-table"><thead><tr><th>${escapeHtml(say("Period", "دوره"))}</th><th>${escapeHtml(say("Start", "شروع"))}</th><th>${escapeHtml(say("End", "پایان"))}</th><th>${escapeHtml(say("Status", "وضعیت"))}</th></tr></thead><tbody>${rows}</tbody></table></div>`
      : `<div class="cp-calendar-empty" data-admin-period-empty>${escapeHtml(say("No financial periods are stored for this project.", "هیچ دورهٔ مالی برای این پروژه ذخیره نشده است."))}</div>`;
    const disabled = canAdmin ? "" : "disabled";
    const form = `<form data-admin-period-form class="cp-expense-fields">
      <label>${escapeHtml(say("Period ID", "شناسه دوره"))}<input name="admin-period-id" value="${escapeHtml(state.periodDraft.periodId)}" ${disabled}></label>
      <label>${escapeHtml(say("Name", "نام"))}<input name="admin-period-name" value="${escapeHtml(state.periodDraft.name)}" ${disabled}></label>
      <label>${escapeHtml(say("Start date", "تاریخ شروع"))}<input name="admin-period-start" type="date" value="${escapeHtml(state.periodDraft.startDate)}" ${disabled}></label>
      <label>${escapeHtml(say("End date", "تاریخ پایان"))}<input name="admin-period-end" type="date" value="${escapeHtml(state.periodDraft.endDate)}" ${disabled}></label>
      <label>${escapeHtml(say("Status", "وضعیت"))}<select name="admin-period-status" ${disabled}><option value="OPEN" ${state.periodDraft.status === "OPEN" ? "selected" : ""}>OPEN</option><option value="CLOSED" ${state.periodDraft.status === "CLOSED" ? "selected" : ""}>CLOSED</option></select></label>
      <div class="cp-calendar-panel-actions">${canAdmin ? `<button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Save period", "ذخیره دوره"))}</button>` : ""}</div>
    </form>`;
    return `${form}${body}`;
  }

  function render(): void {
    if (state.status === "loading") {
      host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(say("Administration", "مدیریت"))}</strong></div><div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading project administration…", "در حال خواندن مدیریت پروژه…"))}</div>`;
      return;
    }
    if (state.status === "error") {
      host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(say("Administration", "مدیریت"))}</strong><div><button type="button" data-admin-action="reload">${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button></div></div><div class="cp-calendar-empty" role="alert">${escapeHtml(say("Administration could not be read", "خواندن مدیریت پروژه ناموفق بود"))} (${escapeHtml(state.errorCode ?? "unknown")})</div>`;
      return;
    }
    const body =
      state.tab === "preferences"
        ? renderPreferences()
        : state.tab === "dictionaries"
          ? renderDictionaries()
          : state.tab === "matrix"
            ? renderMatrix()
            : renderPeriods();
    host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(say("Administration", "مدیریت"))}</strong><div><button type="button" data-admin-action="reload">${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button></div></div>
      ${state.tab === "dictionaries" ? `<div class="cp-register-filters"><label>${escapeHtml(say("Dictionary", "فهرست"))}<select name="admin-dictionary-filter"><option value="">${escapeHtml(say("All dictionaries", "همهٔ فهرست‌ها"))}</option>${state.codes.map((code) => `<option value="${code}" ${state.filters.code === code ? "selected" : ""}>${escapeHtml(code)}</option>`).join("")}</select></label><label>${escapeHtml(say("Search", "جستجو"))}<input type="search" name="admin-dict-search" value="${escapeHtml(state.filters.search)}" placeholder="${escapeHtml(say("ID or label", "شناسه یا برچسب"))}"></label>${canAdmin ? `<button type="button" data-admin-action="new-dict">${escapeHtml(say("New entry", "ورودی جدید"))}</button>` : ""}</div>` : ""}
      ${renderTabs()}
      <div class="cp-admin-body" data-admin-body data-admin-tab="${state.tab}">${body}</div>
      ${state.notice ? `<p class="cp-calendar-notice" data-admin-notice data-state="${state.notice.kind}" role="status">${escapeHtml(state.notice.message)}</p>` : ""}`;
  }

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    const tab = target.closest<HTMLElement>("[data-admin-tab]")?.dataset.adminTab as AdminTab | undefined;
    if (tab) {
      state.tab = tab;
      state.notice = null;
      render();
      return;
    }
    const edit = target.closest<HTMLElement>("[data-admin-dict-edit]");
    if (edit) {
      const code = edit.dataset.adminDictCode;
      const entryId = edit.dataset.adminDictEdit;
      const entry = state.entries.find(
        (item) => item.dictionaryCode === code && item.entryId === entryId,
      );
      if (entry) {
        state.dictionaryMode = "edit";
        state.editingRevision = entry.revision;
        state.draft = {
          dictionaryCode: entry.dictionaryCode,
          entryId: entry.entryId,
          label: entry.label,
          sequence: entry.sequence,
          isActive: entry.isActive,
        };
        state.notice = null;
        render();
      }
      return;
    }
    const remove = target.closest<HTMLElement>("[data-admin-dict-delete]");
    if (remove && canAdmin) {
      const entry = state.entries.find(
        (item) =>
          item.dictionaryCode === remove.dataset.adminDictCode &&
          item.entryId === remove.dataset.adminDictDelete,
      );
      if (entry) {
        void (async () => {
          state.busy = true;
          render();
          const result = await deleteDictionary(transport, context, entry);
          state.busy = false;
          if (!result.ok) {
            notice("error", `${say("Entry was not deleted", "ورودی حذف نشد")} (${result.error.code})`);
          } else {
            notice("ok", say("Dictionary entry deleted.", "ورودی فهرست حذف شد."));
          }
          await reloadDictionaries();
        })();
      }
      return;
    }
    const action = target.closest<HTMLElement>("[data-admin-action]")?.dataset.adminAction;
    if (!action) return;
    if (action === "reload") {
      void (async () => {
        await reloadAll();
        state.notice = null;
        render();
      })();
    } else if (action === "new-dict" && canAdmin) {
      state.dictionaryMode = "create";
      state.editingRevision = null;
      state.draft = defaultDraft();
      state.notice = null;
      render();
    } else if (action === "cancel-dict") {
      state.dictionaryMode = "browse";
      state.editingRevision = null;
      state.notice = null;
      render();
    }
  });

  host.addEventListener("input", (event) => {
    const target = event.target as HTMLInputElement;
    switch (target.name) {
      case "admin-currency": preferenceDraft.currency = target.value.toUpperCase(); break;
      case "admin-unit": preferenceDraft.unitOfMeasure = target.value; break;
      case "admin-dict-entry": state.draft.entryId = target.value; break;
      case "admin-dict-label": state.draft.label = target.value; break;
      case "admin-dict-sequence": state.draft.sequence = Number(target.value); break;
      case "admin-period-id": state.periodDraft.periodId = target.value; break;
      case "admin-period-name": state.periodDraft.name = target.value; break;
      case "admin-period-start": state.periodDraft.startDate = target.value; break;
      case "admin-period-end": state.periodDraft.endDate = target.value; break;
      default: break;
    }
  });

  host.addEventListener("change", (event) => {
    const target = event.target as HTMLInputElement | HTMLSelectElement;
    switch (target.name) {
      case "admin-date-display":
        preferenceDraft.dateDisplay = target.value;
        break;
      case "admin-decimals":
        preferenceDraft.decimalPlaces = Number(target.value);
        break;
      case "admin-fiscal-month":
        preferenceDraft.fiscalYearStartMonth = Number(target.value);
        break;
      case "admin-dict-code":
        state.draft.dictionaryCode = dictionaryCodeOf(target.value);
        break;
      case "admin-dictionary-filter":
        state.filters.code = target.value;
        void reloadDictionaries();
        break;
      case "admin-dict-search":
        state.filters.search = target.value.trim();
        void reloadDictionaries();
        break;
      case "admin-period-status":
        state.periodDraft.status = target.value === "CLOSED" ? "CLOSED" : "OPEN";
        break;
      default:
        if (target.matches("[data-admin-dict-active]")) {
          state.draft.isActive = (target as HTMLInputElement).checked;
        }
        break;
    }
  });

  host.addEventListener("submit", (event) => {
    const form = event.target as HTMLFormElement;
    event.preventDefault();
    if (state.busy || !canAdmin) return;
    if (form.matches("[data-admin-preferences-form]")) {
      void (async () => {
        if (!state.preferences) return;
        state.busy = true;
        render();
        const result = await savePreferences(
          transport,
          context,
          preferenceDraft,
          state.preferences.revision,
        );
        state.busy = false;
        if (!result.ok) {
          if (result.error.code === "ADMIN_PREFERENCES_REVISION_CONFLICT") {
            const reloaded = await loadPreferences(transport, context);
            if (reloaded.ok) {
              state.preferences = reloaded.data;
              preferenceDraft = inputFrom(reloaded.data);
            }
          }
          notice("error", `${say("Preferences were not saved", "ترجیحات ذخیره نشد")} (${result.error.code})`);
          render();
          return;
        }
        state.preferences = result.data;
        preferenceDraft = inputFrom(result.data);
        notice("ok", say("Preferences saved.", "ترجیحات ذخیره شد."));
        render();
      })();
      return;
    }
    if (form.matches("[data-admin-dict-form]")) {
      void (async () => {
        state.busy = true;
        render();
        const editing = state.dictionaryMode === "edit";
        const result = await saveDictionary(
          transport,
          context,
          state.draft,
          editing ? state.editingRevision ?? undefined : undefined,
          editing ? undefined : `admin-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`,
        );
        state.busy = false;
        if (!result.ok) {
          notice("error", `${say("Entry was not saved", "ورودی ذخیره نشد")} (${result.error.code})`);
          if (result.error.code === "ADMIN_DICTIONARY_REVISION_CONFLICT") {
            state.dictionaryMode = "browse";
            await reloadDictionaries();
          } else {
            render();
          }
          return;
        }
        state.dictionaryMode = "browse";
        state.editingRevision = null;
        state.draft = defaultDraft();
        notice("ok", say("Dictionary entry saved.", "ورودی فهرست ذخیره شد."));
        await reloadDictionaries();
      })();
      return;
    }
    if (form.matches("[data-admin-period-form]")) {
      void (async () => {
        state.busy = true;
        render();
        const result = await createFinancialPeriod(transport, context, state.periodDraft);
        state.busy = false;
        if (!result.ok) {
          notice("error", `${say("Financial period was not saved", "دورهٔ مالی ذخیره نشد")} (${result.error.code})`);
          render();
          return;
        }
        state.periodDraft = defaultPeriod();
        notice("ok", say("Financial period saved.", "دورهٔ مالی ذخیره شد."));
        await reloadPeriods();
      })();
    }
  });

  void reloadAll();
}
