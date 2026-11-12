import type { ApiResult, ApiTransport, ProjectContext } from "./client.js";

/**
 * Project tracking read client.
 *
 * Tracking is a *read* of facts that the server already published: the
 * schedule FACT projection, persisted Activity Master rows and persisted
 * assignment facts. This module renders those values verbatim. It does not run
 * scheduling, leveling or money math, and it never fills a missing value with
 * an estimate.
 *
 * The response is versioned (`tracking-read-model.v1`) and every projection is
 * traceable to the schedule calculation run identity returned by the shared
 * scheduling core.
 */

export const TRACKING_API_VERSION = "tracking-read-model.v1";
export const TRACKING_SCALES = ["day", "week", "month"] as const;
export const TRACKING_SORTS = [
  "activity_id",
  "start",
  "finish",
  "total_float",
  "percent_complete",
  "status",
] as const;
export const TRACKING_DIRECTIONS = ["asc", "desc"] as const;
export const TRACKING_VIEWS = [
  "table",
  "bar-chart",
  "gantt-profile",
  "resource-analysis",
] as const;

export type TrackingScale = (typeof TRACKING_SCALES)[number];
export type TrackingSort = (typeof TRACKING_SORTS)[number];
export type TrackingDirection = (typeof TRACKING_DIRECTIONS)[number];
export type TrackingView = (typeof TRACKING_VIEWS)[number];

export type TrackingQuery = {
  scale: TrackingScale;
  groupBy: "wbs" | null;
  sort: TrackingSort;
  direction: TrackingDirection;
};

export const DEFAULT_TRACKING_QUERY: TrackingQuery = {
  scale: "week",
  groupBy: null,
  sort: "start",
  direction: "asc",
};

export type TrackingScope = {
  tenantId: string;
  projectId: string;
  projectRevision: number;
};

export type TrackingLayout = {
  scale: TrackingScale;
  groupBy: "wbs" | null;
  sort: TrackingSort;
  direction: TrackingDirection;
};

export type TrackingSource = {
  calculationRunIdentity: string | null;
  scheduleProjection: string;
  authoritative: boolean;
};

export type TrackingSummary = {
  activityCount: number;
  notStartedCount: number;
  inProgressCount: number;
  completedCount: number;
  criticalCount: number;
  projectFinish: string | null;
  meanPercentComplete: string | null;
  meanPercentBasis: string;
  diagnosticCount: number;
};

export type TrackingRow = {
  activityId: string;
  name: string;
  wbsId: string | null;
  wbsCode: string | null;
  status: string | null;
  percentComplete: string | null;
  start: string | null;
  finish: string | null;
  earlyStart: string | null;
  earlyFinish: string | null;
  lateStart: string | null;
  lateFinish: string | null;
  totalFloat: string | null;
  freeFloat: string | null;
  critical: boolean;
  floatPath: string | null;
  floatPathOrder: number | null;
  duration: string | null;
  plannedFinish: string | null;
  finishVarianceDays: number | null;
};

export type TrackingGroup = {
  group: string;
  activityCount: number;
  criticalCount: number;
  completedCount: number;
};

export type TrackingBarBucket = {
  bucket: string;
  total: number;
  notStarted: number;
  inProgress: number;
  completed: number;
  critical: number;
};

export type TrackingProfileBucket = {
  bucket: string;
  activityCount: number;
  duration: string | null;
};

export type TrackingResource = {
  resourceId: string;
  resourceName: string | null;
  resourceType: string | null;
  assignmentCount: number;
  activityCount: number;
  plannedUnits: string | null;
  actualUnits: string | null;
  remainingUnits: string | null;
  plannedCost: string | null;
  actualCost: string | null;
  remainingCost: string | null;
  currency: string | null;
};

export type TrackingResourceTotals = {
  plannedUnits: string | null;
  actualUnits: string | null;
  remainingUnits: string | null;
  plannedCost: string | null;
  actualCost: string | null;
  remainingCost: string | null;
};

export type TrackingResourceAnalysis =
  | {
      status: "available";
      basis: string;
      resources: TrackingResource[];
      totals: TrackingResourceTotals;
    }
  | {
      status: "unavailable";
      reason: string;
      resources: [];
      totals: null;
    };

export type TrackingWarning = {
  code: string;
  count: number | null;
  activityIds: string[];
};

export type TrackingRead = {
  contractVersion: typeof TRACKING_API_VERSION;
  scope: TrackingScope;
  layout: TrackingLayout;
  source: TrackingSource;
  summary: TrackingSummary;
  rows: TrackingRow[];
  groups: TrackingGroup[];
  barChart: TrackingBarBucket[];
  profile: TrackingProfileBucket[];
  resourceAnalysis: TrackingResourceAnalysis;
  warnings: TrackingWarning[];
};

