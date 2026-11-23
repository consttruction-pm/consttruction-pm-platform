import type { PageContext } from "../app.js";
import { ApiError, api, probe } from "../api.js";
import { badge, el, stateBlock } from "../ui.js";
import {
  emptyLine,
  note,
  pageActions,
  projectFilterOptions,
  readLocalJson,
  section,
  sectionBody,
  selectControl,
  sourceStamp,
  sourceState,
  testId,
  textInput,
  writeLocalJson,
} from "./shared.js";

/**
 * Page 6 — Enterprise dashboards and portlets.
 *
 * Layout, order, size and visibility are user preferences kept on this device
 * and labelled as such. The server dashboard route is probed, never simulated.
 * Portlets display only data returned by their owning source, with source,
 * revision and freshness attached. No indicator is calculated here.
 */

type PortletKey =
  | "schedule"
  | "portfolio"
  | "evm"
  | "capacity"
  | "tasks"
  | "approvals"
  | "risks"
  | "documents"
  | "reports"
  | "access";

type Size = "narrow" | "standard" | "wide";
type Visibility = "private" | "team" | "organization";

type PortletDef = {
  key: PortletKey;
  title: string;
  source: string;
  description: string;
  needsProject: boolean;
  endpoint: (projectId: string) => string;
};

type Layout = {
  dashboard: string;
  revision: number;
  updated_at: string;
  visibility: Visibility;
  portlets: { key: PortletKey; size: Size }[];
  server_id?: string;
  server_revision?: number;
};

type DashboardDef = { id: string; name: string; description: string; defaultPortlets: PortletKey[] };

const STORAGE_KEY = "cubi.enterprise.dashboards.v1";

const PORTLETS: PortletDef[] = [
  { key: "schedule", title: "Schedule health", source: "Engineering schedule read model", description: "Milestones, critical path and look-ahead state. Owned and calculated only by Engineering.", needsProject: true, endpoint: (id) => `/api/enterprise/portlets/schedule-health?project_id=${encodeURIComponent(id)}` },
  { key: "portfolio", title: "Portfolio status", source: "/api/projects", description: "The accessible project register with its server revision.", needsProject: false, endpoint: () => "/api/projects" },
  { key: "evm", title: "Cost & EVM summary", source: "Engineering EVM source", description: "Earned value indicators. This workbench never computes PV, EV, AC, CV, SV or indices.", needsProject: true, endpoint: (id) => `/api/enterprise/portlets/evm-summary?project_id=${encodeURIComponent(id)}` },
  { key: "capacity", title: "Resource capacity", source: "Engineering capacity read model", description: "Capacity segments aggregated by their owner; no client-side roll-up.", needsProject: true, endpoint: (id) => `/api/enterprise/portlets/resource-capacity?project_id=${encodeURIComponent(id)}` },
  { key: "tasks", title: "Task throughput", source: "Enterprise Task API v1", description: "Generic enterprise tasks. Not Engineering activities and not timesheets.", needsProject: true, endpoint: (id) => `/api/enterprise/tasks?project_id=${encodeURIComponent(id)}` },
  { key: "approvals", title: "Approval queue", source: "Enterprise approval API", description: "Revision-pinned decisions awaiting action.", needsProject: false, endpoint: () => "/api/enterprise/approvals" },
  { key: "risks", title: "Risk register", source: "Project risk register", description: "Risk records from the project register, shown read-only.", needsProject: true, endpoint: (id) => `/api/projects/${encodeURIComponent(id)}/risks` },
  { key: "documents", title: "Document control", source: "Project document register", description: "Document records with their server revision.", needsProject: true, endpoint: (id) => `/api/projects/${encodeURIComponent(id)}/documents` },
  { key: "reports", title: "Report definitions", source: "Existing report runtime", description: "Report definitions from the shared reporting service; no second queue.", needsProject: true, endpoint: (id) => `/api/projects/${encodeURIComponent(id)}/reports` },
  { key: "access", title: "Access governance", source: "Enterprise organization API", description: "Organizations, roles and grants. Server authorization only.", needsProject: false, endpoint: () => "/api/enterprise/organizations" },
];

