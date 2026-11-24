import type { PageContext } from "../app.js";
import { ApiError, api, probe, type CapabilityProbe, type ReportDefinition } from "../api.js";
import { pageHref } from "../router.js";
import { badge, el, stateBlock } from "../ui.js";
import {
  detailList,
  emptyLine,
  note,
  pageActions,
  projectFilterOptions,
  section,
  sectionBody,
  sourceStamp,
  sourceState,
  selectControl,
  testId,
  textInput,
} from "./shared.js";

/**
 * Page 14 — Reports and operations.
 *
 * The reporting runtime is an existing platform capability. This page reuses
 * its official project-scoped routes (catalogue, definitions, runs, schedules,
 * run) and reads the existing durable scheduling job queue. It never starts a
 * second queue, worker or scheduler.
 */

type JobsLookup = {
  status: "idle" | "loading" | "found" | "error";
  job?: Record<string, unknown>;
  message?: string;
};

let selectedReportId = "";
let jobsProjectId = "";
const jobsLookup: JobsLookup = { status: "idle" };

export function renderReports(ctx: PageContext, host: HTMLElement): void {
  const requested = ctx.query.get("project") ?? "";
  const allProjects = [...ctx.projects, ...(ctx.sharedProjects ?? [])];
  const selected = allProjects.find((project) => project.project_id === requested) ?? allProjects[0] ?? null;
  const reportFromQuery = ctx.query.get("report") ?? "";
  if (reportFromQuery) selectedReportId = reportFromQuery;
  if (jobsProjectId !== (selected?.project_id ?? "")) {
    jobsProjectId = selected?.project_id ?? "";
    jobsLookup.status = "idle";
    jobsLookup.job = undefined;
    jobsLookup.message = undefined;
  }

  const intro = section(
    "Existing reporting and job runtime",
    "Reports, runs and schedules are served by the platform reporting runtime. Scheduling jobs are served by the existing durable queue. Enterprise reads both; it does not create a parallel queue.",
  );
  sectionBody(intro,
    note("This page has no worker, no cron and no local job store. Every operation below calls an existing server route or is reported as not connected.", "info"),
  );
  testId(intro, "reports-intro");
  host.append(intro);

  const scope = section("Project scope", "Reporting routes are project-scoped. Choose the project whose runtime should be read.");
  const selector = selectControl(
    projectFilterOptions(ctx.projects, ctx.sharedProjects ?? [], "Select a project"),
    selected?.project_id ?? "",
    (value) => ctx.navigate(pageHref("reports", { project: value })),
  );
  sectionBody(scope, el("div", { class: "cubi-toolbar" }, selector));
  host.append(scope);

  if (!selected) {
    host.append(sectionBody(section("No project in scope", ""), emptyLine("No project is visible to this session, so the reporting runtime cannot be scoped.")));
    return;
  }

  const runtime = section("Runtime capability", "The exact server answer for this project. A missing route is reported as unavailable rather than replaced by sample output.");
  const runtimeHost = el("div", {}, loadingLine(ctx));
  sectionBody(runtime, runtimeHost);
  testId(runtime, "reports-runtime");
  host.append(runtime);

  const catalogue = section("Report catalogue", "Definitions the reporting runtime offers for this project.");
  const catalogueHost = el("div", {}, loadingLine(ctx));
  sectionBody(catalogue, catalogueHost);
  testId(catalogue, "reports-catalogue");
  host.append(catalogue);

  const definitions = section("Report definitions", "Stored definitions with their revision. Open a definition to read its runs and schedules.");
  const definitionsHost = el("div", {}, loadingLine(ctx));
  sectionBody(definitions, definitionsHost);
  testId(definitions, "reports-definitions");
  host.append(definitions);

  const operations = section("Definition operations", "Run history and schedules for the selected definition. Running a report uses the same runtime, not a new one.");
  const operationsHost = el("div");
  sectionBody(operations, operationsHost);
  testId(operations, "reports-operations");
  host.append(operations);

  const jobs = section("Existing scheduling job queue", "Durable schedule runs already exist as a platform service. Read a job by id; submission stays in Engineering.");
  sectionBody(jobs, jobsPanel(ctx, selected.project_id));
  testId(jobs, "reports-jobs");
  host.append(jobs);

  void load(ctx, selected.project_id, selected.revision, runtimeHost, catalogueHost, definitionsHost, operationsHost);
}

