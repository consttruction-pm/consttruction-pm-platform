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
import { enterpriseIcon, type EnterpriseIconName } from "./icons.js";
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
import {
  renderRisks,
  renderDocuments,
  renderEps,
  renderTimesheets,
  renderNotifications,
  renderSettings,
  renderForms,
  renderDirectory,
} from "./pages/registers.js";
import { renderAudit } from "./pages/audit.js";
import { renderMemberActivities } from "./pages/member-activities.js";

export type ToastKind = "info" | "error";

export type PageContext = {
  session: SessionInfo;
  projects: ProjectSummary[];
  sharedProjects: ProjectSummary[];
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
  risks: renderRisks,
  documents: renderDocuments,
  eps: renderEps,
  timesheets: renderTimesheets,
  notifications: renderNotifications,
  settings: renderSettings,
  forms: renderForms,
  audit: renderAudit,
  directory: renderDirectory,
  memberActivities: renderMemberActivities,
};

type AppState = {
  session: SessionInfo | null;
  projects: ProjectSummary[];
  sharedProjects: ProjectSummary[];
  locale: EnterpriseLocale;
  page: PageId;
  booting: boolean;
  booted: boolean;
  t: (key: string, vars?: Record<string, string | number>) => string;
};

const state: AppState = {
  session: null,
  projects: [],
  sharedProjects: [],
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
  // The Personal Workbench and the environment selector are the single
  // signed-in entry owned by the shared application shell. The Enterprise
  // sidebar links there instead of mounting a second, parallel workbench.
  if (id === "workbench" || id === "environments") return "/workbench/";
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

/**
 * Top-bar Help control (icon register `top-help`). The visible graphic is a
 * real SVG; the localised label is exposed to assistive technology and as the
 * native tooltip, so the control is never an unexplained "?" glyph.
 */
function helpButton(label: string): HTMLAnchorElement {
  const anchor = link(publicHelpUrl(), "", true, "cubi-btn cubi-btn-ghost cubi-icon-only");
  anchor.append(enterpriseIcon("top-help", label));
  anchor.title = label;
  anchor.setAttribute("aria-label", label);
  return anchor;
}

function sessionGate(nextPath: string): void {
  navigate(`${pageHref("login")}?next=${encodeURIComponent(nextPath)}`, { replace: true });
}

/**
 * Shell navigation entries that carry a registered semantic icon. Only the
 * Projects register is in the ENT-07 icon register; every other entry keeps its
 * text-only rendering.
 */
const NAV_ICONS: Partial<Record<PageId, EnterpriseIconName>> = { projects: "nav-projects" };

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
      const item = el("a");
      const iconName = NAV_ICONS[id];
      if (iconName) item.append(enterpriseIcon(iconName));
      item.append(el("span", { text: state.t(routeById(id).titleKey) }));
      item.href = appHref(id);
      if (state.page === id) item.setAttribute("aria-current", "page");
      section.append(item);
    }
    nav.append(section);
  };
  group("nav.group.entry", ["roles", "workbench", "environments"]);
  group("nav.group.enterprise", ["dashboard", "portfolio", "projects", "eps", "access", "directory", "tasks", "memberActivities", "timesheets", "workflows", "approvals", "risks", "documents", "resources", "reports", "notifications", "knowledge", "forms", "settings", "audit"]);
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
    // The Personal Workbench is one canonical document at /workbench/; the
    // Enterprise application must not mount a second copy of it.
    link("/workbench/", state.t("nav.workbench")),
    el("span", { class: "sep", text: "/" }),
    el("span", { text: state.t(route.titleKey) }),
  );
  const topActions = el("div", { class: "cubi-topbar-actions" });
  const access = environmentAccess(session);
  topActions.append(
    el("span", { class: "cubi-env-pill", text: access.enterprise.allowed ? state.t("brand.enterprise") : state.t("brand.enterprise") + " · " + state.t("common.restricted") }),
  );
  topActions.append(searchBox(), notificationsBell(), link("/workbench/", state.t("nav.workbench"), false, "cubi-btn cubi-btn-ghost"));
  if (access.engineering.allowed) {
    // Switching environments uses the same session; the Engineering server
    // re-authorizes every project request.
    topActions.append(link("/app?view=live", state.t("nav.engineering"), false, "cubi-btn cubi-btn-ghost"));
  }
  topActions.append(
    languageSelect(),
    helpButton(state.t("nav.help")),
  );
  topbar.append(crumbs, topActions);
  installTopbarShortcuts();

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
    sharedProjects: state.sharedProjects,
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

type SearchHit = { label: string; detail: string; href: string };

function searchHits(raw: string): SearchHit[] {
  const needle = raw.trim().toLocaleLowerCase();
  if (!needle) return [];
  const hits: SearchHit[] = [];
  for (const route of ROUTES) {
    if (!route.requiresSession || route.id === "login" || route.id === "not-found") continue;
    const label = state.t(route.titleKey);
    if (`${label} ${route.segment}`.toLocaleLowerCase().includes(needle)) {
      hits.push({ label, detail: `Enterprise · ${pageHref(route.id)}`, href: pageHref(route.id) });
    }
  }
  for (const project of state.projects) {
    if (`${project.name} ${project.project_id}`.toLocaleLowerCase().includes(needle)) {
      hits.push({ label: project.name, detail: `Project · ${project.project_id}`, href: pageHref("projects", { project: project.project_id }) });
    }
  }
  return hits.slice(0, 8);
}

