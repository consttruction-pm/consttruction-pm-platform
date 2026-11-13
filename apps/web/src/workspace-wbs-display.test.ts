import assert from "node:assert/strict";
import test from "node:test";

import type { WorkspaceActivityRow, WorkspaceWbsNode } from "./workspace-model.js";
import {
  buildWbsTreeGuides,
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

function rowKey(row: ReturnType<typeof buildWorkspaceDisplayRows>[number]): string {
  if (row.kind === "wbs") return `wbs:${row.bandKey}`;
  if (row.kind === "fieldGroup") return `band:${row.bandKey}`;
  return `act:${row.activity.id}`;
}

function rowKeys(collapsed: ReadonlySet<string> = new Set()): string[] {
  return buildWorkspaceDisplayRows(activities, nodes, "wbs", collapsed).map(rowKey);
}

test("WBS display rows keep the hierarchy order and indent by real depth", () => {
  const rows = buildWorkspaceDisplayRows(activities, nodes, "wbs");
  assert.deepEqual(rows.map(rowKey), [
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

test("tree guides draw one gutter per visible ancestor and stop at the last sibling", () => {
  const rows = buildWorkspaceDisplayRows(activities, nodes, "wbs");
  const guides = buildWbsTreeGuides(rows);
  const guideFor = (key: string) => {
    const index = rows.findIndex((row) => rowKey(row) === key);
    assert.notEqual(index, -1, `missing display row ${key}`);
    return guides[index];
  };

  // A first-level node is reached by its own elbow only; it never draws a
  // rail for the project band above it.
  assert.deepEqual(guideFor("wbs:W-A").rails, []);
  assert.equal(guideFor("wbs:W-A").lastChild, false);
  // W-A still has the W-B sibling below, so its children keep the left spine.
  assert.deepEqual(guideFor("wbs:W-A1").rails, [true]);
  // W-A1 is the last child of W-A, so its elbow closes the branch.
  assert.equal(guideFor("wbs:W-A1").lastChild, true);
  // A third-level row keeps the W-A spine and leaves the closed W-A1 column
  // empty before drawing its own elbow.
  assert.deepEqual(guideFor("act:A-1").rails, [true, false]);
  assert.equal(guideFor("act:A-1").lastChild, false);
  assert.equal(guideFor("act:A-2").lastChild, true);
  // W-B is the last sibling, so its descendant has no ancestor rail at all.
  assert.deepEqual(guideFor("act:B-1").rails, [false]);
  assert.equal(guideFor("act:B-1").lastChild, true);
});

test("collapsing a branch rebuilds guides for the reduced visible depth", () => {
  const rows = buildWorkspaceDisplayRows(activities, nodes, "wbs", new Set(["W-A"]));
  const guides = buildWbsTreeGuides(rows);
  const wb = rows.findIndex((row) => row.kind === "wbs" && row.wbsId === "W-B");
  assert.ok(wb >= 0);
  assert.deepEqual(guides[wb].rails, []);
  const b1 = rows.findIndex((row) => row.kind === "activity" && row.activity.id === "B-1");
  assert.ok(b1 >= 0);
  assert.equal(guides[b1].depth, 2);
  assert.deepEqual(guides[b1].rails, [false]);
});


test("without WBS grouping the table stays a flat activity list", () => {
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

const statusActivities: WorkspaceActivityRow[] = [
  {
    id: "A-1", wbsId: "W-A1", code: "A1", name: "Excavate",
    cells: { duration: 2, "activity.status": "In Progress" },
    gantt: { start: "2026-09-01T00:00:00Z", finish: "2026-09-03T00:00:00Z", progressPercent: 50, critical: true },
  },
  {
    id: "A-2", wbsId: "W-A1", code: "A2", name: "Haul",
    cells: { duration: 2, "activity.status": "Completed" },
    gantt: { start: "2026-09-03T00:00:00Z", finish: "2026-09-05T00:00:00Z", progressPercent: 100, critical: false },
  },
  {
    id: "B-1", wbsId: "W-B", code: "B1", name: "Rebar",
    cells: { duration: 2 },
    gantt: { start: "2026-09-02T00:00:00Z", finish: "2026-09-04T00:00:00Z", progressPercent: 0, critical: false },
  },
];

test("a field group plan emits value bands in the configured order", () => {
  const asc = buildWorkspaceDisplayRows(statusActivities, nodes, "none", new Set(), [{ fieldId: "activity_status", direction: "asc" }]);
  assert.deepEqual(asc.map(rowKey), [
    "band:field:activity_status:s:Completed",
    "act:A-2",
    "band:field:activity_status:s:In Progress",
    "act:A-1",
    "band:field:activity_status:e:",
    "act:B-1",
  ]);
  const completed = asc[0];
  assert.equal(completed.kind, "fieldGroup");
  if (completed.kind !== "fieldGroup") return;
  assert.equal(completed.summary.activityCount, 1);
  assert.equal(completed.label, "Completed");
  assert.equal(completed.depth, 0);
  assert.equal(asc[1].kind === "activity" ? asc[1].depth : -1, 1);

  const desc = buildWorkspaceDisplayRows(statusActivities, nodes, "none", new Set(), [{ fieldId: "activity_status", direction: "desc" }]);
  assert.deepEqual(desc.filter((row) => row.kind === "fieldGroup").map((row) => row.kind === "fieldGroup" ? row.valueKey : ""),
    ["s:In Progress", "s:Completed", "e:"]);
  // "No value" stays last whatever the direction.
  assert.equal(desc[desc.length - 1].kind === "activity" ? desc[desc.length - 1].kind : "", "activity");
});

test("a WBS plan nests a second field level inside the deepest band", () => {
  const rows = buildWorkspaceDisplayRows(statusActivities, nodes, "wbs", new Set(), [
    { fieldId: "wbs", direction: "asc" },
    { fieldId: "activity_status", direction: "asc" },
  ]);
  assert.deepEqual(rows.map(rowKey), [
    "wbs:W-ROOT",
    "wbs:W-A",
    "wbs:W-A1",
    "band:W-A1>activity_status:s:Completed",
    "act:A-2",
    "band:W-A1>activity_status:s:In Progress",
    "act:A-1",
    "wbs:W-B",
    "band:W-B>activity_status:e:",
    "act:B-1",
  ]);
  const nested = rows.find((row) => row.kind === "fieldGroup" && row.valueKey === "s:In Progress");
  assert.deepEqual(nested?.kind === "fieldGroup" ? [nested.depth, nested.level, nested.bandKey] : [],
    [3, 1, "W-A1>activity_status:s:In Progress"]);
});

test("field bands collapse independently and never share a WBS band key", () => {
  const collapsed = new Set(["W-A1>activity_status:s:In Progress"]);
  const rows = buildWorkspaceDisplayRows(statusActivities, nodes, "wbs", collapsed, [
    { fieldId: "wbs", direction: "asc" },
    { fieldId: "activity_status", direction: "asc" },
  ]);
  assert.deepEqual(rows.map(rowKey), [
    "wbs:W-ROOT",
    "wbs:W-A",
    "wbs:W-A1",
    "band:W-A1>activity_status:s:Completed",
    "act:A-2",
    "band:W-A1>activity_status:s:In Progress",
    "wbs:W-B",
    "band:W-B>activity_status:e:",
    "act:B-1",
  ]);
  const inProgress = rows.find((row) => row.kind === "fieldGroup" && row.valueKey === "s:In Progress");
  assert.equal(inProgress?.kind === "fieldGroup" ? inProgress.collapsed : null, true);
  // The collapsed activity is the only hidden row; its sibling band survives.
  assert.ok(!rows.map(rowKey).includes("act:A-1"));
});

test("a field-first plan groups activities before the WBS hierarchy", () => {
  const rows = buildWorkspaceDisplayRows(statusActivities, nodes, "none", new Set(), [
    { fieldId: "activity_status", direction: "asc" },
    { fieldId: "wbs", direction: "asc" },
  ]);
  assert.deepEqual(rows.map(rowKey), [
    "band:field:activity_status:s:Completed",
    "wbs:field:activity_status:s:Completed>wbs:W-ROOT",
    "wbs:field:activity_status:s:Completed>wbs:W-A",
    "wbs:field:activity_status:s:Completed>wbs:W-A1",
    "act:A-2",
    "band:field:activity_status:s:In Progress",
    "wbs:field:activity_status:s:In Progress>wbs:W-ROOT",
    "wbs:field:activity_status:s:In Progress>wbs:W-A",
    "wbs:field:activity_status:s:In Progress>wbs:W-A1",
    "act:A-1",
    "band:field:activity_status:e:",
    "wbs:field:activity_status:e:>wbs:W-ROOT",
    "wbs:field:activity_status:e:>wbs:W-B",
    "act:B-1",
  ]);
  const firstWbs = rows.find((row) => row.kind === "wbs");
  assert.equal(firstWbs?.kind === "wbs" ? firstWbs.wbsId : "", "W-ROOT");
  assert.equal(firstWbs?.kind === "wbs" ? firstWbs.level : -1, 1);
});

test("a WBS level without loaded nodes is skipped instead of inventing bands", () => {
  const rows = buildWorkspaceDisplayRows(statusActivities, [], "wbs", new Set(), [
    { fieldId: "wbs", direction: "asc" },
    { fieldId: "activity_status", direction: "asc" },
  ]);
  assert.deepEqual(rows.map((row) => row.kind), ["fieldGroup", "activity", "fieldGroup", "activity", "fieldGroup", "activity"]);
});

test("tree guides treat field bands as parents with their own collapse state", () => {
  const rows = buildWorkspaceDisplayRows(statusActivities, nodes, "none", new Set(), [
    { fieldId: "activity_status", direction: "asc" },
  ]);
  const guides = buildWbsTreeGuides(rows);
  assert.equal(guides[0].hasChildren, true);
  assert.equal(guides[0].collapsed, false);
  assert.equal(guides[1].hasChildren, false);
  assert.deepEqual(guides[1].rails, []);
});
