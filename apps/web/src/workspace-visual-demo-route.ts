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

/**
 * The preview server serves its own sign-in page under `/preview/login`; the
 * deployed runtime serves `/login`. The server that renders the shell declares
 * the path in a meta tag so the client never guesses or probes.
 */
export function resolveWorkspaceLoginPath(root?: {
  querySelector(selector: string): { getAttribute(name: string): string | null } | null;
}): string {
  const doc = root ?? (typeof document === "undefined" ? null : document);
  const declared = doc?.querySelector('meta[name="cubi-login-path"]')?.getAttribute("content")?.trim();
  if (declared && declared.startsWith("/") && !declared.startsWith("//") && !declared.includes("\\")) {
    return declared;
  }
  return "/login";
}