const DASHBOARDS: DashboardDef[] = [
  { id: "delivery", name: "Delivery overview", description: "Schedule, portfolio, cost, capacity and work-in-flight for delivery leads.", defaultPortlets: ["schedule", "portfolio", "evm", "capacity", "tasks", "approvals"] },
  { id: "executive", name: "Executive portfolio", description: "Portfolio, indicators, approvals and operational reporting for executives.", defaultPortlets: ["portfolio", "evm", "tasks", "approvals", "reports", "access"] },
  { id: "governance", name: "Access & governance", description: "Access, approvals, documents, risks and reporting evidence.", defaultPortlets: ["access", "approvals", "documents", "risks", "reports", "tasks"] },
];

type DashboardState = {
  dashboardId: string;
  projectId: string;
  filter: string;
  designer: boolean;
  layouts: Record<string, Layout>;
};

export function renderDashboard(ctx: PageContext, host: HTMLElement): void {
  const stored = readLocalJson<Record<string, Layout>>(STORAGE_KEY, {});
  const state: DashboardState = {
    dashboardId: DASHBOARDS[0].id,
    projectId: ctx.projects[0]?.project_id ?? "",
    filter: "",
    designer: false,
    layouts: { ...defaultLayouts(), ...stored },
  };
  const root = el("div");
  host.append(root);
  const paint = (): void => {
    root.replaceChildren(...build(ctx, state, paint));
  };
  paint();
}

function build(ctx: PageContext, state: DashboardState, paint: () => void): HTMLElement[] {
  const dashboard = DASHBOARDS.find((item) => item.id === state.dashboardId) ?? DASHBOARDS[0];
  const layout = state.layouts[dashboard.id] ?? defaultLayout(dashboard);
  state.layouts[dashboard.id] = layout;

  const nodes: HTMLElement[] = [];

  const toolbarCard = section("Dashboard controls", "Choose a dashboard, filter the scope and refresh. Layout changes are saved to the server dashboard API and cached on this device.");
  const toolbar = el("div", { class: "cubi-toolbar" });
  const selector = testId(selectControl(DASHBOARDS.map((item) => ({ value: item.id, label: item.name })), dashboard.id, (value) => {
    state.dashboardId = value;
    paint();
  }), "dashboard-selector");
  const projectFilter = testId(selectControl(
    projectFilterOptions(ctx.projects, ctx.sharedProjects ?? [], "No project filter"),
    state.projectId,
    (value) => {
      state.projectId = value;
      paint();
    },
  ), "dashboard-project-filter");
  const filterInput = testId(textInput({ placeholder: "Filter portlets", value: state.filter }), "dashboard-text-filter");
  filterInput.addEventListener("input", () => {
    state.filter = filterInput.value;
    paint();
  });
  filterInput.setAttribute("aria-label", "Filter portlets by title");
  const refresh = el("button", { class: "cubi-btn cubi-btn-secondary", text: ctx.t("common.refresh"), attrs: { type: "button" } });
  refresh.addEventListener("click", () => {
    ctx.toast("Re-read every portlet source.", "info");
    paint();
  });
  const designerButton = el("button", { class: `cubi-btn ${state.designer ? "cubi-btn-primary" : "cubi-btn-secondary"}`, text: state.designer ? "Close designer" : "Designer", attrs: { type: "button" } });
  designerButton.addEventListener("click", () => {
    state.designer = !state.designer;
    paint();
  });
  toolbar.append(selector, projectFilter, filterInput, refresh, designerButton);
  sectionBody(toolbarCard, toolbar, dashboardStatus(ctx, layout, paint));
  testId(toolbarCard, "dashboard-toolbar");
  nodes.push(toolbarCard);

  if (state.designer) nodes.push(designerPanel(ctx, state, dashboard, layout, paint));

  const grid = el("div", { class: "cubi-dash-layout" });
  testId(grid, "dashboard-portlets");
  const visible = layout.portlets.filter((entry) => {
    const def = portletDef(entry.key);
    return !state.filter || def.title.toLowerCase().includes(state.filter.toLowerCase());
  });
  if (visible.length === 0) {
    grid.append(stateBlock("empty", "No portlet matches", "Clear the filter or add a portlet in the designer."));
  }
  for (const entry of visible) {
    grid.append(portletCard(ctx, state, layout, entry, paint));
  }
  nodes.push(grid);
  return nodes;
}

