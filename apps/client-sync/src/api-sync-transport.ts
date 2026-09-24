import type { SyncMutation, SyncOutcome } from "./mutation-queue.ts";

export type SyncProjectContext = {
  tenant_id: string;
  project_id: string;
  revision: number;
};

export type SyncApiError = {
  code: string;
  retryable: boolean;
};

export type SyncApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: SyncApiError };

export interface VersionedSyncApi {
  post<TRequest, TResponse>(
    path: string,
    request: TRequest,
    context: SyncProjectContext,
    idempotencyKey: string,
  ): Promise<SyncApiResult<TResponse>>;
}

export class ApiSyncTransport {
  private readonly api: VersionedSyncApi;
  private readonly path: string;

  constructor(api: VersionedSyncApi, path = "/api/v1/sync/mutations") {
    this.api = api;
    this.path = path;
  }

  async submit(mutation: SyncMutation): Promise<SyncOutcome> {
    const result = await this.api.post<SyncMutation, SyncOutcome>(
      this.path,
      mutation,
      {
        tenant_id: mutation.tenant_id,
        project_id: mutation.project_id,
        revision: mutation.expected_revision,
      },
      mutation.idempotency_key,
    );

    if (result.ok) {
      if (result.data.mutation_id !== mutation.mutation_id) {
        throw new Error("MUTATION_ID_MISMATCH");
      }
      return result.data;
    }

    return {
      contract_version: "sync-outcome.v1",
      mutation_id: mutation.mutation_id,
      disposition: result.error.retryable ? "retry" : "rejected",
      error_code: result.error.code,
    };
  }
}
