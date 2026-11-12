import type { ApiResult, ApiTransport, DownloadedBinary, ProjectContext } from "./client.js";

/**
 * Project document register client.
 *
 * The document record is revision-guarded metadata. File bytes are stored
 * through the versioned content routes: the server re-validates type, size and
 * SHA-256, and this page verifies the digest it computed from the chosen file
 * before it reports success. No storage reference or hash is ever invented.
 */

export const DOCUMENT_API_VERSION = "1.0";
export const DOCUMENT_CONTENT_API_VERSION = "1.0";

/** Mirrors the server allow-list in `document_storage.py`. */
export const DOCUMENT_MAX_CONTENT_BYTES = 25 * 1024 * 1024;

export const DOCUMENT_CONTENT_TYPES: Readonly<Record<string, string>> = {
  "application/pdf": ".pdf",
  "image/png": ".png",
  "image/jpeg": ".jpg",
  "image/tiff": ".tiff",
  "image/webp": ".webp",
  "text/plain": ".txt",
  "text/csv": ".csv",
  "application/xml": ".xml",
  "text/xml": ".xml",
  "application/msword": ".doc",
  "application/vnd.ms-excel": ".xls",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
};

const EXTENSION_CONTENT_TYPES: Readonly<Record<string, string>> = {
  ".pdf": "application/pdf",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".tif": "image/tiff",
  ".tiff": "image/tiff",
  ".webp": "image/webp",
  ".txt": "text/plain",
  ".csv": "text/csv",
  ".xml": "application/xml",
  ".doc": "application/msword",
  ".xls": "application/vnd.ms-excel",
  ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
};

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

/** An immutable stored byte version as returned by the content API. */
export type DocumentContentVersion = {
  documentId: string;
  version: number;
  documentRevision: number;
  contentHash: string;
  contentType: string;
  byteSize: number;
  originalFilename: string;
  uploadedAt: string;
  uploadedBy: string;
};

export type DocumentContentUpload = {
  documentId: string;
  content: DocumentContentVersion;
  storageRef: string;
  idempotentReplay: boolean;
};

/** A file chosen in the browser, with the digest computed from its bytes. */
export type SelectedDocumentContent = {
  blob: Blob;
  name: string;
  contentType: string;
  byteSize: number;
  contentHash: string;
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

export function formatBytes(value: number): string {
  if (!Number.isFinite(value) || value < 0) return "—";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
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

function positiveInteger(value: unknown, code: string): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 1) throw new Error(code);
  return value;
}

function contentHashOf(value: unknown, code: string): string {
  const hash = requiredText(value, code);
  if (!/^sha256:[0-9a-f]{64}$/.test(hash)) throw new Error(code);
  return hash;
}

export function parseDocumentContentVersion(value: unknown): DocumentContentVersion {
  if (!isRecord(value)) throw new Error("INVALID_DOCUMENT_CONTENT_VERSION");
  return {
    documentId: requiredText(value.document_id, "INVALID_DOCUMENT_CONTENT_VERSION"),
    version: positiveInteger(value.version, "INVALID_DOCUMENT_CONTENT_VERSION"),
    documentRevision: positiveInteger(value.document_revision, "INVALID_DOCUMENT_CONTENT_VERSION"),
    contentHash: contentHashOf(value.content_hash, "INVALID_DOCUMENT_CONTENT_VERSION"),
    contentType: requiredText(value.content_type, "INVALID_DOCUMENT_CONTENT_VERSION"),
    byteSize: positiveInteger(value.byte_size, "INVALID_DOCUMENT_CONTENT_VERSION"),
    originalFilename: requiredText(value.original_filename, "INVALID_DOCUMENT_CONTENT_VERSION"),
    uploadedAt: requiredText(value.uploaded_at, "INVALID_DOCUMENT_CONTENT_VERSION"),
    uploadedBy: requiredText(value.uploaded_by, "INVALID_DOCUMENT_CONTENT_VERSION"),
  };
}

