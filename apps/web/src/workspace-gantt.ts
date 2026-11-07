import type { WorkspaceActivityRow, WorkspaceGanttScale, WorkspaceRelationshipRow, WorkspaceRelationshipType } from "./workspace-model.js";
import type { GanttOrdinalInterval, GanttTimescaleInterval } from "./workspace-presentation.js";

export type GanttScale = {
  startMs: number;
  endMs: number;
  rangeMs: number;
};

export type GanttBarGeometry = {
  activityId: string;
  leftPercent: number;
  widthPercent: number;
  progressPercent: number;
  critical: boolean;
  /** Zero-duration milestones (identical authoritative start and finish). */
  milestone: boolean;
};

export type GanttAxisTick = {
  key: string;
  atMs: number;
  leftPercent: number;
  /** Canonical ISO Gregorian date used by the presentation formatter. */
  date: string;
};

export type GanttLinkGeometry = {
  relationshipId: string;
  type: WorkspaceRelationshipType;
  predecessorId: string;
  successorId: string;
  critical: boolean;
  /** Horizontal anchor as a percentage of the shared timeline track. */
  fromX: number;
  toX: number;
  /** Horizontal position of the vertical routing lane between both anchors. */
  laneX: number;
  /** Vertical anchor in pixels from the first display row's top edge. */
  fromY: number;
  toY: number;
  /** SVG path in a 0..100 x 0..rowsHeight viewBox; one Y unit is one pixel. */
  path: string;
  /** Persisted lag/lead, null when the relationship has no offset. */
  lag: { value: string; unit: string } | null;
};

export type GanttLinkOptions = {
  /** Rendered height of one display row in pixels. */
  rowHeight?: number;
  /** Horizontal separation between a bar edge and the routed lane, in percent. */
  laneGapPercent?: number;
  /**
   * SVG units per horizontal percent. The Gantt uses 10 so the viewBox is
   * 0..1000 wide while its Y range stays exactly one unit per pixel; this keeps
   * arrowheads from stretching with the pane width.
   */
  xUnits?: number;
};

const DEFAULT_ROW_HEIGHT = 22;

/**
 * One row pitch drives the table, the Gantt rows, the bar centre and every
 * relationship anchor. Rows use border-box sizing, so the border is part of
 * the declared height and the pitch equals the row height.
 */
export function ganttRowPitch(rowHeight: number): number {
  if (!Number.isFinite(rowHeight)) return DEFAULT_ROW_HEIGHT;
  return Math.max(14, Math.min(48, Math.round(rowHeight)));
}

/** Vertical centre of display row `index`, in pixels from the row surface top. */
export function ganttRowCenter(index: number, rowHeight: number): number {
  const pitch = ganttRowPitch(rowHeight);
  return index * pitch + pitch / 2;
}

/** Total pixel height of `count` display rows. */
export function ganttRowsHeight(count: number, rowHeight: number): number {
  return Math.max(0, count) * ganttRowPitch(rowHeight);
}

const ganttScaleCache = new WeakMap<readonly WorkspaceActivityRow[], GanttScale | null>();
const ganttGeometryCache = new WeakMap<object, { scale: GanttScale; start: string; finish: string; progressPercent: number; critical: boolean; geometry: GanttBarGeometry | null }>();

export function createGanttScale(activities: readonly WorkspaceActivityRow[]): GanttScale | null {
  const cached = ganttScaleCache.get(activities);
  if (cached !== undefined) return cached;

  const dates = activities
    .map((activity) => activity.gantt)
    .filter((gantt): gantt is NonNullable<WorkspaceActivityRow["gantt"]> => Boolean(gantt))
    .flatMap((gantt) => [Date.parse(gantt.start), Date.parse(gantt.finish)])
    .filter((value) => Number.isFinite(value));

  if (!dates.length) {
    return null;
  }

  const startMs = Math.min(...dates);
  const endMs = Math.max(...dates);
  const scale = {
    startMs,
    endMs,
    rangeMs: Math.max(1, endMs - startMs),
  };
  ganttScaleCache.set(activities, scale);
  return scale;
}

/**
 * Converts already-scheduled datetimes into screen geometry only.
 * It never calculates or changes schedule dates, durations, lags, or progress.
 */
