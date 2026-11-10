import assert from "node:assert/strict";
import test from "node:test";

import { buildActivityNetwork, renderActivityNetwork } from "./workspace-network.js";
import { createWorkspaceState, withActivities, withRelationships } from "./workspace-model.js";
import { renderMainWorkspace } from "./workspace-view.js";

type Container = {
  innerHTML: string;
  querySelectorAll: () => HTMLElement[];
  addEventListener?: (type: string, listener: (event: Event) => void) => void;
};

function activity(id: string, name: string, critical = false) {
  return {
    id,
    wbsId: "W-1",
    code: id,
    name,
    cells: {},
    gantt: {
      start: "2026-10-01",
      finish: "2026-10-02",
      progressPercent: critical ? 100 : 0,
      critical,
    },
  };
}

function relationship(id: string, predecessorId: string, successorId: string, type: "FS" | "SS" = "FS", lagValue = "0") {
  return {
    id,
    predecessorId,
    successorId,
    type,
    lagValue,
    lagUnit: "working-day",
    recordRevision: 1,
  };
}

test("activity network assigns deterministic longest-path levels from persisted relationships", () => {
  const model = buildActivityNetwork(
    [activity("A", "Kickoff"), activity("B", "Design"), activity("C", "Procure"), activity("D", "Build", true)],
    [
      relationship("R1", "A", "B"),
      relationship("R2", "A", "C"),
      relationship("R3", "B", "D"),
      relationship("R4", "C", "D"),
    ],
  );

  assert.equal(model.cycleDetected, false);
  assert.equal(model.levelCount, 3);
  assert.deepEqual(model.nodes.map((node) => [node.id, node.level]), [["A", 0], ["B", 1], ["C", 1], ["D", 2]]);
  assert.deepEqual(model.nodes.map((node) => [node.id, node.row]), [["A", 0], ["B", 0], ["C", 1], ["D", 0]]);
  assert.equal(model.edges.length, 4);
  assert.equal(model.nodes.find((node) => node.id === "D")?.critical, true);
  assert.equal(model.nodes.find((node) => node.id === "D")?.progressLabel, "100%");
  assert.equal(model.omittedRelationships, 0);
});

test("activity network never invents endpoints and reports omitted stored relationships", () => {
  const model = buildActivityNetwork(
    [activity("A", "Kickoff"), activity("B", "Design")],
    [
      relationship("R1", "A", "B"),
      relationship("R2", "A", "MISSING"),
      relationship("R3", "B", "B"),
    ],
  );

  assert.equal(model.edges.length, 1);
  assert.equal(model.edges[0]?.relationshipId, "R1");
  assert.equal(model.omittedRelationships, 2);
});

test("activity network keeps a persisted cycle visible without recalculating dates", () => {
  const model = buildActivityNetwork(
    [activity("A", "One"), activity("B", "Two")],
    [relationship("R1", "A", "B"), relationship("R2", "B", "A")],
  );

  assert.equal(model.cycleDetected, true);
  assert.equal(model.levelCount, 2);
  assert.deepEqual(model.nodes.map((node) => node.level), [1, 1]);
});

test("activity network markup is selectable, labelled and honest about missing logic", () => {
  const html = renderActivityNetwork(
    [activity("A", "Kickoff"), activity("B", "Design")],
    [relationship("R1", "A", "B", "SS", "5")],
    "en",
    "A",
  );

  assert.match(html, /data-network-view/);
  assert.match(html, /data-network-nodes="2"/);
  assert.match(html, /data-network-edges="1"/);
  assert.match(html, /data-gantt-activity-id="A"[^>]*aria-pressed="true"/);
  assert.match(html, /class="cp-network-node is-selected"/);
  assert.match(html, /SS\+5d/);
  assert.match(html, /not recalculated/);
  assert.doesNotMatch(html, /No persisted relationships/);

  const withoutLogic = renderActivityNetwork([activity("A", "Kickoff")], [], "en", null);
  assert.match(withoutLogic, /No persisted relationships are loaded; only activity nodes are shown\./);
});

