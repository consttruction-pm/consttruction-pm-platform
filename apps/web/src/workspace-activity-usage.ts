import type { AssignmentPeriod } from "./workspace-assignments.js";
import { addDecimalText } from "./workspace-assignments.js";

export const ACTIVITY_USAGE_STORAGE_KEY = "cubi:workspace:activity-usage";

export type ActivityUsageMetric = "units" | "cost";
export type ActivityUsageScope = "all" | "selected";
export type ActivityUsageView = "spreadsheet" | "profile";

export type ActivityUsagePrefs = {
  metric: ActivityUsageMetric;
  scope: ActivityUsageScope;
};

export type ActivityUsageSource = {
  status: "loading" | "loaded" | "error";
  errorCode: string | null;
  /** Persisted assignment periods read from the resource read API. */
  periods: readonly AssignmentPeriod[];
};

export type ActivityUsageActivity = {
  id: string;
  code: string;
  name: string;
};

export type ActivityUsageCell = {
  periodStart: string;
  value: string | null;
};

export type ActivityUsageRow = {
  activityId: string;
  label: string;
  code: string | null;
  name: string | null;
  values: readonly ActivityUsageCell[];
  total: string | null;
};

export type ActivityUsageSpreadsheetModel = {
  metric: ActivityUsageMetric;
  scope: ActivityUsageScope;
  /** Sorted unique stored period starts; the timescaled columns. */
  periods: readonly string[];
  rows: readonly ActivityUsageRow[];
  periodTotals: readonly ActivityUsageCell[];
  grandTotal: string | null;
  /** Every stored period for the project, before the scope filter. */
  storedPeriodCount: number;
  storedActivityCount: number;
};

export type ActivityUsageProfileModel = {
  points: readonly ActivityUsageCell[];
  total: string | null;
  peak: string | null;
};

export type ActivityUsageRenderOptions = {
  view: ActivityUsageView;
  source: ActivityUsageSource;
  activities: readonly ActivityUsageActivity[];
  selectedIds: readonly string[];
  locale: string;
  prefs: ActivityUsagePrefs;
};

export const ACTIVITY_USAGE_DEFAULT_PREFS: ActivityUsagePrefs = { metric: "units", scope: "all" };

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

export function normalizeActivityUsagePrefs(input: unknown): ActivityUsagePrefs {
  if (!isRecord(input)) return { ...ACTIVITY_USAGE_DEFAULT_PREFS };
  return {
    metric: input.metric === "cost" ? "cost" : "units",
    scope: input.scope === "selected" ? "selected" : "all",
  };
}

export function activityUsageStorageKey(context: { tenant_id?: string | null; project_id: string }): string {
  // Presentation-only preference, scoped to tenant and project so one plan's
  // chosen metric never changes another plan's usage view.
  return [
    ACTIVITY_USAGE_STORAGE_KEY,
    encodeURIComponent(context.tenant_id ?? ""),
    encodeURIComponent(context.project_id),
  ].join(":");
}

export function readActivityUsagePrefs(
  storage: Pick<Storage, "getItem"> | null,
  context: { tenant_id?: string | null; project_id: string },
): ActivityUsagePrefs {
  if (!storage) return { ...ACTIVITY_USAGE_DEFAULT_PREFS };
  try {
    const raw = storage.getItem(activityUsageStorageKey(context));
    if (!raw) return { ...ACTIVITY_USAGE_DEFAULT_PREFS };
    return normalizeActivityUsagePrefs(JSON.parse(raw) as unknown);
  } catch {
    return { ...ACTIVITY_USAGE_DEFAULT_PREFS };
  }
}

export function storeActivityUsagePrefs(
  storage: Pick<Storage, "setItem"> | null,
  context: { tenant_id?: string | null; project_id: string },
  prefs: ActivityUsagePrefs,
): ActivityUsagePrefs {
  const normalized = normalizeActivityUsagePrefs(prefs);
  if (!storage) return normalized;
  try {
    storage.setItem(activityUsageStorageKey(context), JSON.stringify(normalized));
  } catch {
    // A blocked storage quota must not break the view.
  }
  return normalized;
}

