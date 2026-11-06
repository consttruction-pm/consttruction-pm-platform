export const VISUAL_WORKSPACE_PREVIEW_PROJECT_ID = "preview-rps-01";

/** No alternate demo route is exposed: every /app URL enters the authenticated workspace. */
export function shouldRenderVisualWorkspaceDemo(
  _pathname: string,
  _search: string,
): boolean {
  return false;
}

/** Keep project deep links stable inside the single authenticated workspace. */
export function liveWorkspaceProjectHref(href: string, projectId: string): string {
  const url = new URL(href);
  url.searchParams.set("project", projectId);
  url.searchParams.set("view", "live");
  return url.href;
}


/** Return session recovery to the canonical workspace, preserving only real project deep links. */
export function workspaceLoginNextPath(projectId: string | null): string {
  if (!projectId || projectId === VISUAL_WORKSPACE_PREVIEW_PROJECT_ID) return "/app";
  return `/app?project=${encodeURIComponent(projectId)}&view=live`;
}