/**
 * Topbar search over the routes this deployment actually serves and the
 * projects the session can read. It navigates; it does not fabricate results
 * from pages the router does not know about.
 */
function searchBox(): HTMLElement {
  const wrap = el("div", { class: "cubi-search" });
  const input = el("input", {
    class: "cubi-search-input",
    attrs: {
      type: "search",
      id: "cubi-global-search",
      placeholder: state.t("common.search"),
      "aria-label": `${state.t("common.search")} — pages and projects`,
      "aria-controls": "cubi-search-results",
      "aria-expanded": "false",
      autocomplete: "off",
      spellcheck: "false",
    },
  });
  const results = el("div", { class: "cubi-search-results", attrs: { id: "cubi-search-results", role: "listbox" } });
  results.hidden = true;
  let hits: SearchHit[] = [];
  let active = -1;

  const close = (): void => {
    results.hidden = true;
    results.replaceChildren();
    hits = [];
    active = -1;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
  };

  const paint = (): void => {
    results.replaceChildren();
    if (!hits.length) {
      results.append(el("div", { class: "cubi-search-empty", text: state.t("common.noResults") }));
      results.hidden = false;
      input.setAttribute("aria-expanded", "true");
      return;
    }
    hits.forEach((hit, index) => {
      const item = el("a", { class: `cubi-search-hit${index === active ? " is-active" : ""}`, attrs: { href: hit.href, role: "option", id: `cubi-search-hit-${index}`, "aria-selected": index === active ? "true" : "false" } });
      item.append(el("strong", { text: hit.label }), el("span", { text: hit.detail }));
      results.append(item);
    });
    results.hidden = false;
    input.setAttribute("aria-expanded", "true");
    input.setAttribute("aria-activedescendant", `cubi-search-hit-${Math.max(active, 0)}`);
  };

  input.addEventListener("input", () => {
    hits = searchHits(input.value);
    active = hits.length ? 0 : -1;
    if (input.value.trim()) paint();
    else close();
  });
  input.addEventListener("focus", () => {
    if (input.value.trim()) {
      hits = searchHits(input.value);
      active = hits.length ? 0 : -1;
      paint();
    }
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      close();
      input.blur();
      return;
    }
    if (event.key === "ArrowDown" && hits.length) {
      event.preventDefault();
      active = (active + 1) % hits.length;
      paint();
      return;
    }
    if (event.key === "ArrowUp" && hits.length) {
      event.preventDefault();
      active = (active - 1 + hits.length) % hits.length;
      paint();
      return;
    }
    if (event.key === "Enter" && active >= 0 && hits[active]) {
      event.preventDefault();
      const href = hits[active].href;
      close();
      navigate(href);
    }
  });
  wrap.append(input, results);
  return wrap;
}

/**
 * Notification indicator. The count comes from the notification register this
 * session can read; an unread count is shown only for records the server marks
 * as `unread`. A read failure is reported in the tooltip, never as zero.
 */
function notificationsBell(): HTMLElement {
  const title = state.t("page.notifications.title");
  const anchor = el("a", { class: "cubi-bell", attrs: { href: pageHref("notifications"), "aria-label": title, title } });
  anchor.append(el("span", { class: "cubi-bell-glyph", attrs: { "aria-hidden": "true" } }));
  const count = el("span", { class: "cubi-bell-count", attrs: { hidden: "hidden" } });
  anchor.append(count);
  void api.enterpriseList("notifications", { limit: "50" }).then((payload) => {
    const items = payload.items ?? [];
    const unread = items.filter((item) => String(item.status ?? "").toLowerCase() === "unread").length;
    anchor.title = `${title}: ${items.length} record(s), ${unread} unread`;
    if (unread > 0) {
      count.textContent = String(unread);
      count.removeAttribute("hidden");
    }
  }).catch((error: unknown) => {
    const detail = error instanceof ApiError ? `${error.code} (HTTP ${error.status})` : "unavailable";
    anchor.title = `${title} — ${detail}`;
  });
  return anchor;
}

let shortcutsInstalled = false;

function installTopbarShortcuts(): void {
  if (shortcutsInstalled) return;
  shortcutsInstalled = true;
  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      const input = document.getElementById("cubi-global-search");
      if (input instanceof HTMLInputElement) {
        event.preventDefault();
        input.focus();
        input.select();
      }
    }
  });
  document.addEventListener("mousedown", (event) => {
    const wrap = document.querySelector(".cubi-search");
    if (wrap instanceof HTMLElement && event.target instanceof Node && !wrap.contains(event.target)) {
      const results = document.getElementById("cubi-search-results");
      if (results instanceof HTMLElement) results.hidden = true;
    }
  });
}

function renderPublic(): void {  const root = document.getElementById("cubi-app");
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
  // Sign-out returns to the canonical sign-in page, not the public home, so the
  // next step is always a deliberate re-authentication.
  window.location.assign("/login");
}

async function loadProjects(): Promise<void> {
  if (!state.session) return;
  const [personal, shared] = await Promise.allSettled([
    api.listProjects(),
    api.listSharedProjects(),
  ]);
  state.projects = personal.status === "fulfilled" ? personal.value : [];
  state.sharedProjects = shared.status === "fulfilled" ? shared.value : [];
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
  if ((state.page === "workbench" || state.page === "environments") && window.location.pathname !== "/workbench/") {
    // The Personal Workbench is the single signed-in entry for both
    // environments. These legacy /cubi paths must not render a parallel copy.
    window.location.replace("/workbench/");
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
