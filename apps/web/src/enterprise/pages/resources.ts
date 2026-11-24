import type { PageContext } from "../app.js";
import { ApiError, api, probe, type ResourceRecord } from "../api.js";
import { pageHref } from "../router.js";
import { badge, el } from "../ui.js";
import {
  detailList,
  emptyLine,
  note,
  pageActions,
  projectFilterOptions,
  section,
  sectionBody,
  selectControl,
  sourceStamp,
  sourceState,
  testId,
} from "./shared.js";

/**
 * Page 13 — Resources and capacity.
 *
 * Read-only. Engineering is the owner of resource and capacity facts. This page
 * displays raw records with their revision and never aggregates, levels,
 * forecasts or recomputes utilisation.
 */

export function renderResources(ctx: PageContext, host: HTMLElement): void {
  const requested = ctx.query.get("project") ?? "";
  const allProjects = [...ctx.projects, ...(ctx.sharedProjects ?? [])];
  const selected = allProjects.find((project) => project.project_id === requested) ?? allProjects[0] ?? null;

  const intro = section("Read-only Engineering projection", "Resource names, units, calendars and capacity segments come from Engineering. Enterprise does not own or modify them.");
  sectionBody(intro,
    note("No aggregation, leveling, rate, cost or utilisation calculation is performed on this page. Values are displayed exactly as returned, with their revision.", "warning"),
  );
  testId(intro, "resources-intro");
  host.append(intro);

  const selectorCard = section("Project scope", "Choose the project whose Engineering records should be projected.");
  const selector = testId(selectControl(
    projectFilterOptions(ctx.projects, ctx.sharedProjects ?? [], "Select a project"),
    selected?.project_id ?? "",
    (value) => ctx.navigate(pageHref("resources", { project: value })),
  ), "resources-project");
  sectionBody(selectorCard, el("div", { class: "cubi-toolbar" }, selector));
  host.append(selectorCard);

  if (!selected) {
    host.append(sectionBody(section("No project in scope", ""), emptyLine("No project is visible to this session.")));
    return;
  }

  const details = section("Project context", "Selected project facts.");
  sectionBody(details,
    detailList([
      ["Project", selected.name],
      ["Project ID", selected.project_id],
      ["Revision", String(selected.revision)],
      ["Status", selected.status || "—"],
      ["Responsible manager", selected.obs_responsible_manager || "—"],
    ]),
    pageActions(linkButton("Open Engineering workspace", "/app/"), linkButton("Project portal", pageHref("projects", { project: selected.project_id }))),
  );
  testId(details, "resources-context");
  host.append(details);

  const register = section("Resource register", "Raw resource records from the Engineering read model.");
  const registerHost = el("div", {}, el("div", { class: "cubi-loading" }, el("div", { class: "cubi-spinner" }), el("span", { text: ctx.t("common.loading") })));
  sectionBody(register, registerHost);
  testId(register, "resources-register");
  host.append(register);

  const capacity = section("Capacity segments", "Raw capacity slices. Utilisation and remaining capacity are not calculated here.");
  const capacityHost = el("div", {}, el("div", { class: "cubi-loading" }, el("div", { class: "cubi-spinner" }), el("span", { text: ctx.t("common.loading") })));
  sectionBody(capacity, capacityHost);
  testId(capacity, "resources-capacity");
  host.append(capacity);

  void load(ctx, selected.project_id, registerHost, capacityHost);
}

