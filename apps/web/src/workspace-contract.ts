import type {
  WorkspaceActivityRow,
  WorkspaceCellValue,
  WorkspaceColumn,
  WorkspaceGanttData,
  WorkspaceState,
  WorkspaceWbsNode,
} from "./workspace-model.js";

export const WORKSPACE_CONTROL_ROOM_CONTRACT_VERSION = "workspace-control-room.v2" as const;

export type WorkspaceControlRoomSnapshot = {
  contract_version: typeof WORKSPACE_CONTROL_ROOM_CONTRACT_VERSION;
  context: {
    tenant_id: string;
    project_id: string;
    revision: number;
  };
  columns: readonly WorkspaceControlRoomColumn[];
  activities: readonly WorkspaceControlRoomActivity[];
  wbs_nodes: readonly WorkspaceControlRoomWbsNode[];
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

export type WorkspaceControlRoomWbsNode = {
  wbs_id: string;
  parent_kind: "project" | "wbs";
  parent_wbs_id: string | null;
  local_code: string;
  name: string;
  sequence_number: number;
  record_revision: number;
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
    wbs_nodes: state.wbsNodes.map((node) => ({
      wbs_id: node.id,
      parent_kind: node.parentKind,
      parent_wbs_id: node.parentWbsId,
      local_code: node.localCode,
      name: node.name,
      sequence_number: node.sequenceNumber,
      record_revision: node.recordRevision,
    })),
  };
}

export function workspaceWbsNodesFromSnapshot(
  snapshot: WorkspaceControlRoomSnapshot,
): readonly WorkspaceWbsNode[] {
  if (snapshot.contract_version !== WORKSPACE_CONTROL_ROOM_CONTRACT_VERSION) {
    throw new Error("UNSUPPORTED_WORKSPACE_CONTRACT");
  }
  validateSnapshotIdentity(snapshot);
  return snapshot.wbs_nodes.map((node) => ({
    id: node.wbs_id,
    parentKind: node.parent_kind,
    parentWbsId: node.parent_wbs_id,
    localCode: node.local_code,
    name: node.name,
    sequenceNumber: node.sequence_number,
    recordRevision: node.record_revision,
  }));
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

  if (
    !Array.isArray(snapshot.columns) ||
    !Array.isArray(snapshot.activities) ||
    !Array.isArray(snapshot.wbs_nodes)
  ) {
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

  const wbsIds = new Set<string>();
  let rootCount = 0;
  for (const node of snapshot.wbs_nodes) {
    if (
      !node || typeof node !== "object" || !node.wbs_id || wbsIds.has(node.wbs_id) ||
      (node.parent_kind !== "project" && node.parent_kind !== "wbs") ||
      !node.local_code || !node.name ||
      !Number.isSafeInteger(node.sequence_number) || node.sequence_number < 0 ||
      !Number.isSafeInteger(node.record_revision) || node.record_revision < 1
    ) {
      throw new Error("INVALID_WORKSPACE_WBS_NODE");
    }
    if (node.parent_kind === "project") {
      if (node.parent_wbs_id !== null) throw new Error("INVALID_WORKSPACE_WBS_PARENT");
      rootCount += 1;
    } else if (!node.parent_wbs_id || node.parent_wbs_id === node.wbs_id) {
      throw new Error("INVALID_WORKSPACE_WBS_PARENT");
    }
    wbsIds.add(node.wbs_id);
  }
  if (snapshot.wbs_nodes.length && rootCount !== 1) throw new Error("INVALID_WORKSPACE_WBS_ROOT");
  for (const node of snapshot.wbs_nodes) {
    if (node.parent_kind === "wbs" && !wbsIds.has(node.parent_wbs_id ?? "")) {
      throw new Error("INVALID_WORKSPACE_WBS_PARENT");
    }
    const visited = new Set<string>();
    let currentId: string | null = node.wbs_id;
    const nodesById = new Map(snapshot.wbs_nodes.map((item) => [item.wbs_id, item]));
    while (currentId) {
      if (visited.has(currentId)) throw new Error("WORKSPACE_WBS_CYCLE");
      visited.add(currentId);
      const current = nodesById.get(currentId);
      if (!current || current.parent_kind !== "wbs") break;
      currentId = current.parent_wbs_id;
    }
  }

  const activityIds = new Set<string>();
  for (const activity of snapshot.activities) {
    if (!activity || typeof activity !== "object") {
      throw new Error("INVALID_WORKSPACE_ACTIVITY");
    }
    if (!activity.id || !activity.wbs_id || !activity.name) {
      throw new Error("INVALID_WORKSPACE_ACTIVITY");
    }
    if (!wbsIds.has(activity.wbs_id)) {
      throw new Error("INVALID_WORKSPACE_ACTIVITY_WBS");
    }
    if (activityIds.has(activity.id)) {
      throw new Error("DUPLICATE_WORKSPACE_ACTIVITY");
    }
    activityIds.add(activity.id);
  }
}
