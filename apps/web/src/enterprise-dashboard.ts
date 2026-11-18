import { FetchEnterpriseDashboardClient } from "./enterprise-dashboard-http-client.js";

export type EnterpriseDashboardRole = "enterprise_admin" | "enterprise_user" | "enterprise_viewer";
export type EnterpriseDashboardVisibility = "private" | "users" | "roles" | "users_and_roles" | "global";
export type EnterprisePortletType = "portfolio-control-snapshot.v1" | "portfolio-decision.v1";
export type EnterpriseDashboardLayout = { x: number; y: number; w: number; h: number };
export type EnterpriseDashboardPortlet = {
  instance_id: string;
  type_id: EnterprisePortletType;
  contract_version: EnterprisePortletType;
  config: { portfolio_id: string; decision_id?: string };
  layout: EnterpriseDashboardLayout;
  title?: string | null;
  hide_title?: boolean;
};
export type EnterpriseDashboardDefinition = {
  contract_version: "cubi-enterprise-dashboard.v1";
  dashboard_id: string;
  tenant_id: string;
  context: "enterprise_home" | "portfolio";
  context_portfolio_id: string | null;
  owner_user_id: string;
  title: string;
  description: string;
  status: "active" | "archived";
  visibility: EnterpriseDashboardVisibility;
  shared_user_ids: string[];
  shared_role_ids: EnterpriseDashboardRole[];
  portlets: EnterpriseDashboardPortlet[];
  filters: Array<{ key: string; operator: string; value: unknown }>;
  revision: number;
  created_at: string;
  updated_at: string | null;
  restrict_filter_override: boolean;
  max_rows_per_portlet: number;
};
export type EnterpriseDashboardCatalogItem = {
  dashboard: EnterpriseDashboardDefinition;
  revision: number;
  display_order: number;
};
export type EnterpriseDashboardCatalog = {
  contract_version: "cubi-enterprise-dashboard-catalog.v1";
  /** Effective tenant policy. Optional only for older v1 servers; default is 12. */
  max_portlets?: number;
  displayed_dashboards: EnterpriseDashboardCatalogItem[];
  available_dashboards: EnterpriseDashboardCatalogItem[];
  read_at: string;
};

export function effectiveDashboardPortletLimit(catalog: Pick<EnterpriseDashboardCatalog, "max_portlets"> | null | undefined): number {
  const value = catalog?.max_portlets;
  return Number.isInteger(value) && typeof value === "number" && value >= 1 && value <= 50 ? value : 12;
}
export type EnterprisePortletRead = {
  instance_id: string;
  type_id: string;
  title: string | null;
  hide_title: boolean;
  source_owner: string;
  required_read_permission: string;
  source_data_mode: string;
  source_snapshot_id: string | null;
  source_revision: string | number | null;
  generated_at: string | null;
  freshness_state: "fresh" | "stale" | "missing" | "unknown";
  data: unknown;
  drill_through_refs: Array<{ type: string; id: string; source_revision: string | number }>;
  filtered_out: boolean;
  row_limit: number;
  truncated: boolean;
};
export type EnterpriseDashboardRead = {
  contract_version: "cubi-enterprise-dashboard-read.v1";
  dashboard: EnterpriseDashboardDefinition;
  filters: Array<{ key: string; operator: string; value: unknown }>;
  portlets: EnterprisePortletRead[];
  read_at: string;
};

export interface EnterpriseDashboardClient {
  listCatalog(search?: string): Promise<EnterpriseDashboardCatalog>;
  getDashboard(dashboardId: string): Promise<{ dashboard: EnterpriseDashboardDefinition; revision: number }>;
  readPortlets(dashboardId: string, filterOverrides?: Array<{ key: string; operator: string; value: unknown }>): Promise<EnterpriseDashboardRead>;
  setDisplayPreference(dashboardId: string, displayed: boolean, position?: number): Promise<unknown>;
  createDashboard(payload: { title: string; description: string; context: "enterprise_home" }): Promise<unknown>;
  duplicateDashboard(dashboardId: string, title?: string): Promise<unknown>;
  updateDashboard(dashboardId: string, payload: {
    title: string;
    description: string;
    portlets: EnterpriseDashboardPortlet[];
    filters: Array<{ key: string; operator: string; value: unknown }>;
    restrict_filter_override: boolean;
    max_rows_per_portlet: number;
  }, expectedRevision: number): Promise<unknown>;
  archiveDashboard(dashboardId: string, expectedRevision: number): Promise<unknown>;
  assignShare(dashboardId: string, targetType: "user" | "role" | "all_users", targetId: string, expectedRevision: number): Promise<unknown>;
  revokeShare(dashboardId: string, targetType: "user" | "role" | "all_users", targetId: string, expectedRevision: number): Promise<unknown>;
  saveFilterOverride(dashboardId: string, filters: EnterpriseDashboardFilter[]): Promise<unknown>;
  resetFilterOverride(dashboardId: string): Promise<unknown>;
  listUsers(): Promise<{ users: Array<{ user_id: string; email: string; display_name: string; active: boolean }> }>;
}

export type EnterpriseDashboardFilter = { key: string; operator: string; value: unknown };

export const ENTERPRISE_DASHBOARD_FILTER_CATALOG: ReadonlyArray<{
  key: string;
  label: string;
  value_kind: "text" | "text_list" | "enum" | "datetime" | "boolean";
  operators: readonly string[];
  options?: readonly string[];
}> = Object.freeze([
  { key: "portfolio_id", label: "Portfolio", value_kind: "text", operators: ["eq"] },
  { key: "project_id", label: "Project", value_kind: "text_list", operators: ["eq", "in"] },
  { key: "project_status", label: "Project status", value_kind: "text_list", operators: ["eq", "in"] },
  { key: "membership_status", label: "Portfolio membership", value_kind: "enum", operators: ["eq", "in"], options: ["included", "on_hold", "excluded"] },
  { key: "decision_status", label: "Decision status", value_kind: "enum", operators: ["eq", "in"], options: ["proposed", "under_review", "approved", "rejected", "implemented", "closed", "cancelled"] },
  { key: "generated_after", label: "Generated after", value_kind: "datetime", operators: ["gte"] },
  { key: "generated_before", label: "Generated before", value_kind: "datetime", operators: ["lte"] },
  { key: "include_stale", label: "Include stale data", value_kind: "boolean", operators: ["eq"] },
]);

export function dashboardFilterDefinition(key: string) {
  return ENTERPRISE_DASHBOARD_FILTER_CATALOG.find((item) => item.key === key);
}

export function authorizedDashboardFilterOptions(
  key: string,
  dashboard: EnterpriseDashboardDefinition,
  read: EnterpriseDashboardRead | null | undefined,
): Array<{ value: string; label: string }> {
  if (key === "portfolio_id") {
    return [...new Set(dashboard.portlets
      .map((portlet) => portlet.config.portfolio_id.trim())
      .filter(Boolean))]
      .sort((a, b) => a.localeCompare(b))
      .map((value) => ({ value, label: value }));
  }
  if (key !== "project_id" || !read) return [];
  const projects = new Map<string, string>();
  for (const portlet of read.portlets) {
    if (!portlet.data || typeof portlet.data !== "object") continue;
    const rows = (portlet.data as { projects?: unknown }).projects;
    if (!Array.isArray(rows)) continue;
    for (const row of rows) {
      if (!row || typeof row !== "object") continue;
      const record = row as Record<string, unknown>;
      const id = typeof record.project_id === "string" ? record.project_id.trim() : "";
      if (!id) continue;
      const name = [record.project_name, record.name].find((value) => typeof value === "string" && value.trim());
      if (!projects.has(id)) projects.set(id, typeof name === "string" ? name.trim() : id);
    }
  }
  return [...projects.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([value, label]) => ({ value, label }));
}

export type EnterpriseDashboardLocale = "en" | "fa";
export type EnterprisePortletState = "ready" | "empty" | "stale" | "missing" | "filtered" | "permission_denied" | "error";

export type EnterpriseDashboardPortletCatalogEntry = {
  type_id: string;
  label: string;
  group: "CUBI Portfolio" | "Personal Information" | "Portfolio Views" | "Project Performance" | "Resources" | "Collaboration" | "Document Review";
  enabled: boolean;
  help_url?: string;
  unavailable_reason?: string;
};

/**
 * V26 reference inventory plus the governed CUBI registrations.
 * A P6 entry is not selectable until its authoritative CUBI source contract,
 * actor authorization and drill-through behavior are implemented and tested.
 */
