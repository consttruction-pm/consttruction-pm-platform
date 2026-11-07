/**
 * Browser-local presentation model for the activity table and Gantt chart.
 *
 * These values only change appearance. They never participate in scheduling,
 * never rewrite start/finish/progress facts and never travel through the
 * schedule data contracts. The model is stored in the same project layout
 * metadata the field layout uses so a reload and another browser session show
 * the same saved presentation.
 */
import type { WorkspaceActivityRow } from "./workspace-model.js";
import {
  EMPTY_ACTIVITY_FILTERS,
  normalizeActivityFilterState,
  type ActivityFilterState,
} from "./workspace-activity-filters.js";

export const GANTT_BAR_KINDS = ["task", "critical", "summary", "milestone", "progress", "actual", "baseline"] as const;
export type GanttBarKind = (typeof GANTT_BAR_KINDS)[number];

export const GANTT_BAR_SHAPES = ["bar", "line", "triangle-up", "triangle-down", "diamond", "circle", "none"] as const;
export type GanttBarShape = (typeof GANTT_BAR_SHAPES)[number];

export const GANTT_BAR_PATTERNS = ["solid", "striped", "hatched", "outline"] as const;
export type GanttBarPattern = (typeof GANTT_BAR_PATTERNS)[number];

export type GanttBarRow = 1 | 2 | 3;

export const GANTT_BAR_FILTERS = ["all", "task", "critical", "noncritical", "milestone", "summary", "in-progress", "completed", "not-started"] as const;
export type GanttBarFilter = (typeof GANTT_BAR_FILTERS)[number];

export const GANTT_LABEL_FIELDS = ["none", "activity-id", "activity-name", "duration", "progress"] as const;
export type GanttBarLabelField = (typeof GANTT_LABEL_FIELDS)[number];

export const GANTT_LABEL_POSITIONS = ["inside-left", "inside-center", "inside-right", "above", "below", "right"] as const;
export type GanttBarLabelPosition = (typeof GANTT_LABEL_POSITIONS)[number];

export const TABLE_FONT_FAMILIES = ["system", "segoe", "cairo", "tahoma", "consolas"] as const;
export type TableFontFamily = (typeof TABLE_FONT_FAMILIES)[number];

export type GanttBarStyle = {
  visible: boolean;
  filter: GanttBarFilter;
  row: GanttBarRow;
  /** Height in CSS pixels inside the activity row. */
  height: number;
  startShape: GanttBarShape;
  bodyShape: GanttBarShape;
  finishShape: GanttBarShape;
  startColor: string;
  bodyColor: string;
  finishColor: string;
  borderColor: string;
  pattern: GanttBarPattern;
  labelField: GanttBarLabelField;
  labelPosition: GanttBarLabelPosition;
};

export type TablePresentation = {
  fontFamily: TableFontFamily;
  fontSize: number;
  textColor: string;
  backgroundColor: string;
  /** Fixed height, or the previous height when the mode is "keep". */
  rowHeight: number;
  rowHeightMode: "keep" | "fixed" | "content";
  showIcons: boolean;
  lineNumbers: boolean;
};

export type GanttBarStyleSet = Record<GanttBarKind, GanttBarStyle>;

export const GANTT_TIMESCALE_LINES = [2, 3] as const;
export type GanttTimescaleLines = (typeof GANTT_TIMESCALE_LINES)[number];

export const GANTT_TIMESCALE_FORMATS = ["primary", "ordinal"] as const;
export type GanttTimescaleFormat = (typeof GANTT_TIMESCALE_FORMATS)[number];

export const GANTT_TIMESCALE_TYPES = ["calendar", "week-of-year"] as const;
export type GanttTimescaleType = (typeof GANTT_TIMESCALE_TYPES)[number];

