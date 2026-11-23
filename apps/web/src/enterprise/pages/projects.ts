import type { PageContext } from "../app.js";
import {
  ApiError,
  api,
  probe,
  type CapabilityProbe,
  type DocumentRecord,
  type ProjectSummary,
  type ResourceRecord,
} from "../api.js";
import { enterpriseIcon, type EnterpriseIconName } from "../icons.js";
import { pageHref } from "../router.js";
import { formatDate, formatDateTime } from "../session.js";
import { badge, el, stateBlock, tabs, type Translator } from "../ui.js";
import {
  connectionList,
  detailList,
  emptyLine,
  note,
  pageActions,
  section,
  sectionBody,
  selectControl,
  sourceState,
  testId,
  textInput,
} from "./shared.js";

/**
 * Page 8 — Enterprise projects register and project portal (ENT-07).
 *
 * The register is the server project read. Every tab reads an official
 * project-scoped route and reports its exact state, source and revision. The
 * page never calculates a schedule, CPM, progress or earned value: those stay
 * authoritative in the Engineering environment.
 */

type TabId = "overview" | "engineering" | "resources" | "documents" | "risk" | "reports";
type SortKey = "name" | "revision" | "start" | "finish";
type StaleCheck = () => boolean;

const TAB_IDS: readonly TabId[] = ["overview", "engineering", "resources", "documents", "risk", "reports"];

const TABS: readonly { id: TabId; labelKey: string; icon: EnterpriseIconName }[] = [
  { id: "overview", labelKey: "ent07.tab.overview", icon: "project-overview" },
  { id: "engineering", labelKey: "ent07.tab.engineering", icon: "project-engineering" },
  { id: "resources", labelKey: "ent07.tab.resources", icon: "project-resources" },
  { id: "documents", labelKey: "ent07.tab.documents", icon: "project-documents" },
  { id: "risk", labelKey: "ent07.tab.risks", icon: "project-risks" },
  { id: "reports", labelKey: "ent07.tab.reports", icon: "project-reports" },
];

const SORT_KEYS: readonly SortKey[] = ["name", "revision", "start", "finish"];

const SORT_LABEL_KEYS: Record<SortKey, string> = {
  name: "ent07.register.sortName",
  revision: "ent07.register.sortRevision",
  start: "ent07.register.sortStart",
  finish: "ent07.register.sortFinish",
};

/** Bumped once per page mount; invalidates work from a previous route. */
let pageEpoch = 0;
/** Bumped on every repaint; invalidates work for a tab that is no longer shown. */
let paintEpoch = 0;

