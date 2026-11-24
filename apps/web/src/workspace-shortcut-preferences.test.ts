import assert from "node:assert/strict";
import test from "node:test";
import {
  SHORTCUT_OVERRIDES_STORAGE_PREFIX,
  applyShortcutOverrides,
  conflictingShortcut,
  normalizeShortcutKeys,
  readShortcutOverrides,
  rememberShortcutOverrides,
  shortcutChordFromEvent,
  shortcutOverridesStorageKey,
  withoutShortcutOverride,
} from "./workspace-shortcut-preferences.js";
import { getDesktopShortcuts } from "./workspace-desktop-shell.js";
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

test("overrides round-trip per user and clear when empty", () => {
  const storage = memoryStorage();
  const overrides = { "shortcut.find": { keys: "Ctrl+Alt+F", chord: { key: "f", ctrlOrMeta: true, alt: true } } };
  rememberShortcutOverrides("user-1", overrides, storage);
  assert.deepEqual(readShortcutOverrides("user-1", storage), overrides);
  assert.deepEqual(readShortcutOverrides("user-2", storage), {}, "overrides never leak between users");

  rememberShortcutOverrides("user-1", {}, storage);
  assert.equal(storage.values.has(shortcutOverridesStorageKey("user-1")), false);
  assert.deepEqual(readShortcutOverrides("user-1", storage), {});
});

test("a hand-edited or stale payload is rejected instead of trusted", () => {
  const storage = memoryStorage({
    [shortcutOverridesStorageKey("u")]: JSON.stringify({
      "shortcut.find": { keys: "Ctrl+Alt+F", chord: { key: "f", ctrlOrMeta: true, alt: true } },
      "not-a-shortcut": { keys: "Ctrl+Q", chord: { key: "q", ctrlOrMeta: true } },
      "shortcut.bad-keys": { keys: "   ", chord: { key: "q", ctrlOrMeta: true } },
      "shortcut.bad-chord": { keys: "Ctrl+Q", chord: "Ctrl+Q" },
      "shortcut.no-key": { keys: "Ctrl+Q", chord: { ctrlOrMeta: true } },
    }),
  });
  assert.deepEqual(readShortcutOverrides("u", storage), {
    "shortcut.find": { keys: "Ctrl+Alt+F", chord: { key: "f", ctrlOrMeta: true, alt: true } },
  });

  const malformed = memoryStorage({ [shortcutOverridesStorageKey("u")]: "{not json" });
  assert.deepEqual(readShortcutOverrides("u", malformed), {});
  const array = memoryStorage({ [shortcutOverridesStorageKey("u")]: "[]" });
  assert.deepEqual(readShortcutOverrides("u", array), {});
});

test("the storage key falls back to the shared prefix without a user", () => {
  assert.equal(shortcutOverridesStorageKey("  "), SHORTCUT_OVERRIDES_STORAGE_PREFIX);
  assert.equal(shortcutOverridesStorageKey("u-9"), `${SHORTCUT_OVERRIDES_STORAGE_PREFIX}:u-9`);
});

test("capture requires a modifier for printable keys but accepts function keys", () => {
  assert.equal(shortcutChordFromEvent({ key: "a" }), null, "a bare letter would hijack typing");
  assert.equal(shortcutChordFromEvent({ key: "Control", ctrlKey: true }), null, "a bare modifier is not a binding");
  assert.deepEqual(shortcutChordFromEvent({ key: "F2" }), { keys: "F2", chord: { key: "f2" } });
  assert.deepEqual(shortcutChordFromEvent({ key: "k", ctrlKey: true }), {
    keys: "Ctrl+K",
    chord: { key: "k", ctrlOrMeta: true },
  });
  assert.deepEqual(shortcutChordFromEvent({ key: "K", metaKey: true, shiftKey: true }), {
    keys: "Ctrl+Shift+K",
    chord: { key: "k", ctrlOrMeta: true, shift: true },
  });
  assert.deepEqual(shortcutChordFromEvent({ key: "F9", shiftKey: true }), {
    keys: "Shift+F9",
    chord: { key: "f9", shift: true },
  });
  assert.deepEqual(shortcutChordFromEvent({ key: "+", code: "NumpadAdd", ctrlKey: true }), {
    keys: "Ctrl+Num +",
    chord: { code: "NumpadAdd", ctrlOrMeta: true },
  });
  assert.deepEqual(shortcutChordFromEvent({ key: "Delete" }), {
    keys: "Del",
    chord: { key: "delete" },
  });
});

test("apply rewrites only known ids and drops unknown ones", () => {
  const base = getDesktopShortcuts(["schedule"]);
  const applied = applyShortcutOverrides(base, {
    "shortcut.find": { keys: "Ctrl+Alt+F", chord: { key: "f", ctrlOrMeta: true, alt: true } },
    "shortcut.gone": { keys: "Ctrl+Alt+G", chord: { key: "g", ctrlOrMeta: true, alt: true } },
  });
  assert.equal(applied.length, base.length);
  assert.equal(applied.find((s) => s.id === "shortcut.find")?.keys, "Ctrl+Alt+F");
  assert.equal(applied.some((s) => s.id === "shortcut.gone"), false);
  assert.equal(applied.find((s) => s.id === "shortcut.new")?.keys, "Ctrl+N", "untouched rows keep their default");
});

test("conflict detection ignores the row being rebound and normalizes whitespace/case", () => {
  const base = getDesktopShortcuts(["schedule"]);
  assert.equal(normalizeShortcutKeys(" Ctrl + Alt + F "), "ctrl+alt+f");
  assert.equal(conflictingShortcut(base, "shortcut.find", "ctrl+n")?.id, "shortcut.new");
  assert.equal(conflictingShortcut(base, "shortcut.find", "Ctrl+N")?.id, "shortcut.new");
  assert.equal(conflictingShortcut(base, "shortcut.new", "Ctrl+N"), null, "rebinding to its own key is not a conflict");
  assert.equal(conflictingShortcut(base, "shortcut.find", "Ctrl+Alt+F"), null);
});

test("withoutShortcutOverride returns the same object when nothing changes", () => {
  const overrides = { "shortcut.find": { keys: "Ctrl+Alt+F", chord: { key: "f", ctrlOrMeta: true, alt: true } } };
  assert.equal(withoutShortcutOverride(overrides, "shortcut.new"), overrides);
  const next = withoutShortcutOverride(overrides, "shortcut.find");
  assert.deepEqual(next, {});
  assert.deepEqual(overrides, { "shortcut.find": overrides["shortcut.find"] }, "the input stays immutable");
});
