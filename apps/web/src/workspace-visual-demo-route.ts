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
  return (
    pathname === "/app" &&
    parameters.get("project") === VISUAL_WORKSPACE_PREVIEW_PROJECT_ID
  );
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
