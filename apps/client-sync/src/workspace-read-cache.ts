import type { SyncProjectContext } from "./api-sync-transport.js";

export const WORKSPACE_CONTROL_ROOM_CACHE_VERSION =
  "workspace-control-room-cache.v1" as const;

export type WorkspaceControlRoomReadCache = {
  contract_version: typeof WORKSPACE_CONTROL_ROOM_CACHE_VERSION;
  snapshot_id: string;
  tenant_id: string;
  project_id: string;
  source_revision: number;
  cached_at: string;
  workspace_read: Readonly<Record<string, unknown>>;
};

export type WorkspaceCacheState = "fresh" | "stale";

export function createWorkspaceReadCache(
  snapshot: Record<string, unknown>,
  metadata: {
    snapshot_id: string;
    cached_at: string;
  },
): WorkspaceControlRoomReadCache {
  validateWorkspaceReadEnvelope(snapshot);

  const context = snapshot.context;
  if (!isRecord(context)) {
    throw new Error("INVALID_WORKSPACE_READ_CONTEXT");
  }

  const entry: WorkspaceControlRoomReadCache = {
    contract_version: WORKSPACE_CONTROL_ROOM_CACHE_VERSION,
    snapshot_id: readNonEmptyString(metadata.snapshot_id, "INVALID_WORKSPACE_READ_CACHE_METADATA"),
    tenant_id: readNonEmptyString(context.tenant_id, "INVALID_WORKSPACE_READ_CONTEXT"),
    project_id: readNonEmptyString(context.project_id, "INVALID_WORKSPACE_READ_CONTEXT"),
    source_revision: readRevision(context.revision, "INVALID_WORKSPACE_READ_CONTEXT"),
    cached_at: readDateTime(metadata.cached_at),
    workspace_read: deepFreeze(deepClone(snapshot)),
  };

  return Object.freeze(entry);
}

export function classifyWorkspaceReadCache(
  cache: WorkspaceControlRoomReadCache,
  requestedContext: SyncProjectContext,
): WorkspaceCacheState {
  validateWorkspaceReadCache(cache);

  if (
    cache.tenant_id !== requestedContext.tenant_id ||
    cache.project_id !== requestedContext.project_id ||
    cache.source_revision !== requestedContext.revision
  ) {
    return "stale";
  }

  return "fresh";
}

export function validateWorkspaceReadCache(
  cache: WorkspaceControlRoomReadCache,
): void {
  if (!isRecord(cache)) throw new Error("INVALID_WORKSPACE_READ_CACHE");
  if (cache.contract_version !== WORKSPACE_CONTROL_ROOM_CACHE_VERSION) {
    throw new Error("UNSUPPORTED_WORKSPACE_READ_CACHE_CONTRACT");
  }
  readNonEmptyString(cache.snapshot_id, "INVALID_WORKSPACE_READ_CACHE_METADATA");
  readNonEmptyString(cache.tenant_id, "INVALID_WORKSPACE_READ_CACHE_METADATA");
  readNonEmptyString(cache.project_id, "INVALID_WORKSPACE_READ_CACHE_METADATA");
  readRevision(cache.source_revision, "INVALID_WORKSPACE_READ_CACHE_METADATA");
  readDateTime(cache.cached_at);

  if (!isRecord(cache.workspace_read)) {
    throw new Error("INVALID_WORKSPACE_READ_CACHE_SNAPSHOT");
  }

  validateWorkspaceReadEnvelope(cache.workspace_read);

  const context = cache.workspace_read.context;
  if (!isRecord(context)) {
    throw new Error("INVALID_WORKSPACE_READ_CONTEXT");
  }
  if (
    context.tenant_id !== cache.tenant_id ||
    context.project_id !== cache.project_id ||
    context.revision !== cache.source_revision
  ) {
    throw new Error("CACHE_SNAPSHOT_SCOPE_MISMATCH");
  }
}

function validateWorkspaceReadEnvelope(snapshot: Record<string, unknown>): void {
  if (snapshot.contract_version !== "workspace-control-room-read.v1") {
    throw new Error("UNSUPPORTED_WORKSPACE_READ_CONTRACT");
  }

  const context = snapshot.context;
  if (!isRecord(context)) throw new Error("INVALID_WORKSPACE_READ_CONTEXT");

  readNonEmptyString(context.tenant_id, "INVALID_WORKSPACE_READ_CONTEXT");
  readNonEmptyString(context.project_id, "INVALID_WORKSPACE_READ_CONTEXT");
  readRevision(context.revision, "INVALID_WORKSPACE_READ_CONTEXT");
}

function readRevision(value: unknown, errorCode: string): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0) throw new Error(errorCode);
  return value;
}

function readNonEmptyString(value: unknown, errorCode: string): string {
  if (typeof value !== "string" || value.length === 0) throw new Error(errorCode);
  return value;
}

function readDateTime(value: unknown): string {
  if (typeof value !== "string" || Number.isNaN(Date.parse(value))) {
    throw new Error("INVALID_WORKSPACE_READ_CACHE_TIMESTAMP");
  }
  return value;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function deepClone<T>(value: T): T {
  if (Array.isArray(value)) {
    return value.map((item) => deepClone(item)) as T;
  }
  if (isRecord(value)) {
    return Object.fromEntries(
      Object.entries(value).map(([key, child]) => [key, deepClone(child)]),
    ) as T;
  }
  return value;
}

function deepFreeze<T>(value: T): T {
  if (typeof value !== "object" || value === null) return value;
  if (Array.isArray(value)) {
    for (const child of value) deepFreeze(child);
  } else {
    for (const child of Object.values(value as Record<string, unknown>)) {
      deepFreeze(child);
    }
  }
  return Object.freeze(value);
}
