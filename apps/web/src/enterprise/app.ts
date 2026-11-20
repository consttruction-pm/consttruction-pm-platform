/**
 * CUBI Enterprise Workbench application shell.
 *
 * Served as its own document under /cubi/*. It never boots the Engineering
 * workspace bundle and never changes the Engineering shell.
 */

import { ApiError, api, type ProjectSummary, type SessionInfo } from "./api.js";
import {
  ENTERPRISE_LOCALES,
  LOCALE_LABELS,
  hasReviewedContent,
  isRtl,
  readLocalePreference,
  rememberLocale,
  translator,
  type EnterpriseLocale,
} from "./i18n.js";
import {
  BASE_PATH,
  ROUTES,
  navigate,
  pageHref,
  resolvePage,
  routeById,
  safeNextPath,
  type PageId,
} from "./router.js";
import {
  displayName,
  environmentAccess,
  enterpriseTier,
  initials,
} from "./session.js";
import { ENTERPRISE_CSS } from "./styles.js";
import { badge, button, el, stateBlock } from "./ui.js";

import { renderHome } from "./pages/home.js";
import { renderLogin } from "./pages/login.js";
import { renderRoles } from "./pages/roles.js";
import { renderWorkbench } from "./pages/workbench.js";
import { renderEnvironments } from "./pages/environments.js";
import { renderDashboard } from "./pages/dashboard.js";
import { renderPortfolio } from "./pages/portfolio.js";
import { renderProjects } from "./pages/projects.js";
import { renderAccess } from "./pages/access.js";
import { renderTasks } from "./pages/tasks.js";
import { renderWorkflows } from "./pages/workflows.js";
import { renderApprovals } from "./pages/approvals.js";
import { renderResources } from "./pages/resources.js";
import { renderReports } from "./pages/reports.js";
import { renderKnowledge } from "./pages/knowledge.js";

export type ToastKind = "info" | "error";

export type PageContext = {
  session: SessionInfo;
  projects: ProjectSummary[];
  locale: EnterpriseLocale;
  t: (key: string, vars?: Record<string, string | number>) => string;
  query: URLSearchParams;
  navigate: (path: string) => void;
  open: (page: PageId, params?: Record<string, string | null | undefined>) => void;
  toast: (message: string, kind?: ToastKind) => void;
  reloadProjects: () => Promise<void>;
  signOut: () => Promise<void>;
  onUnauthorized: () => void;
};

export type PublicPageContext = Omit<PageContext, "session">;

type Renderer = (ctx: PageContext, host: HTMLElement) => void | Promise<void>;
type PublicRenderer = (ctx: PublicPageContext, host: HTMLElement) => void | Promise<void>;

const RENDERERS: Record<Exclude<PageId, "login" | "not-found">, Renderer> = {
  home: renderHome,
  roles: renderRoles,
  workbench: renderWorkbench,
  environments: renderEnvironments,
  dashboard: renderDashboard,
  portfolio: renderPortfolio,
  projects: renderProjects,
  access: renderAccess,
  tasks: renderTasks,
  workflows: renderWorkflows,
  approvals: renderApprovals,
  resources: renderResources,
  reports: renderReports,
  knowledge: renderKnowledge,
};

type AppState = {
  session: SessionInfo | null;
  projects: ProjectSummary[];
  locale: EnterpriseLocale;
  page: PageId;
  booting: boolean;
  booted: boolean;
  t: (key: string, vars?: Record<string, string | number>) => string;
};

const state: AppState = {
  session: null,
  projects: [],
  locale: readLocalePreference(),
  page: resolvePage(window.location.pathname),
  booting: true,
  booted: false,
  t: translator(readLocalePreference()),
};

let toastHost: HTMLElement | null = null;

function ensureStyles(): void {
  const id = "cubi-enterprise-styles";
  if (document.getElementById(id)) return;
  const style = document.createElement("style");
  style.id = id;
  style.textContent = ENTERPRISE_CSS;
  document.head.append(style);
}

