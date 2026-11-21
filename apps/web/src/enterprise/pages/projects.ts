import type { PageContext } from "../app.js";
import { ApiError, api, probe, type CapabilityProbe, type DocumentRecord, type ResourceRecord } from "../api.js";
import { pageHref } from "../router.js";
import { formatDate, formatDateTime } from "../session.js";
import { badge, el, stateBlock, tabs } from "../ui.js";
import {
  detailList,
  emptyLine,
  note,
  pageActions,
  section,
  sectionBody,
  sourceStamp,
  sourceState,
  selectControl,
  testId,
  textInput,
} from "./shared.js";

/**
 * Page 8 — Enterprise projects and project portal.
 *
 * The register is real. Each details tab reads an official project-scoped route
 * and reports its exact state. Schedule authority stays in Engineering; this
 * portal links to it instead of re-implementing it.
 */

type TabId = "overview" | "engineering" | "resources" | "documents" | "risk" | "reports";

const TABS: { id: TabId; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "engineering", label: "Engineering source" },
  { id: "resources", label: "Resources" },
  { id: "documents", label: "Documents" },
  { id: "risk", label: "Risks & issues" },
  { id: "reports", label: "Reports" },
];

let activeTab: TabId = "overview";

export function renderProjects(ctx: PageContext, host: HTMLElement): void {
  const projects = ctx.projects;
  const requested = ctx.query.get("project") ?? "";
  const selected = projects.find((project) => project.project_id === requested) ?? projects[0] ?? null;

  const register = section("Enterprise project register", "Every project visible to this session, with its server revision. Selecting a project opens its portal below.");
  if (projects.length === 0) {
    sectionBody(register, emptyLine("No project is visible to this session. Create or join a project in the Engineering environment first."));
  } else {
    const toolbar = el("div", { class: "cubi-toolbar" });
    const search = testId(textInput({ placeholder: "Search project, id or domain" }), "projects-search");
    const statuses = [...new Set(projects.map((project) => project.status || "unknown"))].sort();
    let statusFilter = "all";
    let sortKey = "name";
    const statusControl = testId(selectControl(
      [{ value: "all", label: "All statuses" }, ...statuses.map((status) => ({ value: status, label: status }))],
      "all",
      (value) => { statusFilter = value; paintTable(); },
    ), "projects-status-filter");
    const sortControl = testId(selectControl([
      { value: "name", label: "Sort: name" },
      { value: "revision", label: "Sort: revision (high first)" },
      { value: "start", label: "Sort: start date" },
      { value: "finish", label: "Sort: finish date" },
    ], "name", (value) => { sortKey = value; paintTable(); }), "projects-sort");
    const count = el("span", { class: "cubi-field-hint", attrs: { "aria-live": "polite" } });
    const tableHost = el("div");
    toolbar.append(search, statusControl, sortControl, count);
    search.addEventListener("input", () => paintTable());

    const paintTable = (): void => {
      const needle = search.value.trim().toLocaleLowerCase();
      const rows = projects
        .filter((project) => {
          if (statusFilter !== "all" && (project.status || "unknown") !== statusFilter) return false;
          if (!needle) return true;
          return `${project.name} ${project.project_id} ${project.business_domain ?? ""}`.toLocaleLowerCase().includes(needle);
        })
        .sort((left, right) => {
          if (sortKey === "revision") return right.revision - left.revision;
          if (sortKey === "start") return String(left.start_date ?? "").localeCompare(String(right.start_date ?? ""));
          if (sortKey === "finish") return String(left.finish_date ?? "").localeCompare(String(right.finish_date ?? ""));
          return left.name.localeCompare(right.name, ctx.locale);
        });
      count.textContent = `${rows.length} of ${projects.length} projects returned by the server`;
      const table = el("div", { class: "cubi-table-wrap" });
      const node = el("table", { class: "cubi-table" });
      node.append(el("thead", {}, el("tr", {},
        el("th", { text: "Project" }),
        el("th", { text: "Status" }),
        el("th", { text: "Domain" }),
        el("th", { text: "Revision" }),
        el("th", { text: "Start" }),
        el("th", { text: "Finish" }),
        el("th", { text: "" }),
      )));
      const body = el("tbody");
      if (rows.length === 0) {
        body.append(el("tr", {}, el("td", { class: "cubi-table-empty", text: "No project matches the current filter.", attrs: { colspan: "7" } })));
      }
      for (const project of rows) {
        const open = el("a", { class: "cubi-btn cubi-btn-ghost", text: "Open portal", attrs: { href: pageHref("projects", { project: project.project_id }) } });
        body.append(el("tr", { class: project.project_id === selected?.project_id ? "is-selected" : undefined },
          el("td", {}, el("strong", { text: project.name }), el("div", { class: "cubi-field-hint", text: project.project_id })),
          el("td", {}, badge(project.status || "unknown", project.status === "active" ? "success" : "neutral")),
          el("td", { text: project.business_domain || "—" }),
          el("td", { text: String(project.revision) }),
          el("td", { text: formatDate(project.start_date, ctx.locale) }),
          el("td", { text: formatDate(project.finish_date, ctx.locale) }),
          el("td", {}, open),
        ));
      }
      node.append(body);
      table.append(node);
      tableHost.replaceChildren(table);
    };
    paintTable();
    sectionBody(register, toolbar, tableHost);
  }
  testId(register, "projects-register");
  host.append(register);

  if (!selected) return;

  const portal = section(selected.name, "Project portal — one place to read the project and reach its owned sources.");
  const tabBar = tabs(TABS, activeTab, (id) => {
    activeTab = id;
    ctx.navigate(pageHref("projects", { project: selected.project_id }));
  });
  const tabHost = el("div");
  sectionBody(portal, tabBar, tabHost);
  testId(portal, "projects-portal");
  host.append(portal);
  void renderTab(ctx, tabHost, selected);
}

