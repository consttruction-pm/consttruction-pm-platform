import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

/**
 * Project threshold register client.
 *
 * A threshold definition is an authoritative project rule. Monitoring is a
 * write: the server reads the observed value from project data, appends an
 * immutable run and may raise a real issue. This module never evaluates the
 * level or invents an observed value; it only surfaces what the server stored.
 */

export const THRESHOLD_API_VERSION = "p6-threshold-api.v1";

export const THRESHOLD_SUBJECTS = [
  "schedule",
  "cost",
  "quality",
  "safety",
  "resource",
  "scope",
  "other",
] as const;

export const THRESHOLD_PARAMETERS = [
  "open_issue_count",
  "expense_actual_total",
  "budget_balance",
] as const;

export const THRESHOLD_STATUSES = ["active", "inactive"] as const;
export const THRESHOLD_LEVELS = ["normal", "warning", "issue"] as const;
export const MONETARY_PARAMETERS: readonly string[] = [
  "expense_actual_total",
  "budget_balance",
];

export type ThresholdSubject = (typeof THRESHOLD_SUBJECTS)[number];
export type ThresholdParameter = (typeof THRESHOLD_PARAMETERS)[number];
export type ThresholdStatus = (typeof THRESHOLD_STATUSES)[number];
export type ThresholdLevel = (typeof THRESHOLD_LEVELS)[number];

export type ThresholdRecord = {
  thresholdId: string;
  name: string;
  monitoringSubject: string;
  parameter: string;
  currency: string | null;
  lowerThreshold: string | null;
  upperThreshold: string | null;
  warningLevel: string | null;
  issueLevel: string | null;
  responsibleManager: string | null;
  status: string;
  revision: number;
};

export type ThresholdRunRecord = {
  thresholdId: string;
  runSequence: number;
  observedValue: string;
  level: string;
  currency: string | null;
  actorId: string;
  occurredAt: string;
  generatedIssueId: string | null;
};

export type ThresholdHistoryEvent = {
  entityType: string;
  entityId: string;
  revision: number;
  eventType: string;
  actorId: string;
  occurredAt: string;
  reason: string;
};

export type ThresholdInput = {
  thresholdId: string;
  name: string;
  monitoringSubject: string;
  parameter: string;
  currency: string | null;
  lowerThreshold: string | null;
  upperThreshold: string | null;
  warningLevel: string | null;
  issueLevel: string | null;
  responsibleManager: string | null;
  status: string;
};

export type ThresholdFilters = {
  monitoringSubject: string;
  parameter: string;
  status: string;
  search: string;
};

export type ThresholdPageOptions = {
  transport: ApiTransport;
  context: ProjectContext;
  locale: string;
  canWrite: boolean;
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

function optionalText(value: unknown, code: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string") throw new Error(code);
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function numberText(
  value: unknown,
  code: string,
  options: { allowNegative?: boolean } = {},
): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string") throw new Error(code);
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (!/^-?\d+(\.\d{1,4})?$/.test(trimmed)) throw new Error(code);
  if (!options.allowNegative && trimmed.startsWith("-")) throw new Error(code);
  return trimmed;
}

function revision(value: unknown, code: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1) {
    throw new Error(code);
  }
  return value;
}

function thresholdPath(
  context: ProjectContext,
  thresholdId?: string,
  action?: string,
): string {
  const base = `/api/projects/${encodeURIComponent(context.project_id)}/thresholds`;
  if (!thresholdId) return base;
  return `${base}/${encodeURIComponent(thresholdId)}${action ? `/${action}` : ""}`;
}

export function parseThreshold(value: unknown): ThresholdRecord {
  if (!isRecord(value)) throw new Error("INVALID_THRESHOLD_RECORD");
  if (value.contract_version !== THRESHOLD_API_VERSION) {
    throw new Error("INVALID_THRESHOLD_RESPONSE");
  }
  const thresholdId = value.threshold_id;
  const name = value.name;
  const subject = value.monitoring_subject;
  const parameter = value.parameter;
  const status = value.status;
  if (
    typeof thresholdId !== "string" || !thresholdId.trim() ||
    typeof name !== "string" || !name.trim() ||
    typeof subject !== "string" || !THRESHOLD_SUBJECTS.includes(subject as ThresholdSubject) ||
    typeof parameter !== "string" || !THRESHOLD_PARAMETERS.includes(parameter as ThresholdParameter) ||
    typeof status !== "string" || !THRESHOLD_STATUSES.includes(status as ThresholdStatus)
  ) {
    throw new Error("INVALID_THRESHOLD_RECORD");
  }
  const currency = optionalText(value.currency, "INVALID_THRESHOLD_RECORD");
  if (MONETARY_PARAMETERS.includes(parameter)) {
    if (!currency || !/^[A-Z]{3}$/.test(currency)) throw new Error("INVALID_THRESHOLD_RECORD");
  } else if (currency !== null) {
    throw new Error("INVALID_THRESHOLD_RECORD");
  }
  const lower = numberText(value.lower_threshold, "INVALID_THRESHOLD_RECORD", {
    allowNegative: true,
  });
  const upper = numberText(value.upper_threshold, "INVALID_THRESHOLD_RECORD", {
    allowNegative: true,
  });
  if (lower === null && upper === null) throw new Error("INVALID_THRESHOLD_RECORD");
  if (lower !== null && upper !== null && Number(lower) >= Number(upper)) {
    throw new Error("INVALID_THRESHOLD_RECORD");
  }
  const warning = numberText(value.warning_level, "INVALID_THRESHOLD_RECORD");
  const issue = numberText(value.issue_level, "INVALID_THRESHOLD_RECORD");
  if (warning !== null && issue !== null && Number(issue) <= Number(warning)) {
    throw new Error("INVALID_THRESHOLD_RECORD");
  }
  return {
    thresholdId,
    name,
    monitoringSubject: subject,
    parameter,
    currency,
    lowerThreshold: lower,
    upperThreshold: upper,
    warningLevel: warning,
    issueLevel: issue,
    responsibleManager: optionalText(value.responsible_manager, "INVALID_THRESHOLD_RECORD"),
    status,
    revision: revision(value.revision, "INVALID_THRESHOLD_RECORD"),
  };
}

