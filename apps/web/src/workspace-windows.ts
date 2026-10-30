import type { WorkspaceMenuKey } from "./workspace-model.js";
import { WORKSPACE_NAVIGATION } from "./workspace-navigation.js";
import {
  readStoredValue,
  writeStoredValue,
  type PreferenceStorage,
} from "./workspace-preferences.js";

/**
 * Open workspace windows are a browser-local preference, like the active menu.
 * A window key is always one of the navigation surfaces, so stale storage can
 * never invent a window the build does not render. Closing never leaves the
 * workspace without a surface: the caller always receives a valid active key.
 */
export const WORKSPACE_WINDOWS_STORAGE_KEY = "cubi:workspace-windows";
export const DEFAULT_OPEN_WINDOWS: readonly WorkspaceMenuKey[] = ["schedule", "project"];

const WINDOW_ORDER: readonly WorkspaceMenuKey[] = WORKSPACE_NAVIGATION.map((item) => item.key);
const MAX_OPEN_WINDOWS = WINDOW_ORDER.length;

export function isWorkspaceWindowKey(value: string): value is WorkspaceMenuKey {
  return (WINDOW_ORDER as readonly string[]).includes(value);
}

/** Keep only known keys, deduplicate, and order them like the navigation tree. */
export function normalizeOpenWindows(values: readonly string[]): WorkspaceMenuKey[] {
  const requested = new Set(values.filter(isWorkspaceWindowKey));
  const ordered = WINDOW_ORDER.filter((key) => requested.has(key));
  return ordered.length ? ordered : [...DEFAULT_OPEN_WINDOWS];
}

export function openWorkspaceWindow(
  open: readonly WorkspaceMenuKey[],
  key: WorkspaceMenuKey,
): WorkspaceMenuKey[] {
  if (!isWorkspaceWindowKey(key)) return normalizeOpenWindows(open);
  return normalizeOpenWindows([...open, key]);
}

export function closeWorkspaceWindow(
  open: readonly WorkspaceMenuKey[],
  key: WorkspaceMenuKey,
  active: WorkspaceMenuKey,
): { open: WorkspaceMenuKey[]; active: WorkspaceMenuKey } {
  const current = normalizeOpenWindows(open);
  // The workspace always keeps one window open; the close control is hidden
  // for the last window, and this guard keeps a stale click harmless.
  if (current.length <= 1) return { open: current, active };
  const next = current.filter((item) => item !== key);
  if (!next.length) return { open: current, active };
  const nextActive = active === key ? next[next.length - 1] : active;
  return { open: next, active: nextActive };
}

export function readWorkspaceWindows(
  storage: PreferenceStorage | null = browserStorage(),
): WorkspaceMenuKey[] {
  const raw = readStoredValue(WORKSPACE_WINDOWS_STORAGE_KEY, storage);
  if (!raw) return [...DEFAULT_OPEN_WINDOWS];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [...DEFAULT_OPEN_WINDOWS];
    return normalizeOpenWindows(
      parsed.filter((value): value is string => typeof value === "string").slice(0, MAX_OPEN_WINDOWS),
    );
  } catch {
    return [...DEFAULT_OPEN_WINDOWS];
  }
}

export function rememberWorkspaceWindows(
  open: readonly WorkspaceMenuKey[],
  storage: PreferenceStorage | null = browserStorage(),
): void {
  writeStoredValue(
    WORKSPACE_WINDOWS_STORAGE_KEY,
    JSON.stringify(normalizeOpenWindows(open)),
    storage,
  );
}

function browserStorage(): PreferenceStorage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}
