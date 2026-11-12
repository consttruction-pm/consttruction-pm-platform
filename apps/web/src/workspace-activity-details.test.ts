import assert from "node:assert/strict";
import test from "node:test";

import { createWorkspaceState, type WorkspaceActivityRow } from "./workspace-model.js";
import {
  ACTIVITY_DETAILS_STORAGE_KEY,
  ACTIVITY_DETAILS_TABS,
  ACTIVITY_DETAILS_VISIBLE_TABS_STORAGE_KEY,
  parseActivityProgressHistory,
  readActivityDetailsVisibleTabs,
  renderActivityDetailsPanel,
} from "./workspace-activity-details.js";
import type { ActivityDetailsTabId } from "./workspace-activity-details.js";

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

test("activity details renders the sixteen required Version 26 tabs in order plus the CUBI calendar tab", () => {
  const expected: ActivityDetailsTabId[] = [
    "general", "status", "resources", "predecessors", "successors", "relationships",
    "codes", "notebook", "steps", "wps-docs", "expenses", "issues", "risks",
    "summary", "udfs", "update-history",
  ];
  assert.deepEqual(ACTIVITY_DETAILS_TABS.slice(0, 16).map((tab) => tab.id), expected);
  assert.equal(ACTIVITY_DETAILS_TABS[16]?.id, "calendar");
  const html = render("act-1");
  const positions = expected.map((id) => html.indexOf(`data-detail-tab="${id}"`));
  assert.ok(positions.every((position) => position >= 0), "every required tab is rendered");
  assert.deepEqual([...positions].sort((a, b) => a - b), positions, "tabs keep the required order");
  assert.ok(html.indexOf('data-detail-tab="calendar"') > positions[positions.length - 1]);
});

test("Customize Activity Details dialog lists available and display tabs with the documented buttons", () => {
  const html = render("act-1");
  assert.match(html, /data-details-customize-open/);
  assert.match(html, /data-details-customize-dialog/);
  assert.match(html, /data-customize-list="available"/);
  assert.match(html, /data-customize-list="display"/);
  assert.match(html, /data-customize-add/);
  assert.match(html, /data-customize-remove/);
  assert.match(html, /data-customize-up/);
  assert.match(html, /data-customize-down/);
  assert.match(html, /data-customize-default/);
  assert.match(html, /data-details-customize-apply/);
  assert.match(html, /data-details-customize-ok/);
  assert.match(html, /data-details-customize-close/);
  assert.equal((html.match(/data-customize-tab=/g) ?? []).length, ACTIVITY_DETAILS_TABS.length);
});

test("visible tabs drive both the tab strip and the order", () => {
  const html = renderActivityDetailsPanel({
    locale: "en", activities: ACTIVITIES, selectedActivityId: "act-1",
    relationships: [], projectName: "Shared Core", dataDate: "2026-10-07",
    calendarMode: "gregorian", visibleTabs: ["status", "general"],
  });
  assert.match(html, /data-detail-tab="status"/);
  assert.match(html, /data-detail-tab="general"/);
  assert.doesNotMatch(html, /data-detail-tab="risks"/);
  assert.ok(html.indexOf('data-detail-tab="status"') < html.indexOf('data-detail-tab="general"'));
  assert.match(html, /data-detail-panel="status"/);
});

test("stored tab display sets migrate earlier documents ids and reject unknown ids", () => {
  const store = new Map<string, string>([
    [ACTIVITY_DETAILS_VISIBLE_TABS_STORAGE_KEY, JSON.stringify(["general", "documents", "unknown", "general"])],
  ]);
  const storage = {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => { store.set(key, value); },
  } as unknown as Storage;
  assert.deepEqual(readActivityDetailsVisibleTabs(storage), ["general", "wps-docs"]);
  store.set(ACTIVITY_DETAILS_VISIBLE_TABS_STORAGE_KEY, "{not json");
  assert.equal(readActivityDetailsVisibleTabs(storage).length, ACTIVITY_DETAILS_TABS.length);
});

