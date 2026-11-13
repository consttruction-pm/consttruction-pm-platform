import type { ApiResult, ClientError, ProjectContext } from "./client.js";
import type { ProjectContext as SessionProjectContext, ProjectStatus, ProjectStatusEvent, ProjectSummary, SessionApi } from "./session-api.js";
import { toWorkspaceContext } from "./session-api.js";
import type { WebSyncRuntime } from "./sync-runtime.js";
import type { WorkspaceLocale, WorkspaceState } from "./workspace-model.js";
import type { WorkspaceReadClient } from "./workspace-read-api.js";
import type { loadP6Presentation } from "./p6-api.js";
import {
  closeProjectTab,
  normalizeProjectTabs,
  openProjectTab,
  type ProjectTabState,
} from "./workspace-project-tabs.js";

export type ProjectBootstrapState =
  | { status: "loading" }
  /**
   * The signed-in user has no project membership yet. This is a first-run
   * state, not an error: the bootstrap must lead to a real creation form
   * instead of a dead end that only offers a retry.
   */
  | { status: "empty" }
  | { status: "selecting"; projects: readonly ProjectSummary[] }
  | { status: "opening"; projectId: string }
  | { status: "creating"; projectId: string }
  | { status: "ready"; context: ProjectContext; workspace: WorkspaceState; userId: string; roles: readonly string[] }
  | { status: "error"; error: ClientError };

export type ProjectBootstrapDependencies = {
  sessionApi: SessionApi;
  syncRuntime: WebSyncRuntime;
  workspaceReadClient: WorkspaceReadClient;
  p6PresentationLoader?: (state: WorkspaceState, context: ProjectContext) => ReturnType<typeof loadP6Presentation>;
  /** Per-user project preference. The list from the server still decides access. */
  preferredProjectIdForUser?: (userId: string) => string | null;
  /** Browser-local open project tabs for this user; re-validated against the session list. */
  projectTabsForUser?: (userId: string) => ProjectTabState | null;
  rememberProjectTabsForUser?: (userId: string, state: ProjectTabState) => void;
};

function localError(code: string, messageKey: string, actions: string[] = []): ClientError {
  return {
    code,
    retryable: false,
    message_key: messageKey,
    available_actions: actions,
  };
}

function loaderError(error: unknown): ClientError {
  if (error instanceof Error && error.message === "NETWORK_ERROR") {
    return {
      code: "NETWORK_ERROR",
      retryable: true,
      message_key: "error.network",
      available_actions: ["retry"],
    };
  }
  return {
    code: "P6_PRESENTATION_LOAD_FAILED",
    retryable: false,
    message_key: "error.p6.presentation.invalid",
    available_actions: ["refresh"],
  };
}

export class ProjectBootstrap {
  private generation = 0;
  private projects: readonly ProjectSummary[] = [];
  private roles: readonly string[] = [];
  private userId = "";
  private tabs: ProjectTabState = { open: [], active: "" };

  constructor(private readonly dependencies: ProjectBootstrapDependencies) {}

  async start(
    preferredProjectId: string | null = null,
    locale: WorkspaceLocale = "en",
  ): Promise<ProjectBootstrapState | null> {
    const generation = ++this.generation;

    const session = await this.dependencies.sessionApi.getSession();
    if (!this.isCurrent(generation)) return null;
    if (!session.ok) return { status: "error", error: session.error };
    this.roles = session.data.roles;

    const projects = await this.dependencies.sessionApi.listProjects();
    if (!this.isCurrent(generation)) return null;
    if (!projects.ok) return { status: "error", error: projects.error };

    this.projects = projects.data.projects;
    this.userId = session.data.user_id;

    if (this.projects.length === 0) {
      this.tabs = { open: [], active: "" };
      return { status: "empty" };
    }

    // A remembered project is only honoured when the server's own list for this
    // session still contains it. A stale id must fall back to the normal
    // selection instead of opening a project the user no longer owns.
    const storedTabs = this.dependencies.projectTabsForUser?.(session.data.user_id) ?? null;
    const remembered = preferredProjectId
      ?? storedTabs?.active
      ?? this.dependencies.preferredProjectIdForUser?.(session.data.user_id)
      ?? null;
    const preferred = remembered
      ? this.projects.find((project) => project.project_id === remembered)
      : undefined;
    const authorized = this.projects.map((project) => project.project_id);
    this.setTabs(normalizeProjectTabs(
      storedTabs?.open ?? [],
      preferred?.project_id ?? remembered ?? "",
      authorized,
    ));

    if (preferred) return this.openProject(preferred.project_id, generation, locale);

    if (this.projects.length > 1) {
      return { status: "selecting", projects: this.projects };
    }

    return this.openProject(this.projects[0].project_id, generation, locale);
  }

