import type { ApiResult, ClientError } from "./client.js";

export type Session = {
  session_id: string;
  user_id: string;
  tenant_id: string;
  roles: string[];
  expires_at: string;
};

export type ProjectSummary = {
  project_id: string;
  tenant_id: string;
  name: string;
  revision: number;
  description?: string;
  start_date?: string | null;
  date_system?: "gregorian" | "jalali" | string;
  primary_calendar_id?: string | null;
  /** Optimistic token for metadata edits; never the workspace data revision. */
  settings_revision?: number;
};

export type ProjectMetadataInput = {
  name: string;
  description: string;
  start_date: string | null;
  date_system: "gregorian" | "jalali";
  primary_calendar_id?: string | null;
};

export type ProjectCreateMetadata = {
  description?: string;
  start_date?: string | null;
  date_system?: "gregorian" | "jalali";
};

export type ProjectContext = {
  tenant_id: string;
  project_id: string;
  revision: number;
  user_id: string;
};

export type SessionApi = {
  getSession(): Promise<ApiResult<Session>>;
  listProjects(): Promise<ApiResult<{ projects: ProjectSummary[] }>>;
  openProject(projectId: string): Promise<ApiResult<{ context: ProjectContext }>>;
  createProject(
    projectId: string,
    name: string,
    metadata?: ProjectCreateMetadata,
  ): Promise<ApiResult<{ context: ProjectContext }>>;
  getProject?(projectId: string): Promise<ApiResult<{ project: ProjectSummary }>>;
  updateProject?(
    projectId: string,
    metadata: ProjectMetadataInput,
    expectedRevision: number,
  ): Promise<ApiResult<{ project: ProjectSummary }>>;
};

export class FetchSessionApi implements SessionApi {
  constructor(private readonly baseUrl: string) {}

  getSession() { return this.request<Session>("/api/session"); }
  listProjects() { return this.request<{ projects: ProjectSummary[] }>("/api/projects"); }

  openProject(projectId: string) {
    return this.request<{ context: ProjectContext }>(
      `/api/projects/${encodeURIComponent(projectId)}/open`, "POST",
    );
  }

  createProject(
    projectId: string,
    name: string,
    metadata?: ProjectCreateMetadata,
  ) {
    return this.request<{ context: ProjectContext }>("/api/projects", "POST", {
      project_id: projectId, name, ...metadata,
    });
  }

  getProject(projectId: string) {
    return this.request<{ project: ProjectSummary }>(
      `/api/projects/${encodeURIComponent(projectId)}`,
    );
  }

  updateProject(
    projectId: string,
    metadata: ProjectMetadataInput,
    expectedRevision: number,
  ) {
    return this.request<{ project: ProjectSummary }>(
      `/api/projects/${encodeURIComponent(projectId)}`,
      "PATCH",
      { ...metadata, expected_revision: expectedRevision },
    );
  }

  private async request<T>(
    path: string, method: "GET" | "POST" | "PATCH" = "GET", body?: unknown,
  ): Promise<ApiResult<T>> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    try {
      const response = await fetch(new URL(path, this.baseUrl), {
        method, credentials: "include",
        headers: body === undefined ? {} : { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: controller.signal,
      });
      const payload = await response.json().catch(() => null);
      if (response.ok) return { ok: true, data: payload as T };
      return {
        ok: false,
        error: {
          code: String(payload?.code ?? "API_ERROR"),
          retryable: Boolean(payload?.retryable ?? false),
          message_key: String(payload?.message_key ?? "error.api"),
          available_actions: Array.isArray(payload?.available_actions)
            ? payload.available_actions.map(String) : [],
        },
      };
    } catch {
      const error: ClientError = {
        code: controller.signal.aborted ? "NETWORK_TIMEOUT" : "NETWORK_ERROR",
        retryable: true,
        message_key: "error.network", available_actions: ["retry"],
      };
      return { ok: false, error };
    } finally {
      clearTimeout(timeout);
    }
  }
}

export function toWorkspaceContext(context: ProjectContext) {
  return {
    tenant_id: context.tenant_id,
    project_id: context.project_id,
    revision: context.revision,
  };
}