async function load(ctx: PageContext, projectId: string, registerHost: HTMLElement, capacityHost: HTMLElement): Promise<void> {
  const [resourcesProbe, capacityProbe] = await Promise.all([
    probe(`/api/projects/${encodeURIComponent(projectId)}/p6/resources`),
    probe(`/api/projects/${encodeURIComponent(projectId)}/p6/resource-capacities`),
  ]);

  if (resourcesProbe.state === "available") {
    try {
      const rows = await api.listResources(projectId);
      registerHost.replaceChildren(rows.length ? resourceTable(rows) : emptyLine("No resource is registered for this project."), sourceStamp("Engineering resource read model", "per resource", null, ctx.locale));
    } catch (error) {
      registerHost.replaceChildren(errorPanel(ctx, error));
    }
  } else {
    registerHost.replaceChildren(sourceState(resourcesProbe, ctx.t, { title: "Resource register", source: "Engineering resource read model" }));
  }

  if (capacityProbe.state === "available") {
    try {
      const payload = await fetchJson<{ capacities?: Record<string, unknown>[] }>(`/api/projects/${encodeURIComponent(projectId)}/p6/resource-capacities`);
      const rows = payload.capacities ?? [];
      capacityHost.replaceChildren(rows.length ? capacityTable(rows) : emptyLine("No capacity segment is registered for this project."), sourceStamp("Engineering capacity read model", "per segment", null, ctx.locale));
    } catch (error) {
      capacityHost.replaceChildren(errorPanel(ctx, error));
    }
  } else {
    capacityHost.replaceChildren(sourceState(capacityProbe, ctx.t, { title: "Capacity read model", source: "Engineering capacity read model", detail: "Capacity stays authoritative in Engineering." }));
  }
}

function resourceTable(rows: ResourceRecord[]): HTMLElement {
  const table = el("div", { class: "cubi-table-wrap" });
  const node = el("table", { class: "cubi-table" });
  node.append(el("thead", {}, el("tr", {},
    el("th", { text: "Resource" }),
    el("th", { text: "Type" }),
    el("th", { text: "Unit" }),
    el("th", { text: "Calendar" }),
    el("th", { text: "Email" }),
    el("th", { text: "Active" }),
    el("th", { text: "Revision" }),
  )));
  const body = el("tbody");
  for (const row of rows) {
    body.append(el("tr", {},
      el("td", {}, el("strong", { text: row.name }), el("div", { class: "cubi-field-hint", text: row.resource_id })),
      el("td", { text: row.resource_type }),
      el("td", { text: row.unit_of_measure || "—" }),
      el("td", { text: row.calendar_id || "—" }),
      el("td", { text: row.email || "—" }),
      el("td", {}, badge(row.is_active ? "active" : "inactive", row.is_active ? "success" : "neutral")),
      el("td", { text: String(row.record_revision) }),
    ));
  }
  node.append(body);
  table.append(node);
  return table;
}

function capacityTable(rows: Record<string, unknown>[]): HTMLElement {
  const table = el("div", { class: "cubi-table-wrap" });
  const node = el("table", { class: "cubi-table" });
  node.append(el("thead", {}, el("tr", {},
    el("th", { text: "Resource" }),
    el("th", { text: "From" }),
    el("th", { text: "To" }),
    el("th", { text: "Max units" }),
    el("th", { text: "Unit basis" }),
    el("th", { text: "Hours / period" }),
    el("th", { text: "Project revision" }),
  )));
  const body = el("tbody");
  for (const entry of rows) {
    const segment = (entry.capacity as Record<string, unknown> | undefined) ?? entry;
    const scope = (entry.scope as Record<string, unknown> | undefined) ?? {};
    body.append(el("tr", {},
      el("td", {}, el("strong", { text: String(segment.resource_id ?? "—") })),
      el("td", { text: String(segment.effective_from ?? "—") }),
      el("td", { text: segment.effective_to ? String(segment.effective_to) : "open" }),
      el("td", { text: String(segment.max_units ?? "—") }),
      el("td", { text: String(segment.unit_basis ?? "—") }),
      el("td", { text: String(segment.hours_per_time_period ?? "—") }),
      el("td", { text: String(scope.project_revision ?? "—") }),
    ));
  }
  node.append(body);
  table.append(node);
  return table;
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { credentials: "same-origin", headers: { Accept: "application/json" }, cache: "no-store" });
  if (!response.ok) throw new ApiError(response.status, `HTTP_${response.status}`, `HTTP ${response.status}`);
  return (await response.json()) as T;
}

function errorPanel(ctx: PageContext, error: unknown): HTMLElement {
  const detail = error instanceof ApiError ? `${error.code} (HTTP ${error.status})` : String(error);
  const block = el("div", { class: "cubi-alert cubi-alert-error", attrs: { role: "alert" } }, el("span", { text: `The source could not be read: ${detail}. Nothing was substituted.` }));
  return block;
}

function linkButton(text: string, href: string): HTMLElement {
  const anchor = el("a", { class: "cubi-btn cubi-btn-secondary", text });
  anchor.href = href;
  return anchor;
}