function activityLabel(activity: ActivityUsageActivity | undefined, id: string): string {
  if (!activity) return id;
  const parts = [activity.code, activity.name].filter((part) => part.trim() !== "");
  return parts.length ? parts.join(" ") : id;
}

/**
 * Projects the persisted assignment periods into the Activity Usage
 * Spreadsheet shape: one row per activity with stored periods, one column per
 * stored period start, and exact decimal sums across assignments. No value is
 * derived from activity dates or spread across days.
 */
export function buildActivityUsageSpreadsheet(input: {
  periods: readonly AssignmentPeriod[];
  activities: readonly ActivityUsageActivity[];
  metric: ActivityUsageMetric;
  scope: ActivityUsageScope;
  selectedIds?: readonly string[];
}): ActivityUsageSpreadsheetModel {
  const metric = input.metric === "cost" ? "cost" : "units";
  const scope = input.scope === "selected" ? "selected" : "all";
  const activityById = new Map(input.activities.map((activity) => [activity.id, activity]));
  const storedActivityIds = new Set(input.periods.map((period) => period.activityId));
  const selected = new Set(input.selectedIds ?? []);
  const scoped = scope === "selected"
    ? input.periods.filter((period) => selected.has(period.activityId))
    : input.periods;

  const periods = [...new Set(scoped.map((period) => period.periodStart))].sort((a, b) => a.localeCompare(b));
  const activityIds = [...new Set(scoped.map((period) => period.activityId))];
  const order = new Map(input.activities.map((activity, index) => [activity.id, index]));
  activityIds.sort((a, b) => {
    const left = order.get(a);
    const right = order.get(b);
    if (left !== undefined && right !== undefined) return left - right;
    if (left !== undefined) return -1;
    if (right !== undefined) return 1;
    return a.localeCompare(b, "en", { numeric: true });
  });

  const rows: ActivityUsageRow[] = activityIds.map((activityId) => {
    const activityPeriods = scoped.filter((period) => period.activityId === activityId);
    const values = periods.map((periodStart) => {
      const value = addDecimalText(
        activityPeriods
          .filter((period) => period.periodStart === periodStart)
          .map((period) => (metric === "units" ? period.units : period.cost)),
      );
      return { periodStart, value };
    });
    const activity = activityById.get(activityId);
    return {
      activityId,
      label: activityLabel(activity, activityId),
      code: activity ? activity.code : null,
      name: activity ? activity.name : null,
      values,
      total: addDecimalText(values.map((cell) => cell.value)),
    };
  });

  const periodTotals = periods.map((periodStart) => ({
    periodStart,
    value: addDecimalText(
      rows.map((row) => row.values.find((cell) => cell.periodStart === periodStart)?.value ?? null),
    ),
  }));

  return {
    metric,
    scope,
    periods,
    rows,
    periodTotals,
    grandTotal: addDecimalText(rows.map((row) => row.total)),
    storedPeriodCount: input.periods.length,
    storedActivityCount: storedActivityIds.size,
  };
}

/** Aggregates the same stored facts into one bar per period. */
export function buildActivityUsageProfile(model: ActivityUsageSpreadsheetModel): ActivityUsageProfileModel {
  const points = model.periodTotals.map((cell) => ({ periodStart: cell.periodStart, value: cell.value }));
  const peak = points.reduce<string | null>((max, point) => {
    if (point.value === null) return max;
    if (max === null) return point.value;
    return Number.parseFloat(point.value) > Number.parseFloat(max) ? point.value : max;
  }, null);
  return { points, total: model.grandTotal, peak };
}

function periodLabel(periodStart: string): string {
  return periodStart.length === 10 ? periodStart.slice(5) : periodStart;
}

