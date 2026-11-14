import { API_REQUEST_TIMEOUT_MS } from "./client.js";
import { withCsrfHeader } from "./csrf.js";
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
  /** V26 General tab status: active, inactive, planned or what_if. */
  status?: ProjectStatus;
  /**
   * CUBI Business Domain (the EPS-level classification in P6 terms). The
   * empty string means the project has not been classified yet.
   */
  business_domain?: BusinessDomain | "";
  /** Responsible manager recorded on the project (OBS reference when available). */
  obs_responsible_manager?: string;
  /** Optional absolute http(s) project web-site address. */
  website_url?: string;
  checkout_state?: "checked_in" | "checked_out";
  checked_out_by?: string;
  checked_out_at?: string | null;
  /** V26 Defaults tab: applied to newly created activities only. */
  default_activity_type?: string;
  default_percent_complete_type?: string;
  activity_id_prefix?: string;
  activity_id_suffix?: string;
  activity_id_increment?: number;
  increment_activity_id?: boolean;
};

export type BusinessDomain =
  | "construction"
  | "oil_gas"
  | "infrastructure"
  | "industrial"
  | "energy"
  | "other";

export type ProjectStatus = "active" | "inactive" | "planned" | "what_if";

export type ProjectStatusEvent = {
  event_id: string;
  tenant_id: string;
  project_id: string;
  from_status: ProjectStatus;
  to_status: ProjectStatus;
  actor_user_id: string;
  recorded_at: string;
  settings_revision: number;
};

export type ProjectMetadataInput = {
  name: string;
  description: string;
  start_date: string | null;
  date_system: "gregorian" | "jalali";
  primary_calendar_id?: string | null;
  business_domain?: BusinessDomain | "";
  /** Responsible manager recorded on the project (OBS reference when available). */
  obs_responsible_manager?: string;
  /** Optional absolute http(s) project web-site address. */
  website_url?: string;
  default_activity_type?: string;
  default_percent_complete_type?: string;
  activity_id_prefix?: string;
  activity_id_suffix?: string;
  activity_id_increment?: number;
  increment_activity_id?: boolean;
};

export type ProjectScheduleSettings = {
  contract_version: "p6-project-schedule-settings-api.v1";
  kind: "project_schedule_settings";
  scope: { tenant_id: string; project_id: string; project_revision: number };
  record_revision: number;
  mode: "DATE_BASED" | "TIME_AWARE";
  project_calendar: {
    calendar_id: string;
    calendar_version: string;
    kind: string;
    system: "gregorian" | "jalali";
  };
  project_start: string;
  project_finish: string | null;
  schedule_options: Record<string, unknown>;
  project_leveling_priority: number;
};

export type ProjectScheduleSettingsInput = {
  contract_version: "p6-project-schedule-settings-api.v1";
  expected_record_revision: number;
  mode: "DATE_BASED" | "TIME_AWARE";
  project_calendar_id: string;
  project_calendar_version: string;
  project_calendar_system: "gregorian" | "jalali";
  project_start: string;
  project_finish: string | null;
  schedule_options: Record<string, unknown>;
  project_leveling_priority: number;
};

export type ProjectCreateMetadata = {
  description?: string;
  start_date?: string | null;
  date_system?: "gregorian" | "jalali";
  business_domain?: BusinessDomain | "";
  obs_responsible_manager?: string;
  website_url?: string;
  default_activity_type?: string;
  default_percent_complete_type?: string;
  activity_id_prefix?: string;
  activity_id_suffix?: string;
  activity_id_increment?: number;
  increment_activity_id?: boolean;
};

export type ProjectContext = {
  tenant_id: string;
  project_id: string;
  revision: number;
  user_id: string;
};

export type SessionApi = {
  getSession(): Promise<ApiResult<Session>>;
  login?(email: string, password: string): Promise<ApiResult<Session>>;
  logout?(): Promise<ApiResult<null>>;
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
  setProjectStatus?(
    projectId: string,
    status: ProjectStatus,
    expectedRevision: number,
  ): Promise<ApiResult<{ contract_version: string; project: ProjectSummary }>>;
  projectStatusHistory?(
    projectId: string,
  ): Promise<ApiResult<{ contract_version: string; events: ProjectStatusEvent[] }>>;
  setProjectCheckout?(
    projectId: string,
    checkedOut: boolean,
    expectedRevision: number,
  ): Promise<ApiResult<{ contract_version: string; project: ProjectSummary }>>;
  getProjectScheduleSettings?(
    projectId: string,
  ): Promise<ApiResult<ProjectScheduleSettings>>;
  saveProjectScheduleSettings?(
    projectId: string,
    settings: ProjectScheduleSettingsInput,
  ): Promise<ApiResult<ProjectScheduleSettings>>;
};

export class FetchSessionApi implements SessionApi {
  constructor(private readonly baseUrl: string) {}

  getSession() { return this.request<Session>("/api/session"); }

  login(email: string, password: string) {
    return this.request<Session>("/api/session", "POST", { email, password });
  }

  async logout(): Promise<ApiResult<null>> {
    const result = await this.request<null>("/api/session", "DELETE");
    return result.ok ? { ok: true, data: null } : result;
  }
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

  setProjectStatus(
    projectId: string,
    status: ProjectStatus,
    expectedRevision: number,
  ) {
    return this.request<{ contract_version: string; project: ProjectSummary }>(
      `/api/projects/${encodeURIComponent(projectId)}/status`,
      "POST",
      { status, expected_revision: expectedRevision },
    );
  }

  projectStatusHistory(projectId: string) {
    return this.request<{ contract_version: string; events: ProjectStatusEvent[] }>(
      `/api/projects/${encodeURIComponent(projectId)}/status-history`,
    );
  }

  setProjectCheckout(projectId: string, checkedOut: boolean, expectedRevision: number) {
    return this.request<{ contract_version: string; project: ProjectSummary }>(
      `/api/projects/${encodeURIComponent(projectId)}/checkout`,
      "POST",
      { checked_out: checkedOut, expected_revision: expectedRevision },
    );
  }

  getProjectScheduleSettings(projectId: string) {
    return this.request<ProjectScheduleSettings>(
      `/api/projects/${encodeURIComponent(projectId)}/p6/schedule/settings`,
    );
  }

  saveProjectScheduleSettings(
    projectId: string,
    settings: ProjectScheduleSettingsInput,
  ) {
    return this.request<ProjectScheduleSettings>(
      `/api/projects/${encodeURIComponent(projectId)}/p6/schedule/settings`,
      "POST",
      settings,
    );
  }

  private async request<T>(
    path: string, method: "GET" | "POST" | "PATCH" | "DELETE" = "GET", body?: unknown,
  ): Promise<ApiResult<T>> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), API_REQUEST_TIMEOUT_MS);
    try {
      const response = await fetch(new URL(path, this.baseUrl), {
        method, credentials: "include",
        headers: withCsrfHeader(
          method,
          body === undefined ? {} : { "Content-Type": "application/json" },
        ),
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
