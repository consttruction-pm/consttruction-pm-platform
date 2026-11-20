import { resolveContextualHelp } from "./help-registry.js";
import type { ContextualHelp } from "./help-registry.js";

/**
 * C01–C35 capability inheritance and page-level Help registry.
 *
 * The CUBISITE workbook (`/CUBISITE/cubisite.xlsx` v8) is the product owner's
 * numbering. It is not part of this repository, so this module uses the
 * C01–C35 enumeration already accepted in `docs/cubisite/AUDIT_BASELINE_2026-11-20.md`
 * and never invents a name for an identifier the enumeration does not contain
 * (C05). Every Help title, URL and page number comes from the compiled Help
 * registry; this module only decides *which* recorded surface a capability
 * inherits from.
 */

export type CapabilityStatus =
  | "IMPLEMENTED"
  | "PARTIAL"
  | "PREVIEW"
  | "PLANNED"
  | "CUBI_OWNED"
  | "MISSING_EVIDENCE";

export type CapabilityInheritance = {
  id: string;
  name: string;
  status: CapabilityStatus;
  /** Public routes (as in `site/routes.mjs`) that advertise the capability. */
  publicRoutes: readonly string[];
  /** Traceability ids of the workspace surfaces that implement it. */
  workspaceRows: readonly string[];
  /** The entry whose official topic constrains the claim, when one exists. */
  helpEntryId: string | null;
  /** Feature-contract id from `site/capabilities.mjs`, when one exists. */
  featureId: string | null;
  note: string;
};

/** Capabilities that apply to every published page rather than one route. */
export const SITE_WIDE_CAPABILITIES: readonly string[] = Object.freeze(["C29", "C30", "C31", "C33"]);