export function renderProjects(ctx: PageContext, host: HTMLElement): void {
  const pageToken = ++pageEpoch;
  const query = ctx.query;
  const requested = query.get("project") ?? "";
  const initialTab: TabId = isTab(query.get("tab")) ? (query.get("tab") as TabId) : "overview";

  let projects: ProjectSummary[] = ctx.projects;
  let sharedProjects: ProjectSummary[] = ctx.sharedProjects;
  let selected: ProjectSummary | null =
    projects.find((project) => project.project_id === requested)
    ?? sharedProjects.find((project) => project.project_id === requested)
    ?? projects[0]
    ?? sharedProjects[0]
    ?? null;
  let receivedAt = new Date();
  let busy = false;
  let lastError: unknown = null;
  let loadedOnce = projects.length > 0 || sharedProjects.length > 0;
  let tab: TabId = initialTab;
  /** Updates the toolbar while a refresh is in flight, without a repaint. */
  let syncBusy: (() => void) | null = null;

  const filters = {
    q: query.get("q") ?? "",
    status: query.get("status") ?? "all",
    sort: isSort(query.get("sort")) ? (query.get("sort") as SortKey) : ("name" as SortKey),
  };

  const tabParam = (id: TabId): string | null => (id === "overview" ? null : id);

  const hrefFor = (projectId: string | null, targetTab: TabId = tab): string =>
    pageHref("projects", {
      project: projectId,
      tab: tabParam(targetTab),
      q: filters.q || null,
      status: filters.status !== "all" ? filters.status : null,
      sort: filters.sort !== "name" ? filters.sort : null,
    });

  /** Keep the selection, tab and toolbar state in the address bar. */
  const rememberUrl = (): void => {
    const href = hrefFor(selected?.project_id ?? null);
    const current = `${window.location.pathname}${window.location.search}`;
    if (current !== href) window.history.replaceState({}, "", href);
  };

  const paint = (): void => {
    paintEpoch += 1;
    host.replaceChildren();
    buildRegister();
    buildSharedWorkspace();
    if (selected) buildPortal(selected);
    rememberUrl();
  };

  const refresh = async (): Promise<void> => {
    if (busy) return;
    busy = true;
    lastError = null;
    syncBusy?.();
    try {
      const [personalResult, sharedResult] = await Promise.allSettled([
        api.listProjects(),
        api.listSharedProjects(),
      ]);
      if (pageToken !== pageEpoch) return;
      if (personalResult.status === "rejected") throw personalResult.reason;
      projects = personalResult.value;
      sharedProjects = sharedResult.status === "fulfilled" ? sharedResult.value : [];
      receivedAt = new Date();
      const wanted = selected?.project_id ?? null;
      selected = (wanted
        ? projects.find((project) => project.project_id === wanted)
          ?? sharedProjects.find((project) => project.project_id === wanted)
          ?? null
        : null) ?? projects[0] ?? sharedProjects[0] ?? null;
      loadedOnce = true;
      busy = false;
      paint();
    } catch (error) {
      if (pageToken !== pageEpoch) return;
      busy = false;
      if (errorKind(error) === "unauthenticated") {
        ctx.onUnauthorized();
        return;
      }
      lastError = error;
      loadedOnce = true;
      paint();
    }
  };

  const navigateTo = (projectId: string | null, targetTab: TabId): void => {
    ctx.navigate(hrefFor(projectId, targetTab));
  };

  function buildRegister(): void {
    const t = ctx.t;
    const register = section(t("ent07.register.title"), t("ent07.register.description"));
    testId(register, "projects-register");

    const retry = (): void => {
      void refresh();
    };

    if (!projects.length) {
      if (!loadedOnce && !lastError) {
        sectionBody(register, stateBlock("loading", t("common.loading"), t("ent07.register.description")));
        host.append(register);
        return;
      }
      if (lastError) {
        sectionBody(register, registerFailure(ctx, lastError, retry));
        host.append(register);
        return;
      }
      sectionBody(
        register,
        stateBlock("empty", t("ent07.register.emptyTitle"), t("ent07.register.emptyBody"), [
          actionButton(t("ent07.register.refresh"), retry, "cubi-btn cubi-btn-secondary", "action-refresh"),
        ]),
      );
      host.append(register);
      return;
    }

    const statuses = [...new Set(projects.map((project) => project.status || "unknown"))].sort();
    const tableHost = el("div");
    const count = el("span", { class: "cubi-field-hint", attrs: { "aria-live": "polite" } });
    testId(count, "projects-count");
    const freshnessText = el("span");
    const freshness = el("span", { class: "cubi-freshness", attrs: { "aria-live": "polite" } },
      el("span", { class: "dot" }),
      freshnessText,
    );
    testId(freshness, "projects-freshness");
    const sortSelect = selectControl(
      SORT_KEYS.map((key) => ({ value: key, label: t(SORT_LABEL_KEYS[key]) })),
      filters.sort,
      (value) => {
        filters.sort = value as SortKey;
        paintRows();
        rememberUrl();
      },
    );
    sortSelect.setAttribute("aria-label", t("ent07.register.sortLabel"));
    sortSelect.title = t("ent07.register.sortLabel");
    testId(sortSelect, "projects-sort");

    const statusSelect = selectControl(
      [{ value: "all", label: t("ent07.register.allStatuses") }, ...statuses.map((status) => ({ value: status, label: statusLabel(status, t) }))],
      filters.status,
      (value) => {
        filters.status = value;
        paintRows();
        rememberUrl();
      },
    );
    statusSelect.setAttribute("aria-label", t("ent07.register.statusLabel"));
    statusSelect.title = t("ent07.register.statusLabel");
    testId(statusSelect, "projects-filter-status");

    const search = textInput({
      type: "search",
      placeholder: t("ent07.register.searchPlaceholder"),
      value: filters.q,
      name: "project-search",
    });
    search.setAttribute("aria-label", t("ent07.register.searchLabel"));
    search.title = t("ent07.register.searchLabel");
    testId(search, "projects-search");
    search.addEventListener("input", () => {
      filters.q = search.value;
      paintRows();
      rememberUrl();
    });

    const refreshControl = actionButton(
      busy ? t("ent07.register.refreshing") : t("ent07.register.refresh"),
      () => {
        void refresh();
      },
      "cubi-btn cubi-btn-secondary cubi-icon-btn",
      "action-refresh",
    );
    refreshControl.disabled = busy;
    refreshControl.title = t("ent07.register.refresh");
    testId(refreshControl, "projects-refresh");

    const label = refreshControl.querySelector("span");
    syncBusy = () => {
      refreshControl.disabled = busy;
      if (label) label.textContent = busy ? t("ent07.register.refreshing") : t("ent07.register.refresh");
      freshness.className = `cubi-freshness${busy ? " is-busy" : lastError ? " is-stale" : ""}`;
    };

    const toolbar = el(
      "div",
      { class: "cubi-toolbar cubi-register-toolbar" },
      el("label", { class: "cubi-toolbar-field", title: t("ent07.register.searchLabel") }, enterpriseIcon("projects-search"), search),
      el("label", { class: "cubi-toolbar-field", title: t("ent07.register.statusLabel") }, enterpriseIcon("projects-filter-status"), statusSelect),
      el("label", { class: "cubi-toolbar-field", title: t("ent07.register.sortLabel") }, enterpriseIcon("projects-sort"), sortSelect),
      el("div", { class: "cubi-toolbar-group" }, refreshControl, freshness),
    );

    const epsPanel = el(
      "div",
      { class: "cubi-note" },
      el("strong", { text: `${t("ent07.register.epsTitle")}: ` }),
      badge(t("common.notConnected"), "neutral"),
      el("span", { text: ` ${t("ent07.register.epsBody")}` }),
    );
    testId(epsPanel, "projects-eps");

    const paintRows = (): void => {
      const rows = rowsFor(projects, filters, ctx.locale);
      count.textContent = t("ent07.register.count", { shown: rows.length, total: projects.length });
      freshnessText.textContent = t("ent07.register.received", {
        time: formatDateTime(receivedAt.toISOString(), ctx.locale),
      });
      freshness.className = `cubi-freshness${busy ? " is-busy" : lastError ? " is-stale" : ""}`;
      tableHost.replaceChildren(buildTable(ctx, rows, selected, filters.sort, (key) => {
        filters.sort = key;
        sortSelect.value = key;
        paintRows();
        rememberUrl();
      }, (projectId) => {
        navigateTo(projectId, tab);
      }, (projectId) => hrefFor(projectId, tab)));
      if (lastError && projects.length) {
        tableHost.prepend(registerFailure(ctx, lastError, () => {
          void refresh();
        }));
      }
    };

    sectionBody(register, toolbar, count, epsPanel, tableHost);
    host.append(register);
    paintRows();
  }

  function buildSharedWorkspace(): void {
    if (!sharedProjects.length) return;
    const shared = section(
      "Shared build workspace",
      "In-progress Engineering and Enterprise workspace. It is intentionally separate from the user-owned Projects register and portfolio counts.",
    );
    testId(shared, "shared-build-workspace");
    const rows = el("div", { class: "cubi-list" });
    for (const project of sharedProjects) {
      const open = actionLink("Open shared workspace", hrefFor(project.project_id, "overview"), "project-open");
      rows.append(el("div", { class: "cubi-list-item" },
        el("div", {}, el("strong", { text: project.name }), el("div", { class: "cubi-field-hint", text: project.project_id })),
        open,
      ));
    }
    sectionBody(shared, rows);
    host.append(shared);
  }

  function buildPortal(project: ProjectSummary): void {
    const t = ctx.t;
    const isShared = sharedProjects.some((item) => item.project_id === project.project_id);
    const portal = section(
      project.name,
      `${isShared ? "Shared in-progress workspace" : t("ent07.field.projectId")}: ${project.project_id} · ${t("common.revision")}: ${project.revision}`,
    );
    testId(portal, "projects-portal");

    const paintToken = paintEpoch;
    const tabBar = tabs(
      TABS.map((entry) => ({
        id: entry.id,
        label: t(entry.labelKey),
        icon: enterpriseIcon(entry.icon),
        testId: `tab-${entry.id}`,
      })),
      tab,
      (id) => {
        tab = id;
        navigateTo(project.project_id, id);
      },
    );
    const tabHost = el("div");
    testId(tabHost, "project-tab-body");
    sectionBody(portal, tabBar, tabHost);
    host.append(portal);
    void renderTab(ctx, tabHost, project, tab, pageToken, paintToken, receivedAt);
  }

  /** A register that arrived empty is not evidence of an empty account. */
  const start = (): void => {
    if (projects.length || sharedProjects.length) {
      paint();
      return;
    }
    paint();
    void refresh();
  };

  start();
}

