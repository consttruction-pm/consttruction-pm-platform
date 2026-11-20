/**
 * Enterprise Workbench routing.
 *
 * The Enterprise application is a separate document (`/enterprise.html`) served
 * under `/cubi/*`. It never mounts inside, or replaces, the Engineering shell.
 */

export type PageId =
  | "home"
  | "login"
  | "roles"
  | "workbench"
  | "environments"
  | "dashboard"
  | "portfolio"
  | "projects"
  | "access"
  | "tasks"
  | "workflows"
  | "approvals"
  | "resources"
  | "reports"
  | "knowledge"
  | "not-found";

export type RouteDefinition = {
  id: PageId;
  segment: string;
  titleKey: string;
  group: "entry" | "personal" | "enterprise" | "none";
  requiresSession: boolean;
  enterpriseArea: boolean;
};

export const BASE_PATH = "/cubi";

export const ROUTES: readonly RouteDefinition[] = [
  { id: "home", segment: "", titleKey: "page.home.title", group: "entry", requiresSession: false, enterpriseArea: false },
  { id: "login", segment: "login", titleKey: "page.login.title", group: "none", requiresSession: false, enterpriseArea: false },
  { id: "roles", segment: "roles", titleKey: "page.roles.title", group: "entry", requiresSession: true, enterpriseArea: false },
  { id: "workbench", segment: "workbench", titleKey: "page.workbench.title", group: "personal", requiresSession: true, enterpriseArea: false },
  { id: "environments", segment: "environments", titleKey: "page.environments.title", group: "personal", requiresSession: true, enterpriseArea: false },
  { id: "dashboard", segment: "enterprise/dashboard", titleKey: "page.dashboard.title", group: "enterprise", requiresSession: true, enterpriseArea: true },
  { id: "portfolio", segment: "enterprise/portfolio", titleKey: "page.portfolio.title", group: "enterprise", requiresSession: true, enterpriseArea: true },
  { id: "projects", segment: "enterprise/projects", titleKey: "page.projects.title", group: "enterprise", requiresSession: true, enterpriseArea: true },
  { id: "access", segment: "enterprise/access", titleKey: "page.access.title", group: "enterprise", requiresSession: true, enterpriseArea: true },
  { id: "tasks", segment: "enterprise/tasks", titleKey: "page.tasks.title", group: "enterprise", requiresSession: true, enterpriseArea: true },
  { id: "workflows", segment: "enterprise/workflows", titleKey: "page.workflows.title", group: "enterprise", requiresSession: true, enterpriseArea: true },
  { id: "approvals", segment: "enterprise/approvals", titleKey: "page.approvals.title", group: "enterprise", requiresSession: true, enterpriseArea: true },
  { id: "resources", segment: "enterprise/resources", titleKey: "page.resources.title", group: "enterprise", requiresSession: true, enterpriseArea: true },
  { id: "reports", segment: "enterprise/reports", titleKey: "page.reports.title", group: "enterprise", requiresSession: true, enterpriseArea: true },
  { id: "knowledge", segment: "enterprise/knowledge", titleKey: "page.knowledge.title", group: "enterprise", requiresSession: true, enterpriseArea: true },
];

export function normalizePath(pathname: string): string {
  const withoutQuery = pathname.split("?")[0] ?? "/";
  const trimmed = withoutQuery.replace(/\/+$/, "");
  return (trimmed || "/") + "/";
}

export function routeById(id: PageId): RouteDefinition {
  return ROUTES.find((route) => route.id === id) ?? { ...ROUTES[0], id: "not-found", segment: "__not_found__" };
}

export function resolvePage(pathname: string): PageId {
  const normalized = normalizePath(pathname);
  if (!normalized.startsWith(`${BASE_PATH}/`)) return "not-found";
  const rest = normalized.slice(BASE_PATH.length + 1, -1);
  if (!rest) return "home";
  const match = ROUTES.find((route) => route.segment && route.segment === rest);
  return match ? match.id : "not-found";
}

export function pageHref(id: PageId, params?: Record<string, string | null | undefined>): string {
  const route = routeById(id);
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== null && value !== undefined && value !== "") query.set(key, value);
  }
  const path = `${BASE_PATH}/${route.segment}${route.segment ? "/" : ""}`;
  const text = query.toString();
  return text ? `${path}?${text}` : path;
}

/** Only same-application paths may be used as a post-login destination. */
export function safeNextPath(raw: string | null | undefined): string {
  const value = String(raw ?? "").trim();
  if (!value.startsWith(`${BASE_PATH}/`) || value.startsWith("//")) return pageHref("workbench");
  if (/[\u0000-\u001f]/.test(value)) return pageHref("workbench");
  return value;
}

export function navigate(path: string, { replace = false }: { replace?: boolean } = {}): void {
  if (replace) window.history.replaceState({}, "", path);
  else window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}