function dashboardStatus(ctx: PageContext, layout: Layout, paint: () => void): HTMLElement {
  const row = el("div", { class: "cubi-row" });
  row.append(
    badge(`Layout revision ${layout.revision}`, "info"),
    badge(`Saved ${formatTime(layout.updated_at)}`, "neutral"),
    badge(
      layout.server_id ? `Server sync: saved at revision ${layout.server_revision ?? "—"}` : "Server sync: not confirmed",
      layout.server_id ? "success" : "warning",
    ),
    badge(`Visibility: ${layout.visibility}${layout.server_id ? " · server " + layout.server_id : " (local)"}`, layout.server_id ? "success" : "neutral"),
  );
  const reset = el("button", { class: "cubi-btn cubi-btn-ghost", text: "Reset layout", attrs: { type: "button" } });
  reset.addEventListener("click", () => {
    const dashboard = DASHBOARDS.find((item) => item.id === layout.dashboard) ?? DASHBOARDS[0];
    layout.portlets = dashboard.defaultPortlets.map((key) => ({ key, size: "standard" }));
    layout.revision += 1;
    layout.updated_at = new Date().toISOString();
    persist(layout, ctx);
    paint();
  });
  row.append(reset, el("span", { class: "cubi-field-hint", text: "Layouts are stored with this browser and saved to the dashboard register. The visibility value is metadata; it is not an access-control rule in preview." }));
  return row;
}

function designerPanel(ctx: PageContext, state: DashboardState, dashboard: DashboardDef, layout: Layout, paint: () => void): HTMLElement {
  const card = section("Dashboard designer", "Add, remove, reorder and resize portlets. Drag a portlet row or use the arrow buttons.");
  const wrap = el("div", { class: "cubi-designer" });

  const catalog = el("div", { class: "cubi-catalog" });
  catalog.append(el("p", { class: "cubi-eyebrow", text: "Portlet catalog" }));
  for (const def of PORTLETS) {
    const item = el("div", { class: "cubi-catalog-item" });
    const text = el("div", {}, el("strong", { text: def.title }), el("span", { text: `${def.source} · ${def.description}` }));
    const installed = layout.portlets.some((entry) => entry.key === def.key);
    const add = el("button", { class: "cubi-btn cubi-btn-secondary", text: installed ? "Added" : "Add", attrs: { type: "button" } });
    add.disabled = installed;
    add.addEventListener("click", () => {
      layout.portlets.push({ key: def.key, size: "standard" });
      layout.revision += 1;
      layout.updated_at = new Date().toISOString();
      persist(layout, ctx);
      paint();
    });
    item.append(text, add);
    catalog.append(item);
  }

  const installed = el("div", { class: "cubi-catalog" });
  installed.append(el("p", { class: "cubi-eyebrow", text: `Installed (${layout.portlets.length})` }));
  layout.portlets.forEach((entry, index) => {
    const def = portletDef(entry.key);
    const row = el("div", { class: "cubi-catalog-item", attrs: { draggable: "true" } });
    row.dataset.index = String(index);
    row.addEventListener("dragstart", (event) => {
      event.dataTransfer?.setData("text/plain", String(index));
    });
    row.addEventListener("dragover", (event) => event.preventDefault());
    row.addEventListener("drop", (event) => {
      event.preventDefault();
      const from = Number(event.dataTransfer?.getData("text/plain") ?? "-1");
      if (from < 0 || from === index) return;
      const [moved] = layout.portlets.splice(from, 1);
      layout.portlets.splice(index, 0, moved);
      layout.revision += 1;
      layout.updated_at = new Date().toISOString();
      persist(layout, ctx);
      paint();
    });

    const text = el("div", {}, el("strong", { text: `${def.title} · ${def.source}` }), el("span", { text: `${entry.size}` }));
    const controls = el("div", { class: "cubi-portlet-actions" });
    const up = el("button", { text: "↑", attrs: { type: "button", "aria-label": `Move ${def.title} up` } });
    up.disabled = index === 0;
    up.addEventListener("click", () => {
      [layout.portlets[index - 1], layout.portlets[index]] = [layout.portlets[index], layout.portlets[index - 1]];
      layout.revision += 1;
      layout.updated_at = new Date().toISOString();
      persist(layout, ctx);
      paint();
    });
    const down = el("button", { text: "↓", attrs: { type: "button", "aria-label": `Move ${def.title} down` } });
    down.disabled = index === layout.portlets.length - 1;
    down.addEventListener("click", () => {
      [layout.portlets[index + 1], layout.portlets[index]] = [layout.portlets[index], layout.portlets[index + 1]];
      layout.revision += 1;
      layout.updated_at = new Date().toISOString();
      persist(layout, ctx);
      paint();
    });
    const sizes = el("select", { class: "cubi-input", attrs: { "aria-label": `Size of ${def.title}` } });
    for (const size of ["narrow", "standard", "wide"] as Size[]) {
      const option = el("option", { text: size });
      option.value = size;
      option.selected = entry.size === size;
      sizes.append(option);
    }
    sizes.addEventListener("change", () => {
      entry.size = sizes.value as Size;
      layout.revision += 1;
      layout.updated_at = new Date().toISOString();
      persist(layout, ctx);
      paint();
    });
    const remove = el("button", { text: "✕", attrs: { type: "button", "aria-label": `Remove ${def.title}` } });
    remove.addEventListener("click", () => {
      layout.portlets.splice(index, 1);
      layout.revision += 1;
      layout.updated_at = new Date().toISOString();
      persist(layout, ctx);
      paint();
    });
    controls.append(up, down, sizes, remove);
    row.append(text, controls);
    installed.append(row);
  });

  const sharing = el("div", { class: "cubi-catalog" });
  sharing.append(
    el("p", { class: "cubi-eyebrow", text: "Sharing & visibility" }),
    selectControl([
      { value: "private", label: "Private to me" },
      { value: "team", label: "Share with my team" },
      { value: "organization", label: "Visible to the organization" },
    ], layout.visibility, (value) => {
      layout.visibility = value as Visibility;
      layout.updated_at = new Date().toISOString();
      persist(layout, ctx);
      paint();
    }),
    note("Visibility is saved with the server dashboard record. In preview it is metadata only: it does not restrict who can read the dashboard.", "warning"),
  );

  wrap.append(catalog, el("div", {}, installed, sharing));
  sectionBody(card, wrap, pageActions(
    actionButton("Save layout", () => {
      layout.revision += 1;
      layout.updated_at = new Date().toISOString();
      void persist(layout, ctx, true).then(paint);
    }),
    actionButton("Restore defaults", () => {
      layout.portlets = dashboard.defaultPortlets.map((key) => ({ key, size: "standard" }));
      layout.revision += 1;
      layout.updated_at = new Date().toISOString();
      persist(layout, ctx);
      paint();
    }),
  ));
  testId(card, "dashboard-designer");
  return card;
}

