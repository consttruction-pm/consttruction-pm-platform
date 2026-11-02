import assert from "node:assert/strict";
import test from "node:test";

import { createWorkspaceState, type WorkspaceActivityRow } from "./workspace-model.js";
import { renderActivityDetailsPanel } from "./workspace-activity-details.js";

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
