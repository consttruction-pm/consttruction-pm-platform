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
}
