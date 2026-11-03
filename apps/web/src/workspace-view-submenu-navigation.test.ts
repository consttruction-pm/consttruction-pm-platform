import assert from "node:assert/strict";
import test from "node:test";

import { renderMainWorkspace } from "./workspace-view.js";
import { createWorkspaceState } from "./workspace-model.js";

type RenderContainer = {
  innerHTML: string;
  querySelectorAll: () => HTMLElement[];
};

function render(activeMenu: "schedule" | "reports" | "tracking"): string {
  const state = {
    ...createWorkspaceState(
      { tenant_id: "tenant-1", project_id: "project-1", revision: 3 },
      "en",
    ),
    activeMenu,
  };
  const container: RenderContainer = {
    innerHTML: "",
    querySelectorAll: () => [],
  };
  renderMainWorkspace(container as unknown as HTMLElement, state);
  return container.innerHTML;
}

test("implemented submenu items navigate to the corresponding workspace panels", () => {
  const html = render("schedule");

  assert.match(html, /<a class="cp-submenu-item" href="#cp-activity-grid">Activity Grid<\/a>/);
  assert.match(html, /<a class="cp-submenu-item" href="#cp-gantt">Gantt Chart<\/a>/);
  assert.match(html, /id="cp-activity-grid"/);
  assert.match(html, /id="cp-gantt"/);
});

test("Reports submenu items open their read-only report center tabs", () => {
  const html = render("reports");

  assert.match(html, /data-navigation-action="reports-tab:library"/);
  assert.match(html, /data-navigation-action="reports-tab:layouts"/);
  assert.match(html, /data-navigation-action="reports-tab:page-setup"/);
  assert.match(html, /data-navigation-action="reports-tab:export"/);
  assert.match(html, /class="cp-reports-center"/);
  assert.match(html, /disabled until the report service is connected/);
  assert.doesNotMatch(html, /href="#cp-/);
});

test("Tracking layout choices are selectable while data-dependent actions remain explicitly disabled", () => {
  const html = render("tracking");

  assert.match(html, /data-tracking-layout/);
  assert.match(html, /<option value="table"[^>]*>Project Table<\/option>/);
  assert.match(html, /<option value="bar-chart"[^>]*>Project Bar Chart<\/option>/);
  assert.match(html, /<option value="gantt-profile"[^>]*>Project Gantt \/ Profile<\/option>/);
  assert.match(html, /<option value="resource-analysis"[^>]*>Resource Analysis<\/option>/);
  assert.match(html, /data-tracking-surface="table"/);
  assert.match(html, /No tracking data/);
  assert.match(html, /<button type="button" disabled>Refresh Data<\/button>/);
  assert.match(html, /<button type="button" disabled>Save Layout<\/button>/);
});
