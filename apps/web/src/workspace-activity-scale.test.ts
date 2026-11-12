import assert from "node:assert/strict";
import test from "node:test";

import {
  createWorkspaceState,
  withActivities,
  withWbsNodes,
  type WorkspaceActivityRow,
  type WorkspaceState,
  type WorkspaceWbsNode,
} from "./workspace-model.js";
import { renderMainWorkspace } from "./workspace-view.js";
import { applyActivityFilterState, type ActivityFilterState } from "./workspace-activity-filters.js";
import { DEFAULT_PRESENTATION } from "./workspace-presentation.js";
import { setCollapsedWbsIds } from "./workspace-wbs-display.js";

/**
 * Scale and presentation invariants for the Activities window.
 *
 * The workspace must render an entire project population rather than a fixed
 * number of rows, and a presentation choice (filter, collapsed branch, hidden
 * column) may only change what is drawn. The authoritative activity set that
 * the schedule composer reads stays exactly the same, which is why these tests
 * assert against `state.activities` as well as the rendered markup.
 */

const CONTEXT = { tenant_id: "tenant-scale", project_id: "project-scale", revision: 4 } as const;

function wbsTree(): WorkspaceWbsNode[] {
  const nodes: WorkspaceWbsNode[] = [
    { id: "W0", parentKind: "project", parentWbsId: null, localCode: "1", name: "Project", sequenceNumber: 0, recordRevision: 1 },
  ];
  for (let group = 1; group <= 4; group += 1) {
    nodes.push({
      id: `W${group}`,
      parentKind: "wbs",
      parentWbsId: "W0",
      localCode: String(group),
      name: `Group ${group}`,
      sequenceNumber: group,
      recordRevision: 1,
    });
    for (let leaf = 1; leaf <= 2; leaf += 1) {
      nodes.push({
        id: `W${group}-${leaf}`,
        parentKind: "wbs",
        parentWbsId: `W${group}`,
        localCode: `${group}.${leaf}`,
        name: `Group ${group} leaf ${leaf}`,
        sequenceNumber: leaf,
        recordRevision: 1,
      });
    }
  }
  return nodes;
}

function activities(count: number): WorkspaceActivityRow[] {
  const leaves = ["W1-1", "W1-2", "W2-1", "W2-2", "W3-1", "W3-2", "W4-1", "W4-2"];
  return Array.from({ length: count }, (_, index) => {
    const ordinal = index + 1;
    return {
      id: `S${String(ordinal).padStart(3, "0")}`,
      wbsId: leaves[index % leaves.length]!,
      code: `SC-${String(ordinal).padStart(3, "0")}`,
      name: `Stress activity ${ordinal}`,
      cells: { "activity_name": `Stress activity ${ordinal}`, "activity_status": "Not Started" },
      gantt: { start: "2026-09-01T00:00:00Z", finish: "2026-09-05T00:00:00Z", progressPercent: 0, critical: false },
    };
  });
}

function baseState(count: number): WorkspaceState {
  const state = withWbsNodes(createWorkspaceState(CONTEXT as WorkspaceState["context"], "en"), wbsTree());
  return withActivities(state, activities(count));
}

function render(state: WorkspaceState, filters?: ActivityFilterState): string {
  const container = { innerHTML: "", querySelectorAll: () => [] } as unknown as HTMLElement & { innerHTML: string };
  renderMainWorkspace(container, state, filters ? {
    presentation: { ...DEFAULT_PRESENTATION, filters },
  } : {});
  return (container as unknown as { innerHTML: string }).innerHTML;
}

function countActivityRows(html: string): number {
  return (html.match(/<tr[^>]*data-activity-id="/g) ?? []).length;
}

function countGanttBars(html: string): number {
  return (html.match(/data-gantt-activity-id="/g) ?? []).length;
}

function prefixFilter(): ActivityFilterState {
  return {
    saved: [{
      id: "custom:scale-prefix",
      name: "S0 prefix",
      match: "all",
      criteria: [{ fieldId: "activity_id", operator: "contains", value: "S0" }],
      scope: "layout",
    }],
    activeId: "custom:scale-prefix",
    selectedIds: ["custom:scale-prefix"],
    combine: "all",
    allActivities: false,
    applyMode: "replace",
  };
}

function installStorage(): () => void {
  const values = new Map<string, string>();
  const localStorage = {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => { values.set(key, value); },
    removeItem: (key: string) => { values.delete(key); },
    clear: () => values.clear(),
    key: (index: number) => [...values.keys()][index] ?? null,
    get length() { return values.size; },
  };
  const previous = Object.getOwnPropertyDescriptor(globalThis, "window");
  Object.defineProperty(globalThis, "window", { value: { localStorage }, configurable: true });
  return () => {
    if (previous) Object.defineProperty(globalThis, "window", previous);
    else delete (globalThis as { window?: unknown }).window;
  };
}

test("300 activities render completely in the table and the Gantt with no row cap", () => {
  const state = baseState(300);
  const html = render(state);
  assert.equal(state.activities.length, 300);
  assert.equal(countActivityRows(html), 300);
  assert.equal(countGanttBars(html), 300);
  assert.match(html, /data-activity-id="S001"/);
  assert.match(html, /data-activity-id="S300"/);
});

test("rendering the same 300-activity state is deterministic", () => {
  const state = baseState(300);
  assert.equal(render(state), render(state));
});

test("a filter narrows the rendered rows only; the stored activity set is untouched", () => {
  const state = baseState(300);
  const filters = prefixFilter();
  const applied = applyActivityFilterState(state.activities, filters, state.wbsNodes);
  assert.equal(applied.activities.length, 99);
  assert.equal(state.activities.length, 300);
  assert.equal(countActivityRows(render(state, filters)), 99);
  // Clearing the filter restores the whole population from the same state.
  assert.equal(countActivityRows(render(state)), 300);
});

test("a collapsed WBS branch hides rows without removing activities from state", () => {
  const restore = installStorage();
  try {
    const state = baseState(300);
    const all = countActivityRows(render(state));
    setCollapsedWbsIds(CONTEXT.project_id, ["W1"]);
    const collapsedHtml = render(state);
    const collapsed = countActivityRows(collapsedHtml);
    assert.equal(all, 300);
    assert.ok(collapsed < all, `collapsed rows ${collapsed} should be fewer than ${all}`);
    // Every activity still lives in the authoritative state.
    assert.equal(state.activities.length, 300);
    // Expanding restores exactly the same population.
    setCollapsedWbsIds(CONTEXT.project_id, []);
    assert.equal(countActivityRows(render(state)), 300);
  } finally {
    restore();
  }
});

test("hiding a column keeps every row and its underlying cell data", () => {
  const state = baseState(300);
  const withoutName = {
    ...state,
    columns: state.columns.filter((column) => column.id !== "activity_name" && column.id !== "activity.name"),
  };
  const html = render(withoutName);
  assert.equal(countActivityRows(html), 300);
  assert.doesNotMatch(html, /<th[^>]*data-column-id="activity_name"/);
  assert.equal(withoutName.activities[0]?.cells?.["activity_name"], "Stress activity 1");
});
