import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

/**
 * Project risk register client.
 *
 * The server owns exposure: a risk stores probability and impact on a 1..5
 * scale and the API derives the score and exposure level. This module never
 * re-derives authority from the UI; it only renders what the server returned.
 */

export const RISK_API_VERSION = "p6-risk-api.v1";

export const RISK_CATEGORIES = [
  "technical",
  "commercial",
  "schedule",
  "cost",
  "quality",
  "safety",
  "resource",
  "external",
  "other",
] as const;

export const RISK_STATUSES = ["open", "monitoring", "mitigating", "closed"] as const;
export const RISK_STRATEGIES = ["avoid", "transfer", "mitigate", "accept", "escalate"] as const;
export const RISK_EXPOSURES = ["low", "medium", "high", "critical"] as const;

export type RiskCategory = (typeof RISK_CATEGORIES)[number];
export type RiskStatus = (typeof RISK_STATUSES)[number];
export type RiskStrategy = (typeof RISK_STRATEGIES)[number];
export type RiskExposure = (typeof RISK_EXPOSURES)[number];

export type RiskRecord = {
  riskId: string;
  title: string;
  description: string;
  category: string;
  status: string;
  probability: number;
  impact: number;
  score: number;
  exposureLevel: string;
  responseStrategy: string;
  responseOwner: string | null;
  responseDueDate: string | null;
  owner: string;
  responsibleManager: string | null;
  dateIdentified: string;
  closureNote: string | null;
  revision: number;
};

export type RiskHistoryEvent = {
  entityType: string;
  entityId: string;
  revision: number;
  eventType: string;
  actorId: string;
  occurredAt: string;
  reason: string;
};

export type RiskInput = {
  riskId: string;
  title: string;
  description: string;
  category: string;
  status: string;
  probability: number;
  impact: number;
  responseStrategy: string;
  responseOwner: string | null;
  responseDueDate: string | null;
  owner: string;
  responsibleManager: string | null;
  dateIdentified: string;
  closureNote: string | null;
};

export type RiskFilters = {
  category: string;
  status: string;
  responseStrategy: string;
  exposure: string;
  search: string;
};

export type RiskPageOptions = {
  transport: ApiTransport;
  context: ProjectContext;
  locale: string;
  canWrite: boolean;
};

export function riskExposureLevel(probability: number, impact: number): string {
  const score = probability * impact;
  if (score <= 4) return "low";
  if (score <= 9) return "medium";
  if (score <= 16) return "high";
  return "critical";
}

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

function requiredText(value: unknown, code: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(code);
  return value;
}

function revision(value: unknown, code: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1) {
    throw new Error(code);
  }
  return value;
}

function rating(value: unknown, code: string): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1 || value > 5) {
    throw new Error(code);
  }
  return value;
}

function isIsoDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split("-").map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return (
    parsed.getUTCFullYear() === year &&
    parsed.getUTCMonth() === month - 1 &&
    parsed.getUTCDate() === day
  );
}

function isoDate(value: unknown, code: string): string {
  if (typeof value !== "string" || !isIsoDate(value)) {
    throw new Error(code);
  }
  return value;
}

function riskPath(context: ProjectContext, riskId?: string, action?: string): string {
  const base = `/api/projects/${encodeURIComponent(context.project_id)}/risks`;
  if (!riskId) return base;
  return `${base}/${encodeURIComponent(riskId)}${action ? `/${action}` : ""}`;
}

