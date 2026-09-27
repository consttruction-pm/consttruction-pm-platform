import assert from "node:assert/strict";
import test from "node:test";

import {
  addFormulaColumn,
  createWorkspaceState,
  selectActivity,
  selectWbs,
  setCalendarMode,
  setLocale,
  setControlSummary,
  setFieldOperations,
  setSiteDailyLogs,
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


test("control summary can be attached without changing project context", () => {
  const state = createWorkspaceState(context);
  const summary = {
    resultId: "result-1",
    generatedAt: "2026-09-27T08:00:00Z",
    summaryKey: "control.summary",
    metrics: Object.freeze({ progress_percent: 63 }),
    findings: [],
    proposedActions: [],
  };
  const next = setControlSummary(state, summary);
  assert.equal(next.controlSummary?.resultId, "result-1");
  assert.deepEqual(next.context, context);
});


test("site daily logs attach to the same project workspace", () => {
  const state = createWorkspaceState(context);
  const log = {
    logId: "log-1",
    logDate: "2026-09-27",
    locationKey: "tower-a",
    status: "submitted" as const,
    entries: [],
    updatedAt: "2026-09-27T10:00:00Z",
  };
  const next = setSiteDailyLogs(state, [log]);
  assert.equal(next.siteDailyLogs[0]?.logId, "log-1");
  assert.deepEqual(next.context, context);
});

test("field operations attach without changing project context", () => {
  const state = createWorkspaceState(context);
  const next = setFieldOperations(state, {
    fieldIssues: [{
      issueId: "issue-1",
      category: "quality",
      severity: "high",
      status: "open",
      titleKey: "issue.title",
      detailKey: null,
      reportedBy: "user-1",
      locationKey: "tower-a",
      activityIds: ["A-101"],
      evidenceCount: 1,
    }],
    fieldTimecards: [{
      timecardId: "tc-1",
      personId: "person-1",
      logDate: "2026-09-27",
      workplaceKey: "tower-a",
      attendanceStatus: "on_site",
      startAt: null,
      endAt: null,
      activityAllocations: [{ activityId: "A-101", quantity: "8.00", unit: "hr" }],
    }],
    equipmentStatuses: [{
      reportId: "eq-1",
      equipmentId: "excavator-01",
      reportDate: "2026-09-27",
      workplaceKey: "tower-a",
      status: "active",
      breakdownCauseKey: null,
      reportedBy: "user-2",
      activityAllocations: [],
      meterHours: "120.00",
    }],
  });
  assert.equal(next.fieldIssues[0]?.issueId, "issue-1");
  assert.equal(next.fieldTimecards[0]?.activityAllocations[0]?.quantity, "8.00");
  assert.equal(next.equipmentStatuses[0]?.equipmentId, "excavator-01");
  assert.deepEqual(next.context, context);
});

test("typed activity cells and Gantt data remain server-projected", () => {
  const state = createWorkspaceState(context);
  const next = withActivities(state, [
    {
      id: "A-1",
      wbsId: "W-1",
      code: "01",
      name: "Foundation",
      cells: {
        start: "2026-09-01T08:00:00Z",
        finish: "2026-09-05T17:00:00Z",
        duration: 4,
        progress: 35,
      },
      gantt: {
        start: "2026-09-01T08:00:00Z",
        finish: "2026-09-05T17:00:00Z",
        progressPercent: 35,
        critical: true,
      },
    },
  ]);

  assert.equal(next.activities[0]?.cells?.duration, 4);
  assert.equal(next.activities[0]?.gantt?.critical, true);
  assert.equal(next.activities[0]?.gantt?.progressPercent, 35);
});

test("invalid Gantt geometry is rejected at the workspace boundary", () => {
  const state = createWorkspaceState(context);
  assert.throws(
    () =>
      withActivities(state, [
        {
          id: "A-1",
          wbsId: "W-1",
          code: "01",
          name: "Foundation",
          gantt: {
            start: "2026-09-05",
            finish: "2026-09-01",
            progressPercent: 40,
            critical: false,
          },
        },
      ]),
    /INVALID_GANTT_DATA/,
  );
});
