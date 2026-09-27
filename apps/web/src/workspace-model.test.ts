import { describe, expect, it } from "vitest";

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

describe("workspace model", () => {
  it("creates a shared Main Workspace state without calculating domain values", () => {
    const state = createWorkspaceState(context, "fa", "jalali");

    expect(state.direction).toBe("rtl");
    expect(state.calendarMode).toBe("jalali");
    expect(state.activeMenu).toBe("schedule");
    expect(state.visiblePanels.activity_grid).toBe(true);
    expect(state.columns.find((column) => column.id === "duration")?.dataType).toBe("duration");
  });

  it("keeps WBS and Activity selection mutually scoped", () => {
    let state = createWorkspaceState(context);
    state = withActivities(state, [
      { id: "A-1", wbsId: "W-1", code: "01", name: "Foundation" },
      { id: "A-2", wbsId: "W-2", code: "02", name: "Structure" },
    ]);
    state = selectActivity(state, "A-1");
    expect(state.selectedActivityId).toBe("A-1");

    state = selectWbs(state, "W-2");
    expect(state.selectedWbsId).toBe("W-2");
    expect(state.selectedActivityId).toBeNull();
  });

  it("rejects selection of an activity that is not loaded", () => {
    const state = createWorkspaceState(context);
    expect(() => selectActivity(state, "missing")).toThrow("ACTIVITY_NOT_FOUND");
  });

  it("switches locale direction without mutating project context", () => {
    let state = createWorkspaceState(context);
    state = setLocale(state, "fa");
    state = setCalendarMode(state, "jalali");

    expect(state.direction).toBe("rtl");
    expect(state.calendarMode).toBe("jalali");
    expect(state.context).toEqual(context);
  });

  it("keeps formula columns as metadata only", () => {
    const state = createWorkspaceState(context);
    const next = addFormulaColumn(state, {
      id: "variance",
      label: "Variance",
      dataType: "decimal",
      editable: false,
      formula: "[EV] - [PV]",
      width: 120,
    });

    expect(next.columns.at(-1)?.formula).toBe("[EV] - [PV]");
    expect(next.columns.at(-1)?.dataType).toBe("decimal");
  });

  it("rejects duplicate activity ids", () => {
    const state = createWorkspaceState(context);
    expect(() =>
      withActivities(state, [
        { id: "A-1", wbsId: "W-1", code: "01", name: "One" },
        { id: "A-1", wbsId: "W-1", code: "02", name: "Two" },
      ]),
    ).toThrow("INVALID_ACTIVITY_ROWS");
  });
});
