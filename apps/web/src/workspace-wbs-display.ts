/**
 * WBS display rows for the activity table and Gantt chart.
 *
 * The builder only orders and aggregates persisted rows for display. It never
 * schedules, never re-dates an activity and never invents a summary record:
 * group span, duration and progress are derived from the real child activities
 * that the project read model already returned. Collapse state is a local view
 * preference and is stored per project.
 */
import type {
  WorkspaceActivityGroupBy,
  WorkspaceActivityRow,
  WorkspaceWbsNode,
} from "./workspace-model.js";

export type WorkspaceWbsGroupSummary = {
  /** Earliest persisted child start, or null when no child has schedule data. */
  startMs: number | null;
  /** Latest persisted child finish, or null when no child has schedule data. */
  finishMs: number | null;
  /** Sum of persisted child durations when every child reports one. */
  duration: number | null;
  /** Duration-weighted child progress for display only. */
  progressPercent: number | null;
  /** Number of activities in this node and every descendant node. */
  activityCount: number;
};

export type WorkspaceWbsGroupRow = {
  kind: "wbs";
  wbsId: string;
  node: WorkspaceWbsNode;
  /** 0 for a root WBS band. */
  depth: number;
  hasChildren: boolean;
  collapsed: boolean;
  summary: WorkspaceWbsGroupSummary;
};

export type WorkspaceActivityDisplayRow = {
  kind: "activity";
  activity: WorkspaceActivityRow;
  /** 0 without WBS grouping, otherwise the band depth plus one. */
  depth: number;
  wbsId: string;
};

export type WorkspaceDisplayRow = WorkspaceWbsGroupRow | WorkspaceActivityDisplayRow;

const COLLAPSE_STORAGE_KEY = "cubi:workspace-wbs-collapse";
let collapseStore: Record<string, string[]> | null = null;

function readCollapseStore(): Record<string, string[]> {
  if (collapseStore) return collapseStore;
  collapseStore = {};
  try {
    const raw = typeof window !== "undefined" ? window.localStorage.getItem(COLLAPSE_STORAGE_KEY) : null;
    const parsed = raw ? JSON.parse(raw) as unknown : null;
    if (parsed && typeof parsed === "object") {
      for (const [projectId, value] of Object.entries(parsed as Record<string, unknown>)) {
        if (Array.isArray(value)) {
          collapseStore[projectId] = [...new Set(value.filter((id): id is string => typeof id === "string"))];
        }
      }
    }
  } catch {
    // A disabled or full local store leaves the view fully expanded.
  }
  return collapseStore;
}

function writeCollapseStore(store: Record<string, string[]>): void {
  collapseStore = store;
  try {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(COLLAPSE_STORAGE_KEY, JSON.stringify(store));
    }
  } catch {
    // Local view preference only; the in-memory set still applies this session.
  }
}

export function getCollapsedWbsIds(projectId: string): ReadonlySet<string> {
  return new Set(readCollapseStore()[projectId] ?? []);
}

export function setCollapsedWbsIds(projectId: string, ids: Iterable<string>): ReadonlySet<string> {
  const next = [...new Set(ids)].sort();
  if (next.length === 0) {
    if (!(projectId in readCollapseStore())) return new Set();
    const store = { ...readCollapseStore() };
    delete store[projectId];
    writeCollapseStore(store);
    return new Set();
  }
  writeCollapseStore({ ...readCollapseStore(), [projectId]: next });
  return new Set(next);
}

/** Toggles one WBS band and returns the resulting collapsed set. */
export function toggleCollapsedWbs(projectId: string, wbsId: string): ReadonlySet<string> {
  const collapsed = getCollapsedWbsIds(projectId);
  if (collapsed.has(wbsId)) {
    const next = new Set(collapsed);
    next.delete(wbsId);
    return setCollapsedWbsIds(projectId, next);
  }
  return setCollapsedWbsIds(projectId, [...collapsed, wbsId]);
}