async function renderTab(ctx: PageContext, host: HTMLElement, project: PageContext["projects"][number]): Promise<void> {
  host.replaceChildren(el("div", { class: "cubi-loading" }, el("div", { class: "cubi-spinner" }), el("span", { text: ctx.t("common.loading") })));
  if (activeTab === "overview") {
    host.replaceChildren(
      el("div", { class: "cubi-split" },
        el("div", {},
          detailList([
            ["Project", project.name],
            ["Project ID", project.project_id],
            ["Tenant", project.tenant_id ?? ctx.session.tenant_id],
            ["Status", project.status || "—"],
            ["Business domain", project.business_domain || "—"],
            ["Responsible manager", project.obs_responsible_manager || "—"],
            ["Website", project.website_url || "—"],
          ]),
          sourceStamp("/api/projects", project.revision, null, ctx.locale),
        ),
        el("div", {},
          detailList([
            ["Start", formatDate(project.start_date, ctx.locale)],
            ["Finish", formatDate(project.finish_date, ctx.locale)],
            ["Date system", project.date_system || "—"],
            ["Checkout", project.checkout_state || "—"],
            ["Revision", String(project.revision)],
          ]),
          note("Schedule, activities, progress and earned value are authoritative in Engineering. This portal reads only official project-scoped routes."),
        ),
      ),
      pageActions(linkButton("Open Engineering workspace", "/app/"), linkButton("Portfolio view", pageHref("portfolio", { project: project.project_id }))),
    );
    return;
  }

  if (activeTab === "engineering") {
    const [workspace, issues, evm] = await Promise.all([
      probe(`/api/projects/${encodeURIComponent(project.project_id)}/p6/workspace`),
      probe(`/api/projects/${encodeURIComponent(project.project_id)}/p6/issues`),
      probe(`/api/projects/${encodeURIComponent(project.project_id)}/p6/earned-value`),
    ]);
    host.replaceChildren(
      note("The official route to schedule detail is the Engineering workspace. No schedule, CPM, WBS or activity data is recomputed in Enterprise.", "warning"),
      connectionListLocal(ctx, [["Project P6 workspace read", workspace], ["Issue register", issues], ["Earned-value source", evm]]),
      pageActions(linkButton("Open schedule in Engineering", "/app/")),
    );
    return;
  }

  if (activeTab === "resources") {
    const capability = await probe(`/api/projects/${encodeURIComponent(project.project_id)}/p6/resources`);
    if (capability.state !== "available") {
      host.replaceChildren(sourceState(capability, ctx.t, { title: "Resource projection", source: "Engineering resource read model", detail: "Resources remain owned by Engineering.", retry: () => { void renderTab(ctx, host, project); } }));
      return;
    }
    try {
      const rows = await api.listResources(project.project_id);
      host.replaceChildren(rows.length ? resourcesTable(rows) : emptyLine("No resource is registered for this project."),
        sourceStamp("Engineering resource read model", "per resource", null, ctx.locale));
    } catch (error) {
      host.replaceChildren(requestError(ctx, host, error, () => { void renderTab(ctx, host, project); }));
    }
    return;
  }

  if (activeTab === "documents") {
    const capability = await probe(`/api/projects/${encodeURIComponent(project.project_id)}/documents`);
    if (capability.state !== "available") {
      host.replaceChildren(sourceState(capability, ctx.t, { title: "Document register", source: "Project document store", retry: () => { void renderTab(ctx, host, project); } }));
      return;
    }
    try {
      const rows = await api.listDocuments(project.project_id);
      host.replaceChildren(rows.length ? documentsTable(rows) : emptyLine("No document is registered for this project."),
        sourceStamp("Project document register", "per document", null, ctx.locale));
    } catch (error) {
      host.replaceChildren(requestError(ctx, host, error, () => { void renderTab(ctx, host, project); }));
    }
    return;
  }

  if (activeTab === "risk") {
    const [risksProbe, issuesProbe] = await Promise.all([
      probe(`/api/projects/${encodeURIComponent(project.project_id)}/risks`),
      probe(`/api/projects/${encodeURIComponent(project.project_id)}/p6/issues`),
    ]);
    const blocks: HTMLElement[] = [];
    if (risksProbe.state === "available") {
      const rows = await api.listRisks(project.project_id);
      blocks.push(rows.length ? recordsTable("Risk", rows) : emptyLine("No risk is registered."));
    } else {
      blocks.push(sourceState(risksProbe, ctx.t, { title: "Risk register", source: "Project risk API" }));
    }
    if (issuesProbe.state === "available") {
      const rows = await api.listIssues(project.project_id);
      blocks.push(rows.length ? recordsTable("Issue", rows) : emptyLine("No issue is registered."));
    } else {
      blocks.push(sourceState(issuesProbe, ctx.t, { title: "Issue register", source: "P6 issue API" }));
    }
    host.replaceChildren(...blocks, sourceStamp("Project risk and issue registers", "per record", null, ctx.locale));
    return;
  }

  const [catalogueProbe, definitionsProbe] = await Promise.all([
    probe(`/api/projects/${encodeURIComponent(project.project_id)}/reports/catalogue`),
    probe(`/api/projects/${encodeURIComponent(project.project_id)}/reports`),
  ]);
  const blocks: HTMLElement[] = [];
  if (definitionsProbe.state === "available") {
    const rows = await api.listReports(project.project_id);
    blocks.push(rows.length ? simpleRows("Report", rows) : emptyLine("No report definition is registered."));
  } else {
    blocks.push(sourceState(definitionsProbe, ctx.t, { title: "Report definitions", source: "Existing report runtime" }));
  }
  if (catalogueProbe.state === "available") {
    const catalogue = await api.reportCatalogue(project.project_id);
    blocks.push(el("h3", { text: "Catalogue" }), simpleRows("Catalogue entry", catalogue));
  } else {
    blocks.push(sourceState(catalogueProbe, ctx.t, { title: "Report catalogue", source: "Existing report runtime" }));
  }
  host.replaceChildren(...blocks, sourceStamp("Report runtime", "per definition", null, ctx.locale));
}