/* --------------------------------------------------------------------------
 * Register rendering
 * ----------------------------------------------------------------------- */

function buildTable(
  ctx: PageContext,
  rows: ProjectSummary[],
  selected: ProjectSummary | null,
  sort: SortKey,
  onSort: (key: SortKey) => void,
  onOpen: (projectId: string) => void,
  hrefForProject: (projectId: string) => string,
): HTMLElement {
  const t = ctx.t;
  const wrapper = el("div", { class: "cubi-table-wrap" });
  testId(wrapper, "projects-table");
  const table = el("table", { class: "cubi-table" });
  table.append(el("caption", { class: "cubi-visually-hidden", text: t("ent07.register.title") }));

  const sortable = (key: SortKey, label: string): HTMLElement => {
    const active = sort === key;
    const th = el("th", {
      attrs: {
        scope: "col",
        ...(active ? { "aria-sort": key === "revision" ? "descending" : "ascending" } : {}),
      },
    });
    const control = el("button", { class: "cubi-sort-btn", attrs: { type: "button" } });
    control.append(el("span", { text: label }), enterpriseIcon("projects-sort"));
    control.title = `${t("ent07.register.sortLabel")}: ${label}`;
    control.addEventListener("click", () => onSort(key));
    th.append(control);
    return th;
  };

  const headRow = el("tr");
  headRow.append(
    sortable("name", t("ent07.register.colProject")),
    el("th", { text: t("ent07.register.colStatus"), attrs: { scope: "col" } }),
    el("th", { text: t("ent07.register.colDomain"), attrs: { scope: "col" } }),
    sortable("revision", t("common.revision")),
    sortable("start", t("ent07.register.colStart")),
    sortable("finish", t("ent07.register.colFinish")),
    el("th", { text: t("ent07.register.colActions"), attrs: { scope: "col" } }),
  );
  table.append(el("thead", {}, headRow));

  const body = el("tbody");
  if (!rows.length) {
    body.append(
      el("tr", {}, el("td", {
        class: "cubi-table-empty",
        text: t("ent07.register.noMatch"),
        attrs: { colspan: "7" },
      })),
    );
  }
  for (const project of rows) {
    const isSelected = project.project_id === selected?.project_id;
    const row = el("tr", {
      class: `cubi-row-action${isSelected ? " is-selected" : ""}`,
      attrs: { tabindex: "0", "data-project-id": project.project_id },
    });
    if (isSelected) row.setAttribute("aria-current", "true");
    row.addEventListener("click", () => onOpen(project.project_id));
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        onOpen(project.project_id);
      }
    });

    const open = el("a", { class: "cubi-btn cubi-btn-ghost cubi-icon-btn" });
    open.href = hrefForProject(project.project_id);
    open.append(enterpriseIcon("project-open"), el("span", { text: t("ent07.register.open") }));
    open.title = t("ent07.register.open");
    open.addEventListener("click", (event) => event.stopPropagation());

    row.append(
      el("td", {}, el("strong", { text: project.name }), el("div", { class: "cubi-field-hint", text: project.project_id })),
      el("td", {}, badge(statusLabel(project.status, t), statusTone(project.status))),
      el("td", { text: project.business_domain || "—" }),
      el("td", { text: String(project.revision) }),
      el("td", { text: formatDate(project.start_date, ctx.locale) }),
      el("td", { text: formatDate(project.finish_date, ctx.locale) }),
      el("td", {}, open),
    );
    body.append(row);
  }
  table.append(body);
  wrapper.append(table);
  return wrapper;
}