function sortedChildren(nodes: readonly WorkspaceWbsNode[]): Map<string | null, WorkspaceWbsNode[]> {
  const children = new Map<string | null, WorkspaceWbsNode[]>();
  for (const node of nodes) {
    const parentId = node.parentKind === "project" ? null : node.parentWbsId;
    const siblings = children.get(parentId) ?? [];
    siblings.push(node);
    children.set(parentId, siblings);
  }
  for (const siblings of children.values()) {
    siblings.sort((left, right) =>
      left.sequenceNumber - right.sequenceNumber
      || left.localCode.localeCompare(right.localCode, undefined, { sensitivity: "base" })
      || left.id.localeCompare(right.id),
    );
  }
  return children;
}

/** Depth of every WBS node, root bands first. Orphans are placed at depth 0. */
export function wbsNodeDepths(nodes: readonly WorkspaceWbsNode[]): ReadonlyMap<string, number> {
  const children = sortedChildren(nodes);
  const depths = new Map<string, number>();
  const visit = (parentId: string | null, depth: number): void => {
    for (const node of children.get(parentId) ?? []) {
      if (depths.has(node.id)) continue;
      depths.set(node.id, depth);
      visit(node.id, depth + 1);
    }
  };
  visit(null, 0);
  for (const node of nodes) {
    if (!depths.has(node.id)) depths.set(node.id, 0);
  }
  return depths;
}

function summarize(activities: readonly WorkspaceActivityRow[]): WorkspaceWbsGroupSummary {
  let startMs: number | null = null;
  let finishMs: number | null = null;
  let durationTotal = 0;
  let durationKnown = activities.length > 0;
  let weightTotal = 0;
  let progressWeighted = 0;
  for (const activity of activities) {
    const start = activity.gantt ? Date.parse(activity.gantt.start) : Number.NaN;
    const finish = activity.gantt ? Date.parse(activity.gantt.finish) : Number.NaN;
    if (Number.isFinite(start)) startMs = startMs === null ? start : Math.min(startMs, start);
    if (Number.isFinite(finish)) finishMs = finishMs === null ? finish : Math.max(finishMs, finish);

    const rawDuration = activity.cells?.duration;
    const duration = typeof rawDuration === "number" && Number.isFinite(rawDuration) ? rawDuration : null;
    if (duration === null) durationKnown = false;
    else durationTotal += duration;

    const weight = duration !== null && duration > 0 ? duration : 1;
    const progress = activity.gantt ? activity.gantt.progressPercent : 0;
    if (Number.isFinite(progress)) {
      weightTotal += weight;
      progressWeighted += Math.max(0, Math.min(100, progress)) * weight;
    }
  }
  return {
    startMs,
    finishMs,
    duration: durationKnown ? Math.round(durationTotal * 100) / 100 : null,
    progressPercent: weightTotal > 0 ? Math.round(progressWeighted / weightTotal) : null,
    activityCount: activities.length,
  };
}

/**
 * Builds the ordered table/Gantt rows. WBS bands are only emitted when
 * grouping by WBS and at least one node exists; without that, the table is the
 * flat filtered activity list and no synthetic hierarchy is invented.
 */
