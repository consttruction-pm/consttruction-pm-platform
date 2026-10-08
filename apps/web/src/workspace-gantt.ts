import type { WorkspaceActivityRow } from "./workspace-model.js";

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
  const cached = ganttGeometryCache.get(activity);
  if (cached &&
      cached.scale === scale &&
      cached.start === activity.gantt?.start &&
      cached.finish === activity.gantt?.finish &&
      cached.progressPercent === activity.gantt?.progressPercent &&
      cached.critical === activity.gantt?.critical) {
    return cached.geometry;
  }

  if (!activity.gantt) {
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

  const startMs = Date.parse(activity.gantt.start);
  const endMs = Date.parse(activity.gantt.finish);
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs)) {
    ganttGeometryCache.set(activity, {
      scale,
      start: activity.gantt.start,
      finish: activity.gantt.finish,
      progressPercent: activity.gantt.progressPercent,
      critical: activity.gantt.critical,
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
    progressPercent: clampPercent(activity.gantt.progressPercent),
    critical: activity.gantt.critical,
  };
  ganttGeometryCache.set(activity, {
    scale,
    start: activity.gantt.start,
    finish: activity.gantt.finish,
    progressPercent: activity.gantt.progressPercent,
    critical: activity.gantt.critical,
    geometry,
  });
  return geometry;
}

function clampPercent(value: number): number {
  return Math.max(0, Math.min(100, value));
}
