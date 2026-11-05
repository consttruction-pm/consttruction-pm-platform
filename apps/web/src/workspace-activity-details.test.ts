import assert from "node:assert/strict";
import test from "node:test";

import { createWorkspaceState, type WorkspaceActivityRow } from "./workspace-model.js";
import {
  ACTIVITY_DETAILS_TABS,
  ACTIVITY_DETAILS_VISIBLE_TABS_STORAGE_KEY,
  readActivityDetailsVisibleTabs,
  renderActivityDetailsPanel,
  renderActivityDetailsTabContent,
} from "./workspace-activity-details.js";

const ACTIVITIES: WorkspaceActivityRow[] = [
  { id: "act-1", wbsId: "wbs-1", code: "A120", name: "Excavate foundation" },
  { id: "act-2", wbsId: "wbs-1", code: "A130", name: "Pour foundation" },
];

function render(selectedActivityId: string | null): string {
  return renderActivityDetailsPanel({
    locale: "en",
    activities: ACTIVITIES,
    selectedActivityId,
    relationships: [],
    projectName: "Shared Core",
    dataDate: "2026-10-07",
    calendarMode: "gregorian",
  });
}

test("activity details keeps the selected identity in the cp-detail-selected contract", () => {
  const html = render("act-2");
  assert.match(html, /<span class="cp-details-id cp-detail-selected">A130<\/span>/);
  assert.match(html, /data-details-prev="act-1"/);
  assert.match(html, /data-details-next=""/);
});

test("activity details renders an explicit placeholder when nothing is selected", () => {
  const html = render(null);
  assert.match(html, /cp-detail-selected">—<\/span>/);
  assert.match(html, /data-details-prev="" disabled/);
  assert.match(html, /data-details-next="" disabled/);
});

test("Projects window keeps the bottom pane scoped to Project Details", () => {
  const state = createWorkspaceState({
    tenant_id: "tenant-1", project_id: "project-1", revision: 7,
  });
  const projectState = {
    ...state,
    activeMenu: "project" as const,
    selectedWbsId: "wbs-1",
    wbsNodes: [{
      id: "wbs-1", parentKind: "project" as const, parentWbsId: null,
      localCode: "01", name: "Civil works", sequenceNumber: 1, recordRevision: 2,
    }],
  };
  const html = renderActivityDetailsPanel({
    locale: "en", activities: ACTIVITIES, selectedActivityId: null,
    relationships: [], projectName: "project-1", dataDate: "—",
    calendarMode: "gregorian", state: projectState,
  });
  assert.match(html, /Project Details/);
  assert.match(html, /data-detail-tab="defaults"/);
  assert.match(html, /data-detail-tab="settings"/);
  assert.match(html, /data-detail-tab="baselines"/);
  assert.match(html, /data-detail-tab="documents"/);
  assert.match(html, /data-detail-tab="history"/);
  assert.doesNotMatch(html, /WBS Details/);
});


test("Activity Details exposes the exact Version 26 Professional tab inventory and Customize Tabs dialog", () => {
  assert.deepEqual(ACTIVITY_DETAILS_TABS.map((tab) => tab.id), [
    "general", "status", "resources", "predecessors", "successors", "relationships",
    "codes", "notebook", "steps", "documents", "expenses", "issues", "risks",
    "summary", "udfs", "update-history",
  ]);
  const html = render("act-2");
  assert.match(html, /data-detail-tabs-customize/);
  assert.match(html, /data-detail-tabs-dialog/);
  assert.match(html, /data-detail-tab-visible="issues"/);
  assert.match(html, /data-detail-tab-visible="update-history"/);
  assert.doesNotMatch(html, /data-detail-tab="calendar"/);
  assert.doesNotMatch(html, /data-detail-tab="tasks"/);
});

test("Activity Details visible-tab preferences ignore stale ids and never hide all tabs", () => {
  const partialStorage = {
    getItem: (key: string) => key === ACTIVITY_DETAILS_VISIBLE_TABS_STORAGE_KEY
      ? JSON.stringify(["general", "issues", "calendar", "unknown"])
      : null,
  } as unknown as Storage;
  assert.deepEqual(readActivityDetailsVisibleTabs(partialStorage), ["general", "issues"]);

  const staleOnlyStorage = {
    getItem: () => JSON.stringify(["removed-tab", "calendar"]),
  } as unknown as Storage;
  assert.equal(readActivityDetailsVisibleTabs(staleOnlyStorage).length, 16);

  const malformedStorage = { getItem: () => "not-json" } as unknown as Storage;
  assert.equal(readActivityDetailsVisibleTabs(malformedStorage).length, 16);
});

test("Activity Issues tab renders only issue records linked to the selected activity", () => {
  const base = createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 7 });
  const state = {
    ...base,
    activities: ACTIVITIES,
    fieldIssues: [
      {
        issueId: "ISS-LINKED",
        category: "quality",
        severity: "high" as const,
        status: "open" as const,
        titleKey: "Foundation concrete test failed",
        detailKey: null,
        reportedBy: "site.manager",
        locationKey: null,
        activityIds: ["act-2"],
        evidenceCount: 1,
        updatedAt: "2026-11-05T09:30:00Z",
      },
      {
        issueId: "ISS-OTHER",
        category: "safety",
        severity: "medium" as const,
        status: "in_progress" as const,
        titleKey: "Unrelated access issue",
        detailKey: null,
        reportedBy: "safety.officer",
        locationKey: null,
        activityIds: ["act-1"],
        evidenceCount: 1,
        updatedAt: "2026-11-05T10:30:00Z",
      },
    ],
  };
  const html = renderActivityDetailsTabContent("issues", {
    locale: "en",
    activities: ACTIVITIES,
    selectedActivityId: "act-2",
    relationships: [],
    projectName: "project-1",
    dataDate: "—",
    calendarMode: "gregorian",
    state,
  });
  assert.match(html, /ISS-LINKED/);
  assert.match(html, /Foundation concrete test failed/);
  assert.doesNotMatch(html, /ISS-OTHER/);
  assert.doesNotMatch(html, /Unrelated access issue/);
});

