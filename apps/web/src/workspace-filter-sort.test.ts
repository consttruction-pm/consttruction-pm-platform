import assert from "node:assert/strict";
import test from "node:test";

import { filterAndSortActivities } from "./workspace-filter-sort.js";
import {
  createWorkspaceState,
  setActivityFilter,
  setActivityGroupBy,
  setActivitySort,
  setActivitySortLevels,
  toggleActivitySortDirection,
  withActivities,
} from "./workspace-model.js";

const context = { tenant_id: "tenant-1", project_id: "project-1", revision: 4 };

function activities() {
  return [
    {
      id: "A-10", wbsId: "2 Civil", code: "A-10", name: "Earthworks",
      cells: { "activity.total_float": 12, "activity.status": "In Progress" },
    },
    {
      id: "A-2", wbsId: "1 Project management", code: "A-2", name: "Kickoff",
      cells: { "activity.total_float": 0, "activity.status": "Completed" },
    },
    {
      id: "A-100", wbsId: "2 Civil", code: "A-100", name: "Piling",
      cells: { "activity.total_float": null, "activity.status": "Not Started" },
    },
  ];
}

test("activity filter matches ID, WBS, status and multiple tokens", () => {
  const rows = activities();
  assert.deepEqual(
    filterAndSortActivities(rows, "civil", null).map((row) => row.id),
    ["A-10", "A-100"],
  );
  assert.deepEqual(
    filterAndSortActivities(rows, "  A-100  ", null).map((row) => row.id),
    ["A-100"],
  );
  assert.deepEqual(
    filterAndSortActivities(rows, "civil not started", null).map((row) => row.id),
    ["A-100"],
  );
  assert.equal(filterAndSortActivities(rows, "", null), rows);
});

test("activity page defaults Group and Sort to WBS and keeps each WBS block together", () => {
  const state = createWorkspaceState(context);
  assert.equal(state.activityGroupBy, "wbs");
  assert.deepEqual(state.activitySort, { columnId: "wbs", direction: "asc" });
  assert.deepEqual(state.activitySortLevels, [{ columnId: "wbs", direction: "asc" }]);

  const wbsNodes = [
    { id: "1 Project management", parentKind: "project" as const, parentWbsId: null, localCode: "1", name: "Project management", sequenceNumber: 0, recordRevision: 1 },
    { id: "2 Civil", parentKind: "project" as const, parentWbsId: null, localCode: "2", name: "Civil", sequenceNumber: 1, recordRevision: 1 },
  ];
  const rows = activities();
  const grouped = filterAndSortActivities(rows, "", state.activitySort, state.activityGroupBy, wbsNodes);
  assert.deepEqual(grouped.map((row) => row.id), ["A-2", "A-10", "A-100"]);

  const groupedAndSorted = filterAndSortActivities(
    rows, "", { columnId: "activity_name", direction: "desc" }, "wbs", wbsNodes,
  );
  assert.deepEqual(groupedAndSorted.map((row) => row.id), ["A-2", "A-100", "A-10"]);

  const ungrouped = setActivityGroupBy(state, "none");
  assert.equal(ungrouped.activityGroupBy, "none");
  assert.throws(() => setActivityGroupBy(state, "unknown" as never), /INVALID_ACTIVITY_GROUP_BY/);
});

test("activity sort is numeric when possible, pushes blanks last and is stable", () => {
  const rows = activities();
  assert.deepEqual(
    filterAndSortActivities(rows, "", { columnId: "activity.total_float", direction: "asc" })
      .map((row) => row.id),
    ["A-2", "A-10", "A-100"],
  );
  assert.deepEqual(
    filterAndSortActivities(rows, "", { columnId: "activity.total_float", direction: "desc" })
      .map((row) => row.id),
    ["A-10", "A-2", "A-100"],
  );
  assert.deepEqual(
    filterAndSortActivities(rows, "", { columnId: "activity_id", direction: "asc" })
      .map((row) => row.id),
    ["A-2", "A-10", "A-100"],
  );
  assert.deepEqual(rows.map((row) => row.id), ["A-10", "A-2", "A-100"]);
});

test("activity filter and sort state is immutable and validated", () => {
  const state = withActivities(createWorkspaceState(context), activities());
  const filtered = setActivityFilter(state, "civil");
  assert.notEqual(filtered, state);
  assert.equal(filtered.activityFilter, "civil");
  assert.equal(setActivityFilter(filtered, "civil"), filtered);

  const sorted = setActivitySort(filtered, "activity_id", "desc");
  assert.deepEqual(sorted.activitySort, { columnId: "activity_id", direction: "desc" });
  assert.deepEqual(sorted.activitySortLevels, [{ columnId: "activity_id", direction: "desc" }]);
  assert.notEqual(sorted, filtered);
  assert.equal(toggleActivitySortDirection(sorted).activitySort?.direction, "asc");
  const cleared = setActivitySort(sorted, null);
  assert.equal(cleared.activitySort, null);
  assert.deepEqual(cleared.activitySortLevels, []);
  assert.equal(setActivitySort(cleared, null), cleared);
  assert.throws(() => setActivitySort(state, "missing.column"), /SORT_COLUMN_NOT_FOUND/);

  const limited = setActivityFilter(state, "x".repeat(500));
  assert.equal(limited.activityFilter.length, 200);
});

