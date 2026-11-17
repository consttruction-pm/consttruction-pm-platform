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
  displayed_dashboards: EnterpriseDashboardCatalogItem[];
  available_dashboards: EnterpriseDashboardCatalogItem[];
  read_at: string;
};
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
}

export type EnterpriseDashboardLocale = "en" | "fa";
export type EnterprisePortletState = "ready" | "empty" | "stale" | "missing" | "filtered" | "permission_denied" | "error";

export const ENTERPRISE_DASHBOARD_PORTLET_CATALOG: ReadonlyArray<{
  type_id: EnterprisePortletType;
  label: string;
  enabled: true;
}> = Object.freeze([
  { type_id: "portfolio-control-snapshot.v1", label: "Portfolio Control Snapshot", enabled: true },
  { type_id: "portfolio-decision.v1", label: "Portfolio Decision", enabled: true },
]);

export function orderDashboardCatalog(items: readonly EnterpriseDashboardCatalogItem[]): EnterpriseDashboardCatalogItem[] {
  return [...items].sort((a, b) =>
    a.display_order - b.display_order
    || a.dashboard.title.localeCompare(b.dashboard.title)
    || a.dashboard.dashboard_id.localeCompare(b.dashboard.dashboard_id),
  );
}

export function supportedDashboardPortlets(items: readonly EnterpriseDashboardPortlet[]): EnterpriseDashboardPortlet[] {
  const supported = new Set(ENTERPRISE_DASHBOARD_PORTLET_CATALOG.map((item) => item.type_id));
  return items.filter((item) => supported.has(item.type_id));
}

export function validateDashboardLayout(portlets: readonly EnterpriseDashboardPortlet[]): boolean {
  if (portlets.length > 12) return false;
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
    refresh: "Refresh", expand: "Expand", collapse: "Collapse", maximize: "Maximize", restore: "Restore",
    close: "Close", help: "Help", noDashboards: "No dashboards are available.", noPortlets: "This dashboard has no portlets.",
    loading: "Loading source data…", stale: "Source data is stale.", missing: "Source data is unavailable.",
    filtered: "No source rows match the current filters.", denied: "You do not have permission to view this source.",
    error: "The source could not be loaded.", empty: "No project records in this snapshot.", truncated: "Rows limited for display.",
    general: "General", content: "Content", layout: "Layout", access: "Access", save: "Save changes", cancel: "Cancel",
    name: "Dashboard name", description: "Description", maxRows: "Maximum rows per portlet", filterLock: "Restrict viewer filter overrides",
    addPortlet: "Add portlet", portfolioId: "Portfolio ID", decisionId: "Decision ID", portletTitle: "Portlet title",
    width: "Width", narrow: "Narrow", wide: "Wide", remove: "Remove", visibility: "Visibility",
    private: "Private", users: "Selected users", roles: "Enterprise roles", users_and_roles: "Users and roles", global: "All Enterprise users",
    accessNote: "Sharing changes are applied through the authorized access service; this view does not grant source access.",
    owner: "Owner", revision: "Revision", unsupported: "This portlet type is not enabled in this release.",
    drill: "Open source record", projects: "Projects", status: "Status", membership: "Membership", total: "Total",
    included: "Included", onHold: "On hold", excluded: "Excluded", noData: "No source data was returned.",
    archiveConfirm: "Archive this dashboard?", createName: "Enter a dashboard name.",
  },
  fa: {
    eyebrow: "کوبی سازمانی", title: "داشبوردها", subtitle: "نماهای سازمانی و سبد پروژه بر پایه داده‌های مجاز و معتبر.",
    create: "داشبورد جدید", search: "جستجوی داشبوردها", displayed: "نمایش‌داده‌شده", available: "در دسترس",
    open: "باز کردن", hide: "مخفی‌کردن", show: "نمایش", duplicate: "تکثیر", manage: "سفارشی‌سازی", archive: "بایگانی",
    refresh: "تازه‌سازی", expand: "بازکردن", collapse: "بستن", maximize: "بزرگ‌نمایی", restore: "بازگردانی",
    close: "بستن", help: "راهنما", noDashboards: "داشبوردی در دسترس نیست.", noPortlets: "این داشبورد پورلت ندارد.",
    loading: "دریافت داده منبع…", stale: "داده منبع قدیمی است.", missing: "داده منبع در دسترس نیست.",
    filtered: "رکوردی با فیلترهای فعلی مطابقت ندارد.", denied: "مجوز مشاهده این منبع را ندارید.",
    error: "دریافت منبع انجام نشد.", empty: "رکورد پروژه‌ای در این تصویر وجود ندارد.", truncated: "تعداد ردیف‌ها برای نمایش محدود شده است.",
    general: "عمومی", content: "محتوا", layout: "چیدمان", access: "دسترسی", save: "ذخیره تغییرات", cancel: "انصراف",
    name: "نام داشبورد", description: "شرح", maxRows: "حداکثر ردیف هر پورلت", filterLock: "محدودکردن تغییر فیلتر توسط بیننده",
    addPortlet: "افزودن پورلت", portfolioId: "شناسه سبد", decisionId: "شناسه تصمیم", portletTitle: "عنوان پورلت",
    width: "عرض", narrow: "باریک", wide: "عریض", remove: "حذف", visibility: "سطح دسترسی",
    private: "خصوصی", users: "کاربران منتخب", roles: "نقش‌های سازمانی", users_and_roles: "کاربران و نقش‌ها", global: "همه کاربران سازمان",
    accessNote: "تغییر اشتراک از مسیر سرویس مجاز دسترسی انجام می‌شود؛ نمایش داشبورد به‌تنهایی مجوز منبع ایجاد نمی‌کند.",
    owner: "مالک", revision: "بازبینی", unsupported: "این نوع پورلت در این نسخه فعال نیست.",
    drill: "بازکردن رکورد منبع", projects: "پروژه‌ها", status: "وضعیت", membership: "عضویت", total: "مجموع",
    included: "داخل سبد", onHold: "متوقف", excluded: "خارج از سبد", noData: "داده‌ای از منبع دریافت نشد.",
    archiveConfirm: "این داشبورد بایگانی شود؟", createName: "نام داشبورد را وارد کنید.",
  },
} as const;

