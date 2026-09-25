import { ClientLanguageRuntime } from "../../client-sync/src/language-runtime.ts";
import { ApiRevisionTransport, type VersionedSyncRevisionApi } from "../../client-sync/src/revision-transport.js";
import {
  OfflineMutationQueue,
  type SyncMutation,
  type SyncOutcome,
} from "../../client-sync/src/mutation-queue.js";
import { ClientSyncRunner } from "../../client-sync/src/sync-runner.js";
import { ApiSyncTransport, type VersionedSyncApi } from "../../client-sync/src/api-sync-transport.js";
import { presentSyncConflict, type SyncConflictPresentation } from "../../client-sync/src/conflict-presentation.js";

export class WebSyncRuntime {
  private readonly languageRuntime = new ClientLanguageRuntime();
  private readonly mutationQueue = new OfflineMutationQueue();

  queueMutation(mutation: SyncMutation): void {
    this.mutationQueue.enqueue(mutation);
  }

  pendingMutationCount(): number {
    return this.mutationQueue.size();
  }

  async syncOnce(api: VersionedSyncApi): Promise<readonly SyncOutcome[]> {
    return new ClientSyncRunner(
      this.mutationQueue,
      new ApiSyncTransport(api),
    ).runOnce();
  }

  presentConflict(
    mutation: SyncMutation,
    outcome: SyncOutcome,
  ): SyncConflictPresentation | null {
    return presentSyncConflict(mutation, outcome);
  }

  async refreshRevision(api: VersionedSyncRevisionApi, tenant_id: string, project_id: string, revision: number): Promise<number> {
    const result = await new ApiRevisionTransport(api).refresh({ tenant_id, project_id, revision });
    return result.revision;
  }

  async retryStaleRevision(
    mutationId: string,
    outcome: SyncOutcome,
    revisionApi: VersionedSyncRevisionApi,
  ): Promise<SyncMutation> {
    if (outcome.mutation_id !== mutationId || outcome.disposition !== "conflict" || outcome.error_code !== "STALE_REVISION") {
      throw new Error("INVALID_STALE_REVISION_RETRY");
    }
    const mutation = this.mutationQueue.pending().find((item) => item.mutation_id === mutationId);
    if (!mutation) throw new Error("MUTATION_NOT_PENDING");
    const revision = await new ApiRevisionTransport(revisionApi).refresh({
      tenant_id: mutation.tenant_id,
      project_id: mutation.project_id,
      revision: mutation.expected_revision,
    });
    return this.mutationQueue.retryAtRevision(mutationId, revision.revision);
  }

  configureLanguage(
    registry: Parameters<ClientLanguageRuntime["configure"]>[0],
    defaultLanguage: string,
    preference: Parameters<ClientLanguageRuntime["configure"]>[2],
  ) {
    return this.languageRuntime.configure(registry, defaultLanguage, preference);
  }

  currentLanguage() {
    return this.languageRuntime.current();
  }

  setPreferredLanguage(languageTag: string) {
    return this.languageRuntime.setPreferredLanguage(languageTag);
  }

  canUseLanguageOffline(languageTag: string): boolean {
    return this.languageRuntime.canRunOffline(languageTag);
  }

}
