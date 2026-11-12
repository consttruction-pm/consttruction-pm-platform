import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

/**
 * Project issue register client.
 *
 * Issues are project records with their own revision. This module never
 * computes status or priority rules locally: it sends the requested state and
 * surfaces the authoritative code (for example ISSUE_REVISION_CONFLICT) so the
 * user can reload instead of losing a competing write.
 */

export const ISSUE_API_VERSION = "p6-issue-api.v1";

export const ISSUE_TYPES = ["cost", "schedule", "quality", "safety", "scope", "resource", "other"] as const;
export const ISSUE_STATUSES = ["open", "in_progress", "resolved", "closed"] as const;
export const ISSUE_PRIORITIES = ["low", "normal", "high", "critical"] as const;

export type IssueType = (typeof ISSUE_TYPES)[number];
export type IssueStatus = (typeof ISSUE_STATUSES)[number];
export type IssuePriority = (typeof ISSUE_PRIORITIES)[number];

export type IssueRecord = {
  issueId: string;
  title: string;
  description: string;
  issueType: string;
  status: string;
  priority: string;
  owner: string;
  responsibleManager: string | null;
  dateIdentified: string;
  dueDate: string | null;
  wbsId: string | null;
  activityId: string | null;
  documentRefs: readonly string[];
  resolutionNote: string | null;
  recordRevision: number;
  createdAt: string;
  updatedAt: string;
};

export type IssueHistoryEvent = {
  issueId: string;
  sequence: number;
  eventType: string;
  actorId: string;
  occurredAt: string;
  detail: Record<string, unknown>;
};

export type IssueInput = {
  issueId: string;
  title: string;
  description: string;
  issueType: string;
  status: string;
  priority: string;
  owner: string;
  responsibleManager: string | null;
  dateIdentified: string;
  dueDate: string | null;
  wbsId: string | null;
  activityId: string | null;
  documentRefs: readonly string[];
  resolutionNote: string | null;
};

export type IssueFilters = {
  status: string;
  priority: string;
  issueType: string;
  search: string;
};

export type IssueActivityOption = { id: string; code: string; name: string };
export type IssueWbsOption = { id: string; code: string; name: string };

export type IssuePageOptions = {
  transport: ApiTransport;
  context: ProjectContext;
  locale: string;
  activities: readonly IssueActivityOption[];
  wbsNodes: readonly IssueWbsOption[];
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

function requiredText(value: unknown, code: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(code);
  return value;
}

function integerValue(value: unknown, code: string): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 1) throw new Error(code);
  return value;
}

export function parseIssue(value: unknown): IssueRecord {
  if (!isRecord(value)) throw new Error("INVALID_ISSUE_RECORD");
  if (value.contract_version !== ISSUE_API_VERSION || value.kind !== "p6_issue") {
    throw new Error("INVALID_ISSUE_RESPONSE");
  }
  const payload = value.issue;
  if (!isRecord(payload)) throw new Error("INVALID_ISSUE_RESPONSE");
  const refs = payload.document_refs;
  if (refs !== undefined && (!Array.isArray(refs) || refs.some((item) => typeof item !== "string"))) {
    throw new Error("INVALID_ISSUE_RECORD");
  }
  return {
    issueId: requiredText(payload.issue_id, "INVALID_ISSUE_RECORD"),
    title: requiredText(payload.title, "INVALID_ISSUE_RECORD"),
    description: typeof payload.description === "string" ? payload.description : "",
    issueType: requiredText(payload.issue_type, "INVALID_ISSUE_RECORD"),
    status: requiredText(payload.status, "INVALID_ISSUE_RECORD"),
    priority: requiredText(payload.priority, "INVALID_ISSUE_RECORD"),
    owner: requiredText(payload.owner, "INVALID_ISSUE_RECORD"),
    responsibleManager: optionalText(payload.responsible_manager, "INVALID_ISSUE_RECORD"),
    dateIdentified: requiredText(payload.date_identified, "INVALID_ISSUE_RECORD"),
    dueDate: optionalText(payload.due_date, "INVALID_ISSUE_RECORD"),
    wbsId: optionalText(payload.wbs_id, "INVALID_ISSUE_RECORD"),
    activityId: optionalText(payload.activity_id, "INVALID_ISSUE_RECORD"),
    documentRefs: (refs as string[] | undefined) ?? [],
    resolutionNote: optionalText(payload.resolution_note, "INVALID_ISSUE_RECORD"),
    recordRevision: integerValue(payload.record_revision, "INVALID_ISSUE_RECORD"),
    createdAt: requiredText(payload.created_at, "INVALID_ISSUE_RECORD"),
    updatedAt: requiredText(payload.updated_at, "INVALID_ISSUE_RECORD"),
  };
}

