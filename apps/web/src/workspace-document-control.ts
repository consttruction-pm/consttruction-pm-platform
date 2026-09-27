export const DOCUMENT_RESOURCE_VERSION = "1.0" as const;
export const DOCUMENT_OCR_VERSION = "1.0" as const;
export const DOCUMENT_SEARCH_INDEX_VERSION = "1.0" as const;

export type WorkspaceDocumentType =
  | "contract"
  | "drawing"
  | "correspondence"
  | "rfi"
  | "submittal"
  | "delay_claim"
  | "evidence";

export type WorkspaceDocumentStatus = "draft" | "submitted" | "approved" | "rejected" | "superseded";

export type WorkspaceDocument = Readonly<{
  resourceId: string;
  resourceType: WorkspaceDocumentType;
  revision: number;
  title: string;
  status: WorkspaceDocumentStatus;
  storageRef: string | null;
  contentHash: string | null;
  linkedEntityRefs: readonly string[];
  ocrAvailable: boolean;
  indexed: boolean;
}>;

export type WorkspaceOcrResult = Readonly<{
  documentId: string;
  revision: number;
  provider: string;
  textLength: number;
}>;

export type WorkspaceSearchIndexEntry = Readonly<{
  documentId: string;
  revision: number;
  contentHash: string;
  indexedTextLength: number;
}>;

export type DocumentResourceSnapshot = {
  contract_version: typeof DOCUMENT_RESOURCE_VERSION;
  resource_type: WorkspaceDocumentType;
  resource_id: string;
  tenant_id: string;
  project_id: string;
  revision: number;
  payload: {
    title?: string;
    status?: WorkspaceDocumentStatus;
    storage_ref?: string | null;
    content_hash?: string | null;
    linked_entity_refs?: readonly string[];
    [key: string]: unknown;
  };
};

export type DocumentOcrSnapshot = {
  contract_version: typeof DOCUMENT_OCR_VERSION;
  tenant_id: string;
  project_id: string;
  document_id: string;
  revision: number;
  text: string;
  provider: string;
};

export type DocumentSearchIndexSnapshot = {
  contract_version: typeof DOCUMENT_SEARCH_INDEX_VERSION;
  tenant_id: string;
  project_id: string;
  document_id: string;
  revision: number;
  content_hash: string;
  text: string;
};

export function projectDocument(
  snapshot: DocumentResourceSnapshot,
  context: { tenant_id: string; project_id: string },
  ocr?: DocumentOcrSnapshot,
  index?: DocumentSearchIndexSnapshot,
): WorkspaceDocument {
  if (snapshot.contract_version !== DOCUMENT_RESOURCE_VERSION) {
    throw new Error("UNSUPPORTED_DOCUMENT_RESOURCE_CONTRACT");
  }
  assertScope(snapshot.tenant_id, snapshot.project_id, snapshot.revision, context);
  if (!snapshot.resource_id || !snapshot.resource_type || !Number.isInteger(snapshot.revision) || snapshot.revision < 0) {
    throw new Error("INVALID_DOCUMENT_RESOURCE");
  }

  const title = typeof snapshot.payload.title === "string" ? snapshot.payload.title : snapshot.resource_id;
  const status = snapshot.payload.status ?? "draft";
  if (!["draft", "submitted", "approved", "rejected", "superseded"].includes(status)) {
    throw new Error("INVALID_DOCUMENT_STATUS");
  }

  const storageRef = snapshot.payload.storage_ref ?? null;
  const contentHash = snapshot.payload.content_hash ?? null;
  if (contentHash !== null && !/^sha256:[0-9a-f]{64}$/.test(contentHash)) {
    throw new Error("INVALID_DOCUMENT_CONTENT_HASH");
  }

  const linkedEntityRefs = snapshot.payload.linked_entity_refs ?? [];
  if (!Array.isArray(linkedEntityRefs) || linkedEntityRefs.some((value) => !value || typeof value !== "string")) {
    throw new Error("INVALID_DOCUMENT_LINKED_ENTITY_REFS");
  }

  if (ocr) validateOcrSnapshot(ocr, context, snapshot);
  if (index) validateIndexSnapshot(index, context, snapshot);

  return Object.freeze({
    resourceId: snapshot.resource_id,
    resourceType: snapshot.resource_type,
    revision: snapshot.revision,
    title,
    status,
    storageRef,
    contentHash,
    linkedEntityRefs: Object.freeze([...linkedEntityRefs]),
    ocrAvailable: Boolean(ocr),
    indexed: Boolean(index),
  });
}