export const ENTERPRISE_DASHBOARD_PORTLET_CATALOG: ReadonlyArray<EnterpriseDashboardPortletCatalogEntry> = Object.freeze([
  { type_id: "portfolio-control-snapshot.v1", label: "Portfolio Control Snapshot", group: "CUBI Portfolio", enabled: true },
  { type_id: "portfolio-decision.v1", label: "Portfolio Decision", group: "CUBI Portfolio", enabled: true },
  { type_id: "p6.communication-center", label: "Communication Center", group: "Personal Information", enabled: false, help_url: "https://docs.oracle.com/cd/G48897_01/p6help/en/5947.htm", unavailable_reason: "Requires the governed notification and collaboration service." },
  { type_id: "p6.my-activities", label: "My Activities", group: "Personal Information", enabled: false, help_url: "https://docs.oracle.com/cd/G48897_01/p6help/en/5954.htm", unavailable_reason: "Requires assigned-activity reads and activity-level authorization." },
  { type_id: "p6.my-issues", label: "My Issues", group: "Personal Information", enabled: false, help_url: "https://docs.oracle.com/cd/G48897_01/p6help/en/5956.htm", unavailable_reason: "Requires the canonical project-issue read model and permissions." },
  { type_id: "p6.my-projects", label: "My Projects", group: "Personal Information", enabled: false, help_url: "https://docs.oracle.com/cd/G48897_01/p6help/en/6034.htm", unavailable_reason: "Requires the canonical actor-authorized project directory." },
  { type_id: "p6.my-calendar", label: "My Calendar", group: "Personal Information", enabled: false, help_url: "https://docs.oracle.com/cd/G48897_01/p6help/en/5946.htm", unavailable_reason: "Requires the user calendar and assigned activity read contract." },
  { type_id: "p6.my-risks", label: "My Risks", group: "Personal Information", enabled: false, help_url: "https://docs.oracle.com/cd/G48897_01/p6help/en/5958.htm", unavailable_reason: "Requires the canonical project-risk read model and project authorization." },
  { type_id: "p6.portfolio-view", label: "Portfolio View", group: "Portfolio Views", enabled: false, help_url: "https://docs.oracle.com/cd/G48897_01/p6help/en/5959.htm", unavailable_reason: "Requires approved scorecard, bubble, pie and histogram view contracts." },
  { type_id: "p6.earned-value-performance", label: "Earned Value Performance", group: "Project Performance", enabled: false, help_url: "https://docs.oracle.com/cd/G48897_01/p6help/en/5950.htm", unavailable_reason: "Must consume Engineering-owned published EVM facts; no Enterprise recalculation." },
  { type_id: "p6.schedule-performance", label: "Schedule Performance", group: "Project Performance", enabled: false, help_url: "https://docs.oracle.com/cd/G48897_01/p6help/en/5968.htm", unavailable_reason: "Must consume Engineering-owned published schedule facts." },
  { type_id: "p6.index-performance", label: "Index Performance", group: "Project Performance", enabled: false, help_url: "https://docs.oracle.com/cd/G48897_01/p6help/en/5951.htm", unavailable_reason: "Must consume Engineering-owned CPI/SPI/TCPI facts." },
  { type_id: "p6.project-statistics", label: "Project Statistics", group: "Project Performance", enabled: false, help_url: "https://docs.oracle.com/cd/G48897_01/p6help/en/6041.htm", unavailable_reason: "Requires summarized project/WBS fields and freshness metadata." },
  { type_id: "p6.project-health", label: "Project Health", group: "Project Performance", enabled: false, help_url: "https://docs.oracle.com/cd/G48897_01/p6help/en/5962.htm", unavailable_reason: "Requires the canonical project health and threshold read model." },
  { type_id: "p6.project-notebooks", label: "Project Notebooks", group: "Project Performance", enabled: false, help_url: "https://docs.oracle.com/cd/G48897_01/p6help/en/5964.htm", unavailable_reason: "Requires authorized project notebook/topic reads." },
  { type_id: "p6.project-gantt", label: "Project Gantt Chart", group: "Project Performance", enabled: false, help_url: "https://docs.oracle.com/cd/G48897_01/p6help/en/6037.htm", unavailable_reason: "Requires a read-only multi-project Gantt projection over Engineering schedules." },
  { type_id: "p6.open-resource-requests", label: "Open Requests for Resources", group: "Resources", enabled: false, help_url: "https://docs.oracle.com/cd/G48897_01/p6help/en/5935.htm", unavailable_reason: "Requires resource request read authorization and a separate assignment action boundary." },
  { type_id: "p6.document-review", label: "Document Review", group: "Document Review", enabled: false, help_url: "https://docs.oracle.com/cd/G48897_01/p6help/en/44954.htm", unavailable_reason: "Requires the governed document repository and review workflow." },
]);

export function orderDashboardCatalog(items: readonly EnterpriseDashboardCatalogItem[]): EnterpriseDashboardCatalogItem[] {
  return [...items].sort((a, b) =>
    a.display_order - b.display_order
    || a.dashboard.title.localeCompare(b.dashboard.title)
    || a.dashboard.dashboard_id.localeCompare(b.dashboard.dashboard_id),
  );
}

/** Resolve a tab move against the exact ordered collection rendered in the Displayed section. */
export type EnterpriseDashboardShareAccount = { user_id: string; email: string; display_name: string; active: boolean };

export function dashboardShareAccountOptions(
  accounts: readonly EnterpriseDashboardShareAccount[],
  query: string,
  sharedUserIds: readonly string[],
): EnterpriseDashboardShareAccount[] {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const shared = new Set(sharedUserIds);
  return accounts.filter((account) => account.active && !shared.has(account.user_id)).filter((account) =>
    !normalizedQuery || `${account.display_name} ${account.email} ${account.user_id}`.toLocaleLowerCase().includes(normalizedQuery));
}

export function dashboardDisplayMoveTarget(
  displayedItems: readonly EnterpriseDashboardCatalogItem[],
  dashboardId: string,
  direction: "up" | "down",
): number | null {
  const ordered = orderDashboardCatalog(displayedItems);
  const index = ordered.findIndex((item) => item.dashboard.dashboard_id === dashboardId);
  if (index < 0) return null;
  const target = index + (direction === "up" ? -1 : 1);
  return target < 0 || target >= ordered.length ? null : target;
}

export function moveDashboardPortletHorizontally(
  portlets: readonly EnterpriseDashboardPortlet[],
  index: number,
  direction: "left" | "right",
): EnterpriseDashboardPortlet[] {
  if (!Number.isInteger(index) || index < 0 || index >= portlets.length) return portlets.map((item) => ({ ...item, layout: { ...item.layout } }));
  const current = portlets[index];
  if (current.layout.w !== 6) return portlets.map((item) => ({ ...item, layout: { ...item.layout } }));
  const targetX = direction === "left" ? 0 : 6;
  if (current.layout.x === targetX) return portlets.map((item) => ({ ...item, layout: { ...item.layout } }));
  const overlaps = (a: EnterpriseDashboardLayout, b: EnterpriseDashboardLayout): boolean =>
    a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
  const candidate = { ...current.layout, x: targetX };
  const collisionIndex = portlets.findIndex((item, itemIndex) => itemIndex !== index && overlaps(candidate, item.layout));
  const result = portlets.map((item) => ({ ...item, layout: { ...item.layout } }));
  if (collisionIndex >= 0) {
    const other = result[collisionIndex];
    if (other.layout.w !== 6 || other.layout.x !== targetX) return result;
    other.layout.x = current.layout.x;
  }
  result[index].layout.x = targetX;
  return validateDashboardLayout(result) ? result : portlets.map((item) => ({ ...item, layout: { ...item.layout } }));
}

export function moveDashboardPortletVertically(
  portlets: readonly EnterpriseDashboardPortlet[],
  index: number,
  direction: "up" | "down",
): EnterpriseDashboardPortlet[] {
  const clone = (): EnterpriseDashboardPortlet[] => portlets.map((item) => ({ ...item, layout: { ...item.layout } }));
  if (!Number.isInteger(index) || index < 0 || index >= portlets.length) return clone();
  const current = portlets[index];
  const targetY = current.layout.y + (direction === "up" ? -current.layout.h : current.layout.h);
  if (targetY < 0 || targetY + current.layout.h > 100) return clone();
  const candidate = { ...current.layout, y: targetY };
  const overlaps = (a: EnterpriseDashboardLayout, b: EnterpriseDashboardLayout): boolean =>
    a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
  const collisionIndex = portlets.findIndex((item, itemIndex) => itemIndex !== index && overlaps(candidate, item.layout));
  const result = clone();
  if (collisionIndex >= 0) {
    const other = result[collisionIndex];
    if (other.layout.x !== current.layout.x || other.layout.w !== current.layout.w || other.layout.h !== current.layout.h) return result;
    other.layout.y = current.layout.y;
  }
  result[index].layout.y = targetY;
  return validateDashboardLayout(result) ? result : clone();
}

export function moveDashboardPortletToPosition(
  portlets: readonly EnterpriseDashboardPortlet[],
  fromIndex: number,
  toIndex: number,
): EnterpriseDashboardPortlet[] {
  const clone = (): EnterpriseDashboardPortlet[] => portlets.map((item) => ({ ...item, layout: { ...item.layout } }));
  if (!Number.isInteger(fromIndex) || !Number.isInteger(toIndex)
    || fromIndex < 0 || toIndex < 0 || fromIndex >= portlets.length || toIndex >= portlets.length
    || fromIndex === toIndex) return clone();
  const result = clone();
  const source = result[fromIndex];
  const target = result[toIndex];
  const sourcePosition = { x: source.layout.x, y: source.layout.y };
  source.layout.x = target.layout.x;
  source.layout.y = target.layout.y;
  target.layout.x = sourcePosition.x;
  target.layout.y = sourcePosition.y;
  return validateDashboardLayout(result) ? result : clone();
}

export function reorderDashboardPortlets<T>(items: readonly T[], fromIndex: number, toIndex: number): T[] {
  if (!Number.isInteger(fromIndex) || !Number.isInteger(toIndex) || fromIndex < 0 || toIndex < 0 || fromIndex >= items.length || toIndex >= items.length) return [...items];
  const result = [...items];
  const [moved] = result.splice(fromIndex, 1);
  result.splice(toIndex, 0, moved);
  return result;
}

export function supportedDashboardPortlets(items: readonly EnterpriseDashboardPortlet[]): EnterpriseDashboardPortlet[] {
  const supported = new Set(ENTERPRISE_DASHBOARD_PORTLET_CATALOG.filter((item) => item.enabled).map((item) => item.type_id));
  return items.filter((item) => supported.has(item.type_id));
}

export function validateDashboardLayout(portlets: readonly EnterpriseDashboardPortlet[], maxPortlets = 12): boolean {
  if (!Number.isInteger(maxPortlets) || maxPortlets < 1 || maxPortlets > 50 || portlets.length > maxPortlets) return false;
  for (let i = 0; i < portlets.length; i += 1) {
    const a = portlets[i].layout;
    if (![a.x, a.y, a.w, a.h].every(Number.isInteger)
      || ![0, 6].includes(a.x) || ![6, 12].includes(a.w)
      || a.y < 0 || a.h < 1 || a.x + a.w > 12 || a.y + a.h > 100
      || (a.x === 6 && a.w !== 6)) return false;
    for (let j = i + 1; j < portlets.length; j += 1) {
      const b = portlets[j].layout;
      const separated = a.x + a.w <= b.x || b.x + b.w <= a.x
        || a.y + a.h <= b.y || b.y + b.h <= a.y;
      if (!separated) return false;
    }
  }
  return true;
}

export function displaySummaryMetric(summary: Record<string, unknown> | undefined, key: string): string {
  const value = summary?.[key];
  return typeof value === "number" && Number.isFinite(value) ? String(value) : "—";
}

export function mapEnterprisePortletState(
  portlet: Pick<EnterprisePortletRead, "data" | "freshness_state" | "filtered_out">,
  errorCode?: string,
): EnterprisePortletState {
  if (errorCode === "PROJECT_READ_FORBIDDEN" || errorCode === "DASHBOARD_SOURCE_ACCESS_DENIED") return "permission_denied";
  if (errorCode) return "error";
  if (portlet.freshness_state === "missing" || portlet.data === null) return "missing";
  if (portlet.filtered_out) return "filtered";
  if (portlet.freshness_state === "stale") return "stale";
  if (portlet.data && typeof portlet.data === "object" && "projects" in portlet.data
    && Array.isArray((portlet.data as { projects?: unknown }).projects)
    && (portlet.data as { projects: unknown[] }).projects.length === 0) return "empty";
  return "ready";
}