function renderControls(
  locale: string,
  prefs: ActivityUsagePrefs,
  storedPeriodCount: number,
): string {
  const metricOptions = (["units", "cost"] as const)
    .map((metric) => `<option value="${metric}"${prefs.metric === metric ? " selected" : ""}>${escapeHtml(metric === "units" ? text(locale, "Units", "واحدها") : text(locale, "Cost", "هزینه"))}</option>`)
    .join("");
  const scopeOptions = (["all", "selected"] as const)
    .map((scope) => `<option value="${scope}"${prefs.scope === scope ? " selected" : ""}>${escapeHtml(scope === "all" ? text(locale, "All activities", "همهٔ فعالیت‌ها") : text(locale, "Selected activities", "فعالیت‌های انتخاب‌شده"))}</option>`)
    .join("");
  return `<div class="cp-usage-controls">
    <label>${escapeHtml(text(locale, "Show", "نمایش"))} <select data-usage-metric aria-label="${escapeHtml(text(locale, "Usage value", "مقدار مصرف"))}">${metricOptions}</select></label>
    <label>${escapeHtml(text(locale, "Activities", "فعالیت‌ها"))} <select data-usage-scope aria-label="${escapeHtml(text(locale, "Activity scope", "دامنهٔ فعالیت‌ها"))}">${scopeOptions}</select></label>
    <button type="button" data-usage-refresh>${escapeHtml(text(locale, "Refresh", "به‌روزرسانی"))}</button>
    <span class="cp-usage-count" data-usage-count>${escapeHtml(text(
      locale,
      `${storedPeriodCount} stored period(s)`,
      `${storedPeriodCount} دورهٔ ذخیره‌شده`,
    ))}</span>
  </div>`;
}

function renderStatus(options: ActivityUsageRenderOptions, view: ActivityUsageView): string {
  const { locale, source } = options;
  const heading = `<h3 id="cp-usage-heading">${escapeHtml(view === "spreadsheet" ? text(locale, "Activity Usage Spreadsheet", "صفحه‌گستردهٔ مصرف فعالیت") : text(locale, "Activity Usage Profile", "نیم‌رخ مصرف فعالیت"))}</h3>`;
  const controls = renderControls(locale, options.prefs, source.periods.length);
  if (source.status === "loading") {
    return `<div class="cp-usage-surface" data-usage-view="${view}" data-usage-metric="${options.prefs.metric}" data-usage-scope="${options.prefs.scope}">
      ${heading}${controls}
      <div class="cp-calendar-empty" data-usage-status="loading" role="status">${escapeHtml(text(locale, "Reading stored assignment periods…", "در حال خواندن دوره‌های ذخیره‌شدهٔ تخصیص…"))}</div>
    </div>`;
  }
  if (source.status === "error") {
    return `<div class="cp-usage-surface" data-usage-view="${view}" data-usage-metric="${options.prefs.metric}" data-usage-scope="${options.prefs.scope}">
      ${heading}${controls}
      <div class="cp-calendar-empty" data-usage-status="error" role="alert">${escapeHtml(text(locale, "Stored assignment periods could not be read", "خواندن دوره‌های ذخیره‌شدهٔ تخصیص ناموفق بود"))} (${escapeHtml(source.errorCode ?? "unknown")})</div>
    </div>`;
  }
  return "";
}

function renderSummary(locale: string, model: ActivityUsageSpreadsheetModel): string {
  return `<p class="cp-usage-source" data-usage-source>${escapeHtml(text(
    locale,
    `Read-only projection of ${model.storedPeriodCount} stored assignment period(s) across ${model.storedActivityCount} activity(ies). Values are summed stored facts by period; nothing is derived from activity dates.`,
    `نمایش فقط‌خواندنی ${model.storedPeriodCount} دورهٔ ذخیره‌شدهٔ تخصیص برای ${model.storedActivityCount} فعالیت. مقادیر، حقایق ذخیره‌شده و جمع‌شده در هر دوره‌اند و هیچ مقداری از تاریخ فعالیت‌ها استخراج نمی‌شود.`,
  ))}</p>`;
}