function portletCard(
  ctx: PageContext,
  state: DashboardState,
  layout: Layout,
  entry: { key: PortletKey; size: Size },
  paint: () => void,
): HTMLElement {
  const def = portletDef(entry.key);
  const className = `cubi-portlet ${entry.size === "narrow" ? "narrow" : entry.size === "wide" ? "wide" : ""}`.trim();
  const card = el("article", { class: className });
  card.dataset.portlet = def.key;
  card.draggable = true;
  card.addEventListener("dragstart", (event) => {
    const index = layout.portlets.findIndex((item) => item.key === entry.key);
    event.dataTransfer?.setData("text/plain", String(index));
  });
  card.addEventListener("dragover", (event) => event.preventDefault());
  card.addEventListener("drop", (event) => {
    event.preventDefault();
    const from = Number(event.dataTransfer?.getData("text/plain") ?? "-1");
    const to = layout.portlets.findIndex((item) => item.key === entry.key);
    if (from < 0 || to < 0 || from === to) return;
    const [moved] = layout.portlets.splice(from, 1);
    layout.portlets.splice(to, 0, moved);
    layout.revision += 1;
    layout.updated_at = new Date().toISOString();
    persist(layout, ctx);
    paint();
  });

  const head = el("header", { class: "cubi-portlet-head" });
  head.append(el("div", {}, el("strong", { text: def.title }), el("span", { class: "cubi-field-hint", text: ` · ${def.source}` })));
  const actions = el("div", { class: "cubi-portlet-actions" });
  const sizeButton = el("button", { text: entry.size === "wide" ? "standard" : entry.size === "standard" ? "narrow" : "wide", attrs: { type: "button", "aria-label": "Cycle portlet size" } });
  sizeButton.addEventListener("click", () => {
    entry.size = entry.size === "wide" ? "standard" : entry.size === "standard" ? "narrow" : "wide";
    layout.revision += 1;
    layout.updated_at = new Date().toISOString();
    persist(layout, ctx);
    paint();
  });
  const remove = el("button", { text: "✕", attrs: { type: "button", "aria-label": `Remove ${def.title}` } });
  remove.addEventListener("click", () => {
    layout.portlets = layout.portlets.filter((item) => item.key !== entry.key);
    layout.revision += 1;
    layout.updated_at = new Date().toISOString();
    persist(layout, ctx);
    paint();
  });
  actions.append(sizeButton, remove);
  head.append(actions);
  card.append(head);

  const body = el("div", { class: "cubi-portlet-body" });
  body.append(el("div", { class: "cubi-loading" }, el("div", { class: "cubi-spinner" }), el("span", { text: ctx.t("common.loading") })));
  card.append(body);
  testId(card, `portlet-${def.key}`);

  if (def.needsProject && !state.projectId) {
    body.replaceChildren(stateBlock("empty", "Select a project", "This portlet reads a project-scoped source. Choose a project filter above."));
    return card;
  }

  const path = def.endpoint(state.projectId);
  void probe(path).then(async (probeState) => {
    if (probeState.state !== "available") {
      body.replaceChildren(sourceState(probeState, ctx.t, { title: def.title, source: def.source, retry: paint }));
      return;
    }
    try {
      const content = await loadPortletData(ctx, def.key, state.projectId);
      body.replaceChildren(content.node);
      if (content.revision !== null || content.updated !== null) {
        body.append(sourceStamp(def.source, content.revision, content.updated, ctx.locale));
      } else {
        body.append(sourceStamp(def.source, "per record", null, ctx.locale));
      }
    } catch (error) {
      const detail = error instanceof ApiError ? `${error.code} (HTTP ${error.status})` : String(error);
      body.replaceChildren(stateBlock("error", `${def.title} could not be read`, `${detail}. Nothing was substituted.`));
    }
  });

  return card;
}