test("status At Complete is never replaced by the scheduled-duration grid fact", () => {
  // The active-tab reader falls back to general without storage; provide the
  // same storage contract a browser has so the Status tab renders.
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: { localStorage: { getItem: (key: string) => (key === ACTIVITY_DETAILS_STORAGE_KEY ? "status" : null) } },
  });
  try {
    const renderWith = (cells: Record<string, string | number>): string => renderActivityDetailsPanel({
      locale: "en",
      activities: [{ id: "act-1", wbsId: "wbs-1", code: "A100", name: "Kickoff", cells }],
      selectedActivityId: "act-1",
      relationships: [],
      projectName: "Shared Core",
      dataDate: "2026-10-07",
      calendarMode: "gregorian",
    });
    assert.match(
      renderWith({ at_complete_duration: 4, duration: 0 }),
      /At Complete<\/span><span class="cp-detail-value"[^>]*>4</,
    );
    assert.match(
      renderWith({ duration: 0, planned_duration: 1, remaining_duration: 0 }),
      /At Complete<\/span><span class="cp-detail-value is-empty"[^>]*>Not available</,
    );
  } finally {
    Reflect.deleteProperty(globalThis, "window");
  }
});

test("WPS & Docs reads real linked project documents", () => {
  const state = createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 });
  const withDocs = {
    ...state,
    activeMenu: "schedule" as const,
    documents: [{
      documentId: "DOC-1", title: "Method statement", resourceType: "submittal" as const,
      status: "approved" as const, revision: 4, contentHash: "hash-1",
      hasStorageRef: true, linkedEntityRefs: ["act-1"],
    }],
  };
  const html = renderActivityDetailsPanel({
    locale: "en", activities: ACTIVITIES, selectedActivityId: "act-1",
    relationships: [], projectName: "project-1", dataDate: "2026-10-07",
    calendarMode: "gregorian", state: withDocs, visibleTabs: ["wps-docs"],
  });
  assert.match(html, /Method statement/);
  assert.match(html, /DOC-1/);
  assert.match(html, /hash-1/);
});

test("Resources lists only the assignments stored for the selected activity", () => {
  const html = renderActivityDetailsPanel({
    locale: "en", activities: ACTIVITIES, selectedActivityId: "act-1",
    relationships: [], projectName: "project-1", dataDate: "2026-10-07",
    calendarMode: "gregorian", visibleTabs: ["resources"],
    data: {
      assignments: {
        status: "loaded",
        errorCode: null,
        records: [
          { assignmentId: "AS-1", activityId: "act-1", resourceId: "RES-1", roleId: "civil", units: "24", actualUnits: "8", remainingUnits: "16", plannedCost: "1200", actualCost: null, remainingCost: null, unit: "h", currency: "USD", calendarId: null, calendarVersion: null, note: null, isDriving: null, unitsPerTime: null, unitsPerTimePeriod: null, hoursPerUnitsTimePeriod: null },
          { assignmentId: "AS-2", activityId: "act-2", resourceId: "RES-2", roleId: null, units: "8", actualUnits: null, remainingUnits: "8", plannedCost: null, actualCost: null, remainingCost: null, unit: "h", currency: "USD", calendarId: null, calendarVersion: null, note: null, isDriving: null, unitsPerTime: null, unitsPerTimePeriod: null, hoursPerUnitsTimePeriod: null },
        ],
      },
    },
  });
  assert.match(html, /RES-1/);
  assert.match(html, /civil/);
  assert.match(html, /1200/);
  assert.doesNotMatch(html, /RES-2/);
  assert.match(html, /data-details-refresh="resources"/);
});

test("write editors appear only for writable sessions and capture every stored field", () => {
  const base = {
    locale: "en", activities: ACTIVITIES, selectedActivityId: "act-1",
    relationships: [], projectName: "project-1", dataDate: "2026-10-07",
    calendarMode: "gregorian" as const,
  };
  const readOnly = renderActivityDetailsPanel({ ...base, visibleTabs: ["resources"] });
  assert.doesNotMatch(readOnly, /data-details-form="resources"/);
  assert.match(readOnly, /Add Resource[\s\S]*disabled/);

  const resources = renderActivityDetailsPanel({ ...base, visibleTabs: ["resources"], canWrite: true });
  assert.match(resources, /data-details-form="resources"/);
  for (const name of ["resourceId", "roleId", "units", "plannedCost", "currency", "note"]) {
    assert.match(resources, new RegExp(`name="${name}"`));
  }
  assert.match(resources, /Add assignment/);

  const expenses = renderActivityDetailsPanel({ ...base, visibleTabs: ["expenses"], canWrite: true });
  assert.match(expenses, /data-details-form="expenses"/);
  assert.match(expenses, /name="category"/);
  assert.match(expenses, /<option value="material"/);

  const issues = renderActivityDetailsPanel({ ...base, visibleTabs: ["issues"], canWrite: true });
  assert.match(issues, /data-details-form="issues"/);
  for (const name of ["title", "issueType", "status", "priority", "owner", "dateIdentified"]) {
    assert.match(issues, new RegExp(`name="${name}"`));
  }
});

