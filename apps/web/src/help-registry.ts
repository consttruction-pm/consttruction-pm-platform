import { GENERATED_HELP_ENTRIES } from "./help-registry.generated.js";
import { GENERATED_FEATURES } from "./feature-registry.generated.js";

/**
 * Contextual help resolution.
 *
 * Every answer the assistant gives about a page comes from one of these two
 * registries:
 *   - the official Help reference compiled from `docs/traceability/*.json`,
 *   - the public feature contract compiled from `site/capabilities.mjs`.
 *
 * The resolver can cite a direct topic, the nearest parent topic, an inherited
 * environment topic, or say that no topic exists and point at the internal
 * documentation. It never synthesizes a title, a URL or a reason: the reason is
 * always the one recorded next to the entry.
 */

export type OfficialHelpTopic = {
  source: string;
  title: string;
  url: string;
  pdfPage: number | null;
};

export type HelpRegistryEntry = {
  id: string;
  environment: string;
  kind: string;
  page: string;
  surface: string;
  module: string | null;
  help: OfficialHelpTopic | null;
  rationale: string | null;
  status: string;
};

export type FeatureRegistryEntry = {
  id: string;
  environment: string;
  route: string;
  status: string;
  traceabilityId: string;
  routeNote?: string;
};

export type HelpResolutionLevel = "direct" | "parent" | "inherited" | "internal-docs";

export type ContextualHelp = {
  level: HelpResolutionLevel;
  /** Registry id of the entry the topic came from, when one matched. */
  entryId: string | null;
  surface: string | null;
  topic: OfficialHelpTopic | null;
  /** The recorded reason, verbatim, when the page has no official topic. */
  reason: string | null;
  feature: FeatureRegistryEntry | null;
};

export const HELP_REGISTRY: readonly HelpRegistryEntry[] = GENERATED_HELP_ENTRIES;
export const FEATURE_REGISTRY: readonly FeatureRegistryEntry[] = GENERATED_FEATURES;

const HELP_BY_ID = new Map(HELP_REGISTRY.map((entry) => [entry.id, entry]));

/**
 * Menu → traceability id. A menu is a surface of the workspace shell, and each
 * of these ids names the official topic that documents that surface. Menus
 * without a matching surface (backup) are left unmapped on purpose so the
 * resolver inherits the workspace topic instead of inventing a mapping.
 */
export const WORKSPACE_MENU_HELP: Readonly<Record<string, string>> = Object.freeze({
  project: "ENG-WS-PROJECTS",
  wbs: "ENG-WS-WBS",
  schedule: "ENG-WS-SCHEDULE",
  progress: "ENG-WS-TRACKING",
  resources: "ENG-WS-RESOURCES",
  assignments: "ENG-WS-RESOURCE-USAGE",
  roles: "ENG-WS-ROLES",
  calendars: "ENG-WS-CALENDARS",
  cost: "ENG-WS-EXPENSES",
  expenses: "ENG-WS-EXPENSES",
  documents: "ENG-WS-DOCUMENTS",
  reports: "ENG-WS-REPORTS",
  tracking: "ENG-WS-TRACKING",
  issues: "ENG-WS-ISSUES",
  risks: "ENG-WS-RISKS",
  thresholds: "ENG-WS-THRESHOLDS",
  control: "ENG-WS-TRACKING",
  settings: "ENG-WS-ADMIN",
  administration: "ENG-WS-ADMIN",
  exchange: "ENG-WS-EXCHANGE",
} as const);

const LOCALE_PREFIXES = new Set([
  "en", "fa", "de", "zh", "ar", "fr", "ja", "ko", "ru", "tr",
]);

/** Normalize a browser pathname to the route spelling used by the registries. */
export function normalizeHelpRoute(pathname: string, basePath = ""): string {
  let path = (pathname || "/").split("#")[0].split("?")[0];
  if (basePath && path.startsWith(basePath)) path = path.slice(basePath.length);
  path = path.replace(/index\.html$/, "");
  const segments = path.split("/").filter(Boolean);
  if (segments.length >= 1 && LOCALE_PREFIXES.has(segments[0])) segments.shift();
  if (segments.length === 0) return "/";
  return `/${segments.join("/")}/`.replace(/\/+$/, "/");
}

