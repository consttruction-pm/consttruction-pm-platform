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

  retryStaleRevision(
    mutationId: string,
    outcome: SyncOutcome,
    refreshedRevision: number,
  ): SyncMutation {
    if (outcome.mutation_id !== mutationId || outcome.disposition !== "conflict" || outcome.error_code !== "STALE_REVISION") {
      throw new Error("INVALID_STALE_REVISION_RETRY");
    }
    return this.mutationQueue.retryAtRevision(mutationId, refreshedRevision);
  }
}
