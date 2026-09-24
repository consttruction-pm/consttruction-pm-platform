import { ApiRevisionTransport, type VersionedSyncRevisionApi } from "../../client-sync/src/revision-transport.js";
import {
  OfflineMutationQueue,
  type SyncMutation,
  type SyncOutcome,
} from "../../client-sync/src/mutation-queue.js";
import { ClientSyncRunner } from "../../client-sync/src/sync-runner.js";
import { ApiSyncTransport, type VersionedSyncApi } from "../../client-sync/src/api-sync-transport.js";
import { presentSyncConflict, type SyncConflictPresentation } from "../../client-sync/src/conflict-presentation.js";

export type OfflineMode = "offline" | "online";
export type DesktopProjectState = { tenant_id: string; project_id: string; revision: number; mode: OfflineMode };

export class DesktopRuntime {
  private state: DesktopProjectState | null = null;
  private readonly mutationQueue = new OfflineMutationQueue();
  openProject(tenant_id: string, project_id: string, revision: number, mode: OfflineMode = "offline"): DesktopProjectState {
    if (!tenant_id || !project_id || revision < 0) throw new Error("INVALID_PROJECT_CONTEXT");
    this.state = Object.freeze({ tenant_id, project_id, revision, mode }); return this.state;
  }
  current(): DesktopProjectState { if (!this.state) throw new Error("PROJECT_NOT_OPEN"); return this.state; }
  setMode(mode: OfflineMode): DesktopProjectState { const current = this.current(); this.state = Object.freeze({ ...current, mode }); return this.state; }
  advanceRevision(revision: number): DesktopProjectState { const current = this.current(); if (revision < current.revision) throw new Error("REVISION_REGRESSION"); this.state = Object.freeze({ ...current, revision }); return this.state; }
  queueMutation(mutation: SyncMutation): void { const current = this.current(); if (mutation.tenant_id !== current.tenant_id || mutation.project_id !== current.project_id) throw new Error("PROJECT_CONTEXT_MISMATCH"); this.mutationQueue.enqueue(mutation); }
  pendingMutationCount(): number { return this.mutationQueue.size(); }
  acknowledgeMutation(mutationId: string): void { this.mutationQueue.acknowledge(mutationId); }
  async syncOnce(api: VersionedSyncApi): Promise<readonly SyncOutcome[]> { return new ClientSyncRunner(this.mutationQueue, new ApiSyncTransport(api)).runOnce(); }
  presentConflict(mutation: SyncMutation, outcome: SyncOutcome): SyncConflictPresentation | null { return presentSyncConflict(mutation, outcome); }
  async refreshRevision(api: VersionedSyncRevisionApi): Promise<DesktopProjectState> {
    const current = this.current();
    const result = await new ApiRevisionTransport(api).refresh({
      tenant_id: current.tenant_id,
      project_id: current.project_id,
      revision: current.revision,
    });
    return this.advanceRevision(result.revision);
  }

  retryStaleRevision(mutationId: string, outcome: SyncOutcome, refreshedRevision: number): SyncMutation {
    if (outcome.mutation_id !== mutationId || outcome.disposition !== "conflict" || outcome.error_code !== "STALE_REVISION") {
      throw new Error("INVALID_STALE_REVISION_RETRY");
    }
    const current = this.current();
    if (refreshedRevision < current.revision) throw new Error("REVISION_REGRESSION");
    const mutation = this.mutationQueue.retryAtRevision(mutationId, refreshedRevision);
    this.advanceRevision(refreshedRevision);
    return mutation;
  }
}