function registerFailure(ctx: PageContext, error: unknown, retry: () => void): HTMLElement {
  const t = ctx.t;
  const kind = errorKind(error);
  const detail = error instanceof ApiError ? `${error.code} (HTTP ${error.status})` : String(error);
  const action = actionButton(t("common.retry"), retry, "cubi-btn cubi-btn-secondary");
  if (kind === "forbidden") {
    return stateBlock("forbidden", t("ent07.register.title"), `${t("common.forbidden")} ${detail}`, [action]);
  }
  if (kind === "disconnected") {
    return stateBlock("unavailable", t("ent07.register.disconnectedTitle"), `${t("ent07.register.disconnectedBody")} (${detail})`, [action]);
  }
  return stateBlock("error", t("ent07.register.errorTitle"), `${detail} — ${t("ent07.register.disconnectedBody")}`, [action]);
}

/* --------------------------------------------------------------------------
 * Portal tabs
 * ----------------------------------------------------------------------- */

async function renderTab(
  ctx: PageContext,
  host: HTMLElement,
  project: ProjectSummary,
  tab: TabId,
  pageToken: number,
  paintToken: number,
  receivedAt: Date,
): Promise<void> {
  const t = ctx.t;
  const stale: StaleCheck = () => pageToken !== pageEpoch || paintToken !== paintEpoch;
  const retry = (): void => {
    void renderTab(ctx, host, project, tab, pageToken, paintToken, receivedAt);
  };
  host.replaceChildren(stateBlock("loading", t("common.loading"), project.name));

  try {
    if (tab === "overview") {
      let live = project;
      try {
        live = await api.getProject(project.project_id);
      } catch (error) {
        if (stale()) return;
        if (errorKind(error) === "unauthenticated") {
          ctx.onUnauthorized();
          return;
        }
        host.replaceChildren(projectReadFailure(ctx, error, retry));
        return;
      }
      if (stale()) return;
      host.replaceChildren(overviewBody(ctx, live, receivedAt));
      return;
    }

    if (tab === "engineering") {
      const [workspace, issues, evm] = await Promise.all([
        probe(`/api/projects/${encodeURIComponent(project.project_id)}/p6/workspace`),
        probe(`/api/projects/${encodeURIComponent(project.project_id)}/p6/issues`),
        probe(`/api/projects/${encodeURIComponent(project.project_id)}/p6/earned-value`),
      ]);
      if (stale()) return;
      const connections = connectionList(
        [
          { label: t("ent07.engineering.workspace"), probe: workspace },
          { label: t("ent07.engineering.issues"), probe: issues },
          { label: t("ent07.engineering.evm"), probe: evm },
        ],
        t,
      );
      testId(connections, "engineering-connections");
      host.replaceChildren(
        el("p", { class: "desc", text: t("ent07.engineering.description") }),
        note(t("ent07.overview.boundary"), "warning"),
        connections,
        stampLine(t, `/api/projects/${project.project_id}/p6/*`, project.revision, receivedAt, ctx.locale),
        pageActions(actionLink(t("ent07.engineering.open"), "/app/", "project-engineering")),
      );
      return;
    }

    if (tab === "resources") {
      const capability = await probe(`/api/projects/${encodeURIComponent(project.project_id)}/p6/resources`);
      if (stale()) return;
      if (capability.state !== "available") {
        host.replaceChildren(
          sourceState(capability, t, {
            title: t("ent07.resources.title"),
            source: t("ent07.resources.description"),
            retry,
          }),
        );
        return;
      }
      const rows = await api.listResources(project.project_id);
      if (stale()) return;
      host.replaceChildren(
        el("p", { class: "desc", text: t("ent07.resources.description") }),
        rows.length ? resourcesTable(rows, t) : emptyLine(t("ent07.resources.empty")),
        stampLine(t, `/api/projects/${project.project_id}/p6/resources`, project.revision, receivedAt, ctx.locale),
      );
      return;
    }

    if (tab === "documents") {
      const capability = await probe(`/api/projects/${encodeURIComponent(project.project_id)}/documents`);
      if (stale()) return;
      if (capability.state !== "available") {
        host.replaceChildren(
          sourceState(capability, t, {
            title: t("ent07.documents.title"),
            source: t("ent07.documents.description"),
            retry,
          }),
        );
        return;
      }
      const rows = await api.listDocuments(project.project_id);
      if (stale()) return;
      host.replaceChildren(
        el("p", { class: "desc", text: t("ent07.documents.description") }),
        rows.length ? documentsTable(rows, t) : emptyLine(t("ent07.documents.empty")),
        stampLine(
          t,
          `/api/projects/${project.project_id}/documents`,
          t("common.notProvided"),
          receivedAt,
          ctx.locale,
        ),
      );
      return;
    }

    if (tab === "risk") {
      const [risksCapability, issuesCapability] = await Promise.all([
        probe(`/api/projects/${encodeURIComponent(project.project_id)}/risks`),
        probe(`/api/projects/${encodeURIComponent(project.project_id)}/p6/issues`),
      ]);
      if (stale()) return;
      const blocks: HTMLElement[] = [el("p", { class: "desc", text: t("ent07.risks.description") })];
      if (risksCapability.state === "available") {
        const risks = await api.listRisks(project.project_id);
        if (stale()) return;
        blocks.push(risks.length ? risksTable(risks, t) : emptyLine(t("ent07.risks.empty")));
      } else {
        blocks.push(
          sourceState(risksCapability, t, {
            title: t("ent07.risks.title"),
            source: "/api/projects/{id}/risks",
            retry,
          }),
        );
      }
      blocks.push(el("h3", { class: "cubi-card-title", text: t("ent07.risks.issuesTitle") }));
      if (issuesCapability.state === "available") {
        const issues = await api.listIssues(project.project_id);
        if (stale()) return;
        blocks.push(issues.length ? issuesTable(issues, t) : emptyLine(t("ent07.risks.issuesEmpty")));
      } else {
        blocks.push(
          sourceState(issuesCapability, t, {
            title: t("ent07.risks.issuesTitle"),
            source: "/api/projects/{id}/p6/issues",
            retry,
          }),
        );
      }
      blocks.push(stampLine(t, `/api/projects/${project.project_id}/risks`, project.revision, receivedAt, ctx.locale));
      host.replaceChildren(...blocks);
      return;
    }

    const [catalogueCapability, definitionsCapability] = await Promise.all([
      probe(`/api/projects/${encodeURIComponent(project.project_id)}/reports/catalogue`),
      probe(`/api/projects/${encodeURIComponent(project.project_id)}/reports`),
    ]);
    if (stale()) return;
    const blocks: HTMLElement[] = [el("p", { class: "desc", text: t("ent07.reports.description") })];
    if (definitionsCapability.state === "available") {
      const rows = await api.listReports(project.project_id);
      if (stale()) return;
      blocks.push(rows.length ? reportsTable(rows, t) : emptyLine(t("ent07.reports.empty")));
    } else {
      blocks.push(
        sourceState(definitionsCapability, t, {
          title: t("ent07.reports.title"),
          source: "/api/projects/{id}/reports",
          retry,
        }),
      );
    }
    blocks.push(el("h3", { class: "cubi-card-title", text: t("ent07.reports.catalogue") }));
    if (catalogueCapability.state === "available") {
      const catalogue = await api.reportCatalogue(project.project_id);
      if (stale()) return;
      blocks.push(catalogue.length ? catalogueTable(catalogue, t) : emptyLine(t("ent07.reports.catalogueEmpty")));
    } else {
      blocks.push(
        sourceState(catalogueCapability, t, {
          title: t("ent07.reports.catalogue"),
          source: "/api/projects/{id}/reports/catalogue",
          retry,
        }),
      );
    }
    blocks.push(stampLine(t, `/api/projects/${project.project_id}/reports`, project.revision, receivedAt, ctx.locale));
    host.replaceChildren(...blocks);
  } catch (error) {
    if (stale()) return;
    if (errorKind(error) === "unauthenticated") {
      ctx.onUnauthorized();
      return;
    }
    host.replaceChildren(projectReadFailure(ctx, error, retry));
  }
}

