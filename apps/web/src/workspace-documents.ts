import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

/**
 * Project document register client.
 *
 * The document record is revision-guarded metadata. Bytes stay behind
 * storage_ref; this page never fabricates a content hash and never invents a
 * status transition the server has not declared.
 */

export const DOCUMENT_API_VERSION = "1.0";

export const DOCUMENT_TYPES = [
  "contract",
  "drawing",
  "correspondence",
  "rfi",
  "submittal",
  "delay_claim",
  "evidence",
] as const;

export const DOCUMENT_STATUSES = ["draft", "submitted", "approved", "rejected", "superseded"] as const;

export const DOCUMENT_TRANSITIONS: Readonly<Record<string, readonly string[]>> = {
  draft: ["submitted"],
  submitted: ["approved", "rejected"],
  rejected: ["submitted"],
  approved: ["superseded"],
  superseded: [],
};

export type DocumentType = (typeof DOCUMENT_TYPES)[number];
export type DocumentStatus = (typeof DOCUMENT_STATUSES)[number];

export type DocumentRecord = {
  documentId: string;
  resourceType: string;
  title: string;
  status: string;
  storageRef: string;
  contentHash: string;
  linkedEntityRefs: readonly string[];
  revision: number;
};

export type DocumentHistoryEvent = {
  documentId: string;
  revision: number;
  eventType: string;
  actorId: string;
  occurredAt: string;
  reason: string;
};

export type DocumentInput = {
  documentId: string;
  resourceType: string;
  title: string;
  storageRef: string;
  contentHash: string;
  linkedEntityRefs: readonly string[];
};

export type DocumentFilters = {
  resourceType: string;
  status: string;
  search: string;
};

export type DocumentPageOptions = {
  transport: ApiTransport;
  context: ProjectContext;
  locale: string;
  canWrite: boolean;
  canApprove: boolean;
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

function integerValue(value: unknown, code: string): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 1) throw new Error(code);
  return value;
}

function stringList(value: unknown, code: string): string[] {
  if (value === undefined || value === null) return [];
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string" || !item.trim())) {
    throw new Error(code);
  }
  return (value as string[]).map((item) => item.trim());
}

export function parseDocument(value: unknown): DocumentRecord {
  if (!isRecord(value) || value.contract_version !== DOCUMENT_API_VERSION) {
    throw new Error("INVALID_DOCUMENT_RESPONSE");
  }
  const status = requiredText(value.status, "INVALID_DOCUMENT_RECORD");
  if (!(DOCUMENT_STATUSES as readonly string[]).includes(status)) {
    throw new Error("INVALID_DOCUMENT_RECORD");
  }
  return {
    documentId: requiredText(value.document_id, "INVALID_DOCUMENT_RECORD"),
    resourceType: requiredText(value.resource_type, "INVALID_DOCUMENT_RECORD"),
    title: requiredText(value.title, "INVALID_DOCUMENT_RECORD"),
    status,
    storageRef: requiredText(value.storage_ref, "INVALID_DOCUMENT_RECORD"),
    contentHash: requiredText(value.content_hash, "INVALID_DOCUMENT_RECORD"),
    linkedEntityRefs: stringList(value.linked_entity_refs, "INVALID_DOCUMENT_RECORD"),
    revision: integerValue(value.revision, "INVALID_DOCUMENT_RECORD"),
  };
}

export function parseDocumentHistory(value: unknown): DocumentHistoryEvent[] {
  if (!isRecord(value) || value.contract_version !== DOCUMENT_API_VERSION || !Array.isArray(value.events)) {
    throw new Error("INVALID_DOCUMENT_HISTORY");
  }
  return value.events.map((entry) => {
    if (!isRecord(entry)) throw new Error("INVALID_DOCUMENT_HISTORY");
    return {
      documentId: requiredText(entry.document_id, "INVALID_DOCUMENT_HISTORY"),
      revision: integerValue(entry.revision, "INVALID_DOCUMENT_HISTORY"),
      eventType: requiredText(entry.event_type, "INVALID_DOCUMENT_HISTORY"),
      actorId: requiredText(entry.actor_id, "INVALID_DOCUMENT_HISTORY"),
      occurredAt: requiredText(entry.occurred_at, "INVALID_DOCUMENT_HISTORY"),
      reason: typeof entry.reason === "string" ? entry.reason : "",
    };
  });
}

