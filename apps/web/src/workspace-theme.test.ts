import assert from "node:assert/strict";
import test from "node:test";

import {
  applyWorkspaceTheme,
  DEFAULT_WORKSPACE_THEME,
  isWorkspaceTheme,
  readWorkspaceTheme,
  rememberWorkspaceTheme,
  WORKSPACE_THEME_IDS,
  workspaceThemeLabels,
} from "./workspace-theme.js";

function memoryStorage() {
  const values = new Map<string, string>();
  return {
    values,
    getItem(key: string) { return values.get(key) ?? null; },
    setItem(key: string, value: string) { values.set(key, value); },
    removeItem(key: string) { values.delete(key); },
  };
}

function fakeRoot() {
  const attributes = new Map<string, string>();
  return {
    attributes,
    setAttribute(name: string, value: string) { attributes.set(name, value); },
    removeAttribute(name: string) { attributes.delete(name); },
  } as unknown as HTMLElement & { attributes: Map<string, string> };
}

test("the six CUBI workspace themes are recognized and invalid values fail back safely", () => {
  assert.deepEqual(WORKSPACE_THEME_IDS, [
    "classic", "modern", "graphite", "arctic", "copper", "midnight",
  ]);
  for (const theme of WORKSPACE_THEME_IDS) assert.equal(isWorkspaceTheme(theme), true);
  assert.equal(isWorkspaceTheme("unknown"), false);
  assert.equal(isWorkspaceTheme(null), false);
  assert.equal(readWorkspaceTheme(memoryStorage()), DEFAULT_WORKSPACE_THEME);
});

test("all six theme selections persist through the existing browser preference key", () => {
  const storage = memoryStorage();
  for (const theme of WORKSPACE_THEME_IDS) {
    rememberWorkspaceTheme(theme, storage);
    assert.equal(readWorkspaceTheme(storage), theme);
  }
});

test("theme application selects the shared surface renderer and native color scheme", () => {
  const root = fakeRoot();
  applyWorkspaceTheme("graphite", root);
  assert.equal(root.getAttribute("data-cubi-theme"), "graphite");
  assert.equal(root.getAttribute("data-cubi-theme-surface"), "layered");
  assert.equal(root.getAttribute("data-cubi-color-scheme"), "dark");

  applyWorkspaceTheme("arctic", root);
  assert.equal(root.getAttribute("data-cubi-theme"), "arctic");
  assert.equal(root.getAttribute("data-cubi-theme-surface"), "layered");
  assert.equal(root.getAttribute("data-cubi-color-scheme"), "light");

  applyWorkspaceTheme("classic", root);
  assert.equal(root.getAttribute("data-cubi-theme"), "classic");
  assert.equal(root.getAttribute("data-cubi-theme-surface"), null);
  assert.equal(root.getAttribute("data-cubi-color-scheme"), "light");
});

test("every launch locale has a label for all six themes", () => {
  for (const locale of ["en", "fa", "de", "zh", "ar", "fr", "ja", "ko", "ru"]) {
    const labels = workspaceThemeLabels(locale);
    assert.deepEqual(Object.keys(labels), [...WORKSPACE_THEME_IDS]);
    for (const theme of WORKSPACE_THEME_IDS) {
      assert.ok(labels[theme].trim().length > 0, locale + "/" + theme + " label must exist");
    }
  }
});
