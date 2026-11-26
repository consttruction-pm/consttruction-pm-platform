import assert from "node:assert/strict";
import test from "node:test";
import {
  WORKSPACE_DETAILS_STORAGE_KEY,
  detailsVisibilityStorageKey,
  readWorkspaceDetailsVisible,
  rememberWorkspaceDetailsVisible,
  resolveWorkspaceDetailsVisible,
} from "./workspace-details-preference.js";
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

const context = { tenant_id: "tenant-a", project_id: "project-1", revision: 3 };

test("the visibility key is scoped to the user, tenant, project and window", () => {
  const schedule = detailsVisibilityStorageKey({ context, activeMenu: "schedule" }, "user-1");
  assert.equal(
    schedule,
    `${WORKSPACE_DETAILS_STORAGE_KEY}:user-1:tenant-a:project-1:schedule`,
  );
  assert.notEqual(schedule, detailsVisibilityStorageKey({ context, activeMenu: "project" }, "user-1"));
  assert.notEqual(schedule, detailsVisibilityStorageKey({ context, activeMenu: "schedule" }, "user-2"));
  assert.notEqual(
    schedule,
    detailsVisibilityStorageKey({ context: { ...context, project_id: "project-2" }, activeMenu: "schedule" }, "user-1"),
  );
});

test("a stored value is read back for its own window only", () => {
  const storage = memoryStorage();
  rememberWorkspaceDetailsVisible({ context, activeMenu: "schedule" }, "user-1", false, storage);
  assert.equal(readWorkspaceDetailsVisible({ context, activeMenu: "schedule" }, "user-1", storage), false);
  assert.equal(readWorkspaceDetailsVisible({ context, activeMenu: "project" }, "user-1", storage), null);
  assert.equal(readWorkspaceDetailsVisible({ context, activeMenu: "schedule" }, "user-2", storage), null);
});

test("a window with no stored value resolves to the visible default, never to another window's value", () => {
  const storage = memoryStorage();
  rememberWorkspaceDetailsVisible({ context, activeMenu: "schedule" }, "user-1", false, storage);
  // The Activities window keeps its explicit choice.
  assert.equal(resolveWorkspaceDetailsVisible({ context, activeMenu: "schedule" }, "user-1", storage), false);
  // A window that was never toggled is visible even though the previous window hid it.
  assert.equal(resolveWorkspaceDetailsVisible({ context, activeMenu: "project" }, "user-1", storage), true);
  assert.equal(resolveWorkspaceDetailsVisible({ context, activeMenu: "resources" }, "user-1", storage), true);
});

test("the resolved value follows a later explicit toggle in the same window", () => {
  const storage = memoryStorage();
  assert.equal(resolveWorkspaceDetailsVisible({ context, activeMenu: "schedule" }, "user-1", storage), true);
  rememberWorkspaceDetailsVisible({ context, activeMenu: "schedule" }, "user-1", false, storage);
  assert.equal(resolveWorkspaceDetailsVisible({ context, activeMenu: "schedule" }, "user-1", storage), false);
  rememberWorkspaceDetailsVisible({ context, activeMenu: "schedule" }, "user-1", true, storage);
  assert.equal(resolveWorkspaceDetailsVisible({ context, activeMenu: "schedule" }, "user-1", storage), true);
});

test("a null storage keeps the default instead of failing the render", () => {
  assert.equal(resolveWorkspaceDetailsVisible({ context, activeMenu: "schedule" }, "user-1", null), true);
  assert.equal(readWorkspaceDetailsVisible({ context, activeMenu: "schedule" }, "user-1", null), null);
});
