import type { MobileRuntime, MobileProjectState } from "./runtime.ts";
import type {
  MobileSchedulingRequest,
  MobileSchedulingResult,
  SchedulingDuration,
  SharedSchedulingCoreAdapter,
} from "./shared-scheduling-adapter.ts";

export type MobileShellScreen = "projects" | "wbs" | "activity";

export type MobileWbsNode = Readonly<{
  id: string;
  code: string;
  name: string;
  parent_id: string | null;
  order: number;
}>;

export type MobileActivity = Readonly<{
  id: string;
  wbs_id: string;
  name: string;
  order: number;
}>;

export type MobileLocalProject = Readonly<{
  tenant_id: string;
  project_id: string;
  revision: number;
  name: string;
  wbs: readonly MobileWbsNode[];
  activities: readonly MobileActivity[];
}>;

export type MobileShellState = Readonly<{
  screen: MobileShellScreen;
  project: MobileProjectState | null;
  selected_wbs_id: string | null;
  selected_activity_id: string | null;
  schedule_result: MobileSchedulingResult | null;
}>;

export interface MobileLocalProjectStore {
  load(tenantId: string, projectId: string): Promise<MobileLocalProject | null>;
}

export class InMemoryMobileLocalProjectStore implements MobileLocalProjectStore {
  private readonly projects = new Map<string, MobileLocalProject>();

  constructor(projects: readonly MobileLocalProject[] = []) {
    for (const project of projects) {
      this.projects.set(this.key(project.tenant_id, project.project_id), project);
    }
  }

  async load(tenantId: string, projectId: string): Promise<MobileLocalProject | null> {
    return this.projects.get(this.key(tenantId, projectId)) ?? null;
  }

  private key(tenantId: string, projectId: string): string {
    return `${tenantId}:${projectId}`;
  }
}

/**
 * Framework-neutral local/native navigation seam for the first Mobile V1 slice.
 *
 * It owns presentation state only. Project scheduling, CPM, calendar, float,
 * progress and other business calculations stay outside this shell.
 */
export class MobileProjectShell {
  private localProject: MobileLocalProject | null = null;
  private state: MobileShellState = Object.freeze({
    screen: "projects",
    project: null,
    selected_wbs_id: null,
    selected_activity_id: null,
    schedule_result: null,
  });

  constructor(
    private readonly runtime: MobileRuntime,
    private readonly store: MobileLocalProjectStore,
  ) {}

  current(): MobileShellState {
    return this.state;
  }

  async openLocalProject(tenantId: string, projectId: string): Promise<MobileShellState> {
    const project = await this.store.load(tenantId, projectId);
    if (!project) throw new Error("LOCAL_PROJECT_NOT_FOUND");

    if (
      project.tenant_id !== tenantId ||
      project.project_id !== projectId ||
      project.revision < 0
    ) {
      throw new Error("INVALID_LOCAL_PROJECT_CONTEXT");
    }

    const runtimeState = this.runtime.openProject(
      project.tenant_id,
      project.project_id,
      project.revision,
      "offline",
    );

    this.localProject = project;
    this.state = Object.freeze({
      screen: "wbs",
      project: runtimeState,
      selected_wbs_id: null,
      selected_activity_id: null,
      schedule_result: null,
    });
    return this.state;
  }

  showProjects(): MobileShellState {
    this.state = Object.freeze({
      screen: "projects",
      project: this.state.project,
      selected_wbs_id: null,
      selected_activity_id: null,
      schedule_result: this.state.schedule_result,
    });
    return this.state;
  }

  showWbs(): MobileShellState {
    this.requireProject();
    this.state = Object.freeze({
      ...this.state,
      screen: "wbs",
      selected_activity_id: null,
    });
    return this.state;
  }

  showActivity(wbsId: string, activityId: string): MobileShellState {
    const project = this.requireProjectData();
    const wbs = project.wbs.find((item) => item.id === wbsId);
    if (!wbs) throw new Error("WBS_NOT_FOUND");

    const activity = project.activities.find(
      (item) => item.id === activityId && item.wbs_id === wbsId,
    );
    if (!activity) throw new Error("ACTIVITY_NOT_FOUND");

    this.state = Object.freeze({
      ...this.state,
      screen: "activity",
      selected_wbs_id: wbs.id,
      selected_activity_id: activity.id,
    });
    return this.state;
  }

  async schedule(
    core: SharedSchedulingCoreAdapter,
    input: MobileSchedulingRequest,
  ): Promise<MobileSchedulingResult> {
    this.requireProject();
    const result = await this.runtime.scheduleOffline(core, input);
    this.state = Object.freeze({
      ...this.state,
      schedule_result: result,
    });
    return result;
  }

  listWbs(): readonly MobileWbsNode[] {
    const project = this.requireProjectData();
    return [...project.wbs].sort((a, b) => a.order - b.order || a.id.localeCompare(b.id));
  }

  listRelationships(activityId: string): readonly MobileActivityRelationship[] {\n    const project = this.requireProjectData();\n    const activity = project.activities.find((item) => item.id === activityId);\n    if (!activity) throw new Error("ACTIVITY_NOT_FOUND");\n    return project.relationships\n      .filter((relationship) => relationship.predecessor_id === activityId || relationship.successor_id === activityId);\n  }\n\n  listActivities(wbsId: string): readonly MobileActivity[] {
    const project = this.requireProjectData();
    if (!project.wbs.some((item) => item.id === wbsId)) throw new Error("WBS_NOT_FOUND");
    return project.activities
      .filter((item) => item.wbs_id === wbsId)
      .sort((a, b) => a.order - b.order || a.id.localeCompare(b.id));
  }

  private requireProject(): MobileProjectState {
    if (!this.state.project) throw new Error("PROJECT_NOT_OPEN");
    return this.state.project;
  }

  private requireProjectData(): MobileLocalProject {
    this.requireProject();
    if (!this.localProject) throw new Error("PROJECT_NOT_OPEN");
    return this.localProject;
  }
}