function overviewBody(ctx: PageContext, project: ProjectSummary, receivedAt: Date): HTMLElement {
  const t = ctx.t;
  const body = el(
    "div",
    {},
    el("p", { class: "desc", text: t("ent07.overview.description") }),
    el(
      "div",
      { class: "cubi-split" },
      el(
        "div",
        {},
        el("h3", { class: "cubi-card-title", text: t("ent07.overview.identity") }),
        detailList([
          [t("ent07.field.project"), project.name],
          [t("ent07.field.projectId"), project.project_id],
          [t("ent07.field.tenant"), project.tenant_id ?? ctx.session.tenant_id],
          [t("ent07.field.revision"), String(project.revision)],
          [t("common.status"), statusLabel(project.status, t)],
          [t("ent07.field.domain"), project.business_domain || "—"],
          [t("ent07.field.manager"), project.obs_responsible_manager || "—"],
          [t("ent07.field.website"), project.website_url || "—"],
        ]),
        stampLine(t, `/api/projects/${project.project_id}`, project.revision, receivedAt, ctx.locale),
      ),
      el(
        "div",
        {},
        el("h3", { class: "cubi-card-title", text: t("ent07.overview.schedule") }),
        detailList([
          [t("ent07.field.start"), formatDate(project.start_date, ctx.locale)],
          [t("ent07.field.finish"), formatDate(project.finish_date, ctx.locale)],
          [t("ent07.field.dateSystem"), project.date_system || "—"],
          [t("ent07.field.checkout"), project.checkout_state || "—"],
        ]),
        note(t("ent07.overview.boundary"), "info"),
      ),
    ),
    pageActions(
      actionLink(t("ent07.overview.openEngineering"), "/app/", "project-engineering"),
      actionLink(t("ent07.overview.openPortfolio"), pageHref("portfolio", { project: project.project_id })),
    ),
  );
  testId(body, "project-overview");
  return body;
}

