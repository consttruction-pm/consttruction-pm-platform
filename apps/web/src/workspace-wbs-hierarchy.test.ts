import assert from "node:assert/strict";
import test from "node:test";

import type { WorkspaceWbsNode } from "./workspace-model.js";
import {
  buildWbsHierarchy,
  wbsActivityCounts,
  wbsSubtreeIds,
} from "./workspace-wbs-hierarchy.js";

function node(
  id: string,
  parentWbsId: string | null,
  sequenceNumber: number,
  localCode = id,
): WorkspaceWbsNode {
  return {
    id,
    parentKind: parentWbsId ? "wbs" : "project",
    parentWbsId,
    localCode,
    name: `Name ${id}`,
    sequenceNumber,
    recordRevision: 1,
  };
}

test("hierarchy flattens depth-first in persisted sibling order", () => {
  const rows = buildWbsHierarchy([
    node("B", "A", 20),
    node("A", null, 10),
    node("C", "A", 10),
    node("D", "C", 5),
  ]);
  assert.deepEqual(rows.map((row) => row.node.id), ["A", "C", "D", "B"]);
  assert.deepEqual(rows.map((row) => row.depth), [1, 2, 3, 2]);
  assert.deepEqual(rows.map((row) => row.hasChildren), [true, true, false, false]);
});

test("siblings sort by sequence, then local code, then id", () => {
  const rows = buildWbsHierarchy([
    node("z", null, 0, "B"),
    node("y", null, 0, "A"),
    node("x", null, 0, "A"),
  ]);
  assert.deepEqual(rows.map((row) => row.node.id), ["x", "y", "z"]);
});

test("an orphan is promoted to the root and flagged, never dropped", () => {
  const rows = buildWbsHierarchy([node("orphan", "missing", 1), node("root", null, 2)]);
  assert.deepEqual(rows.map((row) => row.node.id), ["orphan", "root"]);
  assert.equal(rows[0].orphan, true);
  assert.equal(rows[1].orphan, false);
});

test("cycles cannot loop or duplicate rows", () => {
  const rows = buildWbsHierarchy([node("a", "b", 1), node("b", "a", 1)]);
  assert.equal(rows.length, 2);
  assert.deepEqual(new Set(rows.map((row) => row.node.id)), new Set(["a", "b"]));
});

test("duplicate node ids render once", () => {
  const rows = buildWbsHierarchy([node("a", null, 1), node("a", null, 2)]);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].node.sequenceNumber, 1);
});

test("activity counts ignore unknown WBS references and count repeats", () => {
  const counts = wbsActivityCounts([{ wbsId: "a" }, { wbsId: "a" }, { wbsId: "b" }]);
  assert.equal(counts.get("a"), 2);
  assert.equal(counts.get("b"), 1);
  assert.equal(counts.get("missing"), undefined);
});

test("subtree ids cover the node and every descendant only", () => {
  const nodes = [
    node("a", null, 1),
    node("b", "a", 1),
    node("c", "b", 1),
    node("d", "a", 2),
    node("e", null, 2),
  ];
  assert.deepEqual([...wbsSubtreeIds(nodes, "a")], ["a", "b", "c", "d"]);
  assert.deepEqual([...wbsSubtreeIds(nodes, "c")], ["c"]);
  assert.deepEqual([...wbsSubtreeIds(nodes, "missing")], []);
});
