/**
 * Enterprise Workbench API transport.
 *
 * Every call is same-origin, credentialed and cookie/session based. This module
 * never derives tenant, actor or permission authority from client state; those
 * values are read back from the server response.
 */

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly retryable: boolean;

  constructor(status: number, code: string, message: string, retryable = false) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.retryable = retryable;
  }
}

export type SessionInfo = {
  user_id: string;
  tenant_id: string;
  roles: string[];
  expires_at: string;
};

export type ProjectSummary = {
  project_id: string;
  tenant_id?: string;
  name: string;
  revision: number;
  description?: string;
  start_date?: string | null;
  finish_date?: string | null;
  status?: string;
  business_domain?: string;
  obs_responsible_manager?: string;
  website_url?: string;
  date_system?: string;
  checkout_state?: string;
  [key: string]: unknown;
};

export type EnterpriseTask = {
  contract_version: "cubi-enterprise-task.v1";
  task_id: string;
  tenant_id: string;
  title: string;
  description: string | null;
  created_by_user_id: string;
  created_at: string;
  status: "open" | "in_progress" | "blocked" | "completed" | "cancelled";
  priority: "low" | "normal" | "high" | "urgent";
  assigned_user_id: string | null;
  assigned_team_id: string | null;
  project_id: string | null;
  due_at: string | null;
  dependency_ids: string[];
  revision: number;
  updated_at: string | null;
  completed_at: string | null;
  completed_by_user_id: string | null;
};

export type ResourceRecord = {
  resource_id: string;
  name: string;
  resource_type: string;
  parent_resource_id: string | null;
  calendar_id: string | null;
  unit_of_measure: string | null;
  email: string | null;
  is_active: boolean;
  record_revision: number;
};

export type DocumentRecord = {
  document_id: string;
  title: string;
  /** The document register names the category `resource_type`. */
  resource_type?: string;
  document_type?: string;
  status?: string;
  revision?: number;
  updated_at?: string;
  storage_ref?: string;
  content_hash?: string;
  [key: string]: unknown;
};

export type ActivityEnvelope = {
  activity?: {
    activity_id?: string;
    name?: string;
    status?: string;
    percent_complete?: number | null;
  };
};

export type EnterpriseRecord = {  record_id: string;
  kind: string;
  tenant_id: string;
  revision: number;
  status?: string;
  created_at?: string;
  updated_at?: string | null;
  created_by_user_id?: string;
  deleted_at?: string | null;
  [key: string]: unknown;
};

export type EnterpriseList = {
  contract_version: string;
  items: EnterpriseRecord[];
  next_cursor: unknown;
};

export type ReportDefinition = {
  report_id: string;
  name?: string;
  subject?: string;
  revision?: number;
  [key: string]: unknown;
};

const CSRF_HEADER = "x-csrf-token";
const CSRF_COOKIE = "cp_csrf";

function readCookie(name: string): string | null {
  for (const part of document.cookie.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) return decodeURIComponent(rest.join("="));
  }
  return null;
}

function csrfHeader(): Record<string, string> {
  const token = readCookie(CSRF_COOKIE);
  return token ? { [CSRF_HEADER]: token } : {};
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  { timeoutMs = 30_000 }: { timeoutMs?: number } = {},
): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetch(path, {
      credentials: "same-origin",
      cache: "no-store",
      ...init,
      headers: {
        Accept: "application/json",
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...csrfHeader(),
        ...(init.headers ?? {}),
      },
      signal: controller.signal,
    });
  } catch {
    window.clearTimeout(timer);
    throw new ApiError(0, "NETWORK_UNAVAILABLE", "The server could not be reached.");
  } finally {
    window.clearTimeout(timer);
  }
  const text = await response.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = null;
    }
  }
  if (!response.ok) {
    const record = (payload ?? {}) as Record<string, unknown>;
    const code = String(record.code ?? record.message_key ?? `HTTP_${response.status}`);
    const message = String(record.message ?? record.code ?? `HTTP ${response.status}`);
    throw new ApiError(response.status, code, message, Boolean(record.retryable));
  }
  return payload as T;
}

/**
 * Report the real availability of a server capability without inventing data.
 * 404/403/401 are meaningful states, not errors to hide.
 */
