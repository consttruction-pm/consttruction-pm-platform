import assert from "node:assert/strict";
import test from "node:test";

import { renderMainWorkspace } from "./workspace-view.js";
import { createWorkspaceState } from "./workspace-model.js";

type RenderContainer = {
  innerHTML: string;
  querySelectorAll: () => HTMLElement[];
};

function render(activeMenu: "schedule" | "reports"): string {
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

test("preview-only submenu items remain non-interactive", () => {
  const html = render("reports");

  assert.match(html, /<span class="cp-submenu-item" aria-disabled="true" data-submenu-status="preview">Reports<\/span>/);
  assert.match(html, /<span class="cp-submenu-item" aria-disabled="true" data-submenu-status="preview">Print<\/span>/);
  assert.doesNotMatch(html, /href="#cp-/);
});