test("multi-level sort applies each field in order and keeps WBS blocks intact", () => {
  const rows = [
    { id: "A-10", wbsId: "2 Civil", code: "A-10", name: "Earthworks", cells: { "activity.status": "In Progress", "activity.total_float": 12 } },
    { id: "A-11", wbsId: "2 Civil", code: "A-11", name: "Piling", cells: { "activity.status": "In Progress", "activity.total_float": 3 } },
    { id: "A-12", wbsId: "2 Civil", code: "A-12", name: "Foundations", cells: { "activity.status": "In Progress", "activity.total_float": 20 } },
    { id: "A-100", wbsId: "2 Civil", code: "A-100", name: "Steel", cells: { "activity.status": "Not Started", "activity.total_float": 0 } },
    { id: "A-2", wbsId: "1 Project management", code: "A-2", name: "Kickoff", cells: { "activity.status": "Completed", "activity.total_float": 0 } },
  ];
  const levels = [
    { columnId: "activity.status", direction: "desc" as const },
    { columnId: "activity.total_float", direction: "desc" as const },
  ];
  assert.deepEqual(
    filterAndSortActivities(rows, "", null, "none", [], levels).map((row) => row.id),
    ["A-100", "A-12", "A-10", "A-11", "A-2"],
  );

  const wbsNodes = [
    { id: "1 Project management", parentKind: "project" as const, parentWbsId: null, localCode: "1", name: "Project management", sequenceNumber: 0, recordRevision: 1 },
    { id: "2 Civil", parentKind: "project" as const, parentWbsId: null, localCode: "2", name: "Civil", sequenceNumber: 1, recordRevision: 1 },
  ];
  const grouped = filterAndSortActivities(
    rows, "", null, "wbs", wbsNodes,
    [{ columnId: "wbs", direction: "asc" }, ...levels],
  );
  assert.deepEqual(grouped.map((row) => row.id), ["A-2", "A-100", "A-12", "A-10", "A-11"]);
});

test("the sort plan keeps the first level as primary and deduplicates fields", () => {
  const state = withActivities(createWorkspaceState(context), activities());
  const next = setActivitySortLevels(state, [
    { columnId: "activity_name", direction: "desc" },
    { columnId: "progress", direction: "asc" },
    { columnId: "activity_name", direction: "asc" },
    { columnId: "missing.column", direction: "asc" },
  ]);
  assert.deepEqual(next.activitySortLevels, [
    { columnId: "activity_name", direction: "desc" },
    { columnId: "progress", direction: "asc" },
  ]);
  assert.deepEqual(next.activitySort, { columnId: "activity_name", direction: "desc" });
  assert.equal(setActivitySortLevels(next, next.activitySortLevels), next);

  const toggled = toggleActivitySortDirection(next);
  assert.deepEqual(toggled.activitySortLevels, [
    { columnId: "activity_name", direction: "asc" },
    { columnId: "progress", direction: "asc" },
  ]);
  const quick = setActivitySort(toggled, "activity_id", "asc");
  assert.deepEqual(quick.activitySortLevels, [{ columnId: "activity_id", direction: "asc" }]);
});

test("a group plan removes its own fields from the in-band sort plan", () => {
  const rows = [
    { id: "A-10", wbsId: "2 Civil", code: "A-10", name: "Earthworks", cells: { "activity.status": "In Progress", "activity.total_float": 12 } },
    { id: "A-11", wbsId: "2 Civil", code: "A-11", name: "Piling", cells: { "activity.status": "In Progress", "activity.total_float": 3 } },
    { id: "A-2", wbsId: "1 Project management", code: "A-2", name: "Kickoff", cells: { "activity.status": "Completed", "activity.total_float": 0 } },
  ];
  const wbsNodes = [
    { id: "1 Project management", parentKind: "project" as const, parentWbsId: null, localCode: "1", name: "Project management", sequenceNumber: 0, recordRevision: 1 },
    { id: "2 Civil", parentKind: "project" as const, parentWbsId: null, localCode: "2", name: "Civil", sequenceNumber: 1, recordRevision: 1 },
  ];
  // Grouping by status owns the status order, so the remaining plan sorts by
  // float inside each band instead of repeating the grouped field.
  const sorted = filterAndSortActivities(
    rows, "", null, "none", wbsNodes,
    [{ columnId: "activity.status", direction: "asc" }, { columnId: "activity.total_float", direction: "desc" }],
    [{ fieldId: "activity_status", direction: "asc" }],
  );
  assert.deepEqual(sorted.map((row) => row.id), ["A-10", "A-11", "A-2"]);

  const onlyGrouped = filterAndSortActivities(
    rows, "", null, "none", wbsNodes,
    [{ columnId: "activity.status", direction: "asc" }],
    [{ fieldId: "activity_status", direction: "asc" }],
  );
  // Every requested sort field is grouped, so the persisted order is kept.
  assert.deepEqual(onlyGrouped.map((row) => row.id), ["A-10", "A-11", "A-2"]);
});
