import assert from "node:assert/strict";
import test from "node:test";
import {
  WORKSPACE_TOOLBAR_GROUPS,
  WORKSPACE_TOOLBAR_LABELS,
  WORKSPACE_TOOLBAR_STORAGE_KEY,
  isWorkspaceToolbarGroup,
  readHiddenToolbarGroups,
  rememberHiddenToolbarGroups,
  toggleToolbarGroup,
  toolbarVisibilityStorageKey,
} from "./workspace-toolbars.js";
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

test("every toolbar family has a label in every supported locale", () => {
  for (const [locale, pack] of Object.entries(WORKSPACE_TOOLBAR_LABELS)) {
    for (const group of WORKSPACE_TOOLBAR_GROUPS) {
      assert.ok(pack[group].trim().length > 0, `${locale}/${group} must have a label`);
    }
  }
  assert.equal(isWorkspaceToolbarGroup("gantt"), true);
  assert.equal(isWorkspaceToolbarGroup("bogus"), false);
});

test("visibility is stored per user and stale keys are dropped", () => {
  const storage = memoryStorage({
    [toolbarVisibilityStorageKey("u-1")]: JSON.stringify(["reports", "bogus", "edit"]),
    [`${WORKSPACE_TOOLBAR_STORAGE_KEY}:u-2`]: JSON.stringify(["wbs"]),
  });
  assert.deepEqual(readHiddenToolbarGroups("u-1", storage), ["edit", "reports"]);
  assert.deepEqual(readHiddenToolbarGroups("u-2", storage), ["wbs"]);
  assert.deepEqual(readHiddenToolbarGroups("", storage), []);
  assert.deepEqual(readHiddenToolbarGroups("u-3", storage), []);
});

test("toggling a family hides then restores it in canonical order", () => {
  const hidden = toggleToolbarGroup([], "edit");
  assert.deepEqual(hidden, ["edit"]);
  const restored = toggleToolbarGroup(hidden, "edit");
  assert.deepEqual(restored, []);
  const two = toggleToolbarGroup(toggleToolbarGroup([], "reports"), "edit");
  assert.deepEqual(two, ["edit", "reports"], "stored order follows the toolbar family order");
});

test("remembering hidden families round-trips and ignores malformed storage", () => {
  const storage = memoryStorage();
  rememberHiddenToolbarGroups("u-1", ["reports", "reports", "edit"], storage);
  assert.deepEqual(readHiddenToolbarGroups("u-1", storage), ["edit", "reports"]);
  rememberHiddenToolbarGroups("", ["edit"], storage);
  assert.equal(storage.values.has(toolbarVisibilityStorageKey("")), false);
  const broken = memoryStorage({ [toolbarVisibilityStorageKey("u-1")]: "{not-json" });
  assert.deepEqual(readHiddenToolbarGroups("u-1", broken), []);
});
