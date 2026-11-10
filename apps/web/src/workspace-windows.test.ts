import assert from "node:assert/strict";
import test from "node:test";
import {
  DEFAULT_OPEN_WINDOWS,
  WORKSPACE_WINDOWS_STORAGE_KEY,
  WORKSPACE_WINDOW_ORDER_STORAGE_KEY,
  closeWorkspaceWindow,
  moveWorkspaceWindow,
  normalizeOpenWindows,
  openWorkspaceWindow,
  readWorkspaceWindowOrder,
  readWorkspaceWindows,
  rememberWorkspaceWindowOrder,
  rememberWorkspaceWindows,
  reorderWorkspaceWindows,
} from "./workspace-windows.js";
import type { PreferenceStorage } from "./workspace-preferences.js";

function memoryStorage(initial: Record<string, string> = {}): PreferenceStorage & { values: Map<string, string> } {
  const values = new Map(Object.entries(initial));
  return {
    values,
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => { values.set(key, value); },
    removeItem: (key) => { values.delete(key); },
  };
}

test("default windows keep the activities workspace and its project context visible", () => {
  assert.deepEqual([...DEFAULT_OPEN_WINDOWS], ["schedule", "project"]);
  assert.deepEqual(readWorkspaceWindows(memoryStorage()), ["schedule", "project"]);
});

test("stored windows are filtered, deduplicated and ordered like the navigation", () => {
  const storage = memoryStorage({
    [WORKSPACE_WINDOWS_STORAGE_KEY]: JSON.stringify(["reports", "schedule", "reports", "unknown-window", "project"]),
  });
  assert.deepEqual(readWorkspaceWindows(storage), ["project", "schedule", "reports"]);
});

test("stale or malformed storage never opens an unknown window", () => {
  assert.deepEqual(
    readWorkspaceWindows(memoryStorage({ [WORKSPACE_WINDOWS_STORAGE_KEY]: "{not-json" })),
    ["schedule", "project"],
  );
  assert.deepEqual(
    readWorkspaceWindows(memoryStorage({ [WORKSPACE_WINDOWS_STORAGE_KEY]: JSON.stringify(["nope"]) })),
    ["schedule", "project"],
  );
  assert.deepEqual(normalizeOpenWindows([]), ["schedule", "project"]);
});

test("opening a window is idempotent and closing the active window selects a remaining one", () => {
  const opened = openWorkspaceWindow(["schedule"], "resources");
  assert.deepEqual(opened, ["schedule", "resources"]);
  assert.deepEqual(openWorkspaceWindow(opened, "resources"), ["schedule", "resources"]);

  const closed = closeWorkspaceWindow(opened, "resources", "resources");
  assert.deepEqual(closed.open, ["schedule"]);
  assert.equal(closed.active, "schedule");

  const background = closeWorkspaceWindow(opened, "schedule", "resources");
  assert.deepEqual(background.open, ["resources"]);
  assert.equal(background.active, "resources", "closing a background window keeps the active one");
});

test("the last window cannot be closed and an invalid key leaves the set untouched", () => {
  assert.deepEqual(closeWorkspaceWindow(["schedule"], "schedule", "schedule"), {
    open: ["schedule"],
    active: "schedule",
  });
  assert.deepEqual(openWorkspaceWindow(["schedule"], "not-a-window" as never), ["schedule"]);
});

test("remembered windows survive a reload and are normalized on write", () => {
  const storage = memoryStorage();
  rememberWorkspaceWindows(["reports", "schedule", "reports"], storage);
  assert.deepEqual(readWorkspaceWindows(storage), ["schedule", "reports"]);
});

test("reordering a tab moves it without inventing or dropping a window", () => {
  assert.deepEqual(reorderWorkspaceWindows(["schedule", "project", "reports"], "reports", "schedule"), ["reports", "schedule", "project"]);
  assert.deepEqual(reorderWorkspaceWindows(["schedule", "project"], "schedule", "project"), ["project", "schedule"]);
  assert.deepEqual(reorderWorkspaceWindows(["schedule", "project"], "schedule", "schedule"), ["schedule", "project"]);
  assert.deepEqual(reorderWorkspaceWindows(["schedule"], "not-a-window" as never, "schedule"), ["schedule"]);
});

test("keyboard reordering clamps at the ends", () => {
  assert.deepEqual(moveWorkspaceWindow(["schedule", "project", "reports"], "project", 1), ["schedule", "reports", "project"]);
  assert.deepEqual(moveWorkspaceWindow(["schedule", "project"], "schedule", -1), ["schedule", "project"]);
  assert.deepEqual(moveWorkspaceWindow(["schedule", "project"], "project", 5), ["schedule", "project"]);
});

test("a saved tab order is applied on read and defaults keep navigation order", () => {
  const storage = memoryStorage({
    [WORKSPACE_WINDOWS_STORAGE_KEY]: JSON.stringify(["project", "schedule", "reports"]),
    [WORKSPACE_WINDOW_ORDER_STORAGE_KEY]: JSON.stringify(["reports", "project"]),
  });
  assert.deepEqual(readWorkspaceWindows(storage), ["reports", "project", "schedule"]);

  const canonical = memoryStorage({
    [WORKSPACE_WINDOWS_STORAGE_KEY]: JSON.stringify(["reports", "schedule", "project"]),
    [WORKSPACE_WINDOW_ORDER_STORAGE_KEY]: JSON.stringify(["reports", "bogus"]),
  });
  assert.deepEqual(readWorkspaceWindows(canonical), ["reports", "project", "schedule"]);
});

test("remembering an order only keeps real window keys", () => {
  const storage = memoryStorage();
  rememberWorkspaceWindowOrder(["reports", "bogus" as never, "schedule"], storage);
  assert.deepEqual(readWorkspaceWindowOrder(storage), ["reports", "schedule"]);
  assert.deepEqual(readWorkspaceWindowOrder(memoryStorage({ [WORKSPACE_WINDOW_ORDER_STORAGE_KEY]: "{oops" })), []);
});
