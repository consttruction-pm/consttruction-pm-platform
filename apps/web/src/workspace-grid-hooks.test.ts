import test from "node:test";
import assert from "node:assert/strict";
import { createEmptyGridQuery, createReportPrintSelection, normalizeGridQuery } from "./workspace-grid-hooks.js";
import { createWorkspaceState, withActivities } from "./workspace-model.js";

test("grid query drops fields outside the authoritative workspace catalog", () => {
  const state = createWorkspaceState({ tenant_id: "t1", project_id: "p1", revision: 1 });
  const query = normalizeGridQuery(state, {
    sort: [{ fieldId: "activity_name", direction: "asc" }, { fieldId: "removed", direction: "desc" }],
    group: [{ fieldId: "activity_id" }],
    filters: [{ fieldId: "removed", operator: "equals", value: "x" }],
  });
  assert.deepEqual(query.sort.map((x) => x.fieldId), ["activity_name"]);
  assert.deepEqual(query.group.map((x) => x.fieldId), ["activity_id"]);
  assert.equal(query.filters.length, 0);
  assert.deepEqual(createEmptyGridQuery().filters, []);
});

test("report/print selection preserves selected columns and activities", () => {
  let state = createWorkspaceState({ tenant_id: "t1", project_id: "p1", revision: 1 });
  state = withActivities(state, [
    { id: "a1", wbsId: "w1", code: "A1", name: "One" },
    { id: "a2", wbsId: "w1", code: "A2", name: "Two" },
  ]);
  const selection = createReportPrintSelection(state, ["activity_id", "duration"], ["a2"], false);
  assert.deepEqual(selection.columns.map((x) => x.id), ["activity_id", "duration"]);
  assert.deepEqual(selection.activityIds, ["a2"]);
  assert.equal(selection.includeGantt, false);
});