test("Activity Summary displays supplied facts without deriving or fabricating schedule values", () => {
  const activities: WorkspaceActivityRow[] = [{
    ...ACTIVITIES[1],
    cells: {
      early_start: "2026-11-01",
      early_finish: "2026-11-05",
      duration: 4,
      percent_complete: 25,
      total_float: 0,
      free_float: 1,
      is_critical: false,
    },
    gantt: { start: "2026-11-01", finish: "2026-11-05", progressPercent: 25, critical: false },
  }];
  const html = renderActivityDetailsTabContent("summary", {
    locale: "en",
    activities,
    selectedActivityId: "act-2",
    relationships: [],
    projectName: "project-1",
    dataDate: "—",
    calendarMode: "gregorian",
  });
  assert.match(html, /2026-11-01/);
  assert.match(html, /2026-11-05/);
  assert.match(html, />4</);
  assert.match(html, />25</);
  assert.match(html, />0</);
  assert.match(html, />1</);
  assert.match(html, />No</);
});

test("Activity Resources tab does not mistake an unloaded projection for no assignments", () => {
  const html = renderActivityDetailsTabContent("resources", {
    locale: "en",
    activities: ACTIVITIES,
    selectedActivityId: "act-2",
    relationships: [],
    projectName: "project-1",
    dataDate: "—",
    calendarMode: "gregorian",
  });
  assert.match(html, /not included in the current Activity Details projection/i);
  assert.match(html, /does not mean the activity has no resources/i);
});

