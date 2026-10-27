import assert from "node:assert/strict";
import test from "node:test";
import {
  LANDING_LOCALE_STORAGE_KEY,
  WORKSPACE_LOCALE_STORAGE_KEY,
  WORKSPACE_MENU_STORAGE_KEY,
  WORKSPACE_PROJECT_STORAGE_KEY,
  isWorkspaceMenuKey,
  readRequestedProjectId,
  readWorkspaceLocalePreference,
  readWorkspaceMenuPreference,
  readWorkspaceProjectPreference,
  rememberWorkspaceLocale,
  rememberWorkspaceMenu,
  rememberWorkspaceProject,
  requestedProjectHref,
  type PreferenceStorage,
} from "./workspace-preferences.js";

function memoryStorage(initial: Record<string, string> = {}): PreferenceStorage & { values: Map<string, string> } {
  const values = new Map(Object.entries(initial));
  return {
    values,
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => { values.set(key, value); },
    removeItem: (key) => { values.delete(key); },
  };
}

test("stored workspace locale wins when the current build serves it", () => {
  const storage = memoryStorage({
    [WORKSPACE_LOCALE_STORAGE_KEY]: "fa",
    [LANDING_LOCALE_STORAGE_KEY]: "en",
  });
  assert.equal(readWorkspaceLocalePreference(["en", "fa"], storage), "fa");
});

test("the public language route seeds the workspace when no workspace choice exists", () => {
  const storage = memoryStorage({ [LANDING_LOCALE_STORAGE_KEY]: "fa" });
  assert.equal(readWorkspaceLocalePreference(["en", "fa"], storage), "fa");
});

test("unsupported or unregistered locales are ignored instead of half-rendering", () => {
  const storage = memoryStorage();
  storage.setItem(WORKSPACE_LOCALE_STORAGE_KEY, "de");
  assert.equal(readWorkspaceLocalePreference(["en", "fa"], storage), null);
  storage.removeItem!(WORKSPACE_LOCALE_STORAGE_KEY);
  rememberWorkspaceLocale("de", ["en", "fa"], storage);
  assert.equal(storage.values.has(WORKSPACE_LOCALE_STORAGE_KEY), false);
});

test("menu preferences accept only menus that the current navigation defines", () => {
  const storage = memoryStorage({ [WORKSPACE_MENU_STORAGE_KEY]: "schedule" });
  assert.equal(readWorkspaceMenuPreference(storage), "schedule");
  rememberWorkspaceMenu("schedule", storage);
  assert.equal(storage.values.get(WORKSPACE_MENU_STORAGE_KEY), "schedule");
  assert.equal(isWorkspaceMenuKey("deleted-menu"), false);
  storage.setItem(WORKSPACE_MENU_STORAGE_KEY, "deleted-menu");
  assert.equal(readWorkspaceMenuPreference(storage), null);
});

test("a project preference is scoped per signed-in user", () => {
  const storage = memoryStorage();
  rememberWorkspaceProject("user-a", "  project-1  ", storage);
  rememberWorkspaceProject("user-b", "project-2", storage);
  assert.equal(readWorkspaceProjectPreference("user-a", storage), "project-1");
  assert.equal(readWorkspaceProjectPreference("user-b", storage), "project-2");
  rememberWorkspaceProject("user-a", null, storage);
  assert.equal(readWorkspaceProjectPreference("user-a", storage), null);
  assert.equal(readWorkspaceProjectPreference("user-b", storage), "project-2");
  storage.setItem(WORKSPACE_PROJECT_STORAGE_KEY, JSON.stringify({ "user-c": "x".repeat(201) }));
  assert.equal(readWorkspaceProjectPreference("user-c", storage), null);
  storage.setItem(WORKSPACE_PROJECT_STORAGE_KEY, "not-json");
  assert.equal(readWorkspaceProjectPreference("user-b", storage), null);
});

test("blocked storage never throws into the bootstrap", () => {
  const throwing: PreferenceStorage = {
    getItem: () => { throw new Error("blocked"); },
    setItem: () => { throw new Error("blocked"); },
    removeItem: () => { throw new Error("blocked"); },
  };
  assert.equal(readWorkspaceLocalePreference(["en"], throwing), null);
  assert.equal(readWorkspaceMenuPreference(throwing), null);
  assert.equal(readWorkspaceProjectPreference("user-a", throwing), null);
  assert.doesNotThrow(() => rememberWorkspaceLocale("fa", ["en", "fa"], throwing));
  assert.doesNotThrow(() => rememberWorkspaceMenu("project", throwing));
  assert.doesNotThrow(() => rememberWorkspaceProject("user-a", "p1", throwing));
});

test("a project deep link is read from the query and reflected back into the address", () => {
  assert.equal(readRequestedProjectId("?project=p-1&x=2"), "p-1");
  assert.equal(readRequestedProjectId("?project=%20%20"), null);
  assert.equal(readRequestedProjectId("?project=" + "x".repeat(201)), null);
  assert.equal(readRequestedProjectId(""), null);
  assert.equal(
    requestedProjectHref("https://example.test/app/?project=old", "new-id"),
    "https://example.test/app/?project=new-id",
  );
  assert.equal(
    requestedProjectHref("https://example.test/app/?project=old", null),
    "https://example.test/app/",
  );
});