export function parseDocumentContentUpload(value: unknown): DocumentContentUpload {
  if (!isRecord(value) || value.contract_version !== DOCUMENT_CONTENT_API_VERSION) {
    throw new Error("INVALID_DOCUMENT_CONTENT_RESPONSE");
  }
  const documentId = requiredText(value.document_id, "INVALID_DOCUMENT_CONTENT_RESPONSE");
  const content = parseDocumentContentVersion(value.content);
  if (content.documentId !== documentId) throw new Error("INVALID_DOCUMENT_CONTENT_RESPONSE");
  return {
    documentId,
    content,
    storageRef: requiredText(value.storage_ref, "INVALID_DOCUMENT_CONTENT_RESPONSE"),
    idempotentReplay: value.idempotent_replay === true,
  };
}

export function parseDocumentContentVersions(value: unknown, documentId: string): DocumentContentVersion[] {
  if (!isRecord(value) || value.contract_version !== DOCUMENT_CONTENT_API_VERSION || !Array.isArray(value.versions)) {
    throw new Error("INVALID_DOCUMENT_CONTENT_VERSIONS");
  }
  const versions = value.versions.map((entry) => parseDocumentContentVersion(entry));
  if (versions.some((entry) => entry.documentId !== documentId)) {
    throw new Error("INVALID_DOCUMENT_CONTENT_VERSIONS");
  }
  const seen = new Set<number>();
  for (const entry of versions) {
    if (seen.has(entry.version)) throw new Error("INVALID_DOCUMENT_CONTENT_VERSIONS");
    seen.add(entry.version);
  }
  return versions;
}

/** Return the server allow-listed MIME type for a chosen file. */
export function resolveDocumentContentType(name: string, declared: string): string | null {
  const normalized = declared.split(";", 1)[0].trim().toLowerCase();
  if (normalized && DOCUMENT_CONTENT_TYPES[normalized]) return normalized;
  const match = /(\.[A-Za-z0-9]{1,8})$/.exec(name.trim());
  const extension = match ? match[1].toLowerCase() : "";
  return EXTENSION_CONTENT_TYPES[extension] ?? null;
}

/** Validate a chosen file locally before any byte leaves the browser. */
export function validateDocumentContent(name: string, declaredType: string, byteSize: number): string | null {
  if (!Number.isSafeInteger(byteSize) || byteSize <= 0) return "EMPTY_DOCUMENT_CONTENT";
  if (byteSize > DOCUMENT_MAX_CONTENT_BYTES) return "DOCUMENT_CONTENT_TOO_LARGE";
  if (!resolveDocumentContentType(name, declaredType)) return "DOCUMENT_CONTENT_TYPE_REJECTED";
  return null;
}