export function parseRisk(value: unknown): RiskRecord {
  if (!isRecord(value)) throw new Error("INVALID_RISK_RECORD");
  if (value.contract_version !== RISK_API_VERSION) {
    throw new Error("INVALID_RISK_RESPONSE");
  }
  const riskId = requiredText(value.risk_id, "INVALID_RISK_RECORD");
  const title = requiredText(value.title, "INVALID_RISK_RECORD");
  const category = value.category;
  const status = value.status;
  const strategy = value.response_strategy;
  const owner = requiredText(value.owner, "INVALID_RISK_RECORD");
  const probability = rating(value.probability, "INVALID_RISK_RECORD");
  const impact = rating(value.impact, "INVALID_RISK_RECORD");
  const score = value.score;
  const exposure = value.exposure_level;
  if (
    typeof category !== "string" || !RISK_CATEGORIES.includes(category as RiskCategory) ||
    typeof status !== "string" || !RISK_STATUSES.includes(status as RiskStatus) ||
    typeof strategy !== "string" || !RISK_STRATEGIES.includes(strategy as RiskStrategy) ||
    typeof exposure !== "string" || !RISK_EXPOSURES.includes(exposure as RiskExposure)
  ) {
    throw new Error("INVALID_RISK_RECORD");
  }
  if (score !== probability * impact) throw new Error("INVALID_RISK_RECORD");
  if (exposure !== riskExposureLevel(probability, impact)) {
    throw new Error("INVALID_RISK_RECORD");
  }
  const description = value.description;
  if (typeof description !== "string") throw new Error("INVALID_RISK_RECORD");
  const closureNote = optionalText(value.closure_note, "INVALID_RISK_RECORD");
  if (status === "closed" && !closureNote) throw new Error("INVALID_RISK_RECORD");
  return {
    riskId,
    title,
    description,
    category,
    status,
    probability,
    impact,
    score,
    exposureLevel: exposure,
    responseStrategy: strategy,
    responseOwner: optionalText(value.response_owner, "INVALID_RISK_RECORD"),
    responseDueDate:
      value.response_due_date === null || value.response_due_date === undefined
        ? null
        : isoDate(value.response_due_date, "INVALID_RISK_RECORD"),
    owner,
    responsibleManager: optionalText(value.responsible_manager, "INVALID_RISK_RECORD"),
    dateIdentified: isoDate(value.date_identified, "INVALID_RISK_RECORD"),
    closureNote,
    revision: revision(value.revision, "INVALID_RISK_RECORD"),
  };
}