/** Date intervals documented for the Timescale dialog that this runtime can render. */
export const GANTT_TIMESCALE_INTERVALS = ["year-quarter", "year-month", "quarter-month", "month-week", "week-day"] as const;
export type GanttTimescaleInterval = (typeof GANTT_TIMESCALE_INTERVALS)[number];

export const GANTT_ORDINAL_INTERVALS = ["day", "week", "month", "quarter", "year"] as const;
export type GanttOrdinalInterval = (typeof GANTT_ORDINAL_INTERVALS)[number];

export type GanttTimescale = {
  /** Number of header rows: two (period plus ticks) or three (year, period, ticks). */
  lines: GanttTimescaleLines;
  dateFormat: GanttTimescaleFormat;
  type: GanttTimescaleType;
  interval: GanttTimescaleInterval;
  /** ISO date the ordinal numbering starts from; null uses the chart's first date. */
  ordinalStart: string | null;
  ordinalInterval: GanttOrdinalInterval;
  /** Timescale header font size and colours; the grid itself is unchanged. */
  fontSize: number;
  textColor: string;
  backgroundColor: string;
};

export type WbsPresentation = {
  /** One colour per WBS depth, level 1 first. The last entry applies to deeper levels. */
  levelColors: string[];
};

export type WorkspacePresentation = {
  table: TablePresentation;
  bars: GanttBarStyleSet;
  timescale: GanttTimescale;
  wbs: WbsPresentation;
  /** Saved activity filters and the currently applied filter. */
  filters: ActivityFilterState;
};

export type GanttBarFacts = {
  critical: boolean;
  milestone: boolean;
  summary: boolean;
  status: string;
  progress: number;
  hasActual: boolean;
  hasBaseline: boolean;
};

const DEFAULT_TABLE: TablePresentation = {
  fontFamily: "tahoma",
  fontSize: 11,
  textColor: "#000000",
  backgroundColor: "#ffffff",
  rowHeight: 22,
  rowHeightMode: "fixed",
  showIcons: true,
  lineNumbers: false,
};

/**
 * Reference-derived WBS level palette. The hierarchy column uses these colours
 * for the vertical rails and a light tint; activity status, selection and
 * critical-path colours stay independent from them.
 */
export const DEFAULT_WBS_LEVEL_COLORS = [
  "#3b3bbf",
  "#c9a227",
  "#4f9b57",
  "#2f8fae",
  "#b0558a",
  "#7a63bd",
] as const;

export const MAX_WBS_LEVELS = DEFAULT_WBS_LEVEL_COLORS.length;

const DEFAULT_TIMESCALE: GanttTimescale = {
  lines: 2,
  dateFormat: "primary",
  type: "calendar",
  interval: "month-week",
  ordinalStart: null,
  ordinalInterval: "week",
  fontSize: 11,
  textColor: "#17324d",
  backgroundColor: "#e3e9f0",
};

function bar(style: Partial<GanttBarStyle> & Pick<GanttBarStyle, "bodyColor">): GanttBarStyle {
  return {
    visible: true,
    filter: "all",
    row: 1,
    height: 14,
    startShape: "none",
    bodyShape: "bar",
    finishShape: "none",
    startColor: style.bodyColor,
    finishColor: style.bodyColor,
    borderColor: style.bodyColor,
    pattern: "solid",
    labelField: "none",
    labelPosition: "right",
    ...style,
  };
}