const COPY = {
  en: {
    eyebrow: "CUBI ENTERPRISE", title: "Dashboards", subtitle: "Portfolio and enterprise views from authorized source records.",
    create: "New dashboard", search: "Search dashboards", displayed: "Displayed", available: "Available",
    open: "Open", hide: "Hide", show: "Show", duplicate: "Duplicate", manage: "Customize", archive: "Archive",
    refresh: "Refresh", expand: "Expand", collapse: "Collapse", expandAll: "Expand All", collapseAll: "Collapse All", maximize: "Maximize", restore: "Restore",
    close: "Close", help: "Help", print: "Print", noDashboards: "No dashboards are available.", noPortlets: "This dashboard has no portlets.",
    loading: "Loading source data…", stale: "Source data is stale.", missing: "Source data is unavailable.",
    filtered: "No source rows match the current filters.", denied: "You do not have permission to view this source.",
    error: "The source could not be loaded.", empty: "No project records in this snapshot.", truncated: "Rows limited for display.",
    general: "General", content: "Content", layout: "Layout", access: "Access", save: "Save and Close", cancel: "Cancel",
    name: "Dashboard name", description: "Description", maxRows: "Maximum rows per portlet", filterLock: "Restrict viewer filter overrides",
    addPortlet: "Add portlet", portfolioId: "Portfolio ID", decisionId: "Decision ID", portletTitle: "Portlet title",
    width: "Width", narrow: "Narrow", wide: "Wide", remove: "Remove", visibility: "Visibility",
    private: "Private", users: "Selected users", roles: "Enterprise roles", users_and_roles: "Users and roles", global: "All Enterprise users",
    accessNote: "Sharing changes apply immediately through the authorized access service; closing this dialog does not undo them. Dashboard sharing never grants access to underlying source data.",
    owner: "Owner", revision: "Revision", unsupported: "This portlet type is not enabled in this release.",
    drill: "Open source record", projects: "Projects", status: "Status", membership: "Membership", total: "Total",
    included: "Included", onHold: "On hold", excluded: "Excluded", noData: "No source data was returned.",
    archiveConfirm: "Archive this dashboard?", createName: "Enter a dashboard name.", createMode: "Start from", blankDashboard: "Blank dashboard", copyExisting: "Copy existing dashboard", defaultTemplate: "Default Dashboard template", defaultTemplateUnavailable: "The Default Dashboard template is not configured in this release.", sourceDashboard: "Source dashboard", createAction: "Create dashboard",
    projectFilter: "Filter by", applyFilter: "Apply filters", resetFilter: "Reset filters", filterDialog: "Filter by", addFilter: "Add condition", field: "Field", operator: "Operator", value: "Value", removeFilter: "Remove", noFilters: "No filter conditions.", filterValueHint: "Separate multiple values with commas.", filterScopeConflict: "Choose either a portfolio or project filter, not both.", saveMyFilter: "Save as my filter", resetMyFilter: "Reset to dashboard default", filterPortfolio: "Portfolio", filterProject: "Project", filterProjectStatus: "Project status", filterMembership: "Portfolio membership", filterDecisionStatus: "Decision status", filterGeneratedAfter: "Generated after", filterGeneratedBefore: "Generated before", filterIncludeStale: "Include stale data", opEq: "Equals", opIn: "Is one of", opGte: "On or after", opLte: "On or before", statusIncluded: "Included", statusOnHold: "On hold", statusExcluded: "Excluded", decisionProposed: "Proposed", decisionUnderReview: "Under review", decisionApproved: "Approved", decisionRejected: "Rejected", decisionImplemented: "Implemented", decisionClosed: "Closed", decisionCancelled: "Cancelled",
    moveUp: "Move up", moveDown: "Move down", moveLeft: "Move left", moveRight: "Move right", moveDashboardUp: "Move dashboard tab up", moveDashboardDown: "Move dashboard tab down", filterLocked: "The dashboard owner has restricted filter overrides.", defaultFilter: "Dashboard default filter", useCurrentAsDefault: "Use current selection as dashboard default", clearDefaultFilter: "Clear dashboard default filter", accessUserId: "User ID", accessAddUser: "Add user", accessSearchUsers: "Search user accounts", accessSelectUser: "Select an account", accessDirectoryUnavailable: "Account search is unavailable for this session; use the tenant-validated user ID field.", accessAddRole: "Add role", accessRole: "Enterprise role", accessUsers: "Shared users", accessRoles: "Shared roles", accessGlobal: "Share with all Enterprise users", accessRevokeGlobal: "Revoke all-user access", accessDirectoryPending: "Only active accounts in your tenant are listed. If directory access is unavailable, enter a user ID; the server verifies tenant membership.", accessNoUsers: "No individual users are shared.", accessNoRoles: "No roles are shared.", accessSaveError: "The access change could not be saved.", roleAdmin: "Enterprise administrator", roleUser: "Enterprise user", roleViewer: "Enterprise viewer",
  },
  fa: {
    eyebrow: "کوبی سازمانی", title: "داشبوردها", subtitle: "نماهای سازمانی و سبد پروژه بر پایه داده‌های مجاز و معتبر.",
    create: "داشبورد جدید", search: "جستجوی داشبوردها", displayed: "نمایش‌داده‌شده", available: "در دسترس",
    open: "باز کردن", hide: "مخفی‌کردن", show: "نمایش", duplicate: "تکثیر", manage: "سفارشی‌سازی", archive: "بایگانی",
    refresh: "تازه‌سازی", expand: "بازکردن", collapse: "بستن", expandAll: "بازکردن همه", collapseAll: "بستن همه", maximize: "بزرگ‌نمایی", restore: "بازگردانی",
    close: "بستن", help: "راهنما", print: "چاپ", noDashboards: "داشبوردی در دسترس نیست.", noPortlets: "این داشبورد پورلت ندارد.",
    loading: "دریافت داده منبع…", stale: "داده منبع قدیمی است.", missing: "داده منبع در دسترس نیست.",
    filtered: "رکوردی با فیلترهای فعلی مطابقت ندارد.", denied: "مجوز مشاهده این منبع را ندارید.",
    error: "دریافت منبع انجام نشد.", empty: "رکورد پروژه‌ای در این تصویر وجود ندارد.", truncated: "تعداد ردیف‌ها برای نمایش محدود شده است.",
    general: "عمومی", content: "محتوا", layout: "چیدمان", access: "دسترسی", save: "ذخیره و بستن", cancel: "انصراف",
    name: "نام داشبورد", description: "شرح", maxRows: "حداکثر ردیف هر پورلت", filterLock: "محدودکردن تغییر فیلتر توسط بیننده",
    addPortlet: "افزودن پورلت", portfolioId: "شناسه سبد", decisionId: "شناسه تصمیم", portletTitle: "عنوان پورلت",
    width: "عرض", narrow: "باریک", wide: "عریض", remove: "حذف", visibility: "سطح دسترسی",
    private: "خصوصی", users: "کاربران منتخب", roles: "نقش‌های سازمانی", users_and_roles: "کاربران و نقش‌ها", global: "همه کاربران سازمان",
    accessNote: "تغییرات اشتراک بلافاصله از مسیر سرویس مجاز اعمال می‌شوند و بستن پنجره آن‌ها را بازنمی‌گرداند. اشتراک داشبورد مجوز دسترسی به داده‌های منبع ایجاد نمی‌کند.",
    owner: "مالک", revision: "بازبینی", unsupported: "این نوع پورلت در این نسخه فعال نیست.",
    drill: "بازکردن رکورد منبع", projects: "پروژه‌ها", status: "وضعیت", membership: "عضویت", total: "مجموع",
    included: "داخل سبد", onHold: "متوقف", excluded: "خارج از سبد", noData: "داده‌ای از منبع دریافت نشد.",
    archiveConfirm: "این داشبورد بایگانی شود؟", createName: "نام داشبورد را وارد کنید.", createMode: "ایجاد بر پایه", blankDashboard: "داشبورد خالی", copyExisting: "تکثیر داشبورد موجود", defaultTemplate: "الگوی داشبورد پیش‌فرض", defaultTemplateUnavailable: "الگوی داشبورد پیش‌فرض در این نسخه پیکربندی نشده است.", sourceDashboard: "داشبورد مبنا", createAction: "ایجاد داشبورد",
    projectFilter: "فیلتر بر اساس", applyFilter: "اعمال فیلترها", resetFilter: "پاک‌کردن فیلترها", filterDialog: "فیلتر بر اساس", addFilter: "افزودن شرط", field: "فیلد", operator: "عملگر", value: "مقدار", removeFilter: "حذف", noFilters: "شرط فیلتری وجود ندارد.", filterValueHint: "برای چند مقدار از ویرگول استفاده کنید.", filterScopeConflict: "فیلتر سبد پروژه و فیلتر پروژه را هم‌زمان انتخاب نکنید.", saveMyFilter: "ذخیره به‌عنوان فیلتر من", resetMyFilter: "بازنشانی به فیلتر پیش‌فرض داشبورد", filterPortfolio: "سبد پروژه", filterProject: "پروژه", filterProjectStatus: "وضعیت پروژه", filterMembership: "عضویت در سبد", filterDecisionStatus: "وضعیت تصمیم", filterGeneratedAfter: "ایجادشده پس از", filterGeneratedBefore: "ایجادشده پیش از", filterIncludeStale: "شامل داده قدیمی", opEq: "برابر با", opIn: "یکی از", opGte: "در یا پس از", opLte: "در یا پیش از", statusIncluded: "داخل سبد", statusOnHold: "متوقف", statusExcluded: "خارج از سبد", decisionProposed: "پیشنهادشده", decisionUnderReview: "در دست بررسی", decisionApproved: "تأییدشده", decisionRejected: "ردشده", decisionImplemented: "اجراشده", decisionClosed: "بسته", decisionCancelled: "لغوشده",
    moveUp: "انتقال به بالا", moveDown: "انتقال به پایین", moveLeft: "انتقال به چپ", moveRight: "انتقال به راست", moveDashboardUp: "انتقال تب داشبورد به بالا", moveDashboardDown: "انتقال تب داشبورد به پایین", filterLocked: "مالک داشبورد تغییر فیلتر را محدود کرده است.", defaultFilter: "فیلتر پیش‌فرض داشبورد", useCurrentAsDefault: "استفاده از انتخاب فعلی به‌عنوان فیلتر پیش‌فرض", clearDefaultFilter: "پاک‌کردن فیلتر پیش‌فرض داشبورد", accessUserId: "شناسه کاربر", accessAddUser: "افزودن کاربر", accessSearchUsers: "جستجوی حساب‌های کاربری", accessSelectUser: "انتخاب حساب", accessDirectoryUnavailable: "جستجوی حساب برای این نشست در دسترس نیست؛ از شناسه کاربری با اعتبارسنجی سازمان استفاده کنید.", accessAddRole: "افزودن نقش", accessRole: "نقش سازمانی", accessUsers: "کاربران دارای اشتراک", accessRoles: "نقش‌های دارای اشتراک", accessGlobal: "اشتراک با همه کاربران سازمان", accessRevokeGlobal: "لغو دسترسی همگانی", accessDirectoryPending: "فقط حساب‌های فعال همین سازمان نمایش داده می‌شوند. اگر فهرست در دسترس نبود شناسه کاربر را وارد کنید؛ سرور عضویت سازمانی را اعتبارسنجی می‌کند.", accessNoUsers: "اشتراک کاربری جداگانه‌ای وجود ندارد.", accessNoRoles: "اشتراک نقشی وجود ندارد.", accessSaveError: "ذخیره تغییر دسترسی انجام نشد.", roleAdmin: "مدیر سازمانی", roleUser: "کاربر سازمانی", roleViewer: "بیننده سازمانی",
  },
} as const;

