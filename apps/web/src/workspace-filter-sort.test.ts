import assert from "node:assert/strict";
import test from "node:test";

import { filterAndSortActivities } from "./workspace-filter-sort.js";
import {
  createWorkspaceState,
  setActivityFilter,
  setActivityGroupBy,
  setActivitySort,
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
  assert.notEqual(sorted, filtered);
  assert.equal(toggleActivitySortDirection(sorted).activitySort?.direction, "asc");
  const cleared = setActivitySort(sorted, null);
  assert.equal(cleared.activitySort, null);
  assert.equal(setActivitySort(cleared, null), cleared);
  assert.throws(() => setActivitySort(state, "missing.column"), /SORT_COLUMN_NOT_FOUND/);

  const limited = setActivityFilter(state, "x".repeat(500));
  assert.equal(limited.activityFilter.length, 200);
});