export function createGanttBarGeometry(
  activity: WorkspaceActivityRow,
  scale: GanttScale,
): GanttBarGeometry | null {
  const gantt = activity.gantt;
  const cached = ganttGeometryCache.get(activity);
  if (cached &&
      cached.scale === scale &&
      cached.start === gantt?.start &&
      cached.finish === gantt?.finish &&
      cached.progressPercent === gantt?.progressPercent &&
      cached.critical === gantt?.critical) {
    return cached.geometry;
  }

  if (!gantt) {
    ganttGeometryCache.set(activity, {
      scale,
      start: "",
      finish: "",
      progressPercent: 0,
      critical: false,
      geometry: null,
    });
    return null;
  }

  const startMs = Date.parse(gantt.start);
  const endMs = Date.parse(gantt.finish);
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs)) {
    ganttGeometryCache.set(activity, {
      scale,
      start: gantt.start,
      finish: gantt.finish,
      progressPercent: gantt.progressPercent,
      critical: gantt.critical,
      geometry: null,
    });
    return null;
  }

  const leftPercent = clampPercent(((startMs - scale.startMs) / scale.rangeMs) * 100);
  const rightPercent = clampPercent(((endMs - scale.startMs) / scale.rangeMs) * 100);
  const widthPercent = Math.max(1, rightPercent - leftPercent);

  const geometry = {
    activityId: activity.id,
    leftPercent,
    widthPercent,
    progressPercent: clampPercent(gantt.progressPercent),
    critical: gantt.critical,
    milestone: endMs === startMs,
  };
  ganttGeometryCache.set(activity, {
    scale,
    start: gantt.start,
    finish: gantt.finish,
    progressPercent: gantt.progressPercent,
    critical: gantt.critical,
    geometry,
  });
  return geometry;
}

const DAY_MS = 86_400_000;
const MAX_AXIS_TICKS = 40;

export type GanttTimescaleUnit = "year" | "quarter" | "month" | "week";

export type GanttPeriodGroup = {
  key: string;
  unit: GanttTimescaleUnit;
  startMs: number;
  endMs: number;
  leftPercent: number;
  widthPercent: number;
  /** Canonical ISO date of the group's first day. */
  date: string;
};

/**
 * The coarser unit displayed above the tick row for a documented date
 * interval. Week/Day intervals are grouped by month, Month/Week by month,
 * Quarter/Month by quarter and both Year intervals by year.
 */
export function timescaleMajorUnit(interval: GanttTimescaleInterval): GanttTimescaleUnit {
  switch (interval) {
    case "year-quarter":
    case "year-month":
      return "year";
    case "quarter-month":
      return "quarter";
    case "month-week":
    case "week-day":
      return "month";
  }
}

/** Tick density that matches the finer unit of a documented interval. */
export function timescaleTickScale(interval: GanttTimescaleInterval): WorkspaceGanttScale {
  switch (interval) {
    case "year-quarter":
      return "quarter";
    case "year-month":
    case "quarter-month":
      return "month";
    case "month-week":
      return "week";
    case "week-day":
      return "day";
  }
}

function boundaryAt(dateMs: number, unit: GanttTimescaleUnit): number {
  const date = new Date(dateMs);
  switch (unit) {
    case "year":
      return Date.UTC(date.getUTCFullYear(), 0, 1);
    case "quarter":
      return Date.UTC(date.getUTCFullYear(), Math.floor(date.getUTCMonth() / 3) * 3, 1);
    case "month":
      return Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), 1);
    case "week": {
      const day = Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
      const weekday = new Date(day).getUTCDay();
      return day - ((weekday + 6) % 7) * DAY_MS;
    }
  }
}

function nextBoundary(atMs: number, unit: GanttTimescaleUnit): number {
  const date = new Date(atMs);
  switch (unit) {
    case "year":
      return Date.UTC(date.getUTCFullYear() + 1, 0, 1);
    case "quarter":
      return Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 3, 1);
    case "month":
      return Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 1);
    case "week":
      return atMs + 7 * DAY_MS;
  }
}

/**
 * Groups the same authoritative date range used by the bars into header
 * spans. Group boundaries are real calendar boundaries; no date is rounded or
 * moved for scheduling purposes.
 */
export function createGanttPeriodGroups(
  scale: GanttScale,
  unit: GanttTimescaleUnit,
): readonly GanttPeriodGroup[] {
  const groups: GanttPeriodGroup[] = [];
  let at = boundaryAt(scale.startMs, unit);
  let guard = 0;
  while (at <= scale.endMs && guard < 300) {
    const next = nextBoundary(at, unit);
    const visibleStart = Math.max(at, scale.startMs);
    const visibleEnd = Math.min(next, scale.endMs);
    if (visibleEnd > visibleStart) {
      const leftPercent = clampPercent(((visibleStart - scale.startMs) / scale.rangeMs) * 100);
      const rightPercent = clampPercent(((visibleEnd - scale.startMs) / scale.rangeMs) * 100);
      const date = new Date(Math.max(at, scale.startMs)).toISOString().slice(0, 10);
      groups.push(Object.freeze({
        key: `${unit}:${new Date(at).toISOString().slice(0, 10)}`,
        unit,
        startMs: at,
        endMs: next,
        leftPercent,
        widthPercent: Math.max(0.5, rightPercent - leftPercent),
        date,
      }));
    }
    at = next;
    guard += 1;
  }
  return Object.freeze(groups);
}