test("layout options enable the network only with persisted logic and the choice renders it", () => {
  const store = new Map<string, string>();
  const previousWindow = (globalThis as { window?: unknown }).window;
  (globalThis as { window?: unknown }).window = {
    localStorage: {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => store.set(key, value),
    },
  };
  try {
    let state = createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en");
    state = withActivities(state, [activity("A", "Kickoff"), activity("B", "Design")]);
    state = withRelationships(state, [relationship("R1", "A", "B")]);

    const container: Container = { innerHTML: "", querySelectorAll: () => [] };
    renderMainWorkspace(container as unknown as HTMLElement, state);
    assert.match(container.innerHTML, /<select data-top-layout><option value="table-only">Activity Table<\/option><option value="table-gantt" selected>[^\n]*?<option value="activity-network">/);
    assert.match(container.innerHTML, /id="cp-activity-grid"/);

    const key = "cubi:workspace:top-layout:tenant-1:project-1:schedule";
    store.set(key, "activity-network");
    renderMainWorkspace(container as unknown as HTMLElement, state);
    assert.match(container.innerHTML, /data-network-view/);
    assert.match(container.innerHTML, /data-gantt-activity-id="A"/);
    // The network replaces the Gantt in the right pane; the activity table stays on the left.
    assert.match(container.innerHTML, /id="cp-activity-grid"/);
    assert.doesNotMatch(container.innerHTML, /id="cp-gantt"/);
    assert.match(container.innerHTML, /class="cp-p6-split"[^>]*>[\s\S]*id="cp-activity-grid"[\s\S]*data-network-view/);
    assert.match(container.innerHTML, /<option value="activity-network" selected>Activity Network<\/option>/);

    // Without persisted logic the stored choice cannot activate an empty graph.
    let bare = createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en");
    bare = withActivities(bare, [activity("A", "Kickoff")]);
    renderMainWorkspace(container as unknown as HTMLElement, bare);
    assert.match(container.innerHTML, /id="cp-activity-grid"/);
    assert.match(container.innerHTML, /<select data-top-layout><option value="table-only">Activity Table<\/option><option value="table-gantt" selected>[^\n]*?<option value="activity-network" disabled>/);
    assert.match(container.innerHTML, /instead of drawing placeholder nodes/);
  } finally {
    if (previousWindow === undefined) delete (globalThis as { window?: unknown }).window;
    else (globalThis as { window?: unknown }).window = previousWindow;
  }
});

test("changing the top layout persists the preference and swaps the primary view", () => {
  const store = new Map<string, string>();
  const previousWindow = (globalThis as { window?: unknown }).window;
  (globalThis as { window?: unknown }).window = {
    localStorage: {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => store.set(key, value),
    },
  };
  try {
    let state = createWorkspaceState({ tenant_id: "tenant-1", project_id: "project-1", revision: 3 }, "en");
    state = withActivities(state, [activity("A", "Kickoff"), activity("B", "Design")]);
    state = withRelationships(state, [relationship("R1", "A", "B")]);

    const listeners = new Map<string, (event: Event) => void>();
    const container: Container = {
      innerHTML: "",
      querySelectorAll: () => [],
      addEventListener: (type, listener) => listeners.set(type, listener),
    };
    renderMainWorkspace(container as unknown as HTMLElement, state);
    const change = listeners.get("change");
    assert.ok(change);
    change({
      target: { dataset: { topLayout: "" }, value: "activity-network", closest: () => null },
    } as unknown as Event);

    assert.equal(store.get("cubi:workspace:top-layout:tenant-1:project-1:schedule"), "activity-network");
    assert.match(container.innerHTML, /data-network-view/);
  } finally {
    if (previousWindow === undefined) delete (globalThis as { window?: unknown }).window;
    else (globalThis as { window?: unknown }).window = previousWindow;
  }
});
