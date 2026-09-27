import assert from "node:assert/strict";
import test from "node:test";

import {
  addFormulaColumn,
  createWorkspaceState,
  selectActivity,
  selectWbs,
  setCalendarMode,
  setLocale,
  withActivities,
} from "./workspace-model.js";

const context = {
  tenant_id: "tenant-1",
  project_id: "project-1",
  revision: 4,
};

test("workspace model creates a bilingual Main Workspace state", () => {
  const state = createWorkspaceState(context, "fa", "jalali");

  assert.equal(state.direction, "rtl");
  assert.equal(state.calendarMode, "jalali");
  assert.equal(state.activeMenu, "schedule");
  assert.equal(state.visiblePanels.activity_grid, true);
  assert.equal(state.columns.find((column) => column.id === "duration")?.dataType, "duration");
});

test("WBS selection clears Activity selection", () => {
  let state = createWorkspaceState(context);
  state = withActivities(state, [
    { id: "A-1", wbsId: "W-1", code: "01", name: "Foundation" },
    { id: "A-2", wbsId: "W-2", code: "02", name: "Structure" },
  ]);
  state = selectActivity(state, "A-1");
  assert.equal(state.selectedActivityId, "A-1");

  state = selectWbs(state, "W-2");
  assert.equal(state.selectedWbsId, "W-2");
  assert.equal(state.selectedActivityId, null);
});

test("activity selection rejects activities that are not loaded", () => {
  const state = createWorkspaceState(context);
  assert.throws(() => selectActivity(state, "missing"), /ACTIVITY_NOT_FOUND/);
});

test("locale and calendar switches preserve project context", () => {
  let state = createWorkspaceState(context);
  state = setLocale(state, "fa");
  state = setCalendarMode(state, "jalali");

  assert.equal(state.direction, "rtl");
  assert.equal(state.calendarMode, "jalali");
  assert.deepEqual(state.context, context);
});

test("formula columns remain metadata and do not calculate client values", () => {
  const state = createWorkspaceState(context);
  const next = addFormulaColumn(state, {
    id: "variance",
    label: "Variance",
    dataType: "decimal",
    editable: false,
    formula: "[EV] - [PV]",
    width: 120,
  });

  assert.equal(next.columns.at(-1)?.formula, "[EV] - [PV]");
  assert.equal(next.columns.at(-1)?.dataType, "decimal");
});

test("duplicate activity ids are rejected", () => {
  const state = createWorkspaceState(context);
  assert.throws(
    () =>
      withActivities(state, [
        { id: "A-1", wbsId: "W-1", code: "01", name: "One" },
        { id: "A-1", wbsId: "W-1", code: "02", name: "Two" },
      ]),
    /INVALID_ACTIVITY_ROWS/,
  );
});