export const CAPABILITY_INHERITANCE: readonly CapabilityInheritance[] = Object.freeze([
  {
    id: "C01",
    name: "Workspace / Projects",
    status: "PARTIAL",
    publicRoutes: ["platform/", "get-started/"],
    workspaceRows: ["ENG-WS-PROJECTS"],
    helpEntryId: "ENG-WS-PROJECTS",
    featureId: null,
    note: "Project lifecycle is wired on PostgreSQL; the public pages describe the workspace, not a second shell.",
  },
  {
    id: "C02",
    name: "WBS / Activities",
    status: "PARTIAL",
    publicRoutes: ["features/project-controls/"],
    workspaceRows: ["ENG-WS-WBS", "ENG-WS-ACTIVITY-TABLE"],
    helpEntryId: "ENG-WS-WBS",
    featureId: "project-controls",
    note: "WBS hierarchy and the activity table are one surface; the WBS topic owns the hierarchy.",
  },
  {
    id: "C03",
    name: "Field Registry",
    status: "IMPLEMENTED",
    publicRoutes: ["features/project-controls/"],
    workspaceRows: ["ENG-WS-ACTIVITY-TABLE", "ENG-WS-UDF"],
    helpEntryId: "ENG-WS-UDF",
    featureId: "project-controls",
    note: "Field choices and user-defined fields share the column definition path.",
  },
  {
    id: "C04",
    name: "Grid / Layout",
    status: "PARTIAL",
    publicRoutes: ["features/project-controls/"],
    workspaceRows: ["ENG-WS-LAYOUTS", "ENG-WS-ACTIVITY-TABLE"],
    helpEntryId: "ENG-WS-LAYOUTS",
    featureId: "project-controls",
    note: "Saved layouts apply to every grid; the layout topic documents the activity grid it is demonstrated on.",
  },
  {
    id: "C05",
    name: "Unresolved — see workbook gap",
    status: "MISSING_EVIDENCE",
    publicRoutes: [],
    workspaceRows: [],
    helpEntryId: null,
    featureId: null,
    note: "The accepted enumeration jumps from C04 to C06. No accessible artefact names C05; no row is invented.",
  },
  {
    id: "C06",
    name: "Calendar",
    status: "PARTIAL",
    publicRoutes: ["features/scheduling/"],
    workspaceRows: ["ENG-WS-CALENDARS"],
    helpEntryId: "ENG-WS-CALENDARS",
    featureId: "scheduling",
    note: "Project and resource calendars share one registry-driven editor.",
  },
  {
    id: "C07",
    name: "Schedule Options",
    status: "PARTIAL",
    publicRoutes: ["features/scheduling/"],
    workspaceRows: ["ENG-WS-SCHEDULE"],
    helpEntryId: "ENG-WS-SCHEDULE",
    featureId: "scheduling",
    note: "Options are typed and bound to the authoritative schedule snapshot.",
  },
  {
    id: "C08",
    name: "Relationships",
    status: "PARTIAL",
    publicRoutes: ["features/scheduling/"],
    workspaceRows: ["ENG-WS-RELATIONSHIPS", "ENG-WS-GANTT-RELATIONSHIPS"],
    helpEntryId: "ENG-WS-RELATIONSHIPS",
    featureId: "scheduling",
    note: "Relationships are maintained on the activity grid and in the Gantt chart.",
  },
  {
    id: "C09",
    name: "CPM Engine",
    status: "IMPLEMENTED",
    publicRoutes: ["features/scheduling/"],
    workspaceRows: ["ENG-WS-SCHEDULE", "ENG-WS-CRITICAL-PATH"],
    helpEntryId: "ENG-WS-SCHEDULE",
    featureId: "scheduling",
    note: "Calculation runs in the shared scheduling core; the web layer only presents its result.",
  },
  {
    id: "C10",
    name: "Progress / Actuals",
    status: "PARTIAL",
    publicRoutes: ["features/project-controls/"],
    workspaceRows: ["ENG-WS-TRACKING"],
    helpEntryId: "ENG-WS-TRACKING",
    featureId: "project-controls",
    note: "Actuals are recorded through the tracking surface; history is persisted server-side.",
  },
  {
    id: "C11",
    name: "Baselines",
    status: "PARTIAL",
    publicRoutes: ["features/project-controls/"],
    workspaceRows: ["ENG-WS-BASELINES"],
    helpEntryId: "ENG-WS-BASELINES",
    featureId: "project-controls",
    note: "Baseline assignment persists per project; variance views stay inside the tracking surface.",
  },
  {
    id: "C12",
    name: "Resources / Assignments",
    status: "PARTIAL",
    publicRoutes: ["features/resources/"],
    workspaceRows: ["ENG-WS-RESOURCES", "ENG-WS-RESOURCE-USAGE"],
    helpEntryId: "ENG-WS-RESOURCES",
    featureId: "resources",
    note: "Resources, roles and assignments are one registry-backed surface.",
  },
  {
    id: "C13",
    name: "Cost / Financial Periods",
    status: "PARTIAL",
    publicRoutes: ["features/cost/", "pricing/"],
    workspaceRows: ["ENG-WS-EXPENSES"],
    helpEntryId: "ENG-WS-EXPENSES",
    featureId: "cost",
    note: "Expenses and cost accounts are persisted; financial periods remain a partial surface.",
  },
  {
    id: "C14",
    name: "EVM / Earned Schedule",
    status: "PARTIAL",
    publicRoutes: ["features/project-controls/"],
    workspaceRows: ["ENG-WS-TRACKING", "ENG-WS-USAGE-PROFILE"],
    helpEntryId: "ENG-WS-TRACKING",
    featureId: "project-controls",
    note: "Earned value reads the shared core's results; there is no parallel calculation in the web layer.",
  },
  {
    id: "C15",
    name: "Codes / Steps / Issues / Risks",
    status: "PARTIAL",
    publicRoutes: ["features/risks/"],
    workspaceRows: ["ENG-WS-RISKS", "ENG-WS-ISSUES", "ENG-WS-STEPS", "ENG-WS-ACTIVITY-CODES"],
    helpEntryId: "ENG-WS-RISKS",
    featureId: "risks",
    note: "Risk and issue registers, activity codes and steps are four documented surfaces behind one navigation area.",
  },
  {
    id: "C16",
    name: "Interchange",
    status: "PARTIAL",
    publicRoutes: ["integrations/"],
    workspaceRows: ["ENG-WS-EXCHANGE"],
    helpEntryId: "ENG-WS-EXCHANGE",
    featureId: null,
    note: "Import/export is available through the exchange surface; the public integration page describes it.",
  },
  {
    id: "C17",
    name: "Dashboard / Analytics",
    status: "PARTIAL",
    publicRoutes: ["platform/", "features/reporting/"],
    workspaceRows: ["ENG-WS-PORTFOLIOS", "ENT-DASHBOARDS"],
    helpEntryId: "ENT-DASHBOARDS",
    featureId: "portfolio-executive",
    note: "Portfolio views and dashboards are Enterprise surfaces; the shared feature index is their public entry.",
  },
  {
    id: "C18",
    name: "Charts",
    status: "PREVIEW",
    publicRoutes: ["features/reporting/"],
    workspaceRows: ["ENG-WS-GANTT", "ENG-WS-GANTT-BARS"],
    helpEntryId: "ENG-WS-GANTT",
    featureId: "reporting",
    note: "Gantt and profile charts render from the shared core's activity data.",
  },
  {
    id: "C19",
    name: "Reporting",
    status: "PREVIEW",
    publicRoutes: ["features/reporting/"],
    workspaceRows: ["ENG-WS-REPORTS", "ENT-REPORTS"],
    helpEntryId: "ENG-WS-REPORTS",
    featureId: "reporting",
    note: "Report definitions are persisted and printable; the web preview does not yet cover every report type.",
  },
  {
    id: "C20",
    name: "Forms",
    status: "PARTIAL",
    publicRoutes: ["features/"],
    workspaceRows: [],
    helpEntryId: null,
    featureId: null,
    note: "Form templates and submissions persist, but no dedicated public route ships; the feature index is the entry.",
  },
  {
    id: "C21",
    name: "Form Calculations",
    status: "PARTIAL",
    publicRoutes: ["features/"],
    workspaceRows: [],
    helpEntryId: null,
    featureId: null,
    note: "Formulas run through the shared calculation core; the feature index is the public entry.",
  },
  {
    id: "C22",
    name: "Workflow / Approvals",
    status: "PARTIAL",
    publicRoutes: ["features/"],
    workspaceRows: ["ENT-WORKFLOW", "ENT-FEEDBACK-APPROVAL"],
    helpEntryId: "ENT-WORKFLOW",
    featureId: "team-tasks",
    note: "Approval events persist; review workflow is documented on the Enterprise help baseline.",
  },
  {
    id: "C23",
    name: "PMBOK Layer",
    status: "PARTIAL",
    publicRoutes: ["platform/", "features/"],
    workspaceRows: [],
    helpEntryId: null,
    featureId: null,
    note: "PMBOK-aligned templates exist as contracts, not as a separate public product.",
  },
  {
    id: "C24",
    name: "AI Permissions",
    status: "PARTIAL",
    publicRoutes: ["features/ai-assistant/", "security/"],
    workspaceRows: ["ENG-WS-ADMIN"],
    helpEntryId: "ENG-WS-ADMIN",
    featureId: "ai-assistant",
    note: "AI actions pass an explicit action boundary; grants are administered with the other security settings.",
  },
  {
    id: "C25",
    name: "AI Project Bootstrap",
    status: "PARTIAL",
    publicRoutes: ["features/ai-assistant/"],
    workspaceRows: ["ENG-WS-PROJECTS"],
    helpEntryId: "ENG-WS-PROJECTS",
    featureId: "ai-assistant",
    note: "Bootstrap writes through the same project persistence as manual creation.",
  },
  {
    id: "C26",
    name: "AI Schedule Analysis",
    status: "PARTIAL",
    publicRoutes: ["features/ai-assistant/"],
    workspaceRows: ["ENG-WS-SCHEDULE"],
    helpEntryId: "ENG-WS-SCHEDULE",
    featureId: "ai-assistant",
    note: "Schedule analysis reads the shared core's snapshot; it never recalculates in the assistant.",
  },
  {
    id: "C27",
    name: "AI Document / Form Support",
    status: "PARTIAL",
    publicRoutes: ["features/ai-assistant/", "features/documents/"],
    workspaceRows: ["ENG-WS-DOCUMENTS"],
    helpEntryId: "ENG-WS-DOCUMENTS",
    featureId: "ai-assistant",
    note: "Documents and form drafts are handled through the document surface.",
  },
  {
    id: "C28",
    name: "AI Reliability",
    status: "PARTIAL",
    publicRoutes: ["features/ai-assistant/"],
    workspaceRows: [],
    helpEntryId: null,
    featureId: "ai-assistant",
    note: "Idempotency and revision guards are enforced in the action layer; no separate public surface.",
  },
  {
    id: "C29",
    name: "Localization",
    status: "PARTIAL",
    publicRoutes: [],
    workspaceRows: [],
    helpEntryId: null,
    featureId: null,
    note: "Site-wide: ten public locales are complete; the workspace UI is localized for English and Persian.",
  },
  {
    id: "C30",
    name: "RTL / Calendar / Fonts",
    status: "PARTIAL",
    publicRoutes: [],
    workspaceRows: [],
    helpEntryId: null,
    featureId: null,
    note: "Site-wide: direction, locale-aware dates and the Inter/Vazirmatn pairing ship on every page.",
  },
  {
    id: "C31",
    name: "Language Packs",
    status: "PARTIAL",
    publicRoutes: [],
    workspaceRows: [],
    helpEntryId: null,
    featureId: null,
    note: "Site-wide: the ten locale modules are the language packs for the public site.",
  },
  {
    id: "C32",
    name: "Help / Documentation",
    status: "PARTIAL",
    publicRoutes: ["documentation/", "help/", "faq/"],
    workspaceRows: [],
    helpEntryId: null,
    featureId: null,
    note: "Help and documentation index the same registries the assistant cites; neither page invent a topic.",
  },
  {
    id: "C33",
    name: "AI / Product Guide",
    status: "PARTIAL",
    publicRoutes: [],
    workspaceRows: [],
    helpEntryId: null,
    featureId: "ai-assistant",
    note: "Site-wide: the contextual assistant launcher runs on every page and resolves help per route.",
  },
  {
    id: "C34",
    name: "Security / Tenancy",
    status: "PARTIAL",
    publicRoutes: ["security/", "privacy/", "terms/"],
    workspaceRows: ["ENG-WS-ADMIN", "ENT-ORG-ACCESS"],
    helpEntryId: "ENG-WS-ADMIN",
    featureId: null,
    note: "Tenant isolation is enforced server-side; the public security page describes only shipped controls.",
  },
  {
    id: "C35",
    name: "Release / Quality",
    status: "PARTIAL",
    publicRoutes: ["platform/"],
    workspaceRows: [],
    helpEntryId: null,
    featureId: null,
    note: "CI covers typecheck, unit and PostgreSQL suites; the release gate is recorded in the PR chain note.",
  },
]);