export type CapabilityState = "available" | "forbidden" | "unauthenticated" | "unavailable" | "source_unavailable" | "error";

export type CapabilityProbe = {
  path: string;
  state: CapabilityState;
  status: number;
  code: string;
};

export async function probe(path: string): Promise<CapabilityProbe> {
  try {
    await request<unknown>(path);
    return { path, state: "available", status: 200, code: "OK" };
  } catch (error) {
    if (error instanceof ApiError) {
      const state: CapabilityState =
        error.status === 401 ? "unauthenticated"
          : error.status === 403 ? "forbidden"
            : error.status === 404 ? "unavailable"
              : error.status === 503 ? "source_unavailable"
                : "error";
      return { path, state, status: error.status, code: error.code };
    }
    return { path, state: "error", status: 0, code: "UNKNOWN" };
  }
}

export const api = {
  getSession: () => request<SessionInfo>("/api/session"),
  login: (email: string, password: string) =>
    request<SessionInfo>("/api/session", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () => request<unknown>("/api/session", { method: "DELETE" }),

  listProjects: async () => {
    const payload = await request<{ projects: ProjectSummary[] }>("/api/projects");
    return payload.projects ?? [];
  },

  listSharedProjects: async () => {
    const payload = await request<{ projects: ProjectSummary[] }>("/api/shared-projects");
    return payload.projects ?? [];
  },

  /**
   * Read one project. The server re-authorizes the request for this project,
   * so a 403 here is a real answer about the selected project, not a UI gate.
   */
  getProject: async (projectId: string) => {
    const payload = await request<{ project: ProjectSummary }>(
      `/api/projects/${encodeURIComponent(projectId)}`,
    );
    return payload.project;
  },

  listTasks: async (projectId?: string | null) => {
    const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
    return request<{ contract_version: string; tasks: EnterpriseTask[] }>(`/api/enterprise/tasks${query}`);
  },
  createTask: (body: Record<string, unknown>, idempotencyKey: string) =>
    request<{ task: EnterpriseTask }>("/api/enterprise/tasks", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({ contract_version: "cubi-enterprise-task.v1", ...body }),
    }),
  updateTask: (taskId: string, body: Record<string, unknown>) =>
    request<{ task: EnterpriseTask }>(`/api/enterprise/tasks/${encodeURIComponent(taskId)}`, {
      method: "PATCH",
      body: JSON.stringify({ contract_version: "cubi-enterprise-task.v1", ...body }),
    }),

  enterpriseList: (kind: string, query: Record<string, string> = {}) => {
    const parameters = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) if (value) parameters.set(key, value);
    const suffix = parameters.toString() ? `?${parameters.toString()}` : "";
    return request<EnterpriseList>(`/api/enterprise/${encodeURIComponent(kind)}${suffix}`);
  },
  enterpriseCreate: (kind: string, body: Record<string, unknown>, idempotencyKey?: string) =>
    request<{ record: EnterpriseRecord }>(`/api/enterprise/${encodeURIComponent(kind)}`, {
      method: "POST",
      headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {},
      body: JSON.stringify(body),
    }),
  enterpriseUpdate: (kind: string, recordId: string, body: Record<string, unknown>) =>
    request<{ record: EnterpriseRecord }>(`/api/enterprise/${encodeURIComponent(kind)}/${encodeURIComponent(recordId)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  enterpriseDelete: (kind: string, recordId: string, expectedRevision: number) =>
    request<{ record: EnterpriseRecord }>(`/api/enterprise/${encodeURIComponent(kind)}/${encodeURIComponent(recordId)}`, {
      method: "DELETE",
      body: JSON.stringify({ expected_revision: expectedRevision }),
    }),
  enterpriseRestore: (kind: string, recordId: string, expectedRevision: number) =>
    request<{ record: EnterpriseRecord }>(`/api/enterprise/${encodeURIComponent(kind)}/${encodeURIComponent(recordId)}/restore`, {
      method: "POST",
      body: JSON.stringify({ expected_revision: expectedRevision }),
    }),
  listApprovalDecisions: (approvalId: string) =>
    request<{ items: Record<string, unknown>[] }>(`/api/enterprise/approvals/${encodeURIComponent(approvalId)}/decisions`),
  recordApprovalDecision: (approvalId: string, body: Record<string, unknown>, idempotencyKey: string) =>
    request<{ decision: Record<string, unknown> }>(`/api/enterprise/approvals/${encodeURIComponent(approvalId)}/decisions`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(body),
    }),
  publishWorkflow: (workflowId: string, body: Record<string, unknown>) =>
    request<{ record: EnterpriseRecord }>(`/api/enterprise/workflows/${encodeURIComponent(workflowId)}/publish`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listResources: async (projectId: string) => {
    const payload = await request<{ resources: { resource: ResourceRecord }[] }>(
      `/api/projects/${encodeURIComponent(projectId)}/p6/resources`,
    );
    return (payload.resources ?? []).map((entry) => entry.resource);
  },
  listDocuments: async (projectId: string) => {
    const payload = await request<{ documents: DocumentRecord[] }>(
      `/api/projects/${encodeURIComponent(projectId)}/documents`,
    );
    return payload.documents ?? [];
  },
  listIssues: async (projectId: string) => {
    const payload = await request<{ issues: Record<string, unknown>[] }>(
      `/api/projects/${encodeURIComponent(projectId)}/p6/issues`,
    );
    return payload.issues ?? [];
  },
  /** Read-only Engineering activity master; Enterprise never writes here. */
  listProjectActivities: async (projectId: string) => {
    const payload = await request<{ activities?: ActivityEnvelope[] }>(
      `/api/projects/${encodeURIComponent(projectId)}/p6/activities`,
    );
    return { activities: payload.activities ?? [] };
  },
  listRisks: async (projectId: string) => {
    const payload = await request<{ risks: Record<string, unknown>[] }>(
      `/api/projects/${encodeURIComponent(projectId)}/risks`,
    );
    return payload.risks ?? [];
  },

  reportCatalogue: async (projectId: string) => {
    const payload = await request<{ catalogue?: Record<string, unknown>[]; subjects?: Record<string, unknown>[] }>(
      `/api/projects/${encodeURIComponent(projectId)}/reports/catalogue`,
    );
    return payload.subjects ?? payload.catalogue ?? [];
  },
  listReports: async (projectId: string) => {
    const payload = await request<
      { reports?: ReportDefinition[]; definitions?: ReportDefinition[]; catalogue?: ReportDefinition[] } | ReportDefinition[]
    >(`/api/projects/${encodeURIComponent(projectId)}/reports`);
    // The route answers with `{catalogue, reports}`; `definitions` is kept as a
    // compatibility read only. Catalogue descriptors carry no report_id, so
    // they are never reported as saved reports.
    const rows = Array.isArray(payload) ? payload : payload.reports ?? payload.definitions ?? [];
    return rows.filter((row) => Boolean(row && row.report_id));
  },
  listReportRuns: async (projectId: string, reportId: string) => {
    const payload = await request<{ runs?: Record<string, unknown>[] } | Record<string, unknown>[]>(
      `/api/projects/${encodeURIComponent(projectId)}/reports/${encodeURIComponent(reportId)}/runs`,
    );
    return Array.isArray(payload) ? payload : payload.runs ?? [];
  },
  runReport: (projectId: string, reportId: string, parameters?: Record<string, unknown>) =>
    request<Record<string, unknown>>(
      `/api/projects/${encodeURIComponent(projectId)}/reports/${encodeURIComponent(reportId)}/run`,
      {
        method: "POST",
        ...(parameters ? { body: JSON.stringify({ parameters }) } : {}),
      },
    ),
  listReportSchedules: async (projectId: string, reportId: string) => {
    const payload = await request<{ schedules?: Record<string, unknown>[] } | Record<string, unknown>[]>(
      `/api/projects/${encodeURIComponent(projectId)}/reports/${encodeURIComponent(reportId)}/schedules`,
    );
    return Array.isArray(payload) ? payload : payload.schedules ?? [];
  },
};

export function errorText(error: unknown): string {
  if (error instanceof ApiError) return `${error.code} (HTTP ${error.status})`;
  return error instanceof Error ? error.message : String(error);
}