function projectReadFailure(ctx: PageContext, error: unknown, retry: () => void): HTMLElement {
  const t = ctx.t;
  const kind = errorKind(error);
  const detail = error instanceof ApiError ? `${error.code} (HTTP ${error.status})` : String(error);
  const action = actionButton(t("common.retry"), retry, "cubi-btn cubi-btn-secondary");
  if (kind === "forbidden") {
    return stateBlock("forbidden", t("ent07.tab.overview"), `${t("common.forbidden")} ${detail}`, [action]);
  }
  if (kind === "disconnected") {
    return stateBlock("unavailable", t("ent07.register.disconnectedTitle"), `${t("ent07.register.disconnectedBody")} (${detail})`, [action]);
  }
  return stateBlock("error", t("ent07.register.errorTitle"), `${detail}`, [action]);
}

/* --------------------------------------------------------------------------
 * Tab tables
 * ----------------------------------------------------------------------- */

function resourcesTable(rows: ResourceRecord[], t: Translator): HTMLElement {
  return simpleTable(
    [t("ent07.resources.colResource"), t("ent07.resources.colType"), t("ent07.resources.colUnit"), t("ent07.resources.colCalendar"), t("ent07.resources.colActive"), t("common.revision")],
    rows,
    (row) => [
      el("span", {}, el("strong", { text: row.name }), el("div", { class: "cubi-field-hint", text: row.resource_id })),
      row.resource_type,
      row.unit_of_measure || "—",
      row.calendar_id || "—",
      badge(row.is_active ? t("status.active") : t("common.unavailable"), row.is_active ? "success" : "neutral"),
      String(row.record_revision),
    ],
    "tab-resources-table",
  );
}

