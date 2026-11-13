import assert from "node:assert/strict";
import test from "node:test";

import type { WorkspaceActivityRow } from "./workspace-model.js";
import {
  EMPTY_GROUP_KEY,
  WORKSPACE_GROUP_FIELDS,
  compareGroupBands,
  compareGroupValues,
  groupFieldLabel,
  groupFieldValue,
  groupValueKey,
  groupValueLabel,
  isWorkspaceGroupFieldId,
  naturalCompare,
  normalizeGroupLevels,
} from "./workspace-grouping.js";

const activity: WorkspaceActivityRow = {
  id: "A-1",
  wbsId: "W-1",
  code: "01",
  name: "Foundation",
  cells: { "activity.status": "In Progress", "activity.type": "Task Dependent", "activity.total_float": 4 },
  gantt: { start: "2026-09-01T00:00:00Z", finish: "2026-09-03T00:00:00Z", progressPercent: 40, critical: true },
};

test("the group catalog offers only fields this runtime can read", () => {
  assert.deepEqual(WORKSPACE_GROUP_FIELDS.map((field) => field.id), [
    "wbs", "activity_status", "activity_type", "is_critical", "activity_code", "total_float",
  ]);
  assert.equal(isWorkspaceGroupFieldId("activity_status"), true);
  assert.equal(isWorkspaceGroupFieldId("activity_status; DROP TABLE"), false);
  assert.equal(groupFieldLabel("activity_status", "fa"), "وضعیت فعالیت");
  assert.equal(groupFieldLabel("activity_status", "en"), "Activity Status");
});

test("grouped values are read from the persisted row without transforming them", () => {
  assert.equal(groupFieldValue(activity, "wbs"), "W-1");
  assert.equal(groupFieldValue(activity, "activity_status"), "In Progress");
  assert.equal(groupFieldValue(activity, "activity_type"), "Task Dependent");
  assert.equal(groupFieldValue(activity, "is_critical"), true);
  assert.equal(groupFieldValue(activity, "activity_code"), "01");
  assert.equal(groupFieldValue(activity, "total_float"), 4);
  assert.equal(groupFieldValue({ id: "A-2", wbsId: "", code: "", name: "" }, "activity_status"), null);
});

test("group keys are typed, attribute-safe and distinguish text from numbers", () => {
  assert.equal(groupValueKey("1"), "s:1");
  assert.equal(groupValueKey(1), "n:1");
  assert.equal(groupValueKey(true), "b:true");
  assert.equal(groupValueKey(false), "b:false");
  assert.equal(groupValueKey(null), EMPTY_GROUP_KEY);
  assert.equal(groupValueKey("  "), EMPTY_GROUP_KEY);
  assert.ok(!EMPTY_GROUP_KEY.includes("\u0000"));
});

test("band labels localize only the values this runtime owns", () => {
  assert.equal(groupValueLabel("activity_status", "In Progress", "en"), "In Progress");
  assert.equal(groupValueLabel("is_critical", true, "en"), "Critical");
  assert.equal(groupValueLabel("is_critical", false, "en"), "Non-critical");
  assert.equal(groupValueLabel("is_critical", true, "fa-IR"), "بحرانی");
  assert.equal(groupValueLabel("activity_status", null, "en"), "No value");
  assert.equal(groupValueLabel("activity_status", null, "fa"), "بدون مقدار");
});

test("sibling bands sort naturally and keep No value last in both directions", () => {
  assert.deepEqual(
    ["Band 10", "Band 2", "Band 1"].sort(compareGroupValues),
    ["Band 1", "Band 2", "Band 10"],
  );
  assert.equal(compareGroupValues(2, 10), -1);
  assert.equal(compareGroupBands("Completed", "In Progress", "asc"), -1);
  assert.equal(compareGroupBands("Completed", "In Progress", "desc"), 1);
  assert.equal(compareGroupBands(null, "Completed", "asc"), 1);
  assert.equal(compareGroupBands(null, "Completed", "desc"), 1);
  assert.equal(compareGroupBands(null, null, "desc"), 0);
  assert.equal(naturalCompare("A-2", "A-10"), -1);
});

test("group plans keep at most three known unique fields", () => {
  assert.deepEqual(normalizeGroupLevels([
    { fieldId: "wbs", direction: "asc" },
    { fieldId: "activity_status", direction: "desc" },
    { fieldId: "activity_status", direction: "asc" },
    { fieldId: "activity_type", direction: "asc" },
    { fieldId: "total_float", direction: "asc" },
    { fieldId: " ", direction: "asc" },
    { fieldId: "unknown", direction: "asc" },
  ]), [
    { fieldId: "wbs", direction: "asc" },
    { fieldId: "activity_status", direction: "desc" },
    { fieldId: "activity_type", direction: "asc" },
  ]);
  assert.deepEqual(normalizeGroupLevels([]), []);
});