async function load(
  ctx: PageContext,
  projectId: string,
  projectRevision: number,
  runtimeHost: HTMLElement,
  catalogueHost: HTMLElement,
  definitionsHost: HTMLElement,
  operationsHost: HTMLElement,
): Promise<void> {
  const encoded = encodeURIComponent(projectId);
  const [catalogueProbe, definitionsProbe] = await Promise.all([
    probe(`/api/projects/${encoded}/reports/catalogue`),
    probe(`/api/projects/${encoded}/reports`),
  ]);

  runtimeHost.replaceChildren(
    connectionRows([
      ["Report catalogue", catalogueProbe],
      ["Report definitions", definitionsProbe],
    ]),
    sourceStamp("Project reporting runtime", projectRevision, null, ctx.locale),
  );

  if (catalogueProbe.state === "available") {
    try {
      const rows = await api.reportCatalogue(projectId);
      catalogueHost.replaceChildren(rows.length ? catalogueTable(rows) : emptyLine("The runtime catalogue is empty for this project."));
    } catch (error) {
      catalogueHost.replaceChildren(errorPanel(ctx, error, () => { void load(ctx, projectId, projectRevision, runtimeHost, catalogueHost, definitionsHost, operationsHost); }));
    }
  } else {
    catalogueHost.replaceChildren(sourceState(catalogueProbe, ctx.t, { title: "Report catalogue", source: "Platform reporting runtime", detail: "No catalogue is invented locally." }));
  }

  if (definitionsProbe.state === "available") {
    try {
      const rows = await api.listReports(projectId);
      if (!rows.length) {
        definitionsHost.replaceChildren(emptyLine("No report definition is stored for this project."));
      } else {
        const active = rows.find((row) => row.report_id === selectedReportId) ?? rows[0];
        selectedReportId = active.report_id;
        definitionsHost.replaceChildren(definitionsTable(projectId, rows, selectedReportId));
        void renderOperations(ctx, projectId, active, operationsHost);
      }
    } catch (error) {
      definitionsHost.replaceChildren(errorPanel(ctx, error, () => { void load(ctx, projectId, projectRevision, runtimeHost, catalogueHost, definitionsHost, operationsHost); }));
      operationsHost.replaceChildren(emptyLine("Definition operations are unavailable until the definition list can be read."));
    }
  } else {
    definitionsHost.replaceChildren(sourceState(definitionsProbe, ctx.t, { title: "Report definitions", source: "Platform reporting runtime" }));
    operationsHost.replaceChildren(emptyLine("Definition operations require a readable definition list."));
  }
}