function renderSpreadsheet(options: ActivityUsageRenderOptions, model: ActivityUsageSpreadsheetModel): string {
  const { locale } = options;
  const heading = `<h3 id="cp-usage-heading">${escapeHtml(text(locale, "Activity Usage Spreadsheet", "صفحه‌گستردهٔ مصرف فعالیت"))}</h3>`;
  const controls = renderControls(locale, options.prefs, model.storedPeriodCount);
  if (model.storedPeriodCount === 0) {
    return `<div class="cp-usage-surface" data-usage-view="spreadsheet" data-usage-metric="${model.metric}" data-usage-scope="${model.scope}">
      ${heading}${controls}
      <div class="cp-calendar-empty" data-usage-status="empty" data-usage-empty>${escapeHtml(text(locale, "No assignment period is stored for this project, so the Activity Usage Spreadsheet has no values to show.", "برای این پروژه دورهٔ تخصیصی ذخیره نشده است؛ بنابراین صفحه‌گستردهٔ مصرف فعالیت مقداری برای نمایش ندارد."))}</div>
    </div>`;
  }
  if (!model.rows.length) {
    return `<div class="cp-usage-surface" data-usage-view="spreadsheet" data-usage-metric="${model.metric}" data-usage-scope="${model.scope}">
      ${heading}${controls}${renderSummary(locale, model)}
      <div class="cp-calendar-empty" data-usage-status="scope-empty" data-usage-scope-empty>${escapeHtml(text(locale, "No stored assignment period belongs to the selected activities.", "هیچ دورهٔ تخصیص ذخیره‌شده‌ای به فعالیت‌های انتخاب‌شده تعلق ندارد."))}</div>
    </div>`;
  }
  const header = model.periods
    .map((periodStart) => `<th scope="col" class="cp-usage-period" data-usage-period="${escapeHtml(periodStart)}"><time datetime="${escapeHtml(periodStart)}">${escapeHtml(periodStart)}</time></th>`)
    .join("");
  const body = model.rows.map((row) => {
    const cells = row.values.map((cell) => `<td data-usage-cell data-activity-id="${escapeHtml(row.activityId)}" data-period-start="${escapeHtml(cell.periodStart)}" data-value="${escapeHtml(cell.value ?? "")}">${escapeHtml(cell.value ?? "—")}</td>`).join("");
    return `<tr data-usage-row data-activity-id="${escapeHtml(row.activityId)}" data-usage-row-total="${escapeHtml(row.total ?? "")}">
      <th scope="row" class="cp-usage-activity" data-usage-activity="${escapeHtml(row.activityId)}"><span>${escapeHtml(row.label)}</span><small>${escapeHtml(row.activityId)}</small></th>
      ${cells}
      <td class="cp-usage-total" data-usage-row-total-cell data-value="${escapeHtml(row.total ?? "")}">${escapeHtml(row.total ?? "—")}</td>
    </tr>`;
  }).join("");
  const footerCells = model.periodTotals
    .map((cell) => `<td data-usage-period-total data-period-start="${escapeHtml(cell.periodStart)}" data-value="${escapeHtml(cell.value ?? "")}">${escapeHtml(cell.value ?? "—")}</td>`)
    .join("");
  return `<div class="cp-usage-surface" data-usage-view="spreadsheet" data-usage-metric="${model.metric}" data-usage-scope="${model.scope}">
    ${heading}${controls}${renderSummary(locale, model)}
    <div class="cp-usage-table-wrap" data-usage-table>
      <table class="cp-usage-table">
        <thead><tr><th scope="col" class="cp-usage-activity">${escapeHtml(text(locale, "Activity", "فعالیت"))}</th>${header}<th scope="col" class="cp-usage-total">${escapeHtml(text(locale, "Total", "جمع"))}</th></tr></thead>
        <tbody>${body}</tbody>
        <tfoot><tr data-usage-total-row><th scope="row">${escapeHtml(text(locale, "Total", "جمع"))}</th>${footerCells}<td class="cp-usage-total" data-usage-grand-total data-value="${escapeHtml(model.grandTotal ?? "")}">${escapeHtml(model.grandTotal ?? "—")}</td></tr></tfoot>
      </table>
    </div>
  </div>`;
}

