import type { ProjectContext } from "./client.js";

export type { ProjectContext };

export class ProjectContextStore {
  private context: ProjectContext | null = null;

  set(context: ProjectContext): void {
    if (!context.tenant_id || !context.project_id || !Number.isInteger(context.revision) || context.revision < 0) {
      throw new Error("INVALID_PROJECT_CONTEXT");
    }
    this.context = Object.freeze({ ...context });
  }

  get(): ProjectContext {
    if (!this.context) throw new Error("PROJECT_CONTEXT_NOT_SET");
    return this.context;
  }

  updateRevision(revision: number): void {
    if (!Number.isInteger(revision) || revision < 0) throw new Error("INVALID_PROJECT_REVISION");
    const current = this.get();
    if (revision < current.revision) throw new Error("REVISION_REGRESSION");
    this.set({ ...current, revision });
  }

  clear(): void {
    this.context = null;
  }
}
