import type { PageContext } from "../app.js";
import { api, probe } from "../api.js";
import { pageHref } from "../router.js";
import { formatDate } from "../session.js";
import { badge, el } from "../ui.js";
import {
  connectionList,
  detailList,
  emptyLine,
  note,
  pageActions,
  section,
  sectionBody,
  sourceStamp,
  sourceState,
  labelled,
  selectControl,
  testId,
  textInput,
} from "./shared.js";

/**
 * Page 7 — Portfolio and executive center.
 *
 * This page is a reader. It never computes a KPI, EVM value, cost or resource
 * utilisation. Each indicator area states its owning source, the source date and
 * the revision that was read; absent sources are shown as not connected.
 */

export function renderPortfolio(ctx: PageContext, host: HTMLElement): void {
  const projects = ctx.projects;
  const sharedProjects = ctx.sharedProjects ?? [];
  const selectedId = ctx.query.get("project") ?? projects[0]?.project_id ?? "";
  const selected = projects.find((project) => project.project_id === selectedId) ?? projects[0] ?? null;

  const summary = el("div", { class: "cubi-grid cubi-grid-4" });
  summary.append(
    stat("Projects in register", String(projects.length), "Rows returned by /api/projects"),
    stat("Statuses represented", String(new Set(projects.map((project) => project.status || "unknown")).size), "Derived from the register field, not a KPI"),
    stat("Highest revision", projects.length ? String(Math.max(...projects.map((project) => project.revision))) : "—", "Server record revision"),
    stat("KPI engine", "External", "Engineering EVM source; never calculated here"),
  );
  testId(summary, "portfolio-summary");
  host.append(summary);

  const register = section("Portfolio register", "Every row is a project returned by the lifecycle server with its revision and dates.");
  if (projects.length === 0) {
    sectionBody(register, emptyLine("No accessible project is in this portfolio. Project access is granted in the Engineering environment."));
  } else {
    const toolbar = el("div", { class: "cubi-toolbar" });
    const search = testId(textInput({ placeholder: "Search project, id or domain" }), "portfolio-search");
    const statuses = [...new Set(projects.map((project) => project.status || "unknown"))].sort();
    let statusFilter = "all";
    let sortKey = "name";
    const statusControl = testId(selectControl(
      [{ value: "all", label: "All statuses" }, ...statuses.map((status) => ({ value: status, label: status }))],
      "all",
      (value) => { statusFilter = value; paintTable(); },
    ), "portfolio-status-filter");
    const sortControl = testId(selectControl([
      { value: "name", label: "Sort: name" },
      { value: "revision", label: "Sort: revision (high first)" },
      { value: "start", label: "Sort: start date" },
      { value: "finish", label: "Sort: finish date" },
    ], "name", (value) => { sortKey = value; paintTable(); }), "portfolio-sort");
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
        el("th", { text: "Business domain" }),
        el("th", { text: "Status" }),
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
        const open = el("a", { class: "cubi-btn cubi-btn-ghost", text: "Open", attrs: { href: pageHref("projects", { project: project.project_id }) } });
        body.append(el("tr", {},
          el("td", {}, el("strong", { text: project.name }), el("div", { class: "cubi-field-hint", text: project.project_id })),
          el("td", { text: project.business_domain || "—" }),
          el("td", {}, badge(project.status || "unknown", project.status === "active" ? "success" : "neutral")),
          el("td", { text: String(project.revision) }),
          el("td", { text: formatDate(project.start_date, ctx.locale) }),
          el("td", { text: formatDate(project.finish_date, ctx.locale) }),
          el("td", {}, open),
        ));
      }
      node.append(body);
      table.append(node);
      tableHost.replaceChildren(table, sourceStamp("/api/projects", "per project", null, ctx.locale));
    };
    paintTable();
    sectionBody(register, toolbar, tableHost);
  }
  testId(register, "portfolio-register");
  host.append(register);

  if (sharedProjects.length) {
    const shared = section(
      "Shared build workspace",
      "In-progress shared project data for Engineering and Enterprise construction. This workspace is deliberately excluded from personal portfolio totals and the user-owned project register.",
    );
    testId(shared, "portfolio-shared-build-workspace");
    const rows = el("div", { class: "cubi-list" });
    for (const project of sharedProjects) {
      const open = linkButton("Open shared workspace", pageHref("projects", { project: project.project_id }));
      rows.append(el("div", { class: "cubi-list-item" },
        el("div", {}, el("strong", { text: project.name }), el("div", { class: "cubi-field-hint", text: project.project_id })),
        open,
      ));
    }
    sectionBody(shared, rows);
    host.append(shared);
  }

  const split = el("div", { class: "cubi-split" });
  const hierarchy = section("Portfolio hierarchy", "Grouped by the business domain recorded on the project. Grouping is presentation only.");
  const groups = new Map<string, typeof projects>();
  for (const project of projects) {
    const key = project.business_domain || "Unassigned domain";
    groups.set(key, [...(groups.get(key) ?? []), project]);
  }
  const tree = el("div", { class: "cubi-list" });
  if (groups.size === 0) tree.append(emptyLine("No project to group."));
  for (const [domain, items] of groups) {
    tree.append(el("div", { class: "cubi-list-item" }, el("strong", { text: domain }), badge(String(items.length), "neutral")));
    for (const project of items) {
      tree.append(el("div", { class: "cubi-list-item" }, el("span", { text: `· ${project.name}` }), el("span", { class: "cubi-field-hint", text: `rev ${project.revision}` })));
    }
  }
  sectionBody(hierarchy, tree);
  testId(hierarchy, "portfolio-hierarchy");
  split.append(hierarchy);

  const detail = section("Decision context", "Read-only facts for the selected project.");
  if (selected) {
    sectionBody(detail,
      detailList([
        ["Project", selected.name],
        ["Project ID", selected.project_id],
        ["Business domain", selected.business_domain || "—"],
        ["Responsible manager", selected.obs_responsible_manager || "—"],
        ["Date system", selected.date_system || "—"],
        ["Checkout state", selected.checkout_state || "—"],
        ["Revision", String(selected.revision)],
        ["Website", selected.website_url || "—"],
      ]),
      pageActions(linkButton("Project portal", pageHref("projects", { project: selected.project_id })), linkButton("Engineering workspace", "/app/")),
    );
  } else {
    sectionBody(detail, emptyLine("Select a project to see its decision context."));
  }
  testId(detail, "portfolio-detail");
  split.append(detail);
  host.append(split);

  const scorecard = section("Executive scorecard", "Indicator values are read from their owners. A dash means the source did not provide a value; this page never substitutes a calculated one.");
  const scoreBody = el("div", {},
    el("div", { class: "cubi-table-wrap" },
      scorecardTable(ctx, projects),
    ),
    note("Schedule, cost, EVM and resource indicators are owned by CUBI Engineering. Enterprise may display them only through an official, revision-stamped read model.", "warning"),
  );
  sectionBody(scorecard, scoreBody);
  testId(scorecard, "portfolio-scorecard");
  host.append(scorecard);

  const indicator = section("KPI and trend sources", "Each panel reports the real HTTP state of its source. No value is derived locally.");
  const indicatorHost = el("div");
  sectionBody(indicator, indicatorHost);
  testId(indicator, "portfolio-indicators");
  host.append(indicator);

  const decisions = section("Portfolio decisions", "Decisions are revision-pinned. Absent the decision API, no decision is shown or implied.");
  const decisionsHost = el("div");
  sectionBody(decisions, decisionsHost);
  testId(decisions, "portfolio-decisions");
  host.append(decisions);

  void loadSources(ctx, selected?.project_id ?? "", indicatorHost, decisionsHost);
}

