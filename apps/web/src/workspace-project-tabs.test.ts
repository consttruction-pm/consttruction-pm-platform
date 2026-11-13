import assert from "node:assert/strict";
import test from "node:test";
import {
  MAX_PROJECT_TABS,
  adjacentProjectTab,
  closeProjectTab,
  normalizeProjectTabs,
  openProjectTab,
  projectTabsStorageKey,
  readProjectTabs,
  rememberProjectTabs,
  type ProjectTabState,
} from "./workspace-project-tabs.js";

const AUTHORIZED = ["p1", "p2", "p3"];

function storage(initial: Record<string, string> = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => { values.set(key, value); return undefined; },
    removeItem: (key: string) => { values.delete(key); return undefined; },
    values,
  };
}

test("normalization keeps the user's order and drops unauthorized or duplicate tabs", () => {
  assert.deepEqual(
    normalizeProjectTabs(["p2", "p9", "p2", "p1"], "p9", AUTHORIZED),
    { open: ["p2", "p1"], active: "p2" },
  );
});

test("normalization always makes the active project part of the open set", () => {
  assert.deepEqual(
    normalizeProjectTabs([], "p3", AUTHORIZED),
    { open: ["p3"], active: "p3" },
  );
});

test("nothing is opened when the session lists no authorized project", () => {
  assert.deepEqual(normalizeProjectTabs(["p1"], "p1", []), { open: [], active: "" });
});

test("opening a tab appends it without stealing the active tab", () => {
  const state: ProjectTabState = { open: ["p1"], active: "p1" };
  assert.deepEqual(openProjectTab(state, "p3", AUTHORIZED), { open: ["p1", "p3"], active: "p1" });
  assert.deepEqual(openProjectTab(state, "p9", AUTHORIZED), state);
});

test("closing the active tab selects its right neighbour, then its left at the end", () => {
  assert.deepEqual(
    closeProjectTab({ open: ["p1", "p2", "p3"], active: "p2" }, "p2", AUTHORIZED),
    { open: ["p1", "p3"], active: "p3" },
  );
  assert.deepEqual(
    closeProjectTab({ open: ["p1", "p2", "p3"], active: "p3" }, "p3", AUTHORIZED),
    { open: ["p1", "p2"], active: "p2" },
  );
});

test("closing an inactive tab keeps the active project", () => {
  assert.deepEqual(
    closeProjectTab({ open: ["p1", "p2"], active: "p1" }, "p2", AUTHORIZED),
    { open: ["p1"], active: "p1" },
  );
});

test("the last tab cannot close", () => {
  const state: ProjectTabState = { open: ["p2"], active: "p2" };
  assert.deepEqual(closeProjectTab(state, "p2", AUTHORIZED), state);
});

test("adjacent navigation wraps in both directions", () => {
  const state: ProjectTabState = { open: ["p1", "p2", "p3"], active: "p3" };
  assert.equal(adjacentProjectTab(state, 1, AUTHORIZED).active, "p1");
  assert.equal(adjacentProjectTab(state, -1, AUTHORIZED).active, "p2");
});

test("the tab set persists per user and survives a round trip", () => {
  const store = storage();
  rememberProjectTabs("u1", { open: ["p2", "p1"], active: "p1" }, store);
  rememberProjectTabs("u2", { open: ["p3"], active: "p3" }, store);

  assert.equal(projectTabsStorageKey("u1"), "cubi:workspace-project-tabs:u1");
  assert.deepEqual(readProjectTabs("u1", store), { open: ["p2", "p1"], active: "p1" });
  assert.deepEqual(readProjectTabs("u2", store), { open: ["p3"], active: "p3" });
});

test("malformed storage is ignored instead of inventing tabs", () => {
  assert.equal(readProjectTabs("u1", storage({ [projectTabsStorageKey("u1")]: "{}" })), null);
  assert.equal(readProjectTabs("u1", storage({ [projectTabsStorageKey("u1")]: "not-json" })), null);
  assert.equal(readProjectTabs("u1", storage()), null);
});

test("a stored set never exceeds the readable tab limit", () => {
  const store = storage();
  const open = Array.from({ length: MAX_PROJECT_TABS + 4 }, (_, index) => `p${index}`);
  rememberProjectTabs("u1", { open, active: "p0" }, store);
  assert.equal(readProjectTabs("u1", store)?.open.length, MAX_PROJECT_TABS);
});
