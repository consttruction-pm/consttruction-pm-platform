export const VISUAL_WORKSPACE_PREVIEW_PROJECT_ID = "preview-rps-01";

/**
 * The authenticated CUBI workspace is the only public /app shell.
 * Keep this compatibility predicate false so legacy ?view=visual links
 * resolve to the canonical project-backed workspace rather than mounting
 * a second, fixture-only application shell.
 */
export function shouldRenderVisualWorkspaceDemo(
  _pathname: string,
  _search: string,
): boolean {
  return false;
}

/**
 * Persist the canonical live workspace mode in a shareable project URL.
 * This preserves unrelated query parameters such as the selected locale.
 */
export function liveWorkspaceProjectHref(href: string, projectId: string): string {
  const url = new URL(href);
  url.searchParams.set("project", projectId);
  url.searchParams.set("view", "live");
  return url.href;
}

/**
 * Login and session recovery always return to the one authenticated workspace.
 * With no explicit project, let the workspace show the permission-filtered
 * project picker instead of silently selecting a sample/demo project.
 */
export function workspaceLoginNextPath(projectId: string | null): string {
  if (!projectId) return "/app?view=live";
  return `/app?project=${encodeURIComponent(projectId)}&view=live`;
}