function hexDigest(buffer: ArrayBuffer): string {
  return [...new Uint8Array(buffer)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

/** Compute the SHA-256 the server will compare against the stored bytes. */
export async function documentContentHash(bytes: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return `sha256:${hexDigest(digest)}`;
}

/**
 * Read a chosen file, validate it against the documented limits and compute
 * its digest. The digest is derived from the bytes, never typed by a user.
 */
export async function prepareDocumentContent(file: {
  name: string;
  type: string;
  size: number;
  arrayBuffer: () => Promise<ArrayBuffer>;
}): Promise<ApiResult<SelectedDocumentContent>> {
  const problem = validateDocumentContent(file.name, file.type, file.size);
  if (problem) return localError(problem);
  const contentType = resolveDocumentContentType(file.name, file.type);
  if (!contentType) return localError("DOCUMENT_CONTENT_TYPE_REJECTED");
  try {
    const bytes = await file.arrayBuffer();
    if (bytes.byteLength !== file.size) return localError("DOCUMENT_CONTENT_SIZE_MISMATCH");
    return {
      ok: true,
      data: {
        blob: new Blob([bytes], { type: contentType }),
        name: file.name,
        contentType,
        byteSize: file.size,
        contentHash: await documentContentHash(bytes),
      },
    };
  } catch {
    return localError("DOCUMENT_CONTENT_READ_FAILED");
  }
}

/** Parse `filename*=UTF-8''…` or `filename="…"` from a Content-Disposition. */
export function downloadFilename(disposition: string, fallback: string): string {
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
  if (encoded) {
    try {
      return decodeURIComponent(encoded[1].trim());
    } catch {
      return fallback;
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(disposition);
  return plain ? plain[1].trim() : fallback;
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

function contentPath(context: ProjectContext, documentId: string, suffix = ""): string {
  const base = `${documentPath(context, documentId, "content")}`;
  return suffix ? `${base}/${suffix}` : base;
}

export async function loadDocumentContentVersions(
  transport: ApiTransport,
  context: ProjectContext,
  documentId: string,
): Promise<ApiResult<readonly DocumentContentVersion[]>> {
  const result = await transport.get<unknown>(contentPath(context, documentId, "versions"), context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseDocumentContentVersions(result.data, documentId) };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_DOCUMENT_CONTENT_VERSIONS");
  }
}

/**
 * Upload one immutable content version.
 *
 * The revision guard travels in the query and as a header; the idempotency key
 * makes a retry of the same bytes return the stored version instead of a new
 * one. The response digest must equal the digest computed from the chosen
 * file, or the client refuses to report a verified upload.
 */
export async function uploadDocumentContent(
  transport: ApiTransport,
  context: ProjectContext,
  documentId: string,
  content: SelectedDocumentContent,
  options: { expectedRevision: number; idempotencyKey: string },
): Promise<ApiResult<DocumentContentUpload>> {
  if (!transport.postBytes) return localError("TRANSPORT_POST_BYTES_UNSUPPORTED");
  if (!options.idempotencyKey.trim()) return localError("DOCUMENT_IDEMPOTENCY_KEY_REQUIRED");
  if (!Number.isSafeInteger(options.expectedRevision) || options.expectedRevision < 1) {
    return localError("INVALID_EXPECTED_DOCUMENT_REVISION");
  }
  const params = new URLSearchParams({
    expected_revision: String(options.expectedRevision),
    content_type: content.contentType,
    filename: content.name,
    idempotency_key: options.idempotencyKey,
  });
  const result = await transport.postBytes<unknown>(
    `${contentPath(context, documentId)}?${params.toString()}`,
    content.blob,
    content.contentType,
    context,
    {
      "X-File-Name": content.name,
      "X-Expected-Revision": String(options.expectedRevision),
      "Idempotency-Key": options.idempotencyKey,
    },
  );
  if (!result.ok) return result;
  try {
    const upload = parseDocumentContentUpload(result.data);
    if (upload.content.contentHash !== content.contentHash) {
      return localError("DOCUMENT_CONTENT_HASH_MISMATCH");
    }
    return { ok: true, data: upload };
  } catch (error) {
    return localError(error instanceof Error ? error.message : "INVALID_DOCUMENT_CONTENT_RESPONSE");
  }
}

/**
 * Download and verify one stored version (or the latest when version is null).
 * Bytes are only handed to the caller after their SHA-256 matches both the
 * server header and the digest recomputed in the browser.
 */
export async function downloadDocumentContent(
  transport: ApiTransport,
  context: ProjectContext,
  documentId: string,
  version: number | null = null,
): Promise<ApiResult<{ binary: DownloadedBinary; filename: string; contentHash: string }>> {
  if (!transport.download) return localError("TRANSPORT_DOWNLOAD_UNSUPPORTED");
  if (version !== null && (!Number.isSafeInteger(version) || version < 1)) {
    return localError("INVALID_DOCUMENT_CONTENT_VERSION");
  }
  const result = await transport.download(
    contentPath(context, documentId, version === null ? "" : String(version)),
    context,
  );
  if (!result.ok) return result;
  const binary = result.data;
  const declared = binary.contentSha256.trim().toLowerCase();
  if (!/^sha256:[0-9a-f]{64}$/.test(declared)) {
    return localError("DOCUMENT_CONTENT_HASH_MISSING");
  }
  let computed: string;
  try {
    computed = await documentContentHash(await binary.blob.arrayBuffer());
  } catch {
    return localError("DOCUMENT_CONTENT_READ_FAILED");
  }
  if (computed !== declared) return localError("DOCUMENT_CONTENT_HASH_MISMATCH");
  return {
    ok: true,
    data: {
      binary,
      filename: downloadFilename(binary.contentDisposition, documentId),
      contentHash: declared,
    },
  };
}

type PageState = {
  status: "loading" | "loaded" | "error";
  errorCode: string | null;
  documents: readonly DocumentRecord[];
  selectedDocumentId: string | null;
  mode: "browse" | "create" | "edit";
  draft: DocumentInput;
  expectedRevision: number | null;
  tab: "general" | "content" | "history";
  history: readonly DocumentHistoryEvent[];
  historyStatus: "idle" | "loading" | "loaded" | "error";
  versions: readonly DocumentContentVersion[];
  contentStatus: "idle" | "loading" | "loaded" | "error";
  contentError: string | null;
  selectedContent: SelectedDocumentContent | null;
  /** Set when a new document is created with a file; uploaded after create. */
  createContent: SelectedDocumentContent | null;
  uploadKey: string | null;
  downloadBusy: number | null;
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
    versions: [],
    contentStatus: "idle",
    contentError: null,
    selectedContent: null,
    createContent: null,
    uploadKey: null,
    downloadBusy: null,
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
    const chosen = creating ? state.createContent : null;
    const extensions = [...new Set(Object.values(DOCUMENT_CONTENT_TYPES))].join(",");
    return `<form data-document-form class="cp-expense-fields">
      <label>${escapeHtml(say("Document ID", "شناسه سند"))}<input name="document-id" value="${escapeHtml(draft.documentId)}" ${creating ? "" : "readonly"} required></label>
      <label>${escapeHtml(say("Title", "عنوان"))}<input name="document-title" value="${escapeHtml(draft.title)}" required></label>
      <label>${escapeHtml(say("Type", "نوع"))}<select name="document-type">${optionList(DOCUMENT_TYPES, draft.resourceType)}</select></label>
      <label>${escapeHtml(say("Source storage reference", "مرجع ذخیره‌سازی مبدأ"))}<input name="document-storage" value="${escapeHtml(draft.storageRef)}" placeholder="object://…" required></label>
      ${creating ? `<label class="cp-expense-note">${escapeHtml(say("Source file (optional, uploads after the record is created)", "فایل مبدأ (اختیاری، پس از ایجاد رکورد بارگذاری می‌شود)"))}<input type="file" name="document-create-file" accept="${extensions}" ${state.busy ? "disabled" : ""}></label>` : ""}
      <label class="cp-expense-note">${escapeHtml(say("SHA-256 content hash", "هش محتوای SHA-256"))}<input name="document-hash" value="${escapeHtml(draft.contentHash)}" placeholder="sha256:…" ${chosen ? "readonly" : ""} required></label>
      <label class="cp-expense-note">${escapeHtml(say("Linked records (comma separated)", "رکوردهای پیوندشده (با کاما جدا کنید)"))}<input name="document-links" value="${escapeHtml(draft.linkedEntityRefs.join(", "))}"></label>
      ${chosen
        ? `<p class="cp-calendar-notice" data-document-chosen-file>${escapeHtml(say(`Selected ${chosen.name} · ${formatBytes(chosen.byteSize)} · ${chosen.contentHash}`, `انتخاب‌شده ${chosen.name} · ${formatBytes(chosen.byteSize)} · ${chosen.contentHash}`))}</p>`
        : `<p class="cp-calendar-notice">${escapeHtml(say("The hash is computed from the selected file. A file selected here is uploaded immediately after the record is created; the server replaces the source reference with its content-addressed reference and records the verified digest.", "هش از فایل انتخاب‌شده محاسبه می‌شود. فایل انتخاب‌شده بلافاصله پس از ایجاد رکورد بارگذاری می‌شود؛ سرور مرجع مبدأ را با مرجع محتوا‌محور خود جایگزین می‌کند و هش تأییدشده را ثبت می‌کند."))}</p>`}
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

  function contentErrorMessage(code: string): string {
    switch (code) {
      case "DOCUMENT_CONTENT_TOO_LARGE":
        return say("The server rejected the file because it exceeds the 25 MB limit.", "سرور فایل را رد کرد زیرا از محدودیت ۲۵ مگابایت بزرگ‌تر است.");
      case "DOCUMENT_CONTENT_TYPE_REJECTED":
      case "DOCUMENT_CONTENT_TYPE_MISMATCH":
      case "DOCUMENT_CONTENT_TYPE_UNRECOGNIZED":
        return say("The server rejected the file type. Allowed: PDF, Office, image, text, CSV and XML files.", "سرور نوع فایل را رد کرد. مجاز: PDF، آفیس، تصویر، متن، CSV و XML.");
      case "DOCUMENT_CONTENT_HASH_MISMATCH":
      case "DOCUMENT_CONTENT_INTEGRITY_FAILED":
        return say("The stored bytes did not match the SHA-256 digest, so nothing was treated as verified.", "بایت‌های ذخیره‌شده با هش SHA-256 مطابقت نداشتند؛ بنابراین هیچ چیز تأییدشده تلقی نشد.");
      case "DOCUMENT_REVISION_CONFLICT":
        return say("Another session changed this document. The latest revision was reloaded; choose the file again.", "نشست دیگری این سند را تغییر داد. آخرین نسخه دوباره بارگذاری شد؛ فایل را دوباره انتخاب کنید.");
      case "DOCUMENT_PERMISSION_DENIED":
      case "DOCUMENT_ACTOR_MISMATCH":
      case "DOCUMENT_CROSS_SCOPE":
        return say("This account may not upload document bytes to this project.", "این حساب اجازهٔ بارگذاری بایت‌های سند در این پروژه را ندارد.");
      case "DOCUMENT_CONTENT_NOT_FOUND":
        return say("No stored bytes exist for this document or version.", "هیچ بایت ذخیره‌شده‌ای برای این سند یا نسخه وجود ندارد.");
      case "DOCUMENT_STORAGE_UNAVAILABLE":
      case "DOCUMENT_STORAGE_ERROR":
        return say("The binary store is unavailable. Nothing was marked as uploaded.", "مخزن باینری در دسترس نیست. هیچ چیز به‌عنوان بارگذاری‌شده علامت‌گذاری نشد.");
      case "TRANSPORT_POST_BYTES_UNSUPPORTED":
      case "TRANSPORT_DOWNLOAD_UNSUPPORTED":
        return say("This runtime cannot stream file bytes; use the full workspace server.", "این محیط اجرا نمی‌تواند بایت‌های فایل را جریان دهد؛ از سرور کامل محیط کار استفاده کنید.");
      default:
        return say("The file operation did not complete.", "عملیات فایل کامل نشد.");
    }
  }

  function renderContent(item: DocumentRecord): string {
    const canUpload = canWrite && !state.busy;
    const chosen = state.selectedContent;
    const extensions = [...new Set(Object.values(DOCUMENT_CONTENT_TYPES))].join(",");
    const fileControl = `<div class="cp-document-upload">
        <label>${escapeHtml(say("File to upload", "فایل برای بارگذاری"))}<input type="file" name="document-content-file" accept="${extensions}" ${canUpload ? "" : "disabled"}></label>
        <button type="button" data-document-action="upload-content" ${canUpload && chosen ? "" : "disabled"}>${escapeHtml(say("Upload as new version", "بارگذاری به‌عنوان نسخهٔ جدید"))}</button>
      </div>`;
    const chosenBlock = chosen
      ? `<p class="cp-document-selected" data-document-selected-file>${escapeHtml(say(`${chosen.name} · ${formatBytes(chosen.byteSize)} · ${chosen.contentType}`, `${chosen.name} · ${formatBytes(chosen.byteSize)} · ${chosen.contentType}`))}<code>${escapeHtml(chosen.contentHash)}</code></p>`
      : `<p class="cp-calendar-notice">${escapeHtml(say("Choosing a file computes its SHA-256 locally; the server re-validates type, size and digest before storing a version.", "انتخاب فایل، SHA-256 آن را به‌صورت محلی محاسبه می‌کند؛ سرور پیش از ذخیرهٔ نسخه، نوع، اندازه و هش را دوباره اعتبارسنجی می‌کند."))}</p>`;
    let versions: string;
    if (state.contentStatus === "loading") {
      versions = `<div class="cp-calendar-empty" role="status">${escapeHtml(say("Reading stored file versions…", "در حال خواندن نسخه‌های فایل ذخیره‌شده…"))}</div>`;
    } else if (state.contentStatus === "error") {
      versions = `<div class="cp-calendar-empty" role="alert" data-document-content-error="${escapeHtml(state.contentError ?? "unknown")}">${escapeHtml(say("Stored file versions could not be read", "خواندن نسخه‌های فایل ذخیره‌شده ناموفق بود"))} (${escapeHtml(state.contentError ?? "unknown")})</div>`;
    } else if (!state.versions.length) {
      versions = `<div class="cp-calendar-empty" data-document-content-empty>${escapeHtml(say("No file bytes are stored for this document yet.", "هنوز هیچ بایت فایلی برای این سند ذخیره نشده است."))}</div>`;
    } else {
      const rows = [...state.versions].sort((left, right) => right.version - left.version).map((version) => {
        const busy = state.downloadBusy === version.version;
        return `<tr data-document-version="${version.version}"><td>${version.version}</td><td>${escapeHtml(version.originalFilename)}</td><td>${escapeHtml(version.contentType)}</td><td>${escapeHtml(formatBytes(version.byteSize))}</td><td><code title="${escapeHtml(version.contentHash)}">${escapeHtml(version.contentHash.slice(0, 19))}…</code></td><td>${escapeHtml(version.uploadedAt)}</td><td>${escapeHtml(version.uploadedBy)}</td><td><button type="button" data-document-action="download-content" data-document-version="${version.version}" ${busy ? "disabled" : ""}>${escapeHtml(busy ? say("Verifying…", "در حال تأیید…") : say("Download", "دانلود"))}</button></td></tr>`;
      }).join("");
      versions = `<div class="cp-document-versions"><table><thead><tr><th>${escapeHtml(say("Version", "نسخه"))}</th><th>${escapeHtml(say("File", "فایل"))}</th><th>${escapeHtml(say("Type", "نوع"))}</th><th>${escapeHtml(say("Size", "اندازه"))}</th><th>${escapeHtml(say("SHA-256", "SHA-256"))}</th><th>${escapeHtml(say("Uploaded", "بارگذاری"))}</th><th>${escapeHtml(say("By", "توسط"))}</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>`;
    }
    return `<div class="cp-document-content" data-document-content>
      ${versions}
      ${fileControl}
      ${chosenBlock}
      ${canWrite ? "" : `<p class="cp-detail-hint">${escapeHtml(say("Viewers may download stored versions. Uploading requires the project planner or administrator role.", "بازدیدکنندگان می‌توانند نسخه‌های ذخیره‌شده را دانلود کنند. بارگذاری به نقش برنامه‌ریز یا مدیر پروژه نیاز دارد."))}</p>`}
      <p class="cp-calendar-notice">${escapeHtml(say("Bytes live behind a content-addressed server reference; each download verifies the SHA-256 header against the bytes.", "بایت‌ها پشت یک مرجع محتوا‌محور سمت سرور قرار دارند؛ هر دانلود هش SHA-256 را با بایت‌ها تطبیق می‌دهد."))}</p>
    </div>`;
  }

  function renderDetails(): string {
    if (state.mode === "create" || state.mode === "edit") return renderForm();
    const item = selected();
    if (!item) {
      return `<p>${escapeHtml(say("Select a document from the register to read its stored metadata, history and available status actions.", "برای خواندن فراداده، تاریخچه و تغییرهای وضعیت، یک سند را از فهرست انتخاب کنید."))}</p>`;
    }
    const tabs: Array<{ id: PageState["tab"]; en: string; fa: string }> = [
      { id: "general", en: "General", fa: "عمومی" },
      { id: "content", en: "Content", fa: "محتوا" },
      { id: "history", en: "History", fa: "تاریخچه" },
    ];
    const tabStrip = `<div class="cp-documents-tabs" role="tablist" aria-label="${escapeHtml(say("Document detail tabs", "زبانه‌های جزئیات سند"))}">${tabs.map((tab) =>
      `<button type="button" role="tab" aria-selected="${state.tab === tab.id}" data-document-tab="${tab.id}" class="${state.tab === tab.id ? "is-active" : ""}">${escapeHtml(say(tab.en, tab.fa))}</button>`
    ).join("")}</div>`;
    const body = state.tab === "history"
      ? renderHistory()
      : state.tab === "content"
        ? renderContent(item)
        : `${renderGeneral(item)}${renderStatusActions(item)}`;
    return `${tabStrip}<div class="cp-document-detail-body">${body}</div>
      ${state.tab === "general" ? `<div class="cp-calendar-panel-actions"><button type="button" data-document-action="edit" ${state.busy || !canWrite || item.status === "superseded" ? "disabled" : ""}>${escapeHtml(say("Edit metadata", "ویرایش فراداده"))}</button></div>` : ""}`;
  }

  function render(): void {
    host.dataset.documentsStatus = state.status;
    host.dataset.documentsSelected = state.selectedDocumentId ?? "";
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

  async function refreshContent(documentId: string): Promise<void> {
    state.contentStatus = "loading";
    state.contentError = null;
    render();
    const result = await loadDocumentContentVersions(transport, context, documentId);
    if (result.ok) {
      state.contentStatus = "loaded";
      state.versions = result.data;
    } else {
      state.contentStatus = "error";
      state.versions = [];
      state.contentError = result.error.code;
    }
    render();
  }

  function resetContentState(): void {
    state.versions = [];
    state.contentStatus = "idle";
    state.contentError = null;
    state.selectedContent = null;
    state.uploadKey = null;
    state.downloadBusy = null;
  }

  async function chooseContent(file: File | null): Promise<void> {
    if (!file) {
      state.selectedContent = null;
      state.uploadKey = null;
      render();
      return;
    }
    const prepared = await prepareDocumentContent(file);
    if (!prepared.ok) {
      state.selectedContent = null;
      state.uploadKey = null;
      state.notice = {
        kind: "error",
        message: `${contentErrorMessage(prepared.error.code)} (${prepared.error.code})`,
      };
      render();
      return;
    }
    state.selectedContent = prepared.data;
    // One key per chosen digest: retrying the same bytes is idempotent, a new
    // file gets a new key.
    state.uploadKey = crypto.randomUUID();
    state.notice = null;
    render();
  }

  async function chooseCreateContent(file: File | null): Promise<void> {
    if (!file) {
      state.createContent = null;
      state.draft.contentHash = "";
      render();
      return;
    }
    const prepared = await prepareDocumentContent(file);
    if (!prepared.ok) {
      state.createContent = null;
      state.notice = {
        kind: "error",
        message: `${contentErrorMessage(prepared.error.code)} (${prepared.error.code})`,
      };
      render();
      return;
    }
    state.createContent = prepared.data;
    // The hash shown in the create form is derived from the bytes the user
    // chose, never typed or guessed.
    state.draft.contentHash = prepared.data.contentHash;
    state.notice = null;
    render();
  }

  function saveBinary(binary: DownloadedBinary, filename: string): void {
    const owner = host.ownerDocument ?? (typeof document === "undefined" ? null : document);
    if (!owner || typeof URL.createObjectURL !== "function") return;
    const url = URL.createObjectURL(binary.blob);
    const anchor = owner.createElement("a");
    anchor.href = url;
    anchor.download = filename || "document";
    anchor.rel = "noopener";
    owner.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4_000);
  }

  async function uploadSelectedContent(item: DocumentRecord, content: SelectedDocumentContent): Promise<void> {
    if (state.busy) return;
    state.busy = true;
    state.notice = null;
    render();
    const result = await uploadDocumentContent(transport, context, item.documentId, content, {
      expectedRevision: item.revision,
      idempotencyKey: state.uploadKey ?? crypto.randomUUID(),
    });
    state.busy = false;
    if (!result.ok) {
      state.notice = {
        kind: "error",
        message: `${contentErrorMessage(result.error.code)} (${result.error.code})`,
      };
      render();
      if (result.error.code === "DOCUMENT_REVISION_CONFLICT") {
        await reload(item.documentId);
        await refreshContent(item.documentId);
      }
      return;
    }
    state.selectedContent = null;
    state.uploadKey = null;
    state.notice = {
      kind: "ok",
      message: say(
        `Stored version ${result.data.content.version} and verified ${result.data.content.contentHash.slice(0, 19)}…`,
        `نسخهٔ ${result.data.content.version} ذخیره و ${result.data.content.contentHash.slice(0, 19)}… تأیید شد.`,
      ),
    };
    state.tab = "content";
    await reload(result.data.documentId);
    await refreshContent(result.data.documentId);
  }

  async function downloadVersion(item: DocumentRecord, version: number): Promise<void> {
    if (state.downloadBusy !== null) return;
    state.downloadBusy = version;
    state.notice = null;
    render();
    const result = await downloadDocumentContent(transport, context, item.documentId, version);
    state.downloadBusy = null;
    if (!result.ok) {
      state.notice = {
        kind: "error",
        message: `${contentErrorMessage(result.error.code)} (${result.error.code})`,
      };
      render();
      return;
    }
    saveBinary(result.data.binary, result.data.filename);
    state.notice = {
      kind: "ok",
      message: say(
        `Downloaded ${result.data.filename}; SHA-256 verified.`,
        `${result.data.filename} دانلود شد؛ SHA-256 تأیید شد.`,
      ),
    };
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
      else { state.history = []; state.historyStatus = "idle"; resetContentState(); }
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
      resetContentState();
      render();
      void refreshHistory(row.dataset.documentId);
      return;
    }
    const tab = target.closest<HTMLElement>("[data-document-tab]")?.dataset.documentTab as PageState["tab"] | undefined;
    if (tab) {
      state.tab = tab;
      render();
      if (tab === "history" && state.selectedDocumentId) void refreshHistory(state.selectedDocumentId);
      if (tab === "content" && state.selectedDocumentId && state.contentStatus === "idle") {
        void refreshContent(state.selectedDocumentId);
      }
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
      state.createContent = null;
      state.notice = null;
      render();
      return;
    }
    if (action === "cancel") {
      state.mode = "browse";
      state.createContent = null;
      state.notice = null;
      render();
      return;
    }
    if (action === "reload") { void reload(state.selectedDocumentId); return; }
    if (action === "upload-content") {
      const item = selected();
      if (item && state.selectedContent) void uploadSelectedContent(item, state.selectedContent);
      return;
    }
    if (action === "download-content") {
      const item = selected();
      const version = Number(target.closest<HTMLElement>("[data-document-action]")?.dataset.documentVersion);
      if (item && Number.isSafeInteger(version) && version > 0) void downloadVersion(item, version);
      return;
    }
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
    resetContentState();
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
    const target = event.target as HTMLInputElement;
    if (target.name === "document-type") state.draft.resourceType = target.value;
    if (target.name === "document-content-file" || target.name === "document-create-file") {
      const file = target.files?.[0] ?? null;
      if (target.name === "document-create-file") void chooseCreateContent(file);
      else void chooseContent(file);
    }
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
      const pendingContent = creating ? state.createContent : null;
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
      state.createContent = null;
      state.tab = "general";
      await reload(result.data.documentId);
      if (pendingContent) {
        const created = selected();
        if (created) await uploadSelectedContent(created, pendingContent);
      }
    })();
  });

  void reload(null);
}
