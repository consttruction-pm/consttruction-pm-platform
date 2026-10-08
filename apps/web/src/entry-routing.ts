export type EntryRoute = "landing" | "app";

/**
 * GitHub Pages project sites are served below /<repository-name>/ while
 * custom-domain sites are served at /. The app is the only nested route;
 * all other paths should keep the public CUBI landing page visible.
 */
export function resolveEntryRoute(pathname: string): EntryRoute {
  const normalized = pathname.replace(/\/+$/, "") || "/";
  return /\/app(?:\/index\.html)?$/.test(normalized) ? "app" : "landing";
}