test("Activity Update History remains explicit when authoritative activity audit history is absent", () => {
  const html = renderActivityDetailsTabContent("update-history", {
    locale: "en",
    activities: ACTIVITIES,
    selectedActivityId: "act-2",
    relationships: [],
    projectName: "project-1",
    dataDate: "—",
    calendarMode: "gregorian",
  });
  assert.match(html, /Activity-specific audit history is not included/i);
  assert.doesNotMatch(html, /sample|example change/i);
});
test("Activity Resources tab renders only persisted assignments for the selected activity", () => {
  const html = renderActivityDetailsTabContent("resources", {
    locale: "en",
    activities: ACTIVITIES,
    selectedActivityId: "act-2",
    relationships: [],
    projectName: "project-1",
    dataDate: "—",
    calendarMode: "gregorian",
    resourceAssignments: {
      status: "loaded",
      errorCode: null,
      records: [
        { assignmentId: "ASG-2", activityId: "act-2", resourceId: "CRANE-01", roleId: "OPERATOR", units: "40", actualUnits: "12", remainingUnits: "28", plannedCost: "4000", actualCost: "1200", remainingCost: "2800", unit: "h", currency: "EUR", calendarId: "CAL-1", calendarVersion: "1", note: null, isDriving: true, unitsPerTime: "8", unitsPerTimePeriod: "day", hoursPerUnitsTimePeriod: "8" },
        { assignmentId: "ASG-1", activityId: "act-1", resourceId: "EXCAVATOR-01", roleId: null, units: "20", actualUnits: null, remainingUnits: null, plannedCost: null, actualCost: null, remainingCost: null, unit: "h", currency: null, calendarId: null, calendarVersion: null, note: null, isDriving: false, unitsPerTime: null, unitsPerTimePeriod: null, hoursPerUnitsTimePeriod: null },
      ],
    },
  });
  assert.match(html, /CRANE-01/);
  assert.match(html, /ASG-2|OPERATOR/);
  assert.match(html, /4000/);
  assert.doesNotMatch(html, /EXCAVATOR-01/);
});

test("Activity Expenses tab renders linked persisted expenses and excludes other activities", () => {
  const html = renderActivityDetailsTabContent("expenses", {
    locale: "en",
    activities: ACTIVITIES,
    selectedActivityId: "act-2",
    relationships: [],
    projectName: "project-1",
    dataDate: "—",
    calendarMode: "gregorian",
    activityExpenses: {
      status: "loaded",
      errorCode: null,
      records: [
        { expenseId: "EXP-2", name: "Concrete testing", category: "Quality", activityId: "act-2", wbsId: "wbs-1", expenseDate: "2026-11-05", plannedCost: "1500", actualCost: "650", remainingCost: "850", currency: "EUR", note: "Lab batch 04" },
        { expenseId: "EXP-1", name: "Excavator fuel", category: "Plant", activityId: "act-1", wbsId: "wbs-1", expenseDate: null, plannedCost: "500", actualCost: null, remainingCost: null, currency: "EUR", note: null },
      ],
    },
  });
  assert.match(html, /EXP-2/);
  assert.match(html, /Concrete testing/);
  assert.match(html, /Lab batch 04/);
  assert.doesNotMatch(html, /EXP-1/);
  assert.doesNotMatch(html, /Excavator fuel/);
});

test("Activity Details exposes retry states for authoritative related-data failures", () => {
  const resourceHtml = renderActivityDetailsTabContent("resources", {
    locale: "en", activities: ACTIVITIES, selectedActivityId: "act-2", relationships: [],
    projectName: "project-1", dataDate: "—", calendarMode: "gregorian",
    resourceAssignments: { status: "error", records: [], errorCode: "NETWORK_TIMEOUT" },
  });
  const expenseHtml = renderActivityDetailsTabContent("expenses", {
    locale: "en", activities: ACTIVITIES, selectedActivityId: "act-2", relationships: [],
    projectName: "project-1", dataDate: "—", calendarMode: "gregorian",
    activityExpenses: { status: "error", records: [], errorCode: "FORBIDDEN" },
  });
  assert.match(resourceHtml, /data-detail-retry="resources"/);
  assert.match(resourceHtml, /NETWORK_TIMEOUT/);
  assert.match(expenseHtml, /data-detail-retry="expenses"/);
  assert.match(expenseHtml, /FORBIDDEN/);
});
