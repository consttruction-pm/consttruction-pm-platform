import type { WorkspaceActivityRow, WorkspaceGanttScale, WorkspaceRelationshipRow, WorkspaceRelationshipType } from "./workspace-model.js";

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
  /** SVG path in a 0..100 x 0..rows*100 viewBox. */
  path: string;
};

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
  } else {
    const start = new Date(scale.startMs);
    for (let at = Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + 1, 1); at <= scale.endMs;) {
      ticks.push(at);
      const current = new Date(at);
      at = Date.UTC(current.getUTCFullYear(), current.getUTCMonth() + 1, 1);
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
): readonly GanttLinkGeometry[] {
  if (!relationships.length || !bars.length) return [];
  const rowByActivity = new Map<string, number>();
  bars.forEach((bar, index) => rowByActivity.set(bar.activityId, index));
  const links: GanttLinkGeometry[] = [];
  for (const relationship of relationships) {
    const fromIndex = rowByActivity.get(relationship.predecessorId);
    const toIndex = rowByActivity.get(relationship.successorId);
    if (fromIndex === undefined || toIndex === undefined) continue;
    const from = bars[fromIndex];
    const to = bars[toIndex];
    const path = relationshipPath(
      relationship.type,
      from.leftPercent,
      from.leftPercent + from.widthPercent,
      to.leftPercent,
      to.leftPercent + to.widthPercent,
      fromIndex * 100 + 50,
      toIndex * 100 + 50,
    );
    links.push(Object.freeze({
      relationshipId: relationship.id,
      type: relationship.type,
      predecessorId: relationship.predecessorId,
      successorId: relationship.successorId,
      critical: from.critical && to.critical,
      path,
    }));
  }
  return Object.freeze(links);
}

function relationshipPath(
  type: WorkspaceRelationshipType,
  fromLeft: number,
  fromRight: number,
  toLeft: number,
  toRight: number,
  fromY: number,
  toY: number,
): string {
  const gap = 1.5;
  let x1: number;
  let x2: number;
  let mid: number;
  if (type === "SS") {
    x1 = fromLeft;
    x2 = toLeft;
    mid = clampPercent(Math.min(x1, x2) - gap);
  } else if (type === "FF") {
    x1 = fromRight;
    x2 = toRight;
    mid = clampPercent(Math.max(x1, x2) + gap);
  } else if (type === "SF") {
    x1 = fromLeft;
    x2 = toRight;
    mid = clampPercent(Math.min(x1, x2) - gap);
  } else {
    x1 = fromRight;
    x2 = toLeft;
    mid = clampPercent(Math.max(x1, x2) + gap);
  }
  return `M ${round(x1)} ${fromY} H ${round(mid)} V ${toY} H ${round(x2)}`;
}

function round(value: number): number {
  return Math.round(value * 100) / 100;
}

function clampPercent(value: number): number {
  return Math.max(0, Math.min(100, value));
}
