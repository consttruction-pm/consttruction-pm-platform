/**
 * Page 19 — Team member activities.
 *
 * Activities and their progress belong to Engineering. This page is a
 * read-only projection of the authoritative Engineering route; it offers no
 * write control and never derives a value of its own.
 */

import type { PageContext } from "../app.js";
import { api, ApiError, probe, type ActivityEnvelope } from "../api.js";
import { badge, el } from "../ui.js";
import { connectionRow, note, section, sectionBody, selectControl, sourceState, testId, textInput } from "./shared.js";

export function renderMemberActivities(ctx: PageContext, host: HTMLElement): void {
  const intro = section("Engineering-owned activity records", "Activities, their status and their progress are maintained in Engineering; Enterprise reads them and links back.");
  const help = el("a", { class: "cubi-btn cubi-btn-ghost", text: "Open the Help topic", attrs: { target: "_blank", rel: "noopener noreferrer" } });
  help.href = "https://docs.oracle.com/cd/G48897_01/p6help/en/50904.htm";
  sectionBody(intro,
    el("p", { class: "cubi-field-hint", text: "Help topic: About P6 Team Member Status Updates" }),
    note("This page has no create, edit or delete control. Writing progress here would duplicate the Engineering calculation, so it is not offered.", "warning"),
    el("div", { class: "cubi-row" }, help),
  );
  testId(intro, "member-activities-intro");
  host.append(intro);

  const list = section("Project activities", "Read from the Engineering activity route for the selected project.");
  const picker = selectControl(
    [{ value: "", label: "Select a project" }, ...ctx.projects.map((project) => ({ value: project.project_id, label: project.name }))],
    ctx.projects[0]?.project_id ?? "",
    (value) => { void load(value); },
  );
  let currentProject = "";
  let lastRows: { activity_id?: string; name?: string; status?: string; percent_complete?: number | null }[] = [];
  const search = textInput({ placeholder: "Search activity id or name" });
  search.disabled = true;
  search.addEventListener("input", () => {
    const needle = search.value.trim().toLocaleLowerCase();
    const rows = !needle ? lastRows : lastRows.filter((row) => `${row.activity_id ?? ""} ${row.name ?? ""}`.toLocaleLowerCase().includes(needle));
    listHost.replaceChildren(rows.length ? activityTable(currentProject, rows) : el("p", { class: "cubi-field-hint", text: "No activity matches the current search." }));
  });
  const listHost = el("div", { class: "cubi-field-hint", text: "Select a project to read its activities." });
  sectionBody(list, el("div", { class: "cubi-toolbar" }, el("label", { class: "cubi-field" }, el("span", { class: "cubi-field-label", text: "Project" }), picker), search), listHost);
  testId(list, "member-activities-list");
  host.append(list);

  const capability = section("Connection", "The answer from the Engineering route is reported unchanged.");
  const capabilityHost = el("div", { class: "cubi-field-hint", text: "No route has been read yet." });
  sectionBody(capability, capabilityHost);
  testId(capability, "member-activities-capability");
  host.append(capability);

  const load = async (projectId: string): Promise<void> => {
    if (!projectId) {
      listHost.replaceChildren(el("p", { class: "cubi-field-hint", text: "Select a project to read its activities." }));
      capabilityHost.replaceChildren(el("p", { class: "cubi-field-hint", text: "No route has been read yet." }));
      return;
    }
    const path = `/api/projects/${encodeURIComponent(projectId)}/p6/activities`;
    const state = await probe(path);
    capabilityHost.replaceChildren(connectionRow("Engineering activities", state, ctx.t));
    if (state.state === "unauthenticated") {
      ctx.onUnauthorized();
      return;
    }
    if (state.state !== "available") {
      listHost.replaceChildren(sourceState(state, ctx.t, {
        title: "Engineering activities are not reachable",
        source: "Engineering activity API",
        retry: () => { void load(projectId); },
      }));
      return;
    }
    try {
      const payload = await api.listProjectActivities(projectId);
      const rows = (payload.activities ?? []).map((entry) => entry.activity).filter((activity): activity is NonNullable<ActivityEnvelope["activity"]> => Boolean(activity));
      currentProject = projectId;
      lastRows = rows;
      search.value = "";
      search.disabled = rows.length === 0;
      listHost.replaceChildren(rows.length ? activityTable(projectId, rows) : el("p", { class: "cubi-field-hint", text: "Engineering answered with zero activities for this project." }));
    } catch (error) {
      listHost.replaceChildren(el("p", { class: "cubi-alert cubi-alert-error", text: error instanceof ApiError ? `${error.code} (HTTP ${error.status})` : String(error) }));
    }
  };

  if (ctx.projects.length >= 1) {
    picker.value = ctx.projects[0].project_id;
    void load(ctx.projects[0].project_id);
  }
}

function activityTable(
  projectId: string,
  rows: { activity_id?: string; name?: string; status?: string; percent_complete?: number | null }[],
): HTMLElement {
  const wrap = el("div", { class: "cubi-table-wrap" });
  testId(wrap, "member-activities-table");
  const table = el("table", { class: "cubi-table" });
  table.append(el("thead", {}, el("tr", {},
    el("th", { text: "Activity" }),
    el("th", { text: "Name" }),
    el("th", { text: "Status" }),
    el("th", { text: "Percent complete" }),
    el("th", { text: "" }),
  )));
  const body = el("tbody");
  for (const row of rows) {
    const open = el("a", { class: "cubi-btn cubi-btn-ghost", text: "Open in Engineering" });
    open.href = `/app?project=${encodeURIComponent(projectId)}&view=live`;
    body.append(el("tr", {},
      el("td", { text: row.activity_id ?? "—" }),
      el("td", { text: row.name ?? "—" }),
      el("td", {}, badge(row.status ?? "—", "neutral")),
      el("td", { text: row.percent_complete === null || row.percent_complete === undefined ? "—" : `${row.percent_complete}%` }),
      el("td", {}, open),
    ));
  }
  table.append(body);
  wrap.append(table);
  wrap.append(el("p", { class: "cubi-note", text: `Source: Engineering activity master route · project ${projectId} · read-only. Values are shown exactly as returned; nothing is recalculated.` }));
  return wrap;
}