type PortletData = { node: HTMLElement; revision: number | string | null; updated: string | null };

async function loadPortletData(ctx: PageContext, key: PortletKey, projectId: string): Promise<PortletData> {
  if (key === "portfolio") {
    if (!ctx.projects.length) return { node: emptyLine("No accessible project."), revision: null, updated: null };
    const table = simpleTable(["Project", "Status", "Revision"], ctx.projects.slice(0, 8).map((project) => [project.name, project.status ?? "—", String(project.revision)]));
    return { node: table, revision: "per project", updated: null };
  }
  if (key === "documents") {
    const rows = await api.listDocuments(projectId);
    if (!rows.length) return { node: emptyLine("No document is registered for this project."), revision: null, updated: null };
    return {
      node: simpleTable(["Document", "Type", "Status", "Revision"], rows.slice(0, 8).map((row) => [row.title, String(row.document_type ?? "—"), String(row.status ?? "—"), String(row.revision ?? "—")])),
      revision: "per document",
      updated: null,
    };
  }
  if (key === "risks") {
    const rows = await api.listRisks(projectId);
    if (!rows.length) return { node: emptyLine("No risk is registered for this project."), revision: null, updated: null };
    return {
      node: simpleTable(["Risk", "Status", "Severity", "Revision"], rows.slice(0, 8).map((row, index) => [
        String(row.title ?? row.name ?? row.risk_id ?? `Record ${index + 1}`),
        String(row.status ?? "—"),
        String(row.severity ?? row.rating ?? "—"),
        String(row.revision ?? row.record_revision ?? "—"),
      ])),
      revision: "per risk",
      updated: null,
    };
  }
  if (key === "reports") {
    const rows = await api.listReports(projectId);
    if (!rows.length) return { node: emptyLine("No report definition is registered for this project."), revision: null, updated: null };
    return {
      node: simpleTable(["Report", "Subject", "Revision"], rows.slice(0, 8).map((row) => [String(row.name ?? row.report_id), String(row.subject ?? "—"), String(row.revision ?? "—")])),
      revision: "per definition",
      updated: null,
    };
  }
  // Connected but a summary contract that the workbench must not invent.
  const descriptions: Record<string, string> = {
    schedule: "The schedule summary is served by the Engineering schedule read model. Open the Engineering workspace to inspect the authoritative schedule.",
    evm: "Earned-value indicators are produced only by the Engineering EVM source. This portlet will show them unchanged, with source revision, once that source responds.",
    capacity: "Capacity is owned by Engineering. This workbench will display the aggregated read model verbatim; it will never recompute utilisation.",
    tasks: "Task records are available through the Enterprise Task API. Open Team & task center for the full register.",
    approvals: "Approval decisions are available through the approval API. Open the approval center to review revision-pinned items.",
    access: "Organization and grant records are available through the organization API. Open Organization & access.",
  };
  return {
    node: el("p", { class: "cubi-field-hint", text: descriptions[key] ?? "This source responded. Open its center for the full record." }),
    revision: null,
    updated: null,
  };
}

