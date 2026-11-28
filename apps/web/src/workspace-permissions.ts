/**
 * Project roles the authenticated session exposes to the Engineering workspace.
 *
 * The browser never grants a capability: these helpers only decide which
 * already-authorized surfaces to show. Every write and administration action
 * is authorized again by the server against the same session roles.
 */
export const PROJECT_ROLE = {
  viewer: "viewer",
  planner: "planner",
  projectAdmin: "project_admin",
  /** Platform owner role issued by the session service, not a project membership. */
  globalAdmin: "global_admin",
} as const;

export type ProjectRole = (typeof PROJECT_ROLE)[keyof typeof PROJECT_ROLE];

/** Roles that may write project data; the server enforces PROJECT_WRITE. */
export const PROJECT_WRITE_ROLES: readonly string[] = [
  PROJECT_ROLE.planner,
  PROJECT_ROLE.projectAdmin,
];

/**
 * Roles that may open project administration.
 *
 * `project_admin` is the project-scoped administrator; `global_admin` is the
 * platform owner the session service issues. Both are server-issued roles, so
 * recognizing the platform owner here does not widen any server permission.
 */
export const PROJECT_ADMIN_ROLES: readonly string[] = [
  PROJECT_ROLE.projectAdmin,
  PROJECT_ROLE.globalAdmin,
];

export function hasAnyRole(roles: readonly string[], wanted: readonly string[]): boolean {
  return roles.some((role) => wanted.includes(role));
}

export function canWriteProject(roles: readonly string[]): boolean {
  return hasAnyRole(roles, PROJECT_WRITE_ROLES);
}

export function canAdministerProject(roles: readonly string[]): boolean {
  return hasAnyRole(roles, PROJECT_ADMIN_ROLES);
}
