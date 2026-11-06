export const VISUAL_WORKSPACE_PREVIEW_PROJECT_ID = "preview-rps-01";

/**
 * Select the curated visual shell for the shared preview project without
 * changing the authenticated, data-backed workspace used by every other
 * project. The explicit "live" switch is retained so the real API workspace
 * remains available for integration testing and development.
 */
export function shouldRenderVisualWorkspaceDemo(
  pathname: string,
  search: string,
): boolean {
  const parameters = new URLSearchParams(search);
  if (parameters.get("view") === "live") return false;
  if (parameters.get("view") === "visual") return true;
  // Static hosting serves app.html as /app/ (and sometimes /app/index.html).
  // Normalize equivalent workspace URLs before selecting the visual preview.
  const normalizedPath = pathname.replace(/\\/+$/, "").replace(/\\/index\\.html$/, "") || "/";
  if (normalizedPath !== "/app") return false;

  // The accepted entry flow is Home → Login → Visual Workspace. A direct
  // login with no project context must therefore land in the visual shell,
  // not the unrelated live/API workspace. Explicit non-preview project IDs
  // continue to select the authenticated live workspace.
  const projectId = parameters.get("project");
  return !projectId || projectId === VISUAL_WORKSPACE_PREVIEW_PROJECT_ID;
}

/**
 * Persist the distinction between a visual sample and the real, project-backed
 * workspace in a shareable URL. Live bootstrap always writes this view marker
 * so refresh/re-entry cannot fall back into the visual preview route.
 */
export function liveWorkspaceProjectHref(href: string, projectId: string): string {
  const url = new URL(href);
  url.searchParams.set("project", projectId);
  url.searchParams.set("view", "live");
  return url.href;
}


/**
 * Keep session-recovery sign-in on the visual entry surface unless the user
 * explicitly opened a different project.
 */
export function workspaceLoginNextPath(projectId: string | null): string {
  if (!projectId || projectId === VISUAL_WORKSPACE_PREVIEW_PROJECT_ID) {
    return `/app?project=${VISUAL_WORKSPACE_PREVIEW_PROJECT_ID}`;
  }
  return `/app?project=${encodeURIComponent(projectId)}&view=live`;
}