  async createProject(
    projectId: string,
    name: string,
    locale: WorkspaceLocale = "en",
    metadata: {
      description?: string;
      start_date?: string | null;
      date_system?: "gregorian" | "jalali";
      business_domain?:
        | "construction"
        | "oil_gas"
        | "infrastructure"
        | "industrial"
        | "energy"
        | "other"
        | "";
    } = {},
  ): Promise<ProjectBootstrapState | null> {
    const generation = ++this.generation;
    const result = await this.dependencies.sessionApi.createProject(
      projectId, name, metadata,
    );
    if (!this.isCurrent(generation)) return null;
    if (!result.ok) return { status: "error", error: result.error };
    // The Projects window and the title bar read this list, so the new project
    // must be in it before the workspace renders, not after a page reload.
    const listed = await this.dependencies.sessionApi.listProjects();
    if (!this.isCurrent(generation)) return null;
    if (listed.ok) this.projects = listed.data.projects;
    return this.hydrateProject(result.data.context, generation, locale);
  }

  /** Read the authoritative project row, including metadata, for the editor. */
  async loadProjectSummary(projectId: string): Promise<ApiResult<{ project: ProjectSummary }>> {
    if (!this.dependencies.sessionApi.getProject) {
      return {
        ok: false,
        error: localError("PROJECT_METADATA_UNAVAILABLE", "error.project.metadata_unavailable", ["refresh"]),
      };
    }
    return this.dependencies.sessionApi.getProject(projectId);
  }

  /** Save metadata under the revision the editor loaded; a 409 means reload. */
  async saveProjectMetadata(
    projectId: string,
    metadata: {
      name: string;
      description: string;
      start_date: string | null;
      date_system: "gregorian" | "jalali";
      primary_calendar_id?: string | null;
      business_domain?:
        | "construction"
        | "oil_gas"
        | "infrastructure"
        | "industrial"
        | "energy"
        | "other"
        | "";
    },
    expectedRevision: number,
  ): Promise<ApiResult<{ project: ProjectSummary }>> {
    if (!this.dependencies.sessionApi.updateProject) {
      return {
        ok: false,
        error: localError("PROJECT_METADATA_UNAVAILABLE", "error.project.metadata_unavailable", ["refresh"]),
      };
    }
    return this.dependencies.sessionApi.updateProject(projectId, metadata, expectedRevision);
  }

  /** Change the V26 project status under the configuration revision guard. */
  async saveProjectStatus(
    projectId: string,
    status: ProjectStatus,
    expectedRevision: number,
  ): Promise<ApiResult<{ contract_version: string; project: ProjectSummary }>> {
    if (!this.dependencies.sessionApi.setProjectStatus) {
      return {
        ok: false,
        error: localError("PROJECT_STATUS_UNAVAILABLE", "error.project.metadata_unavailable", ["refresh"]),
      };
    }
    return this.dependencies.sessionApi.setProjectStatus(projectId, status, expectedRevision);
  }

  /** Immutable status history for the settings panel. */
  async loadProjectStatusHistory(
    projectId: string,
  ): Promise<ApiResult<{ contract_version: string; events: ProjectStatusEvent[] }>> {
    if (!this.dependencies.sessionApi.projectStatusHistory) {
      return {
        ok: false,
        error: localError("PROJECT_STATUS_HISTORY_UNAVAILABLE", "error.project.metadata_unavailable", ["refresh"]),
      };
    }
    return this.dependencies.sessionApi.projectStatusHistory(projectId);
  }

  /** Projects the current session may open, exactly as the session service listed them. */
  openableProjects(): readonly ProjectSummary[] {
    return this.projects;
  }

  /** Open project tabs in the user's order; the active tab is the current context. */
  projectTabs(): ProjectTabState {
    return { open: [...this.tabs.open], active: this.tabs.active };
  }

  private authorizedProjectIds(): string[] {
    return this.projects.map((project) => project.project_id);
  }

