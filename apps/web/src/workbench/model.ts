/**
 * Pure presentation helpers for the CUBI AI Workbench.
 *
 * Nothing here calculates a schedule, a cost or an earned value. The helpers
 * only format server values, group server records for display, and decide which
 * honest state a panel is in (loading, empty, blocked, stale, forbidden).
 */
import {
  getWorkspaceIntlLocale,
  getWorkspaceLocaleDirection,
  translateWorkspaceUiText,
} from "../workspace-localization.js";
import type {
  AIActionProposal,
  RiskRecord,
  WorkbenchCommandPlan,
  WorkbenchContext,
  WorkbenchStudio,
  WorkspaceActivityRow,
  WorkspaceReadSnapshot,
  WorkspaceWbsNode,
} from "./api.js";

export const STUDIO_ORDER = [
  "import-staging",
  "schedule-scenario",
  "risk-analysis",
  "project-analysis",
  "decision-approval",
] as const;

export type StudioId = (typeof STUDIO_ORDER)[number];

const STUDIO_LABELS: Record<StudioId, [string, string]> = {
  "import-staging": ["Project Import Review & Staging", "بازبینی و آماده‌سازی ورود پروژه"],
  "schedule-scenario": ["Schedule Scenario Studio", "کارگاه سناریوی زمان‌بندی"],
  "risk-analysis": ["Risk Analysis Studio", "کارگاه تحلیل ریسک"],
  "project-analysis": ["Project Analysis Studio", "کارگاه تحلیل پروژه"],
  "decision-approval": ["Decision & Approval Workspace", "فضای تصمیم و تأیید"],
};

const STATUS_LABELS: Record<string, [string, string]> = {
  LIVE_VERIFIED: ["Live, verified", "فعال و تأییدشده"],
  WIRED_WRITE: ["Connected, read and write", "متصل، خواندن و نوشتن"],
  WIRED_READ: ["Connected, read only", "متصل، فقط خواندن"],
  PARTIAL: ["Partial", "جزئی"],
  SHELL_ONLY: ["Shell only", "فقط پوسته"],
  PLANNED: ["Planned", "برنامه‌ریزی‌شده"],
  BLOCKED: ["Blocked", "مسدود"],
  HELP_REFERENCE_PENDING: ["Help reference pending", "مرجع راهنما در انتظار"],
};

export function t(locale: string, english: string, persian: string): string {
  return translateWorkspaceUiText(locale, english, persian);
}

export function direction(locale: string): "ltr" | "rtl" {
  return getWorkspaceLocaleDirection(locale);
}

export function intlLocale(locale: string): string {
  return getWorkspaceIntlLocale(locale);
}

