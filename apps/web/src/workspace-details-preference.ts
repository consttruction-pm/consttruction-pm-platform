import type { WorkspaceState } from "./workspace-model.js";
import {
  readStoredValue,
  writeStoredValue,
  type PreferenceStorage,
} from "./workspace-preferences.js";

/**
 * The bottom Details pane is a presentation preference, never project data.
 * The value is scoped to the signed-in user, tenant, project and workspace
 * window so hiding Details in one window or project can never hide it in
 * another. A missing value means the documented default: Details visible.
 *
 * Browser localStorage is per user profile; the explicit user segment keeps
 * profiles that share a kiosk browser from inheriting each other's layout.
 */
export const WORKSPACE_DETAILS_STORAGE_KEY = "cubi:workspace:details-visible";

export function detailsVisibilityStorageKey(
  state: Pick<WorkspaceState, "context" | "activeMenu">,
  userId: string,
): string {
  return [
    WORKSPACE_DETAILS_STORAGE_KEY,
    encodeURIComponent(userId.trim()),
    encodeURIComponent(state.context.tenant_id ?? ""),
    encodeURIComponent(state.context.project_id),
    state.activeMenu,
  ].join(":");
}

export function readWorkspaceDetailsVisible(
  state: Pick<WorkspaceState, "context" | "activeMenu">,
  userId: string,
  storage: PreferenceStorage | null = browserStorage(),
): boolean | null {
  const raw = readStoredValue(detailsVisibilityStorageKey(state, userId), storage);
  if (raw === "true") return true;
  if (raw === "false") return false;
  return null;
}

export function rememberWorkspaceDetailsVisible(
  state: Pick<WorkspaceState, "context" | "activeMenu">,
  userId: string,
  visible: boolean,
  storage: PreferenceStorage | null = browserStorage(),
): void {
  writeStoredValue(
    detailsVisibilityStorageKey(state, userId),
    visible ? "true" : "false",
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
