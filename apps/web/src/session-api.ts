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
};

export type ProjectContextResponse = {
  tenant_id: string;
  project_id: string;
  revision: number;
  user_id: string;
};

export type SessionApi = {
  getSession(): Promise<ApiResult<Session>>;
  listProjects(): Promise<ApiResult<{ projects: ProjectSummary[] }>>;
  openProject(projectId: string): Promise<ApiResult<{ context: ProjectContextResponse }>>;
};

export type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export class FetchSessionApi implements SessionApi {
  constructor(
    private readonly baseUrl: string,
    private readonly fetchImpl: FetchLike = fetch,
  ) {}

  getSession(): Promise<ApiResult<Session>> {
    return this.request<Session>("/api/session");
  }

  listProjects(): Promise<ApiResult<{ projects: ProjectSummary[] }>> {
    return this.request<{ projects: ProjectSummary[] }>("/api/projects");
  }

  openProject(projectId: string): Promise<ApiResult<{ context: ProjectContextResponse }>> {
    if (!projectId) {
      return Promise.resolve({
        ok: false,
        error: {
          code: "PROJECT_ID_REQUIRED",
          retryable: false,
          message_key: "error.project.id_required",
          available_actions: [],
        },
      });
    }
    return this.request<{ context: ProjectContextResponse }>(
      `/api/projects/${encodeURIComponent(projectId)}/open`,
      "POST",
    );
  }

  private async request<T>(
    path: string,
    method: "GET" | "POST" = "GET",
  ): Promise<ApiResult<T>> {
    try {
      const response = await this.fetchImpl(new URL(path, this.baseUrl), {
        method,
        credentials: "include",
        headers: { Accept: "application/json" },
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
  context: ProjectContextResponse,
): { tenant_id: string; project_id: string; revision: number } {
  return {
    tenant_id: context.tenant_id,
    project_id: context.project_id,
    revision: context.revision,
  };
}
