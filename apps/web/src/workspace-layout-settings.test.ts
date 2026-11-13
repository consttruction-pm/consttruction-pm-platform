import assert from "node:assert/strict";
import test from "node:test";

import { P6_LAYOUT_SCHEMA_VERSION, type LayoutDefinition } from "./p6-field-layout-foundation.js";
import {
  GROUP_SORT_METADATA_KEY,
  GROUP_SORT_UPDATED_KEY,
  MAX_SAVED_COLLAPSED_WBS,
  WBS_COLLAPSE_METADATA_KEY,
  collapsedWbsMetadata,
  groupSortMetadata,
  readCollapsedWbsMetadata,
  readGroupSortMetadata,
  withCollapsedWbsMetadata,
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
    groupLevels: [],
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
      groupLevels: [{ fieldId: "wbs", direction: "asc" }],
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
    groupLevels: [{ fieldId: "wbs", direction: "asc" }],
    sortLevels: [
      { columnId: "status", direction: "desc" },
      { columnId: "activity_name", direction: "asc" },
      { columnId: "start", direction: "desc" },
    ],
  });
  assert.equal(metadata[GROUP_SORT_UPDATED_KEY], 0);
  const merged = withGroupSortMetadata(layout(), "wbs", [], 10);
  assert.equal(merged.metadata?.layoutName, "Baseline");
  assert.deepEqual(readGroupSortMetadata(merged.metadata), { groupBy: "wbs", groupLevels: [{ fieldId: "wbs", direction: "asc" }], sortLevels: [] });
});

test("a saved layout restores the collapsed WBS branches it was saved with", () => {
  const saved = withCollapsedWbsMetadata(layout(), ["WBS-RPS-CIVIL", " WBS-RPS-PROF ", "WBS-RPS-CIVIL", ""]);
  assert.equal(saved.scope, "project");
  assert.equal(saved.revision, 3);
  assert.equal(saved.metadata?.layoutName, "Baseline");
  assert.deepEqual(saved.metadata?.[WBS_COLLAPSE_METADATA_KEY], ["WBS-RPS-CIVIL", "WBS-RPS-PROF"]);
  const restored = readCollapsedWbsMetadata(saved.metadata);
  assert.deepEqual([...(restored ?? [])].sort(), ["WBS-RPS-CIVIL", "WBS-RPS-PROF"]);
});

test("an absent collapse block leaves the view alone but an empty one expands everything", () => {
  assert.equal(readCollapsedWbsMetadata(undefined), null);
  assert.equal(readCollapsedWbsMetadata({}), null);
  assert.equal(readCollapsedWbsMetadata({ [WBS_COLLAPSE_METADATA_KEY]: "WBS-RPS-CIVIL" }), null);
  assert.equal(readCollapsedWbsMetadata({ [WBS_COLLAPSE_METADATA_KEY]: { id: "x" } }), null);
  const empty = readCollapsedWbsMetadata({ [WBS_COLLAPSE_METADATA_KEY]: [] });
  assert.equal(empty?.size, 0);
  const filtered = readCollapsedWbsMetadata({
    [WBS_COLLAPSE_METADATA_KEY]: ["WBS-A", 7, null, " ", "WBS-B", "WBS-A"],
  });
  assert.deepEqual([...(filtered ?? [])].sort(), ["WBS-A", "WBS-B"]);
});

test("collapse metadata is capped and never replaces the other layout keys", () => {
  const ids = Array.from({ length: MAX_SAVED_COLLAPSED_WBS + 20 }, (_, index) => `WBS-${index}`);
  const metadata = collapsedWbsMetadata(ids);
  const stored = metadata[WBS_COLLAPSE_METADATA_KEY] as string[];
  assert.equal(stored.length, MAX_SAVED_COLLAPSED_WBS);
  const merged = withCollapsedWbsMetadata(layout(), ids.slice(0, 2));
  assert.equal(merged.metadata?.layoutName, "Baseline");
  const both = withCollapsedWbsMetadata(
    withGroupSortMetadata(layout(), "wbs", [], 10),
    ["WBS-RPS-CIVIL"],
  );
  assert.deepEqual(readGroupSortMetadata(both.metadata), { groupBy: "wbs", groupLevels: [{ fieldId: "wbs", direction: "asc" }], sortLevels: [] });
  assert.deepEqual([...(readCollapsedWbsMetadata(both.metadata) ?? [])], ["WBS-RPS-CIVIL"]);
});

test("a multi-level group plan round-trips and unknown fields are dropped", () => {
  const metadata = groupSortMetadata("wbs", [], 10, [
    { fieldId: "wbs", direction: "asc" },
    { fieldId: "activity_status", direction: "desc" },
    { fieldId: "activity_status", direction: "asc" },
    { fieldId: "not_a_field", direction: "asc" },
  ]);
  const saved = readGroupSortMetadata(metadata);
  assert.deepEqual(saved?.groupLevels, [
    { fieldId: "wbs", direction: "asc" },
    { fieldId: "activity_status", direction: "desc" },
  ]);
  const legacy = readGroupSortMetadata({
    [GROUP_SORT_METADATA_KEY]: { groupBy: "wbs", sortLevels: [{ columnId: "status", direction: "asc" }] },
  });
  assert.deepEqual(legacy?.groupLevels, [{ fieldId: "wbs", direction: "asc" }]);
  const flat = readGroupSortMetadata({
    [GROUP_SORT_METADATA_KEY]: { groupBy: "none", groupLevels: [], sortLevels: [] },
  });
  assert.deepEqual(flat?.groupLevels, []);
  const invalidOnly = readGroupSortMetadata({
    [GROUP_SORT_METADATA_KEY]: { groupBy: "none", groupLevels: [{ fieldId: "bogus" }], sortLevels: [] },
  });
  assert.deepEqual(invalidOnly?.groupLevels, []);
});
