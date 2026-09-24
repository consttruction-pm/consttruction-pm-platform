import {
  OfflineMutationQueue,
  type SyncMutation,
} from "../../client-sync/src/mutation-queue.js";
import { validateProjectContext } from "../../../shared/client-contracts/project-context";
import type { ProjectContext } from "../../../shared/client-contracts/project-context";

export type { ProjectContext } from "../../../shared/client-contracts/project-context";
export type OfflineMode = "offline" | "online";

export type DesktopProjectState = ProjectContext & { mode: OfflineMode };

export class DesktopRuntime {
  private state: DesktopProjectState | null = null;
  private readonly mutationQueue = new OfflineMutationQueue();

  openProject(
    tenant_id: string,
    project_id: string,
    revision: number,
    mode: OfflineMode = "offline",
  ): DesktopProjectState {
    const context: ProjectContext = { tenant_id, project_id, revision };
    validateProjectContext(context);
    this.state = Object.freeze({ ...context, mode });
    return this.state;
  }

  current(): DesktopProjectState {
    if (!this.state) throw new Error("PROJECT_NOT_OPEN");
    return this.state;
  }

  setMode(mode: OfflineMode): DesktopProjectState {
    const current = this.current();
    this.state = Object.freeze({ ...current, mode });
    return this.state;
  }

  advanceRevision(revision: number): DesktopProjectState {
    const current = this.current();
    if (revision < current.revision) {
      throw new Error("REVISION_REGRESSION");
    }
    validateProjectContext({ ...current, revision });
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