export function statusTransitions(status: string): readonly string[] {
  return DOCUMENT_TRANSITIONS[status] ?? [];
}

export function buildDocumentPayload(input: DocumentInput, status: string): Record<string, unknown> {
  const documentId = input.documentId.trim();
  const title = input.title.trim();
  const storageRef = input.storageRef.trim();
  const contentHash = input.contentHash.trim();
  if (!documentId || !title || !storageRef || !contentHash) throw new Error("DOCUMENT_FIELDS_REQUIRED");
  if (!(DOCUMENT_TYPES as readonly string[]).includes(input.resourceType)) {
    throw new Error("INVALID_DOCUMENT_RESOURCE_TYPE");
  }
  if (!(DOCUMENT_STATUSES as readonly string[]).includes(status)) {
    throw new Error("INVALID_DOCUMENT_STATUS");
  }
  if (!/^sha256:[0-9a-f]{64}$/.test(contentHash)) {
    throw new Error("INVALID_DOCUMENT_CONTENT_HASH");
  }
  return {
    contract_version: DOCUMENT_API_VERSION,
    document_id: documentId,
    resource_type: input.resourceType,
    title,
    status,
    storage_ref: storageRef,
    content_hash: contentHash,
    linked_entity_refs: input.linkedEntityRefs.map((ref) => ref.trim()).filter(Boolean),
  };
}

function documentPath(context: ProjectContext, documentId?: string, suffix?: string): string {
  const base = `/api/projects/${encodeURIComponent(context.project_id)}/documents`;
  if (!documentId) return base;
  const path = `${base}/${encodeURIComponent(documentId)}`;
  return suffix ? `${path}/${suffix}` : path;
}

function filterQuery(filters: DocumentFilters): string {
  const params = new URLSearchParams();
  if (filters.resourceType.trim()) params.set("resource_type", filters.resourceType.trim());
  if (filters.status.trim()) params.set("status", filters.status.trim());
  if (filters.search.trim()) params.set("search", filters.search.trim());
  const query = params.toString();
  return query ? `?${query}` : "";
}

