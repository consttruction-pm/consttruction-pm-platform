import type { ProjectContext } from "./client.js";
import {
  WorkspaceReadClient,
  type WorkspaceReadOptions,
} from "./workspace-read-api.js";
import type { WorkspaceState } from "./workspace-model.js";

/**
 * Structural seam for the shared client-sync WorkspaceReadCacheAdapter.
 *
 * Web does not own cache policy or scheduling/control calculations. The concrete
 * implementation is supplied by the application composition root and comes
 * from apps/client-sync.
 */
export interface WorkspaceReadCacheReader {
  read(
    context: ProjectContext,
    online: boolean,
    now?: string,
  ): Promise<{
    mode: "online" | "offline";
    state: "fresh" | "stale";
    cache: {
      workspace_read: Readonly<Record<string, unknown>>;
    };
  }>;
}

export type WorkspaceCachedReadResult = {
  data: WorkspaceState;
  mode: "online" | "offline";
  cacheState: "fresh" | "stale";
};

export class CachedWorkspaceReadClient {
  async load(
    context: ProjectContext,
    online: boolean,
    options: WorkspaceReadOptions = {},
  ): Promise<WorkspaceCachedReadResult> {
    const cached = await this.cacheReader.read(context, online);

    const transport = {
      async get<T>(
        _path: string,
        _context: ProjectContext,
      ) {
        return {
          ok: true as const,
          data: cached.cache.workspace_read as T,
        };
      },
      async post<TRequest, TResponse>() {
        throw new Error("CACHED_WORKSPACE_READ_TRANSPORT_POST_NOT_EXPECTED");
      },
    };

    const snapshotContext = readProjectContext(cached.cache.workspace_read);
    const result = await new WorkspaceReadClient(transport).load(snapshotContext, options);
    if (!result.ok) {
      throw new Error(result.error.code);
    }

    return {
      data: result.data,
      mode: cached.mode,
      cacheState: cached.state,
    };
  }

  constructor(private readonly cacheReader: WorkspaceReadCacheReader) {}
}

function readProjectContext(
  snapshot: Readonly<Record<string, unknown>>,
): ProjectContext {
  const value = snapshot.context;
  if (
    typeof value !== "object" ||
    value === null ||
    Array.isArray(value) ||
    typeof (value as Record<string, unknown>).tenant_id !== "string" ||
    typeof (value as Record<string, unknown>).project_id !== "string" ||
    !Number.isSafeInteger((value as Record<string, unknown>).revision) ||
    ((value as Record<string, unknown>).revision as number) < 0
  ) {
    throw new Error("INVALID_WORKSPACE_READ_CONTEXT");
  }

  return {
    tenant_id: (value as Record<string, string>).tenant_id,
    project_id: (value as Record<string, string>).project_id,
    revision: (value as Record<string, number>).revision,
  };
}
