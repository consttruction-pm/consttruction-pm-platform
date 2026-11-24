import type { DesktopShortcut, DesktopShortcutChord } from "./workspace-desktop-shell.js";
import {
  readStoredValue,
  writeStoredValue,
  type PreferenceStorage,
} from "./workspace-preferences.js";

/**
 * Browser-local shortcut rebinding. The catalogue in
 * `workspace-desktop-shell.ts` stays the canonical default; this module stores
 * only per-user deviations and re-validates them against the current build, so
 * a stale or hand-edited value can never bind a key to a command that no
 * longer exists.
 *
 * Nothing here is project data: overrides are keyed by the signed-in user and
 * live in the browser, like the other workspace preferences.
 */
export const SHORTCUT_OVERRIDES_STORAGE_PREFIX = "cubi:workspace-shortcut-overrides";

export type ShortcutOverride = { keys: string; chord: DesktopShortcutChord };
export type ShortcutOverrides = Readonly<Record<string, ShortcutOverride>>;

const MAX_KEYS_LENGTH = 32;
const MAX_KEY_LENGTH = 16;
const MAX_CODE_LENGTH = 32;

export function shortcutOverridesStorageKey(userId: string): string {
  const normalized = userId.trim();
  return normalized
    ? `${SHORTCUT_OVERRIDES_STORAGE_PREFIX}:${normalized}`
    : SHORTCUT_OVERRIDES_STORAGE_PREFIX;
}

function validChord(value: unknown): DesktopShortcutChord | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const record = value as Record<string, unknown>;
  const chord: DesktopShortcutChord = {};
  if (typeof record.key === "string" && record.key.length > 0 && record.key.length <= MAX_KEY_LENGTH) {
    chord.key = record.key;
  } else if (typeof record.code === "string" && record.code.length > 0 && record.code.length <= MAX_CODE_LENGTH) {
    chord.code = record.code;
  } else {
    return null;
  }
  if (record.ctrlOrMeta === true) chord.ctrlOrMeta = true;
  if (record.alt === true) chord.alt = true;
  if (record.shift === true) chord.shift = true;
  return chord;
}

export function readShortcutOverrides(
  userId: string,
  storage: PreferenceStorage | null = browserStorage(),
): ShortcutOverrides {
  const raw = readStoredValue(shortcutOverridesStorageKey(userId), storage);
  if (!raw) return {};
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return {};
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
  const overrides: Record<string, ShortcutOverride> = {};
  for (const [id, value] of Object.entries(parsed as Record<string, unknown>)) {
    if (!/^shortcut\.[A-Za-z0-9_.-]+$/.test(id)) continue;
    if (!value || typeof value !== "object" || Array.isArray(value)) continue;
    const record = value as Record<string, unknown>;
    const keys = typeof record.keys === "string" ? record.keys.trim().slice(0, MAX_KEYS_LENGTH) : "";
    const chord = validChord(record.chord);
    if (!keys || !chord) continue;
    overrides[id] = { keys, chord };
  }
  return overrides;
}

export function rememberShortcutOverrides(
  userId: string,
  overrides: ShortcutOverrides,
  storage: PreferenceStorage | null = browserStorage(),
): void {
  const ids = Object.keys(overrides);
  writeStoredValue(
    shortcutOverridesStorageKey(userId),
    ids.length ? JSON.stringify(overrides) : null,
    storage,
  );
}

/** Apply overrides that still address a default catalogue entry. */
export function applyShortcutOverrides(
  base: readonly DesktopShortcut[],
  overrides: ShortcutOverrides,
): DesktopShortcut[] {
  return base.map((shortcut) => {
    const override = overrides[shortcut.id];
    return override
      ? { ...shortcut, keys: override.keys, chord: override.chord }
      : shortcut;
  });
}

export function withoutShortcutOverride(
  overrides: ShortcutOverrides,
  id: string,
): ShortcutOverrides {
  if (!(id in overrides)) return overrides;
  const next = { ...overrides };
  delete next[id];
  return next;
}

const MODIFIER_KEYS = new Set(["Control", "Shift", "Alt", "Meta", "OS", "AltGraph", "CapsLock"]);

const NAMED_KEY_LABELS: Record<string, string> = {
  " ": "Space",
  Space: "Space",
  ArrowUp: "↑",
  ArrowDown: "↓",
  ArrowLeft: "←",
  ArrowRight: "→",
  Insert: "Ins",
  Delete: "Del",
  Enter: "Enter",
  Escape: "Esc",
  Tab: "Tab",
  Backspace: "Backspace",
  Home: "Home",
  End: "End",
  PageUp: "PageUp",
  PageDown: "PageDown",
};

function keyLabel(event: { key: string; code?: string }): string | null {
  if (event.code === "NumpadAdd") return "Num +";
  if (event.code === "NumpadSubtract") return "Num -";
  if (event.code === "NumpadMultiply") return "Num *";
  if (event.code === "NumpadDivide") return "Num /";
  if (NAMED_KEY_LABELS[event.key]) return NAMED_KEY_LABELS[event.key];
  if (event.key.length === 1) return event.key.toUpperCase();
  return /^F\d{1,2}$/.test(event.key) ? event.key : null;
}

/**
 * Build a canonical binding from a keydown event. Returns null for a bare
 * modifier, an unusable key, or a printable key without Ctrl/Alt — binding
 * "a" alone would hijack ordinary typing.
 */
export function shortcutChordFromEvent(event: {
  key: string;
  code?: string;
  ctrlKey?: boolean;
  metaKey?: boolean;
  altKey?: boolean;
  shiftKey?: boolean;
}): { keys: string; chord: DesktopShortcutChord } | null {
  if (!event.key || MODIFIER_KEYS.has(event.key)) return null;
  const ctrlOrMeta = Boolean(event.ctrlKey || event.metaKey);
  const alt = Boolean(event.altKey);
  const shift = Boolean(event.shiftKey);
  const label = keyLabel(event);
  if (!label) return null;
  const printable = event.key.length === 1;
  if (printable && !ctrlOrMeta && !alt) return null;
  const keys = [ctrlOrMeta ? "Ctrl" : "", alt ? "Alt" : "", shift ? "Shift" : "", label]
    .filter(Boolean)
    .join("+");
  if (!keys || keys.length > MAX_KEYS_LENGTH) return null;
  const chord: DesktopShortcutChord = {};
  if (event.code === "NumpadAdd" || event.code === "NumpadSubtract"
    || event.code === "NumpadMultiply" || event.code === "NumpadDivide") {
    chord.code = event.code;
  } else {
    chord.key = event.key.toLowerCase();
  }
  if (ctrlOrMeta) chord.ctrlOrMeta = true;
  if (alt) chord.alt = true;
  if (shift) chord.shift = true;
  return { keys, chord };
}

export function normalizeShortcutKeys(keys: string): string {
  return keys.replace(/\s+/g, "").toLowerCase();
}

/** Another catalogue entry already using this chord, or null. */
export function conflictingShortcut(
  shortcuts: readonly DesktopShortcut[],
  id: string,
  keys: string,
): DesktopShortcut | null {
  const normalized = normalizeShortcutKeys(keys);
  return shortcuts.find(
    (shortcut) => shortcut.id !== id && normalizeShortcutKeys(shortcut.keys) === normalized,
  ) ?? null;
}

function browserStorage(): PreferenceStorage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}
