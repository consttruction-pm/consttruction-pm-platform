import assert from "node:assert/strict";
import test from "node:test";

import type { WorkspaceActivityRow } from "./workspace-model.js";
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
