import { validateProjectContext } from "../../../shared/client-contracts/project-context";
import type { ProjectContext } from "../../../shared/client-contracts/project-context";

export type { ProjectContext } from "../../../shared/client-contracts/project-context";

export class ProjectContextStore {
  private context: ProjectContext | null = null;

  set(context: ProjectContext): void {
    validateProjectContext(context);
    this.context = Object.freeze({ ...context });
  }

  get(): ProjectContext {
    if (!this.context) throw new Error("PROJECT_CONTEXT_NOT_SET");
    return this.context;
  }

  updateRevision(revision: number): void {
    const current = this.get();
    validateProjectContext({ ...current, revision });
    this.context = Object.freeze({ ...current, revision });
  }

  clear(): void {
    this.context = null;
  }
}