function simpleTable(headers: string[], rows: string[][]): HTMLElement {
  const wrap = el("div", { class: "cubi-table-wrap" });
  const table = el("table", { class: "cubi-table" });
  table.append(el("thead", {}, el("tr", {}, ...headers.map((header) => el("th", { text: header })))));
  const body = el("tbody");
  for (const row of rows) {
    body.append(el("tr", {}, ...row.map((cell, index) => el("td", {}, index === 0 ? el("strong", { text: cell }) : el("span", { text: cell })))));
  }
  table.append(body);
  wrap.append(table);
  return wrap;
}

function portletDef(key: PortletKey): PortletDef {
  return PORTLETS.find((item) => item.key === key) ?? PORTLETS[0];
}

function defaultLayout(dashboard: DashboardDef): Layout {
  return {
    dashboard: dashboard.id,
    revision: 1,
    updated_at: new Date().toISOString(),
    visibility: "private",
    portlets: dashboard.defaultPortlets.map((key) => ({ key, size: "standard" })),
  };
}

function defaultLayouts(): Record<string, Layout> {
  const result: Record<string, Layout> = {};
  for (const dashboard of DASHBOARDS) result[dashboard.id] = defaultLayout(dashboard);
  return result;
}

function persist(layout: Layout, ctx: PageContext, announce = false): Promise<void> {
  const stored = readLocalJson<Record<string, Layout>>(STORAGE_KEY, {});
  stored[layout.dashboard] = layout;
  if (!writeLocalJson(STORAGE_KEY, stored)) ctx.toast("This browser refused local storage; the layout will not persist.", "error");
  return syncServer(layout, ctx, announce);
}

async function syncServer(layout: Layout, ctx: PageContext, announce = false): Promise<void> {
  const definition = DASHBOARDS.find((item) => item.id === layout.dashboard);
  const body = {
    dashboard_key: layout.dashboard,
    title: definition?.name ?? layout.dashboard,
    visibility: layout.visibility,
    portlets: layout.portlets,
    revision_note: "saved from the Enterprise dashboard designer",
  };
  try {
    if (layout.server_id) {
      const payload = await api.enterpriseUpdate("dashboards", layout.server_id, {
        expected_revision: layout.server_revision ?? layout.revision,
        ...body,
      });
      layout.server_revision = payload.record.revision;
    } else {
      const payload = await api.enterpriseCreate("dashboards", body, typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `layout-${Date.now()}`);
      layout.server_id = payload.record.record_id;
      layout.server_revision = payload.record.revision;
    }
    const stored = readLocalJson<Record<string, Layout>>(STORAGE_KEY, {});
    stored[layout.dashboard] = layout;
    writeLocalJson(STORAGE_KEY, stored);
    if (announce) {
      ctx.toast(`Layout saved on the server (revision ${String(layout.server_revision)}).`, "info");
    }
  } catch (error) {
    // The local layout remains usable; report honestly that the server did not
    // confirm the save instead of claiming a server write.
    const detail = error instanceof ApiError ? `${error.code} (HTTP ${error.status})` : String(error);
    if (announce) ctx.toast(`Layout saved in this browser only; the server did not confirm: ${detail}.`, "error");
  }
}

function actionButton(text: string, onClick: () => void): HTMLElement {
  const node = el("button", { class: "cubi-btn cubi-btn-secondary", text, attrs: { type: "button" } });
  node.addEventListener("click", onClick);
  return node;
}

function formatTime(iso: string): string {
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) return iso;
  return new Date(parsed).toISOString().slice(0, 16).replace("T", " ");
}