type Copy = typeof COPY[keyof typeof COPY];
type MountOptions = {
  locale?: EnterpriseDashboardLocale;
  onDrillThrough?: (reference: EnterprisePortletRead["drill_through_refs"][number]) => void;
};

function node<K extends keyof HTMLElementTagNameMap>(tag: K, className?: string, text?: string): HTMLElementTagNameMap[K] {
  const result = document.createElement(tag);
  if (className) result.className = className;
  if (text !== undefined) result.textContent = text;
  return result;
}
function button(label: string, action: () => void | Promise<void>, className = "ced-button"): HTMLButtonElement {
  const result = node("button", className, label);
  result.type = "button";
  result.addEventListener("click", () => { void action(); });
  return result;
}
function dashboardOf(item: EnterpriseDashboardCatalogItem): EnterpriseDashboardDefinition { return item.dashboard; }
function portletLabel(type: string): string {
  return ENTERPRISE_DASHBOARD_PORTLET_CATALOG.find((item) => item.type_id === type)?.label ?? type;
}
function installDashboardStyles(): void {
  if (document.getElementById("cubi-enterprise-dashboard-styles")) return;
  const style = node("style");
  style.id = "cubi-enterprise-dashboard-styles";
  style.textContent = `
    .ced-shell{font:inherit;color:var(--cp-text,#17202a);background:var(--cp-bg,#f5f7fa);min-height:100%;padding:24px}
    .ced-head,.ced-toolbar,.ced-row,.ced-portlet-head,.ced-tabs{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
    .ced-head{justify-content:space-between;margin-bottom:18px}.ced-eyebrow{color:var(--cp-blue,#1976d2);font-size:11px;font-weight:800;letter-spacing:.12em}
    .ced-title{margin:3px 0;font-size:25px;color:var(--cp-navy,#0f2747)}.ced-subtitle,.ced-muted{color:var(--cp-muted,#667085)}
    .ced-button{border:1px solid var(--cp-border,#d9e0e7);background:#fff;border-radius:8px;padding:8px 12px;cursor:pointer}
    .ced-button.primary{background:var(--cp-navy,#0f2747);color:#fff;border-color:var(--cp-navy,#0f2747)}
    .ced-button:disabled{opacity:.45;cursor:not-allowed}.ced-tabs{border-bottom:1px solid var(--cp-border,#d9e0e7);margin:14px 0;padding-bottom:8px}
    .ced-panel,.ced-card{background:#fff;border:1px solid var(--cp-border,#d9e0e7);border-radius:12px;padding:16px}
    .ced-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:14px}.ced-card h3{margin:0 0 6px}
    .ced-row{justify-content:space-between}.ced-section{margin:22px 0}.ced-input,.ced-select{border:1px solid var(--cp-border,#d9e0e7);border-radius:8px;padding:9px;background:#fff;max-width:100%}
    .ced-portlet{background:#fff;border:1px solid var(--cp-border,#d9e0e7);border-radius:12px;overflow:hidden;margin:12px 0}
    .ced-portlet-head{padding:10px 14px;background:#f7fafd;border-bottom:1px solid var(--cp-border,#d9e0e7);justify-content:space-between}
    .ced-portlet-body{padding:14px;overflow:auto}.ced-maximized{position:fixed;inset:12px;z-index:1000;background:#fff;overflow:auto}.ced-badge{display:inline-block;border-radius:99px;padding:3px 8px;background:#edf3f9;color:var(--cp-navy,#0f2747);font-size:12px}
    .ced-table{width:100%;border-collapse:collapse}.ced-table th,.ced-table td{text-align:start;border-bottom:1px solid #e6e9ee;padding:8px;font-size:13px}
    .ced-dialog{border:0;border-radius:14px;width:min(820px,94vw);max-height:90vh;padding:0;box-shadow:0 18px 70px #0f274733}.ced-dialog::backdrop{background:#081a2f77}
    .ced-dialog-inner{padding:20px;overflow:auto;max-height:90vh}.ced-form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
    .ced-field{display:flex;flex-direction:column;gap:5px}.ced-warning{padding:10px;border-radius:8px;background:#fff6e6;color:#805500}
    .ced-error{padding:10px;border-radius:8px;background:#fff0f0;color:#9d2727}
    @media(max-width:640px){.ced-shell{padding:14px}.ced-head{align-items:flex-start}.ced-title{font-size:21px}}
  `;
  document.head.append(style);
}

export function mountEnterpriseDashboardFromHttp(container: HTMLElement, options: MountOptions = {}): Promise<void> {
  return mountEnterpriseDashboard(container, new FetchEnterpriseDashboardClient(), options);
}

