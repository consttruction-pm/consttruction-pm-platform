import {
  readStoredValue,
  writeStoredValue,
  type PreferenceStorage,
} from "./workspace-preferences.js";

/**
 * Open project tabs are a browser-local preference, like the open workspace
 * windows. The signed-in session's own project list stays authoritative: a
 * stored tab is dropped when that list no longer contains the project, so a
 * stale or edited storage value can never open a project the user lost access
 * to. Opening a tab never writes project data; the server re-authorizes every
 * transition through POST /api/projects/{id}/open.
 */
export const PROJECT_TABS_STORAGE_PREFIX = "cubi:workspace-project-tabs";
/** A workspace with more than a dozen project tabs is not readable on a phone. */
export const MAX_PROJECT_TABS = 12;

export type ProjectTabState = {
  open: readonly string[];
  active: string;
};

const EMPTY_TABS: ProjectTabState = { open: [], active: "" };

function normalizeId(value: unknown): string | null {
  return typeof value === "string" && value.trim() && value.length <= 200
    ? value.trim()
    : null;
}

function uniqueAuthorized(
  values: readonly unknown[],
  authorized: ReadonlySet<string>,
): string[] {
  const seen = new Set<string>();
  const kept: string[] = [];
  for (const value of values) {
    const id = normalizeId(value);
    if (!id || !authorized.has(id) || seen.has(id)) continue;
    seen.add(id);
    kept.push(id);
    if (kept.length >= MAX_PROJECT_TABS) break;
  }
  return kept;
}

/**
 * The stored set filtered by the session's own list, in the user's order. The
 * active tab is always part of the set; when nothing survives, the first
 * authorized project becomes the only open tab.
 */
export function normalizeProjectTabs(
  open: readonly unknown[],
  active: unknown,
  authorizedIds: readonly string[],
): ProjectTabState {
  const authorized = new Set(authorizedIds.map((id) => id.trim()).filter(Boolean));
  if (!authorized.size) return { ...EMPTY_TABS };
  const activeId = normalizeId(active);
  const requested = [...open];
  if (activeId && authorized.has(activeId)) requested.push(activeId);
  const kept = uniqueAuthorized(requested, authorized);
  const resolvedActive = activeId && kept.includes(activeId) ? activeId : kept[0] ?? "";
  return { open: kept, active: resolvedActive };
}

/** Open a project tab without changing which tab is active. */
export function openProjectTab(
  state: ProjectTabState,
  projectId: string,
  authorizedIds: readonly string[],
): ProjectTabState {
  const normalized = normalizeProjectTabs(state.open, state.active, authorizedIds);
  const id = normalizeId(projectId);
  if (!id || !authorizedIds.includes(id)) return normalized;
  if (normalized.open.includes(id)) return normalized;
  return normalizeProjectTabs([...normalized.open, id], normalized.active, authorizedIds);
}

/**
 * Close one tab. The last tab cannot be closed: the workspace always shows one
 * authorized project, and the caller keeps the current context. Closing the
 * active tab selects its right neighbour, or its left neighbour at the end.
 */
export function closeProjectTab(
  state: ProjectTabState,
  projectId: string,
  authorizedIds: readonly string[],
): ProjectTabState {
  const normalized = normalizeProjectTabs(state.open, state.active, authorizedIds);
  const id = normalizeId(projectId);
  if (!id || !normalized.open.includes(id) || normalized.open.length <= 1) {
    return normalized;
  }
  const index = normalized.open.indexOf(id);
  const open = normalized.open.filter((item) => item !== id);
  if (normalized.active !== id) return { open, active: normalized.active };
  const nextActive = open[Math.min(index, open.length - 1)] ?? open[0] ?? "";
  return { open, active: nextActive };
}

/** Move the active tab by a signed offset, which wraps at both ends. */
export function adjacentProjectTab(
  state: ProjectTabState,
  offset: number,
  authorizedIds: readonly string[],
): ProjectTabState {
  const normalized = normalizeProjectTabs(state.open, state.active, authorizedIds);
  if (normalized.open.length <= 1) return normalized;
  const index = normalized.open.indexOf(normalized.active);
  const count = normalized.open.length;
  const target = ((index + offset) % count + count) % count;
  return { open: normalized.open, active: normalized.open[target] ?? normalized.active };
}

export function projectTabsStorageKey(userId: string): string {
  const normalized = userId.trim();
  return normalized
    ? `${PROJECT_TABS_STORAGE_PREFIX}:${normalized}`
    : PROJECT_TABS_STORAGE_PREFIX;
}

export function readProjectTabs(
  userId: string,
  storage: PreferenceStorage | null = browserStorage(),
): ProjectTabState | null {
  const raw = readStoredValue(projectTabsStorageKey(userId), storage);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
    const record = parsed as Record<string, unknown>;
    if (!Array.isArray(record.open)) return null;
    return {
      open: record.open.filter((value): value is string => typeof value === "string"),
      active: typeof record.active === "string" ? record.active : "",
    };
  } catch {
    return null;
  }
}

export function rememberProjectTabs(
  userId: string,
  state: ProjectTabState,
  storage: PreferenceStorage | null = browserStorage(),
): void {
  const normalized = {
    open: state.open.filter((value) => typeof value === "string").slice(0, MAX_PROJECT_TABS),
    active: state.active,
  };
  writeStoredValue(projectTabsStorageKey(userId), JSON.stringify(normalized), storage);
}

function browserStorage(): PreferenceStorage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}
