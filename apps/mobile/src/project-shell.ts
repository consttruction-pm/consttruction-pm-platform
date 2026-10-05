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

export type MobileActivityRelationship = Readonly<{
  predecessor_id: string;
  successor_id: string;
  type: "FS" | "SS" | "FF" | "SF";
  lag: SchedulingDuration;
}>;

export type MobileLocalProject = Readonly<{
  tenant_id: string;
  project_id: string;
  revision: number;
  name: string;
  wbs: readonly MobileWbsNode[];
  activities: readonly MobileActivity[];
  relationships: readonly MobileActivityRelationship[];
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
  save(project: MobileLocalProject): Promise<void>;
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

  async save(project: MobileLocalProject): Promise<void> {
    this.projects.set(this.key(project.tenant_id, project.project_id), project);
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

  async addWbsNode(input: Omit<MobileWbsNode, "order"> & { order?: number }): Promise<MobileShellState> {
    const project = this.requireProjectData();
    if (!input.id.trim() || !input.code.trim() || !input.name.trim()) throw new Error("INVALID_WBS");
    if (project.wbs.some((item) => item.id === input.id)) throw new Error("WBS_ALREADY_EXISTS");
    if (input.parent_id !== null && !project.wbs.some((item) => item.id === input.parent_id)) {
      throw new Error("WBS_PARENT_NOT_FOUND");
    }
    const order = input.order ?? (project.wbs.reduce((max, item) => Math.max(max, item.order), 0) + 1);
    if (!Number.isInteger(order) || order < 0) throw new Error("INVALID_WBS_ORDER");
    const nextRevision = project.revision + 1;
    const updated = Object.freeze({
      ...project,
      revision: nextRevision,
      wbs: Object.freeze([...project.wbs, Object.freeze({ ...input, order })]),
    });
    await this.store.save(updated);
    this.localProject = updated;
    const runtimeState = this.runtime.advanceRevision(nextRevision);
    this.state = Object.freeze({ ...this.state, project: runtimeState, schedule_result: null });
    return this.state;
  }

  async updateWbsNode(
    wbsId: string,
    patch: Partial<Pick<MobileWbsNode, "code" | "name" | "parent_id">>,
  ): Promise<MobileShellState> {
    const project = this.requireProjectData();
    const current = project.wbs.find((item) => item.id === wbsId);
    if (!current) throw new Error("WBS_NOT_FOUND");
    const nextParent = "parent_id" in patch ? patch.parent_id ?? null : current.parent_id;
    if (nextParent !== null && !project.wbs.some((item) => item.id === nextParent)) {
      throw new Error("WBS_PARENT_NOT_FOUND");
    }
    const seen = new Set<string>();
    let ancestor = nextParent;
    while (ancestor !== null) {
      if (ancestor === wbsId || seen.has(ancestor)) throw new Error("WBS_PARENT_CYCLE");
      seen.add(ancestor);
      ancestor = project.wbs.find((item) => item.id === ancestor)?.parent_id ?? null;
    }
    const code = patch.code ?? current.code;
    const name = patch.name ?? current.name;
    if (!code.trim() || !name.trim()) throw new Error("INVALID_WBS");
    const nextRevision = project.revision + 1;
    const updated = Object.freeze({
      ...project,
      revision: nextRevision,
      wbs: Object.freeze(project.wbs.map((item) => item.id === wbsId ? Object.freeze({ ...item, code, name, parent_id: nextParent }) : item)),
    });
    await this.store.save(updated);
    this.localProject = updated;
    const runtimeState = this.runtime.advanceRevision(nextRevision);
    this.state = Object.freeze({ ...this.state, project: runtimeState, schedule_result: null });
    return this.state;
  }

  async addActivity(
    input: Omit<MobileActivity, "order"> & { order?: number },
  ): Promise<MobileShellState> {
    const project = this.requireProjectData();
    if (!input.id.trim() || !input.name.trim()) throw new Error("INVALID_ACTIVITY");
    if (project.activities.some((item) => item.id === input.id)) throw new Error("ACTIVITY_ALREADY_EXISTS");
    if (!project.wbs.some((item) => item.id === input.wbs_id)) throw new Error("WBS_NOT_FOUND");
    const order = input.order ?? (project.activities.filter((item) => item.wbs_id === input.wbs_id).reduce((max, item) => Math.max(max, item.order), 0) + 1);
    if (!Number.isInteger(order) || order < 0) throw new Error("INVALID_ACTIVITY_ORDER");
    const nextRevision = project.revision + 1;
    const updated = Object.freeze({
      ...project,
      revision: nextRevision,
      activities: Object.freeze([...project.activities, Object.freeze({ ...input, order })]),
    });
    await this.store.save(updated);
    this.localProject = updated;
    const runtimeState = this.runtime.advanceRevision(nextRevision);
    this.state = Object.freeze({ ...this.state, project: runtimeState, schedule_result: null });
    return this.state;
  }

  async updateActivity(
    activityId: string,
    patch: Partial<Pick<MobileActivity, "wbs_id" | "name">>,
  ): Promise<MobileShellState> {
    const project = this.requireProjectData();
    const current = project.activities.find((item) => item.id === activityId);
    if (!current) throw new Error("ACTIVITY_NOT_FOUND");
    const wbsId = patch.wbs_id ?? current.wbs_id;
    const name = patch.name ?? current.name;
    if (!name.trim()) throw new Error("INVALID_ACTIVITY");
    if (!project.wbs.some((item) => item.id === wbsId)) throw new Error("WBS_NOT_FOUND");
    const nextOrder = wbsId === current.wbs_id
      ? current.order
      : project.activities
          .filter((item) => item.wbs_id === wbsId && item.id !== activityId)
          .reduce((max, item) => Math.max(max, item.order), 0) + 1;
    const nextRevision = project.revision + 1;
    const updated = Object.freeze({
      ...project,
      revision: nextRevision,
      activities: Object.freeze(project.activities.map((item) => item.id === activityId
        ? Object.freeze({ ...item, wbs_id: wbsId, name, order: nextOrder })
        : item)),
    });
    await this.store.save(updated);
    this.localProject = updated;
    const runtimeState = this.runtime.advanceRevision(nextRevision);
    this.state = Object.freeze({ ...this.state, project: runtimeState, schedule_result: null });
    return this.state;
  }

  listRelationships(activityId: string): readonly MobileActivityRelationship[] {
    const project = this.requireProjectData();
    const activity = project.activities.find((item) => item.id === activityId);
    if (!activity) throw new Error("ACTIVITY_NOT_FOUND");
    return project.relationships.filter(
      (relationship) =>
        relationship.predecessor_id === activityId || relationship.successor_id === activityId,
    );
  }

  listActivities(wbsId: string): readonly MobileActivity[] {
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