export type PublicRoute = { id: string; path: string };
export type PublicFeature = { id: string; route: string; status: string };

export type PageInheritance = {
  route: string;
  capabilityIds: string[];
  help: ContextualHelp;
};

export type CapabilityMatrixRegistry = {
  schema: "cubi-capability-page-help-registry.v1";
  reconciliation: {
    engineeringPdfPages: number;
    engineeringPdfPagesMatched: number;
    officialTopics: number;
    officialTopicsReachable: number;
    checkedOn: string;
  };
  capabilities: Array<{
    id: string;
    name: string;
    status: CapabilityStatus;
    publicRoutes: string[];
    workspaceRows: string[];
    helpEntryId: string | null;
    featureId: string | null;
    note: string;
  }>;
  pages: Array<{
    route: string;
    capabilityIds: string[];
    help: {
      level: string;
      entryId: string | null;
      surface: string | null;
      topic: { source: string; title: string; url: string; pdfPage: number | null } | null;
      reason: string | null;
      featureId: string | null;
    };
  }>;
  evidenceGaps: Array<{ id: string; question: string; needed: string }>;
};

const PAGE_TRAILER = "/login/ and /app/ are boundaries, not indexable routes: the first is the\nsign-in entry and the second is the canonical workspace.";
const PRIVATE_ROUTES = ["login/", "app/"];