function resourcesTable(rows: ResourceRecord[]): HTMLElement {
  const table = el("div", { class: "cubi-table-wrap" });
  const node = el("table", { class: "cubi-table" });
  node.append(el("thead", {}, el("tr", {},
    el("th", { text: "Resource" }),
    el("th", { text: "Type" }),
    el("th", { text: "Unit" }),
    el("th", { text: "Calendar" }),
    el("th", { text: "Active" }),
    el("th", { text: "Revision" }),
  )));
  const body = el("tbody");
  for (const row of rows.slice(0, 100)) {
    body.append(el("tr", {},
      el("td", {}, el("strong", { text: row.name }), el("div", { class: "cubi-field-hint", text: row.resource_id })),
      el("td", { text: row.resource_type }),
      el("td", { text: row.unit_of_measure || "—" }),
      el("td", { text: row.calendar_id || "—" }),
      el("td", {}, badge(row.is_active ? "active" : "inactive", row.is_active ? "success" : "neutral")),
      el("td", { text: String(row.record_revision) }),
    ));
  }
  node.append(body);
  table.append(node);
  return table;
}

function documentsTable(rows: DocumentRecord[]): HTMLElement {
  const table = el("div", { class: "cubi-table-wrap" });
  const node = el("table", { class: "cubi-table" });
  node.append(el("thead", {}, el("tr", {},
    el("th", { text: "Document" }),
    el("th", { text: "Type" }),
    el("th", { text: "Status" }),
    el("th", { text: "Revision" }),
    el("th", { text: "Updated" }),
  )));
  const body = el("tbody");
  for (const row of rows.slice(0, 100)) {
    body.append(el("tr", {},
      el("td", {}, el("strong", { text: row.title }), el("div", { class: "cubi-field-hint", text: row.document_id })),
      el("td", { text: String(row.document_type ?? "—") }),
      el("td", {}, badge(String(row.status ?? "—"), "neutral")),
      el("td", { text: String(row.revision ?? "—") }),
      el("td", { text: String(row.updated_at ?? "—") }),
    ));
  }
  node.append(body);
  table.append(node);
  return table;
}

