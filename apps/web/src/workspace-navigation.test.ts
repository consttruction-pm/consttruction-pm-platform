import assert from "node:assert/strict";
import test from "node:test";

import {
  getWorkspaceNavigation,
  getWorkspaceNavigationStatus,
  WORKSPACE_NAVIGATION,
} from "./workspace-navigation.js";
import { createWorkspaceState } from "./workspace-model.js";

test("workspace navigation exposes every V1 main menu surface", () => {
  assert.deepEqual(
    WORKSPACE_NAVIGATION.map((item) => item.key),
    ["project", "schedule", "progress", "resources", "cost", "documents", "reports", "control", "settings"],
  );
});

test("schedule is the implemented Activity/WBS surface and exposes its review screens", () => {
  const item = getWorkspaceNavigation("schedule");

  assert.equal(item.status, "implemented");
  assert.deepEqual(item.submenus.map((submenu) => submenu.en), ["Activity Grid", "Gantt Chart"]);
});

test("unsupported V1 surfaces are explicitly marked preview instead of being presented as implemented", () => {
  assert.equal(getWorkspaceNavigation("progress").status, "preview");
  assert.equal(getWorkspaceNavigation("resources").status, "preview");
  assert.equal(getWorkspaceNavigation("cost").status, "preview");
  assert.equal(getWorkspaceNavigation("reports").status, "preview");
});

test("navigation status follows the workspace active menu", () => {
  const state = createWorkspaceState({
    tenant_id: "tenant-1",
    project_id: "project-1",
    revision: 0,
  });

  assert.equal(getWorkspaceNavigationStatus(state), "implemented");
  assert.equal(
    getWorkspaceNavigationStatus({ ...state, activeMenu: "reports" }),
    "preview",
  );
});