function setDocumentLanguage(): void {
  document.documentElement.lang = state.locale === "tr" ? "tr-TR" : state.locale;
  document.documentElement.dir = isRtl(state.locale) ? "rtl" : "ltr";
  document.body.classList.add("cubi-body");
}

function toast(message: string, kind: ToastKind = "info"): void {
  if (!toastHost) return;
  const item = el("div", { class: `cubi-toast ${kind === "error" ? "error" : ""}`.trim(), text: message, attrs: { role: "status" } });
  toastHost.append(item);
  window.setTimeout(() => item.remove(), 4200);
}

function appHref(id: PageId): string {
  return pageHref(id);
}

function brandBlock(subtitle: string): HTMLElement {
  const brand = el("a", { class: "cubi-brand" });
  brand.href = `${BASE_PATH}/`;
  brand.append(
    el("span", { class: "cubi-brand-mark", text: "CB" }),
    el("span", { class: "cubi-brand-text" }, el("strong", { text: "CUBI" }), el("span", { text: subtitle })),
  );
  return brand;
}

function publicNav(): HTMLElement {
  const nav = el("header", { class: "cubi-public-nav" }, brandBlock("PLATFORM"));
  const links = el("nav", { class: "cubi-public-links", attrs: { "aria-label": "Primary" } });
  links.append(
    link(`${BASE_PATH}/#environments`, state.t("nav.environments")),
    link(publicHelpUrl(), state.t("nav.help"), true),
    link(pageHref("login"), state.t("common.signIn"), false, "cubi-btn cubi-btn-secondary"),
  );
  nav.append(links);
  return nav;
}

function link(href: string, text: string, external = false, className = ""): HTMLAnchorElement {
  const anchor = el("a", { class: className || undefined, text });
  anchor.href = href;
  if (external) {
    anchor.target = "_blank";
    anchor.rel = "noopener noreferrer";
  }
  return anchor;
}

export function publicHelpUrl(): string {
  return "https://docs.oracle.com/cd/G48897_01/p6help/en/toc.htm";
}

function sessionGate(nextPath: string): void {
  navigate(`${pageHref("login")}?next=${encodeURIComponent(nextPath)}`, { replace: true });
}