export function parseThresholdRun(value: unknown): ThresholdRunRecord {
  if (!isRecord(value)) throw new Error("INVALID_THRESHOLD_RUN");
  if (value.contract_version !== THRESHOLD_API_VERSION) {
    throw new Error("INVALID_THRESHOLD_RUN");
  }
  const thresholdId = value.threshold_id;
  const sequence = value.run_sequence;
  const observed = numberText(value.observed_value, "INVALID_THRESHOLD_RUN", {
    allowNegative: true,
  });
  const level = value.level;
  if (
    typeof thresholdId !== "string" || !thresholdId.trim() ||
    typeof sequence !== "number" || !Number.isInteger(sequence) || sequence < 1 ||
    observed === null ||
    typeof level !== "string" || !THRESHOLD_LEVELS.includes(level as ThresholdLevel) ||
    typeof value.actor_id !== "string" || !value.actor_id.trim() ||
    typeof value.occurred_at !== "string" || !value.occurred_at.trim()
  ) {
    throw new Error("INVALID_THRESHOLD_RUN");
  }
  return {
    thresholdId,
    runSequence: sequence,
    observedValue: observed,
    level,
    currency: optionalText(value.currency, "INVALID_THRESHOLD_RUN"),
    actorId: value.actor_id,
    occurredAt: value.occurred_at,
    generatedIssueId: optionalText(value.generated_issue_id, "INVALID_THRESHOLD_RUN"),
  };
}

export function parseThresholdHistoryEvent(value: unknown): ThresholdHistoryEvent {
  if (!isRecord(value)) throw new Error("INVALID_THRESHOLD_HISTORY");
  if (value.contract_version !== THRESHOLD_API_VERSION) {
    throw new Error("INVALID_THRESHOLD_HISTORY");
  }
  const entityType = value.entity_type;
  const entityId = value.entity_id;
  const revisionValue = value.revision;
  const eventType = value.event_type;
  const actorId = value.actor_id;
  const occurredAt = value.occurred_at;
  if (
    typeof entityType !== "string" || !entityType.trim() ||
    typeof entityId !== "string" || !entityId.trim() ||
    typeof revisionValue !== "number" || !Number.isInteger(revisionValue) || revisionValue < 1 ||
    typeof eventType !== "string" || !eventType.trim() ||
    typeof actorId !== "string" || !actorId.trim() ||
    typeof occurredAt !== "string" || !occurredAt.trim()
  ) {
    throw new Error("INVALID_THRESHOLD_HISTORY");
  }
  return {
    entityType,
    entityId,
    revision: revisionValue,
    eventType,
    actorId,
    occurredAt,
    reason: typeof value.reason === "string" ? value.reason : "",
  };
}