/** ISO-8601 week number for a date, used by the "Week of Year" timescale type. */
export function isoWeekNumber(dateMs: number): number {
  const date = new Date(dateMs);
  const day = Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
  const weekday = (new Date(day).getUTCDay() + 6) % 7;
  const thursday = day - weekday * DAY_MS + 3 * DAY_MS;
  const yearStart = Date.UTC(new Date(thursday).getUTCFullYear(), 0, 1);
  return Math.floor((thursday - yearStart) / (7 * DAY_MS)) + 1;
}

/**
 * Sequential number of a date from the ordinal start. Dates before the start
 * are negative, matching the reference description.
 */
export function ordinalNumberAt(
  dateMs: number,
  startMs: number,
  interval: GanttOrdinalInterval,
): number {
  const date = new Date(dateMs);
  const start = new Date(startMs);
  const dayDiff = Math.floor(
    (Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate())
      - Date.UTC(start.getUTCFullYear(), start.getUTCMonth(), start.getUTCDate())) / DAY_MS,
  );
  switch (interval) {
    case "day":
      return dayDiff + 1;
    case "week":
      return Math.floor(dayDiff / 7) + 1;
    case "month":
      return (date.getUTCFullYear() - start.getUTCFullYear()) * 12 + date.getUTCMonth() - start.getUTCMonth() + 1;
    case "quarter":
      return (date.getUTCFullYear() - start.getUTCFullYear()) * 4
        + Math.floor(date.getUTCMonth() / 3) - Math.floor(start.getUTCMonth() / 3) + 1;
    case "year":
      return date.getUTCFullYear() - start.getUTCFullYear() + 1;
  }
}

/**
 * Builds axis ticks from the same authoritative date range as the bars.
 * The zoom only selects which canonical dates receive a label; it never
 * derives, rounds or shifts a schedule date.
 */
export function createGanttAxisTicks(
  scale: GanttScale,
  mode: WorkspaceGanttScale,
): readonly GanttAxisTick[] {
  const ticks: number[] = [scale.startMs];
  if (mode === "day") {
    for (let at = Math.floor(scale.startMs / DAY_MS) * DAY_MS + DAY_MS; at <= scale.endMs; at += DAY_MS) {
      ticks.push(at);
    }
  } else if (mode === "week") {
    let at = Math.floor(scale.startMs / DAY_MS) * DAY_MS;
    do {
      at += DAY_MS;
    } while (new Date(at).getUTCDay() !== 1);
    for (; at <= scale.endMs; at += 7 * DAY_MS) {
      ticks.push(at);
    }
  } else if (mode === "month") {
    const start = new Date(scale.startMs);
    for (let at = Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + 1, 1); at <= scale.endMs;) {
      ticks.push(at);
      const current = new Date(at);
      at = Date.UTC(current.getUTCFullYear(), current.getUTCMonth() + 1, 1);
    }
  } else if (mode === "quarter") {
    const start = new Date(scale.startMs);
    const nextQuarterMonth = Math.floor(start.getUTCMonth() / 3) * 3 + 3;
    for (let at = Date.UTC(start.getUTCFullYear(), nextQuarterMonth, 1); at <= scale.endMs;) {
      ticks.push(at);
      const current = new Date(at);
      at = Date.UTC(current.getUTCFullYear(), current.getUTCMonth() + 3, 1);
    }
  } else {
    const start = new Date(scale.startMs);
    for (let at = Date.UTC(start.getUTCFullYear() + 1, 0, 1); at <= scale.endMs;) {
      ticks.push(at);
      const current = new Date(at);
      at = Date.UTC(current.getUTCFullYear() + 1, 0, 1);
    }
  }

  const selected = ticks.length > MAX_AXIS_TICKS
    ? ticks.filter((_, index) => index % Math.ceil(ticks.length / MAX_AXIS_TICKS) === 0 || index === ticks.length - 1)
    : ticks;

  const seen = new Set<string>();
  return Object.freeze(selected.map((atMs) => {
    const date = new Date(atMs).toISOString().slice(0, 10);
    let key = date;
    for (let suffix = 2; seen.has(key); suffix += 1) key = `${date}#${suffix}`;
    seen.add(key);
    return Object.freeze({
      key,
      atMs,
      leftPercent: clampPercent(((atMs - scale.startMs) / scale.rangeMs) * 100),
      date,
    });
  }));
}

/**
 * Routes persisted relationship links between already-computed bar positions.
 * Link type semantics come from the stored relationship; nothing is converted.
 */