/** Help for one route, resolved exactly as the assistant resolves it. */
export function pageHelp(route: string): ContextualHelp {
  return resolveContextualHelp(`/${route}`);
}

export function pageInheritance(routes: readonly PublicRoute[]): PageInheritance[] {
  return routes.map((route) => ({
    route: route.path,
    capabilityIds: capabilityIdsForRoute(route.path),
    help: pageHelp(route.path),
  }));
}

export function capabilityIdsForRoute(route: string): string[] {
  const ids = CAPABILITY_INHERITANCE.filter((capability) => capability.publicRoutes.includes(route)).map(
    (capability) => capability.id,
  );
  return [...new Set([...ids, ...SITE_WIDE_CAPABILITIES])].sort((a, b) => a.localeCompare(b));
}

function escapeCell(value: string): string {
  return value.replace(/\|/g, "\\|").replace(/\n/g, " ");
}

function topicLabel(help: ContextualHelp): string {
  if (!help.topic) return "— (internal documentation)";
  const page = help.topic.pdfPage === null ? "" : `, p. ${help.topic.pdfPage}`;
  return `${help.topic.title}${page}`;
}

function entryLabel(help: ContextualHelp): string {
  if (help.entryId) return help.entryId;
  return "—";
}

function levelLabel(help: ContextualHelp): string {
  switch (help.level) {
    case "direct":
      return "direct";
    case "parent":
      return "parent";
    case "inherited":
      return "inherited";
    case "internal-docs":
      return "internal-docs";
  }
}