function documentsTable(rows: DocumentRecord[], t: Translator): HTMLElement {
  return simpleTable(
    [t("ent07.documents.colDocument"), t("ent07.documents.colType"), t("common.status")],
    rows,
    (row) => [
      el("span", {}, el("strong", { text: row.title }), el("div", { class: "cubi-field-hint", text: row.document_id })),
      String(row.resource_type ?? row.document_type ?? "—"),
      badge(String(row.status ?? "—"), "neutral"),
    ],
    "tab-documents-table",
  );
}

function risksTable(rows: Record<string, unknown>[], t: Translator): HTMLElement {
  return simpleTable(
    [t("ent07.risks.colRecord"), t("common.status"), t("ent07.risks.colSeverity"), t("common.revision")],
    rows,
    (row, index) => [
      el("span", {}, el("strong", { text: String(row.title ?? row.risk_id ?? `#${index + 1}`) }), el("div", { class: "cubi-field-hint", text: String(row.risk_id ?? "") })),
      String(row.status ?? "—"),
      String(row.exposure_level ?? row.severity ?? row.rating ?? "—"),
      String(row.revision ?? row.record_revision ?? "—"),
    ],
    "tab-risks-table",
  );
}

function issuesTable(rows: Record<string, unknown>[], t: Translator): HTMLElement {
  return simpleTable(
    [t("ent07.risks.colRecord"), t("common.status"), t("ent07.risks.colSeverity"), t("common.revision")],
    rows,
    (row, index) => {
      const issue = (row.issue ?? row) as Record<string, unknown>;
      return [
        el("span", {}, el("strong", { text: String(issue.title ?? issue.issue_id ?? `#${index + 1}`) }), el("div", { class: "cubi-field-hint", text: String(issue.issue_id ?? "") })),
        String(issue.status ?? "—"),
        String(issue.priority ?? "—"),
        String(issue.record_revision ?? issue.revision ?? "—"),
      ];
    },
    "tab-issues-table",
  );
}

function reportsTable(rows: Record<string, unknown>[], t: Translator): HTMLElement {
  return simpleTable(
    [t("ent07.reports.colReport"), t("ent07.reports.colSubject"), t("common.revision")],
    rows,
    (row) => [
      el("span", {}, el("strong", { text: String(row.name ?? row.report_id ?? "—") }), el("div", { class: "cubi-field-hint", text: String(row.report_id ?? "") })),
      String(row.subject ?? "—"),
      String(row.record_revision ?? row.revision ?? "—"),
    ],
    "tab-reports-table",
  );
}

function catalogueTable(rows: Record<string, unknown>[], t: Translator): HTMLElement {
  return simpleTable(
    [t("ent07.reports.colSubject"), t("ent07.reports.colReport")],
    rows,
    (row) => [
      el("span", {}, el("strong", { text: String(row.label ?? row.subject ?? "—") }), el("div", { class: "cubi-field-hint", text: String(row.subject ?? "") })),
      String(Array.isArray(row.fields) ? `${(row.fields as unknown[]).length} ${t("common.details")}` : "—"),
    ],
    "tab-catalogue-table",
  );
}

