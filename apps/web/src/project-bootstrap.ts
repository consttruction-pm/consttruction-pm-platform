import type { ApiResult, ClientError, ProjectContext } from "./client.js";
import type { ProjectSummary, SessionApi } from "./session-api.js";
import { toWorkspaceContext } from "./session-api.js";
import type { WebSyncRuntime } from "./sync-runtime.js";
import type { WorkspaceState } from "./workspace-model.js";
import type { WorkspaceReadClient } from "./workspace-read-api.js";
import type { loadP6Presentation } from "./p6-api.js";

export type ProjectBootstrapState =
  | { status: "loading" }
  | { status: "selecting"; projects: readonly ProjectSummary[] }
  | { status: "opening"; projectId: string }
  | { status: "ready"; context: ProjectContext; workspace: WorkspaceState }
  | { status: "error"; error: ClientError };

export type ProjectBootstrapDependencies = {
  sessionApi: SessionApi;
  syncRuntime: WebSyncRuntime;
  workspaceReadClient: WorkspaceReadClient;
  p6PresentationLoader?: (state: WorkspaceState, context: ProjectContext) => ReturnType<typeof loadP6Presentation>;
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

  constructor(private readonly dependencies: ProjectBootstrapDependencies) {}

  async start(): Promise<ProjectBootstrapState | null> {
    const generation = ++this.generation;

    const session = await this.dependencies.sessionApi.getSession();
    if (!this.isCurrent(generation)) return null;
    if (!session.ok) return { status: "error", error: session.error };

    const projects = await this.dependencies.sessionApi.listProjects();
    if (!this.isCurrent(generation)) return null;
    if (!projects.ok) return { status: "error", error: projects.error };

    this.projects = projects.data.projects;

    if (this.projects.length === 0) {
      return {
        status: "error",
        error: localError(
          "NO_PROJECTS_AVAILABLE",
          "error.projects.none",
          ["retry"],
        ),
      };
    }

    if (this.projects.length > 1) {
      return { status: "selecting", projects: this.projects };
    }

    return this.openProject(this.projects[0].project_id, generation);
  }

  async selectProject(projectId: string): Promise<ProjectBootstrapState | null> {
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

    return this.openProject(projectId, generation);
  }

  private async openProject(
    projectId: string,
    generation: number,
  ): Promise<ProjectBootstrapState | null> {
    if (!this.isCurrent(generation)) return null;

    const opening: ProjectBootstrapState = { status: "opening", projectId };
    void opening;

    const result = await this.dependencies.sessionApi.openProject(projectId);
    if (!this.isCurrent(generation)) return null;
    if (!result.ok) return { status: "error", error: result.error };

    const context = toWorkspaceContext(result.data.context);
    this.dependencies.syncRuntime.openProject(
      context.tenant_id,
      context.project_id,
      context.revision,
    );

    const workspace = await this.dependencies.workspaceReadClient.load(context);
    if (!this.isCurrent(generation)) return null;
    if (!workspace.ok) return { status: "error", error: workspace.error };

    let hydratedWorkspace = workspace.data;
    if (this.dependencies.p6PresentationLoader) {
      try {
        hydratedWorkspace = await this.dependencies.p6PresentationLoader(workspace.data, context);
      } catch (error) {
        if (!this.isCurrent(generation)) return null;
        return { status: "error", error: loaderError(error) };
      }
    }

    if (!this.isCurrent(generation)) return null;
    return { status: "ready", context, workspace: hydratedWorkspace };
  }

  private isCurrent(generation: number): boolean {
    return generation === this.generation;
  }
}