export type TrackingPageOptions = {
  transport: ApiTransport;
  context: ProjectContext;
  locale: string;
};

function text(locale: string, en: string, fa: string): string {
  return locale.split("-")[0] === "fa" ? fa : en;
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function fail(code: string): never {
  throw new Error(code);
}

function localError(code: string): ApiResult<never> {
  return {
    ok: false,
    error: {
      code,
      retryable: false,
      message_key: "error.request.invalid",
      available_actions: [],
    },
  };
}

function requiredText(value: unknown, code: string): string {
  if (typeof value !== "string" || !value.trim()) fail(code);
  return value;
}

function optionalText(value: unknown, code: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string") fail(code);
  return value;
}

/** Numbers are rendered exactly as the server serialized them. */
function scalarText(value: unknown, code: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") {
    if (!Number.isFinite(value)) fail(code);
    return String(value);
  }
  if (typeof value === "string") return value;
  fail(code);
}

function requiredInteger(value: unknown, code: string, min = 0): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < min) fail(code);
  return value;
}

function optionalInteger(value: unknown, code: string): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== "number" || !Number.isInteger(value)) fail(code);
  return value;
}

function requiredBoolean(value: unknown, code: string): boolean {
  if (typeof value !== "boolean") fail(code);
  return value;
}

function scaleOf(value: unknown, code: string): TrackingScale {
  if (typeof value !== "string" || !TRACKING_SCALES.includes(value as TrackingScale)) {
    fail(code);
  }
  return value as TrackingScale;
}

function sortOf(value: unknown, code: string): TrackingSort {
  if (typeof value !== "string" || !TRACKING_SORTS.includes(value as TrackingSort)) {
    fail(code);
  }
  return value as TrackingSort;
}

function directionOf(value: unknown, code: string): TrackingDirection {
  if (
    typeof value !== "string" ||
    !TRACKING_DIRECTIONS.includes(value as TrackingDirection)
  ) {
    fail(code);
  }
  return value as TrackingDirection;
}

const INVALID = "INVALID_TRACKING_RESPONSE";

export function trackingPath(context: ProjectContext, query: TrackingQuery): string {
  const params = new URLSearchParams();
  params.set("scale", query.scale);
  if (query.groupBy) params.set("group_by", query.groupBy);
  params.set("sort", query.sort);
  params.set("direction", query.direction);
  return `/api/projects/${encodeURIComponent(context.project_id)}/tracking/read?${params.toString()}`;
}

function parseScope(value: unknown): TrackingScope {
  if (!isRecord(value)) fail(INVALID);
  return {
    tenantId: requiredText(value.tenant_id, INVALID),
    projectId: requiredText(value.project_id, INVALID),
    projectRevision: requiredInteger(value.project_revision, INVALID),
  };
}

function parseLayout(value: unknown): TrackingLayout {
  if (!isRecord(value)) fail(INVALID);
  const groupBy = value.group_by;
  if (groupBy !== null && groupBy !== undefined && groupBy !== "wbs") fail(INVALID);
  return {
    scale: scaleOf(value.scale, INVALID),
    groupBy: groupBy === "wbs" ? "wbs" : null,
    sort: sortOf(value.sort, INVALID),
    direction: directionOf(value.direction, INVALID),
  };
}

function parseSource(value: unknown): TrackingSource {
  if (!isRecord(value)) fail(INVALID);
  return {
    calculationRunIdentity: optionalText(value.calculation_run_identity, INVALID),
    scheduleProjection: requiredText(value.schedule_projection, INVALID),
    authoritative: value.authoritative === true ? true : fail(INVALID),
  };
}

function parseSummary(value: unknown): TrackingSummary {
  if (!isRecord(value)) fail(INVALID);
  return {
    activityCount: requiredInteger(value.activity_count, INVALID),
    notStartedCount: requiredInteger(value.not_started_count, INVALID),
    inProgressCount: requiredInteger(value.in_progress_count, INVALID),
    completedCount: requiredInteger(value.completed_count, INVALID),
    criticalCount: requiredInteger(value.critical_count, INVALID),
    projectFinish: optionalText(value.project_finish, INVALID),
    meanPercentComplete: scalarText(value.mean_percent_complete, INVALID),
    meanPercentBasis: requiredText(value.mean_percent_basis, INVALID),
    diagnosticCount: requiredInteger(value.diagnostic_count, INVALID),
  };
}

