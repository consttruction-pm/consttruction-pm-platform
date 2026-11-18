import type {
  EnterpriseDashboardCatalog,
  EnterpriseDashboardClient,
  EnterpriseDashboardDefinition,
  EnterpriseDashboardFilter,
  EnterpriseDashboardPortlet,
  EnterpriseDashboardRead,
} from "./enterprise-dashboard.js";

type StoredDashboard = { dashboard: EnterpriseDashboardDefinition; revision: number };

export class EnterpriseDashboardHttpError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string) {
    super(code);
    this.name = "EnterpriseDashboardHttpError";
    this.status = status;
    this.code = code;
  }
}

function idempotencyKey(): string {
  if (typeof crypto === "undefined" || typeof crypto.randomUUID !== "function") {
    throw new Error("SECURE_IDEMPOTENCY_KEY_UNAVAILABLE");
  }
  return crypto.randomUUID();
}

/** Same-origin adapter. Session and tenant identity are supplied only by the server. */
export class FetchEnterpriseDashboardClient implements EnterpriseDashboardClient {
  constructor(
    private readonly fetcher: typeof fetch = fetch,
    private readonly root = "/api/enterprise/dashboards",
  ) {}

  async listCatalog(search = ""): Promise<EnterpriseDashboardCatalog> {
    const query = new URLSearchParams({ limit: "500" });
    if (search.trim()) query.set("search", search.trim());
    return this.request<EnterpriseDashboardCatalog>(`?${query.toString()}`);
  }

  getDashboard(dashboardId: string): Promise<StoredDashboard> {
    return this.request<StoredDashboard>(`/${encodeURIComponent(dashboardId)}`);
  }

  readPortlets(
    dashboardId: string,
    filterOverrides?: Array<{ key: string; operator: string; value: unknown }>,
  ): Promise<EnterpriseDashboardRead> {
    return this.request<EnterpriseDashboardRead>(`/${encodeURIComponent(dashboardId)}/read`, {
      method: "POST",
      body: JSON.stringify(filterOverrides === undefined ? {} : { filter_overrides: filterOverrides }),
    });
  }

  setDisplayPreference(dashboardId: string, displayed: boolean, position?: number): Promise<unknown> {
    return this.request(`/${encodeURIComponent(dashboardId)}/display`, {
      method: "PUT",
      body: JSON.stringify({ displayed, ...(position === undefined ? {} : { position }) }),
    });
  }

  createDashboard(payload: { title: string; description: string; context: "enterprise_home" }): Promise<unknown> {
    return this.request("", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey() },
      body: JSON.stringify(payload),
    });
  }

  duplicateDashboard(dashboardId: string, title?: string): Promise<unknown> {
    return this.request(`/${encodeURIComponent(dashboardId)}/duplicate`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey() },
      body: JSON.stringify(title === undefined ? {} : { title }),
    });
  }

  updateDashboard(
    dashboardId: string,
    payload: {
      title: string;
      description: string;
      portlets: EnterpriseDashboardPortlet[];
      filters: Array<{ key: string; operator: string; value: unknown }>;
      restrict_filter_override: boolean;
      max_rows_per_portlet: number;
    },
    expectedRevision: number,
  ): Promise<unknown> {
    return this.request(`/${encodeURIComponent(dashboardId)}`, {
      method: "PATCH",
      body: JSON.stringify({ ...payload, expected_revision: expectedRevision }),
    });
  }

  archiveDashboard(dashboardId: string, expectedRevision: number): Promise<unknown> {
    return this.request(`/${encodeURIComponent(dashboardId)}/archive`, {
      method: "POST",
      body: JSON.stringify({ expected_revision: expectedRevision }),
    });
  }

  listUsers(): Promise<{ users: Array<{ user_id: string; email: string; display_name: string; active: boolean }> }> {
    return this.request("/../users");
  }

  saveFilterOverride(dashboardId: string, filters: EnterpriseDashboardFilter[]): Promise<unknown> {
    return this.request(`/${encodeURIComponent(dashboardId)}/filter-override`, {
      method: "POST",
      body: JSON.stringify({ filters }),
    });
  }

  resetFilterOverride(dashboardId: string): Promise<unknown> {
    return this.request(`/${encodeURIComponent(dashboardId)}/filter-override`, {
      method: "DELETE",
    });
  }

  assignShare(
    dashboardId: string,
    targetType: "user" | "role" | "all_users",
    targetId: string,
    expectedRevision: number,
  ): Promise<unknown> {
    return this.share(dashboardId, "POST", targetType, targetId, expectedRevision);
  }

  revokeShare(
    dashboardId: string,
    targetType: "user" | "role" | "all_users",
    targetId: string,
    expectedRevision: number,
  ): Promise<unknown> {
    return this.share(dashboardId, "DELETE", targetType, targetId, expectedRevision);
  }

  private share(
    dashboardId: string,
    method: "POST" | "DELETE",
    targetType: "user" | "role" | "all_users",
    targetId: string,
    expectedRevision: number,
  ): Promise<unknown> {
    return this.request(`/${encodeURIComponent(dashboardId)}/shares`, {
      method,
      body: JSON.stringify({ target_type: targetType, target_id: targetId, expected_revision: expectedRevision }),
    });
  }

  private async request<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    if (init.body !== undefined) headers.set("Content-Type", "application/json");
    const response = await this.fetcher(`${this.root}${path}`, {
      ...init,
      headers,
      credentials: "same-origin",
      cache: "no-store",
    });
    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    if (!response.ok) {
      const code = payload && typeof payload === "object" && "code" in payload
        ? String((payload as { code: unknown }).code)
        : `HTTP_${response.status}`;
      throw new EnterpriseDashboardHttpError(response.status, code);
    }
    return payload as T;
  }
}
