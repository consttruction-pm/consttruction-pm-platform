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
  RiskRecord,
  WorkbenchCommandPlan,
  WorkbenchContext,
  WorkbenchStudio,
  WorkspaceReadSnapshot,
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

/** Count server rows for presentation; no ratio or forecast is derived. */
export function analysisCounts(snapshot: WorkspaceReadSnapshot | null): AnalysisCounts | null {
  if (!snapshot) return null;
  const activities = Array.isArray(snapshot.workspace.activities)
    ? snapshot.workspace.activities
    : [];
  const wbs = Array.isArray(snapshot.workspace.wbs) ? snapshot.workspace.wbs : [];
  const relationships = Array.isArray(snapshot.workspace.relationships)
    ? snapshot.workspace.relationships
    : [];
  const critical = activities.filter((activity) => {
    const gantt = (activity as { gantt?: { critical?: boolean } }).gantt;
    return gantt?.critical === true;
  }).length;
  return {
    activities: activities.length,
    wbs: wbs.length,
    relationships: relationships.length,
    critical,
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