export async function mountEnterpriseDashboard(
  container: HTMLElement,
  client: EnterpriseDashboardClient,
  options: MountOptions = {},
): Promise<void> {
  const locale = options.locale ?? (navigator.language.toLowerCase().startsWith("fa") ? "fa" : "en");
  const t: Copy = COPY[locale];
  const filterLabel = (key: string): string => {
    const labels: Record<string, string> = {
      portfolio_id: t.filterPortfolio, project_id: t.filterProject, project_status: t.filterProjectStatus,
      membership_status: t.filterMembership, decision_status: t.filterDecisionStatus,
      generated_after: t.filterGeneratedAfter, generated_before: t.filterGeneratedBefore, include_stale: t.filterIncludeStale,
    };
    return labels[key] ?? key;
  };
  const operatorLabel = (operator: string): string => {
    const labels: Record<string, string> = { eq: t.opEq, in: t.opIn, gte: t.opGte, lte: t.opLte };
    return labels[operator] ?? operator;
  };
  const roleLabel = (role: string): string => {
    const labels: Record<string, string> = {
      enterprise_admin: t.roleAdmin,
      enterprise_user: t.roleUser,
      enterprise_viewer: t.roleViewer,
    };
    return labels[role] ?? role;
  };
  const filterValueLabel = (value: string): string => {
    const labels: Record<string, string> = {
      included: t.statusIncluded, on_hold: t.statusOnHold, excluded: t.statusExcluded,
      proposed: t.decisionProposed, under_review: t.decisionUnderReview, approved: t.decisionApproved,
      rejected: t.decisionRejected, implemented: t.decisionImplemented, closed: t.decisionClosed,
      cancelled: t.decisionCancelled,
    };
    return labels[value] ?? value;
  };
  installDashboardStyles();
  document.documentElement.lang = locale;
  document.documentElement.dir = locale === "fa" ? "rtl" : "ltr";
  document.title = `CUBI Enterprise · ${t.title}`;
  container.replaceChildren();
  const shell = node("main", "ced-shell");
  shell.dir = locale === "fa" ? "rtl" : "ltr";
  const head = node("header", "ced-head");
  const heading = node("div");
  heading.append(node("div", "ced-eyebrow", t.eyebrow), node("h1", "ced-title", t.title), node("p", "ced-subtitle", t.subtitle));
  const headActions = node("div", "ced-toolbar");
  const refreshAll = button(t.refresh, async () => { await loadCatalog(); });
  const create = button(t.create, () => createDashboard(), "ced-button primary");
  headActions.append(refreshAll, create);
  head.append(heading, headActions);
  const status = node("p", "ced-muted");
  const tabs = node("nav", "ced-tabs");
  const content = node("section");
  shell.append(head, status, tabs, content);
  container.append(shell);

  let catalog: EnterpriseDashboardCatalog | null = null;
  let activeDashboardId: string | null = null;
  let activeRead: EnterpriseDashboardRead | null = null;
  let activeDefinition: EnterpriseDashboardDefinition | null = null;
  let searchTerm = "";
  let activeFilterOverrides: EnterpriseDashboardFilter[] | null = null;

  async function loadCatalog(): Promise<EnterpriseDashboardCatalog | null> {
    status.textContent = t.loading;
    try {
      catalog = await client.listCatalog(searchTerm);
      renderCatalog();
      status.textContent = "";
      if (activeDashboardId && catalog.displayed_dashboards.some((item) => item.dashboard.dashboard_id === activeDashboardId)) {
        await openDashboard(activeDashboardId);
      }
      return catalog;
    } catch {
      status.textContent = t.error;
      content.replaceChildren(node("div", "ced-error", t.error));
      return null;
    }
  }
  function renderTabs(): void {
    tabs.replaceChildren();
    if (!catalog) return;
    for (const item of orderDashboardCatalog(catalog.displayed_dashboards)) {
      const tab = button(item.dashboard.title, () => openDashboard(item.dashboard.dashboard_id), "ced-button");
      if (item.dashboard.dashboard_id === activeDashboardId) tab.setAttribute("aria-current", "page");
      tabs.append(tab);
    }
  }
  function renderCatalog(): void {
    renderTabs();
    content.replaceChildren();
    const search = node("input", "ced-input");
    search.type = "search";
    search.placeholder = t.search;
    search.value = searchTerm;
    search.setAttribute("aria-label", t.search);
    search.addEventListener("change", () => { searchTerm = search.value; void loadCatalog(); });
    const searchRow = node("div", "ced-toolbar");
    searchRow.append(search);
    content.append(searchRow);
    if (!catalog) return;
    const groups: Array<[string, EnterpriseDashboardCatalogItem[], boolean]> = [
      [t.displayed, orderDashboardCatalog(catalog.displayed_dashboards), true],
      [t.available, orderDashboardCatalog(catalog.available_dashboards), false],
    ];
    for (const [label, items, displayed] of groups) {
      const section = node("section", "ced-section");
      section.append(node("h2", "", label));
      if (!items.length) section.append(node("p", "ced-muted", t.noDashboards));
      const grid = node("div", "ced-grid");
      for (const [itemIndex, item] of items.entries()) {
        const dashboard = dashboardOf(item);
        const card = node("article", "ced-card");
        card.append(node("h3", "", dashboard.title), node("p", "ced-muted", dashboard.description || "—"));
        const meta = node("div", "ced-row");
        meta.append(node("span", "ced-badge", dashboard.visibility), node("span", "ced-muted", `${t.revision} ${item.revision}`));
        const actions = node("div", "ced-toolbar");
        actions.append(button(t.open, () => openDashboard(dashboard.dashboard_id)));
        actions.append(button(displayed ? t.hide : t.show, async () => {
          await client.setDisplayPreference(dashboard.dashboard_id, !displayed, displayed ? undefined : catalog!.displayed_dashboards.length);
          await loadCatalog();
        }));
        if (displayed) {
          const moveUp = button(t.moveDashboardUp, async () => {
            const target = dashboardDisplayMoveTarget(items, dashboard.dashboard_id, "up");
            if (target === null) return;
            await client.setDisplayPreference(dashboard.dashboard_id, true, target);
            await loadCatalog();
          });
          const moveDown = button(t.moveDashboardDown, async () => {
            const target = dashboardDisplayMoveTarget(items, dashboard.dashboard_id, "down");
            if (target === null) return;
            await client.setDisplayPreference(dashboard.dashboard_id, true, target);
            await loadCatalog();
          });
          moveUp.disabled = dashboardDisplayMoveTarget(items, dashboard.dashboard_id, "up") === null;
          moveDown.disabled = dashboardDisplayMoveTarget(items, dashboard.dashboard_id, "down") === null;
          actions.append(moveUp, moveDown);
        }
        actions.append(button(t.duplicate, async () => { await client.duplicateDashboard(dashboard.dashboard_id); await loadCatalog(); }));
        actions.append(button(t.archive, async () => {
          if (!window.confirm(t.archiveConfirm)) return;
          await client.archiveDashboard(dashboard.dashboard_id, item.revision);
          if (activeDashboardId === dashboard.dashboard_id) activeDashboardId = null;
          await loadCatalog();
        }));
        card.append(meta, actions);
        grid.append(card);
      }
      section.append(grid);
      content.append(section);
    }
  }
  async function createDashboard(): Promise<void> {
    if (!catalog) return;
    const dialog = node("dialog", "ced-dialog");
    const inner = node("div", "ced-dialog-inner");
    inner.append(node("h2", "", t.create));
    const titleInput = input("new-dashboard-title", "");
    titleInput.maxLength = 200;
    titleInput.placeholder = t.createName;
    const mode = node("select", "ced-select");
    const blankOption = node("option", "", t.blankDashboard);
    blankOption.value = "blank";
    mode.append(blankOption);
    const copyOption = node("option", "", t.copyExisting);
    copyOption.value = "existing";
    mode.append(copyOption);
    const defaultOption = node("option", "", t.defaultTemplate);
    defaultOption.value = "default";
    defaultOption.disabled = true;
    defaultOption.title = t.defaultTemplateUnavailable;
    mode.append(defaultOption);
    const sourceSelect = node("select", "ced-select");
    const emptySource = node("option", "", t.sourceDashboard);
    emptySource.value = "";
    sourceSelect.append(emptySource);
    const accessible = new Map<string, EnterpriseDashboardCatalogItem>();
    for (const item of [...catalog.displayed_dashboards, ...catalog.available_dashboards]) {
      accessible.set(item.dashboard.dashboard_id, item);
    }
    for (const item of orderDashboardCatalog([...accessible.values()])) {
      const option = node("option", "", item.dashboard.title);
      option.value = item.dashboard.dashboard_id;
      sourceSelect.append(option);
    }
    const sourceField = field(t.sourceDashboard, sourceSelect);
    sourceField.hidden = true;
    mode.addEventListener("change", () => { sourceField.hidden = mode.value !== "existing"; });
    const footer = node("div", "ced-row");
    footer.append(button(t.createAction, async () => {
      const title = titleInput.value.trim();
      if (!title) {
        status.textContent = t.createName;
        return;
      }
      try {
        status.textContent = t.loading;
        if (mode.value === "existing") {
          if (!sourceSelect.value) {
            status.textContent = t.sourceDashboard;
            return;
          }
          await client.duplicateDashboard(sourceSelect.value, title);
        } else if (mode.value === "blank") {
          await client.createDashboard({ title, description: "", context: "enterprise_home" });
        } else {
          return;
        }
        dialog.close();
        dialog.remove();
        await loadCatalog();
      } catch {
        status.textContent = t.error;
      }
    }, "ced-button primary"));
    footer.append(button(t.cancel, () => { dialog.close(); dialog.remove(); }));
    inner.append(field(t.name, titleInput), field(t.createMode, mode), sourceField, node("p", "ced-muted", t.defaultTemplateUnavailable), footer);
    dialog.append(inner);
    container.append(dialog);
    dialog.showModal();
    titleInput.focus();
  }
  async function openDashboard(dashboardId: string): Promise<void> {
    activeDashboardId = dashboardId;
    status.textContent = t.loading;
    renderTabs();
    try {
      const [stored, read] = await Promise.all([client.getDashboard(dashboardId), client.readPortlets(dashboardId)]);
      activeDefinition = stored.dashboard;
      activeFilterOverrides = null;
      activeRead = read;
      status.textContent = "";
      renderViewer();
    } catch (error) {
      const code = error instanceof Error ? error.message : "UNKNOWN";
      status.textContent = code.includes("FORBIDDEN") ? t.denied : t.error;
      content.replaceChildren(node("div", "ced-error", status.textContent));
    }
  }
  function renderViewer(): void {
    if (!activeDefinition || !activeRead) return;
    content.replaceChildren();
    const titleRow = node("div", "ced-row");
    titleRow.append(node("h2", "", activeDefinition.title));
    titleRow.append(button(t.manage, () => openManageDialog(), "ced-button primary"));
    titleRow.append(button(t.duplicate, async () => { await client.duplicateDashboard(activeDefinition!.dashboard_id); await loadCatalog(); }));
    titleRow.append(button(t.expandAll, () => setAllPortletsExpanded(true)));
    titleRow.append(button(t.collapseAll, () => setAllPortletsExpanded(false)));
    content.append(titleRow);
    const filterRow = node("div", "ced-toolbar ced-section");
    const filtersForSummary = activeFilterOverrides === null ? activeRead.filters : activeFilterOverrides;
    const filterSummary = filtersForSummary.length
      ? filtersForSummary.map((item) => `${dashboardFilterDefinition(item.key) ? filterLabel(item.key) : item.key} ${operatorLabel(item.operator)} ${Array.isArray(item.value) ? item.value.map((value) => filterValueLabel(String(value))).join(", ") : filterValueLabel(String(item.value))}`).join(" · ")
      : t.noFilters;
    filterRow.append(node("span", "ced-muted", filterSummary));
    const configureFilters = button(t.projectFilter, () => openFilterDialog(), "ced-button");
    configureFilters.disabled = activeDefinition.restrict_filter_override;
    const resetFilter = button(t.resetMyFilter, async () => {
      if (!activeDefinition) return;
      try {
        status.textContent = t.loading;
        await client.resetFilterOverride(activeDefinition.dashboard_id);
        activeFilterOverrides = null;
        activeRead = await client.readPortlets(activeDefinition.dashboard_id);
        status.textContent = "";
        renderViewer();
      } catch {
        status.textContent = t.error;
      }
    });
    resetFilter.disabled = activeDefinition.restrict_filter_override;
    filterRow.append(configureFilters, resetFilter);
    if (activeDefinition.restrict_filter_override) filterRow.append(node("span", "ced-muted", t.filterLocked));
    content.append(filterRow);
    if (!activeRead.portlets.length) {
      content.append(node("p", "ced-muted", t.noPortlets));
      return;
    }
    for (const read of activeRead.portlets) content.append(renderPortlet(read));
  }
  function setAllPortletsExpanded(expanded: boolean): void {
    for (const card of Array.from(content.querySelectorAll<HTMLElement>(".ced-portlet"))) {
      const body = card.querySelector<HTMLElement>(".ced-portlet-body");
      const control = card.querySelector<HTMLButtonElement>("[data-portlet-expand-control]");
      if (!body || !control) continue;
      body.hidden = !expanded;
      control.textContent = expanded ? t.collapse : t.expand;
      control.setAttribute("aria-expanded", String(expanded));
    }
  }

  function openFilterDialog(): void {
    if (!activeDefinition || activeDefinition.restrict_filter_override) return;
    let draft = (activeFilterOverrides ?? activeRead?.filters ?? activeDefinition.filters).map((item) => ({
      key: item.key, operator: item.operator, value: Array.isArray(item.value) ? [...item.value] : item.value,
    }));
    const dialog = node("dialog", "ced-dialog");
    const inner = node("div", "ced-dialog-inner");
    inner.append(node("h2", "", t.filterDialog));
    const conditions = node("div", "ced-section");
    const fieldSelect = node("select", "ced-select");
    for (const definition of ENTERPRISE_DASHBOARD_FILTER_CATALOG) {
      const option = node("option", "", filterLabel(definition.key));
      option.value = definition.key;
      fieldSelect.append(option);
    }
    const operatorSelect = node("select", "ced-select");
    const valueHost = node("div", "ced-field");
    function renderValueControl(): void {
      const definition = dashboardFilterDefinition(fieldSelect.value)!;
      const previousOperator = operatorSelect.value;
      operatorSelect.replaceChildren();
      for (const operator of definition.operators) {
        const option = node("option", "", operatorLabel(operator));
        option.value = operator;
        option.selected = operator === previousOperator;
        operatorSelect.append(option);
      }
      valueHost.replaceChildren(node("span", "ced-muted", t.value));
      let control: HTMLElement;
      if (definition.value_kind === "enum") {
        const select = node("select", "ced-select");
        if (operatorSelect.value === "in") select.multiple = true;
        for (const value of definition.options ?? []) {
          const option = node("option", "", filterValueLabel(value));
          option.value = value;
          select.append(option);
        }
        control = select;
      } else if (definition.value_kind === "boolean") {
        const select = node("select", "ced-select");
        for (const [value, label] of [["true", "true"], ["false", "false"]]) {
          const option = node("option", "", label);
          option.value = value;
          select.append(option);
        }
        control = select;
      } else if (["portfolio_id", "project_id"].includes(definition.key)) {
        const options = activeDefinition
          ? authorizedDashboardFilterOptions(definition.key, activeDefinition, activeRead)
          : [];
        if (options.length) {
          const picker = node("select", "ced-select");
          picker.multiple = operatorSelect.value === "in";
          const existing = draft.find((item) => item.key === definition.key)?.value;
          const selectedValues = new Set((Array.isArray(existing) ? existing : existing === undefined ? [] : [existing]).map(String));
          for (const item of options) {
            const option = node("option", "", item.label);
            option.value = item.value;
            option.selected = selectedValues.has(item.value);
            picker.append(option);
          }
          const search = node("input", "ced-input");
          search.type = "search";
          search.placeholder = t.search;
          search.addEventListener("input", () => {
            const query = search.value.trim().toLocaleLowerCase();
            for (const option of Array.from(picker.options)) {
              option.hidden = Boolean(query) && !option.textContent?.toLocaleLowerCase().includes(query)
                && !option.value.toLocaleLowerCase().includes(query);
            }
          });
          valueHost.append(search);
          control = picker;
        } else {
          const inputControl = node("input", "ced-input");
          inputControl.type = "text";
          inputControl.placeholder = t.filterValueHint;
          control = inputControl;
          valueHost.append(node("small", "ced-muted", t.filterValueHint));
        }
      } else {
        const inputControl = node("input", "ced-input");
        inputControl.type = definition.value_kind === "datetime" ? "datetime-local" : "text";
        if (definition.value_kind === "text_list") inputControl.placeholder = t.filterValueHint;
        control = inputControl;
      }
      control.dataset.filterValue = "true";
      valueHost.append(control);
      if (definition.value_kind === "text_list" && !["portfolio_id", "project_id"].includes(definition.key)) valueHost.append(node("small", "ced-muted", t.filterValueHint));
    }
    fieldSelect.addEventListener("change", renderValueControl);
    operatorSelect.addEventListener("change", renderValueControl);
    renderValueControl();
    const add = button(t.addFilter, () => {
      const definition = dashboardFilterDefinition(fieldSelect.value);
      const control = valueHost.querySelector<HTMLInputElement | HTMLSelectElement>("[data-filter-value]");
      if (!definition || !control || draft.some((item) => item.key === definition.key)) return;
      if (["portfolio_id", "project_id"].includes(definition.key)
        && draft.some((item) => ["portfolio_id", "project_id"].includes(item.key))) {
        status.textContent = t.filterScopeConflict;
        return;
      }
      let value: unknown;
      if (definition.value_kind === "boolean") value = (control as HTMLSelectElement).value === "true";
      else if (definition.value_kind === "enum" && operatorSelect.value === "in") value = Array.from((control as HTMLSelectElement).selectedOptions).map((option) => option.value);
      else if (definition.value_kind === "text_list" && operatorSelect.value === "in") {
        value = control instanceof HTMLSelectElement && control.multiple
          ? Array.from(control.selectedOptions).map((option) => option.value)
          : (control as HTMLInputElement).value.split(",").map((item) => item.trim()).filter(Boolean);
      }
      else if (definition.value_kind === "datetime") {
        const raw = (control as HTMLInputElement).value;
        value = raw ? new Date(raw).toISOString() : "";
      } else value = (control as HTMLInputElement | HTMLSelectElement).value.trim();
      if (value === "" || (Array.isArray(value) && !value.length)) return;
      draft.push({ key: definition.key, operator: operatorSelect.value, value });
      renderConditions();
    });
    function renderConditions(): void {
      conditions.replaceChildren();
      if (!draft.length) conditions.append(node("p", "ced-muted", t.noFilters));
      for (const [index, item] of draft.entries()) {
        const row = node("div", "ced-row ced-panel ced-section");
        const value = Array.isArray(item.value) ? item.value.map((entry) => filterValueLabel(String(entry))).join(", ") : filterValueLabel(String(item.value));
        row.append(node("span", "", `${filterLabel(item.key)} · ${operatorLabel(item.operator)} · ${value}`));
        row.append(button(t.removeFilter, () => { draft = draft.filter((_, itemIndex) => itemIndex !== index); renderConditions(); }));
        conditions.append(row);
      }
    }
    renderConditions();
    const footer = node("div", "ced-row");
    footer.append(button(t.applyFilter, async () => {
      if (!activeDefinition) return;
      try {
        status.textContent = t.loading;
        activeFilterOverrides = draft;
        activeRead = await client.readPortlets(activeDefinition.dashboard_id, draft);
        dialog.close();
        dialog.remove();
        status.textContent = "";
        renderViewer();
      } catch (error) {
        status.textContent = error instanceof Error && error.message.includes("FORBIDDEN") ? t.denied : t.error;
      }
    }, "ced-button primary"));
    footer.append(button(t.saveMyFilter, async () => {
      if (!activeDefinition) return;
      try {
        status.textContent = t.loading;
        await client.saveFilterOverride(activeDefinition.dashboard_id, draft);
        activeFilterOverrides = null;
        activeRead = await client.readPortlets(activeDefinition.dashboard_id);
        dialog.close();
        dialog.remove();
        status.textContent = "";
        renderViewer();
      } catch (error) {
        status.textContent = error instanceof Error && error.message.includes("FORBIDDEN") ? t.denied : t.error;
      }
    }));
    footer.append(button(t.resetMyFilter, async () => {
      if (!activeDefinition) return;
      try {
        status.textContent = t.loading;
        await client.resetFilterOverride(activeDefinition.dashboard_id);
        activeFilterOverrides = null;
        activeRead = await client.readPortlets(activeDefinition.dashboard_id);
        dialog.close();
        dialog.remove();
        status.textContent = "";
        renderViewer();
      } catch {
        status.textContent = t.error;
      }
    }));
    footer.append(button(t.cancel, () => { dialog.close(); dialog.remove(); }));
    inner.append(node("div", "ced-form-grid", ""), field(t.field, fieldSelect), field(t.operator, operatorSelect), valueHost, add, conditions, footer);
    dialog.append(inner);
    container.append(dialog);
    dialog.showModal();
  }

  function renderPortlet(read: EnterprisePortletRead): HTMLElement {
    const card = node("article", "ced-portlet");
    const head = node("header", "ced-portlet-head");
    const label = read.hide_title ? portletLabel(read.type_id) : (read.title || portletLabel(read.type_id));
    const headingNode = node("strong", "", label);
    const controls = node("div", "ced-toolbar");
    let maximized = false;
    const body = node("div", "ced-portlet-body");
    const renderBody = (): void => {
      body.replaceChildren();
      const state = mapEnterprisePortletState(read);
      const stateText: Record<EnterprisePortletState, string> = {
        ready: "", empty: t.empty, stale: t.stale, missing: t.missing, filtered: t.filtered,
        permission_denied: t.denied, error: t.error,
      };
      if (state !== "ready") {
        body.append(node("p", state === "permission_denied" || state === "error" ? "ced-error" : "ced-warning", stateText[state]));
        return;
      }
      if (read.type_id === "portfolio-control-snapshot.v1") renderPortfolioSnapshot(body, read);
      else if (read.type_id === "portfolio-decision.v1") renderPortfolioDecision(body, read);
      else body.append(node("p", "ced-warning", t.unsupported));
    };
    const collapse = button(t.collapse, () => {
      body.hidden = !body.hidden;
      collapse.textContent = body.hidden ? t.expand : t.collapse;
      collapse.setAttribute("aria-expanded", String(!body.hidden));
    });
    collapse.dataset.portletExpandControl = "true";
    collapse.setAttribute("aria-expanded", "true");
    const maximize = button(t.maximize, () => {
      maximized = !maximized;
      card.classList.toggle("ced-maximized", maximized);
      maximize.textContent = maximized ? t.restore : t.maximize;
    });
    const refresh = button(t.refresh, async () => {
      if (!activeDefinition) return;
      const result = await client.readPortlets(activeDefinition.dashboard_id, activeFilterOverrides ?? undefined);
      activeRead = result;
      renderViewer();
    });
    const help = button(t.help, () => {
      const helpDialog = node("dialog", "ced-dialog");
      const helpPanel = node("div", "ced-dialog-inner");
      helpPanel.append(node("h2", "", label));
      helpPanel.append(node("p", "ced-muted", `${t.owner}: ${read.source_owner}`));
      helpPanel.append(node("p", "ced-muted", `${t.revision}: ${read.source_revision ?? "—"}`));
      helpPanel.append(node("p", "ced-muted", read.required_read_permission));
      helpPanel.append(node("p", "ced-muted", `${read.source_data_mode} · ${read.freshness_state}`));
      if (read.generated_at) helpPanel.append(node("p", "ced-muted", new Date(read.generated_at).toLocaleString()));
      helpPanel.append(button(t.close, () => helpDialog.close(), "ced-button"));
      helpDialog.append(helpPanel);
      helpDialog.addEventListener("close", () => helpDialog.remove(), { once: true });
      container.append(helpDialog);
      helpDialog.showModal();
    });
    const print = button(t.print, () => {
      const styleId = "ced-portlet-print-style";
      if (!document.getElementById(styleId)) {
        const style = document.createElement("style");
        style.id = styleId;
        style.textContent = "@media print { body.ced-print-portlet-mode * { visibility: hidden !important; } body.ced-print-portlet-mode .ced-print-target, body.ced-print-portlet-mode .ced-print-target * { visibility: visible !important; } body.ced-print-portlet-mode .ced-print-target { position: absolute !important; inset: 0 auto auto 0 !important; width: 100% !important; max-height: none !important; overflow: visible !important; box-shadow: none !important; } }";
        document.head.append(style);
      }
      const cleanup = (): void => {
        document.body.classList.remove("ced-print-portlet-mode");
        card.classList.remove("ced-print-target");
        window.removeEventListener("afterprint", cleanup);
      };
      cleanup();
      document.body.classList.add("ced-print-portlet-mode");
      card.classList.add("ced-print-target");
      window.addEventListener("afterprint", cleanup, { once: true });
      window.print();
    });
    const close = button(t.close, () => card.remove());
    controls.append(collapse, maximize, refresh, help, print, close);
    head.append(headingNode, controls);
    card.append(head, body);
    renderBody();
    for (const reference of read.drill_through_refs ?? []) {
      const drill = button(t.drill, () => options.onDrillThrough?.(reference));
      body.append(drill);
    }
    return card;
  }
  function renderPortfolioSnapshot(target: HTMLElement, read: EnterprisePortletRead): void {
    if (!read.data || typeof read.data !== "object") {
      target.append(node("p", "ced-muted", t.noData));
      return;
    }
    const data = read.data as { summary?: Record<string, number>; projects?: Array<Record<string, unknown>> };
    const summary = data.summary;
    if (summary) {
      const strip = node("div", "ced-grid");
      for (const [label, key] of [[t.total, "total_projects"], [t.included, "included_projects"], [t.onHold, "on_hold_projects"], [t.excluded, "excluded_projects"]] as const) {
        const metric = node("div", "ced-panel");
        metric.append(node("div", "ced-muted", label), node("strong", "", displaySummaryMetric(summary, key)));
        strip.append(metric);
      }
      target.append(strip);
    }
    const projects = Array.isArray(data.projects) ? data.projects : [];
    if (!projects.length) {
      target.append(node("p", "ced-muted", t.empty));
      return;
    }
    const table = node("table", "ced-table");
    const thead = node("thead");
    const row = node("tr");
    for (const label of [t.projects, t.status, t.membership]) row.append(node("th", "", label));
    thead.append(row);
    const tbody = node("tbody");
    for (const project of projects) {
      const tr = node("tr");
      tr.append(node("td", "", String(project.project_id ?? "—")));
      tr.append(node("td", "", String(project.status ?? "—")));
      tr.append(node("td", "", String(project.membership_status ?? "—")));
      tbody.append(tr);
    }
    table.append(thead, tbody);
    target.append(table);
    if (read.truncated) target.append(node("p", "ced-muted", t.truncated));
  }
  function renderPortfolioDecision(target: HTMLElement, read: EnterprisePortletRead): void {
    if (!read.data || typeof read.data !== "object") {
      target.append(node("p", "ced-muted", t.noData));
      return;
    }
    const data = read.data as Record<string, unknown>;
    for (const [label, key] of [["Decision ID", "decision_id"], [t.status, "status"], ["Title", "title"], ["Revision", "revision"]] as const) {
      if (data[key] !== undefined && data[key] !== null) {
        const row = node("p");
        row.append(node("strong", "", `${label}: `), document.createTextNode(String(data[key])));
        target.append(row);
      }
    }
  }
  function openManageDialog(): void {
    if (!activeDefinition) return;
    let layoutOrder = activeDefinition.portlets.map((_, index) => index);
    let draftPortlets = activeDefinition.portlets.map((portlet) => ({ ...portlet, layout: { ...portlet.layout }, config: { ...portlet.config } }));
    let draftTitle = activeDefinition.title;
    let draftDescription = activeDefinition.description;
    let draftMaxRows = activeDefinition.max_rows_per_portlet;
    let draftFilterLock = activeDefinition.restrict_filter_override;
    let draftDashboardFilters = activeDefinition.filters.map((item) => ({ ...item, value: Array.isArray(item.value) ? [...item.value] : item.value }));
    let currentSection = -1;
    const dialog = node("dialog", "ced-dialog");
    const inner = node("div", "ced-dialog-inner");
    const title = node("h2", "", t.manage);
    const tabBar = node("nav", "ced-tabs");
    const panel = node("section");
    const footer = node("div", "ced-row");
    const save = button(t.save, async () => {
      if (!activeDefinition) return;
      captureActiveSection();
      const nextPortlets = draftPortlets;
      if (!validateDashboardLayout(nextPortlets, effectiveDashboardPortletLimit(catalog))) {
        panel.prepend(node("p", "ced-error", "Invalid or overlapping portlet layout."));
        return;
      }
      await client.updateDashboard(activeDefinition.dashboard_id, {
        title: draftTitle.trim() || activeDefinition.title,
        description: draftDescription,
        portlets: nextPortlets,
        filters: draftDashboardFilters,
        restrict_filter_override: draftFilterLock,
        max_rows_per_portlet: Math.max(1, Math.min(500, draftMaxRows)),
      }, activeDefinition.revision);
      dialog.close();
      dialog.remove();
      await openDashboard(activeDefinition.dashboard_id);
      await loadCatalog();
    }, "ced-button primary");
    const cancel = button(t.cancel, () => { dialog.close(); dialog.remove(); });
    footer.append(save, cancel);
    const sections: Array<[string, () => void]> = [
      [t.content, () => renderContent()],
      [t.layout, () => renderLayout()],
      [t.access, () => renderAccess()],
    ];
    function captureActiveSection(): void {
      if (currentSection === 0) {
        draftTitle = dialog.querySelector<HTMLInputElement>("[name=dashboard-title]")?.value ?? draftTitle;
        draftDescription = dialog.querySelector<HTMLTextAreaElement>("[name=dashboard-description]")?.value ?? draftDescription;
        draftMaxRows = Number(dialog.querySelector<HTMLInputElement>("[name=max-rows]")?.value ?? draftMaxRows);
        draftFilterLock = dialog.querySelector<HTMLInputElement>("[name=filter-lock]")?.checked ?? draftFilterLock;
        draftPortlets = readEditorPortlets(dialog, draftPortlets, layoutOrder);
        layoutOrder = draftPortlets.map((_, index) => index);
      } else if (currentSection === 1) {
        // Layout coordinates are authoritative. Switching tabs must never flatten the 2-D grid.
        layoutOrder = draftPortlets.map((_, index) => index);
      }
    }
    function activateSection(index: number): void {
      captureActiveSection();
      currentSection = index;
      tabBar.replaceChildren();
      sections.forEach(([label], i) => tabBar.append(button(label, () => activateSection(i), i === index ? "ced-button primary" : "ced-button")));
      panel.replaceChildren();
      sections[index][1]();
    }
    function refreshContent(): void {
      draftPortlets = readEditorPortlets(dialog, draftPortlets, layoutOrder);
      layoutOrder = draftPortlets.map((_, index) => index);
      renderContent();
    }
    function renderGeneral(target: HTMLElement): void {
      target.replaceChildren();
      target.append(node("h3", "", t.general));
      const form = node("div", "ced-form-grid");
      form.append(field(t.name, input("dashboard-title", draftTitle)));
      const description = node("textarea", "ced-input");
      description.name = "dashboard-description";
      description.value = draftDescription;
      form.append(field(t.description, description));
      form.append(field(t.maxRows, input("max-rows", String(draftMaxRows), "number")));
      const lock = node("input");
      lock.type = "checkbox"; lock.name = "filter-lock"; lock.checked = draftFilterLock;
      form.append(field(t.filterLock, lock));
      const filterSection = node("section", "ced-section");
      filterSection.append(node("h3", "", t.defaultFilter));
      if (!draftDashboardFilters.length) filterSection.append(node("p", "ced-muted", t.noFilters));
      for (const [index, item] of draftDashboardFilters.entries()) {
        const value = Array.isArray(item.value) ? item.value.join(", ") : String(item.value);
        const row = node("div", "ced-row ced-panel");
        row.append(node("span", "", `${filterLabel(item.key)} · ${operatorLabel(item.operator)} · ${value}`));
        row.append(button(t.removeFilter, () => {
          draftDashboardFilters = draftDashboardFilters.filter((_, itemIndex) => itemIndex !== index);
          refreshContent();
        }));
        filterSection.append(row);
      }
      filterSection.append(button(t.useCurrentAsDefault, () => {
        draftDashboardFilters = (activeFilterOverrides ?? activeDefinition!.filters).map((item) => ({
          ...item, value: Array.isArray(item.value) ? [...item.value] : item.value,
        }));
        refreshContent();
      }));
      filterSection.append(button(t.clearDefaultFilter, () => {
        draftDashboardFilters = [];
        refreshContent();
      }));
      target.append(form, filterSection);
    }
    function renderContent(): void {
      panel.replaceChildren();
      const generalSection = node("section", "ced-section");
      renderGeneral(generalSection);
      panel.append(generalSection);
      const portletSection = node("section", "ced-section");
      portletSection.append(node("h3", "", t.content));
      const list = node("div", "ced-section");
      draftPortlets.forEach((portlet, index) => {
        const row = node("div", "ced-panel ced-section ced-editor-portlet");
        row.dataset.existingPortletIndex = String(index);
        row.append(node("strong", "", portletLabel(portlet.type_id)));
        row.append(field(t.portletTitle, input(`portlet-title-${index}`, portlet.title ?? "")));
        const width = node("select", "ced-select");
        width.name = `portlet-width-${index}`;
        for (const [value, label] of [[6, t.narrow], [12, t.wide]] as const) {
          const option = node("option", "", label);
          option.value = String(value);
          option.selected = portlet.layout.w === value;
          width.append(option);
        }
        row.append(field(t.width, width));
        const hide = node("input");
        hide.type = "checkbox";
        hide.name = `hide-title-${index}`;
        hide.checked = Boolean(portlet.hide_title);
        row.append(field("Hide title", hide));
        row.append(button(t.remove, () => row.remove()));
        list.append(row);
      });
      const addType = node("select", "ced-select");
      for (const item of ENTERPRISE_DASHBOARD_PORTLET_CATALOG) {
        const option = node("option", "", item.enabled ? item.label : `${item.label} — not available`);
        option.value = item.type_id;
        option.disabled = !item.enabled;
        if (!item.enabled && item.unavailable_reason) option.title = item.unavailable_reason;
        addType.append(option);
      }
      const portfolio = input("new-portfolio-id", "");
      const decision = input("new-decision-id", "");
      const add = button(t.addPortlet, () => {
        if (list.querySelectorAll(".ced-editor-portlet").length >= effectiveDashboardPortletLimit(catalog)) return;
        const type = addType.value as EnterprisePortletType;
        const config = {
          portfolio_id: portfolio.value.trim(),
          ...(type === "portfolio-decision.v1" ? { decision_id: decision.value.trim() } : {}),
        };
        if (!config.portfolio_id || (type === "portfolio-decision.v1" && !config.decision_id)) return;
        const row = node("div", "ced-panel ced-section ced-editor-portlet");
        row.dataset.newPortlet = type;
        row.dataset.portfolioId = config.portfolio_id;
        row.dataset.decisionId = config.decision_id ?? "";
        row.append(node("strong", "", portletLabel(type)), node("span", "ced-muted", config.portfolio_id));
        row.append(button(t.remove, () => row.remove()));
        list.append(row);
      });
      portletSection.append(
        list,
        node("p", "ced-muted", t.unsupported),
        addType,
        field(t.portfolioId, portfolio),
        field(t.decisionId, decision),
        add,
      );
      panel.append(portletSection);
    }
    function renderLayout(): void {
      panel.replaceChildren();
      const list = node("div", "ced-section");
      draftPortlets.forEach((portlet, originalIndex) => {
        const row = node("div", "ced-panel ced-row ced-section");
        row.draggable = true;
        row.dataset.layoutIndex = String(originalIndex);
        row.addEventListener("dragstart", (event) => {
          event.dataTransfer?.setData("text/plain", String(originalIndex));
          if (event.dataTransfer) event.dataTransfer.effectAllowed = "move";
        });
        row.addEventListener("dragover", (event) => {
          event.preventDefault();
          if (event.dataTransfer) event.dataTransfer.dropEffect = "move";
        });
        row.addEventListener("drop", (event) => {
          event.preventDefault();
          const rawIndex = event.dataTransfer?.getData("text/plain");
          if (rawIndex === undefined || rawIndex === null || rawIndex.trim() === "") return;
          const fromIndex = Number(rawIndex);
          if (!Number.isInteger(fromIndex)) return;
          draftPortlets = moveDashboardPortletToPosition(draftPortlets, fromIndex, originalIndex);
          renderLayout();
        });
        row.append(node("strong", "", portletLabel(portlet.type_id)));
        row.append(node("span", "ced-muted", portlet.layout.w === 12 ? t.wide : t.narrow));
        const up = button(t.moveUp, () => {
          draftPortlets = moveDashboardPortletVertically(draftPortlets, originalIndex, "up");
          renderLayout();
        });
        const down = button(t.moveDown, () => {
          draftPortlets = moveDashboardPortletVertically(draftPortlets, originalIndex, "down");
          renderLayout();
        });
        up.disabled = portlet.layout.y === 0;
        down.disabled = portlet.layout.y + portlet.layout.h >= 100;
        const left = button(t.moveLeft, () => {
          draftPortlets = moveDashboardPortletHorizontally(draftPortlets, originalIndex, "left");
          renderLayout();
        });
        const right = button(t.moveRight, () => {
          draftPortlets = moveDashboardPortletHorizontally(draftPortlets, originalIndex, "right");
          renderLayout();
        });
        left.disabled = portlet.layout.w !== 6 || portlet.layout.x === 0;
        right.disabled = portlet.layout.w !== 6 || portlet.layout.x === 6;
        row.append(up, down, left, right);
        list.append(row);
      });
      panel.append(list, node("p", "ced-muted", "Drag a portlet onto another to exchange their positions when the resulting layout remains valid. Arrow controls move portlets within the two-column layout; Narrow/Wide sizing is configured in Content."));
    }
    function renderAccess(): void {
      if (!activeDefinition) return;
      panel.replaceChildren();
      const definition = activeDefinition;
      const summary = node("div", "ced-panel");
      summary.append(node("strong", "", t.visibility), node("p", "", t[definition.visibility]));
      summary.append(node("p", "ced-muted", t.accessNote));
      summary.append(node("p", "ced-muted", `${t.owner}: ${definition.owner_user_id}`));
      panel.append(summary);

      const users = node("section", "ced-section");
      users.append(node("h3", "", t.accessUsers));
      if (definition.visibility === "global") users.append(node("p", "ced-muted", t.global));
      else if (!definition.shared_user_ids.length) users.append(node("p", "ced-muted", t.accessNoUsers));
      for (const userId of definition.shared_user_ids) {
        const row = node("div", "ced-row ced-panel");
        row.append(node("span", "", userId));
        row.append(button(t.remove, async () => {
          await changeShare("user", userId, false);
        }));
        users.append(row);
      }
      const userSearch = input("dashboard-share-search", "");
      userSearch.type = "search";
      const userSelect = node("select", "ced-select");
      const placeholder = node("option", "", t.accessSelectUser);
      placeholder.value = "";
      userSelect.append(placeholder);
      let accessAccounts: EnterpriseDashboardShareAccount[] = [];
      function renderAccountOptions(): void {
        const selected = userSelect.value;
        userSelect.replaceChildren();
        const empty = node("option", "", t.accessSelectUser);
        empty.value = "";
        userSelect.append(empty);
        for (const account of dashboardShareAccountOptions(accessAccounts, userSearch.value, definition.shared_user_ids)) {
          const option = node("option", "", `${account.display_name || account.user_id} · ${account.email}`);
          option.value = account.user_id;
          option.selected = account.user_id === selected;
          userSelect.append(option);
        }
      }
      userSearch.addEventListener("input", renderAccountOptions);
      const addSelectedUser = button(t.accessAddUser, async () => {
        await changeShare("user", userSelect.value, true);
      });
      addSelectedUser.disabled = definition.visibility === "global";
      const userInput = input("dashboard-share-user", "");
      userInput.autocomplete = "off";
      const addById = button(t.accessAddUser, async () => {
        await changeShare("user", userInput.value.trim(), true);
      });
      addById.disabled = definition.visibility === "global";
      users.append(field(t.accessSearchUsers, userSearch), field(t.accessSelectUser, userSelect), addSelectedUser);
      users.append(field(t.accessUserId, userInput), addById);
      users.append(node("p", "ced-muted", t.accessDirectoryPending));
      void client.listUsers().then((result) => {
        accessAccounts = result.users.filter((item) => item.active === true);
        renderAccountOptions();
      }).catch(() => {
        users.append(node("p", "ced-muted", t.accessDirectoryUnavailable));
      });
      panel.append(users);

      const roles = node("section", "ced-section");
      roles.append(node("h3", "", t.accessRoles));
      if (!definition.shared_role_ids.length) roles.append(node("p", "ced-muted", t.accessNoRoles));
      for (const roleId of definition.shared_role_ids) {
        const row = node("div", "ced-row ced-panel");
        row.append(node("span", "", roleLabel(roleId)));
        row.append(button(t.remove, async () => { await changeShare("role", roleId, false); }));
        roles.append(row);
      }
      const roleSelect = node("select", "ced-select");
      for (const roleId of ["enterprise_admin", "enterprise_user", "enterprise_viewer"] as const) {
        if (definition.shared_role_ids.includes(roleId)) continue;
        const option = node("option", "", roleLabel(roleId));
        option.value = roleId;
        roleSelect.append(option);
      }
      const addRole = button(t.accessAddRole, async () => { await changeShare("role", roleSelect.value, true); });
      addRole.disabled = definition.visibility === "global" || !roleSelect.options.length;
      roles.append(field(t.accessRole, roleSelect), addRole);
      panel.append(roles);

      const global = node("section", "ced-section ced-panel");
      if (definition.visibility === "global") {
        global.append(button(t.accessRevokeGlobal, async () => { await changeShare("all_users", "", false); }));
      } else {
        global.append(button(t.accessGlobal, async () => { await changeShare("all_users", "", true); }));
      }
      global.append(node("p", "ced-muted", t.accessNote));
      panel.append(global);
    }

    async function changeShare(targetType: "user" | "role" | "all_users", targetId: string, assign: boolean): Promise<void> {
      if (!activeDefinition) return;
      if (targetType !== "all_users" && !targetId.trim()) {
        status.textContent = t.accessSaveError;
        return;
      }
      try {
        status.textContent = t.loading;
        const id = activeDefinition.dashboard_id;
        const revision = activeDefinition.revision;
        if (assign) await client.assignShare(id, targetType, targetId, revision);
        else await client.revokeShare(id, targetType, targetId, revision);
        const fresh = await client.getDashboard(id);
        activeDefinition = fresh.dashboard;
        status.textContent = "";
        renderAccess();
        await loadCatalog();
      } catch (error) {
        status.textContent = error instanceof Error && error.message.includes("FORBIDDEN") ? t.denied : t.accessSaveError;
      }
    }
    inner.append(title, tabBar, panel, footer);
    dialog.append(inner);
    container.append(dialog);
    activateSection(0);
    dialog.showModal();
  }
  function readEditorPortlets(dialog: HTMLDialogElement, original: EnterpriseDashboardPortlet[], order: readonly number[] = original.map((_, index) => index)): EnterpriseDashboardPortlet[] {
    const result: EnterpriseDashboardPortlet[] = [];
    for (const index of order) {
      const portlet = original[index];
      if (!portlet) continue;
      const row = dialog.querySelector<HTMLElement>(`[data-existing-portlet-index="${index}"]`);
      if (!row) continue;
      const title = row.querySelector<HTMLInputElement>(`[name="portlet-title-${index}"]`)?.value ?? portlet.title ?? "";
      const hideTitle = row.querySelector<HTMLInputElement>(`[name="hide-title-${index}"]`)?.checked ?? Boolean(portlet.hide_title);
      const width = Number(row.querySelector<HTMLSelectElement>(`[name="portlet-width-${index}"]`)?.value ?? portlet.layout.w);
      const x = width === 12 ? 0 : (portlet.layout.x === 6 ? 6 : 0);
      result.push({
        ...portlet,
        title: title.trim() || null,
        hide_title: hideTitle,
        layout: { ...portlet.layout, x, w: width },
      });
    }
    // Preserve existing x/y coordinates; the P6-style layout is a two-dimensional grid.
    const nextY = Math.max(0, ...result.map((item) => item.layout.y + item.layout.h));
    let addedIndex = 0;
    for (const row of dialog.querySelectorAll<HTMLElement>("[data-new-portlet]")) {
      const type = row.dataset.newPortlet as EnterprisePortletType;
      const index = result.length;
      const config = {
        portfolio_id: row.dataset.portfolioId ?? "",
        ...(type === "portfolio-decision.v1" ? { decision_id: row.dataset.decisionId ?? "" } : {}),
      };
      result.push({
        instance_id: `portlet-${Date.now()}-${index}`,
        type_id: type,
        contract_version: type,
        config,
        layout: { x: 0, y: nextY + addedIndex * 4, w: 12, h: 4 },
        title: null,
        hide_title: false,
      });
      addedIndex += 1;
    }
    return result;
  }
  function input(name: string, value: string, type = "text"): HTMLInputElement {
    const result = node("input", "ced-input");
    result.name = name; result.value = value; result.type = type;
    return result;
  }
  function field(label: string, control: HTMLElement): HTMLElement {
    const wrapper = node("label", "ced-field");
    wrapper.append(node("span", "ced-muted", label), control);
    return wrapper;
  }

  const loadedCatalog = await loadCatalog();
  if (loadedCatalog && loadedCatalog.displayed_dashboards.length) {
    await openDashboard(loadedCatalog.displayed_dashboards[0].dashboard.dashboard_id);
  }
}