test("Issues are filtered by the stored activity reference and Update History renders revision events", () => {
  const base = {
    locale: "en", activities: ACTIVITIES, selectedActivityId: "act-1",
    relationships: [], projectName: "project-1", dataDate: "2026-10-07",
    calendarMode: "gregorian" as const,
    data: {
      issues: {
        status: "loaded" as const, errorCode: null,
        records: [
          { issueId: "IS-1", title: "Late concrete", activityId: "act-1", issueType: "schedule", priority: "high", status: "open", owner: "planner", updatedAt: "2026-10-08", description: "", responsibleManager: null, dateIdentified: "2026-10-08", dueDate: null, wbsId: null, documentRefs: [], resolutionNote: null, recordRevision: 1, createdAt: "2026-10-08" },
          { issueId: "IS-2", title: "Other activity", activityId: "act-2", issueType: "cost", priority: "low", status: "closed", owner: "planner", updatedAt: "2026-10-09", description: "", responsibleManager: null, dateIdentified: "2026-10-09", dueDate: null, wbsId: null, documentRefs: [], resolutionNote: null, recordRevision: 1, createdAt: "2026-10-09" },
        ],
      },
      history: {
        status: "loaded" as const, errorCode: null,
        records: [
          { eventId: "EV-1", activityId: "act-1", recordedAt: "2026-10-08T10:00:00Z", actorUserId: "user-1", fromRecordRevision: 2, toRecordRevision: 3, changes: [{ field: "percent_complete", before: "40", after: "55" }], outOfSequence: true },
        ],
      },
    },
  };
  const issues = renderActivityDetailsPanel({ ...base, visibleTabs: ["issues"] });
  assert.match(issues, /IS-1/);
  assert.doesNotMatch(issues, /IS-2/);

  const history = renderActivityDetailsPanel({ ...base, visibleTabs: ["update-history"] });
  assert.match(history, /R2 → R3/);
  assert.match(history, /percent_complete: 40 → 55/);
  assert.match(history, /Out of sequence/);
});

test("detail tabs distinguish a pending read from a loaded but empty collection", () => {
  const pending = renderActivityDetailsPanel({
    locale: "en", activities: ACTIVITIES, selectedActivityId: "act-1",
    relationships: [], projectName: "project-1", dataDate: "2026-10-07",
    calendarMode: "gregorian", visibleTabs: ["expenses"],
    data: { expenses: { status: "loading", records: [], errorCode: null } },
  });
  assert.match(pending, /Loading authoritative records/);
  assert.doesNotMatch(pending, /No expense records are stored/);

  const empty = renderActivityDetailsPanel({
    locale: "en", activities: ACTIVITIES, selectedActivityId: "act-1",
    relationships: [], projectName: "project-1", dataDate: "2026-10-07",
    calendarMode: "gregorian", visibleTabs: ["expenses"],
    data: { expenses: { status: "loaded", records: [], errorCode: null } },
  });
  assert.match(empty, /No expense records are stored for this activity/);

  const failed = renderActivityDetailsPanel({
    locale: "en", activities: ACTIVITIES, selectedActivityId: "act-1",
    relationships: [], projectName: "project-1", dataDate: "2026-10-07",
    calendarMode: "gregorian", visibleTabs: ["expenses"],
    data: { expenses: { status: "error", records: [], errorCode: "COST_READ_FAILED" } },
  });
  assert.match(failed, /COST_READ_FAILED/);
});

test("progress history parsing rejects malformed payloads instead of inventing events", () => {
  assert.throws(() => parseActivityProgressHistory({ events: "nope" }), /INVALID_ACTIVITY_PROGRESS_HISTORY/);
  assert.throws(() => parseActivityProgressHistory({ kind: "p6_activity_progress_history", events: [{ event_id: "EV-1" }] }), /INVALID_ACTIVITY_PROGRESS_HISTORY/);
  const parsed = parseActivityProgressHistory({
    kind: "p6_activity_progress_history",
    events: [{
      event_id: "EV-1", activity_id: "act-1", recorded_at: "2026-10-08T10:00:00Z",
      actor_user_id: "user-1", from_record_revision: 1, to_record_revision: 2,
      changes: [{ field: "status", before: "planned", after: "active" }],
      out_of_sequence: { is_out_of_sequence: false, findings: [] },
    }],
  });
  assert.equal(parsed[0]?.eventId, "EV-1");
  assert.equal(parsed[0]?.changes[0]?.field, "status");
  assert.equal(parsed[0]?.outOfSequence, false);
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