export function buildWorkspaceDisplayRows(
  activities: readonly WorkspaceActivityRow[],
  wbsNodes: readonly WorkspaceWbsNode[],
  groupBy: WorkspaceActivityGroupBy,
  collapsedWbsIds: ReadonlySet<string> = new Set(),
): WorkspaceDisplayRow[] {
  if (groupBy !== "wbs" || wbsNodes.length === 0) {
    return activities.map((activity) => ({
      kind: "activity" as const,
      activity,
      depth: 0,
      wbsId: activity.wbsId,
    }));
  }

  const nodeById = new Map(wbsNodes.map((node) => [node.id, node]));
  const children = sortedChildren(wbsNodes);
  const activitiesByWbs = new Map<string, WorkspaceActivityRow[]>();
  const orphanActivities: WorkspaceActivityRow[] = [];
  for (const activity of activities) {
    if (!nodeById.has(activity.wbsId)) {
      orphanActivities.push(activity);
      continue;
    }
    const group = activitiesByWbs.get(activity.wbsId) ?? [];
    group.push(activity);
    activitiesByWbs.set(activity.wbsId, group);
  }

  // One bottom-up pass computes each node's full activity set; a node is shown
  // only when it really contains at least one filtered activity.
  const subtree = new Map<string, WorkspaceActivityRow[]>();
  const collect = (node: WorkspaceWbsNode, guard: Set<string>): WorkspaceActivityRow[] => {
    const cached = subtree.get(node.id);
    if (cached) return cached;
    if (guard.has(node.id)) return [];
    guard.add(node.id);
    const members = [...(activitiesByWbs.get(node.id) ?? [])];
    for (const child of children.get(node.id) ?? []) {
      members.push(...collect(child, guard));
    }
    subtree.set(node.id, members);
    return members;
  };
  for (const node of wbsNodes) collect(node, new Set());

  const rows: WorkspaceDisplayRow[] = [];
  const visit = (node: WorkspaceWbsNode, depth: number): void => {
    const members = subtree.get(node.id) ?? [];
    if (members.length === 0) return;
    const direct = activitiesByWbs.get(node.id) ?? [];
    const childGroups = (children.get(node.id) ?? []).filter((child) => (subtree.get(child.id)?.length ?? 0) > 0);
    const hasChildren = direct.length > 0 || childGroups.length > 0;
    const collapsed = hasChildren && collapsedWbsIds.has(node.id);
    rows.push({
      kind: "wbs",
      wbsId: node.id,
      node,
      depth,
      hasChildren,
      collapsed,
      summary: summarize(members),
    });
    if (collapsed) return;
    for (const child of childGroups) visit(child, depth + 1);
    for (const activity of direct) {
      rows.push({ kind: "activity", activity, depth: depth + 1, wbsId: node.id });
    }
  };
  for (const root of children.get(null) ?? []) visit(root, 0);
  for (const node of wbsNodes) {
    if (node.parentKind !== "project" && !nodeById.has(node.parentWbsId ?? "")) visit(node, 0);
  }
  for (const activity of orphanActivities) {
    rows.push({ kind: "activity", activity, depth: 0, wbsId: activity.wbsId });
  }
  return rows;
}

/** Every WBS node that currently contains a filtered activity (any depth). */
export function collectWbsGroupIds(
  activities: readonly WorkspaceActivityRow[],
  wbsNodes: readonly WorkspaceWbsNode[],
): ReadonlySet<string> {
  if (!activities.length || !wbsNodes.length) return new Set();
  const display = buildWorkspaceDisplayRows(activities, wbsNodes, "wbs", new Set());
  return new Set(display.filter((row): row is WorkspaceWbsGroupRow => row.kind === "wbs").map((row) => row.wbsId));
}

/** Collapse All keeps the top-level WBS bands visible, as the desktop grid does. */
export function collapseAllWbsIds(
  activities: readonly WorkspaceActivityRow[],
  wbsNodes: readonly WorkspaceWbsNode[],
): ReadonlySet<string> {
  const depths = wbsNodeDepths(wbsNodes);
  const all = collectWbsGroupIds(activities, wbsNodes);
  return new Set([...all].filter((id) => (depths.get(id) ?? 0) > 0));
}

/** The target node plus every ancestor, used by "Collapse To…". */
export function wbsPathIds(nodeId: string, wbsNodes: readonly WorkspaceWbsNode[]): ReadonlySet<string> {
  const byId = new Map(wbsNodes.map((node) => [node.id, node]));
  const path = new Set<string>();
  let current = byId.get(nodeId);
  while (current && !path.has(current.id)) {
    path.add(current.id);
    current = current.parentKind === "wbs" && current.parentWbsId ? byId.get(current.parentWbsId) : undefined;
  }
  return path;
}

/** Collapses every branch except the target path, which stays open. */
export function collapseToWbsIds(
  activities: readonly WorkspaceActivityRow[],
  wbsNodes: readonly WorkspaceWbsNode[],
  targetId: string,
): ReadonlySet<string> {
  const keep = wbsPathIds(targetId, wbsNodes);
  return new Set([...collectWbsGroupIds(activities, wbsNodes)].filter((id) => !keep.has(id)));
}