export async function loadDocuments(
  transport: ApiTransport,
  context: ProjectContext,
  filters: DocumentFilters = { resourceType: "", status: "", search: "" },
): Promise<ApiResult<readonly DocumentRecord[]>> {
  const result = await transport.get<unknown>(`${documentPath(context)}${filterQuery(filters)}`, context);
  if (!result.ok) return result;
  const payload = result.data;
  if (!isRecord(payload) || payload.contract_version !== DOCUMENT_API_VERSION || !Array.isArray(payload.documents)) {
    return localError("INVALID_DOCUMENT_LIST");
  }
  try {
    return { ok: true, data: payload.documents.map((item) => parseDocument(item)) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_DOCUMENT_LIST");
  }
}

export async function loadDocumentHistory(
  transport: ApiTransport,
  context: ProjectContext,
  documentId: string,
): Promise<ApiResult<readonly DocumentHistoryEvent[]>> {
  const result = await transport.get<unknown>(documentPath(context, documentId, "history"), context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseDocumentHistory(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_DOCUMENT_HISTORY");
  }
}

export async function createDocument(
  transport: ApiTransport,
  context: ProjectContext,
  input: DocumentInput,
): Promise<ApiResult<DocumentRecord>> {
  let payload: Record<string, unknown>;
  try {
    // A new document starts as a draft; approval is a separate audited action.
    payload = buildDocumentPayload(input, "draft");
  } catch (error) {
    return localError(error instanceof Error ? error.message : "DOCUMENT_FIELDS_REQUIRED");
  }
  const result = await transport.post<Record<string, unknown>, unknown>(
    documentPath(context),
    payload,
    context,
    crypto.randomUUID(),
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseDocument(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_DOCUMENT_RESPONSE");
  }
}

export async function updateDocument(
  transport: ApiTransport,
  context: ProjectContext,
  input: DocumentInput,
  status: string,
  expectedRevision: number,
): Promise<ApiResult<DocumentRecord>> {
  if (!transport.put) return localError("TRANSPORT_PUT_UNSUPPORTED");
  let payload: Record<string, unknown>;
  try {
    payload = { ...buildDocumentPayload(input, status), expected_revision: expectedRevision };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "DOCUMENT_FIELDS_REQUIRED");
  }
  const result = await transport.put<Record<string, unknown>, unknown>(
    documentPath(context, input.documentId.trim()),
    payload,
    context,
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseDocument(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_DOCUMENT_RESPONSE");
  }
}

export async function transitionDocument(
  transport: ApiTransport,
  context: ProjectContext,
  documentId: string,
  status: string,
  expectedRevision: number,
  reason: string,
): Promise<ApiResult<DocumentRecord>> {
  const result = await transport.post<Record<string, unknown>, unknown>(
    documentPath(context, documentId, "status"),
    { status, expected_revision: expectedRevision, reason: reason.trim() },
    context,
    crypto.randomUUID(),
  );
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseDocument(result.data) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_DOCUMENT_RESPONSE");
  }
}

type PageState = {
  status: "loading" | "loaded" | "error";
  errorCode: string | null;
  documents: readonly DocumentRecord[];
  selectedDocumentId: string | null;
  mode: "browse" | "create" | "edit";
  draft: DocumentInput;
  expectedRevision: number | null;
  tab: "general" | "history";
  history: readonly DocumentHistoryEvent[];
  historyStatus: "idle" | "loading" | "loaded" | "error";
  transitionReason: string;
  filters: DocumentFilters;
  busy: boolean;
  notice: { kind: "ok" | "error"; message: string } | null;
};

function emptyDraft(): DocumentInput {
  return {
    documentId: "",
    resourceType: "drawing",
    title: "",
    storageRef: "",
    contentHash: "",
    linkedEntityRefs: [],
  };
}

function draftFrom(record: DocumentRecord): DocumentInput {
  return {
    documentId: record.documentId,
    resourceType: record.resourceType,
    title: record.title,
    storageRef: record.storageRef,
    contentHash: record.contentHash,
    linkedEntityRefs: [...record.linkedEntityRefs],
  };
}

export function mountWorkspaceDocumentsPage(host: HTMLElement, options: DocumentPageOptions): void {
  if (host.dataset.documentsMounted === "true") return;
  host.dataset.documentsMounted = "true";
  const { transport, context, locale, canWrite, canApprove } = options;
  const state: PageState = {
    status: "loading",
    errorCode: null,
    documents: [],
    selectedDocumentId: null,
    mode: "browse",
    draft: emptyDraft(),
    expectedRevision: null,
    tab: "general",
    history: [],
    historyStatus: "idle",
    transitionReason: "",
    filters: { resourceType: "", status: "", search: "" },
    busy: false,
    notice: null,
  };

  const say = (en: string, fa: string): string => text(locale, en, fa);
  const selected = (): DocumentRecord | null =>
    state.documents.find((item) => item.documentId === state.selectedDocumentId) ?? null;
  const optionList = (values: readonly string[], current: string, placeholder?: string): string => {
    const known = values.includes(current);
    const prefix = current && !known
      ? `<option value="${escapeHtml(current)}" selected>${escapeHtml(current)}</option>`
      : placeholder !== undefined
        ? `<option value=""${current ? "" : " selected"}>${escapeHtml(placeholder)}</option>`
        : "";
    return prefix + values.map((value) =>
      `<option value="${escapeHtml(value)}"${value === current ? " selected" : ""}>${escapeHtml(value)}</option>`
    ).join("");
  };

  function renderRegister(): string {
    if (state.status === "loading") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading project documents…", "در حال خواندن اسناد پروژه…"))}</div>`;
    }
    if (state.status === "error") {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Project documents could not be read", "خواندن اسناد پروژه ناموفق بود"))} (${escapeHtml(state.errorCode ?? "unknown")})</div>`;
    }
    if (!state.documents.length) {
      const filtered = Boolean(state.filters.resourceType || state.filters.status || state.filters.search);
      return `<div class="cp-calendar-empty">${escapeHtml(filtered
        ? say("No document matches the current filters.", "هیچ سندی با پالایه‌های فعلی مطابقت ندارد.")
        : say("No project documents are stored for this project.", "هیچ سندی برای این پروژه ذخیره نشده است."))}</div>`;
    }
    const rows = state.documents.map((item) => {
      const active = item.documentId === state.selectedDocumentId;
      return `<tr data-document-row data-document-id="${escapeHtml(item.documentId)}" tabindex="0" role="button" aria-selected="${active}" class="${active ? "is-selected" : ""}"><td><strong>${escapeHtml(item.documentId)}</strong></td><td>${escapeHtml(item.title)}</td><td>${escapeHtml(item.resourceType)}</td><td><span class="cp-document-status" data-status="${escapeHtml(item.status)}">${escapeHtml(item.status)}</span></td><td>${item.linkedEntityRefs.length}</td><td>${item.revision}</td></tr>`;
    }).join("");
    return `<div class="cp-register-table-wrap"><table><thead><tr><th>${escapeHtml(say("Document ID", "شناسه سند"))}</th><th>${escapeHtml(say("Title", "عنوان"))}</th><th>${escapeHtml(say("Type", "نوع"))}</th><th>${escapeHtml(say("Status", "وضعیت"))}</th><th>${escapeHtml(say("Links", "پیوندها"))}</th><th>${escapeHtml(say("Rev", "نسخه"))}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function renderFilters(): string {
    return `<div class="cp-issue-filters">
      <label>${escapeHtml(say("Search", "جستجو"))}<input name="document-search" value="${escapeHtml(state.filters.search)}" placeholder="${escapeHtml(say("ID or title", "شناسه یا عنوان"))}"></label>
      <label>${escapeHtml(say("Type", "نوع"))}<select name="document-filter-type">${optionList(DOCUMENT_TYPES, state.filters.resourceType, say("All", "همه"))}</select></label>
      <label>${escapeHtml(say("Status", "وضعیت"))}<select name="document-filter-status">${optionList(DOCUMENT_STATUSES, state.filters.status, say("All", "همه"))}</select></label>
      <button type="button" data-document-action="apply-filters">${escapeHtml(say("Apply", "اعمال"))}</button>
      <button type="button" data-document-action="clear-filters">${escapeHtml(say("Clear", "پاک کردن"))}</button>
    </div>`;
  }

  function inputRow(label: string, value: string | null): string {
    return `<label>${escapeHtml(label)}<input readonly value="${escapeHtml(value ?? say("Not provided", "ارائه نشده"))}"></label>`;
  }

  function renderForm(): string {
    const draft = state.draft;
    const creating = state.mode === "create";
    return `<form data-document-form class="cp-expense-fields">
      <label>${escapeHtml(say("Document ID", "شناسه سند"))}<input name="document-id" value="${escapeHtml(draft.documentId)}" ${creating ? "" : "readonly"} required></label>
      <label>${escapeHtml(say("Title", "عنوان"))}<input name="document-title" value="${escapeHtml(draft.title)}" required></label>
      <label>${escapeHtml(say("Type", "نوع"))}<select name="document-type">${optionList(DOCUMENT_TYPES, draft.resourceType)}</select></label>
      <label>${escapeHtml(say("Storage reference", "مرجع ذخیره‌سازی"))}<input name="document-storage" value="${escapeHtml(draft.storageRef)}" required></label>
      <label class="cp-expense-note">${escapeHtml(say("SHA-256 content hash", "هش محتوای SHA-256"))}<input name="document-hash" value="${escapeHtml(draft.contentHash)}" placeholder="sha256:…" required></label>
      <label class="cp-expense-note">${escapeHtml(say("Linked records (comma separated)", "رکوردهای پیوندشده (با کاما جدا کنید)"))}<input name="document-links" value="${escapeHtml(draft.linkedEntityRefs.join(", "))}"></label>
      <p class="cp-calendar-notice">${escapeHtml(say("The record stores metadata only. The file bytes remain behind the storage reference and the hash is supplied by the upload source, never invented here.", "این رکورد فقط فراداده را ذخیره می‌کند. بایت‌های فایل پشت مرجع ذخیره‌سازی می‌مانند و هش از سوی منبع بارگذاری ارائه می‌شود و هرگز در اینجا ساخته نمی‌شود."))}</p>
      <div class="cp-calendar-panel-actions"><button type="submit" ${state.busy ? "disabled" : ""}>${escapeHtml(creating ? say("Create document", "ایجاد سند") : say("Save changes", "ذخیره تغییرات"))}</button><button type="button" data-document-action="cancel">${escapeHtml(say("Cancel", "لغو"))}</button></div>
    </form>`;
  }

  function renderStatusActions(item: DocumentRecord): string {
    const transitions = statusTransitions(item.status);
    if (!transitions.length) {
      return `<p>${escapeHtml(say("A superseded document is final and accepts no further transitions.", "سند جایگزین‌شده نهایی است و انتقال دیگری نمی‌پذیرد."))}</p>`;
    }
    const approval = (status: string): boolean => status === "approved" || status === "rejected";
    const buttons = transitions.map((status) => {
      const approvalGated = approval(status) && !canApprove;
      const gated = !canWrite || approvalGated;
      const reason = !canWrite
        ? say("Writing requires the project planner or administrator role.", "نوشتن به نقش برنامه‌ریز یا مدیر پروژه نیاز دارد.")
        : approvalGated
          ? say("Approval decisions require the project administrator role.", "تصمیم‌های تأیید به نقش مدیر پروژه نیاز دارد.")
          : "";
      return `<button type="button" data-document-transition="${escapeHtml(status)}" ${state.busy || gated ? "disabled" : ""} title="${escapeHtml(reason)}">${escapeHtml(status)}</button>`;
    }).join("");
    return `<div class="cp-calendar-panel-actions"><label>${escapeHtml(say("Transition reason", "دلیل انتقال"))}<input name="document-transition-reason" value="${escapeHtml(state.transitionReason)}"></label>${buttons}</div>`;
  }

  function renderGeneral(item: DocumentRecord): string {
    return `<div class="cp-expense-fields">
      ${inputRow(say("Document ID", "شناسه سند"), item.documentId)}
      ${inputRow(say("Title", "عنوان"), item.title)}
      ${inputRow(say("Type", "نوع"), item.resourceType)}
      ${inputRow(say("Status", "وضعیت"), item.status)}
      ${inputRow(say("Record revision", "نسخه رکورد"), String(item.revision))}
      ${inputRow(say("Storage reference", "مرجع ذخیره‌سازی"), item.storageRef)}
      <label class="cp-expense-note">${escapeHtml(say("Content hash", "هش محتوا"))}<input readonly value="${escapeHtml(item.contentHash)}"></label>
      ${inputRow(say("Linked records", "رکوردهای پیوندشده"), item.linkedEntityRefs.join(", ") || null)}
    </div>`;
  }

  function renderHistory(): string {
    if (state.historyStatus === "loading") {
      return `<div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading document history…", "در حال خواندن تاریخچهٔ سند…"))}</div>`;
    }
    if (state.historyStatus === "error") {
      return `<div class="cp-calendar-empty" role="alert">${escapeHtml(say("Document history could not be read.", "خواندن تاریخچهٔ سند ناموفق بود."))}</div>`;
    }
    if (!state.history.length) {
      return `<p>${escapeHtml(say("No history events are stored yet.", "هنوز رویدادی در تاریخچه ذخیره نشده است."))}</p>`;
    }
    return `<ol class="cp-issue-history">${state.history.map((event) =>
      `<li data-document-event="${escapeHtml(event.eventType)}"><strong>${escapeHtml(event.eventType)}</strong><span>${escapeHtml(event.actorId)} · ${escapeHtml(event.occurredAt)} · r${event.revision}</span>${event.reason ? `<p>${escapeHtml(event.reason)}</p>` : ""}</li>`
    ).join("")}</ol>`;
  }

  function renderDetails(): string {
    if (state.mode === "create" || state.mode === "edit") return renderForm();
    const item = selected();
    if (!item) {
      return `<p>${escapeHtml(say("Select a document from the register to read its stored metadata, history and available status actions.", "برای خواندن فراداده، تاریخچه و تغییرهای وضعیت، یک سند را از فهرست انتخاب کنید."))}</p>`;
    }
    const tabStrip = `<div class="cp-documents-tabs" role="tablist" aria-label="${escapeHtml(say("Document detail tabs", "زبانه‌های جزئیات سند"))}"><button type="button" role="tab" aria-selected="${state.tab === "general"}" data-document-tab="general" class="${state.tab === "general" ? "is-active" : ""}">${escapeHtml(say("General", "عمومی"))}</button><button type="button" role="tab" aria-selected="${state.tab === "history"}" data-document-tab="history" class="${state.tab === "history" ? "is-active" : ""}">${escapeHtml(say("History", "تاریخچه"))}</button></div>`;
    const body = state.tab === "history"
      ? renderHistory()
      : `${renderGeneral(item)}${renderStatusActions(item)}`;
    return `${tabStrip}<div class="cp-document-detail-body">${body}</div>
      <div class="cp-calendar-panel-actions"><button type="button" data-document-action="edit" ${state.busy || !canWrite || item.status === "superseded" ? "disabled" : ""}>${escapeHtml(say("Edit metadata", "ویرایش فراداده"))}</button></div>`;
  }

  function render(): void {
    host.innerHTML = `<div class="cp-register-toolbar"><strong>${escapeHtml(say("Project Documents", "اسناد پروژه"))}</strong><span>${state.documents.length} ${escapeHtml(say("record(s)", "رکورد"))}</span><div><button type="button" data-document-action="new" ${state.busy || !canWrite ? "disabled" : ""}>${escapeHtml(say("New Document", "سند جدید"))}</button><button type="button" data-document-action="reload" ${state.busy ? "disabled" : ""}>${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button></div></div>
      ${renderFilters()}
      ${renderRegister()}
      <section class="cp-register-details" data-document-details><header><strong>${escapeHtml(say("Document Details", "جزئیات سند"))}</strong><span>${selected() ? escapeHtml(selected()?.documentId ?? "") : escapeHtml(say("No selection", "بدون انتخاب"))}</span></header><div class="cp-register-detail-content">${renderDetails()}</div></section>
      ${state.notice ? `<p class="cp-calendar-notice" data-document-notice data-state="${state.notice.kind}" role="status">${escapeHtml(state.notice.message)}</p>` : ""}`;
  }

  async function refreshHistory(documentId: string): Promise<void> {
    state.historyStatus = "loading";
    render();
    const result = await loadDocumentHistory(transport, context, documentId);
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
    const result = await loadDocuments(transport, context, state.filters);
    if (result.ok) {
      state.status = "loaded";
      state.errorCode = null;
      state.documents = result.data;
      const kept = keepSelection && result.data.some((item) => item.documentId === keepSelection);
      state.selectedDocumentId = kept ? keepSelection : null;
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
    state.expectedRevision = item.revision;
    state.notice = null;
    render();
  }

  async function submitTransition(status: string): Promise<void> {
    const item = selected();
    if (!item || state.busy) return;
    state.busy = true;
    render();
    const result = await transitionDocument(
      transport,
      context,
      item.documentId,
      status,
      item.revision,
      state.transitionReason,
    );
    state.busy = false;
    if (!result.ok) {
      state.notice = {
        kind: "error",
        message: `${say("Status was not changed", "وضعیت تغییر نکرد")} (${result.error.code})`,
      };
      render();
      if (result.error.code === "DOCUMENT_REVISION_CONFLICT") await reload(item.documentId);
      return;
    }
    state.transitionReason = "";
    state.notice = {
      kind: "ok",
      message: say(`Document status is now ${result.data.status}.`, `وضعیت سند اکنون ${result.data.status} است.`),
    };
    state.tab = "general";
    await reload(result.data.documentId);
  }

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    const row = target.closest<HTMLElement>("[data-document-row]");
    if (row?.dataset.documentId) {
      state.selectedDocumentId = row.dataset.documentId;
      state.mode = "browse";
      state.tab = "general";
      state.notice = null;
      state.transitionReason = "";
      render();
      void refreshHistory(row.dataset.documentId);
      return;
    }
    const tab = target.closest<HTMLElement>("[data-document-tab]")?.dataset.documentTab as PageState["tab"] | undefined;
    if (tab) {
      state.tab = tab;
      render();
      if (tab === "history" && state.selectedDocumentId) void refreshHistory(state.selectedDocumentId);
      return;
    }
    const transition = target.closest<HTMLElement>("[data-document-transition]")?.dataset.documentTransition;
    if (transition) { void submitTransition(transition); return; }
    const action = target.closest<HTMLElement>("[data-document-action]")?.dataset.documentAction;
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
    if (action === "reload") { void reload(state.selectedDocumentId); return; }
    if (action === "apply-filters") {
      const search = host.querySelector<HTMLInputElement>("[name=document-search]");
      const type = host.querySelector<HTMLSelectElement>("[name=document-filter-type]");
      const status = host.querySelector<HTMLSelectElement>("[name=document-filter-status]");
      state.filters = {
        search: search?.value ?? "",
        resourceType: type?.value ?? "",
        status: status?.value ?? "",
      };
      void reload(null);
      return;
    }
    if (action === "clear-filters") {
      state.filters = { resourceType: "", status: "", search: "" };
      void reload(null);
      return;
    }
    if (action === "edit") { beginEdit(); }
  });

  host.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const row = (event.target as HTMLElement).closest<HTMLElement>("[data-document-row]");
    if (!row?.dataset.documentId) return;
    event.preventDefault();
    state.selectedDocumentId = row.dataset.documentId;
    state.mode = "browse";
    state.tab = "general";
    render();
    void refreshHistory(row.dataset.documentId);
  });

  host.addEventListener("input", (event) => {
    const target = event.target as HTMLInputElement;
    switch (target.name) {
      case "document-id": state.draft.documentId = target.value; break;
      case "document-title": state.draft.title = target.value; break;
      case "document-storage": state.draft.storageRef = target.value; break;
      case "document-hash": state.draft.contentHash = target.value; break;
      case "document-links":
        state.draft.linkedEntityRefs = target.value.split(",").map((item) => item.trim()).filter(Boolean);
        break;
      case "document-transition-reason": state.transitionReason = target.value; break;
      case "document-search": state.filters.search = target.value; break;
      default: break;
    }
  });

  host.addEventListener("change", (event) => {
    const target = event.target as HTMLSelectElement;
    if (target.name === "document-type") state.draft.resourceType = target.value;
  });

  host.addEventListener("submit", (event) => {
    const form = event.target as HTMLFormElement;
    if (!form.matches("[data-document-form]")) return;
    event.preventDefault();
    if (state.busy) return;
    void (async () => {
      state.busy = true;
      render();
      const creating = state.mode === "create";
      const current = creating ? null : selected();
      const result = creating
        ? await createDocument(transport, context, state.draft)
        : await updateDocument(
            transport,
            context,
            state.draft,
            current?.status ?? "draft",
            state.expectedRevision ?? 0,
          );
      state.busy = false;
      if (!result.ok) {
        state.notice = {
          kind: "error",
          message: `${creating ? say("Document was not created", "سند ایجاد نشد") : say("Document was not saved", "سند ذخیره نشد")} (${result.error.code})`,
        };
        render();
        if (result.error.code === "DOCUMENT_REVISION_CONFLICT") {
          state.mode = "browse";
          await reload(state.selectedDocumentId);
        }
        return;
      }
      state.notice = {
        kind: "ok",
        message: creating ? say("Document created as a draft.", "سند به‌صورت پیش‌نویس ایجاد شد.") : say("Document metadata saved.", "فرادادهٔ سند ذخیره شد."),
      };
      state.mode = "browse";
      state.tab = "general";
      await reload(result.data.documentId);
    })();
  });

  void reload(null);
}
