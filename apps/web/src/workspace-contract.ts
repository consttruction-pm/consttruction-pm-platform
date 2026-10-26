import type {
  WorkspaceActivityRow,
  WorkspaceCellValue,
  WorkspaceColumn,
  WorkspaceGanttData,
  WorkspaceState,
  WorkspaceWbsSummary,
} from "./workspace-model.js";

export const WORKSPACE_CONTROL_ROOM_CONTRACT_VERSION = "workspace-control-room.v1" as const;

export type WorkspaceControlRoomSnapshot = {
  contract_version: typeof WORKSPACE_CONTROL_ROOM_CONTRACT_VERSION;
  context: {
    tenant_id: string;
    project_id: string;
    revision: number;
  };
  columns: readonly WorkspaceControlRoomColumn[];
  activities: readonly WorkspaceControlRoomActivity[];
  /**
   * Optional additive projection. Older read envelopes can omit it; when it is
   * present it is authoritative and never recomputed in the browser.
   */
  wbs_summary?: readonly WorkspaceControlRoomWbsSummary[];
};

export type WorkspaceControlRoomWbsSummary = {
  wbs_id: string;
  activity_count: number;
  critical_count: number;
  scheduled_start: string | null;
  scheduled_finish: string | null;
  total_float_min: number | null;
};

export type WorkspaceControlRoomColumn = {
  id: string;
  label: string;
  data_type: WorkspaceColumn["dataType"];
  editable: boolean;
  formula: string | null;
  width: number;
};

export type WorkspaceControlRoomActivity = {
  id: string;
  wbs_id: string;
  code: string;
  name: string;
  cells: Readonly<Record<string, WorkspaceCellValue>>;
  gantt: WorkspaceGanttData | null;
};

export function createWorkspaceControlRoomSnapshot(
  state: WorkspaceState,
): WorkspaceControlRoomSnapshot {
  return {
    contract_version: WORKSPACE_CONTROL_ROOM_CONTRACT_VERSION,
    context: {
      tenant_id: state.context.tenant_id,
      project_id: state.context.project_id,
      revision: state.context.revision,
    },
    columns: state.columns.map((column) => ({
      id: column.id,
      label: column.label,
      data_type: column.dataType,
      editable: column.editable,
      formula: column.formula,
      width: column.width,
    })),
    activities: state.activities.map((activity) => ({
      id: activity.id,
      wbs_id: activity.wbsId,
      code: activity.code,
      name: activity.name,
      cells: Object.freeze({ ...(activity.cells ?? {}) }),
      gantt: activity.gantt
        ? Object.freeze({
            start: activity.gantt.start,
            finish: activity.gantt.finish,
            progressPercent: activity.gantt.progressPercent,
            critical: activity.gantt.critical,
          })
        : null,
    })),
  };
}

export function workspaceActivitiesFromSnapshot(
  snapshot: WorkspaceControlRoomSnapshot,
): readonly WorkspaceActivityRow[] {
  if (snapshot.contract_version !== WORKSPACE_CONTROL_ROOM_CONTRACT_VERSION) {
    throw new Error("UNSUPPORTED_WORKSPACE_CONTRACT");
  }
  validateSnapshotIdentity(snapshot);

  const ids = new Set<string>();
  for (const activity of snapshot.activities) {
    if (ids.has(activity.id)) {
      throw new Error("DUPLICATE_WORKSPACE_ACTIVITY");
    }
    ids.add(activity.id);
  }

  return snapshot.activities.map((activity) => ({
    id: activity.id,
    wbsId: activity.wbs_id,
    code: activity.code,
    name: activity.name,
    cells: Object.freeze({ ...activity.cells }),
    gantt: activity.gantt
      ? Object.freeze({
          start: activity.gantt.start,
          finish: activity.gantt.finish,
          progressPercent: activity.gantt.progressPercent,
          critical: activity.gantt.critical,
        })
      : undefined,
  }));
}

export function workspaceWbsSummaryFromSnapshot(
  snapshot: WorkspaceControlRoomSnapshot,
): readonly WorkspaceWbsSummary[] {
  if (snapshot.wbs_summary === undefined) return [];
  if (!Array.isArray(snapshot.wbs_summary)) {
    throw new Error("INVALID_WORKSPACE_WBS_SUMMARY");
  }
  const ids = new Set<string>();
  return snapshot.wbs_summary.map((group) => {
    if (!group || typeof group !== "object") {
      throw new Error("INVALID_WORKSPACE_WBS_SUMMARY");
    }
    if (!group.wbs_id || ids.has(group.wbs_id)) {
      throw new Error("INVALID_WORKSPACE_WBS_SUMMARY");
    }
    if (
      !Number.isInteger(group.activity_count) ||
      group.activity_count < 0 ||
      !Number.isInteger(group.critical_count) ||
      group.critical_count < 0 ||
      group.critical_count > group.activity_count
    ) {
      throw new Error("INVALID_WORKSPACE_WBS_SUMMARY");
    }
    for (const value of [group.scheduled_start, group.scheduled_finish]) {
      if (value !== null && (typeof value !== "string" || !value.trim())) {
        throw new Error("INVALID_WORKSPACE_WBS_SUMMARY");
      }
    }
    if (group.total_float_min !== null && !Number.isFinite(group.total_float_min)) {
      throw new Error("INVALID_WORKSPACE_WBS_SUMMARY");
    }
    ids.add(group.wbs_id);
    return Object.freeze({
      wbsId: group.wbs_id,
      activityCount: group.activity_count,
      criticalCount: group.critical_count,
      scheduledStart: group.scheduled_start,
      scheduledFinish: group.scheduled_finish,
      totalFloatMin: group.total_float_min,
    });
  });
}

function validateSnapshotIdentity(snapshot: WorkspaceControlRoomSnapshot): void {
  const MAX_SAFE_REVISION = 9_007_199_254_740_991;
  if (
    !snapshot.context.tenant_id ||
    !snapshot.context.project_id ||
    !Number.isInteger(snapshot.context.revision) ||
    snapshot.context.revision < 0 ||
    snapshot.context.revision > MAX_SAFE_REVISION
  ) {
    throw new Error("INVALID_WORKSPACE_CONTEXT");
  }

  if (!Array.isArray(snapshot.columns) || !Array.isArray(snapshot.activities)) {
    throw new Error("INVALID_WORKSPACE_COLLECTION");
  }

  const columnIds = new Set<string>();
  for (const column of snapshot.columns) {
    if (!column || typeof column !== "object" || !column.id || columnIds.has(column.id)) {
      throw new Error("DUPLICATE_WORKSPACE_COLUMN");
    }
    if (!Number.isFinite(column.width) || column.width <= 0) {
      throw new Error("INVALID_WORKSPACE_COLUMN");
    }
    columnIds.add(column.id);
  }

  const activityIds = new Set<string>();
  for (const activity of snapshot.activities) {
    if (!activity || typeof activity !== "object") {
      throw new Error("INVALID_WORKSPACE_ACTIVITY");
    }
    if (!activity.id || !activity.wbs_id || !activity.name) {
      throw new Error("INVALID_WORKSPACE_ACTIVITY");
    }
    if (activityIds.has(activity.id)) {
      throw new Error("DUPLICATE_WORKSPACE_ACTIVITY");
    }
    activityIds.add(activity.id);
  }
}
