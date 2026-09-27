import type {
  WorkspaceActivityRow,
  WorkspaceCellValue,
  WorkspaceColumn,
  WorkspaceGanttData,
  WorkspaceState,
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

  const columnIds = new Set<string>();
  for (const column of snapshot.columns) {
    if (!column.id || columnIds.has(column.id)) {
      throw new Error("DUPLICATE_WORKSPACE_COLUMN");
    }
    if (!Number.isFinite(column.width) || column.width <= 0) {
      throw new Error("INVALID_WORKSPACE_COLUMN");
    }
    columnIds.add(column.id);
  }
}