export function buildRegistry(
  routes: readonly PublicRoute[],
  features: readonly PublicFeature[],
): CapabilityMatrixRegistry {
  const pages = pageInheritance(routes).map((page) => ({
    route: page.route,
    capabilityIds: page.capabilityIds,
    help: {
      level: page.help.level,
      entryId: page.help.entryId,
      surface: page.help.surface,
      topic: page.help.topic,
      reason: page.help.reason,
      featureId: page.help.feature?.id ?? null,
    },
  }));
  return {
    schema: "cubi-capability-page-help-registry.v1",
    reconciliation: {
      engineeringPdfPages: 53,
      engineeringPdfPagesMatched: 53,
      officialTopics: 69,
      officialTopicsReachable: 69,
      checkedOn: "2026-11-20",
    },
    capabilities: CAPABILITY_INHERITANCE.map((capability) => ({
      id: capability.id,
      name: capability.name,
      status: capability.status,
      publicRoutes: [...capability.publicRoutes],
      workspaceRows: [...capability.workspaceRows],
      helpEntryId: capability.helpEntryId,
      featureId: capability.featureId,
      note: capability.note,
    })),
    pages,
    evidenceGaps: [
      {
        id: "C05",
        question:
          "Which CUBISITE capability owns the C05 slot between Grid/Layout (C04) and Calendar (C06)?",
        needed:
          "Row C05 of `/CUBISITE/cubisite.xlsx` v8 (sheet «ماتریس قابلیت‌ها»). Until it is supplied, C05 stays unnamed and uncited.",
      },
    ],
  };
}

