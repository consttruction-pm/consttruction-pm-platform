import type { ApiResult, ApiTransport, ClientError } from "./client.js";

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
  createProject(projectId: string, name: string): Promise<ApiResult<{ context: ProjectContext }>>;
};

export class FetchSessionApi implements SessionApi {
  constructor(private readonly baseUrl: string) {}

  getSession() {
    return this.request<Session>("/api/session");
  }

  listProjects() {
    return this.request<{ projects: ProjectSummary[] }>("/api/projects");
  }

  openProject(projectId: string) {
    return this.request<{ context: ProjectContext }>(
      `/api/projects/${encodeURIComponent(projectId)}/open`,
      "POST",
    );
  }

  createProject(projectId: string, name: string) {
    return this.request<{ context: ProjectContext }>("/api/projects", "POST", {
      project_id: projectId,
      name,
    });
  }

  private async request<T>(
    path: string,
    method: "GET" | "POST" = "GET",
    body?: unknown,
  ): Promise<ApiResult<T>> {
    try {
      const response = await fetch(new URL(path, this.baseUrl), {
        method,
        credentials: "include",
        headers: body === undefined ? {} : { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
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
            ? payload.available_actions.map(String)
            : [],
        },
      };
    } catch {
      const error: ClientError = {
        code: "NETWORK_ERROR",
        retryable: true,
        message_key: "error.network",
        available_actions: ["retry"],
      };
      return { ok: false, error };
    }
  }
}

export function toWorkspaceContext(
  context: ProjectContext,
): { tenant_id: string; project_id: string; revision: number } {
  return {
    tenant_id: context.tenant_id,
    project_id: context.project_id,
    revision: context.revision,
  };
}
