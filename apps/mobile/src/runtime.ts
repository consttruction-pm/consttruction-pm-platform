import {
  OfflineMutationQueue,
  type SyncMutation,
} from "../../client-sync/src/mutation-queue.js";

export type MobileMode = "offline" | "online";

export type MobileProjectState = {
  tenant_id: string;
  project_id: string;
  revision: number;
  mode: MobileMode;
};

export class MobileRuntime {
  private state: MobileProjectState | null = null;
  private readonly mutationQueue = new OfflineMutationQueue();

  openProject(
    tenant_id: string,
    project_id: string,
    revision: number,
    mode: MobileMode = "offline",
  ): MobileProjectState {
    if (!tenant_id || !project_id || revision < 0) {
      throw new Error("INVALID_PROJECT_CONTEXT");
    }
    this.state = Object.freeze({ tenant_id, project_id, revision, mode });
    return this.state;
  }

  current(): MobileProjectState {
    if (!this.state) throw new Error("PROJECT_NOT_OPEN");
    return this.state;
  }

  setMode(mode: MobileMode): MobileProjectState {
    const current = this.current();
    this.state = Object.freeze({ ...current, mode });
    return this.state;
  }

  advanceRevision(revision: number): MobileProjectState {
    const current = this.current();
    if (revision < current.revision) {
      throw new Error("REVISION_REGRESSION");
    }
    this.state = Object.freeze({ ...current, revision });
    return this.state;
  }

  queueMutation(mutation: SyncMutation): void {
    const current = this.current();
    if (
      mutation.tenant_id !== current.tenant_id ||
      mutation.project_id !== current.project_id
    ) {
      throw new Error("PROJECT_CONTEXT_MISMATCH");
    }
    this.mutationQueue.enqueue(mutation);
  }

  pendingMutationCount(): number {
    return this.mutationQueue.size();
  }

  acknowledgeMutation(mutationId: string): void {
    this.mutationQueue.acknowledge(mutationId);
  }
}