export function renderMarkdown(
  routes: readonly PublicRoute[],
  features: readonly PublicFeature[],
): string {
  const registry = buildRegistry(routes, features);
  const lines: string[] = [];

  lines.push("# CUBISITE — capability, page and Help inheritance matrix (C01–C35)");
  lines.push("");
  lines.push(
    "This matrix is generated from the committed sources. It answers one question per identifier:",
  );
  lines.push(
    "which public pages may claim the capability, which workspace surface implements it, and which",
  );
  lines.push(
    "recorded Help topic — if any — constrains what the claim may say. Nothing here is authored by hand",
  );
  lines.push("beyond the C-number assignment; titles, URLs and page numbers come from the Help registry.");
  lines.push("");
  lines.push("## 1. Sources and the workbook gap");
  lines.push("");
  lines.push("| Source | Role |");
  lines.push("| --- | --- |");
  lines.push(
    "| `docs/cubisite/AUDIT_BASELINE_2026-11-20.md` | The accepted C01–C35 enumeration and status vocabulary. |",
  );
  lines.push(
    "| `docs/traceability/engineering-v26.json`, `enterprise-v26.json` | Official Help topics, PDF pages and executable evidence per surface (83 rows). |",
  );
  lines.push(
    "| `apps/web/site/routes.mjs` | The 25 approved public routes. |",
  );
  lines.push(
    "| `apps/web/site/capabilities.mjs` | The published feature contract (10 entries). |",
  );
  lines.push(
    "| `apps/web/src/help-registry.ts` | The resolver that turns a route into one of four Help levels. |",
  );
  lines.push("");
  lines.push(
    "The product owner's workbook, `/CUBISITE/cubisite.xlsx` v8, is the authority for the C-numbering.",
  );
  lines.push(
    "It is **not present** in this repository, in its history, or in the issue's attachments, so the",
  );
  lines.push(
    "enumeration in the audit baseline is used as-is. That is why C05 has no name: inventing one would",
  );
  lines.push("put a fabricated capability into the product contract.");
  lines.push("");
  lines.push("## 2. Inheritance rules");
  lines.push("");
  lines.push(
    "1. **direct** — the route (or the workspace menu on it) has its own traceability row with an official topic.",
  );
  lines.push(
    "2. **parent** — a deeper path without its own row inherits the nearest documented ancestor.",
  );
  lines.push(
    "3. **inherited** — a path under `/app/` or `/environments/` inherits the environment shell topic.",
  );
  lines.push(
    "4. **internal-docs** — no official topic exists; the assistant links to CUBI's own documentation and may say only the recorded reason.",
  );
  lines.push("");
  lines.push(
    "The same four levels are what the assistant renders, so this matrix and the live assistant cannot",
  );
  lines.push("disagree: both call `resolveContextualHelp`.");
  lines.push("");
  lines.push("## 3. Capabilities C01–C35");
  lines.push("");
  lines.push("| ID | Capability | Status | Public pages | Workspace surface | Help entry | Feature |");
  lines.push("| --- | --- | --- | --- | --- | --- | --- |");
  for (const capability of CAPABILITY_INHERITANCE) {
    const pages = capability.publicRoutes.length
      ? capability.publicRoutes.map((route) => `\`/${route}\``).join(", ")
      : SITE_WIDE_CAPABILITIES.includes(capability.id)
        ? "every published page"
        : "—";
    const rows = capability.workspaceRows.length
      ? capability.workspaceRows.map((id) => `\`${id}\``).join(", ")
      : "—";
    const help = capability.helpEntryId ? `\`${capability.helpEntryId}\`` : "—";
    const feature = capability.featureId ? `\`${capability.featureId}\`` : "—";
    lines.push(
      `| ${capability.id} | ${escapeCell(capability.name)} | ${capability.status} | ${pages} | ${rows} | ${help} | ${feature} |`,
    );
  }
  lines.push("");
  lines.push(
    "`C29`, `C30`, `C31` and `C33` are site-wide by nature: localization, direction and fonts, language",
  );
  lines.push(
    "packs and the contextual assistant apply to every published page, so they are listed once rather",
  );
  lines.push("than repeated in each page row.");
  lines.push("");
  lines.push("## 4. Page inheritance — the 25 public routes");
  lines.push("");
  lines.push("| Route | Capabilities | Help level | Entry | Official topic |");
  lines.push("| --- | --- | --- | --- | --- |");
  for (const page of registry.pages) {
    const help = {
      level: page.help.level as ContextualHelp["level"],
      entryId: page.help.entryId,
      surface: page.help.surface,
      topic: page.help.topic,
      reason: page.help.reason,
      feature: null,
    } as ContextualHelp;
    const topic = topicLabel(help);
    lines.push(
      `| \`/${page.route}\` | ${page.capabilityIds.join(", ") || "—"} | ${levelLabel(help)} | ${entryLabel(help)} | ${escapeCell(topic)} |`,
    );
  }
  lines.push("");
  lines.push("## 5. Boundaries");
  lines.push("");
  lines.push("| Route | Help level | Entry | Official topic |");
  lines.push("| --- | --- | --- | --- |");
  for (const route of PRIVATE_ROUTES) {
    const help = pageHelp(route);
    lines.push(
      `| \`/${route}\` | ${levelLabel(help)} | ${entryLabel(help)} | ${escapeCell(topicLabel(help))} |`,
    );
  }
  lines.push("");
  lines.push(PAGE_TRAILER);
  lines.push("");
  lines.push("## 6. C05 investigation");
  lines.push("");
  lines.push(
    "Every repository artefact was searched for `C05`: the audit baseline, the traceability registries,",
  );
  lines.push(
    "the capability contract, the crosswalks and the issue text. The only hit outside the audit is",
  );
  lines.push(
    "`docs/audits/JALAL4_TO_JALAL5_CROSSWALK_2026-10-18.md`, which maps a `C05` of a **different**",
  );
  lines.push(
    "numbering series (the Jalal crosswalk's C01–C09 covers commercial, contract and claims work) to",
  );
  lines.push(
    "J4-40. That series is not the CUBISITE C01–C35 series, so it cannot name the missing row.",
  );
  lines.push("");
  lines.push(
    "Conclusion: C05 is an **evidence gap in the source workbook**, not an implementation gap. It is",
  );
  lines.push(
    "carried as `MISSING_EVIDENCE` with no public page, no workspace surface and no Help topic, and it",
  );
  lines.push("is excluded from every page's capability list.");
  lines.push("");
  lines.push("## 7. PDF ↔ official HTML Help reconciliation");
  lines.push("");
  lines.push(
    "The Engineering baseline pairs each topic with a page of the 815-page V26 Help PDF. Both sides were",
  );
  lines.push("checked on 2026-11-20 against the supplied PDF and the live HTML Help:");
  lines.push("");
  lines.push("| Check | Result |");
  lines.push("| --- | --- |");
  lines.push(
    `| Engineering rows with a PDF page | ${registry.reconciliation.engineeringPdfPages} |`,
  );
  lines.push(
    `| PDF pages whose header or body carries the recorded topic title | ${registry.reconciliation.engineeringPdfPagesMatched} / ${registry.reconciliation.engineeringPdfPages} |`,
  );
  lines.push(
    `| Rows with an official HTML topic (Engineering + Enterprise) | ${registry.reconciliation.officialTopics} |`,
  );
  lines.push(
    `| Topics that answered HTTP 200 with the recorded title in the page | ${registry.reconciliation.officialTopicsReachable} / ${registry.reconciliation.officialTopics} |`,
  );
  lines.push("");
  lines.push(
    "Method: `pdftotext -f <page> -l <page> <pdf> -` per Engineering row, and a bounded `curl` per URL;",
  );
  lines.push(
    "titles were compared after lowercasing and stripping punctuation. No row needed a page correction,",
  );
  lines.push(
    "so the PDF page and the HTML topic in the registry refer to the same subject for every Engineering",
  );
  lines.push("row. Enterprise rows cite the HTML-only Enterprise baseline and carry no PDF page by design.");
  lines.push("");
  lines.push("## 8. Open gaps");
  lines.push("");
  lines.push("| Item | Status | Owner action |");
  lines.push("| --- | --- | --- |");
  lines.push(
    "| C05 name and definition | Blocked on source | Supply row C05 of the v8 workbook; the matrix will pick it up through `CAPABILITY_INHERITANCE`. |",
  );
  lines.push(
    "| C20–C23 public entry | Partial | Forms, calculations, workflow and PMBOK have no dedicated route; they inherit the feature index. |",
  );
  lines.push(
    "| C29 workspace localization | Partial | Workspace UI is English/Persian only; the ten locales cover the public site. |",
  );
  lines.push("");
  return `${lines.join("\n").replace(/\n+$/, "")}\n`;
}

export function renderRegistryJson(
  routes: readonly PublicRoute[],
  features: readonly PublicFeature[],
): string {
  return `${JSON.stringify(buildRegistry(routes, features), null, 2)}\n`;
}
