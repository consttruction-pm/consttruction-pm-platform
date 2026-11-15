/** Temporary development navigation only. Never use this context for API authorization. */
export const DEVELOPMENT_ROLE_STORAGE_KEY = "cubi.development-role-context.v1";
export const DEVELOPMENT_ENVIRONMENT_STORAGE_KEY = "cubi.development-environment-context.v1";
export const DEVELOPMENT_ROLES = ["viewer", "planner", "project_admin"] as const;
export const DEVELOPMENT_ENVIRONMENTS = ["engineering", "enterprise"] as const;
export type DevelopmentRole = (typeof DEVELOPMENT_ROLES)[number];
export type DevelopmentEnvironment = (typeof DEVELOPMENT_ENVIRONMENTS)[number];

export interface PreviewEnvironmentInfo {
  environments: string[];
  publicDemo: boolean;
}

export function parseDevelopmentRole(value: unknown): DevelopmentRole | null {
  return typeof value === "string" && (DEVELOPMENT_ROLES as readonly string[]).includes(value)
    ? value as DevelopmentRole
    : null;
}

export function parseDevelopmentEnvironment(value: unknown): DevelopmentEnvironment | null {
  return typeof value === "string" && (DEVELOPMENT_ENVIRONMENTS as readonly string[]).includes(value)
    ? value as DevelopmentEnvironment
    : null;
}

/** The fixture runtime calls its project_admin persona "admin". */
export function previewLoginRole(role: DevelopmentRole): string {
  return role === "project_admin" ? "admin" : role;
}

/** Only the local workbench is an allowed post-selection redirect. */
export function resolveRoleSelectionNext(value: string | null): string {
  if (!value) return "/workben¶»§q«^