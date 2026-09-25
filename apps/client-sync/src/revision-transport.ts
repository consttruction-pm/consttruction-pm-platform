import type { SyncProjectContext, SyncApiResult } from "./api-sync-transport.js";

export type SyncProjectRevision = {
  contract_version: "sync-project-revision.v1";
  tenant_id: string;
  project_id: string;
  revision: number;
};

function isValidRevision(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
}

export interface VersionedSyncRevisionApi {
  get<TResponse>(
    path: string,
    context: SyncProjectContext,
  ): Promise<SyncApiResult<TResponse>>;
}

export class ApiRevisionTransport {
  private readonly api: VersionedSyncRevisionApi;
  private readonly path: string;

  constructor(api: VersionedSyncRevisionApi, path = "/api/v1/sync/revision") {
    this.api = api;
    this.path = path;
  }

  async refresh(context: SyncProjectContext): Promise<SyncProjectRevision> {
    const result = await this.api.get<SyncProjectRevision>(this.path, context);
    if (!result.ok) {
      throw new Error(result.error.code);
    }

    const revision = result.data;
    if (
      revision.contract_version !== "sync-project-revision.v1" ||
      revision.tenant_id !== context.tenant_id ||
      revision.project_id !== context.project_id ||
      !isValidRevision(revision.revision)
    ) {
      throw new Error("INVALID_PROJECT_REVISION_RESPONSE");
    }

    return revision;
  }
}
