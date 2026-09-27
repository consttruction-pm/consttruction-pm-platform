import { ApiRevisionTransport, type VersionedSyncRevisionApi } from "../../client-sync/src/revision-transport.ts";
import {
  OfflineMutationQueue,
  type SyncMutation,
  type SyncOutcome,
} from "../../client-sync/src/mutation-queue.js";
import { ClientSyncRunner } from "../../client-sync/src/sync-runner.js";
import { ApiSyncTransport, type VersionedSyncApi } from "../../client-sync/src/api-sync-transport.js";
import { presentSyncConflict, type SyncConflictPresentation } from "../../client-sync/src/conflict-presentation.js";
import { WorkspaceReadCacheAdapter, type WorkspaceReadResult } from "../../client-sync/src/workspace-read-cache-adapter.js";

export type MobileMode = "offline" | "online";
export type MobileProjectState = { tenant_id: string; project_id: string; revision: number; mode: MobileMode };

export class MobileRuntime {
  private state: MobileProjectState | null = null;
  private readonly mutationQueue = new OfflineMutationQueue();
  openProject(tenant_id: string, project_id: string, revision: number, mode: MobileMode = "offline"): MobileProjectState {
    if (!tenant_id || !project_id || revision < 0) throw new Error("INVALID_PROJECT_CONTEXT");
    this.state = Object.freeze({ tenant_id, project_id, revision, mode }); return this.state;
  }
  current(): MobileProjectState { if (!this.state) throw new Error("PROJECT_NOT_OPEN"); return this.state; }
  setMode(mode: MobileMode): MobileProjectState { const current = this.current(); this.state = Object.freeze({ ...current, mode }); return this.state; }
  advanceRevision(revision: number): MobileProjectState { const current = this.current(); if (revision < current.revision) throw new Error("REVISION_REGRESSION"); this.state = Object.freeze({ ...current, revision }); return this.state; }
  queueMutation(mutation: SyncMutation): void { const current = this.current(); if (mutation.tenant_id !== current.tenant_id || mutation.project_id !== current.project_id) throw new Error("PROJECT_CONTEXT_MISMATCH"); this.mutationQueue.enqueue(mutation); }
  pendingMutationCount(): number { return this.mutationQueue.size(); }
  acknowledgeMutation(mutationId: string): void { this.mutationQueue.acknowledge(mutationId); }
  async syncOnce(api: VersionedSyncApi): Promise<readonly SyncOutcome[]> { return new ClientSyncRunner(this.mutationQueue, new ApiSyncTransport(api)).runOnce(); }
  async readWorkspace(adapter: WorkspaceReadCacheAdapter): Promise<WorkspaceReadResult> {
    const current = this.current();
    return adapter.read(
      { tenant_id: current.tenant_id, project_id: current.project_id, revision: current.revision },
      current.mode === "online",
    );
  }
  presentConflict(mutation: SyncMutation, outcome: SyncOutcome): SyncConflictPresentation | null { return presentSyncConflict(mutation, outcome); }
  async refreshRevision(api: VersionedSyncRevisionApi): Promise<MobileProjectState> {
    const current = this.current();
    const result = await new ApiRevisionTransport(api).refresh({
      tenant_id: current.tenant_id,
      project_id: current.project_id,
      revision: current.revision,
    });
    return this.advanceRevision(result.revision);
  }

  async retryStaleRevision(mutationId: string, outcome: SyncOutcome, revisionApi: VersionedSyncRevisionApi): Promise<SyncMutation> {
    if (outcome.mutation_id !== mutationId || outcome.disposition !== "conflict" || outcome.error_code !== "STALE_REVISION") {
      throw new Error("INVALID_STALE_REVISION_RETRY");
    }
    const current = this.current();
    const mutation = this.mutationQueue.pending().find((item) => item.mutation_id === mutationId);
    if (!mutation) throw new Error("MUTATION_NOT_PENDING");
    const revision = await new ClientSyncRunner(this.mutationQueue).refreshConflictRevision(
      mutationId,
      new ApiRevisionTransport(revisionApi),
    );
    if (revision.revision < current.revision) throw new Error("REVISION_REGRESSION");
    const retried = this.mutationQueue.retryAtRevision(mutationId, revision.revision);
    this.advanceRevision(revision.revision);
    return retried;
  }
}