function parseRow(value: unknown): TrackingRow {
  if (!isRecord(value)) fail(INVALID);
  const critical = requiredBoolean(value.critical, INVALID);
  return {
    activityId: requiredText(value.activity_id, INVALID),
    name: typeof value.name === "string" ? value.name : fail(INVALID),
    wbsId: optionalText(value.wbs_id, INVALID),
    wbsCode: optionalText(value.wbs_code, INVALID),
    status: optionalText(value.status, INVALID),
    percentComplete: scalarText(value.percent_complete, INVALID),
    start: optionalText(value.start, INVALID),
    finish: optionalText(value.finish, INVALID),
    earlyStart: optionalText(value.early_start, INVALID),
    earlyFinish: optionalText(value.early_finish, INVALID),
    lateStart: optionalText(value.late_start, INVALID),
    lateFinish: optionalText(value.late_finish, INVALID),
    totalFloat: scalarText(value.total_float, INVALID),
    freeFloat: scalarText(value.free_float, INVALID),
    critical,
    floatPath: optionalText(value.float_path, INVALID),
    floatPathOrder: optionalInteger(value.float_path_order, INVALID),
    duration: scalarText(value.duration, INVALID),
    plannedFinish: optionalText(value.planned_finish, INVALID),
    finishVarianceDays: optionalInteger(value.finish_variance_days, INVALID),
  };
}

function parseGroups(value: unknown): TrackingGroup[] {
  if (!Array.isArray(value)) fail(INVALID);
  return value.map((entry) => {
    if (!isRecord(entry)) fail(INVALID);
    return {
      group: requiredText(entry.group, INVALID),
      activityCount: requiredInteger(entry.activity_count, INVALID),
      criticalCount: requiredInteger(entry.critical_count, INVALID),
      completedCount: requiredInteger(entry.completed_count, INVALID),
    };
  });
}

function parseBarChart(value: unknown): TrackingBarBucket[] {
  if (!Array.isArray(value)) fail(INVALID);
  return value.map((entry) => {
    if (!isRecord(entry)) fail(INVALID);
    const bucket = {
      bucket: requiredText(entry.bucket, INVALID),
      total: requiredInteger(entry.total, INVALID),
      notStarted: requiredInteger(entry.not_started, INVALID),
      inProgress: requiredInteger(entry.in_progress, INVALID),
      completed: requiredInteger(entry.completed, INVALID),
      critical: requiredInteger(entry.critical, INVALID),
    };
    if (bucket.notStarted + bucket.inProgress + bucket.completed > bucket.total) fail(INVALID);
    if (bucket.critical > bucket.total) fail(INVALID);
    return bucket;
  });
}

function parseProfile(value: unknown): TrackingProfileBucket[] {
  if (!Array.isArray(value)) fail(INVALID);
  return value.map((entry) => {
    if (!isRecord(entry)) fail(INVALID);
    return {
      bucket: requiredText(entry.bucket, INVALID),
      activityCount: requiredInteger(entry.activity_count, INVALID),
      duration: scalarText(entry.duration, INVALID),
    };
  });
}

function nullableTotals(value: unknown, code: string): TrackingResourceTotals {
  if (!isRecord(value)) fail(code);
  const fields = [
    "planned_units",
    "actual_units",
    "remaining_units",
    "planned_cost",
    "actual_cost",
    "remaining_cost",
  ] as const;
  // An available analysis always serializes every total, even when zero.
  for (const field of fields) if (!(field in value)) fail(code);
  return {
    plannedUnits: scalarText(value.planned_units, code),
    actualUnits: scalarText(value.actual_units, code),
    remainingUnits: scalarText(value.remaining_units, code),
    plannedCost: scalarText(value.planned_cost, code),
    actualCost: scalarText(value.actual_cost, code),
    remainingCost: scalarText(value.remaining_cost, code),
  };
}

function parseResourceAnalysis(value: unknown): TrackingResourceAnalysis {
  if (!isRecord(value)) fail(INVALID);
  if (value.status === "unavailable") {
    if (!Array.isArray(value.resources)) fail(INVALID);
    return {
      status: "unavailable",
      reason: requiredText(value.reason, INVALID),
      resources: [],
      totals: null,
    };
  }
  if (value.status !== "available") fail(INVALID);
  if (!Array.isArray(value.resources)) fail(INVALID);
  const resources = value.resources.map((entry) => {
    if (!isRecord(entry)) fail(INVALID);
    return {
      resourceId: requiredText(entry.resource_id, INVALID),
      resourceName: optionalText(entry.resource_name, INVALID),
      resourceType: optionalText(entry.resource_type, INVALID),
      assignmentCount: requiredInteger(entry.assignment_count, INVALID),
      activityCount: requiredInteger(entry.activity_count, INVALID),
      plannedUnits: scalarText(entry.planned_units, INVALID),
      actualUnits: scalarText(entry.actual_units, INVALID),
      remainingUnits: scalarText(entry.remaining_units, INVALID),
      plannedCost: scalarText(entry.planned_cost, INVALID),
      actualCost: scalarText(entry.actual_cost, INVALID),
      remainingCost: scalarText(entry.remaining_cost, INVALID),
      currency: optionalText(entry.currency, INVALID),
    };
  });
  return {
    status: "available",
    basis: requiredText(value.basis, INVALID),
    resources,
    totals: nullableTotals(value.totals, INVALID),
  };
}

