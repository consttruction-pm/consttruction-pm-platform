import assert from "node:assert/strict";
import test from "node:test";

import { planActivityReplacements } from "./workspace-activity-bulk.js";

const ACTIVITIES = [
  { id: "A1", name: "Design external interfaces" },
  { id: "A2", name: "design internal interfaces" },
  { id: "A3", name: "Procurement" },
];

test("replace matches every occurrence and keeps untouched rows out of the plan", () => {
  const edits = planActivityReplacements(ACTIVITIES, {
    find: "interfaces", replace: "surfaces", matchCase: false, onlySelected: false,
  });
  assert.deepEqual(edits.map((edit) => [edit.id, edit.next]), [
    ["A1", "Design external surfaces"],
    ["A2", "design internal surfaces"],
  ]);
});

test("match case and selection scope narrow the plan", () => {
  assert.deepEqual(
    planActivityReplacements(ACTIVITIES, { find: "Design", replace: "Model", matchCase: true, onlySelected: false })
      .map((edit) => edit.id),
    ["A1"],
  );
  assert.deepEqual(
    planActivityReplacements(ACTIVITIES, {
      find: "design", replace: "model", matchCase: false, onlySelected: true, selectedIds: ["A2"],
    }).map((edit) => edit.id),
    ["A2"],
  );
});

test("an empty find never plans a whole-name replacement", () => {
  assert.deepEqual(planActivityReplacements(ACTIVITIES, {
    find: "", replace: "X", matchCase: false, onlySelected: false,
  }), []);
  assert.deepEqual(planActivityReplacements(ACTIVITIES, {
    find: "Missing", replace: "X", matchCase: false, onlySelected: false,
  }), []);
});
