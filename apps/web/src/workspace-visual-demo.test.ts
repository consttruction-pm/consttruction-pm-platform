import assert from "node:assert/strict";
import test from "node:test";
import { createWorkspaceState, type WorkspaceState } from "./workspace-model.js";
import { createVisualDemoState, renderVisualDemo } from "./workspace-visual-demo.js";

function liveWorkspace(): WorkspaceState {
  const context = {
    tenant_id: "tenant-live-test",
    project_id: "cubi-live-test-01",
    revision: 12,
  };
  const base = createWorkspaceState(context);
  return {
    ...base,
    wbsNodes: [
      {
        id: "WBS-ROOT",
        parentKind: "project",
        parentWbsId: null,
        localCode: "1",
        name: "North Treatment Plant",
        sequenceNumber: 0,
        recordRevision: 1,
      },
      {
        id: "WBS-CIVIL",
        parentKind: "wbs",
        parentWbsId: "WBS-ROOT",
        localCode: "1.2",
        name: "Civil Works",
        sequenceNumber: 20,
        recordRevision: 1,
      },
    ],
    activities: [
      {
        id: "CIV-010",
        wbsId: "WBS-CIVIL",
        code: "CIV-010",
        name: "Excavate pump foundation",
        cells: {
          "activity.planned_duration": "4",
          "activity.remaining_duration": "2",
          "activity.duration_percent_complete": 50,
          "activity.status": "In Progress",
          "activity.early_start": "2026-11-02",
          "activity.early_finish": "2026-11-05",
          "activity.late_start": "2026-11-04",
          "activity.late_finish": "2026-11-09",
          "activity.total_float": 2,
          "activity.free_float": 1,
        },
        gantt: {
          start: "2026-11-02",
          finish: "2026-11-05",
          progressPercent: 50,
          critical: false,
        },
      },
      {
        id: "CIV-020",
        wbsId: "WBS-CIVIL",
        code: "CIV-020",
        name: "Cast reinforced concrete",
        cells: {
          "activity.planned_duration": "6",
          "activity.remaining_duration": "6",
          "activity.status": "Not Started",
          "activity.total_float": 0,
          "activity.free_float": 0,
        },
        gantt: {
          start: "2026-11-09",
          finish: "2026-11-16",
          progressPercent: 0,
          critical: true,
        },
      },
    ],
    relationships: [
      {
        id: "REL-CIV-010-020",
        predecessorId: "CIV-010",
        successorId: "CIV-020",
        type: "FS",
        lagValue: "2",
        lagUnit: "working-day",
        recordRevision: 1,
      },
    ],
  };
}

test("default visual workspace is projected from the authenticated project data", () => {
  const workspace = liveWorkspace();
  const state = createVisualDemoState("en", workspace);
  state.activityId = "CIV-020";
  const html = renderVisualDemo(state);

  assert.match(html, /cubi-live-test-01/);
  assert.match(html, /North Treatment Plant/);
  assert.match(html, /Civil Works/);
  assert.match(html, /CIV-010/);
  assert.match(html, /Excavate pump foundation/);
  assert.match(html, /CIV-020/);
  assert.match(html, /Cast reinforced concrete/);
  assert.match(html, /working-day/);
  assert.match(html, /Connected project/);
  assert.match(html, /read-only visual shell/);
  assert.doesNotMatch(html, /CUBI-DEMO-001/);
  assert.doesNotMatch(html, /Riverside Pump Station Upgrade/);
  assert.doesNotMatch(html, /A1320/);
});

test("visual workspace does not fabricate dates, progress, budgets or baseline for live projects", () => {
  const workspace = liveWorkspace();
  const withoutFacts: WorkspaceState = {
    ...workspace,
    activities: workspace.activities.map((activity) => ({
      ...activity,
      gantt: undefined,
      cells: {},
    })),
  };
  const html = renderVisualDemo(createVisualDemoState("en", withoutFacts));

  assert.match(html, /No authoritative schedule dates are available/);
  assert.match(html, /—/);
  assert.doesNotMatch(html, /03-Dec-2026/);
  assert.doesNotMatch(html, /BL-01/);
});

test("unconnected live project modules show an honest placeholder rather than demo rows", () => {
  const state = createVisualDemoState("en", liveWorkspace());
  state.window = "resources";
  const html = renderVisualDemo(state);

  assert.match(html, /This view is not connected to live project data yet/);
  assert.doesNotMatch(html, /Mobile crane 50t/);
  assert.doesNotMatch(html, /R-100/);
});