function simpleTable<T>(
  labels: string[],
  rows: T[],
  render: (row: T, index: number) => (Node | string)[],
  testid?: string,
): HTMLElement {
  const wrapper = el("div", { class: "cubi-table-wrap" });
  if (testid) testId(wrapper, testid);
  const table = el("table", { class: "cubi-table" });
  table.append(el("thead", {}, el("tr", {}, ...labels.map((label) => el("th", { text: label, attrs: { scope: "col" } })))));
  const body = el("tbody");
  rows.slice(0, 200).forEach((row, index) => {
    const tr = el("tr");
    for (const cell of render(row, index)) tr.append(el("td", {}, cell));
    body.append(tr);
  });
  table.append(body);
  wrapper.append(table);
  return wrapper;
}

/* --------------------------------------------------------------------------
 * Small helpers
 * ----------------------------------------------------------------------- */

function isTab(value: string | null): boolean {
  return Boolean(value) && (TAB_IDS as readonly string[]).includes(value as string);
}

function isSort(value: string | null): boolean {
  return Boolean(value) && (SORT_KEYS as readonly string[]).includes(value as string);
}

function statusLabel(status: string | null | undefined, t: Translator): string {
  if (!status) return t("ent07.register.unknownStatus");
  const known: Record<string, string> = {
    active: "status.active",
    completed: "status.completed",
    pending: "status.pending",
    draft: "status.draft",
    archived: "status.archived",
    locked: "status.locked",
  };
  const key = known[status.toLowerCase()];
  return key ? t(key) : status;
}

function statusTone(status: string | null | undefined): "success" | "neutral" | "warning" | "danger" {
  switch ((status ?? "").toLowerCase()) {
    case "active":
      return "success";
    case "completed":
      return "neutral";
    case "locked":
    case "archived":
      return "warning";
    default:
      return "neutral";
  }
}

function rowsFor(projects: ProjectSummary[], filters: { q: string; status: string; sort: SortKey }, locale: string): ProjectSummary[] {
  const needle = filters.q.trim().toLocaleLowerCase(locale);
  return projects
    .filter((project) => {
      if (filters.status !== "all" && (project.status || "unknown") !== filters.status) return false;
      if (!needle) return true;
      return `${project.name} ${project.project_id} ${project.business_domain ?? ""}`.toLocaleLowerCase(locale).includes(needle);
    })
    .sort((left, right) => {
      switch (filters.sort) {
        case "revision":
          return right.revision - left.revision;
        case "start":
          return String(left.start_date ?? "").localeCompare(String(right.start_date ?? ""));
        case "finish":
          return String(left.finish_date ?? "").localeCompare(String(right.finish_date ?? ""));
        default:
          return left.name.localeCompare(right.name, locale);
      }
    });
}

function errorKind(error: unknown): "forbidden" | "unauthenticated" | "disconnected" | "error" {
  if (error instanceof ApiError) {
    if (error.status === 401) return "unauthenticated";
    if (error.status === 403) return "forbidden";
    if (error.status === 0) return "disconnected";
  }
  return "error";
}

function stampLine(
  t: Translator,
  source: string,
  revision: number | string | null | undefined,
  receivedAt: Date,
  locale: string,
): HTMLElement {
  const parts = [
    `${t("common.source")}: ${source}`,
    `${t("common.revision")}: ${revision ?? "—"}`,
    t("ent07.register.received", { time: formatDateTime(receivedAt.toISOString(), locale) }),
  ];
  return el("p", { class: "cubi-note", text: parts.join(" · ") });
}

function actionLink(text: string, href: string, icon?: EnterpriseIconName): HTMLAnchorElement {
  const anchor = el("a", { class: "cubi-btn cubi-btn-secondary cubi-icon-btn" });
  anchor.href = href;
  if (icon) anchor.append(enterpriseIcon(icon));
  anchor.append(el("span", { text }));
  return anchor;
}

function actionButton(text: string, onClick: () => void, className: string, icon?: EnterpriseIconName): HTMLButtonElement {
  const button = el("button", { class: className, attrs: { type: "button" } });
  if (icon) button.append(enterpriseIcon(icon));
  button.append(el("span", { text }));
  button.addEventListener("click", onClick);
  return button;
}

/** Kept because the page previously re-exported the formatter for its callers. */
export { formatDateTime };

/* Pure helpers are exported for the ENT-07 unit tests. */
export {
  TABS as PROJECT_TABS,
  rowsFor as filterAndSortProjects,
  statusLabel as projectStatusLabel,
  isTab as isProjectTab,
  isSort as isProjectSort,
  errorKind as projectErrorKind,
};
