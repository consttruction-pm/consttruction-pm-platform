import assert from "node:assert/strict";
import test from "node:test";

import type { WorkspaceActivityRow, WorkspaceWbsNode } from "./workspace-model.js";
import {
  buildWorkspaceDisplayRows,
  collapseAllWbsIds,
  collapseToWbsIds,
  collectWbsGroupIds,
  getCollapsedWbsIds,
  setCollapsedWbsIds,
  toggleCollapsedWbs,
  wbsNodeDepths,
} from "./workspace-wbs-display.js";

const nodes: WorkspaceWbsNode[] = [
  { id: "W-ROOT", parentKind: "project", parentWbsId: null, localCode: "1", name: "Project", sequenceNumber: 0, recordRevision: 1 },
  { id: "W-A", parentKind: "wbs", parentWbsId: "W-ROOT", localCode: "1.1", name: "Civil", sequenceNumber: 10, recordRevision: 1 },
  { id: "W-A1", parentKind: "wbs", parentWbsId: "W-A", localCode: "1.1.1", name: "Earthwork", sequenceNumber: 10, recordRevision: 1 },
  { id: "W-B", parentKind: "wbs", parentWbsId: "W-ROOT", localCode: "1.2", name: "Structure", sequenceNumber: 20, recordRevision: 1 },
];

const activities: WorkspaceActivityRow[] = [
  {
    id: "A-1", wbsId: "W-A1", code: "A1", name: "Excavate",
    cells: { duration: 2 },
    gantt: { start: "2026-09-01T00:00:00Z", finish: "2026-09-03T00:00:00Z", progressPercent: 50, critical: true },
  },
  {
    id: "A-2", wbsId: "W-A1", code: "A2", name: "Haul",
    cells: { duration: 2 },
    gantt: { start: "2026-09-03T00:00:00Z", finish: "2026-09-05T00:00:00Z", progressPercent: 100, critical: false },
  },
  {
    id: "B-1", wbsId: "W-B", code: "B1", name: "Rebar",
    cells: { duration: 2 },
    gantt: { start: "2026-09-02T00:00:00Z", finish: "2026-09-04T00:00:00Z", progressPercent: 0, critical: false },
  },
];

function rowKeys(collapsed: ReadonlySet<string> = new Set()): string[] {
  return buildWorkspaceDisplayRows(activities, nodes, "wbs", collapsed)
    .map((row) => row.kind === "wbs" ? `wbs:${row.wbsId}` : `act:${row.activity.id}`);
}

test("WBS display rows keep the hierarchy order and indent by real depth", () => {
  const rows = buildWorkspaceDisplayRows(activities, nodes, "wbs");
  assert.deepEqual(rows.map((row) => row.kind === "wbs" ? `wbs:${row.wbsId}` : `act:${row.activity.id}`), [
    "wbs:W-ROOT",
    "wbs:W-A",
    "wbs:W-A1",
    "act:A-1",
    "act:A-2",
    "wbs:W-B",
    "act:B-1",
  ]);
  const a1 = rows.find((row) => row.kind === "wbs" && row.wbsId === "W-A1");
  assert.equal(a1?.kind === "wbs" ? a1.depth : -1, 2);
  const activity = rows.find((row) => row.kind === "activity" && row.activity.id === "A-1");
  assert.equal(activity?.kind === "activity" ? activity.depth : -1, 3);
});

test("WBS summaries derive span, duration and weighted progress from persisted children", () => {
  const root = buildWorkspaceDisplayRows(activities, nodes, "wbs")[0];
  assert.equal(root.kind, "wbs");
  if (root.kind !== "wbs") return;
  assert.equal(root.summary.activityCount, 3);
  assert.equal(new Date(root.summary.startMs as number).toISOString().slice(0, 10), "2026-09-01");
  assert.equal(new Date(root.summary.finishMs as number).toISOString().slice(0, 10), "2026-09-05");
  assert.equal(root.summary.duration, 6);
  assert.equal(root.summary.progressPercent, 50);
});

test("collapsing one branch hides only that subtree and keeps child ids intact when reopened", () => {
  assert.deepEqual(rowKeys(new Set(["W-A"])), ["wbs:W-ROOT", "wbs:W-A", "wbs:W-B", "act:B-1"]);
  assert.deepEqual(rowKeys(new Set(["W-ROOT"])), ["wbs:W-ROOT"]);
  assert.deepEqual(rowKeys(new Set(["W-A1"])), ["wbs:W-ROOT", "wbs:W-A", "wbs:W-A1", "wbs:W-B", "act:B-1"]);
  assert.deepEqual(rowKeys(), ["wbs:W-ROOT", "wbs:W-A", "wbs:W-A1", "act:A-1", "act:A-2", "wbs:W-B", "act:B-1"]);
});

test("without WBS grouping the grid stays a flat activity list", () => {
  const rows = buildWorkspaceDisplayRows(activities, nodes, "none");
  assert.deepEqual(rows.map((row) => row.kind), ["activity", "activity", "activity"]);
  assert.deepEqual(rows.map((row) => row.kind === "activity" ? row.depth : -1), [0, 0, 0]);
});

test("collapse helpers keep root bands visible and preserve the target path", () => {
  const depths = wbsNodeDepths(nodes);
  assert.equal(depths.get("W-A1"), 2);
  assert.deepEqual([...collapseAllWbsIds(activities, nodes)].sort(), ["W-A", "W-A1", "W-B"]);
  assert.deepEqual([...collapseToWbsIds(activities, nodes, "W-A1")].sort(), ["W-B"]);
  assert.deepEqual([...collectWbsGroupIds(activities, nodes)].sort(), ["W-A", "W-A1", "W-B", "W-ROOT"]);
});

test("collapse preference is stored per project and toggles both ways", () => {
  setCollapsedWbsIds("project-collapse-test", []);
  assert.deepEqual([...getCollapsedWbsIds("project-collapse-test")], []);
  toggleCollapsedWbs("project-collapse-test", "W-A");
  assert.deepEqual([...getCollapsedWbsIds("project-collapse-test")], ["W-A"]);
  toggleCollapsedWbs("project-collapse-test", "W-A");
  assert.deepEqual([...getCollapsedWbsIds("project-collapse-test")], []);
  setCollapsedWbsIds("project-collapse-test", ["W-B", "W-A", "W-A"]);
  assert.deepEqual([...getCollapsedWbsIds("project-collapse-test")], ["W-A", "W-B"]);
  setCollapsedWbsIds("project-collapse-test", []);
});
