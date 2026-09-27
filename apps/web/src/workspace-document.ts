import type { ProjectScope } from "./workspace-field-ops.js";

export const DOCUMENT_WEB_VERSION = "document-web.v1" as const;

export const DOCUMENT_TYPES = [
  "contract",
  "drawing",
  "correspondence",
  "rfi",
  "submittal",
  "delay_claim",
  "evidence",
] as const;

export const DOCUMENT_STATUSES = [
  "draft",
  "submitted",
  "approved",
  "rejected",
  "superseded",
] as const;

export type WorkspaceDocumentType = (typeof DOCUMENT_TYPES)[number];
export type WorkspaceDocumentStatus = (typeof DOCUMENT_STATUSES)[number];

export type DocumentSnapshot = Readonly<{
  document_id: string;
  tenant_id: string;
  project_id: string;
  resource_type: string;
  title: string;
  status: string;
  storage_ref: string;
  content_hash: string;
  linked_entity_refs: readonly string[];
  revision: number;
}>;

export type WorkspaceDocument = Readonly<{
  documentId: string;
  resourceType: WorkspaceDocumentType;
  title: string;
  status: WorkspaceDocumentStatus;
  revision: number;
  contentHash: string;
  linkedEntityRefs: readonly string[];
  hasStorageRef: boolean;
}>;

export function projectDocument(
  snapshot: DocumentSnapshot,
  scope: ProjectScope,
): WorkspaceDocument {
  if (
    !Number.isInteger(snapshot.revision) ||
    snapshot.revision < 0 ||
    snapshot.revision > 9_007_199_254_740_991
  ) {
    throw new Error("INVALID_DOCUMENT_REVISION");
  }
  if (
    snapshot.tenant_id !== scope.tenant_id ||
    snapshot.project_id !== scope.project_id ||
    snapshot.revision !== scope.project_revision
  ) {
    throw new Error("STALE_DOCUMENT_SCOPE");
  }
  if (!DOCUMENT_TYPES.includes(snapshot.resource_type as WorkspaceDocumentType)) {
    throw new Error("UNSUPPORTED_DOCUMENT_TYPE");
  }
  if (!DOCUMENT_STATUSES.includes(snapshot.status as WorkspaceDocumentStatus)) {
    throw new Error("UNSUPPORTED_DOCUMENT_STATUS");
  }
  if (!snapshot.document_id.trim() || !snapshot.title.trim()) {
    throw new Error("INVALID_DOCUMENT_IDENTITY");
  }
  if (!snapshot.storage_ref.trim()) {
    throw new Error("INVALID_DOCUMENT_STORAGE_REF");
  }
  if (!/^sha256:[0-9a-fA-F]{64}$/.test(snapshot.content_hash)) {
    throw new Error("INVALID_DOCUMENT_CONTENT_HASH");
  }
  if (!Array.isArray(snapshot.linked_entity_refs) || !snapshot.linked_entity_refs.every((ref) => typeof ref === "string" && ref.trim())) {
    throw new Error("INVALID_DOCUMENT_LINKS");
  }

  return Object.freeze({
    documentId: snapshot.document_id,
    resourceType: snapshot.resource_type as WorkspaceDocumentType,
    title: snapshot.title,
    status: snapshot.status as WorkspaceDocumentStatus,
    revision: snapshot.revision,
    contentHash: snapshot.content_hash,
    linkedEntityRefs: Object.freeze([...snapshot.linked_entity_refs]),
    hasStorageRef: true,
  });
}