export async function loadThresholds(
  transport: ApiTransport,
  context: ProjectContext,
  filters?: ThresholdFilters,
): Promise<ApiResult<readonly ThresholdRecord[]>> {
  const query = new URLSearchParams();
  if (filters?.monitoringSubject) query.set("monitoring_subject", filters.monitoringSubject);
  if (filters?.parameter) query.set("parameter", filters.parameter);
  if (filters?.status) query.set("status", filters.status);
  if (filters?.search) query.set("search", filters.search);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  const result = await transport.get<unknown>(`${thresholdPath(context)}${suffix}`, context);
  if (!result.ok) return result;
  const payload = result.data;
  if (
    !isRecord(payload) ||
    payload.contract_version !== THRESHOLD_API_VERSION ||
    !Array.isArray(payload.thresholds)
  ) {
    return localError("INVALID_THRESHOLD_LIST");
  }
  try {
    return { ok: true, data: payload.thresholds.map((item) => parseThreshold(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_THRESHOLD_LIST");
  }
}

export async function loadThresholdRuns(
  transport: ApiTransport,
  context: ProjectContext,
  thresholdId: string,
): Promise<ApiResult<readonly ThresholdRunRecord[]>> {
  const result = await transport.get<unknown>(
    thresholdPath(context, thresholdId, "runs"),
    context,
  );
  if (!result.ok) return result;
  const payload = result.data;
  if (
    !isRecord(payload) ||
    payload.contract_version !== THRESHOLD_API_VERSION ||
    !Array.isArray(payload.runs)
  ) {
    return localError("INVALID_THRESHOLD_RUNS");
  }
  try {
    return { ok: true, data: payload.runs.map((item) => parseThresholdRun(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_THRESHOLD_RUNS");
  }
}

export async function loadThresholdHistory(
  transport: ApiTransport,
  context: ProjectContext,
  thresholdId: string,
): Promise<ApiResult<readonly ThresholdHistoryEvent[]>> {
  const result = await transport.get<unknown>(
    thresholdPath(context, thresholdId, "history"),
    context,
  );
  if (!result.ok) return result;
  const payload = result.data;
  if (
    !isRecord(payload) ||
    payload.contract_version !== THRESHOLD_API_VERSION ||
    !Array.isArray(payload.events)
  ) {
    return localError("INVALID_THRESHOLD_HISTORY");
  }
  try {
    return { ok: true, data: payload.events.map((item) => parseThresholdHistoryEvent(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_THRESHOLD_HISTORY");
  }
}

function trimmedOrNull(value: string | null): string | null {
  const trimmed = (value ?? "").trim();
  return trimmed ? trimmed : null;
}

export function buildThresholdPayload(input: ThresholdInput): Record<string, unknown> {
  const thresholdId = input.thresholdId.trim();
  const name = input.name.trim();
  const subject = input.monitoringSubject.trim();
  const parameter = input.parameter.trim();
  const status = input.status.trim();
  if (!thresholdId || !name || !subject || !parameter || !status) {
    throw new Error("THRESHOLD_FIELDS_REQUIRED");
  }
  if (!THRESHOLD_SUBJECTS.includes(subject as ThresholdSubject)) {
    throw new Error("INVALID_THRESHOLD_SUBJECT");
  }
  if (!THRESHOLD_PARAMETERS.includes(parameter as ThresholdParameter)) {
    throw new Error("INVALID_THRESHOLD_PARAMETER");
  }
  if (!THRESHOLD_STATUSES.includes(status as ThresholdStatus)) {
    throw new Error("INVALID_THRESHOLD_STATUS");
  }
  const monetary = MONETARY_PARAMETERS.includes(parameter);
  const currency = trimmedOrNull(input.currency);
  if (monetary) {
    if (!currency || !/^[A-Z]{3}$/.test(currency)) throw new Error("INVALID_THRESHOLD_CURRENCY");
  } else if (currency !== null) {
    throw new Error("THRESHOLD_CURRENCY_NOT_ALLOWED");
  }
  const lower = numberText(input.lowerThreshold, "INVALID_THRESHOLD_NUMBER", {
    allowNegative: true,
  });
  const upper = numberText(input.upperThreshold, "INVALID_THRESHOLD_NUMBER", {
    allowNegative: true,
  });
  if (lower === null && upper === null) throw new Error("THRESHOLD_BOUND_REQUIRED");
  if (lower !== null && upper !== null && Number(lower) >= Number(upper)) {
    throw new Error("INVALID_THRESHOLD_BOUNDS");
  }
  const warning = numberText(input.warningLevel, "INVALID_THRESHOLD_LEVEL");
  const issue = numberText(input.issueLevel, "INVALID_THRESHOLD_LEVEL");
  if (warning !== null && issue !== null && Number(issue) <= Number(warning)) {
    throw new Error("INVALID_THRESHOLD_LEVELS");
  }
  return {
    threshold_id: thresholdId,
    name,
    monitoring_subject: subject,
    parameter,
    currency: monetary ? currency : null,
    lower_threshold: lower,
    upper_threshold: upper,
    warning_level: warning,
    issue_level: issue,
    responsible_manager: trimmedOrNull(input.responsibleManager),
    status,
  };
}

export async function saveThreshold(
  transport: ApiTransport,
  context: ProjectContext,
  input: ThresholdInput,
  expectedRevision?: number,
): Promise<ApiResult<ThresholdRecord>> {
  let payload: Record<string, unknown>;
  try {
    payload = buildThresholdPayload(input);
  } catch (error) {
    return localError(error instanceof Error ? error.message : "THRESHOLD_FIELDS_REQUIRED");
  }
  let result: ApiResult<unknown> | undefined;
  if (expectedRevision === undefined) {
    result = await transport.post<Record<string, unknown>, unknown>(
      thresholdPath(context),
      payload,
      context,
      crypto.randomUUID(),
    );
  } else if (transport.patch) {
    result = await transport.patch<Record<string, unknown>, unknown>(
      thresholdPath(context, input.thresholdId.trim()),
      { ...payload, expected_revision: expectedRevision },
      context,
    );
  }
  if (!result) return localError("TRANSPORT_UNAVAILABLE");
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseThreshold(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_THRESHOLD_RESPONSE");
  }
}

export async function deleteThreshold(
  transport: ApiTransport,
  context: ProjectContext,
  thresholdId: string,
  expectedRevision: number,
): Promise<ApiResult<{ deleted: true }>> {
  if (!transport.delete) return localError("TRANSPORT_UNAVAILABLE");
  const result = await transport.delete<Record<string, unknown>, unknown>(
    thresholdPath(context, thresholdId),
    { expected_revision: expectedRevision },
    context,
  );
  if (!result.ok) return result;
  return { ok: true, data: { deleted: true } };
}

export async function monitorThreshold(
  transport: ApiTransport,
  context: ProjectContext,
  thresholdId: string,
): Promise<ApiResult<{ threshold: ThresholdRecord; run: ThresholdRunRecord }>> {
  const result = await transport.post<Record<string, unknown>, unknown>(
    thresholdPath(context, thresholdId, "monitor"),
    {},
    context,
    crypto.randomUUID(),
  );
  if (!result.ok) return result;
  const payload = result.data;
  if (
    !isRecord(payload) ||
    payload.contract_version !== THRESHOLD_API_VERSION ||
    !isRecord(payload.threshold) ||
    !isRecord(payload.run)
  ) {
    return localError("INVALID_THRESHOLD_MONITOR_RESPONSE");
  }
  try {
    return {
      ok: true,
      data: {
        threshold: parseThreshold(payload.threshold),
        run: parseThresholdRun(payload.run),
      },
    };
  } catch (error) {
    return localError(
      error instanceof Error ? error.message : "INVALID_THRESHOLD_MONITOR_RESPONSE",
    );
  }
}

type PageState = {
  status: "loading" | "loaded" | "error";
  errorCode: string | null;
  thresholds: readonly ThresholdRecord[];
  selectedId: string | null;
  mode: "browse" | "create" | "edit";
  editingRevision: number | null;
  draft: ThresholdInput;
  filters: ThresholdFilters;
  runs: readonly ThresholdRunRecord[];
  runsStatus: "idle" | "loading" | "loaded" | "error";
  history: readonly ThresholdHistoryEvent[];
  historyStatus: "idle" | "loading" | "loaded" | "error";
  busy: boolean;
  notice: { kind: "ok" | "error"; message: string } | null;
};

function emptyDraft(): ThresholdInput {
  return {
    thresholdId: "",
    name: "",
    monitoringSubject: "cost",
    parameter: "expense_actual_total",
    currency: "USD",
    lowerThreshold: null,
    upperThreshold: "1000",
    warningLevel: "10",
    issueLevel: "50",
    responsibleManager: null,
    status: "active",
  };
}

function draftFromThreshold(item: ThresholdRecord): ThresholdInput {
  return {
    thresholdId: item.thresholdId,
    name: item.name,
    monitoringSubject: item.monitoringSubject,
    parameter: item.parameter,
    currency: item.currency,
    lowerThreshold: item.lowerThreshold,
    upperThreshold: item.upperThreshold,
    warningLevel: item.warningLevel,
    issueLevel: item.issueLevel,
    responsibleManager: item.responsibleManager,
    status: item.status,
  };
}

export function mountWorkspaceThresholdsPage(
  host: HTMLElement,
  options: ThresholdPageOptions,
): void {
  if (host.dataset.thresholdsMounted === "true") return;
  host.dataset.thresholdsMounted = "true";
  const { transport, context, locale, canWrite } = options;
  const state: PageState = {
    status: "loading",
    errorCode: null,
    thresholds: [],
    selectedId: null,
    mode: "browse",
    editingRevision: null,
    draft: emptyDraft(),
    filters: { monitoringSubject: "", parameter: "", status: "", search: "" },
    runs: [],
    runsStatus: "idle",
    history: [],
    historyStatus: "idle",
    busy: false,
    notice: null,
  };

  const say = (en: string, fa: string): string => text(locale, en, fa);
  const selected = (): ThresholdRecord | null =>
    state.thresholds.find((item) => item.thresholdId === state.selectedId) ?? null;
  const subjectLabel = (value: string): string =>
    ({
      schedule: say("Schedule", "زمان‌بندی"),
      cost: say("Cost", "هزینه"),
      quality: say("Quality", "کیفیت"),
      safety: say("Safety", "ایمنی"),
      resource: say("Resource", "منبع"),
      scope: say("Scope", "دامنه"),
      other: say("Other", "سایر"),
    })[value] ?? value;
  const parameterLabel = (value: string): string =>
    ({
      open_issue_count: say("Open issues", "مسائل باز"),
      expense_actual_total: say("Actual expenses", "هزینهٔ واقعی"),
      budget_balance: say("Budget balance", "مانده بودجه"),
    })[value] ?? value;
  const levelLabel = (value: string): string =>
    ({
      normal: say("Normal", "عادی"),
      warning: say("Warning", "هشدار"),
      issue: say("Issue", "مسئله"),
    })[value] ?? value;

  function renderRegister(): string {
    if (state.status === "loading") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading project thresholds…", "در حال خواندن آستانه‌های پروژه…"))}</div>`;
    }
    if (state.status === "error") {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Project thresholds could not be read", "خواندن آستانه‌های پروژه ناموفق بود"))} (${escapeHtml(state.errorCode ?? "unknown")})</div>`;
    }
    if (!state.thresholds.length) {
      return `<div class="cp-calendar-empty">${escapeHtml(say("No thresholds are stored for this project.", "هیچ آستانه‌ای برای این پروژه ذخیره نشده است."))}</div>`;
    }
    const rows = state.thresholds.map((item) => {
      const active = item.thresholdId === state.selectedId;
      const actions = canWrite
        ? `<button type="button" data-threshold-edit="${escapeHtml(item.thresholdId)}">${escapeHtml(say("Edit", "ویرایش"))}</button><button type="button" data-threshold-delete="${escapeHtml(item.thresholdId)}" data-threshold-revision="${item.revision}">${escapeHtml(say("Delete", "حذف"))}</button>`
        : "—";
      return `<tr data-threshold-row data-threshold-id="${escapeHtml(item.thresholdId)}" tabindex="0" role="button" aria-selected="${active}" class="${active ? "is-selected" : ""}"><td><strong>${escapeHtml(item.thresholdId)}</strong><br><span>${escapeHtml(item.name)}</span></td><td>${escapeHtml(subjectLabel(item.monitoringSubject))}</td><td>${escapeHtml(parameterLabel(item.parameter))}${item.currency ? ` (${escapeHtml(item.currency)})` : ""}</td><td>${escapeHtml(item.lowerThreshold ?? "—")} / ${escapeHtml(item.upperThreshold ?? "—")}</td><td>${escapeHtml(item.warningLevel ?? "—")} / ${escapeHtml(item.issueLevel ?? "—")}</td><td>${escapeHtml(item.responsibleManager ?? "—")}</td><td>${escapeHtml(item.status)}</td><td class="cp-register-actions">${actions}</td></tr>`;
    });
    return `<div class="cp-table-scroll"><table class="cp-register-table"><thead><tr><th>${escapeHtml(say("Threshold", "آستانه"))}</th><th>${escapeHtml(say("Subject", "موضوع"))}</th><th>${escapeHtml(say("Parameter", "پارامتر"))}</th><th>${escapeHtml(say("Lower / Upper", "حد پایین / بالا"))}</th><th>${escapeHtml(say("Warning / Issue", "هشدار / مسئله"))}</th><th>${escapeHtml(say("Manager", "مدیر"))}</th><th>${escapeHtml(say("Status", "وضعیت"))}</th><th></th></tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
  }

  function renderFilters(): string {
    const subjectOptions = THRESHOLD_SUBJECTS.map(
      (value) => `<option value="${value}" ${state.filters.monitoringSubject === value ? "selected" : ""}>${escapeHtml(subjectLabel(value))}</option>`,
    ).join("");
    const parameterOptions = THRESHOLD_PARAMETERS.map(
      (value) => `<option value="${value}" ${state.filters.parameter === value ? "selected" : ""}>${escapeHtml(parameterLabel(value))}</option>`,
    ).join("");
    const statusOptions = THRESHOLD_STATUSES.map(
      (value) => `<option value="${value}" ${state.filters.status === value ? "selected" : ""}>${escapeHtml(value)}</option>`,
    ).join("");
    return `<div class="cp-register-filters">
      <label>${escapeHtml(say("Subject", "موضوع"))}<select name="threshold-subject-filter"><option value="">${escapeHtml(say("All subjects", "همهٔ موضوع‌ها"))}</option>${subjectOptions}</select></label>
      <label>${escapeHtml(say("Parameter", "پارامتر"))}<select name="threshold-parameter-filter"><option value="">${escapeHtml(say("All parameters", "همهٔ پارامترها"))}</option>${parameterOptions}</select></label>
      <label>${escapeHtml(say("Status", "وضعیت"))}<select name="threshold-status-filter"><option value="">${escapeHtml(say("All statuses", "همهٔ وضعیت‌ها"))}</option>${statusOptions}</select></label>
      <label>${escapeHtml(say("Search", "جستجو"))}<input type="search" name="threshold-search-filter" value="${escapeHtml(state.filters.search)}" placeholder="${escapeHtml(say("ID or name", "شناسه یا نام"))}"></label>
    </div>`;
  }

  function renderForm(): string {
    const editing = state.mode === "edit";
    const draft = state.draft;
    const subjectOptions = THRESHOLD_SUBJECTS.map(
      (value) => `<option value="${value}" ${draft.monitoringSubject === value ? "selected" : ""}>${escapeHtml(subjectLabel(value))}</option>`,
    ).join("");
    const parameterOptions = THRESHOLD_PARAMETERS.map(
      (value) => `<option value="${value}" ${draft.parameter === value ? "selected" : ""}>${escapeHtml(parameterLabel(value))}</option>`,
    ).join("");
    const monetary = MONETARY_PARAMETERS.includes(draft.parameter);
    return `<form data-threshold-form class="cp-expense-fields">
      <label>${escapeHtml(say("Threshold ID", "شناسه آستانه"))}<input name="threshold-id" value="${escapeHtml(draft.thresholdId)}" ${editing ? "readonly" : ""} required></label>
      <label>${escapeHtml(say("Name", "نام"))}<input name="threshold-name" value="${escapeHtml(draft.name)}" required></label>
      <label>${escapeHtml(say("Monitoring Subject", "موضوع پایش"))}<select name="threshold-subject">${subjectOptions}</select></label>
      <label>${escapeHtml(say("Parameter", "پارامتر"))}<select name="threshold-parameter">${parameterOptions}</select></label>
      <label>${escapeHtml(say("Currency", "ارز"))}<input name="threshold-currency" value="${escapeHtml(draft.currency ?? "")}" ${monetary ? "" : "disabled"} placeholder="USD"></label>
      <label>${escapeHtml(say("Lower Threshold", "حد پایین"))}<input name="threshold-lower" value="${escapeHtml(draft.lowerThreshold ?? "")}" inputmode="decimal"></label>
      <label>${escapeHtml(say("Upper Threshold", "حد بالا"))}<input name="threshold-upper" value="${escapeHtml(draft.upperThreshold ?? "")}" inputmode="decimal"></label>
      <label>${escapeHtml(say("Warning Level", "سطح هشدار"))}<input name="threshold-warning" value="${escapeHtml(draft.warningLevel ?? "")}" inputmode="decimal"></label>
      <label>${escapeHtml(say("Issue Level", "سطح مسئله"))}<input name="threshold-issue" value="${escapeHtml(draft.issueLevel ?? "")}" inputmode="decimal"></label>
      <label>${escapeHtml(say("Responsible Manager", "مدیر مسئول"))}<input name="threshold-manager" value="${escapeHtml(draft.responsibleManager ?? "")}"></label>
      <label>${escapeHtml(say("Status", "وضعیت"))}<select name="threshold-status">${THRESHOLD_STATUSES.map((value) => `<option value="${value}" ${draft.status === value ? "selected" : ""}>${value}</option>`).join("")}</select></label>
      <div class="cp-calendar-panel-actions"><button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(editing ? say("Save threshold", "ذخیره آستانه") : say("Create threshold", "ایجاد آستانه"))}</button><button type="button" data-threshold-action="cancel">${escapeHtml(say("Cancel", "لغو"))}</button></div>
    </form>`;
  }

  function renderRuns(): string {
    if (state.runsStatus === "loading") {
      return `<p class="cp-register-notice">${escapeHtml(say("Reading monitoring runs…", "در حال خواندن اجراهای پایش…"))}</p>`;
    }
    if (state.runsStatus === "error") {
      return `<p class="cp-register-notice" role="alert">${escapeHtml(say("Monitoring runs could not be read.", "خواندن اجراهای پایش ناموفق بود."))}</p>`;
    }
    if (!state.runs.length) {
      return `<p class="cp-register-notice">${escapeHtml(say("No monitoring run has been recorded for this threshold yet.", "هنوز هیچ اجرای پایشی برای این آستانه ثبت نشده است."))}</p>`;
    }
    const rows = [...state.runs].reverse().map(
      (run) => `<tr><td>${run.runSequence}</td><td>${escapeHtml(run.observedValue)}${run.currency ? ` ${escapeHtml(run.currency)}` : ""}</td><td>${escapeHtml(levelLabel(run.level))}</td><td>${escapeHtml(run.generatedIssueId ?? "—")}</td><td>${escapeHtml(run.occurredAt)}</td></tr>`,
    ).join("");
    return `<table class="cp-register-table"><thead><tr><th>${escapeHtml(say("Run", "اجرا"))}</th><th>${escapeHtml(say("Observed", "مقدار مشاهده‌شده"))}</th><th>${escapeHtml(say("Level", "سطح"))}</th><th>${escapeHtml(say("Generated Issue", "مسئلهٔ ایجادشده"))}</th><th>${escapeHtml(say("Occurred", "زمان"))}</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  function renderHistory(): string {
    if (state.historyStatus === "loading") {
      return `<p class="cp-register-notice">${escapeHtml(say("Reading threshold history…", "در حال خواندن تاریخچهٔ آستانه…"))}</p>`;
    }
    if (state.historyStatus === "error") {
      return `<p class="cp-register-notice" role="alert">${escapeHtml(say("Threshold history could not be read.", "خواندن تاریخچهٔ آستانه ناموفق بود."))}</p>`;
    }
    if (!state.history.length) return "";
    return `<ul class="cp-register-history">${state.history.map(
      (event) => `<li><strong>${escapeHtml(event.eventType)}</strong> · ${escapeHtml(say("revision", "نسخه"))} ${event.revision} · ${escapeHtml(event.actorId)} · ${escapeHtml(event.occurredAt)}${event.reason ? ` · ${escapeHtml(event.reason)}` : ""}</li>`,
    ).join("")}</ul>`;
  }

  function renderDetails(): string {
    if (state.mode !== "browse") return renderForm();
    const item = selected();
    if (!item) {
      return `<p>${escapeHtml(say("Select a threshold from the register to read its stored definition, monitoring runs and history.", "برای خواندن تعریف ذخیره‌شده، اجراهای پایش و تاریخچه، یک آستانه را از فهرست انتخاب کنید."))}</p>`;
    }
    const row = (label: string, value: string | null): string =>
      `<label>${escapeHtml(label)}<input readonly value="${escapeHtml(value ?? say("Not provided", "ارائه نشده"))}"></label>`;
    return `<div class="cp-expense-fields">
      ${row(say("Threshold ID", "شناسه آستانه"), item.thresholdId)}
      ${row(say("Name", "نام"), item.name)}
      ${row(say("Monitoring Subject", "موضوع پایش"), subjectLabel(item.monitoringSubject))}
      ${row(say("Parameter", "پارامتر"), parameterLabel(item.parameter))}
      ${row(say("Currency", "ارز"), item.currency)}
      ${row(say("Lower Threshold", "حد پایین"), item.lowerThreshold)}
      ${row(say("Upper Threshold", "حد بالا"), item.upperThreshold)}
      ${row(say("Warning Level", "سطح هشدار"), item.warningLevel)}
      ${row(say("Issue Level", "سطح مسئله"), item.issueLevel)}
      ${row(say("Responsible Manager", "مدیر مسئول"), item.responsibleManager)}
      ${row(say("Status", "وضعیت"), item.status)}
      ${row(say("Revision", "نسخه"), String(item.revision))}
    </div>
    <div class="cp-calendar-panel-actions">${canWrite ? `<button type="button" data-threshold-monitor data-threshold-id="${escapeHtml(item.thresholdId)}" ${state.busy || item.status !== "active" ? "disabled" : ""}>${escapeHtml(say("Run monitoring", "اجرای پایش"))}</button>` : ""}</div>
    <section class="cp-threshold-runs"><header><strong>${escapeHtml(say("Monitoring Runs", "اجراهای پایش"))}</strong></header>${renderRuns()}</section>
    <section class="cp-threshold-history"><header><strong>${escapeHtml(say("Definition History", "تاریخچهٔ تعریف"))}</strong></header>${renderHistory()}</section>`;
  }

  function render(): void {
    host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(say("Project Thresholds", "آستانه‌های پروژه"))}</strong><div>${canWrite ? `<button type="button" data-threshold-action="new" ${state.busy ? "disabled" : ""}>${escapeHtml(say("New Threshold", "آستانهٔ جدید"))}</button>` : ""}<button type="button" data-threshold-action="reload" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button></div></div>
      ${renderFilters()}
      ${renderRegister()}
      <section class="cp-register-details"><header><strong>${escapeHtml(say("Threshold Details", "جزئیات آستانه"))}</strong><span>${selected() ? escapeHtml(selected()?.thresholdId ?? "") : escapeHtml(say("No selection", "بدون انتخاب"))}</span></header><div class="cp-register-detail-content">${renderDetails()}</div></section>
      ${state.notice ? `<p class="cp-calendar-notice" data-threshold-notice data-state="${state.notice.kind}" role="status">${escapeHtml(state.notice.message)}</p>` : ""}`;
  }

  async function reloadThresholds(keepSelection: string | null): Promise<void> {
    state.status = "loading";
    render();
    const result = await loadThresholds(transport, context, state.filters);
    if (result.ok) {
      state.status = "loaded";
      state.errorCode = null;
      state.thresholds = result.data;
      state.selectedId =
        keepSelection && result.data.some((item) => item.thresholdId === keepSelection)
          ? keepSelection
          : null;
    } else {
      state.status = "error";
      state.errorCode = result.error.code;
    }
    render();
  }

  async function reloadRuns(id: string): Promise<void> {
    state.runsStatus = "loading";
    state.runs = [];
    render();
    const result = await loadThresholdRuns(transport, context, id);
    if (state.selectedId !== id) return;
    state.runsStatus = result.ok ? "loaded" : "error";
    state.runs = result.ok ? result.data : [];
    render();
  }

  async function reloadHistory(id: string): Promise<void> {
    state.historyStatus = "loading";
    state.history = [];
    render();
    const result = await loadThresholdHistory(transport, context, id);
    if (state.selectedId !== id) return;
    state.historyStatus = result.ok ? "loaded" : "error";
    state.history = result.ok ? result.data : [];
    render();
  }

  function selectThreshold(id: string): void {
    state.selectedId = id;
    state.mode = "browse";
    state.notice = null;
    render();
    void reloadRuns(id);
    void reloadHistory(id);
  }

  function beginEdit(item: ThresholdRecord): void {
    state.selectedId = item.thresholdId;
    state.mode = "edit";
    state.editingRevision = item.revision;
    state.draft = draftFromThreshold(item);
    state.notice = null;
    render();
  }

  async function runDelete(id: string, expectedRevision: number): Promise<void> {
    state.busy = true;
    render();
    const result = await deleteThreshold(transport, context, id, expectedRevision);
    state.busy = false;
    if (!result.ok) {
      state.notice = {
        kind: "error",
        message: `${say("Threshold was not deleted", "آستانه حذف نشد")} (${result.error.code})`,
      };
      await reloadThresholds(id);
      return;
    }
    state.notice = { kind: "ok", message: say("Threshold deleted.", "آستانه حذف شد.") };
    state.selectedId = null;
    state.mode = "browse";
    state.runs = [];
    state.history = [];
    await reloadThresholds(null);
  }

  async function runMonitor(id: string): Promise<void> {
    state.busy = true;
    render();
    const result = await monitorThreshold(transport, context, id);
    state.busy = false;
    if (!result.ok) {
      state.notice = {
        kind: "error",
        message: `${say("Monitoring did not complete", "پایش انجام نشد")} (${result.error.code})`,
      };
      render();
      return;
    }
    const level = levelLabel(result.data.run.level);
    const issue = result.data.run.generatedIssueId
      ? ` · ${say("issue", "مسئله")} ${result.data.run.generatedIssueId}`
      : "";
    state.notice = {
      kind: result.data.run.level === "issue" ? "error" : "ok",
      message: `${say("Monitoring recorded", "پایش ثبت شد")} · ${level} · ${result.data.run.observedValue}${result.data.run.currency ? ` ${result.data.run.currency}` : ""}${issue}`,
    };
    await reloadThresholds(id);
    void reloadRuns(id);
    void reloadHistory(id);
  }

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    if (!canWrite && target.closest<HTMLElement>(
      "[data-threshold-edit],[data-threshold-delete],[data-threshold-monitor]",
    )) return;
    const edit = target.closest<HTMLElement>("[data-threshold-edit]")?.dataset.thresholdEdit;
    if (edit) {
      const item = state.thresholds.find((row) => row.thresholdId === edit);
      if (item) beginEdit(item);
      return;
    }
    const remove = target.closest<HTMLElement>("[data-threshold-delete]");
    if (remove?.dataset.thresholdDelete) {
      void runDelete(
        remove.dataset.thresholdDelete,
        Number(remove.dataset.thresholdRevision),
      );
      return;
    }
    const monitor = target.closest<HTMLElement>("[data-threshold-monitor]");
    if (monitor?.dataset.thresholdId) {
      void runMonitor(monitor.dataset.thresholdId);
      return;
    }
    const row = target.closest<HTMLElement>("[data-threshold-row]");
    if (row?.dataset.thresholdId) {
      selectThreshold(row.dataset.thresholdId);
      return;
    }
    const action = target.closest<HTMLElement>("[data-threshold-action]")?.dataset.thresholdAction;
    if (!action) return;
    if (action === "new") {
      if (!canWrite) return;
      state.mode = "create";
      state.editingRevision = null;
      state.draft = emptyDraft();
      state.notice = null;
      render();
    } else if (action === "cancel") {
      state.mode = "browse";
      state.editingRevision = null;
      state.notice = null;
      render();
    } else if (action === "reload") {
      void reloadThresholds(state.selectedId);
    }
  });

  host.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const target = event.target as HTMLElement;
    if (target.matches("input, select, textarea")) return;
    const row = target.closest<HTMLElement>("[data-threshold-row]");
    if (row?.dataset.thresholdId) {
      event.preventDefault();
      selectThreshold(row.dataset.thresholdId);
    }
  });

  host.addEventListener("input", (event) => {
    const target = event.target as HTMLInputElement;
    switch (target.name) {
      case "threshold-id": state.draft.thresholdId = target.value; break;
      case "threshold-name": state.draft.name = target.value; break;
      case "threshold-currency": state.draft.currency = target.value; break;
      case "threshold-lower": state.draft.lowerThreshold = target.value; break;
      case "threshold-upper": state.draft.upperThreshold = target.value; break;
      case "threshold-warning": state.draft.warningLevel = target.value; break;
      case "threshold-issue": state.draft.issueLevel = target.value; break;
      case "threshold-manager": state.draft.responsibleManager = target.value; break;
      default: break;
    }
  });

  host.addEventListener("change", (event) => {
    const target = event.target as HTMLSelectElement | HTMLInputElement;
    switch (target.name) {
      case "threshold-subject": state.draft.monitoringSubject = target.value; break;
      case "threshold-parameter":
        state.draft.parameter = target.value;
        if (!MONETARY_PARAMETERS.includes(target.value)) state.draft.currency = null;
        else if (!state.draft.currency) state.draft.currency = "USD";
        render();
        return;
      case "threshold-status": state.draft.status = target.value; break;
      case "threshold-subject-filter":
        state.filters.monitoringSubject = target.value;
        void reloadThresholds(state.selectedId);
        return;
      case "threshold-parameter-filter":
        state.filters.parameter = target.value;
        void reloadThresholds(state.selectedId);
        return;
      case "threshold-status-filter":
        state.filters.status = target.value;
        void reloadThresholds(state.selectedId);
        return;
      case "threshold-search-filter":
        state.filters.search = target.value.trim();
        void reloadThresholds(state.selectedId);
        return;
      default: break;
    }
  });

  host.addEventListener("submit", (event) => {
    const form = event.target as HTMLFormElement;
    if (!form.matches("[data-threshold-form]")) return;
    event.preventDefault();
    if (state.busy || !canWrite) return;
    void (async () => {
      state.busy = true;
      render();
      const editing = state.mode === "edit";
      const result = await saveThreshold(
        transport,
        context,
        state.draft,
        editing ? state.editingRevision ?? undefined : undefined,
      );
      state.busy = false;
      if (!result.ok) {
        state.notice = {
          kind: "error",
          message: `${say("Threshold was not saved", "آستانه ذخیره نشد")} (${result.error.code})`,
        };
        if (result.error.code === "THRESHOLD_REVISION_CONFLICT") {
          state.mode = "browse";
          await reloadThresholds(state.draft.thresholdId);
          return;
        }
        render();
        return;
      }
      state.notice = { kind: "ok", message: say("Threshold saved.", "آستانه ذخیره شد.") };
      state.mode = "browse";
      state.editingRevision = null;
      await reloadThresholds(result.data.thresholdId);
      if (state.selectedId) {
        void reloadRuns(result.data.thresholdId);
        void reloadHistory(result.data.thresholdId);
      }
    })();
  });

  void reloadThresholds(null);
}
