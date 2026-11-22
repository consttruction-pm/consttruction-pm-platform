import type { WorkspaceMenuKey } from "./workspace-model.js";

/**
 * The Engineering workspace is one session-gated document. A refresh on a
 * module address such as /app/wbs/ must reopen that window, not the last
 * window the browser remembered, so the path is the highest-priority source
 * of the active menu. Unknown segments fall through to the stored preference.
 */
const MODULE_MENUS: Record<string, WorkspaceMenuKey> = {
  projects: "project",
  project: "project",
  wbs: "wbs",
  activities: "schedule",
  schedule: "schedule",
  progress: "progress",
  resources: "resources",
  assignments: "assignments",
  roles: "roles",
  calendars: "calendars",
  costs: "cost",
  cost: "cost",
  expenses: "expenses",
  documents: "documents",
  reports: "reports",
  tracking: "tracking",
  issues: "issues",
  risks: "risks",
  thresholds: "thresholds",
  control: "control",
  settings: "settings",
  administration: "administration",
  exchange: "exchange",
  backup: "backup",
};

export function moduleMenuFromPath(pathname: string): WorkspaceMenuKey | undefined {
  const match = /^\/app\/([a-z][a-z-]*)\/?$/.exec(pathname);
  if (!match) return undefined;
  return MODULE_MENUS[match[1]];
}

export const WORKSPACE_MODULE_PATH_MENUS = MODULE_MENUS;