async function loadSources(ctx: PageContext, projectId: string, indicatorHost: HTMLElement, decisionsHost: HTMLElement): Promise<void> {
  const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  const [kpi, trends, decisions, evm] = await Promise.all([
    probe(`/api/enterprise/portfolio/indicators${query}`),
    probe(`/api/enterprise/portfolio/trends${query}`),
    probe(`/api/enterprise/decisions${query}`),
    probe("/api/enterprise/evm/capability"),
  ]);
  indicatorHost.replaceChildren(
    connectionList([
      { label: "Portfolio KPI read model", probe: kpi },
      { label: "Portfolio trend read model", probe: trends },
      { label: "Decision register", probe: decisions },
      { label: "Engineering EVM capability", probe: evm },
    ], ctx.t),
    sourceState(kpi, ctx.t, { title: "KPI source", source: "Enterprise portfolio KPI read model", detail: "Indicators must carry owner, date and revision. Until that route is mounted, the scorecard shows no number." }),
    sourceState(trends, ctx.t, { title: "Trend source", source: "Portfolio trend read model", detail: "A trend is never interpolated or derived from project dates." }),
  );
  if (decisions.state === "available") {
    void api.enterpriseList("decisions", projectId ? { project_id: projectId } : {}).then((payload) => {
      const table = el("div", { class: "cubi-table-wrap" });
      const node = el("table", { class: "cubi-table" });
      node.append(el("thead", {}, el("tr", {},
        el("th", { text: "Decision" }),
        el("th", { text: "Status" }),
        el("th", { text: "Revision" }),
        el("th", { text: "Project" }),
      )));
      const body = el("tbody");
      if (payload.items.length === 0) {
        body.append(el("tr", {}, el("td", { class: "cubi-table-empty", text: "No decision is recorded for this scope.", attrs: { colspan: "4" } })));
      }
      for (const item of payload.items) {
        body.append(el("tr", {},
          el("td", {}, el("strong", { text: String(item.title ?? item.record_id) }), el("div", { class: "cubi-field-hint", text: item.record_id })),
          el("td", {}, badge(String(item.status ?? "—"), item.status === "approved" ? "success" : "info")),
          el("td", { text: String(item.revision) }),
          el("td", { text: String(item.project_id ?? "—") }),
        ));
      }
      node.append(body);
      table.append(node);
      decisionsHost.replaceChildren(table, decisionForm(ctx, projectId));
    }).catch((error: unknown) => {
      decisionsHost.replaceChildren(el("p", { class: "cubi-alert cubi-alert-error", text: String(error) }));
    });
  } else {
    decisionsHost.replaceChildren(
      sourceState(decisions, ctx.t, { title: "Decision register", source: "Enterprise decision API", detail: "Portfolio decisions are revision-pinned and approved by an authorized role." }),
    );
  }
}