async function renderOperations(ctx: PageContext, projectId: string, definition: ReportDefinition, host: HTMLElement): Promise<void> {
  host.replaceChildren(loadingLine(ctx));
  const encodedProject = encodeURIComponent(projectId);
  const encodedReport = encodeURIComponent(definition.report_id);
  const [runsProbe, schedulesProbe] = await Promise.all([
    probe(`/api/projects/${encodedProject}/reports/${encodedReport}/runs`),
    probe(`/api/projects/${encodedProject}/reports/${encodedReport}/schedules`),
  ]);

  const head = el("div", { class: "cubi-split" },
    el("div", {},
      detailList([
        ["Definition", definition.name || definition.report_id],
        ["Report ID", definition.report_id],
        ["Subject", definition.subject || "—"],
        ["Revision", String(definition.revision ?? "—")],
      ]),
      sourceStamp("/api/projects/{id}/reports/{report_id}", definition.revision, null, ctx.locale),
    ),
    el("div", {},
      connectionRows([["Run history", runsProbe], ["Schedules", schedulesProbe]]),
      pageActions(runButton(ctx, projectId, definition, host)),
    ),
  );

  const blocks: HTMLElement[] = [head];
  if (runsProbe.state === "available") {
    try {
      const runs = await api.listReportRuns(projectId, definition.report_id);
      blocks.push(el("h3", { text: "Run history" }));
      blocks.push(runs.length ? recordsTable(runs, "run_id") : emptyLine("This definition has not run yet."));
    } catch (error) {
      blocks.push(errorPanel(ctx, error, () => { void renderOperations(ctx, projectId, definition, host); }));
    }
  } else {
    blocks.push(sourceState(runsProbe, ctx.t, { title: "Run history", source: "Platform reporting runtime" }));
  }

  if (schedulesProbe.state === "available") {
    try {
      const schedules = await api.listReportSchedules(projectId, definition.report_id);
      blocks.push(el("h3", { text: "Schedules" }));
      blocks.push(schedules.length ? recordsTable(schedules, "schedule_id") : emptyLine("No schedule is registered for this definition."));
    } catch (error) {
      blocks.push(errorPanel(ctx, error, () => { void renderOperations(ctx, projectId, definition, host); }));
    }
  } else {
    blocks.push(sourceState(schedulesProbe, ctx.t, { title: "Schedules", source: "Platform reporting runtime" }));
  }

  host.replaceChildren(...blocks);
}

function runButton(ctx: PageContext, projectId: string, definition: ReportDefinition, host: HTMLElement): HTMLElement {
  const button = el("button", { class: "cubi-btn cubi-btn-primary", text: "Run report", attrs: { type: "button" } });
  const status = el("span", { class: "cubi-field-hint" });
  const row = el("div", { class: "cubi-inline" }, button, status);
  button.addEventListener("click", async () => {
    button.disabled = true;
    status.textContent = "Requesting a run from the existing runtime…";
    try {
      const result = await api.runReport(projectId, definition.report_id);
      const runId = String(result.run_id ?? "—");
      status.textContent = `Runtime accepted the run (${runId}).`;
      await renderOperations(ctx, projectId, definition, host);
    } catch (error) {
      const detail = error instanceof ApiError ? `${error.code} (HTTP ${error.status})` : String(error);
      status.textContent = `The runtime refused the run: ${detail}. Nothing was queued locally.`;
      button.disabled = false;
    }
  });
  return testId(row, "reports-run");
}

function definitionsTable(projectId: string, rows: ReportDefinition[], selectedId: string): HTMLElement {
  const table = el("div", { class: "cubi-table-wrap" });
  const node = el("table", { class: "cubi-table" });
  node.append(el("thead", {}, el("tr", {},
    el("th", { text: "Definition" }),
    el("th", { text: "Subject" }),
    el("th", { text: "Revision" }),
    el("th", { text: "" }),
  )));
  const body = el("tbody");
  for (const row of rows) {
    const href = pageHref("reports", { project: projectId, report: row.report_id });
    const open = el("a", { class: "cubi-btn cubi-btn-ghost", text: row.report_id === selectedId ? "Selected" : "Inspect", attrs: { href } });
    body.append(el("tr", { class: row.report_id === selectedId ? "is-selected" : "" },
      el("td", {}, el("strong", { text: row.name || row.report_id }), el("div", { class: "cubi-field-hint", text: row.report_id })),
      el("td", { text: row.subject || "—" }),
      el("td", { text: String(row.revision ?? "—") }),
      el("td", {}, open),
    ));
  }
  node.append(body);
  table.append(node);
  return table;
}

