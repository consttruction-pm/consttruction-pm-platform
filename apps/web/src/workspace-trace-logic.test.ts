import assert from "node:assert/strict";
import test from "node:test";
import {
  TRACE_LOGIC_DEFAULT_DEPTH,
  TRACE_LOGIC_MAX_DEPTH,
  buildTraceLogic,
  readTraceLogicDepth,
  renderTraceLogic,
  storeTraceLogicDepth,
} from "./workspace-trace-logic.js";
import type { WorkspaceActivityRow, WorkspaceRelationshipRow } from "./workspace-model.js";

function activity(id: string, name = id, critical = false, progressPercent = 0): WorkspaceActivityRow {
  return {
    id,
    wbsId: "wbs-1",
    code: id,
    name,
    gantt: { start: "2026-01-01", finish: "2026-01-02", progressPercent, critical },
  };
}

function link(
  id: string,
  predecessorId: string,
  successorId: string,
  type: WorkspaceRelationshipRow["type"] = "FS",
  lagValue = "0",
  lagUnit = "working-day",
): WorkspaceRelationshipRow {
  return { id, predecessorId, successorId, type, lagValue, lagUnit, recordRevision: 1 };
}

function memoryStorage(): Storage {
  const rows = new Map<string, string>();
  return {
    get length() { return rows.size; },
    clear: () => rows.clear(),
    getItem: (key: string) => rows.get(key) ?? null,
    key: (index: number) => Array.from(rows.keys())[index] ?? null,
    removeItem: (key: string) => { rows.delete(key); },
    setItem: (key: string, value: string) => { rows.set(key, String(value)); },
  };
}

test("trace logic lists direct predecessors and successors with their persisted logic", () => {
  const activities = [activity("A"), activity("B", "Start", true), activity("C")];
  const relationships = [link("r1", "A", "B", "SS", "2", "working-hour"), link("r2", "B", "C", "FF")];
  const model = buildTraceLogic(activities, relationships, "B", "en", 3);
  assert.equal(model.selectedId, "B");
  assert.deepEqual(model.predecessors.map((row) => row.activity.id), ["A"]);
  assert.deepEqual(model.successors.map((row) => row.activity.id), ["C"]);
  assert.equal(model.predecessors[0]?.relationshipId, "r1");
  assert.equal(model.predecessors[0]?.edgeLabel, "SS+2h");
  assert.equal(model.successors[0]?.edgeLabel, "FF");
  assert.equal(model.successors[0]?.critical, false);
  assert.equal(model.cycleDetected, false);
  assert.equal(model.missingReferences, 0);
});

test("trace logic walks level by level and respects the chosen depth", () => {
  const activities = [activity("A"), activity("B"), activity("C")];
  const relationships = [link("r1", "A", "B"), link("r2", "B", "C")];
  const shallow = buildTraceLogic(activities, relationships, "C", "en", 1);
  assert.deepEqual(shallow.predecessors.map((row) => [row.activity.id, row.level]), [["B", 1]]);
  const deeper = buildTraceLogic(activities, relationships, "C", "en", 2);
  assert.deepEqual(deeper.predecessors.map((row) => [row.activity.id, row.level]), [["B", 1], ["A", 2]]);
});

test("trace logic clamps depth and stops on cycles instead of looping", () => {
  const activities = [activity("A"), activity("B")];
  const relationships = [link("r1", "A", "B"), link("r2", "B", "A")];
  const model = buildTraceLogic(activities, relationships, "A", "en", 99);
  assert.equal(model.depth, TRACE_LOGIC_MAX_DEPTH);
  assert.equal(model.cycleDetected, true);
  assert.deepEqual(model.successors.map((row) => row.activity.id), ["B"]);
  const low = buildTraceLogic(activities, relationships, "A", "en", -4);
  assert.equal(low.depth, 1);
});

test("trace logic reports a converging diamond once without inventing a cycle", () => {
  const activities = ["A", "B", "C", "D"].map((id) => activity(id));
  const relationships = [link("r1", "A", "B"), link("r2", "A", "C"), link("r3", "B", "D"), link("r4", "C", "D")];
  const model = buildTraceLogic(activities, relationships, "A", "en", 3);
  assert.equal(model.cycleDetected, false);
  assert.deepEqual(
    model.successors.map((row) => [row.activity.id, row.level]),
    [["B", 1], ["C", 1], ["D", 2]],
  );
});

test("relationships to activities that are not loaded are counted, never invented", () => {
  const model = buildTraceLogic([activity("A")], [link("r1", "ghost", "A"), link("r2", "A", "ghost")], "A", "en", 2);
  assert.equal(model.predecessors.length, 0);
  assert.equal(model.successors.length, 0);
  assert.equal(model.missingReferences, 2);
});

test("trace logic needs a loaded selected activity", () => {
  const model = buildTraceLogic([activity("A")], [link("r1", "A", "A")], "missing", "en", 2);
  assert.equal(model.selectedId, null);
  assert.deepEqual(model.predecessors, []);
  assert.deepEqual(model.successors, []);
});

test("trace depth preference is clamped and survives storage failures", () => {
  const storage = memoryStorage();
  assert.equal(readTraceLogicDepth(storage), TRACE_LOGIC_DEFAULT_DEPTH);
  storeTraceLogicDepth(3, storage);
  assert.equal(readTraceLogicDepth(storage), 3);
  storeTraceLogicDepth(-5, storage);
  assert.equal(readTraceLogicDepth(storage), 1);
  storage.setItem("cubi:workspace:trace-logic-depth", "not-a-number");
  assert.equal(readTraceLogicDepth(storage), TRACE_LOGIC_DEFAULT_DEPTH);
  const broken = { ...memoryStorage(), getItem: () => { throw new Error("denied"); } } as unknown as Storage;
  assert.equal(readTraceLogicDepth(broken), TRACE_LOGIC_DEFAULT_DEPTH);
});

test("trace logic renderer exposes navigation, depth and escaped labels", () => {
  const activities = [activity("A", "<script>alert(1)</script>", true, 42), activity("B", "Build")];
  const relationships = [link("r1", "A", "B", "FS", "3", "working-day")];
  const html = renderTraceLogic(activities, relationships, "en", "B", 2);
  assert.match(html, /data-trace-logic/);
  assert.match(html, /data-trace-selected="B"/);
  assert.match(html, /data-trace-depth-value="2"/);
  assert.match(html, /<option value="2" selected>2<\/option>/);
  assert.match(html, /data-trace-goto="A"/);
  assert.doesNotMatch(html, /<script>alert/);
  assert.match(html, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
  assert.match(html, /FS\+3d/);
  assert.match(html, /42%/);
});

test("trace logic renderer explains cycles and empty chains", () => {
  const cyclic = renderTraceLogic(
    [activity("A"), activity("B")],
    [link("r1", "A", "B"), link("r2", "B", "A")],
    "en",
    "A",
    3,
  );
  assert.match(cyclic, /ircular dependency/);
  const lonely = renderTraceLogic([activity("A")], [], "en", "A", 2);
  assert.match(lonely, /No persisted relationship/);
  const none = renderTraceLogic([activity("A")], [], "en", null, 2);
  assert.match(none, /Select an activity to trace/);
});
