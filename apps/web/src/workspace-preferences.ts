import type { WorkspaceLocale, WorkspaceMenuKey } from "./workspace-model.js";
import { WORKSPACE_NAVIGATION } from "./workspace-navigation.js";

/**
 * Browser-local preferences that must survive a refresh without inventing a
 * server-side concept. Every value is re-validated against the current build
 * and the session's own project list before it is used, so stale storage can
 * never open a project the user cannot access or a menu that no longer exists.
 */
export const WORKSPACE_LOCALE_STORAGE_KEY = "cubi:workspace-locale";
export const WORKSPACE_MENU_STORAGE_KEY = "cubi:workspace-menu";
export const WORKSPACE_PROJECT_STORAGE_KEY = "cubi:workspace-project";
/** The public language routes own this key; the workspace acknowledges it on first visit. */
export const LANDING_LOCALE_STORAGE_KEY = "cubi:landing-locale";

export type PreferenceStorage = Pick<Storage, "getItem" | "setItem"> & Partial<Pick<Storage, "removeItem">>;

const WORKSPACE_MENU_KEYS: readonly WorkspaceMenuKey[] = WORKSPACE_NAVIGATION.map(
  (item) => item.key,
);

function browserStorage(): PreferenceStorage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    // Storage can be disabled by policy or a privacy mode; the UI must still work.
    return null;
  }
}

export function readStoredValue(
  key: string,
  storage: PreferenceStorage | null = browserStorage(),
): string | null {
  try {
    const value = storage?.getItem(key)?.trim();
    return value ? value : null;
  } catch {
    return null;
  }
}

export function writeStoredValue(
  key: string,
  value: string | null,
  storage: PreferenceStorage | null = browserStorage(),
): void {
  try {
    if (value === null) storage?.removeItem?.(key);
    else storage?.setItem(key, value);
  } catch {
    // A blocked storage write must not block navigation or project work.
  }
}

export function isWorkspaceMenuKey(value: string): value is WorkspaceMenuKey {
  return (WORKSPACE_MENU_KEYS as readonly string[]).includes(value);
}

/** Stored workspace language, then the language route the visitor chose publicly. */
export function readWorkspaceLocalePreference(
  available: readonly string[],
  storage: PreferenceStorage | null = browserStorage(),
): WorkspaceLocale | null {
  const workspace = readStoredValue(WORKSPACE_LOCALE_STORAGE_KEY, storage);
  if (workspace && available.includes(workspace)) return workspace;
  const landing = readStoredValue(LANDING_LOCALE_STORAGE_KEY, storage);
  if (landing && available.includes(landing)) return landing;
  return null;
}

export function rememberWorkspaceLocale(
  locale: WorkspaceLocale,
  available: readonly string[],
  storage: PreferenceStorage | null = browserStorage(),
): void {
  if (!available.includes(locale)) return;
  writeStoredValue(WORKSPACE_LOCALE_STORAGE_KEY, locale, storage);
}

export function readWorkspaceMenuPreference(
  storage: PreferenceStorage | null = browserStorage(),
): WorkspaceMenuKey | null {
  const value = readStoredValue(WORKSPACE_MENU_STORAGE_KEY, storage);
  return value && isWorkspaceMenuKey(value) ? value : null;
}

export function rememberWorkspaceMenu(
  menu: WorkspaceMenuKey,
  storage: PreferenceStorage | null = browserStorage(),
): void {
  if (!isWorkspaceMenuKey(menu)) return;
  writeStoredValue(WORKSPACE_MENU_STORAGE_KEY, menu, storage);
}

export function readWorkspaceProjectPreference(
  userId: string,
  storage: PreferenceStorage | null = browserStorage(),
): string | null {
  const normalizedUser = userId.trim();
  if (!normalizedUser) return null;
  const raw = readStoredValue(WORKSPACE_PROJECT_STORAGE_KEY, storage);
  if (!raw) return null;
  try {
    const values = JSON.parse(raw) as unknown;
    if (!values || typeof values !== "object" || Array.isArray(values)) return null;
    const projectId = (values as Record<string, unknown>)[normalizedUser];
    return typeof projectId === "string" && projectId.trim() && projectId.length <= 200
      ? projectId.trim()
      : null;
  } catch {
    return null;
  }
}

export function rememberWorkspaceProject(
  userId: string,
  projectId: string | null,
  storage: PreferenceStorage | null = browserStorage(),
): void {
  const normalizedUser = userId.trim();
  if (!normalizedUser) return;
  let values: Record<string, string> = {};
  try {
    const raw = readStoredValue(WORKSPACE_PROJECT_STORAGE_KEY, storage);
    const parsed = raw ? JSON.parse(raw) as unknown : null;
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      for (const [key, value] of Object.entries(parsed as Record<string, unknown>)) {
        if (typeof value === "string" && value.trim()) values[key] = value.trim();
      }
    }
  } catch {
    values = {};
  }
  const normalizedProject = projectId?.trim() ?? "";
  if (normalizedProject) values[normalizedUser] = normalizedProject;
  else delete values[normalizedUser];
  writeStoredValue(
    WORKSPACE_PROJECT_STORAGE_KEY,
    Object.keys(values).length ? JSON.stringify(values) : null,
    storage,
  );
}

/**
 * A project selection can be carried in a link (?project=...) so a copied URL
 * reopens the same workspace. The server remains authoritative: bootstrap only
 * accepts it when the signed-in user's own project list contains it.
 */
export function readRequestedProjectId(search: string): string | null {
  try {
    const value = new URLSearchParams(search).get("project")?.trim() ?? "";
    return value && value.length <= 200 ? value : null;
  } catch {
    return null;
  }
}

export function requestedProjectHref(href: string, projectId: string | null): string {
  try {
    const url = new URL(href);
    if (projectId) url.searchParams.set("project", projectId);
    else url.searchParams.delete("project");
    return url.href;
  } catch {
    return href;
  }
}