function parseWarnings(value: unknown): TrackingWarning[] {
  if (!Array.isArray(value)) fail(INVALID);
  return value.map((entry) => {
    if (!isRecord(entry)) fail(INVALID);
    const activityIds = entry.activity_ids;
    if (
      activityIds !== undefined &&
      (!Array.isArray(activityIds) || activityIds.some((id) => typeof id !== "string"))
    ) {
      fail(INVALID);
    }
    return {
      code: requiredText(entry.code, INVALID),
      count: optionalInteger(entry.count, INVALID),
      activityIds: (activityIds as string[] | undefined) ?? [],
    };
  });
}

export function parseTrackingRead(value: unknown): TrackingRead {
  if (!isRecord(value)) fail(INVALID);
  if (value.contract_version !== TRACKING_API_VERSION) fail(INVALID);
  const scope = parseScope(value.scope);
  const layout = parseLayout(value.layout);
  const source = parseSource(value.source);
  const summary = parseSummary(value.summary);
  if (!Array.isArray(value.rows)) fail(INVALID);
  const rows = value.rows.map(parseRow);
  if (new Set(rows.map((row) => row.activityId)).size !== rows.length) fail(INVALID);
  if (summary.activityCount !== rows.length) fail(INVALID);
  const groups = parseGroups(value.groups);
  if (layout.groupBy === "wbs" && groups.length > 0) {
    const grouped = groups.reduce((total, group) => total + group.activityCount, 0);
    if (grouped !== rows.length) fail(INVALID);
  }
  return {
    contractVersion: TRACKING_API_VERSION,
    scope,
    layout,
    source,
    summary,
    rows,
    groups,
    barChart: parseBarChart(value.bar_chart),
    profile: parseProfile(value.profile),
    resourceAnalysis: parseResourceAnalysis(value.resource_analysis),
    warnings: parseWarnings(value.warnings),
  };
}

export async function loadTrackingRead(
  transport: ApiTransport,
  context: ProjectContext,
  query: TrackingQuery,
): Promise<ApiResult<TrackingRead>> {
  const result = await transport.get<unknown>(trackingPath(context, query), context);
  if (!result.ok) return result;
  try {
    return { ok: true, data: parseTrackingRead(result.data) };
  } catch {
    return localError(INVALID);
  }
}

type PageState = {
  status: "loading" | "loaded" | "error";
  errorCode: string | null;
  query: TrackingQuery;
  view: TrackingView;
  data: TrackingRead | null;
  request: number;
};

function dash(locale: string): string {
  return text(locale, "—", "—");
}

function display(value: string | null, locale: string): string {
  if (value === null || value.trim() === "") return dash(locale);
  return escapeHtml(value);
}

function viewLabel(view: TrackingView, locale: string): string {
  switch (view) {
    case "table":
      return text(locale, "Project Table", "جدول پروژه");
    case "bar-chart":
      return text(locale, "Project Bar Chart", "نمودار میله‌ای پروژه");
    case "gantt-profile":
      return text(locale, "Project Gantt / Profile", "گانت / منحنی پروژه");
    case "resource-analysis":
      return text(locale, "Resource Analysis", "تحلیل منابع");
  }
}

function errorMessage(code: string, locale: string): string {
  switch (code) {
    case "TRACKING_SCHEDULE_NOT_PUBLISHED":
      return text(
        locale,
        "No schedule has been published for this project. Run the schedule before reading tracking.",
        "هیچ زمان‌بندی‌ای برای این پروژه منتشر نشده است. پیش از خواندن رهگیری، زمان‌بندی را اجرا کنید.",
      );
    case "TRACKING_SCHEDULE_HAS_NO_ACTIVITIES":
      return text(
        locale,
        "The published schedule has no activities, so there is nothing to track.",
        "زمان‌بندی منتشرشده هیچ فعالیتی ندارد؛ بنابراین چیزی برای رهگیری وجود ندارد.",
      );
    case "CROSS_SCOPE_ACCESS":
    case "TRACKING_READ_NOT_AUTHORIZED":
      return text(
        locale,
        "You are not authorized to read tracking for this project.",
        "شما مجاز به خواندن رهگیری این پروژه نیستید.",
      );
    case "INVALID_TRACKING_RESPONSE":
      return text(
        locale,
        "The tracking response failed verification and was not displayed.",
        "پاسخ رهگیری در اعتبارسنجی رد شد و نمایش داده نشد.",
      );
    default:
      return text(
        locale,
        `Tracking could not be read (${code}).`,
        `خواندن رهگیری ناموفق بود (${code}).`,
      );
  }
}