export function projectOcrResult(
  snapshot: DocumentOcrSnapshot,
  context: { tenant_id: string; project_id: string },
): WorkspaceOcrResult {
  if (snapshot.contract_version !== DOCUMENT_OCR_VERSION) {
    throw new Error("UNSUPPORTED_DOCUMENT_OCR_CONTRACT");
  }
  if (
    snapshot.tenant_id !== context.tenant_id ||
    snapshot.project_id !== context.project_id
  ) {
    throw new Error("STALE_DOCUMENT_OCR_SCOPE");
  }
  if (!snapshot.document_id || !snapshot.provider || typeof snapshot.text !== "string") {
    throw new Error("INVALID_DOCUMENT_OCR");
  }
  return Object.freeze({
    documentId: snapshot.document_id,
    revision: snapshot.revision,
    provider: snapshot.provider,
    textLength: snapshot.text.length,
  });
}

export function projectSearchIndex(
  snapshot: DocumentSearchIndexSnapshot,
  context: { tenant_id: string; project_id: string },
): WorkspaceSearchIndexEntry {
  if (snapshot.contract_version !== DOCUMENT_SEARCH_INDEX_VERSION) {
    throw new Error("UNSUPPORTED_DOCUMENT_SEARCH_CONTRACT");
  }
  if (
    snapshot.tenant_id !== context.tenant_id ||
    snapshot.project_id !== context.project_id
  ) {
    throw new Error("STALE_DOCUMENT_SEARCH_SCOPE");
  }
  if (
    !snapshot.document_id ||
    !/^sha256:[0-9a-f]{64}$/.test(snapshot.content_hash) ||
    typeof snapshot.text !== "string"
  ) {
    throw new Error("INVALID_DOCUMENT_SEARCH_INDEX");
  }
  return Object.freeze({
    documentId: snapshot.document_id,
    revision: snapshot.revision,
    contentHash: snapshot.content_hash,
    indexedTextLength: snapshot.text.length,
  });
}

function validateOcrSnapshot(
  snapshot: DocumentOcrSnapshot,
  context: { tenant_id: string; project_id: string },
  document: DocumentResourceSnapshot,
): void {
  const result = projectOcrResult(snapshot, context);
  if (result.documentId !== document.resource_id || result.revision !== document.revision) {
    throw new Error("DOCUMENT_OCR_REVISION_MISMATCH");
  }
}

function validateIndexSnapshot(
  snapshot: DocumentSearchIndexSnapshot,
  context: { tenant_id: string; project_id: string },
  document: DocumentResourceSnapshot,
): void {
  const result = projectSearchIndex(snapshot, context);
  if (result.documentId !== document.resource_id || result.revision !== document.revision) {
    throw new Error("DOCUMENT_INDEX_REVISION_MISMATCH");
  }
  if (document.payload.content_hash && result.contentHash !== document.payload.content_hash) {
    throw new Error("DOCUMENT_INDEX_CONTENT_HASH_MISMATCH");
  }
}

function assertScope(
  tenantId: string,
  projectId: string,
  revision: number,
  context: { tenant_id: string; project_id: string },
): void {
  if (
    tenantId !== context.tenant_id ||
    projectId !== context.project_id
  ) {
    throw new Error("STALE_DOCUMENT_RESOURCE_SCOPE");
  }
}