export function parseRiskHistoryEvent(value: unknown): RiskHistoryEvent {
  if (!isRecord(value)) throw new Error("INVALID_RISK_HISTORY");
  if (value.contract_version !== RISK_API_VERSION) {
    throw new Error("INVALID_RISK_HISTORY");
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
    throw new Error("INVALID_RISK_HISTORY");
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

export async function loadRisks(
  transport: ApiTransport,
  context: ProjectContext,
  filters?: RiskFilters,
): Promise<ApiResult<readonly RiskRecord[]>> {
  const query = new URLSearchParams();
  if (filters?.category) query.set("category", filters.category);
  if (filters?.status) query.set("status", filters.status);
  if (filters?.responseStrategy) query.set("response_strategy", filters.responseStrategy);
  if (filters?.exposure) query.set("exposure", filters.exposure);
  if (filters?.search) query.set("search", filters.search);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  const result = await transport.get<unknown>(`${riskPath(context)}${suffix}`, context);
  if (!result.ok) return result;
  const payload = result.data;
  if (
    !isRecord(payload) ||
    payload.contract_version !== RISK_API_VERSION ||
    !Array.isArray(payload.risks)
  ) {
    return localError("INVALID_RISK_LIST");
  }
  try {
    return { ok: true, data: payload.risks.map((item) => parseRisk(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_RISK_LIST");
  }
}

export async function loadRiskHistory(
  transport: ApiTransport,
  context: ProjectContext,
  riskId: string,
): Promise<ApiResult<readonly RiskHistoryEvent[]>> {
  const result = await transport.get<unknown>(riskPath(context, riskId, "history"), context);
  if (!result.ok) return result;
  const payload = result.data;
  if (
    !isRecord(payload) ||
    payload.contract_version !== RISK_API_VERSION ||
    !Array.isArray(payload.events)
  ) {
    return localError("INVALID_RISK_HISTORY");
  }
  try {
    return { ok: true, data: payload.events.map((item) => parseRiskHistoryEvent(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_RISK_HISTORY");
  }
}

function trimmedOrNull(value: string | null): string | null {
  const trimmed = (value ?? "").trim();
  return trimmed ? trimmed : null;
}

export function buildRiskPayload(input: RiskInput): Record<string, unknown> {
  const riskId = input.riskId.trim();
  const title = input.title.trim();
  const category = input.category.trim();
  const status = input.status.trim();
  const strategy = input.responseStrategy.trim();
  const owner = input.owner.trim();
  if (!riskId || !title || !category || !status || !strategy || !owner) {
    throw new Error("RISK_FIELDS_REQUIRED");
  }
  if (!RISK_CATEGORIES.includes(category as RiskCategory)) {
    throw new Error("INVALID_RISK_CATEGORY");
  }
  if (!RISK_STATUSES.includes(status as RiskStatus)) {
    throw new Error("INVALID_RISK_STATUS");
  }
  if (!RISK_STRATEGIES.includes(strategy as RiskStrategy)) {
    throw new Error("INVALID_RISK_STRATEGY");
  }
  if (!Number.isInteger(input.probability) || input.probability < 1 || input.probability > 5) {
    throw new Error("INVALID_RISK_PROBABILITY");
  }
  if (!Number.isInteger(input.impact) || input.impact < 1 || input.impact > 5) {
    throw new Error("INVALID_RISK_IMPACT");
  }
  const dateIdentified = input.dateIdentified.trim();
  if (!isIsoDate(dateIdentified)) {
    throw new Error("INVALID_RISK_DATE_IDENTIFIED");
  }
  const due = trimmedOrNull(input.responseDueDate);
  if (due !== null) {
    if (!isIsoDate(due)) throw new Error("INVALID_RISK_RESPONSE_DUE_DATE");
    if (due < dateIdentified) throw new Error("RISK_DATE_ORDER_INVALID");
  }
  const closureNote = trimmedOrNull(input.closureNote);
  if (status === "closed" && !closureNote) throw new Error("RISK_CLOSURE_NOTE_REQUIRED");
  return {
    risk_id: riskId,
    title,
    description: input.description.trim(),
    category,
    status,
    probability: input.probability,
    impact: input.impact,
    response_strategy: strategy,
    response_owner: trimmedOrNull(input.responseOwner),
    response_due_date: due,
    owner,
    responsible_manager: trimmedOrNull(input.responsibleManager),
    date_identified: dateIdentified,
    closure_note: closureNote,
  };
}

export async function saveRisk(
  transport: ApiTransport,
  context: ProjectContext,
  input: RiskInput,
  expectedRevision?: number,
): Promise<ApiResult<RiskRecord>> {
  let payload: Record<string, unknown>;
  try {
    payload = buildRiskPayload(input);
  } catch (error) {
    return localError(error instanceof Error ? error.message : "RISK_FIELDS_REQUIRED");
  }
  let result: ApiResult<unknown> | undefined;
  if (expectedRevision === undefined) {
    result = await transport.post<Record<string, unknown>, unknown>(
      riskPath(context),
      payload,
      context,
      crypto.randomUUID(),
    );
  } else if (transport.patch) {
    result = await transport.patch<Record<string, unknown>, unknown>(
      riskPath(context, input.riskId.trim()),
      { ...payload, expected_revision: expectedRevision },
      context,
    );
  }
  if (!result) return localError("TRANSPORT_UNAVAILABLE");
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseRisk(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_RISK_RESPONSE");
  }
}

export async function deleteRisk(
  transport: ApiTransport,
  context: ProjectContext,
  riskId: string,
  expectedRevision: number,
): Promise<ApiResult<{ deleted: true }>> {
  if (!transport.delete) return localError("TRANSPORT_UNAVAILABLE");
  const result = await transport.delete<Record<string, unknown>, unknown>(
    riskPath(context, riskId),
    { expected_revision: expectedRevision },
    context,
  );
  if (!result.ok) return result;
  return { ok: true, data: { deleted: true } };
}

type PageState = {
  status: "loading" | "loaded" | "error";
  errorCode: string | null;
  risks: readonly RiskRecord[];
  selectedId: string | null;
  mode: "browse" | "create" | "edit";
  editingRevision: number | null;
  draft: RiskInput;
  filters: RiskFilters;
  history: readonly RiskHistoryEvent[];
  historyStatus: "idle" | "loading" | "loaded" | "error";
  busy: boolean;
  notice: { kind: "ok" | "error"; message: string } | null;
};

function emptyDraft(): RiskInput {
  return {
    riskId: "",
    title: "",
    description: "",
    category: "schedule",
    status: "open",
    probability: 3,
    impact: 3,
    responseStrategy: "mitigate",
    responseOwner: null,
    responseDueDate: null,
    owner: "",
    responsibleManager: null,
    dateIdentified: new Date().toISOString().slice(0, 10),
    closureNote: null,
  };
}

function draftFromRisk(item: RiskRecord): RiskInput {
  return {
    riskId: item.riskId,
    title: item.title,
    description: item.description,
    category: item.category,
    status: item.status,
    probability: item.probability,
    impact: item.impact,
    responseStrategy: item.responseStrategy,
    responseOwner: item.responseOwner,
    responseDueDate: item.responseDueDate,
    owner: item.owner,
    responsibleManager: item.responsibleManager,
    dateIdentified: item.dateIdentified,
    closureNote: item.closureNote,
  };
}

export function mountWorkspaceRisksPage(host: HTMLElement, options: RiskPageOptions): void {
  if (host.dataset.risksMounted === "true") return;
  host.dataset.risksMounted = "true";
  const { transport, context, locale, canWrite } = options;
  const state: PageState = {
    status: "loading",
    errorCode: null,
    risks: [],
    selectedId: null,
    mode: "browse",
    editingRevision: null,
    draft: emptyDraft(),
    filters: { category: "", status: "", responseStrategy: "", exposure: "", search: "" },
    history: [],
    historyStatus: "idle",
    busy: false,
    notice: null,
  };

  const say = (en: string, fa: string): string => text(locale, en, fa);
  const selected = (): RiskRecord | null =>
    state.risks.find((item) => item.riskId === state.selectedId) ?? null;
  const categoryLabel = (value: string): string =>
    ({
      technical: say("Technical", "فنی"),
      commercial: say("Commercial", "تجاری"),
      schedule: say("Schedule", "زمان‌بندی"),
      cost: say("Cost", "هزینه"),
      quality: say("Quality", "کیفیت"),
      safety: say("Safety", "ایمنی"),
      resource: say("Resource", "منبع"),
      external: say("External", "بیرونی"),
      other: say("Other", "سایر"),
    })[value] ?? value;
  const statusLabel = (value: string): string =>
    ({
      open: say("Open", "باز"),
      monitoring: say("Monitoring", "پایش"),
      mitigating: say("Mitigating", "کاهش اثر"),
      closed: say("Closed", "بسته"),
    })[value] ?? value;
  const strategyLabel = (value: string): string =>
    ({
      avoid: say("Avoid", "اجتناب"),
      transfer: say("Transfer", "انتقال"),
      mitigate: say("Mitigate", "کاهش"),
      accept: say("Accept", "پذیرش"),
      escalate: say("Escalate", "ارجاع"),
    })[value] ?? value;
  const exposureLabel = (value: string): string =>
    ({
      low: say("Low", "کم"),
      medium: say("Medium", "متوسط"),
      high: say("High", "زیاد"),
      critical: say("Critical", "بحرانی"),
    })[value] ?? value;

  function renderMatrix(): string {
    const counts = new Map<string, number>();
    for (const item of state.risks) {
      const key = `${item.probability}-${item.impact}`;
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    const head = [1, 2, 3, 4, 5]
      .map((impact) => `<th scope="col">${impact}</th>`)
      .join("");
    const rows = [5, 4, 3, 2, 1]
      .map((probability) => {
        const cells = [1, 2, 3, 4, 5]
          .map((impact) => {
            const count = counts.get(`${probability}-${impact}`) ?? 0;
            const level = riskExposureLevel(probability, impact);
            return `<td data-risk-matrix-cell="${probability}-${impact}" data-exposure="${level}" class="cp-risk-cell cp-risk-cell-${level}">${count || ""}</td>`;
          })
          .join("");
        return `<tr><th scope="row">${probability}</th>${cells}</tr>`;
      })
      .join("");
    return `<table class="cp-risk-matrix" data-risk-matrix aria-label="${escapeHtml(say("Risk scoring matrix", "ماتریس امتیاز ریسک"))}"><caption>${escapeHtml(say("Probability × Impact", "احتمال × اثر"))}</caption><thead><tr><th></th>${head}</tr></thead><tbody>${rows}</tbody></table>`;
  }

  function renderRegister(): string {
    if (state.status === "loading") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading project risks…", "در حال خواندن ریسک‌های پروژه…"))}</div>`;
    }
    if (state.status === "error") {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Project risks could not be read", "خواندن ریسک‌های پروژه ناموفق بود"))} (${escapeHtml(state.errorCode ?? "unknown")})</div>`;
    }
    if (!state.risks.length) {
      return `<div class="cp-calendar-empty">${escapeHtml(say("No risks are stored for this project.", "هیچ ریسکی برای این پروژه ذخیره نشده است."))}</div>`;
    }
    const rows = state.risks.map((item) => {
      const active = item.riskId === state.selectedId;
      const actions = canWrite
        ? `<button type="button" data-risk-edit="${escapeHtml(item.riskId)}">${escapeHtml(say("Edit", "ویرایش"))}</button><button type="button" data-risk-delete="${escapeHtml(item.riskId)}" data-risk-revision="${item.revision}">${escapeHtml(say("Delete", "حذف"))}</button>`
        : "—";
      return `<tr data-risk-row data-risk-id="${escapeHtml(item.riskId)}" tabindex="0" role="button" aria-selected="${active}" class="${active ? "is-selected" : ""}"><td><strong>${escapeHtml(item.riskId)}</strong><br><span>${escapeHtml(item.title)}</span></td><td>${escapeHtml(categoryLabel(item.category))}</td><td>${item.probability} × ${item.impact}</td><td><strong>${item.score}</strong> · ${escapeHtml(exposureLabel(item.exposureLevel))}</td><td>${escapeHtml(strategyLabel(item.responseStrategy))}</td><td>${escapeHtml(item.owner)}</td><td>${escapeHtml(statusLabel(item.status))}</td><td class="cp-register-actions">${actions}</td></tr>`;
    });
    return `<div class="cp-table-scroll"><table class="cp-register-table"><thead><tr><th>${escapeHtml(say("Risk", "ریسک"))}</th><th>${escapeHtml(say("Category", "دسته"))}</th><th>${escapeHtml(say("Probability × Impact", "احتمال × اثر"))}</th><th>${escapeHtml(say("Score / Exposure", "امتیاز / مواجهه"))}</th><th>${escapeHtml(say("Response", "پاسخ"))}</th><th>${escapeHtml(say("Owner", "مسئول"))}</th><th>${escapeHtml(say("Status", "وضعیت"))}</th><th></th></tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
  }

  function renderFilters(): string {
    const categoryOptions = RISK_CATEGORIES.map(
      (value) => `<option value="${value}" ${state.filters.category === value ? "selected" : ""}>${escapeHtml(categoryLabel(value))}</option>`,
    ).join("");
    const statusOptions = RISK_STATUSES.map(
      (value) => `<option value="${value}" ${state.filters.status === value ? "selected" : ""}>${escapeHtml(statusLabel(value))}</option>`,
    ).join("");
    const strategyOptions = RISK_STRATEGIES.map(
      (value) => `<option value="${value}" ${state.filters.responseStrategy === value ? "selected" : ""}>${escapeHtml(strategyLabel(value))}</option>`,
    ).join("");
    const exposureOptions = RISK_EXPOSURES.map(
      (value) => `<option value="${value}" ${state.filters.exposure === value ? "selected" : ""}>${escapeHtml(exposureLabel(value))}</option>`,
    ).join("");
    return `<div class="cp-register-filters">
      <label>${escapeHtml(say("Category", "دسته"))}<select name="risk-category-filter"><option value="">${escapeHtml(say("All categories", "همهٔ دسته‌ها"))}</option>${categoryOptions}</select></label>
      <label>${escapeHtml(say("Status", "وضعیت"))}<select name="risk-status-filter"><option value="">${escapeHtml(say("All statuses", "همهٔ وضعیت‌ها"))}</option>${statusOptions}</select></label>
      <label>${escapeHtml(say("Response", "پاسخ"))}<select name="risk-strategy-filter"><option value="">${escapeHtml(say("All responses", "همهٔ پاسخ‌ها"))}</option>${strategyOptions}</select></label>
      <label>${escapeHtml(say("Exposure", "مواجهه"))}<select name="risk-exposure-filter"><option value="">${escapeHtml(say("All exposures", "همهٔ مواجهه‌ها"))}</option>${exposureOptions}</select></label>
      <label>${escapeHtml(say("Search", "جستجو"))}<input type="search" name="risk-search-filter" value="${escapeHtml(state.filters.search)}" placeholder="${escapeHtml(say("ID, title or owner", "شناسه، عنوان یا مسئول"))}"></label>
    </div>`;
  }

  function renderForm(): string {
    const editing = state.mode === "edit";
    const draft = state.draft;
    const categoryOptions = RISK_CATEGORIES.map(
      (value) => `<option value="${value}" ${draft.category === value ? "selected" : ""}>${escapeHtml(categoryLabel(value))}</option>`,
    ).join("");
    const statusOptions = RISK_STATUSES.map(
      (value) => `<option value="${value}" ${draft.status === value ? "selected" : ""}>${escapeHtml(statusLabel(value))}</option>`,
    ).join("");
    const strategyOptions = RISK_STRATEGIES.map(
      (value) => `<option value="${value}" ${draft.responseStrategy === value ? "selected" : ""}>${escapeHtml(strategyLabel(value))}</option>`,
    ).join("");
    const levelOptions = (value: number): string =>
      [1, 2, 3, 4, 5]
        .map((option) => `<option value="${option}" ${value === option ? "selected" : ""}>${option}</option>`)
        .join("");
    return `<form data-risk-form class="cp-expense-fields">
      <label>${escapeHtml(say("Risk ID", "شناسه ریسک"))}<input name="risk-id" value="${escapeHtml(draft.riskId)}" ${editing ? "readonly" : ""} required></label>
      <label>${escapeHtml(say("Title", "عنوان"))}<input name="risk-title" value="${escapeHtml(draft.title)}" required></label>
      <label>${escapeHtml(say("Category", "دسته"))}<select name="risk-category">${categoryOptions}</select></label>
      <label>${escapeHtml(say("Status", "وضعیت"))}<select name="risk-status">${statusOptions}</select></label>
      <label>${escapeHtml(say("Probability", "احتمال"))}<select name="risk-probability">${levelOptions(draft.probability)}</select></label>
      <label>${escapeHtml(say("Impact", "اثر"))}<select name="risk-impact">${levelOptions(draft.impact)}</select></label>
      <label>${escapeHtml(say("Response Strategy", "راهبرد پاسخ"))}<select name="risk-strategy">${strategyOptions}</select></label>
      <label>${escapeHtml(say("Owner", "مسئول"))}<input name="risk-owner" value="${escapeHtml(draft.owner)}" required></label>
      <label>${escapeHtml(say("Response Owner", "مسئول پاسخ"))}<input name="risk-response-owner" value="${escapeHtml(draft.responseOwner ?? "")}"></label>
      <label>${escapeHtml(say("Response Due", "مهلت پاسخ"))}<input type="date" name="risk-response-due" value="${escapeHtml(draft.responseDueDate ?? "")}"></label>
      <label>${escapeHtml(say("Responsible Manager", "مدیر مسئول"))}<input name="risk-manager" value="${escapeHtml(draft.responsibleManager ?? "")}"></label>
      <label>${escapeHtml(say("Date Identified", "تاریخ شناسایی"))}<input type="date" name="risk-identified" value="${escapeHtml(draft.dateIdentified)}" required></label>
      <label class="cp-field-wide">${escapeHtml(say("Description", "شرح"))}<textarea name="risk-description" rows="2">${escapeHtml(draft.description)}</textarea></label>
      <label class="cp-field-wide">${escapeHtml(say("Closure Note", "یادداشت بستن"))}<input name="risk-closure-note" value="${escapeHtml(draft.closureNote ?? "")}"></label>
      <div class="cp-calendar-panel-actions"><button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(editing ? say("Save risk", "ذخیره ریسک") : say("Create risk", "ایجاد ریسک"))}</button><button type="button" data-risk-action="cancel">${escapeHtml(say("Cancel", "لغو"))}</button></div>
    </form>`;
  }

  function renderHistory(): string {
    if (state.historyStatus === "loading") {
      return `<p class="cp-register-notice">${escapeHtml(say("Reading risk history…", "در حال خواندن تاریخچهٔ ریسک…"))}</p>`;
    }
    if (state.historyStatus === "error") {
      return `<p class="cp-register-notice" role="alert">${escapeHtml(say("Risk history could not be read.", "خواندن تاریخچهٔ ریسک ناموفق بود."))}</p>`;
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
      return `<p>${escapeHtml(say("Select a risk from the register to read its stored exposure, response and history.", "برای خواندن مواجهه، پاسخ و تاریخچهٔ ذخیره‌شده، یک ریسک را از فهرست انتخاب کنید."))}</p>`;
    }
    const row = (label: string, value: string | null): string =>
      `<label>${escapeHtml(label)}<input readonly value="${escapeHtml(value ?? say("Not provided", "ارائه نشده"))}"></label>`;
    return `<div class="cp-expense-fields">
      ${row(say("Risk ID", "شناسه ریسک"), item.riskId)}
      ${row(say("Title", "عنوان"), item.title)}
      ${row(say("Category", "دسته"), categoryLabel(item.category))}
      ${row(say("Status", "وضعیت"), statusLabel(item.status))}
      ${row(say("Probability × Impact", "احتمال × اثر"), `${item.probability} × ${item.impact}`)}
      ${row(say("Score", "امتیاز"), String(item.score))}
      ${row(say("Exposure", "مواجهه"), exposureLabel(item.exposureLevel))}
      ${row(say("Response Strategy", "راهبرد پاسخ"), strategyLabel(item.responseStrategy))}
      ${row(say("Owner", "مسئول"), item.owner)}
      ${row(say("Response Owner", "مسئول پاسخ"), item.responseOwner)}
      ${row(say("Response Due", "مهلت پاسخ"), item.responseDueDate)}
      ${row(say("Responsible Manager", "مدیر مسئول"), item.responsibleManager)}
      ${row(say("Date Identified", "تاریخ شناسایی"), item.dateIdentified)}
      ${row(say("Closure Note", "یادداشت بستن"), item.closureNote)}
      ${row(say("Revision", "نسخه"), String(item.revision))}
      ${row(say("Description", "شرح"), item.description || null)}
    </div>
    <div class="cp-calendar-panel-actions">${canWrite ? `<button type="button" data-risk-edit="${escapeHtml(item.riskId)}">${escapeHtml(say("Edit risk", "ویرایش ریسک"))}</button>` : ""}</div>
    <section class="cp-risk-history"><header><strong>${escapeHtml(say("Risk History", "تاریخچهٔ ریسک"))}</strong></header>${renderHistory()}</section>`;
  }

  function render(): void {
    host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(say("Project Risks", "ریسک‌های پروژه"))}</strong><div>${canWrite ? `<button type="button" data-risk-action="new" ${state.busy ? "disabled" : ""}>${escapeHtml(say("New Risk", "ریسک جدید"))}</button>` : ""}<button type="button" data-risk-action="reload" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button></div></div>
      ${renderFilters()}
      <div class="cp-risk-body"><div class="cp-risk-register">${renderRegister()}</div><aside class="cp-risk-matrix-panel">${renderMatrix()}</aside></div>
      <section class="cp-register-details"><header><strong>${escapeHtml(say("Risk Details", "جزئیات ریسک"))}</strong><span>${selected() ? escapeHtml(selected()?.riskId ?? "") : escapeHtml(say("No selection", "بدون انتخاب"))}</span></header><div class="cp-register-detail-content">${renderDetails()}</div></section>
      ${state.notice ? `<p class="cp-calendar-notice" data-risk-notice data-state="${state.notice.kind}" role="status">${escapeHtml(state.notice.message)}</p>` : ""}`;
  }

  async function reloadRisks(keepSelection: string | null): Promise<void> {
    state.status = "loading";
    render();
    const result = await loadRisks(transport, context, state.filters);
    if (result.ok) {
      state.status = "loaded";
      state.errorCode = null;
      state.risks = result.data;
      state.selectedId =
        keepSelection && result.data.some((item) => item.riskId === keepSelection)
          ? keepSelection
          : null;
    } else {
      state.status = "error";
      state.errorCode = result.error.code;
    }
    render();
  }

  async function reloadHistory(id: string): Promise<void> {
    state.historyStatus = "loading";
    state.history = [];
    render();
    const result = await loadRiskHistory(transport, context, id);
    if (state.selectedId !== id) return;
    state.historyStatus = result.ok ? "loaded" : "error";
    state.history = result.ok ? result.data : [];
    render();
  }

  function selectRisk(id: string): void {
    state.selectedId = id;
    state.mode = "browse";
    state.notice = null;
    render();
    void reloadHistory(id);
  }

  function beginEdit(item: RiskRecord): void {
    state.selectedId = item.riskId;
    state.mode = "edit";
    state.editingRevision = item.revision;
    state.draft = draftFromRisk(item);
    state.notice = null;
    render();
  }

  async function runDelete(id: string, expectedRevision: number): Promise<void> {
    state.busy = true;
    render();
    const result = await deleteRisk(transport, context, id, expectedRevision);
    state.busy = false;
    if (!result.ok) {
      state.notice = {
        kind: "error",
        message: `${say("Risk was not deleted", "ریسک حذف نشد")} (${result.error.code})`,
      };
      await reloadRisks(id);
      return;
    }
    state.notice = { kind: "ok", message: say("Risk deleted.", "ریسک حذف شد.") };
    state.selectedId = null;
    state.mode = "browse";
    state.history = [];
    await reloadRisks(null);
  }

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    if (!canWrite && target.closest<HTMLElement>("[data-risk-edit],[data-risk-delete]")) return;
    const edit = target.closest<HTMLElement>("[data-risk-edit]")?.dataset.riskEdit;
    if (edit) {
      const item = state.risks.find((row) => row.riskId === edit);
      if (item) beginEdit(item);
      return;
    }
    const remove = target.closest<HTMLElement>("[data-risk-delete]");
    if (remove?.dataset.riskDelete) {
      void runDelete(remove.dataset.riskDelete, Number(remove.dataset.riskRevision));
      return;
    }
    const row = target.closest<HTMLElement>("[data-risk-row]");
    if (row?.dataset.riskId) {
      selectRisk(row.dataset.riskId);
      return;
    }
    const action = target.closest<HTMLElement>("[data-risk-action]")?.dataset.riskAction;
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
      void reloadRisks(state.selectedId);
    }
  });

  host.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const target = event.target as HTMLElement;
    if (target.matches("input, select, textarea")) return;
    const row = target.closest<HTMLElement>("[data-risk-row]");
    if (row?.dataset.riskId) {
      event.preventDefault();
      selectRisk(row.dataset.riskId);
    }
  });

  host.addEventListener("input", (event) => {
    const target = event.target as HTMLInputElement | HTMLTextAreaElement;
    switch (target.name) {
      case "risk-id": state.draft.riskId = target.value; break;
      case "risk-title": state.draft.title = target.value; break;
      case "risk-description": state.draft.description = target.value; break;
      case "risk-owner": state.draft.owner = target.value; break;
      case "risk-response-owner": state.draft.responseOwner = target.value; break;
      case "risk-response-due": state.draft.responseDueDate = target.value; break;
      case "risk-manager": state.draft.responsibleManager = target.value; break;
      case "risk-identified": state.draft.dateIdentified = target.value; break;
      case "risk-closure-note": state.draft.closureNote = target.value; break;
      default: break;
    }
  });

  host.addEventListener("change", (event) => {
    const target = event.target as HTMLSelectElement | HTMLInputElement;
    switch (target.name) {
      case "risk-category": state.draft.category = target.value; break;
      case "risk-status": state.draft.status = target.value; break;
      case "risk-probability": state.draft.probability = Number(target.value); break;
      case "risk-impact": state.draft.impact = Number(target.value); break;
      case "risk-strategy": state.draft.responseStrategy = target.value; break;
      case "risk-category-filter":
        state.filters.category = target.value;
        void reloadRisks(state.selectedId);
        return;
      case "risk-status-filter":
        state.filters.status = target.value;
        void reloadRisks(state.selectedId);
        return;
      case "risk-strategy-filter":
        state.filters.responseStrategy = target.value;
        void reloadRisks(state.selectedId);
        return;
      case "risk-exposure-filter":
        state.filters.exposure = target.value;
        void reloadRisks(state.selectedId);
        return;
      case "risk-search-filter":
        state.filters.search = target.value.trim();
        void reloadRisks(state.selectedId);
        return;
      default: break;
    }
  });

  host.addEventListener("submit", (event) => {
    const form = event.target as HTMLFormElement;
    if (!form.matches("[data-risk-form]")) return;
    event.preventDefault();
    if (state.busy || !canWrite) return;
    void (async () => {
      state.busy = true;
      render();
      const editing = state.mode === "edit";
      const result = await saveRisk(
        transport,
        context,
        state.draft,
        editing ? state.editingRevision ?? undefined : undefined,
      );
      state.busy = false;
      if (!result.ok) {
        state.notice = {
          kind: "error",
          message: `${say("Risk was not saved", "ریسک ذخیره نشد")} (${result.error.code})`,
        };
        if (result.error.code === "RISK_REVISION_CONFLICT") {
          state.mode = "browse";
          await reloadRisks(state.draft.riskId);
          return;
        }
        render();
        return;
      }
      state.notice = { kind: "ok", message: say("Risk saved.", "ریسک ذخیره شد.") };
      state.mode = "browse";
      state.editingRevision = null;
      await reloadRisks(result.data.riskId);
      if (state.selectedId) void reloadHistory(result.data.riskId);
    })();
  });

  void reloadRisks(null);
}