export function mountWorkspaceTrackingPage(
  host: HTMLElement,
  options: TrackingPageOptions,
): void {
  if (host.dataset.trackingMounted === "true") return;
  host.dataset.trackingMounted = "true";
  const { transport, context, locale } = options;
  const state: PageState = {
    status: "loading",
    errorCode: null,
    query: { ...DEFAULT_TRACKING_QUERY },
    view: "table",
    data: null,
    request: 0,
  };

  const say = (en: string, fa: string): string => text(locale, en, fa);

  function renderSummary(data: TrackingRead): string {
    const s = data.summary;
    const stats: Array<[string, string, string]> = [
      [say("Activities", "فعالیت‌ها"), String(s.activityCount), "activity-count"],
      [say("Not Started", "شروع‌نشده"), String(s.notStartedCount), "not-started"],
      [say("In Progress", "در جریان"), String(s.inProgressCount), "in-progress"],
      [say("Completed", "تکمیل‌شده"), String(s.completedCount), "completed"],
      [say("Critical", "بحرانی"), String(s.criticalCount), "critical"],
      [say("Project Finish", "پایان پروژه"), display(s.projectFinish, locale), "project-finish"],
      [
        say("Mean % Complete", "% میانگین تکمیل"),
        display(s.meanPercentComplete, locale),
        "mean-percent",
      ],
      [say("Diagnostics", "عیب‌یابی‌ها"), String(s.diagnosticCount), "diagnostics"],
    ];
    return `<div class="cp-tracking-summary" data-tracking-summary>${stats
      .map(
        ([label, value, key]) =>
          `<div class="cp-tracking-stat" data-tracking-stat="${key}"><span>${escapeHtml(label)}</span><strong>${value}</strong></div>`,
      )
      .join("")}</div>`;
  }

  function renderTable(data: TrackingRead): string {
    const head = [
      say("Activity ID", "شناسه فعالیت"),
      say("Activity Name", "نام فعالیت"),
      say("WBS", "ساختار شکست"),
      say("Status", "وضعیت"),
      say("% Complete", "% تکمیل"),
      say("Start", "شروع"),
      say("Finish", "پایان"),
      say("Total Float", "شناوری کل"),
      say("Critical", "بحرانی"),
      say("Planned Finish", "پایان برنامه‌ای"),
      say("Variance (days)", "انحراف (روز)"),
    ]
      .map((label) => `<th scope="col">${escapeHtml(label)}</th>`)
      .join("");
    const groups = data.groups.length
      ? `<div class="cp-table-scroll cp-tracking-groups"><table class="cp-register-table" data-tracking-groups><caption>${escapeHtml(say("WBS groups", "گروه‌های ساختار شکست"))}</caption><thead><tr><th scope="col">${escapeHtml(say("Group", "گروه"))}</th><th scope="col">${escapeHtml(say("Activities", "فعالیت‌ها"))}</th><th scope="col">${escapeHtml(say("Completed", "تکمیل‌شده"))}</th><th scope="col">${escapeHtml(say("Critical", "بحرانی"))}</th></tr></thead><tbody>${data.groups
          .map(
            (group) =>
              `<tr data-tracking-group="${escapeHtml(group.group)}"><td>${escapeHtml(group.group)}</td><td>${group.activityCount}</td><td>${group.completedCount}</td><td>${group.criticalCount}</td></tr>`,
          )
          .join("")}</tbody></table></div>`
      : "";
    const body = data.rows
      .map(
        (row) =>
          `<tr data-tracking-row data-activity-id="${escapeHtml(row.activityId)}"${row.critical ? ' data-critical="true"' : ""}><td>${escapeHtml(row.activityId)}</td><td>${escapeHtml(row.name)}</td><td>${display(row.wbsCode, locale)}</td><td>${display(row.status, locale)}</td><td>${display(row.percentComplete, locale)}</td><td>${display(row.start, locale)}</td><td>${display(row.finish, locale)}</td><td>${display(row.totalFloat, locale)}</td><td>${row.critical ? escapeHtml(say("Yes", "بله")) : escapeHtml(say("No", "خیر"))}</td><td>${display(row.plannedFinish, locale)}</td><td>${display(row.finishVarianceDays === null ? null : String(row.finishVarianceDays), locale)}</td></tr>`,
      )
      .join("");
    return `${groups}<div class="cp-table-scroll"><table class="cp-register-table" data-tracking-table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
  }

  function renderBarChart(data: TrackingRead): string {
    if (!data.barChart.length) {
      return `<div class="cp-tracking-empty" data-tracking-empty>${escapeHtml(say("No activity has a published finish date, so no bar buckets can be drawn.", "هیچ فعالیتی تاریخ پایان منتشرشده ندارد؛ بنابراین میله‌ای برای ترسیم وجود ندارد."))}</div>`;
    }
    const max = Math.max(...data.barChart.map((bucket) => bucket.total), 1);
    const rows = data.barChart
      .map((bucket) => {
        const width = (count: number): string => `${(count / max) * 100}%`;
        return `<div class="cp-tracking-bar-row" data-tracking-bar="${escapeHtml(bucket.bucket)}"><span class="cp-tracking-bar-label">${escapeHtml(bucket.bucket)}</span><span class="cp-tracking-bar-track" role="img" aria-label="${escapeHtml(
          `${bucket.bucket}: ${bucket.total} ${say("activities", "فعالیت")}, ${bucket.completed} ${say("completed", "تکمیل‌شده")}, ${bucket.inProgress} ${say("in progress", "در جریان")}, ${bucket.notStarted} ${say("not started", "شروع‌نشده")}, ${bucket.critical} ${say("critical", "بحرانی")}`,
        )}"><span class="cp-tracking-bar-seg is-completed" style="width:${width(bucket.completed)}"></span><span class="cp-tracking-bar-seg is-progress" style="width:${width(bucket.inProgress)}"></span><span class="cp-tracking-bar-seg is-not-started" style="width:${width(bucket.notStarted)}"></span></span><span class="cp-tracking-bar-value">${bucket.total} · ${bucket.critical} ${escapeHtml(say("critical", "بحرانی"))}</span></div>`;
      })
      .join("");
    const legend = `<div class="cp-tracking-legend"><span class="cp-tracking-key is-completed"></span>${escapeHtml(say("Completed", "تکمیل‌شده"))}<span class="cp-tracking-key is-progress"></span>${escapeHtml(say("In Progress", "در جریان"))}<span class="cp-tracking-key is-not-started"></span>${escapeHtml(say("Not Started", "شروع‌نشده"))}</div>`;
    return `<div class="cp-tracking-bars" data-tracking-bars>${rows}</div>${legend}<p class="cp-tracking-hint">${escapeHtml(say("Buckets count activities by published finish date at the selected scale.", "هر بازه، فعالیت‌ها را بر پایه تاریخ پایان منتشرشده در مقیاس انتخاب‌شده می‌شمارد."))}</p>`;
  }

  function renderProfile(data: TrackingRead): string {
    if (!data.profile.length) {
      return `<div class="cp-tracking-empty" data-tracking-empty>${escapeHtml(say("No activity has a published start date, so the profile is empty.", "هیچ فعالیتی تاریخ شروع منتشرشده ندارد؛ بنابراین منحنی خالی است."))}</div>`;
    }
    const max = Math.max(...data.profile.map((bucket) => bucket.activityCount), 1);
    const bars = data.profile
      .map(
        (bucket) =>
          `<div class="cp-tracking-bar-row" data-tracking-profile="${escapeHtml(bucket.bucket)}"><span class="cp-tracking-bar-label">${escapeHtml(bucket.bucket)}</span><span class="cp-tracking-bar-track"><span class="cp-tracking-bar-seg is-profile" style="width:${(bucket.activityCount / max) * 100}%"></span></span><span class="cp-tracking-bar-value">${bucket.activityCount} · ${escapeHtml(say("duration", "مدت"))} ${display(bucket.duration, locale)}</span></div>`,
      )
      .join("");
    return `<div class="cp-tracking-bars" data-tracking-profile-bars>${bars}</div><p class="cp-tracking-hint">${escapeHtml(say("Profile buckets count activity starts and sum published durations per bucket.", "بازه‌های منحنی، شروع فعالیت‌ها را می‌شمارند و مدت‌های منتشرشده را جمع می‌زنند."))}</p>`;
  }

  function renderResources(data: TrackingRead): string {
    const analysis = data.resourceAnalysis;
    if (analysis.status === "unavailable") {
      return `<div class="cp-tracking-empty" data-tracking-resource-unavailable data-reason="${escapeHtml(analysis.reason)}">${escapeHtml(say("Resource assignments are not available for this project, so no resource totals are shown.", "تخصیص منابع برای این پروژه در دسترس نیست؛ بنابراین جمع منابع نمایش داده نمی‌شود."))} <code>${escapeHtml(analysis.reason)}</code></div>`;
    }
    if (!analysis.resources.length) {
      return `<div class="cp-tracking-empty" data-tracking-empty>${escapeHtml(say("No resource assignments are stored for this project.", "هیچ تخصیص منبعی برای این پروژه ذخیره نشده است."))}</div>`;
    }
    const head = [
      say("Resource", "منبع"),
      say("Type", "نوع"),
      say("Assignments", "تخصیص‌ها"),
      say("Activities", "فعالیت‌ها"),
      say("Planned Units", "واحد برنامه‌ای"),
      say("Actual Units", "واحد واقعی"),
      say("Remaining Units", "واحد باقی‌مانده"),
      say("Planned Cost", "هزینه برنامه‌ای"),
      say("Actual Cost", "هزینه واقعی"),
      say("Remaining Cost", "هزینه باقی‌مانده"),
      say("Currency", "ارز"),
    ]
      .map((label) => `<th scope="col">${escapeHtml(label)}</th>`)
      .join("");
    const body = analysis.resources
      .map(
        (resource) =>
          `<tr data-tracking-resource="${escapeHtml(resource.resourceId)}"><td>${escapeHtml(resource.resourceName ?? resource.resourceId)}</td><td>${display(resource.resourceType, locale)}</td><td>${resource.assignmentCount}</td><td>${resource.activityCount}</td><td>${display(resource.plannedUnits, locale)}</td><td>${display(resource.actualUnits, locale)}</td><td>${display(resource.remainingUnits, locale)}</td><td>${display(resource.plannedCost, locale)}</td><td>${display(resource.actualCost, locale)}</td><td>${display(resource.remainingCost, locale)}</td><td>${display(resource.currency, locale)}</td></tr>`,
      )
      .join("");
    const totals = analysis.totals;
    const totalsRow = `<tr data-tracking-resource-totals><th scope="row">${escapeHtml(say("Total", "جمع"))}</th><td></td><td></td><td></td><td>${display(totals.plannedUnits, locale)}</td><td>${display(totals.actualUnits, locale)}</td><td>${display(totals.remainingUnits, locale)}</td><td>${display(totals.plannedCost, locale)}</td><td>${display(totals.actualCost, locale)}</td><td>${display(totals.remainingCost, locale)}</td><td></td></tr>`;
    return `<div class="cp-table-scroll"><table class="cp-register-table" data-tracking-resource-table><caption>${escapeHtml(say("Persisted assignment facts", "واقعیت‌های تخصیص ذخیره‌شده"))}</caption><thead><tr>${head}</tr></thead><tbody>${body}${totalsRow}</tbody></table></div>`;
  }

  function renderWarnings(data: TrackingRead): string {
    if (!data.warnings.length) return "";
    return `<ul class="cp-tracking-warnings" data-tracking-warnings>${data.warnings
      .map(
        (warning) =>
          `<li data-tracking-warning="${escapeHtml(warning.code)}"><code>${escapeHtml(warning.code)}</code>${warning.count === null ? "" : ` · ${warning.count}`}${warning.activityIds.length ? ` · ${escapeHtml(warning.activityIds.join(", "))}` : ""}</li>`,
      )
      .join("")}</ul>`;
  }

  function renderPanel(data: TrackingRead): string {
    switch (state.view) {
      case "table":
        return renderTable(data);
      case "bar-chart":
        return renderBarChart(data);
      case "gantt-profile":
        return renderProfile(data);
      case "resource-analysis":
        return renderResources(data);
    }
  }

  function renderAside(data: TrackingRead): string {
    const identity = data.source.calculationRunIdentity;
    return `<aside><strong>${escapeHtml(say("Project", "پروژه"))}</strong><p data-tracking-project>${escapeHtml(data.scope.projectId)}</p><dl><dt>${escapeHtml(say("Revision", "نسخه"))}</dt><dd data-tracking-revision>${data.scope.projectRevision}</dd><dt>${escapeHtml(say("Tenant", "مستأجر"))}</dt><dd>${escapeHtml(data.scope.tenantId)}</dd><dt>${escapeHtml(say("Calculation run", "اجرای محاسبه"))}</dt><dd data-tracking-run title="${escapeHtml(identity ?? "")}">${identity ? escapeHtml(identity.slice(0, 12)) : display(null, locale)}</dd><dt>${escapeHtml(say("Projection", "تصویر داده"))}</dt><dd><code>${escapeHtml(data.source.scheduleProjection)}</code></dd></dl><p class="cp-tracking-hint">${escapeHtml(say("Read-only: every value is a stored schedule or assignment fact. This window never runs CPM or edits data.", "فقط‌خواندنی: همه مقادیر، واقعیت‌های ذخیره‌شده زمان‌بندی یا تخصیص هستند. این پنجره CPM اجرا نمی‌کند و داده‌ای را ویرایش نمی‌کند."))}</p></aside>`;
  }

  function render(): void {
    const data = state.data;
    let body = "";
    if (state.status === "loading") {
      body = `<div class="cp-tracking-empty" role="status">${escapeHtml(say("Reading published schedule and assignment facts…", "در حال خواندن واقعیت‌های منتشرشده زمان‌بندی و تخصیص…"))}</div>`;
    } else if (state.status === "error") {
      body = `<div class="cp-tracking-empty" role="alert" data-tracking-error="${escapeHtml(state.errorCode ?? "unknown")}">${escapeHtml(errorMessage(state.errorCode ?? "unknown", locale))}</div>`;
    } else if (data) {
      body = `<div class="cp-tracking-layout">${renderAside(data)}<section class="cp-tracking-chart" data-tracking-panel="${state.view}"><div class="cp-tracking-chart-head"><strong>${escapeHtml(viewLabel(state.view, locale))}</strong><span>${data.layout.scale} · ${data.layout.sort} ${data.layout.direction}</span></div>${renderPanel(data)}</section></div>${renderWarnings(data)}`;
    }
    const controls = `<div class="cp-tracking-toolbar"><strong>${escapeHtml(say("Tracking", "رهگیری"))}</strong><div class="cp-tracking-controls"><div class="cp-tracking-views" role="tablist" aria-label="${escapeHtml(say("Tracking layout", "چیدمان رهگیری"))}">${TRACKING_VIEWS.map(
      (view) =>
        `<button type="button" role="tab" data-tracking-view="${view}" aria-selected="${state.view === view}" class="${state.view === view ? "is-selected" : ""}">${escapeHtml(viewLabel(view, locale))}</button>`,
    ).join("")}</div><label>${escapeHtml(say("Scale", "مقیاس"))}<select name="tracking-scale">${TRACKING_SCALES.map((scale) => `<option value="${scale}" ${state.query.scale === scale ? "selected" : ""}>${escapeHtml(scale)}</option>`).join("")}</select></label><label>${escapeHtml(say("Group by", "گروه‌بندی بر"))}<select name="tracking-group"><option value="" ${state.query.groupBy === null ? "selected" : ""}>${escapeHtml(say("None", "هیچ"))}</option><option value="wbs" ${state.query.groupBy === "wbs" ? "selected" : ""}>WBS</option></select></label><label>${escapeHtml(say("Sort", "ترتیب"))}<select name="tracking-sort">${TRACKING_SORTS.map((sort) => `<option value="${sort}" ${state.query.sort === sort ? "selected" : ""}>${escapeHtml(sort)}</option>`).join("")}</select></label><label>${escapeHtml(say("Direction", "جهت"))}<select name="tracking-direction">${TRACKING_DIRECTIONS.map((direction) => `<option value="${direction}" ${state.query.direction === direction ? "selected" : ""}>${escapeHtml(direction)}</option>`).join("")}</select></label><button type="button" data-tracking-action="refresh" ${state.status === "loading" ? "disabled" : ""}>${escapeHtml(say("Refresh", "به‌روزرسانی"))}</button></div></div>`;
    const summary = state.status === "loaded" && data ? renderSummary(data) : "";
    host.innerHTML = `${controls}${summary}${body}`;
    host.dataset.trackingStatus = state.status;
  }

  async function reload(): Promise<void> {
    const request = ++state.request;
    state.status = "loading";
    state.errorCode = null;
    state.data = null;
    render();
    const result = await loadTrackingRead(transport, context, state.query);
    if (request !== state.request) return;
    if (!result.ok) {
      state.status = "error";
      state.errorCode = result.error.code;
      render();
      return;
    }
    state.status = "loaded";
    state.data = result.data;
    render();
  }

  host.addEventListener("click", (event) => {
    const target = event.target as HTMLElement;
    const view = target.closest<HTMLElement>("[data-tracking-view]")?.dataset.trackingView;
    if (view && (TRACKING_VIEWS as readonly string[]).includes(view)) {
      state.view = view as TrackingView;
      render();
      return;
    }
    if (target.closest("[data-tracking-action='refresh']")) {
      if (state.status !== "loading") void reload();
    }
  });

  host.addEventListener("change", (event) => {
    const target = event.target as HTMLSelectElement;
    switch (target.name) {
      case "tracking-scale":
        if (!(TRACKING_SCALES as readonly string[]).includes(target.value)) return;
        state.query.scale = target.value as TrackingScale;
        void reload();
        break;
      case "tracking-group":
        state.query.groupBy = target.value === "wbs" ? "wbs" : null;
        void reload();
        break;
      case "tracking-sort":
        if (!(TRACKING_SORTS as readonly string[]).includes(target.value)) return;
        state.query.sort = target.value as TrackingSort;
        void reload();
        break;
      case "tracking-direction":
        if (!(TRACKING_DIRECTIONS as readonly string[]).includes(target.value)) return;
        state.query.direction = target.value as TrackingDirection;
        void reload();
        break;
      default:
        break;
    }
  });

  void reload();
}
