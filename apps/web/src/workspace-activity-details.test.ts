import assert from "node:assert/strict";
import test from "node:test";

import { createWorkspaceState, type WorkspaceActivityRow } from "./workspace-model.js";
import {
  ACTIVITY_DETAILS_TABS,
  ACTIVITY_DETAILS_VISIBLE_TABS_STORAGE_KEY,
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

test("activity details renders the seventeen Version 26 tabs in documented order plus the CUBI calendar tab", () => {
  const expected: ActivityDetailsTabId[] = [
    "general", "status", "resources", "predecessors", "successors", "codes",
    "tasks", "discussion", "notebook", "steps", "feedback", "wps-docs",
    "expenses", "summary", "relationships", "risks", "udfs",
  ];
  assert.deepEqual(ACTIVITY_DETAILS_TABS.slice(0, 17).map((tab) => tab.id), expected);
  assert.equal(ACTIVITY_DETAILS_TABS[17]?.id, "calendar");
  const html = render("act-1");
  const positions = expected.map((id) => html.indexOf(`data-detail-tab="${id}"`));
  assert.ok(positions.every((position) => position >= 0), "every official tab is rendered");
  assert.deepEqual([...positions].sort((a, b) => a - b), positions, "tabs keep the v26 order");
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
