import assert from "node:assert/strict";
import test from "node:test";

import {
  ACTIVITY_COPY_PREFERENCE_KEY,
  DEFAULT_ACTIVITY_COPY_OPTIONS,
  loadActivityCopyPreference,
  nextCopyId,
  planCopiedRelationships,
  saveActivityCopyPreference,
} from "./workspace-activity-copy.js";

test("copy options persist and restore exactly the operator's choices", () => {
  const storage = new Map<string, string>();
  const adapter = {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => { storage.set(key, value); },
  };
  saveActivityCopyPreference(adapter, {
    ...DEFAULT_ACTIVITY_COPY_OPTIONS,
    relationships: false,
    expenses: false,
    onlyBetweenCopied: true,
  }, true);
  assert.ok(storage.has(ACTIVITY_COPY_PREFERENCE_KEY));
  const restored = loadActivityCopyPreference(adapter);
  assert.equal(restored?.skipDialog, true);
  assert.equal(restored?.options.relationships, false);
  assert.equal(restored?.options.expenses, false);
  // A stored sub-option never survives without its parent checkbox.
  assert.equal(restored?.options.onlyBetweenCopied, true);
});

test("load ignores malformed or partial preferences", () => {
  const storage = new Map<string, string>([[ACTIVITY_COPY_PREFERENCE_KEY, "{not-json"]]);
  const adapter = {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => { storage.set(key, value); },
  };
  assert.equal(loadActivityCopyPreference(adapter), null);
});

const RELATIONSHIPS = [
  { id: "R1", predecessorId: "A", successorId: "B", type: "FS", lagValue: "0", lagUnit: "working-day" },
  { id: "R2", predecessorId: "B", successorId: "C", type: "SS", lagValue: "2", lagUnit: "working-day" },
  { id: "R3", predecessorId: "X", successorId: "A", type: "FF", lagValue: "0", lagUnit: "working-day" },
];

test("copied relationships follow the new IDs and keep links to uncopied activities", () => {
  const mapped = new Map([["A", "A-C1"], ["B", "B-C1"]]);
  const planned = planCopiedRelationships(RELATIONSHIPS, ["A", "B"], mapped, false);
  assert.deepEqual(planned.map((item) => [item.predecessorId, item.successorId, item.type]), [
    ["A-C1", "B-C1", "FS"],
    ["B-C1", "C", "SS"],
    ["X", "A-C1", "FF"],
  ]);
});

test("only-between-copied drops links to activities outside the copied set", () => {
  const mapped = new Map([["A", "A-C1"], ["B", "B-C1"]]);
  const planned = planCopiedRelationships(RELATIONSHIPS, ["A", "B"], mapped, true);
  assert.deepEqual(planned.map((item) => [item.predecessorId, item.successorId]), [["A-C1", "B-C1"]]);
});

test("nextCopyId never reuses an existing child identity", () => {
  assert.equal(nextCopyId("EXP-1", new Set()), "EXP-1-C1");
  assert.equal(nextCopyId("EXP-1", new Set(["EXP-1-C1", "EXP-1-C2"]), "-C"), "EXP-1-C3");
});