type Copy = typeof COPY.en;
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

export async function mountEnterpriseDashboard(
  container: HTMLElement,
  client: EnterpriseDashboardClient,
  options: MountOptions = {},
): Promise<void> {
  const locale = options.locale ?? (navigator.language.toLowerCase().startsWith("fa") ? "fa" : "en");
  const t: Copy = COPY[locale];
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
  const refreshAll = button(t.refresh, () => loadCatalog());
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

  async function loadCatalog(): Promise<void> {
    status.textContent = t.loading;
    try {
      catalog = await client.listCatalog(searchTerm);
      renderCatalog();
      status.textContent = "";
      if (activeDashboardId && catalog.displayed_dashboards.some((item) => item.dashboard.dashboard_id === activeDashboardId)) {
        await openDashboard(activeDashboardId);
      }
    } catch {
      status.textContent = t.error;
      content.replaceChildren(node("div", "ced-error", t.error));
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
      for (const item of items) {
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
    const title = window.prompt(t.createName);
    if (!title?.trim()) return;
    await client.createDashboard({ title: title.trim(), description: "", context: "enterprise_home" });
    await loadCatalog();
  }
  async function openDashboard(dashboardId: string): Promise<void> {
    activeDashboardId = dashboardId;
    status.textContent = t.loading;
    renderTabs();
    try {
      const [stored, read] = await Promise.all([client.getDashboard(dashboardId), client.readPortlets(dashboardId)]);
      activeDefinition = stored.dashboard;
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
    content.append(titleRow);
    if (!activeRead.portlets.length) {
      content.append(node("p", "ced-muted", t.noPortlets));
      return;
    }
    for (const read of activeRead.portlets) content.append(renderPortlet(read));
  }
  function renderPortlet(read: EnterprisePortletRead): HTMLElement {
    const card = node("article", "ced-portlet");
    const head = node("header", "ced-portlet-head");
    const label = read.hide_title ? portletLabel(read.type_id) : (read.title || portletLabel(read.type_id));
    const headingNode = node("strong", "", label);
    const controls = node("div", "ced-toolbar");
    let expanded = true;
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
      expanded = !expanded;
      body.hidden = !expanded;
      collapse.textContent = expanded ? t.collapse : t.expand;
    });
    const maximize = button(t.maximize, () => {
      maximized = !maximized;
      card.classList.toggle("ced-maximized", maximized);
      maximize.textContent = maximized ? t.restore : t.maximize;
    });
    const refresh = button(t.refresh, async () => {
      if (!activeDefinition) return;
      const result = await client.readPortlets(activeDefinition.dashboard_id);
      activeRead = result;
      renderViewer();
    });
    const help = button(t.help, () => window.alert(`${label}\n${read.source_owner}\n${read.required_read_permission}`));
    const close = button(t.close, () => card.remove());
    controls.append(collapse, maximize, refresh, help, close);
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
    const dialog = node("dialog", "ced-dialog");
    const inner = node("div", "ced-dialog-inner");
    const title = node("h2", "", t.manage);
    const tabBar = node("nav", "ced-tabs");
    const panel = node("section");
    const footer = node("div", "ced-row");
    const save = button(t.save, async () => {
      if (!activeDefinition) return;
      const titleInput = dialog.querySelector<HTMLInputElement>("[name=dashboard-title]");
      const descriptionInput = dialog.querySelector<HTMLTextAreaElement>("[name=dashboard-description]");
      const rowsInput = dialog.querySelector<HTMLInputElement>("[name=max-rows]");
      const lockInput = dialog.querySelector<HTMLInputElement>("[name=filter-lock]");
      const nextPortlets = readEditorPortlets(dialog, activeDefinition.portlets);
      if (!validateDashboardLayout(nextPortlets)) {
        panel.prepend(node("p", "ced-error", "Invalid or overlapping portlet layout."));
        return;
      }
      await client.updateDashboard(activeDefinition.dashboard_id, {
        title: titleInput?.value.trim() || activeDefinition.title,
        description: descriptionInput?.value ?? activeDefinition.description,
        portlets: nextPortlets,
        filters: activeDefinition.filters,
        restrict_filter_override: lockInput?.checked ?? activeDefinition.restrict_filter_override,
        max_rows_per_portlet: Math.max(1, Math.min(500, Number(rowsInput?.value) || 100)),
      }, activeDefinition.revision);
      dialog.close();
      dialog.remove();
      await openDashboard(activeDefinition.dashboard_id);
      await loadCatalog();
    }, "ced-button primary");
    const cancel = button(t.cancel, () => { dialog.close(); dialog.remove(); });
    footer.append(save, cancel);
    const sections: Array<[string, () => void]> = [
      [t.general, () => renderGeneral()],
      [t.content, () => renderContent()],
      [t.layout, () => renderLayout()],
      [t.access, () => renderAccess()],
    ];
    function activateSection(index: number): void {
      tabBar.replaceChildren();
      sections.forEach(([label], i) => tabBar.append(button(label, () => activateSection(i), i === index ? "ced-button primary" : "ced-button")));
      panel.replaceChildren();
      sections[index][1]();
    }
    function renderGeneral(): void {
      const form = node("div", "ced-form-grid");
      form.append(field(t.name, input("dashboard-title", activeDefinition!.title)));
      const description = node("textarea", "ced-input");
      description.name = "dashboard-description";
      description.value = activeDefinition!.description;
      form.append(field(t.description, description));
      form.append(field(t.maxRows, input("max-rows", String(activeDefinition!.max_rows_per_portlet), "number")));
      const lock = node("input");
      lock.type = "checkbox"; lock.name = "filter-lock"; lock.checked = activeDefinition!.restrict_filter_override;
      form.append(field(t.filterLock, lock));
      panel.append(form);
    }
    function renderContent(): void {
      const list = node("div", "ced-section");
      activeDefinition!.portlets.forEach((portlet, index) => {
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
        const option = node("option", "", item.label);
        option.value = item.type_id;
        addType.append(option);
      }
      const portfolio = input("new-portfolio-id", "");
      const decision = input("new-decision-id", "");
      const add = button(t.addPortlet, () => {
        if (list.querySelectorAll(".ced-editor-portlet").length >= 12) return;
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
      panel.append(
        list,
        node("p", "ced-muted", t.unsupported),
        addType,
        field(t.portfolioId, portfolio),
        field(t.decisionId, decision),
        add,
      );
    }
    function renderLayout(): void {
      const list = node("div");
      activeDefinition!.portlets.forEach((portlet) => {
        list.append(node("p", "ced-muted", `${portletLabel(portlet.type_id)} · ${portlet.layout.w === 12 ? t.wide : t.narrow} · row ${portlet.layout.y + 1}`));
      });
      panel.append(list, node("p", "ced-muted", "Narrow/Wide layout follows the two-column dashboard grid. Width can be changed in Content."));
    }
    function renderAccess(): void {
      const mode = node("div", "ced-panel");
      mode.append(node("strong", "", t.visibility), node("p", "", t[activeDefinition!.visibility]));
      mode.append(node("p", "ced-muted", t.accessNote));
      mode.append(node("p", "ced-muted", `${t.owner}: ${activeDefinition!.owner_user_id}`));
      panel.append(mode);
    }
    inner.append(title, tabBar, panel, footer);
    dialog.append(inner);
    container.append(dialog);
    activateSection(0);
    dialog.showModal();
  }
  function readEditorPortlets(dialog: HTMLDialogElement, original: EnterpriseDashboardPortlet[]): EnterpriseDashboardPortlet[] {
    const result: EnterpriseDashboardPortlet[] = [];
    for (const [index, portlet] of original.entries()) {
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

  await loadCatalog();
  if (catalog?.displayed_dashboards.length) await openDashboard(catalog.displayed_dashboards[0].dashboard.dashboard_id);
}
