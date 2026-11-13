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
/** User-defined tab order; kept apart so the open set stays canonical and valid. */
export const WORKSPACE_WINDOW_ORDER_STORAGE_KEY = "cubi:workspace-window-order";
export const DEFAULT_OPEN_WINDOWS: readonly WorkspaceMenuKey[] = ["schedule", "project"];

const WINDOW_ORDER: readonly WorkspaceMenuKey[] = WORKSPACE_NAVIGATION.map((item) => item.key);
const MAX_OPEN_WINDOWS = WINDOW_ORDER.length;

export function isWorkspaceWindowKey(value: string): value is WorkspaceMenuKey {
  return (WINDOW_ORDER as readonly string[]).includes(value);
}

/** Keep only known keys and deduplicate while preserving the caller's order. */
function sanitizeOpenWindows(values: readonly string[]): WorkspaceMenuKey[] {
  const seen = new Set<WorkspaceMenuKey>();
  const kept: WorkspaceMenuKey[] = [];
  for (const value of values) {
    if (!isWorkspaceWindowKey(value) || seen.has(value)) continue;
    seen.add(value);
    kept.push(value);
  }
  return kept;
}

/** Keep only known keys, deduplicate, and order them like the navigation tree. */
export function normalizeOpenWindows(values: readonly string[]): WorkspaceMenuKey[] {
  const requested = new Set(sanitizeOpenWindows(values));
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

/** Apply a saved tab order without inventing or dropping a window. */
export function applyWorkspaceWindowOrder(
  open: readonly WorkspaceMenuKey[],
  order: readonly WorkspaceMenuKey[],
): WorkspaceMenuKey[] {
  const current = sanitizeOpenWindows(open);
  const effective = current.length ? current : [...DEFAULT_OPEN_WINDOWS];
  const ranks = new Map(order.map((key, index) => [key, index]));
  const positions = new Map(effective.map((key, index) => [key, index]));
  return [...effective].sort((left, right) => {
    const leftRank = ranks.get(left) ?? Number.MAX_SAFE_INTEGER;
    const rightRank = ranks.get(right) ?? Number.MAX_SAFE_INTEGER;
    return leftRank === rightRank
      ? (positions.get(left) ?? 0) - (positions.get(right) ?? 0)
      : leftRank - rightRank;
  });
}

export function reorderWorkspaceWindows(
  open: readonly WorkspaceMenuKey[],
  from: WorkspaceMenuKey,
  to: WorkspaceMenuKey,
): WorkspaceMenuKey[] {
  const current = sanitizeOpenWindows(open);
  const fromIndex = current.indexOf(from);
  const toIndex = current.indexOf(to);
  if (fromIndex < 0 || toIndex < 0 || fromIndex === toIndex) return current;
  const next = [...current];
  const [moved] = next.splice(fromIndex, 1);
  next.splice(toIndex, 0, moved);
  return next;
}

/** Move a tab by a signed offset; used by the keyboard reorder path. */
export function moveWorkspaceWindow(
  open: readonly WorkspaceMenuKey[],
  key: WorkspaceMenuKey,
  offset: number,
): WorkspaceMenuKey[] {
  const current = sanitizeOpenWindows(open);
  const index = current.indexOf(key);
  if (index < 0) return current;
  const target = Math.min(current.length - 1, Math.max(0, index + offset));
  if (target === index) return current;
  return reorderWorkspaceWindows(current, key, current[target]);
}

export function readWorkspaceWindowOrder(
  storage: PreferenceStorage | null = browserStorage(),
): WorkspaceMenuKey[] {
  const raw = readStoredValue(WORKSPACE_WINDOW_ORDER_STORAGE_KEY, storage);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    const seen = new Set<string>();
    return parsed
      .filter((value): value is string => typeof value === "string" && isWorkspaceWindowKey(value))
      .filter((value) => (seen.has(value) ? false : (seen.add(value), true)))
      .slice(0, MAX_OPEN_WINDOWS) as WorkspaceMenuKey[];
  } catch {
    return [];
  }
}

export function rememberWorkspaceWindowOrder(
  open: readonly WorkspaceMenuKey[],
  storage: PreferenceStorage | null = browserStorage(),
): void {
  writeStoredValue(
    WORKSPACE_WINDOW_ORDER_STORAGE_KEY,
    JSON.stringify(open.filter(isWorkspaceWindowKey)),
    storage,
  );
}

export function readWorkspaceWindows(
  storage: PreferenceStorage | null = browserStorage(),
): WorkspaceMenuKey[] {
  const raw = readStoredValue(WORKSPACE_WINDOWS_STORAGE_KEY, storage);
  if (!raw) return [...DEFAULT_OPEN_WINDOWS];
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [...DEFAULT_OPEN_WINDOWS];
    const stored = sanitizeOpenWindows(
      parsed.filter((value): value is string => typeof value === "string").slice(0, MAX_OPEN_WINDOWS),
    );
    if (!stored.length) return [...DEFAULT_OPEN_WINDOWS];
    const normalized = normalizeOpenWindows(stored);
    const savedOrder = readWorkspaceWindowOrder(storage);
    return savedOrder.length ? applyWorkspaceWindowOrder(normalized, savedOrder) : normalized;
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

/**
 * Each project tab owns the set of windows it had open. The set is stored apart
 * from the shared default so switching projects restores that project's
 * workspace instead of overwriting it with the previous project's windows.
 */
export function projectWorkspaceWindowsStorageKey(projectId: string): string {
  return `${WORKSPACE_WINDOWS_STORAGE_KEY}:${projectId}`;
}

export function readProjectWorkspaceWindows(
  projectId: string,
  storage: PreferenceStorage | null = browserStorage(),
  fallback: readonly WorkspaceMenuKey[] = readWorkspaceWindows(storage),
): WorkspaceMenuKey[] {
  const fallbackWindows = [...fallback];
  const raw = readStoredValue(projectWorkspaceWindowsStorageKey(projectId), storage);
  if (!raw) return fallbackWindows;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return fallbackWindows;
    const stored = sanitizeOpenWindows(
      parsed.filter((value): value is string => typeof value === "string").slice(0, MAX_OPEN_WINDOWS),
    );
    if (!stored.length) return fallbackWindows;
    return normalizeOpenWindows(stored);
  } catch {
    return fallbackWindows;
  }
}

export function rememberProjectWorkspaceWindows(
  projectId: string,
  open: readonly WorkspaceMenuKey[],
  storage: PreferenceStorage | null = browserStorage(),
): void {
  if (!projectId.trim()) return;
  writeStoredValue(
    projectWorkspaceWindowsStorageKey(projectId),
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
