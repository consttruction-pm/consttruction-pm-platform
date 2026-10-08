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
};

export function createGanttScale(activities: readonly WorkspaceActivityRow[]): GanttScale | null {
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
  return {
    startMs,
    endMs,
    rangeMs: Math.max(1, endMs - startMs),
  };
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
  if (!gantt) {
    return null;
  }

  const startMs = Date.parse(gantt.start);
  const endMs = Date.parse(gantt.finish);
  if (!Number.isFinite(startMs) || !Number.isFinite(endMs)) {
    return null;
  }

  const leftPercent = clampPercent(((startMs - scale.startMs) / scale.rangeMs) * 100);
  const rightPercent = clampPercent(((endMs - scale.startMs) / scale.rangeMs) * 100);
  const widthPercent = Math.max(1, rightPercent - leftPercent);

  return {
    activityId: activity.id,
    leftPercent,
    widthPercent,
    progressPercent: clampPercent(gantt.progressPercent),
    critical: gantt.critical,
  };
}

function clampPercent(value: number): number {
  return Math.max(0, Math.min(100, value));
}