export function parseIssueHistory(value: unknown): IssueHistoryEvent[] {
  if (!isRecord(value) || value.contract_version !== ISSUE_API_VERSION || !Array.isArray(value.events)) {
    throw new Error("INVALID_ISSUE_HISTORY");
  }
  return value.events.map((entry) => {
    if (!isRecord(entry) || !isRecord(entry.event)) throw new Error("INVALID_ISSUE_HISTORY");
    const event = entry.event;
    const detail = isRecord(event.detail) ? event.detail : {};
    return {
      issueId: requiredText(event.issue_id, "INVALID_ISSUE_HISTORY"),
      sequence: integerValue(event.event_sequence, "INVALID_ISSUE_HISTORY"),
      eventType: requiredText(event.event_type, "INVALID_ISSUE_HISTORY"),
      actorId: requiredText(event.actor_id, "INVALID_ISSUE_HISTORY"),
      occurredAt: requiredText(event.occurred_at, "INVALID_ISSUE_HISTORY"),
      detail,
    };
  });
}

function issuePath(context: ProjectContext, issueId?: string, suffix?: string): string {
  const base = `/api/projects/${encodeURIComponent(context.project_id)}/p6/issues`;
  if (!issueId) return base;
  const path = `${base}/${encodeURIComponent(issueId)}`;
  return suffix ? `${path}/${suffix}` : path;
}

function filterQuery(filters: IssueFilters): string {
  const params = new URLSearchParams();
  if (filters.status.trim()) params.set("status", filters.status.trim());
  if (filters.priority.trim()) params.set("priority", filters.priority.trim());
  if (filters.issueType.trim()) params.set("issue_type", filters.issueType.trim());
  if (filters.search.trim()) params.set("search", filters.search.trim());
  const query = params.toString();
  return query ? `?${query}` : "";
}