export const DEFAULT_PRESENTATION: WorkspacePresentation = {
  table: { ...DEFAULT_TABLE },
  filters: EMPTY_ACTIVITY_FILTERS,
  timescale: { ...DEFAULT_TIMESCALE },
  wbs: { levelColors: [...DEFAULT_WBS_LEVEL_COLORS] },
  bars: {
    // The default palette follows the classic desktop scheduling worksurface:
    // light outlined work bars, a dark solid summary, a black milestone diamond
    // and green actual bars, with the activity id printed beside each bar.
    task: bar({ bodyColor: "#eef3f8", borderColor: "#1f3b57", filter: "task", labelField: "activity-id" }),
    critical: bar({ bodyColor: "#f6dcd7", borderColor: "#9e2b25", filter: "critical", labelField: "activity-id" }),
    summary: bar({ bodyColor: "#17324d", borderColor: "#0f2a44", filter: "summary", height: 10, startShape: "triangle-down", finishShape: "triangle-down", labelField: "none" }),
    milestone: bar({ bodyColor: "#1f2933", borderColor: "#111827", filter: "milestone", bodyShape: "diamond", height: 14 }),
    progress: bar({ bodyColor: "#1f3b57", borderColor: "#1f3b57", filter: "all", height: 6 }),
    actual: bar({ bodyColor: "#2e7d5b", borderColor: "#246448", filter: "all", row: 2, height: 6 }),
    baseline: bar({ bodyColor: "#6b7785", borderColor: "#6b7785", filter: "all", row: 3, height: 4, bodyShape: "line" }),
  },
};

const HEX_COLOR = /^#[0-9a-f]{6}$/i;

export function isHexColor(value: unknown): value is string {
  return typeof value === "string" && HEX_COLOR.test(value);
}

function color(value: unknown, fallback: string): string {
  if (isHexColor(value)) return value.toLowerCase();
  if (typeof value === "string") {
    const short = /^#([0-9a-f])([0-9a-f])([0-9a-f])$/i.exec(value.trim());
    if (short) return `#${short[1]}${short[1]}${short[2]}${short[2]}${short[3]}${short[3]}`.toLowerCase();
  }
  return fallback;
}

function clampInteger(value: unknown, min: number, max: number, fallback: number): number {
  const number = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.min(max, Math.max(min, Math.round(number)));
}

function oneOf<T extends string>(values: readonly T[], value: unknown, fallback: T): T {
  return typeof value === "string" && (values as readonly string[]).includes(value) ? value as T : fallback;
}

function boolean(value: unknown, fallback: boolean): boolean {
  return typeof value === "boolean" ? value : fallback;
}

