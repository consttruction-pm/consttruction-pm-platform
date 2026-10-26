import assert from "node:assert/strict";
import test from "node:test";

import { filterAndSortActivities } from "./workspace-filter-sort.js";
import {
  createWorkspaceState,
  setActivityFilter,
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

test("WBS selection filters by exact persisted group and composes with text and sort", () => {
  const rows = activities();
  assert.deepEqual(
    filterAndSortActivities(rows, "", null, "2 Civil").map((row) => row.id),
    ["A-10", "A-100"],
  );
  assert.deepEqual(
    filterAndSortActivities(rows, "piling", null, "2 Civil").map((row) => row.id),
    ["A-100"],
  );
  assert.deepEqual(
    filterAndSortActivities(
      rows,
      "",
      { columnId: "activity.total_float", direction: "asc" },
      "2 Civil",
    ).map((row) => row.id),
    ["A-10", "A-100"],
  );
  assert.deepEqual(filterAndSortActivities(rows, "", null, "Missing"), []);
  assert.equal(filterAndSortActivities(rows, "", null, null), rows);
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