  private setTabs(next: ProjectTabState): void {
    this.tabs = next;
    if (this.userId) {
      this.dependencies.rememberProjectTabsForUser?.(this.userId, next);
    }
  }

  /**
   * Close one project tab. The last tab stays open and the current context is
   * unchanged; closing the active tab opens and authorizes its neighbour.
   */
  async closeProject(
    projectId: string,
    locale: WorkspaceLocale = "en",
  ): Promise<ProjectBootstrapState | null> {
    const before = this.tabs;
    const next = closeProjectTab(before, projectId, this.authorizedProjectIds());
    if (next.open.length === before.open.length) return null;
    this.setTabs(next);
    if (next.active === before.active) return null;
    const generation = ++this.generation;
    return this.openProject(next.active, generation, locale);
  }

  async selectProject(
    projectId: string,
    locale: WorkspaceLocale = "en",
  ): Promise<ProjectBootstrapState | null> {
    const generation = ++this.generation;
    if (!this.projects.some((project) => project.project_id === projectId)) {
      return {
        status: "error",
        error: localError(
          "PROJECT_NOT_AVAILABLE",
          "error.project.not_available",
          ["select_project"],
        ),
      };
    }

    // The register and tab labels are read from this list, so a switch refreshes
    // it before opening: another session may have renamed the project or moved
    // its configuration revision, and the UI must not show the stale record.
    const listed = await this.dependencies.sessionApi.listProjects();
    if (!this.isCurrent(generation)) return null;
    if (listed.ok) {
      this.projects = listed.data.projects;
      this.setTabs(normalizeProjectTabs(
        this.tabs.open,
        projectId,
        this.authorizedProjectIds(),
      ));
    }

    return this.openProject(projectId, generation, locale);
  }

  private async openProject(
    projectId: string,
    generation: number,
    locale: WorkspaceLocale,
  ): Promise<ProjectBootstrapState | null> {
    if (!this.isCurrent(generation)) return null;

    const opening: ProjectBootstrapState = { status: "opening", projectId };
    void opening;

    const result = await this.dependencies.sessionApi.openProject(projectId);
    if (!this.isCurrent(generation)) return null;
    if (!result.ok) return { status: "error", error: result.error };

    return this.hydrateProject(result.data.context, generation, locale);
  }

  private async hydrateProject(
    projectContext: SessionProjectContext,
    generation: number,
    locale: WorkspaceLocale,
  ): Promise<ProjectBootstrapState | null> {
    if (!this.isCurrent(generation)) return null;

    const context = toWorkspaceContext(projectContext);
    this.dependencies.syncRuntime.openProject(
      context.tenant_id,
      context.project_id,
      context.revision,
    );

    // The language is part of the read: server-backed guidance and every
    // localized projection must be produced in the language the user chose,
    // instead of defaulting to English and only relabelling the shell.
    const summary = this.projects.find((project) => project.project_id === projectContext.project_id) ?? null;
    const workspace = await this.dependencies.workspaceReadClient.load(context, {
      locale,
      // The Gantt shades non-working days from this project's persisted
      // calendar, so the summary's reference travels with the read instead of
      // being guessed from the calendar catalogue.
      primaryCalendarId: summary?.primary_calendar_id ?? null,
    });
    if (!this.isCurrent(generation)) return null;
    if (!workspace.ok) return { status: "error", error: workspace.error };

    let hydratedWorkspace = workspace.data;
    if (this.dependencies.p6PresentationLoader) {
      try {
        hydratedWorkspace = await this.dependencies.p6PresentationLoader(workspace.data, context);
      } catch (error) {
        return { status: "error", error: loaderError(error) };
      }
    }

    if (!this.isCurrent(generation)) return null;
    const authorized = this.authorizedProjectIds();
    if (authorized.includes(projectContext.project_id)) {
      // The server confirmed this context, so the tab becomes active. A project
      // that left the session list is never re-added here.
      this.setTabs(normalizeProjectTabs(
        openProjectTab(this.tabs, projectContext.project_id, authorized).open,
        projectContext.project_id,
        authorized,
      ));
    }
    return {
      status: "ready",
      context,
      workspace: hydratedWorkspace,
      userId: projectContext.user_id,
      roles: this.roles,
    };
  }

  private isCurrent(generation: number): boolean {
    return generation === this.generation;
  }
}