function renderShell(): void {
  const root = document.getElementById("cubi-app");
  if (!root) return;
  const session = state.session;
  if (!session) return;
  const route = routeById(state.page);
  const shell = el("div", { class: "cubi-shell" });

  const sidebar = el("aside", { class: "cubi-sidebar" });
  sidebar.append(brandBlock(state.t("brand.workbench")));

  const nav = el("nav", { class: "cubi-nav", attrs: { "aria-label": "Enterprise" } });
  const group = (labelKey: string, ids: PageId[]): void => {
    const section = el("div", { class: "cubi-nav-group" });
    section.append(el("span", { class: "cubi-nav-label", text: state.t(labelKey) }));
    for (const id of ids) {
      const item = el("a", { text: state.t(routeById(id).titleKey) });
      item.href = appHref(id);
      if (state.page === id) item.setAttribute("aria-current", "page");
      section.append(item);
    }
    nav.append(section);
  };
  group("nav.group.entry", ["roles", "workbench", "environments"]);
  group("nav.group.enterprise", ["dashboard", "portfolio", "projects", "access", "tasks", "workflows", "approvals", "resources", "reports", "knowledge"]);
  sidebar.append(nav);

  const foot = el("div", { class: "cubi-sidebar-foot" });
  const identity = el("div", { class: "cubi-identity" });
  identity.append(
    el("span", { class: "cubi-avatar", text: initials(session.user_id) }),
    el("div", { class: "cubi-identity-text" },
      el("strong", { text: displayName(session.user_id) }),
      el("span", { text: state.t("common.organization") + ": " + session.tenant_id }),
    ),
  );
  const signOut = el("button", { class: "cubi-signout", text: state.t("common.signOut"), attrs: { type: "button" } });
  signOut.addEventListener("click", () => { void doSignOut(); });
  foot.append(identity, el("div", { class: "cubi-row" }, signOut, link(pageHref("home"), state.t("nav.home"), false, "cubi-signout")));
  sidebar.append(foot);

  const main = el("div", { class: "cubi-main" });
  const topbar = el("header", { class: "cubi-topbar" });
  const crumbs = el("div", { class: "cubi-crumbs" });
  crumbs.append(
    link(`${BASE_PATH}/`, "CUBI"),
    el("span", { class: "sep", text: "/" }),
    link(pageHref("workbench"), state.t("nav.workbench")),
    el("span", { class: "sep", text: "/" }),
    el("span", { text: state.t(route.titleKey) }),
  );
  const topActions = el("div", { class: "cubi-topbar-actions" });
  const access = environmentAccess(session);
  topActions.append(
    el("span", { class: "cubi-env-pill", text: access.enterprise.allowed ? state.t("brand.enterprise") : state.t("brand.enterprise") + " · " + state.t("common.restricted") }),
    languageSelect(),
    link(publicHelpUrl(), "?", true, "cubi-btn cubi-btn-ghost"),
  );
  topbar.append(crumbs, topActions);

  const content = el("main", { class: "cubi-content", attrs: { id: "cubi-main", tabindex: "-1" } });
  main.append(topbar, content);
  shell.append(sidebar, main);
  root.replaceChildren(shell);

  const host = el("div", { class: "cubi-page" });
  content.append(host);
  host.append(pageHeader());
  const body = el("div", { class: "cubi-page-body" });
  host.append(body);

  const renderer = RENDERERS[state.page as keyof typeof RENDERERS];
  if (!renderer) {
    body.append(stateBlock("empty", "Not found", "This page does not exist in the Enterprise workbench."));
    return;
  }
  const query = new URLSearchParams(window.location.search);
  const ctx: PageContext = {
    session,
    projects: state.projects,
    locale: state.locale,
    t: state.t,
    query,
    navigate: (path) => navigate(path),
    open: (page, params) => navigate(pageHref(page, params)),
    toast,
    reloadProjects: loadProjects,
    signOut: doSignOut,
    onUnauthorized: () => sessionGate(window.location.pathname),
  };
  try {
    const result = renderer(ctx, body);
    if (result instanceof Promise) {
      result.catch((error: unknown) => {
        body.replaceChildren(stateBlock("error", state.t("common.error"), String(error instanceof Error ? error.message : error)));
      });
    }
  } catch (error) {
    body.replaceChildren(stateBlock("error", state.t("common.error"), String(error instanceof Error ? error.message : error)));
  }
}

function pageHeader(): HTMLElement {
  const route = routeById(state.page);
  const head = el("div", { class: "cubi-page-head" });
  const copy = el("div");
  copy.append(
    el("span", { class: "cubi-eyebrow", text: route.enterpriseArea ? "CUBI ENTERPRISE" : "CUBI WORKBENCH" }),
    el("h1", { text: state.t(route.titleKey) }),
  );
  const subtitle = `${route.titleKey.replace(".title", ".subtitle")}`;
  copy.append(el("p", { text: state.t(subtitle) }));
  head.append(copy);
  return head;
}

function languageSelect(): HTMLElement {
  const wrapper = el("label", { class: "cubi-lang" });
  const control = el("select", { attrs: { "aria-label": state.t("common.locale") } });
  for (const locale of ENTERPRISE_LOCALES) {
    const option = el("option", { text: LOCALE_LABELS[locale] });
    option.value = locale;
    option.selected = locale === state.locale;
    control.append(option);
  }
  control.addEventListener("change", () => {
    const next = control.value as EnterpriseLocale;
    state.locale = next;
    rememberLocale(next);
    setDocumentLanguage();
    void rerender();
  });
  wrapper.append(control);
  return wrapper;
}

