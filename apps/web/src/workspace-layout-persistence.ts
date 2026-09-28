import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import { migrateWorkspaceLayout, type WorkspaceLayout, type WorkspaceLayoutStore } from "./workspace-layout.js";
import type { P6FieldCatalogEntry } from "./p6-field-registry-client.js";

export type WorkspaceLayoutPersistence = {
  loadLayout(
    context: ProjectContext,
    subjectArea: string,
    scope: WorkspaceLayout["scope"],
    layoutId: string,
  ): Promise<ApiResult<unknown>>;
  saveLayout(
    context: ProjectContext,
    layout: WorkspaceLayout,
    idempotencyKey: string,
  ): Promise<ApiResult<WorkspaceLayout>>;
};

export type WorkspaceLayoutIdentity = Readonly<{
  subjectArea: string;
  scope: WorkspaceLayout["scope"];
  layoutId: string;
}>;

export function workspaceLayoutCacheKey(
  context: ProjectContext,
  identity: WorkspaceLayoutIdentity,
  principalKey = "",
): string {
  return [
    context.tenant_id,
    context.project_id,
    principalKey,
    identity.scope,
    identity.subjectArea,
    identity.layoutId,
  ].join("::");
}

export class ApiWorkspaceLayoutStore implements WorkspaceLayoutStore {
  private readonly cache = new Map<string, WorkspaceLayout>();

  constructor(
    private readonly transport: ApiTransport,
    private readonly endpoint: string,
    private readonly catalog: readonly P6FieldCatalogEntry[],
  ) {}

  load(key: string): WorkspaceLayout | null {
    return this.cache.get(key) ?? null;
  }

  save(key: string, layout: WorkspaceLayout): void {
    this.cache.set(key, layout);
  }

  async loadFromApi(
    key: string,
    context: ProjectContext,
    subjectArea: string,
    scope: WorkspaceLayout["scope"],
    layoutId: string,
  ): Promise<ApiResult<WorkspaceLayout>> {
    const result = await this.transport.get<unknown>(
      this.endpointForLoad(subjectArea, scope, layoutId),
      context,
    );
    if (!result.ok) return result;

    const serverRevision = extractRevision(result.data);
    if (serverRevision !== null && serverRevision !== context.revision) {
      return {
        ok: false,
        error: {
          code: "WORKSPACE_LAYOUT_REVISION_CONFLICT",
          retryable: false,
          message_key: "workspace.layout.revisionConflict",
          available_actions: ["reload"],
        },
      };
    }

    let layout: WorkspaceLayout;
    try {
      layout = migrateWorkspaceLayout(result.data, this.catalog, context.revision);
    } catch (error) {
      return {
        ok: false,
        error: {
          code: error instanceof Error ? error.message : "INVALID_WORKSPACE_LAYOUT",
          retryable: false,
          message_key: "workspace.layout.invalid",
          available_actions: ["reload"],
        },
      };
    }

    if (
      layout.layout_id !== layoutId ||
      layout.subject_area !== subjectArea ||
      layout.scope !== scope
    ) {
      return {
        ok: false,
        error: {
          code: "WORKSPACE_LAYOUT_IDENTITY_MISMATCH",
          retryable: false,
          message_key: "workspace.layout.identityMismatch",
          available_actions: ["reload"],
        },
      };
    }

    this.cache.set(key, layout);
    return { ok: true, data: layout };
  }

  async saveToApi(
    key: string,
    context: ProjectContext,
    layout: WorkspaceLayout,
    idempotencyKey: string,
  ): Promise<ApiResult<WorkspaceLayout>> {
    if (layout.revision !== context.revision) {
      return {
        ok: false,
        error: {
          code: "STALE_WORKSPACE_LAYOUT_REVISION",
          retryable: false,
          message_key: "workspace.layout.staleRevision",
          available_actions: ["reload"],
        },
      };
    }

    const result = await this.transport.post<WorkspaceLayout, WorkspaceLayout>(
      this.endpoint,
      layout,
      context,
      idempotencyKey,
    );
    if (result.ok) this.cache.set(key, result.data);
    return result;
  }

  private endpointForLoad(
    subjectArea: string,
    scope: WorkspaceLayout["scope"],
    layoutId: string,
  ): string {
    const separator = this.endpoint.includes("?") ? "&" : "?";
    const params = new URLSearchParams({
      subject_area: subjectArea,
      scope,
      layout_id: layoutId,
    });
    return `${this.endpoint}${separator}${params.toString()}`;
  }
}

function extractRevision(value: unknown): number | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  const revision = (value as Record<string, unknown>).revision;
  return typeof revision === "number" && Number.isInteger(revision) && revision >= 0
    ? revision
    : null;
}