function decisionForm(ctx: PageContext, projectId: string): HTMLElement {
  const form = el("div", { class: "cubi-form-grid" });
  const title = textInput({ placeholder: "Decision title" });
  const outcome = el("select", { class: "cubi-input" });
  for (const value of ["pending", "approved", "rejected", "deferred"]) {
    const option = el("option", { text: value });
    option.value = value;
    outcome.append(option);
  }
  const submit = el("button", { class: "cubi-btn cubi-btn-primary", text: "Record decision", attrs: { type: "button" } });
  submit.addEventListener("click", () => {
    if (!title.value.trim()) return;
    submit.disabled = true;
    void api.enterpriseCreate("decisions", {
      title: title.value.trim(),
      project_id: projectId || null,
      status: outcome.value,
    }, typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `decision-${Date.now()}`)
      .then(() => { ctx.toast("Decision recorded on the server.", "info"); window.location.reload(); })
      .catch((error: unknown) => { submit.disabled = false; ctx.toast(String(error), "error"); });
  });
  form.append(labelled("Decision", title), labelled("Status", outcome), labelled("", submit));
  return form;
}

function scorecardTable(ctx: PageContext, projects: PageContext["projects"]): HTMLElement {
  const table = el("table", { class: "cubi-table" });
  table.append(el("thead", {}, el("tr", {},
    el("th", { text: "Project" }),
    el("th", { text: "Schedule" }),
    el("th", { text: "Cost / EVM" }),
    el("th", { text: "Resources" }),
    el("th", { text: "Source date" }),
    el("th", { text: "Revision" }),
  )));
  const body = el("tbody");
  if (!projects.length) {
    body.append(el("tr", {}, el("td", { class: "cubi-table-empty", text: "No project in scope.", attrs: { colspan: "6" } })));
  }
  for (const project of projects) {
    body.append(el("tr", {},
      el("td", {}, el("strong", { text: project.name })),
      el("td", {}, badge("source not connected", "neutral")),
      el("td", {}, badge("source not connected", "neutral")),
      el("td", {}, badge("source not connected", "neutral")),
      el("td", { text: formatDate(project.start_date, ctx.locale) }),
      el("td", { text: String(project.revision) }),
    ));
  }
  table.append(body);
  return table;
}

function stat(label: string, value: string, meta: string): HTMLElement {
  const node = el("div", { class: "cubi-stat" });
  node.append(el("span", { class: "cubi-stat-label", text: label }), el("strong", { class: "cubi-stat-value", text: value }), el("span", { class: "cubi-stat-meta", text: meta }));
  return node;
}

function linkButton(text: string, href: string): HTMLElement {
  const anchor = el("a", { class: "cubi-btn cubi-btn-secondary", text });
  anchor.href = href;
  return anchor;
}