export function normalizeBarStyle(value: unknown, fallback: GanttBarStyle): GanttBarStyle {
  const input = value && typeof value === "object" ? value as Record<string, unknown> : {};
  const row = clampInteger(input.row, 1, 3, fallback.row) as GanttBarRow;
  return {
    visible: boolean(input.visible, fallback.visible),
    filter: oneOf(GANTT_BAR_FILTERS, input.filter, fallback.filter),
    row,
    height: clampInteger(input.height, 3, 24, fallback.height),
    startShape: oneOf(GANTT_BAR_SHAPES, input.startShape, fallback.startShape),
    bodyShape: oneOf(GANTT_BAR_SHAPES, input.bodyShape, fallback.bodyShape),
    finishShape: oneOf(GANTT_BAR_SHAPES, input.finishShape, fallback.finishShape),
    startColor: color(input.startColor, fallback.startColor),
    bodyColor: color(input.bodyColor, fallback.bodyColor),
    finishColor: color(input.finishColor, fallback.finishColor),
    borderColor: color(input.borderColor, fallback.borderColor),
    pattern: oneOf(GANTT_BAR_PATTERNS, input.pattern, fallback.pattern),
    labelField: oneOf(GANTT_LABEL_FIELDS, input.labelField, fallback.labelField),
    labelPosition: oneOf(GANTT_LABEL_POSITIONS, input.labelPosition, fallback.labelPosition),
  };
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export function isIsoDate(value: unknown): value is string {
  return typeof value === "string" && ISO_DATE.test(value) && Number.isFinite(Date.parse(`${value}T00:00:00Z`));
}

export function normalizeTimescale(value: unknown, fallback: GanttTimescale = DEFAULT_TIMESCALE): GanttTimescale {
  const input = value && typeof value === "object" ? value as Record<string, unknown> : {};
  return {
    lines: input.lines === 3 ? 3 : fallback.lines,
    dateFormat: oneOf(GANTT_TIMESCALE_FORMATS, input.dateFormat, fallback.dateFormat),
    type: oneOf(GANTT_TIMESCALE_TYPES, input.type, fallback.type),
    interval: oneOf(GANTT_TIMESCALE_INTERVALS, input.interval, fallback.interval),
    ordinalStart: isIsoDate(input.ordinalStart) ? input.ordinalStart : null,
    ordinalInterval: oneOf(GANTT_ORDINAL_INTERVALS, input.ordinalInterval, fallback.ordinalInterval),
    fontSize: clampInteger(input.fontSize, 8, 16, fallback.fontSize),
    textColor: color(input.textColor, fallback.textColor),
    backgroundColor: color(input.backgroundColor, fallback.backgroundColor),
  };
}

export function normalizeWbs(value: unknown, fallback: WbsPresentation = DEFAULT_PRESENTATION.wbs): WbsPresentation {
  const input = value && typeof value === "object" ? value as Record<string, unknown> : {};
  const source = Array.isArray(input.levelColors) ? input.levelColors : [];
  return {
    levelColors: Array.from({ length: MAX_WBS_LEVELS }, (_, index) =>
      color(source[index], fallback.levelColors[index] ?? DEFAULT_WBS_LEVEL_COLORS[Math.min(index, MAX_WBS_LEVELS - 1)]),
    ),
  };
}

/** Colour for a zero-based WBS depth; deeper levels reuse the last colour. */
export function wbsLevelColor(wbs: WbsPresentation, depth: number): string {
  const index = Math.max(0, Math.min(wbs.levelColors.length - 1, Math.round(depth)));
  return wbs.levelColors[index] ?? DEFAULT_WBS_LEVEL_COLORS[MAX_WBS_LEVELS - 1];
}

export function normalizePresentation(value: unknown): WorkspacePresentation {
  const input = value && typeof value === "object" ? value as Record<string, unknown> : {};
  const tableInput = input.table && typeof input.table === "object" ? input.table as Record<string, unknown> : {};
  const barsInput = input.bars && typeof input.bars === "object" ? input.bars as Record<string, unknown> : {};
  const bars = {} as GanttBarStyleSet;
  for (const kind of GANTT_BAR_KINDS) {
    bars[kind] = normalizeBarStyle(barsInput[kind], DEFAULT_PRESENTATION.bars[kind]);
  }
  return {
    table: {
      fontFamily: oneOf(TABLE_FONT_FAMILIES, tableInput.fontFamily, DEFAULT_TABLE.fontFamily),
      fontSize: clampInteger(tableInput.fontSize, 9, 16, DEFAULT_TABLE.fontSize),
      textColor: color(tableInput.textColor, DEFAULT_TABLE.textColor),
      backgroundColor: color(tableInput.backgroundColor, DEFAULT_TABLE.backgroundColor),
      rowHeight: clampInteger(tableInput.rowHeight, 18, 40, DEFAULT_TABLE.rowHeight),
      rowHeightMode: oneOf(["keep", "fixed", "content"] as const, tableInput.rowHeightMode, DEFAULT_TABLE.rowHeightMode),
      showIcons: boolean(tableInput.showIcons, DEFAULT_TABLE.showIcons),
      lineNumbers: boolean(tableInput.lineNumbers, DEFAULT_TABLE.lineNumbers),
    },
    bars,
    timescale: normalizeTimescale(input.timescale),
    wbs: normalizeWbs(input.wbs),
    filters: normalizeActivityFilterState(input.filters),
  };
}

export function presentationFontFamily(family: TableFontFamily): string {
  switch (family) {
    case "segoe": return '"Segoe UI", "Vazirmatn", system-ui, sans-serif';
    case "cairo": return '"Cairo", "Vazirmatn", "Segoe UI", sans-serif';
    case "tahoma": return 'Tahoma, "Segoe UI", sans-serif';
    case "consolas": return 'Consolas, "Courier New", monospace';
    default: return 'system-ui, -apple-system, "Segoe UI", Roboto, "Vazirmatn", sans-serif';
  }
}

export function barKindMatchesFilter(filter: GanttBarFilter, facts: GanttBarFacts): boolean {
  switch (filter) {
    case "all": return true;
    case "task": return !facts.summary && !facts.milestone;
    case "critical": return facts.critical;
    case "noncritical": return !facts.critical;
    case "milestone": return facts.milestone;
    case "summary": return facts.summary;
    case "in-progress": return facts.progress > 0 && facts.progress < 100;
    case "completed": return facts.progress >= 100 || facts.status.toLowerCase() === "completed";
    case "not-started": return facts.progress <= 0 && (facts.status === "" || facts.status.toLowerCase() === "not started");
    default: return false;
  }
}

const PRIMARY_PRECEDENCE: readonly GanttBarKind[] = ["milestone", "summary", "critical", "task"];

/**
 * Selects the single primary bar style for an activity. Specialised styles win
 * over the generic task bar so one activity never draws two overlapping
 * primary bars. Hiding a specialised style deliberately falls back to the task
 * style instead of leaving the row blank.
 */
export function selectPrimaryBarKind(bars: GanttBarStyleSet, facts: GanttBarFacts): GanttBarKind | null {
  for (const kind of PRIMARY_PRECEDENCE) {
    const style = bars[kind];
    if (style.visible && barKindMatchesFilter(style.filter, facts)) return kind;
  }
  return null;
}

export function hasActualDates(activity: WorkspaceActivityRow): boolean {
  const cells = activity.cells ?? {};
  const start = cells["activity.actual_start"] ?? cells["actual_start"];
  const finish = cells["activity.actual_finish"] ?? cells["actual_finish"];
  return typeof start === "string" && start.trim() !== "" && typeof finish === "string" && finish.trim() !== "";
}

export function hasBaselineDates(activity: WorkspaceActivityRow): boolean {
  const cells = activity.cells ?? {};
  const start = cells["activity.baseline_start"] ?? cells["baseline_start"];
  const finish = cells["activity.baseline_finish"] ?? cells["baseline_finish"];
  return typeof start === "string" && start.trim() !== "" && typeof finish === "string" && finish.trim() !== "";
}

export function presentationDataAvailability(activities: readonly WorkspaceActivityRow[]): { actual: boolean; baseline: boolean } {
  let actual = false;
  let baseline = false;
  for (const activity of activities) {
    if (!actual && hasActualDates(activity)) actual = true;
    if (!baseline && hasBaselineDates(activity)) baseline = true;
    if (actual && baseline) break;
  }
  return { actual, baseline };
}

export function activityBarFacts(activity: WorkspaceActivityRow, bar: { critical: boolean; milestone: boolean; progressPercent: number }): GanttBarFacts {
  const cells = activity.cells ?? {};
  const type = String(cells["activity.activity_type"] ?? cells.activity_type ?? "").toLowerCase();
  const status = String(cells["activity.activity_status"] ?? cells.status ?? "");
  return {
    critical: bar.critical,
    milestone: bar.milestone,
    summary: type === "wbs summary" || type === "wbs_summary",
    status,
    progress: bar.progressPercent,
    hasActual: hasActualDates(activity),
    hasBaseline: hasBaselineDates(activity),
  };
}

export function barLabelText(field: GanttBarLabelField, bar: { activityId: string; progressPercent: number }, activity: WorkspaceActivityRow | undefined): string {
  switch (field) {
    case "activity-id": return bar.activityId;
    case "activity-name": return activity?.name ?? "";
    case "duration": {
      const value = activity?.cells?.duration;
      return value === undefined || value === null ? "" : String(value);
    }
    case "progress": return `${bar.progressPercent}%`;
    default: return "";
  }
}