export function escapeHtml(value: unknown): string {
  const text = value === null || value === undefined ? "" : String(value);
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function formatNumber(locale: string, value: number): string {
  return new Intl.NumberFormat(intlLocale(locale), { maximumFractionDigits: 2 }).format(value);
}

export function formatDate(locale: string, value: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value.length <= 10 ? `${value}T00:00:00Z` : value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat(intlLocale(locale), {
    year: "numeric",
    month: "short",
    day: "2-digit",
    timeZone: "UTC",
  }).format(parsed);
}

export function formatDateTime(locale: string, value: string | null): string {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat(intlLocale(locale), {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}

export function studioLabel(locale: string, id: string): string {
  const entry = STUDIO_LABELS[id as StudioId];
  if (!entry) return id;
  return t(locale, entry[0], entry[1]);
}

export function statusLabel(locale: string, status: string): string {
  const entry = STATUS_LABELS[status];
  if (!entry) return status;
  return t(locale, entry[0], entry[1]);
}

export function statusTone(status: string): string {
  switch (status) {
    case "LIVE_VERIFIED":
    case "WIRED_WRITE":
      return "is-live";
    case "WIRED_READ":
      return "is-read";
    case "PARTIAL":
      return "is-partial";
    case "BLOCKED":
      return "is-blocked";
    default:
      return "is-planned";
  }
}

const PROPOSAL_STATUS_LABELS: Record<string, [string, string]> = {
  proposed: ["Awaiting a decision", "در انتظار تصمیم"],
  approved: ["Approved", "تأییدشده"],
  rejected: ["Rejected", "ردشده"],
  executing: ["Executing", "در حال اجرا"],
  executed: ["Executed", "اجراشده"],
  failed: ["Execution failed", "اجرا ناموفق"],
  stale: ["Stale", "کهنه"],
};

export function proposalStatusLabel(locale: string, status: string): string {
  const entry = PROPOSAL_STATUS_LABELS[status.toLowerCase()];
  if (!entry) return status;
  return t(locale, entry[0], entry[1]);
}

export function proposalStatusTone(status: string): string {
  switch (status.toLowerCase()) {
    case "executed":
      return "is-live";
    case "approved":
      return "is-read";
    case "proposed":
      return "is-partial";
    case "rejected":
    case "failed":
      return "is-blocked";
    default:
      return "is-planned";
  }
}

export function studioById(
  context: WorkbenchContext | null,
  id: string,
): WorkbenchStudio | null {
  return context?.studios.find((studio) => studio.id === id) ?? null;
}

export type PlanAction = {
  openStudio: StudioId | null;
  blocked: boolean;
  question: { id: string; prompt: string; options: { value: string; label: string }[] } | null;
};

/**
 * Decide what the command panel may do next. A plan never opens a studio the
 * server marked BLOCKED, and an unresolved command never guesses a studio.
 */
export function planAction(plan: WorkbenchCommandPlan): PlanAction {
  const studioId = plan.studio as StudioId | null;
  const question = plan.questions.length > 0 ? plan.questions[0] : null;
  return {
    openStudio: plan.can_open && studioId ? studioId : null,
    blocked: plan.refusal === "STUDIO_BLOCKED" || plan.can_open === false && Boolean(studioId),
    question,
  };
}

export type RiskMatrixCell = {
  probability: number;
  impact: number;
  risks: RiskRecord[];
};

/** Group stored risks into a 5×5 matrix without changing any rating. */
export function riskMatrix(risks: readonly RiskRecord[], size = 5): RiskMatrixCell[] {
  const cells: RiskMatrixCell[] = [];
  for (let probability = size; probability >= 1; probability -= 1) {
    for (let impact = 1; impact <= size; impact += 1) {
      cells.push({
        probability,
        impact,
        risks: risks.filter(
          (risk) => risk.probability === probability && risk.impact === impact,
        ),
      });
    }
  }
  return cells;
}

export type AnalysisCounts = {
  activities: number;
  wbs: number;
  relationships: number;
  critical: number;
};

/**
 * Only a recorded official reference may become a link. The server supplies the
 * URL; the client still refuses any other origin or scheme before rendering it.
 */
export function verifiedHelpUrl(value: unknown): string | null {
  return typeof value === "string" && value.startsWith("https://docs.oracle.com/")
    ? value
    : null;
}

/**
 * The canonical v2 read names the hierarchy `wbs_nodes`. An older envelope used
 * `wbs`; reading both keeps the stored rows visible instead of silently showing
 * zero WBS elements.
 */
export function workspaceWbsNodes(
  snapshot: WorkspaceReadSnapshot | null,
): readonly WorkspaceWbsNode[] {
  if (!snapshot) return [];
  if (Array.isArray(snapshot.workspace.wbs_nodes)) return snapshot.workspace.wbs_nodes;
  return Array.isArray(snapshot.workspace.wbs) ? snapshot.workspace.wbs : [];
}

/** Count server rows for presentation; no ratio or forecast is derived. */
export function analysisCounts(snapshot: WorkspaceReadSnapshot | null): AnalysisCounts | null {
  if (!snapshot) return null;
  const activities = Array.isArray(snapshot.workspace.activities)
    ? snapshot.workspace.activities
    : [];
  const relationships = Array.isArray(snapshot.workspace.relationships)
    ? snapshot.workspace.relationships
    : [];
  const critical = activities.filter((activity) => activity.gantt?.critical === true).length;
  return {
    activities: activities.length,
    wbs: workspaceWbsNodes(snapshot).length,
    relationships: relationships.length,
    critical,
  };
}

export type ActivityProposalWarning =
  | "CURRENT_STATE_UNAVAILABLE"
  | "ACTIVITY_ID_EXISTS"
  | "WBS_NOT_IN_CURRENT_READ";

export type ActivityProposalImpact = {
  kind: "activity.create";
  activityId: string;
  proposed: {
    name: string;
    duration: string;
    unit: string;
    wbsId: string;
    wbsLabel: string | null;
  };
  exists: boolean;
  current: {
    name: string;
    wbsId: string;
    wbsLabel: string;
    duration: string | null;
  } | null;
  warnings: readonly ActivityProposalWarning[];
};

function text(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function wbsDisplay(node: WorkspaceWbsNode | null): string | null {
  if (!node) return null;
  const code = text(node.local_code) ?? text(node.code);
  const label = [code, text(node.name)].filter(Boolean).join(" ");
  return label || text(node.wbs_id);
}

function activityDuration(row: WorkspaceActivityRow): string | null {
  const value = row.cells?.duration;
  return typeof value === "string" || typeof value === "number" ? String(value) : null;
}

/**
 * Compare one `activity.create` proposal payload with the canonical current
 * workspace read. This is a literal record lookup; it never schedules, costs or
 * forecasts. A different tool returns null because no generic preview exists.
 */
export function proposalImpact(
  snapshot: WorkspaceReadSnapshot | null,
  proposal: AIActionProposal,
): ActivityProposalImpact | null {
  if (proposal.tool_name !== "activity.create") return null;
  const payload = proposal.payload;
  const activityId = text(payload.activity_id);
  const name = text(payload.name);
  const wbsId = text(payload.wbs_id);
  const unit = text(payload.duration_unit);
  const duration =
    typeof payload.duration_value === "string" || typeof payload.duration_value === "number"
      ? String(payload.duration_value)
      : null;
  if (!activityId || !name || !wbsId || !unit || duration === null) return null;

  const warnings: ActivityProposalWarning[] = [];
  if (!snapshot) {
    return {
      kind: "activity.create",
      activityId,
      proposed: { name, duration, unit, wbsId, wbsLabel: null },
      exists: false,
      current: null,
      warnings: ["CURRENT_STATE_UNAVAILABLE"],
    };
  }
  const nodes = workspaceWbsNodes(snapshot);
  const node = nodes.find((item) => item.wbs_id === wbsId) ?? null;
  const existing =
    (snapshot.workspace.activities ?? []).find((item) => item.id === activityId) ?? null;
  if (!node) warnings.push("WBS_NOT_IN_CURRENT_READ");
  if (existing) warnings.push("ACTIVITY_ID_EXISTS");
  const currentWbsNode = existing
    ? nodes.find((item) => item.wbs_id === existing.wbs_id) ?? null
    : null;
  return {
    kind: "activity.create",
    activityId,
    proposed: { name, duration, unit, wbsId, wbsLabel: wbsDisplay(node) },
    exists: Boolean(existing),
    current: existing
      ? {
          name: text(existing.name) ?? existing.id,
          wbsId: text(existing.wbs_id) ?? "",
          wbsLabel: wbsDisplay(currentWbsNode) ?? text(existing.wbs_id) ?? "—",
          duration: activityDuration(existing),
        }
      : null,
    warnings,
  };
}

export type MetricRow = {
  key: string;
  label: string;
  value: number;
};

/** Present stored control-intelligence metrics without renaming their meaning. */
export function metricRows(snapshot: WorkspaceReadSnapshot | null): MetricRow[] {
  const metrics = snapshot?.control_intelligence?.metrics;
  if (!metrics || typeof metrics !== "object") return [];
  return Object.entries(metrics)
    .filter(([, value]) => typeof value === "number" && Number.isFinite(value))
    .map(([key, value]) => ({
      key,
      label: key.replace(/[_.]+/g, " ").replace(/\b\w/g, (character) => character.toUpperCase()),
      value,
    }))
    .sort((left, right) => left.key.localeCompare(right.key));
}

export function metricSourceSummary(snapshot: WorkspaceReadSnapshot | null): string[] {
  const refs = snapshot?.control_intelligence?.source_refs ?? [];
  const labels = refs
    .map((ref) => ref.label || ref.id || ref.kind || "")
    .filter((label) => label.trim().length > 0);
  return [...new Set(labels)];
}

export function readQuery(query: string, name: string): string | null {
  return new URLSearchParams(query).get(name);
}

export function withProject(url: string, projectId: string): string {
  const parsed = new URL(url, "http://workbench.invalid");
  parsed.searchParams.set("project", projectId);
  return `${parsed.pathname}${parsed.search}`;
}

export function isWritable(context: WorkbenchContext | null): boolean {
  return Boolean(context?.permissions.can_propose);
}

export function riskFormDefaults(): {
  category: string;
  status: string;
  response_strategy: string;
  probability: number;
  impact: number;
} {
  return {
    category: "schedule",
    status: "open",
    response_strategy: "mitigate",
    probability: 3,
    impact: 3,
  };
}