function findByPage(route: string): HelpRegistryEntry | undefined {
  const wanted = route === "/" ? "/" : `${route.replace(/\/+$/, "")}/`;
  return HELP_REGISTRY.find(
    (entry) => (entry.page === "/" ? "/" : `${entry.page.replace(/\/+$/, "")}/`) === wanted,
  );
}

function inheritedRoot(route: string): HelpRegistryEntry | undefined {
  if (route === "/app" || route.startsWith("/app/")) return HELP_BY_ID.get("ENG-WS-SHELL");
  if (route.startsWith("/enterprise") || route.startsWith("/environments")) {
    return HELP_BY_ID.get("ENT-HOME");
  }
  // An unknown public path must not borrow the home page's topic: nothing in
  // the registry describes it, so the caller falls back to internal docs.
  return undefined;
}

function featureForRoute(route: string): FeatureRegistryEntry | null {
  const normalized = route === "/" ? "/" : `${route.replace(/\/+$/, "")}/`;
  return (
    FEATURE_REGISTRY.find((feature) => feature.route === normalized) ??
    FEATURE_REGISTRY.find((feature) => normalized.startsWith(feature.route)) ??
    null
  );
}

function internalDocs(entry: HelpRegistryEntry | null, route: string): ContextualHelp {
  return {
    level: "internal-docs",
    entryId: entry?.id ?? null,
    surface: entry?.surface ?? null,
    topic: null,
    reason: entry?.rationale ?? null,
    feature: featureForRoute(route),
  };
}

/**
 * Resolve the contextual help for a page. `menu` lets a workspace menu select
 * its own documented surface before the path is considered.
 */
export function resolveContextualHelp(
  pathname: string,
  options: { basePath?: string; menu?: string | null } = {},
): ContextualHelp {
  const route = normalizeHelpRoute(pathname, options.basePath ?? "");

  if (options.menu && WORKSPACE_MENU_HELP[options.menu]) {
    const entry = HELP_BY_ID.get(WORKSPACE_MENU_HELP[options.menu]);
    if (entry) {
      return entry.help
        ? {
            level: "direct",
            entryId: entry.id,
            surface: entry.surface,
            topic: entry.help,
            reason: null,
            feature: featureForRoute(route),
          }
        : internalDocs(entry, route);
    }
  }

  const direct = findByPage(route);
  if (direct) {
    return direct.help
      ? {
          level: "direct",
          entryId: direct.id,
          surface: direct.surface,
          topic: direct.help,
          reason: null,
          feature: featureForRoute(route),
        }
      : internalDocs(direct, route);
  }

  // Walk up to the nearest documented ancestor: /app/activities/extra → /app/activities/.
  // The workspace and environment roots are inherited context, not the page a
  // visitor is on, so reaching them is reported as inherited.
  const inheritedRoots = new Set(["/app/", "/environments/"]);
  const segments = route.split("/").filter(Boolean);
  for (let length = segments.length - 1; length > 0; length -= 1) {
    const candidate = `/${segments.slice(0, length).join("/")}/`;
    const entry = findByPage(candidate);
    if (entry?.help) {
      return {
        level: inheritedRoots.has(candidate) ? "inherited" : "parent",
        entryId: entry.id,
        surface: entry.surface,
        topic: entry.help,
        reason: null,
        feature: featureForRoute(route),
      };
    }
  }

  const root = inheritedRoot(route);
  if (root?.help) {
    return {
      level: "inherited",
      entryId: root.id,
      surface: root.surface,
      topic: root.help,
      reason: null,
      feature: featureForRoute(route),
    };
  }

  return internalDocs(null, route);
}

/** The feature contract for a public route, or null when the route is not a feature. */
export function resolveFeature(route: string): FeatureRegistryEntry | null {
  return featureForRoute(normalizeHelpRoute(route));
}
