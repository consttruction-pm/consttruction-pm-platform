import type { PageContext } from "../app.js";
import { ApiError, api, probe, type CapabilityProbe, type EnterpriseTask } from "../api.js";
import { BASE_PATH, pageHref } from "../router.js";
import { displayName, enterpriseTier, environmentAccess, formatDate } from "../session.js";
import { badge, el } from "../ui.js";
import {
  capabilityChip,
  connectionList,
  emptyLine,
  note,
  pageActions,
  section,
  sectionBody,
  sourceState,
  testId,
} from "./shared.js";

/**
 * Page 4 — Personal workbench.
 *
 * The workbench aggregates real server state and explicitly labels sources that
 * are not installed. It never seeds demo tasks or synthesizes a "connected"
 * state.
 */

const QUICK_LINKS = [
  { id: "dashboard", text: "Dashboards" },
  { id: "portfolio", text: "Portfolio" },
  { id: "projects", text: "Projects" },
  { id: "access", text: "Organization & access" },
  { id: "tasks", text: "Team & tasks" },
  { id: "workflows", text: "Workflow studio" },
  { id: "approvals", text: "Approvals" },
  { id: "resources", text: "Resources & capacity" },
  { id: "reports", text: "Reports & operations" },
  { id: "knowledge", text: "Knowledge & PMBOK" },
] as const;

export function renderWorkbench(ctx: PageContext, host: HTMLElement): void {
  const tier = enterpriseTier(ctx.session.roles);
  const access = environmentAccess(ctx.session);

  const hero = el("section", { class: "cubi-card cubi-card-accent" });
  const heroBody = el("div", { class: "cubi-card-body" });
  heroBody.append(
    el("p", { class: "cubi-eyebrow", text: `${ctx.t("common.welcome")} · ${displayName(ctx.session.user_id)}` }),
    el("h2", { text: ctx.t("page.workbench.title") }),
    el("p", { text: `${ctx.t("common.organization")}: ${ctx.session.tenant_id} · ${access.enterprise.allowed ? `Enterprise ${tier}` : "No Enterprise entitlement on this session"}` }),
  );
  hero.append(heroBody);
  testId(hero, "workbench-hero");
  host.append(hero);

  const stats = el("div", { class: "cubi-grid cubi-grid-4" });
  const taskStat = el("div", { class: "cubi-stat" }, el("span", { class: "cubi-stat-label", text: "Assigned tasks" }), el("strong", { class: "cubi-stat-value", text: "…" }), el("span", { class: "cubi-stat-meta", text: "Reading /api/enterprise/tasks" }));
  const approvalStat = el("div", { class: "cubi-stat" }, el("span", { class: "cubi-stat-label", text: "Pending approvals" }), el("strong", { class: "cubi-stat-value", text: "…" }), el("span", { class: "cubi-stat-meta", text: "Reading /api/enterprise/approvals" }));
  stats.append(
    el("div", { class: "cubi-stat" }, el("span", { class: "cubi-stat-label", text: "Enterprise tier" }), el("strong", { class: "cubi-stat-value", text: tier ?? "none" }), el("span", { class: "cubi-stat-meta", text: tier ? "Granted by the server session" : "Request from an administrator" })),
    el("div", { class: "cubi-stat" }, el("span", { class: "cubi-stat-label", text: "Visible projects" }), el("strong", { class: "cubi-stat-value", text: String(ctx.projects.length) }), el("span", { class: "cubi-stat-meta", text: "From /api/projects" })),
    taskStat,
    approvalStat,
  );
  host.append(stats);

  const sources = section("Live source status", "Every status is the real HTTP answer for this session. A missing route is shown as unavailable, never replaced with sample rows.");
  const sourceHost = el("div");
  sectionBody(sources, sourceHost);
  testId(sources, "workbench-sources");
  host.append(sources);

  const tasksCard = section("My assigned enterprise tasks", "Generic collaboration tasks only. P6 activities, timesheets and progress remain in the Engineering environment.");
  const tasksHost = el("div", {}, el("div", { class: "cubi-loading" }, el("div", { class: "cubi-spinner" }), el("span", { text: ctx.t("common.loading") })));
  sectionBody(tasksCard, tasksHost);
  testId(tasksCard, "workbench-tasks");
  host.append(tasksCard);

  const projectsCard = section("Recent accessible projects", "Project facts are read from the lifecycle server. Opening a project does not copy or recalculate its schedule.");
  const projectsBody = el("div");
  if (ctx.projects.length === 0) {
    projectsBody.append(emptyLine("No project is visible to this session. Project access is granted in the Engineering environment."));
  } else {
    const table = el("div", { class: "cubi-table-wrap" });
    const node = el("table", { class: "cubi-table" });
    node.append(el("thead", {}, el("tr", {},
      el("th", { text: "Project" }),
      el("th", { text: "Status" }),
      el("th", { text: "Revision" }),
      el("th", { text: "Start" }),
      el("th", { text: "Finish" }),
    )));
    const body = el("tbody");
    for (const project of ctx.projects.slice(0, 8)) {
      const nameCell = el("div", { class: "cubi-list-item" });
      nameCell.append(el("strong", { text: project.name }), badge(project.project_id.slice(0, 12), "neutral"));
      body.append(el("tr", {},
        el("td", {}, nameCell),
        el("td", { text: project.status || "—" }),
        el("td", { text: String(project.revision) }),
        el("td", { text: formatDate(project.start_date, ctx.locale) }),
        el("td", { text: formatDate(project.finish_date, ctx.locale) }),
      ));
    }
    node.append(body);
    table.append(node);
    projectsBody.append(table);
  }
  sectionBody(projectsCard, projectsBody, pageActions(linkButton("Open project register", pageHref("projects")), linkButton("Open Engineering workspace", "/app/")));
  testId(projectsCard, "workbench-projects");
  host.append(projectsCard);

  const linksCard = section("Enterprise centers", "Ten operational surfaces plus this personal entry point.");
  const grid = el("div", { class: "cubi-knowledge-grid" });
  for (const link of QUICK_LINKS) {
    const card = el("button", { class: "cubi-knowledge-card", attrs: { type: "button" } });
    card.append(el("h3", { text: link.text }), el("p", { text: "Open the center in this workbench." }));
    card.addEventListener("click", () => ctx.navigate(pageHref(link.id)));
    grid.append(card);
  }
  sectionBody(linksCard, grid);
  testId(linksCard, "workbench-links");
  host.append(linksCard);

  void loadSources(ctx, sourceHost, tasksHost, taskStat, approvalStat);
}

