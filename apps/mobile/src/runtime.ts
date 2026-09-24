import { validateProjectContext } from "../../../shared/client-contracts/project-context";
import type { ProjectContext } from "../../../shared/client-contracts/project-context";

export type { ProjectContext } from "../../../shared/client-contracts/project-context";
export type MobileMode = "offline" | "online";

export type MobileProjectState = ProjectContext & { mode: MobileMode };

export class MobileRuntime {
  private state: MobileProjectState | null = null;

  openProject(tenant_id: string, project_id: string, revision: number, mode: MobileMode = "offline"): MobileProjectState {
    const context: ProjectContext = { tenant_id, project_id, revision };
    validateProjectContext(context);
    this.state = Object.freeze({ ...context, mode });
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
    if (revision < current.revision) throw new Error("REVISION_REGRESSION");
    validateProjectContext({ ...current, revision });
    this.state = Object.freeze({ ...current, revision });
    return this.state;
  }
}