function recordsTable(kind: string, rows: Record<string, unknown>[]): HTMLElement {
  const table = el("div", { class: "cubi-table-wrap" });
  const node = el("table", { class: "cubi-table" });
  node.append(el("thead", {}, el("tr", {}, el("th", { text: kind }), el("th", { text: "Status" }), el("th", { text: "Severity" }), el("th", { text: "Revision" }))));
  const body = el("tbody");
  rows.slice(0, 100).forEach((row, index) => {
    body.append(el("tr", {},
      el("td", {}, el("strong", { text: String(row.title ?? row.name ?? row[`${kind.toLowerCase()}_id`] ?? `${kind} ${index + 1}`) })),
      el("td", { text: String(row.status ?? "—") }),
      el("td", { text: String(row.severity ?? row.rating ?? "—") }),
      el("td", { text: String(row.revision ?? row.record_revision ?? "—") }),
    ));
  });
  node.append(body);
  table.append(node);
  return table;
}

function simpleRows(kind: string, rows: Record<string, unknown>[]): HTMLElement {
  const table = el("div", { class: "cubi-table-wrap" });
  const node = el("table", { class: "cubi-table" });
  node.append(el("thead", {}, el("tr", {}, el("th", { text: kind }), el("th", { text: "Subject" }), el("th", { text: "Revision" }))));
  const body = el("tbody");
  rows.slice(0, 100).forEach((row, index) => {
    body.append(el("tr", {},
      el("td", {}, el("strong", { text: String(row.name ?? row.report_id ?? row.id ?? `${kind} ${index + 1}`) })),
      el("td", { text: String(row.subject ?? row.description ?? "—") }),
      el("td", { text: String(row.revision ?? "—") }),
    ));
  });
  node.append(body);
  table.append(node);
  return table;
}

function connectionListLocal(ctx: PageContext, entries: [string, CapabilityProbe][]): HTMLElement {
  const wrap = el("div", { class: "cubi-conn" });
  for (const [label, capability] of entries) {
    wrap.append(el("div", { class: "cubi-conn-row" },
      el("span", {}, el("strong", { text: label }), el("span", { class: "path", text: ` ${capability.path}` })),
      el("span", {}, badge(`${capability.status || "—"}`, capability.state === "available" ? "success" : capability.state === "forbidden" ? "warning" : "neutral"), el("span", { text: " " }), badge(capability.state, capability.state === "available" ? "success" : "neutral")),
    ));
  }
  return wrap;
}

function requestError(ctx: PageContext, host: HTMLElement, error: unknown, retry: () => void): HTMLElement {
  const detail = error instanceof ApiError ? `${error.code} (HTTP ${error.status})` : String(error);
  return stateBlock("error", "The source could not be read", `${detail}. Nothing was substituted.`, [retryElement(retry, ctx)]);
}

function retryElement(retry: () => void, ctx: PageContext): HTMLElement {
  const button = el("button", { class: "cubi-btn cubi-btn-secondary", text: ctx.t("common.retry"), attrs: { type: "button" } });
  button.addEventListener("click", retry);
  return button;
}

function linkButton(text: string, href: string): HTMLElement {
  const anchor = el("a", { class: "cubi-btn cubi-btn-secondary", text });
  anchor.href = href;
  return anchor;
}

export { formatDateTime };
