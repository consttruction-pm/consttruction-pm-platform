import { ApiRevisionTransport, type VersionedSyncRevisionApi } from "../../client-sync/src/revision-transport.js";
import {
  OfflineMutationQueue,
  type SyncMutation,
  type SyncOutcome,
} from "../../client-sync/src/mutation-queue.js";
import { ClientSyncRunner } from "../../client-sync/src/sync-runner.js";
import { ApiSyncTransport, type VersionedSyncApi } from "../../client-sync/src/api-sync-transport.js";
import { presentSyncConflict, type SyncConflictPresentation } from "../../client-sync/src/conflict-presentation.js";
import { ProjectContextStore, type ProjectContext } from "./project-context.js";

export class WebSyncRuntime {
  private readonly projectContext = new ProjectContextStore();
  private readonly mutationQueue = new OfflineMutationQueue();

  openProject(tenant_id: string, project_id: string, revision: number): ProjectContext {
    this.projectContext.set({ tenant_id, project_id, revision });
    return this.projectContext.get();
  }

  currentProject(): ProjectContext {
    return this.projectContext.get();
  }

  queueMutation(mutation: SyncMutation): void {
    const current = this.currentProject();
    if (mutation.tenant_id !== current.tenant_id || mutation.project_id !== current.project_id) {
      throw new Error("PROJECT_CONTEXT_MISMATCH");
    }
    this.mutationQueue.enqueue(mutation);
  }

  pendingMutationCount(): number {
    return this.mutationQueue.size();
  }

  private syncRunner(): ClientSyncRunner {
    return new ClientSyncRunner(this.mutationQueue, {
      submit: (mutation) => {
        throw new Error("SYNC_SUBMIT_NOT_CONFIGURED");
      },
    });
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

  async refreshRevision(api: VersionedSyncRevisionApi): Promise<number> {
    const current = this.currentProject();
    const result = await new ApiRevisionTransport(api).refresh(current);
    this.projectContext.updateRevision(result.revision);
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
    const current = this.currentProject();
    const mutation = this.mutationQueue.pending().find((item) => item.mutation_id === mutationId);
    if (!mutation) throw new Error("MUTATION_NOT_PENDING");
    if (mutation.tenant_id !== current.tenant_id || mutation.project_id !== current.project_id) {
      throw new Error("PROJECT_CONTEXT_MISMATCH");
    }
    const revision = await this.syncRunner().refreshConflictRevision(
      mutationId,
      new ApiRevisionTransport(revisionApi),
    );
    this.projectContext.updateRevision(revision.revision);
    return this.mutationQueue.retryAtRevision(mutationId, revision.revision);
  }
}