export async function loadIssues(
  transport: ApiTransport,
  context: ProjectContext,
  filters: IssueFilters = { status: "", priority: "", issueType: "", search: "" },
): Promise<ApiResult<readonly IssueRecord[]>> {
  const result = await transport.get<unknown>(`${issuePath(context)}${filterQuery(filters)}`, context);
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || payload.contract_version !== ISSUE_API_VERSION || !Array.isArray(payload.issues)) {
    return localError("INVALID_ISSUE_LIST");
  }
  try {
    return { ok: true, data: payload.issues.map((item) => parseIssue(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ISSUE_LIST");
  }
}

export async function loadIssueHistory(
  transport: ApiTransport,
  context: ProjectContext,
  issueId: string,
): Promise<ApiResult<readonly IssueHistoryEvent[]>> {
  const result = await transport.get<unknown>(issuePath(context, issueId, "history"), context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseIssueHistory(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ISSUE_HISTORY");
  }
}

export function buildIssuePayload(input: IssueInput): Record<string, unknown> {
  const issueId = input.issueId.trim();
  const title = input.title.trim();
  const owner = input.owner.trim();
  if (!issueId || !title || !owner) throw new Error("ISSUE_FIELDS_REQUIRED");
  if (!(ISSUE_TYPES as readonly string[]).includes(input.issueType)) throw new Error("INVALID_ISSUE_TYPE");
  if (!(ISSUE_STATUSES as readonly string[]).includes(input.status)) throw new Error("INVALID_ISSUE_STATUS");
  if (!(ISSUE_PRIORITIES as readonly string[]).includes(input.priority)) throw new Error("INVALID_ISSUE_PRIORITY");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(input.dateIdentified)) throw new Error("INVALID_ISSUE_DATE");
  if (input.dueDate !== null && !/^\d{4}-\d{2}-\d{2}$/.test(input.dueDate)) throw new Error("INVALID_ISSUE_DATE");
  return {
    contract_version: ISSUE_API_VERSION,
    issue_id: issueId,
    title,
    description: input.description.trim(),
    issue_type: input.issueType,
    status: input.status,
    priority: input.priority,
    owner,
    responsible_manager: input.responsibleManager?.trim() || null,
    date_identified: input.dateIdentified,
    due_date: input.dueDate,
    wbs_id: input.wbsId?.trim() || null,
    activity_id: input.activityId?.trim() || null,
    document_refs: input.documentRefs.map((ref) => ref.trim()).filter(Boolean),
    resolution_note: input.resolutionNote?.trim() || null,
  };
}

export async function saveIssue(
  transport: ApiTransport,
  context: ProjectContext,
  input: IssueInput,
): Promise<ApiResult<IssueRecord>> {
  let payload: Record<string, unknown>;
  try {
    payload = buildIssuePayload(input);
  } catch (error) {
    return localError(error instanceof Error ? error.message : "ISSUE_FIELDS_REQUIRED");
  }
  const result = await transport.post<Record<string, unknown>, unknown>(
    issuePath(context),
    payload,
    context,
    crypto.randomUUID(),
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseIssue(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ISSUE_RESPONSE");
  }
}

export async function updateIssue(
  transport: ApiTransport,
  context: ProjectContext,
  input: IssueInput,
  expectedRevision: number,
): Promise<ApiResult<IssueRecord>> {
  if (!transport.put) return localError("TRANSPORT_PUT_UNSUPPORTED");
  let payload: Record<string, unknown>;
  try {
    payload = { ...buildIssuePayload(input), expected_revision: expectedRevision };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "ISSUE_FIELDS_REQUIRED");
  }
  const result = await transport.put<Record<string, unknown>, unknown>(
    issuePath(context, input.issueId.trim()),
    payload,
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseIssue(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ISSUE_RESPONSE");
  }
}

export async function addIssueComment(
  transport: ApiTransport,
  context: ProjectContext,
  issueId: string,
  comment: string,
  expectedRevision: number,
): Promise<ApiResult<IssueRecord>> {
  if (!comment.trim()) return localError("ISSUE_COMMENT_REQUIRED");
  const result = await transport.post<Record<string, unknown>, unknown>(
    issuePath(context, issueId, "comments"),
    { comment: comment.trim(), expected_revision: expectedRevision },
    context,
    crypto.randomUUID(),
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseIssue(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_ISSUE_RESPONSE");
  }
}

export async function deleteIssue(
  transport: ApiTransport,
  context: ProjectContext,
  issueId: string,
  expectedRevision: number,
): Promise<ApiResult<{ deleted: boolean }>> {
  if (!transport.delete) return localError("TRANSPORT_DELETE_UNSUPPORTED");
  const result = await transport.delete<Record<string, unknown>, unknown>(
    issuePath(context, issueId),
    { expected_revision: expectedRevision },
    context,
  );
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || payload.contract_version !== ISSUE_API_VERSION || payload.deleted !== true) {
    return localError("INVALID_ISSUE_DELETE_RESPONSE");
  }
  return { ok: true, data: { deleted: true } };
}

type PageState = {
  status: "loading" | "loaded" | "error";
  errorCode: string | null;
  issues: readonly IssueRecord[];
  selectedIssueId: string | null;
  mode: "browse" | "create" | "edit";
  draft: IssueInput;
  expectedRevision: number | null;
  tab: "general" | "details" | "documents" | "history";
  history: readonly IssueHistoryEvent[];
  historyStatus: "idle" | "loading" | "loaded" | "error";
  comment: string;
  filters: IssueFilters;
  busy: boolean;
  notice: { kind: "ok" | "error"; message: string } | null;
};

function emptyDraft(): IssueInput {
  return {
    issueId: "",
    title: "",
    description: "",
    issueType: "schedule",
    status: "open",
    priority: "normal",
    owner: "",
    responsibleManager: null,
    dateIdentified: new Date().toISOString().slice(0, 10),
    dueDate: null,
    wbsId: null,
    activityId: null,
    documentRefs: [],
    resolutionNote: null,
  };
}

function draftFrom(record: IssueRecord): IssueInput {
  return {
    issueId: record.issueId,
    title: record.title,
    description: record.description,
    issueType: record.issueType,
    status: record.status,
    priority: record.priority,
    owner: record.owner,
    responsibleManager: record.responsibleManager,
    dateIdentified: record.dateIdentified,
    dueDate: record.dueDate,
    wbsId: record.wbsId,
    activityId: record.activityId,
    documentRefs: [...record.documentRefs],
    resolutionNote: record.resolutionNote,
  };
}

export function mountWorkspaceIssuesPage(host: HTMLElement, options: IssuePageOptions): void {
  if (host.dataset.issuesMounted === "true") return;
  host.dataset.issuesMounted = "true";
  const { transport, context, locale, activities, wbsNodes } = options;
  const state: PageState = {
    status: "loading",
    errorCode: null,
    issues: [],
    selectedIssueId: null,
    mode: "browse",
    draft: emptyDraft(),
    expectedRevision: null,
    tab: "general",
    history: [],
    historyStatus: "idle",
    comment: "",
    filters: { status: "", priority: "", issueType: "", search: "" },
    busy: false,
    notice: null,
  };

  const say = (en: string, fa: string): string => text(locale, en, fa);
  const selected = (): IssueRecord | null =>
    state.issues.find((item) => item.issueId === state.selectedIssueId) ?? null;
  const activityLabel = (id: string): string => {
    const activity = activities.find((item) => item.id === id);
    return activity ? `${activity.code} ${activity.name}` : id;
  };
  const wbsLabel = (id: string): string => {
    const node = wbsNodes.find((item) => item.id === id);
    return node ? `${node.code} ${node.name}` : id;
  };
  const optionList = (values: readonly string[], current: string): string => {
    const known = values.includes(current);
    const prefix = current && !known ? `<option value="${escapeHtml(current)}" selected>${escapeHtml(current)}</option>` : "";
    return prefix + values.map((value) =>
      `<option value="${escapeHtml(value)}"${value === current ? " selected" : ""}>${escapeHtml(value)}</option>`
    ).join("");
  };
  const filterOptions = (values: readonly string[], current: string, allLabel: string): string =>
    `<option value=""${current ? "" : " selected"}>${escapeHtml(allLabel)}</option>` + values.map((value) =>
      `<option value="${escapeHtml(value)}"${value === current ? " selected" : ""}>${escapeHtml(value)}</option>`
    ).join("");
  const referenceOptions = (
    current: string | null,
    items: readonly { id: string; label: string }[],
    placeholder: string,
  ): string => {
    const known = current !== null && items.some((item) => item.id === current);
    const prefix = current && !known
      ? `<option value="${escapeHtml(current)}" selected>${escapeHtml(current)}</option>`
      : `<option value="">${escapeHtml(placeholder)}</option>`;
    return prefix + items.map((item) =>
      `<option value="${escapeHtml(item.id)}"${item.id === current ? " selected" : ""}>${escapeHtml(item.label)}</option>`
    ).join("");
  };

  function renderRegister(): string {
    if (state.status === "loading") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading project issues…", "در حال خواندن مسائل پروژه…"))}</div>`;
    }
    if (state.status === "error") {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Project issues could not be read", "خواندن مسائل پروژه ناموفق بود"))} (${escapeHtml(state.errorCode ?? "unknown")})</div>`;
    }
    if (!state.issues.length) {
      const filtered = Boolean(state.filters.status || state.filters.priority || state.filters.issueType || state.filters.search);
      return `<div class="cp-calendar-empty">${escapeHtml(filtered
        ? say("No issue matches the current filters.", "هیچ مسئله‌ای با پالایه‌های فعلی مطابقت ندارد.")
        : say("No project issues are stored for this project.", "هیچ مسئله‌ای برای این پروژه ذخیره نشده است."))}</div>`;
    }
    const rows = state.issues.map((item) => {
      const active = item.issueId === state.selectedIssueId;
      return `<tr data-issue-row data-issue-id="${escapeHtml(item.issueId)}" tabindex="0" role="button" aria-selected="${active}" class="${active ? "is-selected" : ""}"><td><strong>${escapeHtml(item.issueId)}</strong></td><td>${escapeHtml(item.title)}</td><td>${escapeHtml(item.issueType)}</td><td><span class="cp-issue-status" data-status="${escapeHtml(item.status)}">${escapeHtml(item.status)}</span></td><td><span class="cp-issue-priority" data-priority="${escapeHtml(item.priority)}">${escapeHtml(item.priority)}</span></td><td>${escapeHtml(item.owner)}</td><td>${escapeHtml(item.dueDate ?? "—")}</td><td>${item.recordRevision}</td></tr>`;
    }).join("");
    return `<div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(say("Issue ID", "شناسه مسئله"))}</th><th>${escapeHtml(say("Title", "عنوان"))}</th><th>${escapeHtml(say("Type", "نوع"))}</th><th>${escapeHtml(say("Status", "وضعیت"))}</th><th>${escapeHtml(say("Priority", "اولویت"))}</th><th>${escapeHtml(say("Owner", "مسئول"))}</th><th>${escapeHtml(say("Due", "موعد"))}</th><th>${escapeHtml(say("Rev", "نسخه"))}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function renderFilters(): string {
    return `<div class="cp-issue-filters">
      <label>${escapeHtml(say("Search", "جستجو"))}<input name="issue-search" value="${escapeHtml(state.filters.search)}" placeholder="${escapeHtml(say("ID, title, owner", "شناسه، عنوان، مسئول"))}"></label>
      <label>${escapeHtml(say("Status", "وضعیت"))}<select name="issue-filter-status">${filterOptions(ISSUE_STATUSES, state.filters.status, say("All", "همه"))}</select></label>
      <label>${escapeHtml(say("Priority", "اولویت"))}<select name="issue-filter-priority">${filterOptions(ISSUE_PRIORITIES, state.filters.priority, say("All", "همه"))}</select></label>
      <label>${escapeHtml(say("Type", "نوع"))}<select name="issue-filter-type">${filterOptions(ISSUE_TYPES, state.filters.issueType, say("All", "همه"))}</select></label>
      <button type="button" data-issue-action="apply-filters">${escapeHtml(say("Apply", "اعمال"))}</button>
      <button type="button" data-issue-action="clear-filters">${escapeHtml(say("Clear", "پاک کردن"))}</button>
    </div>`;
  }

  function inputRow(label: string, value: string | null): string {
    return `<label>${escapeHtml(label)}<input readonly value="${escapeHtml(value ?? say("Not provided", "ارائه نشده"))}"></label>`;
  }

  function renderForm(): string {
    const draft = state.draft;
    const creating = state.mode === "create";
    return `<form data-issue-form class="cp-expense-fields">
      <label>${escapeHtml(say("Issue ID", "شناسه مسئله"))}<input name="issue-id" value="${escapeHtml(draft.issueId)}" ${creating ? "" : "readonly"} required></label>
      <label>${escapeHtml(say("Title", "عنوان"))}<input name="issue-title" value="${escapeHtml(draft.title)}" required></label>
      <label>${escapeHtml(say("Type", "نوع"))}<select name="issue-type">${optionList(ISSUE_TYPES, draft.issueType)}</select></label>
      <label>${escapeHtml(say("Status", "وضعیت"))}<select name="issue-status">${optionList(ISSUE_STATUSES, draft.status)}</select></label>
      <label>${escapeHtml(say("Priority", "اولویت"))}<select name="issue-priority">${optionList(ISSUE_PRIORITIES, draft.priority)}</select></label>
      <label>${escapeHtml(say("Owner", "مسئول"))}<input name="issue-owner" value="${escapeHtml(draft.owner)}" required></label>
      <label>${escapeHtml(say("Responsible Manager", "مدیر مسئول"))}<input name="issue-manager" value="${escapeHtml(draft.responsibleManager ?? "")}"></label>
      <label>${escapeHtml(say("Date Identified", "تاریخ شناسایی"))}<input name="issue-identified" type="date" value="${escapeHtml(draft.dateIdentified)}" required></label>
      <label>${escapeHtml(say("Due Date", "موعد"))}<input name="issue-due" type="date" value="${escapeHtml(draft.dueDate ?? "")}"></label>
      <label>${escapeHtml(say("WBS", "ساختار شکست"))}<select name="issue-wbs">${referenceOptions(draft.wbsId, wbsNodes.map((item) => ({ id: item.id, label: `${item.code} ${item.name}` })), say("No WBS reference", "بدون ارجاع ساختار شکست"))}</select></label>
      <label>${escapeHtml(say("Activity", "فعالیت"))}<select name="issue-activity">${referenceOptions(draft.activityId, activities.map((item) => ({ id: item.id, label: `${item.code} ${item.name}` })), say("No activity reference", "بدون ارجاع فعالیت"))}</select></label>
      <label class="cp-expense-note">${escapeHtml(say("Description", "شرح"))}<textarea name="issue-description" rows="2">${escapeHtml(draft.description)}</textarea></label>
      <label class="cp-expense-note">${escapeHtml(say("Documents (comma separated)", "اسناد (با کاما جدا کنید)"))}<input name="issue-documents" value="${escapeHtml(draft.documentRefs.join(", "))}"></label>
      <label class="cp-expense-note">${escapeHtml(say("Resolution Note", "یادداشت حل"))}<input name="issue-resolution" value="${escapeHtml(draft.resolutionNote ?? "")}"></label>
      <div class="cp-calendar-panel-actions"><button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(creating ? say("Create issue", "ایجاد مسئله") : say("Save changes", "ذخیره تغییرات"))}</button><button type="button" data-issue-action="cancel">${escapeHtml(say("Cancel", "لغو"))}</button></div>
    </form>`;
  }

  function renderGeneral(item: IssueRecord): string {
    return `<div class="cp-expense-fields">
      ${inputRow(say("Issue ID", "شناسه مسئله"), item.issueId)}
      ${inputRow(say("Title", "عنوان"), item.title)}
      ${inputRow(say("Type", "نوع"), item.issueType)}
      ${inputRow(say("Status", "وضعیت"), item.status)}
      ${inputRow(say("Priority", "اولویت"), item.priority)}
      ${inputRow(say("Owner", "مسئول"), item.owner)}
      ${inputRow(say("Responsible Manager", "مدیر مسئول"), item.responsibleManager)}
      ${inputRow(say("Date Identified", "تاریخ شناسایی"), item.dateIdentified)}
      ${inputRow(say("Due Date", "موعد"), item.dueDate)}
      ${inputRow(say("Record revision", "نسخه رکورد"), String(item.recordRevision))}
    </div>`;
  }

  function renderDetailsTab(item: IssueRecord): string {
    return `<div class="cp-expense-fields">
      ${inputRow(say("WBS", "ساختار شکست"), item.wbsId ? wbsLabel(item.wbsId) : null)}
      ${inputRow(say("Activity", "فعالیت"), item.activityId ? activityLabel(item.activityId) : null)}
      ${inputRow(say("Created", "ایجاد"), item.createdAt)}
      ${inputRow(say("Updated", "به‌روزرسانی"), item.updatedAt)}
      <label class="cp-expense-note">${escapeHtml(say("Description", "شرح"))}<textarea readonly rows="3">${escapeHtml(item.description)}</textarea></label>
      <label class="cp-expense-note">${escapeHtml(say("Resolution Note", "یادداشت حل"))}<textarea readonly rows="2">${escapeHtml(item.resolutionNote ?? "")}</textarea></label>
    </div>`;
  }

  function renderDocumentsTab(item: IssueRecord): string {
    if (!item.documentRefs.length) {
      return `<p>${escapeHtml(say("No document references are linked to this issue.", "هیچ سند ارجاع‌شده‌ای به این مسئله پیوند نشده است."))}</p>`;
    }
    return `<ul class="cp-issue-documents">${item.documentRefs.map((ref) =>
      `<li data-issue-document="${escapeHtml(ref)}">${escapeHtml(ref)}</li>`
    ).join("")}</ul>`;
  }

  function renderHistoryTab(item: IssueRecord): string {
    const commentForm = `<div class="cp-issue-comment"><label>${escapeHtml(say("Add comment", "افزودن یادداشت"))}<input name="issue-comment" value="${escapeHtml(state.comment)}" placeholder="${escapeHtml(say("Comment text", "متن یادداشت"))}"></label><button type="button" data-issue-action="comment" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Add comment", "افزودن یادداشت"))}</button></div>`;
    if (state.historyStatus === "loading") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading issue history…", "در حال خواندن تاریخچهٔ مسئله…"))}</div>`;
    }
    if (state.historyStatus === "error") {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Issue history could not be read.", "خواندن تاریخچهٔ مسئله ناموفق بود."))}</div>`;
    }
    const events = state.history.length
      ? `<ol class="cp-issue-history">${state.history.map((event) => {
          const detail = event.eventType === "commented" && typeof event.detail.comment === "string"
            ? event.detail.comment
            : event.eventType === "status_changed"
              ? `${String(event.detail.from_status ?? "?")} → ${String(event.detail.to_status ?? "?")}`
              : Array.isArray(event.detail.fields)
                ? (event.detail.fields as unknown[]).join(", ")
                : "";
          return `<li data-issue-event="${escapeHtml(event.eventType)}"><strong>${escapeHtml(event.eventType)}</strong><span>${escapeHtml(event.actorId)} · ${escapeHtml(event.occurredAt)}</span><p>${escapeHtml(detail)}</p></li>`;
        }).join("")}</ol>`
      : `<p>${escapeHtml(say("No history events are stored yet.", "هنوز رویدادی در تاریخچه ذخیره نشده است."))}</p>`;
    return `${events}${item.status !== "closed" ? commentForm : `<p>${escapeHtml(say("Closed issues are final and accept no new comments.", "مسائل بسته‌شده نهایی هستند و یادداشت جدید نمی‌پذیرند."))}</p>`}`;
  }

  function renderDetails(): string {
    if (state.mode === "create" || state.mode === "edit") return renderForm();
    const item = selected();
    if (!item) {
      return `<p>${escapeHtml(say("Select an issue from the register to read its stored values, history and documents.", "برای خواندن مقادیر، تاریخچه و اسناد، یک مسئله را از فهرست انتخاب کنید."))}</p>`;
    }
    const tabs: { id: PageState["tab"]; en: string; fa: string }[] = [
      { id: "general", en: "General", fa: "عمومی" },
      { id: "details", en: "Details", fa: "جزئیات" },
      { id: "documents", en: "Documents", fa: "اسناد" },
      { id: "history", en: "History", fa: "تاریخچه" },
    ];
    const tabStrip = `<div class="cp-documents-tabs" role="tablist" aria-label="${escapeHtml(say("Issue detail tabs", "زبانه‌های جزئیات مسئله"))}">${tabs.map((tab) =>
      `<button type="button" role="tab" aria-selected="${state.tab === tab.id}" data-issue-tab="${tab.id}" class="${state.tab === tab.id ? "is-active" : ""}">${escapeHtml(say(tab.en, tab.fa))}</button>`
    ).join("")}</div>`;
    let body: string;
    if (state.tab === "details") body = renderDetailsTab(item);
    else if (state.tab === "documents") body = renderDocumentsTab(item);
    else if (state.tab === "history") body = renderHistoryTab(item);
    else body = renderGeneral(item);
    return `${tabStrip}<div class="cp-issue-detail-body">${body}</div>
      <div class="cp-calendar-panel-actions">
        <button type="button" data-issue-action="edit" ${state.busy || item.status === "closed" ? "disabled" : ""} title="${escapeHtml(item.status === "closed" ? say("Closed issues are final", "مسائل بسته‌شده نهایی هستند") : "")}">${escapeHtml(say("Edit issue", "ویرایش مسئله"))}</button>
        <button type="button" data-issue-action="delete" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Delete issue", "حذف مسئله"))}</button>
      </div>`;
  }

  function render(): void {
    host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(say("Project Issues", "مسائل پروژه"))}</strong><span>${state.issues.length} ${escapeHtml(say("record(s)", "رکورد"))}</span><div><button type="button" data-issue-action="new" ${state.busy ? "disabled" : ""}>${escapeHtml(say("New Issue", "مسئلهٔ جدید"))}</button><button type="button" data-issue-action="reload" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button></div></div>
      ${renderFilters()}
      ${renderRegister()}
      <section class="cp-register-details" data-issue-details><header><strong>${escapeHtml(say("Issue Details", "جزئیات مسئله"))}</strong><span>${selected() ? escapeHtml(selected()?.issueId ?? "") : escapeHtml(say("No selection", "بدون انتخاب"))}</span></header><div class="cp-register-detail-content">${renderDetails()}</div></section>
      ${state.notice ? `<p class="cp-calendar-notice" data-issue-notice data-state="${state.notice.kind}" role="status">${escapeHtml(state.notice.message)}</p>` : ""}`;
  }

  async function refreshHistory(issueId: string): Promise<void> {
    state.historyStatus = "loading";
    render();
    const result = await loadIssueHistory(transport, context, issueId);
    if (result.ok) {
      state.historyStatus = "loaded";
      state.history = result.data;
    } else {
      state.historyStatus = "error";
      state.history = [];
    }
    render();
  }

  async function reload(keepSelection: string | null): Promise<void> {
    state.status = "loading";
    render();
    const result = await loadIssues(transport, context, state.filters);
    if (result.ok) {
      state.status = "loaded";
      state.errorCode = null;
      state.issues = result.data;
      const kept = keepSelection && result.data.some((item) => item.issueId === keepSelection);
      state.selectedIssueId = kept ? keepSelection : null;
      if (kept) void refreshHistory(keepSelection as string);
      else { state.history = []; state.historyStatus = "idle"; }
    } else {
      state.status = "error";
      state.errorCode = result.error.code;
    }
    render();
  }

  function beginEdit(): void {
    const item = selected();
    if (!item) return;
    state.mode = "edit";
    state.draft = draftFrom(item);
    state.expectedRevision = item.recordRevision;
    state.notice = null;
    render();
  }

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    const row = target.closest<HTMLElement>("[data-issue-row]");
    if (row?.dataset.issueId) {
      state.selectedIssueId = row.dataset.issueId;
      state.mode = "browse";
      state.tab = "general";
      state.notice = null;
      state.comment = "";
      render();
      void refreshHistory(row.dataset.issueId);
      return;
    }
    const tab = target.closest<HTMLElement>("[data-issue-tab]")?.dataset.issueTab as PageState["tab"] | undefined;
    if (tab) {
      state.tab = tab;
      render();
      if (tab === "history" && state.selectedIssueId) void refreshHistory(state.selectedIssueId);
      return;
    }
    const action = target.closest<HTMLElement>("[data-issue-action]")?.dataset.issueAction;
    if (!action) return;
    if (action === "new") {
      state.mode = "create";
      state.draft = emptyDraft();
      state.expectedRevision = null;
      state.notice = null;
      render();
      return;
    }
    if (action === "cancel") {
      state.mode = "browse";
      state.notice = null;
      render();
      return;
    }
    if (action === "reload") { void reload(state.selectedIssueId); return; }
    if (action === "apply-filters") {
      const search = host.querySelector<HTMLInputElement>("[name=issue-search]");
      const status = host.querySelector<HTMLSelectElement>("[name=issue-filter-status]");
      const priority = host.querySelector<HTMLSelectElement>("[name=issue-filter-priority]");
      const type = host.querySelector<HTMLSelectElement>("[name=issue-filter-type]");
      state.filters = {
        search: search?.value ?? "",
        status: status?.value ?? "",
        priority: priority?.value ?? "",
        issueType: type?.value ?? "",
      };
      void reload(null);
      return;
    }
    if (action === "clear-filters") {
      state.filters = { status: "", priority: "", issueType: "", search: "" };
      void reload(null);
      return;
    }
    if (action === "edit") { beginEdit(); return; }
    if (action === "delete") { void removeSelected(); return; }
    if (action === "comment") { void submitComment(); }
  });

  host.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const row = (event.target as HTMLElement).closest<HTMLElement>("[data-issue-row]");
    if (!row?.dataset.issueId) return;
    event.preventDefault();
    state.selectedIssueId = row.dataset.issueId;
    state.mode = "browse";
    state.tab = "general";
    render();
    void refreshHistory(row.dataset.issueId);
  });

  host.addEventListener("input", (event) => {
    const target = event.target as HTMLInputElement | HTMLTextAreaElement;
    switch (target.name) {
      case "issue-comment": state.comment = target.value; break;
      case "issue-id": state.draft.issueId = target.value; break;
      case "issue-title": state.draft.title = target.value; break;
      case "issue-owner": state.draft.owner = target.value; break;
      case "issue-manager": state.draft.responsibleManager = target.value; break;
      case "issue-identified": state.draft.dateIdentified = target.value; break;
      case "issue-due": state.draft.dueDate = target.value || null; break;
      case "issue-description": state.draft.description = target.value; break;
      case "issue-resolution": state.draft.resolutionNote = target.value; break;
      case "issue-documents":
        state.draft.documentRefs = target.value.split(",").map((item) => item.trim()).filter(Boolean);
        break;
      case "issue-search": state.filters.search = target.value; break;
      default: break;
    }
  });

  host.addEventListener("change", (event) => {
    const target = event.target as HTMLSelectElement;
    if (target.name === "issue-type") state.draft.issueType = target.value;
    if (target.name === "issue-status") state.draft.status = target.value;
    if (target.name === "issue-priority") state.draft.priority = target.value;
    if (target.name === "issue-wbs") state.draft.wbsId = target.value || null;
    if (target.name === "issue-activity") state.draft.activityId = target.value || null;
  });

  host.addEventListener("submit", (event) => {
    const form = event.target as HTMLFormElement;
    if (!form.matches("[data-issue-form]")) return;
    event.preventDefault();
    if (state.busy) return;
    void (async () => {
      state.busy = true;
      render();
      const creating = state.mode === "create";
      const result = creating
        ? await saveIssue(transport, context, state.draft)
        : await updateIssue(transport, context, state.draft, state.expectedRevision ?? 0);
      state.busy = false;
      if (!result.ok) {
        state.notice = {
          kind: "error",
          message: `${creating ? say("Issue was not created", "مسئله ایجاد نشد") : say("Issue was not saved", "مسئله ذخیره نشد")} (${result.error.code})`,
        };
        render();
        if (result.error.code === "ISSUE_REVISION_CONFLICT") {
          // A competing write won; reload the authoritative record instead of
          // overwriting it with this stale form.
          state.mode = "browse";
          await reload(result.error.code === "ISSUE_REVISION_CONFLICT" ? state.selectedIssueId : null);
        }
        return;
      }
      state.notice = {
        kind: "ok",
        message: creating ? say("Issue created.", "مسئله ایجاد شد.") : say("Issue saved.", "مسئله ذخیره شد."),
      };
      state.mode = "browse";
      state.tab = "general";
      await reload(result.data.issueId);
    })();
  });

  async function submitComment(): Promise<void> {
    const item = selected();
    if (!item || state.busy) return;
    if (!state.comment.trim()) {
      state.notice = { kind: "error", message: say("Enter a comment first.", "ابتدا یک یادداشت وارد کنید.") };
      render();
      return;
    }
    state.busy = true;
    render();
    const result = await addIssueComment(transport, context, item.issueId, state.comment, item.recordRevision);
    state.busy = false;
    if (!result.ok) {
      state.notice = {
        kind: "error",
        message: `${say("Comment was not saved", "یادداشت ذخیره نشد")} (${result.error.code})`,
      };
      render();
      if (result.error.code === "ISSUE_REVISION_CONFLICT") await reload(item.issueId);
      return;
    }
    state.comment = "";
    state.notice = { kind: "ok", message: say("Comment added.", "یادداشت افزوده شد.") };
    state.issues = state.issues.map((entry) =>
      entry.issueId === result.data.issueId ? result.data : entry
    );
    state.tab = "history";
    await refreshHistory(item.issueId);
  }

  async function removeSelected(): Promise<void> {
    const item = selected();
    if (!item || state.busy) return;
    const confirmed = typeof window === "undefined" || typeof window.confirm !== "function"
      ? true
      : window.confirm(say(`Delete issue ${item.issueId}?`, `مسئلهٔ ${item.issueId} حذف شود؟`));
    if (!confirmed) return;
    state.busy = true;
    render();
    const result = await deleteIssue(transport, context, item.issueId, item.recordRevision);
    state.busy = false;
    if (!result.ok) {
      state.notice = {
        kind: "error",
        message: `${say("Issue was not deleted", "مسئله حذف نشد")} (${result.error.code})`,
      };
      render();
      if (result.error.code === "ISSUE_REVISION_CONFLICT") await reload(item.issueId);
      return;
    }
    state.notice = { kind: "ok", message: say("Issue deleted.", "مسئله حذف شد.") };
    state.selectedIssueId = null;
    state.history = [];
    state.historyStatus = "idle";
    await reload(null);
  }

  void reload(null);
}
