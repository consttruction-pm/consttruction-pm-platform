import type { SyncProjectContext } from "./api-sync-transport.js";
import {
  classifyWorkspaceReadCache,
  createWorkspaceReadCache,
  type WorkspaceCacheState,
  type WorkspaceControlRoomReadCache,
} from "./workspace-read-cache.js";

export type WorkspaceReadResult =
  | { mode: "online"; state: "fresh"; cache: WorkspaceControlRoomReadCache }
  | { mode: "offline"; state: WorkspaceCacheState; cache: WorkspaceControlRoomReadCache }
  | { mode: "online"; state: "stale"; cache: WorkspaceControlRoomReadCache | null };

export interface WorkspaceControlRoomReadTransport {
  fetch(context: SyncProjectContext): Promise<Record<string, unknown>>;
}

export interface WorkspaceReadCacheStore {
  load(context: SyncProjectContext): Promise<WorkspaceControlRoomReadCache | null>;
  save(cache: WorkspaceControlRoomReadCache): Promise<void>;
}

export class WorkspaceReadCacheAdapter {
  constructor(
    private readonly transport: WorkspaceControlRoomReadTransport,
    private readonly store: WorkspaceReadCacheStore,
  ) {}

  async read(
    context: SyncProjectContext,
    online: boolean,
    now = new Date().toISOString(),
  ): Promise<WorkspaceReadResult> {
    const cached = await this.store.load(context);
    const cachedState = cached ? classifyWorkspaceReadCache(cached, context) : null;

    if (!online) {
      if (!cached) throw new Error("WORKSPACE_READ_UNAVAILABLE_OFFLINE");
      return { mode: "offline", state: cachedState ?? "stale", cache: cached };
    }

    if (cached && cachedState === "fresh") {
      return { mode: "online", state: "fresh", cache: cached };
    }

    const snapshot = await this.transport.fetch(context);
    const cache = createWorkspaceReadCache(snapshot, {
      snapshot_id: createSnapshotId(snapshot, context),
      cached_at: now,
    });

    if (classifyWorkspaceReadCache(cache, context) !== "fresh") {
      throw new Error("WORKSPACE_READ_REFRESH_SCOPE_MISMATCH");
    }

    await this.store.save(cache);
    return { mode: "online", state: "fresh", cache };
  }
}

function createSnapshotId(snapshot: Record<string, unknown>, context: SyncProjectContext): string {
  const snapshotContext = isRecord(snapshot.context) ? snapshot.context : undefined;
  return `workspace:${context.tenant_id}:${context.project_id}:${snapshotContext?.revision ?? context.revision}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