function renderPublic(): void {
  const root = document.getElementById("cubi-app");
  if (!root) return;
  const page = el("div", { class: "cubi-public" });
  page.append(publicNav());
  const host = el("div");
  page.append(host);
  const footer = el("footer", { class: "cubi-public-footer" });
  footer.append(
    el("span", { text: "© " + new Date().getFullYear() + " CUBI Platform. Enterprise and Engineering are separate environments." }),
    el("span", {}, link(pageHref("home"), "CUBI"), el("span", { text: " · " }), link(publicHelpUrl(), state.t("nav.help"), true)),
  );
  page.append(footer);
  root.replaceChildren(page);

  if (state.page === "home") {
    renderHome(publicContext(), host);
  } else if (state.page === "login") {
    renderLogin(publicContext(), host);
  } else {
    host.append(stateBlock("empty", "Not found", "This public page does not exist."));
  }
}

function publicContext(): PublicPageContext {
  const query = new URLSearchParams(window.location.search);
  return {
    projects: state.projects,
    locale: state.locale,
    t: state.t,
    query,
    navigate: (path) => navigate(path),
    open: (page, params) => navigate(pageHref(page, params)),
    toast,
    reloadProjects: loadProjects,
    signOut: doSignOut,
    onUnauthorized: () => sessionGate(window.location.pathname),
  };
}

export function isAuthenticated(): boolean {
  return Boolean(state.session);
}

async function doSignOut(): Promise<void> {
  try {
    await api.logout();
  } catch {
    // A missing session is already signed out; still clear local state.
  }
  state.session = null;
  navigate(`${BASE_PATH}/`, { replace: true });
}

async function loadProjects(): Promise<void> {
  if (!state.session) return;
  try {
    state.projects = await api.listProjects();
  } catch {
    state.projects = [];
  }
}

async function bootstrap(): Promise<void> {
  ensureStyles();
  setDocumentLanguage();
  toastHost = el("div", { class: "cubi-toast-host", attrs: { "aria-live": "polite" } });
  document.body.append(toastHost);
  try {
    state.session = await api.getSession();
  } catch (error) {
    if (error instanceof ApiError && error.status !== 401) {
      // Keep the page usable; pages surface their own connection state.
      state.session = null;
    } else {
      state.session = null;
    }
  }
  if (state.session) await loadProjects();
  state.booting = false;
}

async function rerender(): Promise<void> {
  state.page = resolvePage(window.location.pathname);
  state.t = translator(state.locale);
  setDocumentLanguage();
  if (!state.booted) {
    state.booted = true;
    await bootstrap();
  }
  const publicPage = state.page === "home" || state.page === "login" || state.page === "not-found";
  if (state.page === "not-found") {
    renderPlainNotFound();
    return;
  }
  if (publicPage) {
    renderPublic();
    return;
  }
  if (!state.session) {
    sessionGate(safeNextPath(window.location.pathname + window.location.search));
    return;
  }
  renderShell();
}

function renderPlainNotFound(): void {
  const root = document.getElementById("cubi-app");
  if (!root) return;
  root.replaceChildren(
    el("div", { class: "cubi-content" },
      stateBlock("empty", "Page not found", "The requested CUBI page does not exist.", [button("Go to workbench", () => navigate(pageHref("workbench")))]),
    ),
  );
}

export async function mountEnterpriseWorkbench(): Promise<void> {
  window.addEventListener("popstate", () => { void rerender(); });
  document.addEventListener("click", (event) => {
    const target = event.target as HTMLElement | null;
    const anchor = target?.closest("a");
    if (!anchor) return;
    const href = anchor.getAttribute("href");
    if (!href || anchor.target === "_blank" || anchor.hasAttribute("download")) return;
    if (!href.startsWith(`${BASE_PATH}/`) || href.startsWith("//")) return;
    event.preventDefault();
    navigate(href);
  });
  await rerender();
}

export function enterpriseRoutesForTest(): readonly string[] {
  return ROUTES.map((route) => `${BASE_PATH}/${route.segment}`);
}

export function sessionRolesSummary(roles: readonly string[]): string {
  const tier = enterpriseTier(roles);
  return tier ? `enterprise:${tier}` : "enterprise:none";
}

export function localeFallbackNotice(locale: EnterpriseLocale): string | null {
  return hasReviewedContent(locale) ? null : "Long-form content falls back to English for this locale.";
}

export { badge, el };