async function loadSources(
  ctx: PageContext,
  sourceHost: HTMLElement,
  tasksHost: HTMLElement,
  taskStat: HTMLElement,
  approvalStat: HTMLElement,
): Promise<void> {
  const [tasksProbe, approvalsProbe, dashboardsProbe, orgsProbe] = await Promise.all([
    probe("/api/enterprise/tasks"),
    probe("/api/enterprise/approvals"),
    probe("/api/enterprise/dashboards"),
    probe("/api/enterprise/organizations"),
  ]);
  sourceHost.replaceChildren(
    connectionList([
      { label: "Enterprise task API", probe: tasksProbe },
      { label: "Approval API", probe: approvalsProbe },
      { label: "Dashboard API", probe: dashboardsProbe },
      { label: "Organization API", probe: orgsProbe },
    ], ctx.t),
    note("Routes marked unavailable are registered as contracts only in this build. The workbench keeps their UI visible and never simulates their records.", "warning"),
  );
  setStat(taskStat, ctx, tasksProbe);
  setStat(approvalStat, ctx, approvalsProbe);

  if (tasksProbe.state !== "available") {
    tasksHost.replaceChildren(sourceState(tasksProbe, ctx.t, {
      title: "Task source is not connected",
      source: "Enterprise Task API v1 (PostgreSQL)",
      detail: "The task store uses PostgreSQL advisory locks and triggers, so it is not mounted on the SQLite preview. The contract is registered under /api/enterprise/tasks.",
    }));
    return;
  }
  try {
    const payload = await api.listTasks(null);
    const mine = payload.tasks.filter((task) => task.assigned_user_id === ctx.session.user_id);
    tasksHost.replaceChildren(mine.length ? taskTable(ctx, mine) : emptyLine("No enterprise task is assigned to you. Create one in Team & task center."));
    setStatValue(taskStat, String(mine.length), "Assigned to this session");
  } catch (error) {
    const detail = error instanceof ApiError ? `${error.code} (HTTP ${error.status})` : String(error);
    tasksHost.replaceChildren(el("div", { class: "cubi-alert cubi-alert-error", text: `The task list could not be read: ${detail}.` }));
  }
}

function setStat(node: HTMLElement, ctx: PageContext, probeState: CapabilityProbe): void {
  const value = node.querySelector(".cubi-stat-value");
  const meta = node.querySelector(".cubi-stat-meta");
  if (value) value.textContent = probeState.state === "available" ? "0" : "—";
  if (meta) meta.textContent = probeState.state === "available" ? "Source connected" : "Source not connected";
  node.append(el("div", { class: "cubi-row" }, capabilityChip(probeState, ctx.t)));
}

function setStatValue(node: HTMLElement, value: string, meta: string): void {
  const valueNode = node.querySelector(".cubi-stat-value");
  const metaNode = node.querySelector(".cubi-stat-meta");
  if (valueNode) valueNode.textContent = value;
  if (metaNode) metaNode.textContent = meta;
}

function taskTable(ctx: PageContext, tasks: EnterpriseTask[]): HTMLElement {
  const wrap = el("div", { class: "cubi-table-wrap" });
  const table = el("table", { class: "cubi-table" });
  table.append(el("thead", {}, el("tr", {},
    el("th", { text: "Title" }),
    el("th", { text: "Status" }),
    el("th", { text: "Priority" }),
    el("th", { text: "Due" }),
    el("th", { text: "Revision" }),
  )));
  const body = el("tbody");
  for (const task of tasks.slice(0, 10)) {
    body.append(el("tr", {},
      el("td", {}, el("strong", { text: task.title })),
      el("td", {}, badge(task.status, task.status === "completed" ? "success" : task.status === "blocked" ? "danger" : "info")),
      el("td", { text: task.priority }),
      el("td", { text: formatDate(task.due_at, ctx.locale) }),
      el("td", { text: String(task.revision) }),
    ));
  }
  table.append(body);
  wrap.append(table);
  return wrap;
}

function linkButton(text: string, href: string): HTMLElement {
  const anchor = el("a", { class: "cubi-btn cubi-btn-secondary", text });
  anchor.href = href;
  return anchor;
}

export { BASE_PATH };
