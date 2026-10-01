import type { WorkspaceMenuKey, WorkspaceState } from "./workspace-model.js";

export type WorkspaceSurfaceStatus = "implemented" | "partial" | "preview";

export type WorkspaceNavigationItem = {
  key: WorkspaceMenuKey;
  label: string;
  status: WorkspaceSurfaceStatus;
  submenus: readonly string[];
};

export const WORKSPACE_NAVIGATION: readonly WorkspaceNavigationItem[] = [
  { key: "project", label: "Project", status: "partial", submenus: ["Project / WBS", "Details"] },
  { key: "schedule", label: "Schedule", status: "implemented", submenus: ["Activity Grid", "Gantt Chart"] },
  { key: "progress", label: "Progress", status: "preview", submenus: ["Progress Overview", "Progress Detail"] },
  { key: "resources", label: "Resources", status: "preview", submenus: ["Resources", "Assignments"] },
  { key: "cost", label: "Cost", status: "preview", submenus: ["Cost Overview", "Cost Detail"] },
  { key: "documents", label: "Documents", status: "partial", submenus: ["Documents", "Evidence"] },
  { key: "reports", label: "Reports", status: "preview", submenus: ["Reports", "Print"] },
  { key: "control", label: "Control", status: "partial", submenus: ["Control Summary", "Changes & Claims"] },
  { key: "settings", label: "Settings", status: "partial", submenus: ["Language", "Workspace"] },
];

export function getWorkspaceNavigation(
  activeMenu: WorkspaceMenuKey,
): WorkspaceNavigationItem {
  const item = WORKSPACE_NAVIGATION.find((entry) => entry.key === activeMenu);
  if (!item) throw new Error("WORKSPACE_MENU_NOT_FOUND");
  return item;
}

export function getWorkspaceNavigationStatus(state: WorkspaceState): WorkspaceSurfaceStatus {
  return getWorkspaceNavigation(state.activeMenu).status;
}
