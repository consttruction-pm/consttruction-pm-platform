import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";
import { migrateWorkspaceLayout, type WorkspaceLayout, type WorkspaceLayoutStore } from "./workspace-layout.js";
import type { P6FieldCatalogEntry } from "./p6-field-registry-client.js";

export type WorkspaceLayoutPersistence = {
  loadLayout(context: ProjectContext, subjectArea: string, scope: WorkspaceLayout["scope"], layoutId: string): Promise<ApiResult<unknown>>;
  saveLayout(context: ProjectContext, layout: WorkspaceLayout, idempotencyKey: string): Promise<ApiResult<WorkspaceLayout>>;
};

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
      this.endpointFor("load"),
      context,
    );
    if (!result.ok) return result;

    const layout = migrateWorkspaceLayout(result.data, this.catalog, context.revision);
    if (layout.layout_id !== layoutId || layout.subject_area !== subjectArea || layout.scope !== scope) {
      return { ok: false, error: { code: "WORKSPACE_LAYOUT_IDENTITY_MISMATCH", retryable: false, message_key: "workspace.layout.identityMismatch", available_actions: ["reload"] } };
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
      return { ok: false, error: { code: "STALE_WORKSPACE_LAYOUT_REVISION", retryable: false, message_key: "workspace.layout.staleRevision", available_actions: ["reload"] } };
    }
    const result = await this.transport.post<WorkspaceLayout, WorkspaceLayout>(
      this.endpointFor("save"),
      layout,
      context,
      idempotencyKey,
    );
    if (result.ok) this.cache.set(key, result.data);
    return result;
  }

  private endpointFor(operation: "load" | "save"): string {
    return operation === "load" ? this.endpoint : this.endpoint;
  }
}