function barHeight(value: string | null, peak: string | null): number {
  if (value === null || peak === null) return 0;
  const numeric = Number.parseFloat(value);
  const maximum = Number.parseFloat(peak);
  if (!Number.isFinite(numeric) || !Number.isFinite(maximum) || maximum <= 0) return 0;
  return Math.max(2, Math.min(100, Math.round((numeric / maximum) * 100)));
}

function renderProfile(options: ActivityUsageRenderOptions, model: ActivityUsageSpreadsheetModel): string {
  const { locale } = options;
  const heading = `<h3 id="cp-usage-heading">${escapeHtml(text(locale, "Activity Usage Profile", "نیم‌رخ مصرف فعالیت"))}</h3>`;
  const controls = renderControls(locale, options.prefs, model.storedPeriodCount);
  if (model.storedPeriodCount === 0) {
    return `<div class="cp-usage-surface" data-usage-view="profile" data-usage-metric="${model.metric}" data-usage-scope="${model.scope}">
      ${heading}${controls}
      <div class="cp-calendar-empty" data-usage-status="empty" data-usage-empty>${escapeHtml(text(locale, "No assignment period is stored for this project, so the Activity Usage Profile has no bars to draw.", "برای این پروژه دورهٔ تخصیصی ذخیره نشده است؛ بنابراین نیم‌رخ مصرف فعالیت میله‌ای برای ترسیم ندارد."))}</div>
    </div>`;
  }
  if (!model.rows.length) {
    return `<div class="cp-usage-surface" data-usage-view="profile" data-usage-metric="${model.metric}" data-usage-scope="${model.scope}">
      ${heading}${controls}${renderSummary(locale, model)}
      <div class="cp-calendar-empty" data-usage-status="scope-empty" data-usage-scope-empty>${escapeHtml(text(locale, "No stored assignment period belongs to the selected activities.", "هیچ دورهٔ تخصیص ذخیره‌شده‌ای به فعالیت‌های انتخاب‌شده تعلق ندارد."))}</div>
    </div>`;
  }
  const profile = buildActivityUsageProfile(model);
  const metricLabel = model.metric === "units" ? text(locale, "Units", "واحدها") : text(locale, "Cost", "هزینه");
  const bars = profile.points.map((point) => {
    const height = barHeight(point.value, profile.peak);
    return `<div class="cp-usage-profile-bar" data-usage-profile-bar data-period-start="${escapeHtml(point.periodStart)}" data-value="${escapeHtml(point.value ?? "")}" title="${escapeHtml(`${point.periodStart}: ${point.value ?? "—"} ${metricLabel}`)}">
      <span class="cp-usage-bar-value">${escapeHtml(point.value ?? "—")}</span>
      <b style="height:${height}%"></b>
      <em>${escapeHtml(periodLabel(point.periodStart))}</em>
    </div>`;
  }).join("");
  return `<div class="cp-usage-surface" data-usage-view="profile" data-usage-metric="${model.metric}" data-usage-scope="${model.scope}">
    ${heading}${controls}${renderSummary(locale, model)}
    <p class="cp-usage-profile-summary" data-usage-profile-summary>${escapeHtml(text(
      locale,
      `${metricLabel}: total ${profile.total ?? "—"} · peak ${profile.peak ?? "—"} over ${profile.points.length} period(s)`,
      `${metricLabel}: جمع ${profile.total ?? "—"} · اوج ${profile.peak ?? "—"} در ${profile.points.length} دوره`,
    ))}</p>
    <div class="cp-usage-profile-chart" role="img" aria-label="${escapeHtml(text(locale, "Stored values by period", "مقادیر ذخیره‌شده به تفکیک دوره"))}">${bars}</div>
  </div>`;
}

/** Renders one usage surface; both views read the same persisted period rows. */
export function renderActivityUsage(options: ActivityUsageRenderOptions): string {
  const status = renderStatus(options, options.view);
  if (status) return status;
  const model = buildActivityUsageSpreadsheet({
    periods: options.source.periods,
    activities: options.activities,
    metric: options.prefs.metric,
    scope: options.prefs.scope,
    selectedIds: options.selectedIds,
  });
  return options.view === "spreadsheet"
    ? renderSpreadsheet(options, model)
    : renderProfile(options, model);
}