export function createGanttLinkGeometry(
  relationships: readonly WorkspaceRelationshipRow[],
  bars: readonly GanttBarGeometry[],
  /** Display-row index per activity, so WBS bands do not shift the link path. */
  rowIndexByActivity?: ReadonlyMap<string, number>,
  options: GanttLinkOptions = {},
): readonly GanttLinkGeometry[] {
  if (!relationships.length || !bars.length) return [];
  const rowHeight = ganttRowPitch(options.rowHeight ?? DEFAULT_ROW_HEIGHT);
  const gap = options.laneGapPercent ?? 1.5;
  const xUnits = Number.isFinite(options.xUnits) && (options.xUnits as number) > 0 ? options.xUnits as number : 1;
  const barIndexByActivity = new Map<string, number>();
  bars.forEach((bar, index) => barIndexByActivity.set(bar.activityId, index));
  const links: GanttLinkGeometry[] = [];
  // Each successive link gets its own routing lane so parallel relationships
  // between the same rows stay visually separate instead of overprinting.
  let laneOrdinal = 0;
  for (const relationship of relationships) {
    const fromBarIndex = barIndexByActivity.get(relationship.predecessorId);
    const toBarIndex = barIndexByActivity.get(relationship.successorId);
    if (fromBarIndex === undefined || toBarIndex === undefined) continue;
    const from = bars[fromBarIndex];
    const to = bars[toBarIndex];
    // A milestone is a point: both relationship edges meet at its date.
    const fromStart = from.leftPercent;
    const fromFinish = from.milestone ? from.leftPercent : from.leftPercent + from.widthPercent;
    const toStart = to.leftPercent;
    const toFinish = to.milestone ? to.leftPercent : to.leftPercent + to.widthPercent;
    const fromRow = rowIndexByActivity?.get(relationship.predecessorId) ?? fromBarIndex;
    const toRow = rowIndexByActivity?.get(relationship.successorId) ?? toBarIndex;
    const fromY = ganttRowCenter(fromRow, rowHeight);
    const toY = ganttRowCenter(toRow, rowHeight);
    const route = relationshipRoute(relationship.type, fromStart, fromFinish, toStart, toFinish, gap, laneOrdinal);
    laneOrdinal += 1;
    const lagNumber = Number(relationship.lagValue);
    const lag = Number.isFinite(lagNumber) && lagNumber !== 0 && relationship.lagValue.trim() !== ""
      ? Object.freeze({ value: relationship.lagValue, unit: relationship.lagUnit })
      : null;
    links.push(Object.freeze({
      relationshipId: relationship.id,
      type: relationship.type,
      predecessorId: relationship.predecessorId,
      successorId: relationship.successorId,
      critical: from.critical && to.critical,
      fromX: route.fromX,
      toX: route.toX,
      laneX: route.laneX,
      fromY,
      toY,
      path: `M ${round(route.fromX * xUnits)} ${round(fromY)} H ${round(route.laneX * xUnits)} V ${round(toY)} H ${round(route.toX * xUnits)}`,
      lag,
    }));
  }
  return Object.freeze(links);
}

function relationshipRoute(
  type: WorkspaceRelationshipType,
  fromStart: number,
  fromFinish: number,
  toStart: number,
  toFinish: number,
  gap: number,
  laneOrdinal: number,
): { fromX: number; toX: number; laneX: number } {
  let fromX: number;
  let toX: number;
  let laneX: number;
  const laneOffset = gap + (laneOrdinal % 4) * 0.8;
  if (type === "SS") {
    fromX = fromStart;
    toX = toStart;
    // Start-to-start enters the successor's start edge from its left, even
    // when the successor starts earlier than the predecessor.
    laneX = Math.min(fromX, toX) - laneOffset;
  } else if (type === "FF") {
    fromX = fromFinish;
    toX = toFinish;
    laneX = Math.max(fromX, toX) + laneOffset;
  } else if (type === "SF") {
    fromX = fromStart;
    toX = toFinish;
    laneX = Math.max(fromX, toX) + laneOffset;
  } else {
    fromX = fromFinish;
    toX = toStart;
    // Finish-to-start normally has room between the two edges; when the
    // successor overlaps, route around both bars instead of through them.
    laneX = toX > fromX + 0.5
      ? Math.min(toX - 0.2, Math.max(fromX + 0.2, fromX + laneOffset))
      : Math.max(fromX, toX) + laneOffset;
  }
  return {
    fromX: clampPercent(fromX),
    toX: clampPercent(toX),
    laneX: Math.max(0.2, Math.min(99.8, laneX)),
  };
}

function round(value: number): number {
  return Math.round(value * 100) / 100;
}

function clampPercent(value: number): number {
  return Math.max(0, Math.min(100, value));
}
