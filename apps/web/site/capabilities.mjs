// Canonical public capability catalog.
//
// This file is the single source for the machine-readable capability contract
// served as `/capabilities.json`. Every entry must point at:
//   - a published public route,
//   - executable evidence in the repository,
//   - a row in `docs/traceability/*-v26.json` whose status matches.
//
// `apps/web/scripts/generate-capability-catalog.mjs` verifies all three and
// writes the JSON artifact; `apps/web/src/capability-catalog.test.ts` enforces
// the same rules on the committed output. The catalog carries no live project
// data and never duplicates runtime storage.

export const CAPABILITIES = [
  {
    id: "scheduling",
    environment: "engineering",
    route: "features/scheduling/",
    traceabilityId: "ENG-PUB-FEATURES-SCHEDULING",
    evidence: ["apps/web/public/features/scheduling/index.html", "apps/web/src/workspace-administration.test.ts"],
    status: "IMPLEMENTED",
  },
  {
    id: "project-controls",
    environment: "engineering",
    route: "features/project-controls/",
    traceabilityId: "ENG-PUB-FEATURES-PROJECT-CONTROLS",
    evidence: ["apps/web/public/features/project-controls/index.html", "apps/web/src/workspace-view.test.ts"],
    status: "IMPLEMENTED",
  },
  {
    id: "resources",
    environment: "engineering",
    route: "features/resources/",
    traceabilityId: "ENG-PUB-FEATURES-RESOURCES",
    evidence: ["apps/web/public/features/resources/index.html", "apps/web/src/workspace-assignments.test.ts"],
    status: "IMPLEMENTED",
  },
  {
    id: "cost",
    environment: "engineering",
    route: "features/cost/",
    traceabilityId: "ENG-PUB-FEATURES-COST",
    evidence: ["apps/web/public/features/cost/index.html", "apps/web/src/p6-capacity-panel.test.ts"],
    status: "PARTIAL",
  },
  {
    id: "documents",
    environment: "engineering",
    route: "features/documents/",
    traceabilityId: "ENG-PUB-FEATURES-DOCUMENTS",
    evidence: ["apps/web/public/features/documents/index.html", "apps/web/src/workspace-activity-details.test.ts"],
    status: "PARTIAL",
  },
  {
    id: "risks",
    environment: "engineering",
    route: "features/risks/",
    traceabilityId: "ENG-PUB-FEATURES-RISKS",
    evidence: ["apps/web/public/features/risks/index.html", "apps/web/src/workspace-view.test.ts"],
    status: "PARTIAL",
  },
  {
    id: "reporting",
    environment: "engineering",
    route: "features/reporting/",
    traceabilityId: "ENG-PUB-FEATURES-REPORTING",
    evidence: [
      "apps/web/public/features/reporting/index.html",
      "apps/web/src/p6-report-print-field-selection.test.ts",
    ],
    status: "PARTIAL",
  },
  {
    id: "ai-assistant",
    environment: "engineering",
    route: "features/ai-assistant/",
    traceabilityId: "ENG-PUB-FEATURES-AI-ASSISTANT",
    evidence: ["apps/web/public/features/ai-assistant/index.html", "apps/web/src/landing.ts"],
    status: "CUBI_OWNED",
  },
  {
    id: "team-tasks",
    environment: "enterprise",
    route: "features/",
    traceabilityId: "ENT-TEAM-TASKS",
    evidence: ["apps/web/src/enterprise-task-center.test.ts", "src/construction_pm/enterprise_task_http.py"],
    status: "IMPLEMENTED",
    routeNote: "Enterprise capability; the shared feature index is the public entry until an Enterprise marketing route ships.",
  },
  {
    id: "portfolio-executive",
    environment: "enterprise",
    route: "features/",
    traceabilityId: "ENT-PORTFOLIO",
    evidence: ["src/construction_pm/enterprise_dashboard.py", "src/construction_pm/enterprise_dashboard_application.py"],
    status: "PARTIAL",
    routeNote: "Enterprise capability; the shared feature index is the public entry until an Enterprise marketing route ships.",
  },
];

// Public commercial offer. The price is not authored here: the generator reads
// the authoritative TypeScript constant and fails if this value drifts.
export const PUBLIC_OFFER = {
  plan: "pro_monthly",
  currency: "USD",
  unitPriceMinor: 999,
  priceSource: "apps/web/src/pro-checkout.ts",
  checkoutRoute: "pricing/",
};

export const CONTRACT_VERSION = "cubi-public-capabilities.v1";