function catalogueTable(rows: Record<string, unknown>[]): HTMLElement {
  const table = el("div", { class: "cubi-table-wrap" });
  const node = el("table", { class: "cubi-table" });
  node.append(el("thead", {}, el("tr", {},
    el("th", { text: "Entry" }),
    el("th", { text: "Description" }),
    el("th", { text: "Subject" }),
  )));
  const body = el("tbody");
  for (const row of rows) {
    body.append(el("tr", {},
      el("td", {}, el("strong", { text: String(row.label ?? row.name ?? row.report_id ?? row.id ?? row.key ?? "—") })),
      el("td", { text: String(row.description ?? (Array.isArray(row.fields) ? `${row.fields.length} fields` : "—")) }),
      el("td", { text: String(row.subject ?? row.label ?? "—") }),
    ));
  }
  node.append(body);
  table.append(node);
  return table;
}

function recordsTable(rows: Record<string, unknown>[], idKey: string): HTMLElement {
  const columns = collectColumns(rows);
  const table = el("div", { class: "cubi-table-wrap" });
  const node = el("table", { class: "cubi-table" });
  const headRow = el("tr", {}, el("th", { text: idKey.replace("_id", "") }));
  for (const column of columns) {
    if (column === idKey) continue;
    headRow.append(el("th", { text: column.replace(/_/g, " ") }));
  }
  node.append(el("thead", {}, headRow));
  const body = el("tbody");
  for (const row of rows.slice(0, 100)) {
    const tr = el("tr", {}, el("td", {}, el("strong", { text: String(row[idKey] ?? "—") })));
    for (const column of columns) {
      if (column === idKey) continue;
      tr.append(el("td", { text: formatValue(row[column]) }));
    }
    body.append(tr);
  }
  node.append(body);
  table.append(node);
  return table;
}

