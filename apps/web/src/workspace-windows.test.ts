import assert from "node:assert/strict";
import test from "node:test";
import {
  DEFAULT_OPEN_WINDOWS,
  WORKSPACE_WINDOWS_STORAGE_KEY,
  closeWorkspaceWindow,
  normalizeOpenWindows,
  openWorkspaceWindow,
  readWorkspaceWindows,
  rememberWorkspaceWindows,
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
