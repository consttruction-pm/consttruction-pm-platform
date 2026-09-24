import type { ProjectContext } from "./client.js";

export type { ProjectContext };

export class ProjectContextStore {
  private context: ProjectContext | null = null;

  set(context: ProjectContext): void {
    if (!context.tenant_id || !context.project_id || context.revision < 0) {
      throw new Error("INVALID_PROJECT_CONTEXT");
    }
    this.context = Object.freeze({ ...context });
  }

  get(): ProjectContext {
    if (!this.context) throw new Error("PROJECT_CONTEXT_NOT_SET");
    return this.context;
  }

  updateRevision(revision: number): void {
    if (revision < 0) throw new Error("INVALID_PROJECT_REVISION");
    const current = this.get();
    this.set({ ...current, revision });
  }

  clear(): void {
    this.context = null;
  }
}