function collectColumns(rows: Record<string, unknown>[]): string[] {
  const seen: string[] = [];
  for (const row of rows.slice(0, 20)) {
    for (const key of Object.keys(row)) {
      if (!seen.includes(key) && seen.length < 8) seen.push(key);
    }
  }
  return seen;
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function jobsPanel(ctx: PageContext, projectId: string): HTMLElement {
  const wrap = el("div");
  wrap.append(note("Submission, workers and retries belong to the existing scheduling job service. This page only reads a job id you already have; it creates nothing.", "info"));

  const contract = el("div", { class: "cubi-table-wrap" });
  const table = el("table", { class: "cubi-table" });
  table.append(el("thead", {}, el("tr", {}, el("th", { text: "Existing route" }), el("th", { text: "Purpose" }), el("th", { text: "Owner" }))));
  table.append(el("tbody", {},
    el("tr", {}, el("td", {}, el("code", { text: "POST /api/v1/schedule/projects/{id}/jobs" })), el("td", { text: "Submit a durable run" }), el("td", { text: "Scheduling Core" })),
    el("tr", {}, el("td", {}, el("code", { text: "GET /api/v1/schedule/projects/{id}/jobs/{job_id}" })), el("td", { text: "Read job state" }), el("td", { text: "Scheduling Core" })),
    el("tr", {}, el("td", {}, el("code", { text: "GET …/jobs/{job_id}/result" })), el("td", { text: "Read the stored result" }), el("td", { text: "Scheduling Core" })),
    el("tr", {}, el("td", {}, el("code", { text: "POST …/jobs/{job_id}/cancel" })), el("td", { text: "Request cancellation" }), el("td", { text: "Scheduling Core" })),
  ));
  contract.append(table);
  wrap.append(contract);

  if (jobsLookup.status === "idle" || jobsLookup.status === "error") {
    const input = testId(textInput({ placeholder: "Existing job id", name: "job_id" }), "reports-job-id");
    const button = el("button", { class: "cubi-btn cubi-btn-secondary", text: "Read job", attrs: { type: "button" } });
    const host = el("div");
    if (jobsLookup.status === "error") host.append(note(jobsLookup.message ?? "The job could not be read.", "warning"));
    button.addEventListener("click", async () => {
      const jobId = input.value.trim();
      if (!jobId) {
        host.replaceChildren(note("Enter an existing job id first.", "warning"));
        return;
      }
      jobsLookup.status = "loading";
      host.replaceChildren(loadingLine(ctx));
      try {
        const job = await readJob(projectId, jobId);
        jobsLookup.status = "found";
        jobsLookup.job = job;
        host.replaceChildren(jobDetail(ctx, job));
      } catch (error) {
        jobsLookup.status = "error";
        const detail = error instanceof ApiError ? `${error.code} (HTTP ${error.status})` : String(error);
        jobsLookup.message = `The existing queue did not return this job: ${detail}. Nothing was substituted.`;
        host.replaceChildren(note(jobsLookup.message, "warning"));
      }
    });
    wrap.append(el("div", { class: "cubi-toolbar" }, input, button), host);
  } else if (jobsLookup.status === "found" && jobsLookup.job) {
    wrap.append(jobDetail(ctx, jobsLookup.job));
  } else {
    wrap.append(loadingLine(ctx));
  }
  return testId(wrap, "reports-jobs-panel");
}

function jobDetail(ctx: PageContext, job: Record<string, unknown>): HTMLElement {
  return el("div", {},
    detailList([
      ["Job", String(job.job_id ?? "—")],
      ["State", String(job.state ?? "—")],
      ["Attempts", `${String(job.attempts ?? "—")} / ${String(job.max_attempts ?? "—")}`],
      ["Engine", String(job.engine_version ?? "—")],
      ["Revision", String(job.revision ?? "—")],
      ["Updated", String(job.updated_at ?? "—")],
    ]),
    sourceStamp("Existing scheduling job service", job.revision as number | undefined, job.updated_at as string | undefined, ctx.locale),
  );
}

async function readJob(projectId: string, jobId: string): Promise<Record<string, unknown>> {
  const path = `/api/v1/schedule/projects/${encodeURIComponent(projectId)}/jobs/${encodeURIComponent(jobId)}`;
  const response = await fetch(path, { credentials: "same-origin", headers: { Accept: "application/json" }, cache: "no-store" });
  if (!response.ok) throw new ApiError(response.status, `HTTP_${response.status}`, `HTTP ${response.status}`);
  return (await response.json()) as Record<string, unknown>;
}

function connectionRows(entries: [string, CapabilityProbe][]): HTMLElement {
  const wrap = el("div", { class: "cubi-conn" });
  for (const [label, capability] of entries) {
    wrap.append(el("div", { class: "cubi-conn-row" },
      el("span", {}, el("strong", { text: label }), el("span", { class: "path", text: ` ${capability.path}` })),
      el("span", {}, badge(`${capability.status || "—"}`, capability.state === "available" ? "success" : capability.state === "forbidden" ? "warning" : capability.state === "unavailable" ? "neutral" : "danger"), el("span", { text: " " }), badge(capability.state, capability.state === "available" ? "success" : capability.state === "unavailable" ? "neutral" : "warning")),
    ));
  }
  return wrap;
}

function loadingLine(ctx: PageContext): HTMLElement {
  return el("div", { class: "cubi-loading" }, el("div", { class: "cubi-spinner" }), el("span", { text: ctx.t("common.loading") }));
}

function errorPanel(ctx: PageContext, error: unknown, retry: () => void): HTMLElement {
  const detail = error instanceof ApiError ? `${error.code} (HTTP ${error.status})` : String(error);
  const button = el("button", { class: "cubi-btn cubi-btn-secondary", text: ctx.t("common.retry"), attrs: { type: "button" } });
  button.addEventListener("click", retry);
  return stateBlock("error", "The reporting runtime could not be read", `${detail}. Nothing was substituted.`, [button]);
}

