import assert from "node:assert/strict";
import test from "node:test";

import { P6_LAYOUT_SCHEMA_VERSION, type LayoutDefinition } from "./p6-field-layout-foundation.js";
import {
  GROUP_SORT_METADATA_KEY,
  GROUP_SORT_UPDATED_KEY,
  groupSortMetadata,
  readGroupSortMetadata,
  withGroupSortMetadata,
} from "./workspace-layout-settings.js";

function layout(): LayoutDefinition {
  return {
    schema_version: P6_LAYOUT_SCHEMA_VERSION,
    scope: "project",
    view_id: "activity",
    revision: 3,
    columns: [],
    metadata: { layoutName: "Baseline" },
  };
}

test("a saved layout restores the group mode and the ordered sort plan", () => {
  const saved = withGroupSortMetadata(
    layout(),
    "none",
    [
      { columnId: "status", direction: "desc" },
      { columnId: "activity_name", direction: "asc" },
    ],
    Date.parse("2026-11-12T10:00:00Z"),
  );
  assert.equal(saved.scope, "project");
  assert.equal(saved.revision, 3);
  assert.equal(saved.metadata?.layoutName, "Baseline");
  assert.deepEqual(readGroupSortMetadata(saved.metadata), {
    groupBy: "none",
    sortLevels: [
      { columnId: "status", direction: "desc" },
      { columnId: "activity_name", direction: "asc" },
    ],
  });
  assert.equal(saved.metadata?.[GROUP_SORT_UPDATED_KEY], Date.parse("2026-11-12T10:00:00Z"));
});

test("a malformed or absent group/sort block is ignored instead of trusted", () => {
  assert.equal(readGroupSortMetadata(undefined), null);
  assert.equal(readGroupSortMetadata({}), null);
  assert.equal(readGroupSortMetadata({ [GROUP_SORT_METADATA_KEY]: "wbs" }), null);
  assert.equal(readGroupSortMetadata({ [GROUP_SORT_METADATA_KEY]: { groupBy: "status" } }), null);
  assert.deepEqual(
    readGroupSortMetadata({
      [GROUP_SORT_METADATA_KEY]: {
        groupBy: "wbs",
        sortLevels: [
          { columnId: "status", direction: "sideways" },
          { columnId: "", direction: "asc" },
          null,
          { columnId: "wbs", direction: "asc" },
          { columnId: "activity_name", direction: "desc" },
          { columnId: "start", direction: "asc" },
        ],
      },
    }),
    {
      groupBy: "wbs",
      sortLevels: [
        { columnId: "status", direction: "asc" },
        { columnId: "wbs", direction: "asc" },
        { columnId: "activity_name", direction: "desc" },
      ],
    },
  );
});

test("writing metadata caps the plan at three levels and keeps other keys", () => {
  const metadata = groupSortMetadata("wbs", [
    { columnId: "status", direction: "desc" },
    { columnId: "activity_name", direction: "asc" },
    { columnId: "start", direction: "desc" },
    { columnId: "finish", direction: "asc" },
  ], -5);
  assert.deepEqual(metadata[GROUP_SORT_METADATA_KEY], {
    groupBy: "wbs",
    sortLevels: [
      { columnId: "status", direction: "desc" },
      { columnId: "activity_name", direction: "asc" },
      { columnId: "start", direction: "desc" },
    ],
  });
  assert.equal(metadata[GROUP_SORT_UPDATED_KEY], 0);
  const merged = withGroupSortMetadata(layout(), "wbs", [], 10);
  assert.equal(merged.metadata?.layoutName, "Baseline");
  assert.deepEqual(readGroupSortMetadata(merged.metadata), { groupBy: "wbs", sortLevels: [] });
});
