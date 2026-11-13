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
  WorkspaceActivityGroupLevel,
  WorkspaceActivityRow,
  WorkspaceCellValue,
  WorkspaceWbsNode,
} from "./workspace-model.js";
import {
  compareGroupBands,
  groupFieldValue,
  groupValueKey,
  groupValueLabel,
  naturalCompare,
} from "./workspace-grouping.js";

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
  /**
   * Collapse token for this band. A top-level WBS band uses the node id (the
   * long-standing view preference); a WBS band nested under a field band is
   * prefixed with its parent path so each occurrence collapses independently.
   */
  bandKey: string;
  /** Zero-based group plan level that produced this band. */
  level: number;
  node: WorkspaceWbsNode;
  /** 0 for a root WBS band. */
  depth: number;
  hasChildren: boolean;
  collapsed: boolean;
  summary: WorkspaceWbsGroupSummary;
};

/**
 * A band produced by a non-WBS group level. Its label is the persisted value
 * of the grouped field; the summary is derived from the same child activities
 * the project read model returned.
 */
export type WorkspaceFieldGroupRow = {
  kind: "fieldGroup";
  bandKey: string;
  fieldId: string;
  /** Canonical value key (``\u0000none`` for rows without a value). */
  valueKey: string;
  /** Localized display label for the band. */
  label: string;
  /** Zero-based group plan level that produced this band. */
  level: number;
  /** 0 for an outer band. */
  depth: number;
  hasChildren: boolean;
  collapsed: boolean;
  summary: WorkspaceWbsGroupSummary;
};

export type WorkspaceBandRow = WorkspaceWbsGroupRow | WorkspaceFieldGroupRow;

export type WorkspaceActivityDisplayRow = {
  kind: "activity";
  activity: WorkspaceActivityRow;
  /** 0 without grouping, otherwise one deeper than the innermost band. */
  depth: number;
  wbsId: string;
};

export type WorkspaceDisplayRow = WorkspaceBandRow | WorkspaceActivityDisplayRow;

export function isWorkspaceBandRow(row: WorkspaceDisplayRow): row is WorkspaceBandRow {
  return row.kind === "wbs" || row.kind === "fieldGroup";
}

export type WbsTreeGuide = {
  depth: number;
  /**
   * One entry per ancestor level. `true` means that ancestor still has a
   * following sibling, so its vertical rail must continue through this row.
   * `false` means the rail stops at the ancestor's last descendant.
   */
  rails: readonly boolean[];
  /** This row is the last child of its parent in the visible tree. */
  lastChild: boolean;
  hasChildren: boolean;
  collapsed: boolean;
};

/**
 * Derives tree drawing guides from the already ordered display rows. It only
 * describes parent/child/sibling relationships in the visible list; it never
 * changes row order or grouping.
 */
export function buildWbsTreeGuides(rows: readonly WorkspaceDisplayRow[]): readonly WbsTreeGuide[] {
  const depth = rows.map((row) => Math.max(0, Math.round(row.depth)));
  const last = depth.map((rowDepth, index) => {
    for (let next = index + 1; next < rows.length; next += 1) {
      if (depth[next] < rowDepth) return true;
      if (depth[next] === rowDepth) return false;
    }
    return true;
  });
  const lastAtDepth: number[] = [];
  return rows.map((row, index) => {
    const rowDepth = depth[index];
    const rails: boolean[] = [];
    // The column immediately before a node is the node's own elbow. Every
    // further-left column belongs to an ancestor two or more levels up; it
    // continues only while that ancestor still has a following sibling.
    for (let level = 0; level < Math.max(0, rowDepth - 1); level += 1) {
      const ancestor = lastAtDepth[level + 1];
      rails.push(ancestor !== undefined && !last[ancestor]);
    }
    lastAtDepth.length = rowDepth + 1;
    lastAtDepth[rowDepth] = index;
    return Object.freeze({
      depth: rowDepth,
      rails: Object.freeze(rails),
      lastChild: last[index],
      hasChildren: row.kind === "wbs" || row.kind === "fieldGroup" ? row.hasChildren : false,
      collapsed: row.kind === "wbs" || row.kind === "fieldGroup" ? row.collapsed : false,
    });
  });
}

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
 * Builds the ordered table/Gantt rows for an ordered group plan.
 *
 * Bands are emitted only for groups that really contain at least one filtered
 * activity, so a group level never invents an empty band. WBS levels walk the
 * persisted node tree in sequence order; field levels order sibling bands by
 * the persisted value with the configured direction. Rows inside the innermost
 * band keep the caller's sort order — the builder never re-sorts activities.
 *
 * ``groupLevels`` wins when present; otherwise the legacy ``groupBy`` flag is
 * mapped to the single-level WBS plan it has always meant.
 */
export function buildWorkspaceDisplayRows(
  activities: readonly WorkspaceActivityRow[],
  wbsNodes: readonly WorkspaceWbsNode[],
  groupBy: WorkspaceActivityGroupBy,
  collapsedWbsIds: ReadonlySet<string> = new Set(),
  groupLevels: readonly WorkspaceActivityGroupLevel[] = [],
  locale = "en",
): WorkspaceDisplayRow[] {
  const levels = groupLevels.length > 0
    ? groupLevels
    : groupBy === "wbs" ? [{ fieldId: "wbs", direction: "asc" as const }] : [];
  if (levels.length === 0) {
    return activities.map((activity) => ({
      kind: "activity" as const,
      activity,
      depth: 0,
      wbsId: activity.wbsId,
    }));
  }

  const rows: WorkspaceDisplayRow[] = [];
  const index = wbsNodes.length > 0 ? buildWbsIndex(wbsNodes) : null;

  const emit = (members: readonly WorkspaceActivityRow[], levelIndex: number, depth: number, parentKey: string): void => {
    if (members.length === 0) return;
    if (levelIndex >= levels.length) {
      for (const activity of members) {
        rows.push({ kind: "activity", activity, depth, wbsId: activity.wbsId });
      }
      return;
    }
    const level = levels[levelIndex];
    if (level.fieldId === "wbs") {
      emitWbs(members, levelIndex, depth, parentKey);
      return;
    }
    emitField(members, level, levelIndex, depth, parentKey);
  };

  const emitField = (
    members: readonly WorkspaceActivityRow[],
    level: WorkspaceActivityGroupLevel,
    levelIndex: number,
    depth: number,
    parentKey: string,
  ): void => {
    const groups = new Map<string, { value: WorkspaceCellValue; members: WorkspaceActivityRow[] }>();
    for (const activity of members) {
      const value = groupFieldValue(activity, level.fieldId);
      const key = groupValueKey(value);
      const group = groups.get(key) ?? { value, members: [] };
      group.members.push(activity);
      groups.set(key, group);
    }
    const ordered = [...groups.entries()].sort(([leftKey, left], [rightKey, right]) =>
      compareGroupBands(left.value, right.value, level.direction) || naturalCompare(leftKey, rightKey));
    for (const [key, group] of ordered) {
      const bandKey = parentKey ? `${parentKey}>${level.fieldId}:${key}` : `field:${level.fieldId}:${key}`;
      const collapsed = collapsedWbsIds.has(bandKey);
      rows.push({
        kind: "fieldGroup",
        bandKey,
        fieldId: level.fieldId,
        valueKey: key,
        label: groupValueLabel(level.fieldId, group.value, locale),
        level: levelIndex,
        depth,
        hasChildren: true,
        collapsed,
        summary: summarize(group.members),
      });
      if (collapsed) continue;
      emit(group.members, levelIndex + 1, depth + 1, bandKey);
    }
  };

  const emitWbs = (
    members: readonly WorkspaceActivityRow[],
    levelIndex: number,
    depth: number,
    parentKey: string,
  ): void => {
    const tree = index;
    if (!tree) {
      // No WBS hierarchy is loaded, so this level cannot form bands. Skip it
      // and keep the deeper levels / activities rather than inventing bands
      // from raw database ids (the table stays flat for a bare project).
      emit(members, levelIndex + 1, depth, parentKey);
      return;
    }
    const activitiesByWbs = new Map<string, WorkspaceActivityRow[]>();
    const orphans: WorkspaceActivityRow[] = [];
    for (const activity of members) {
      if (!tree.nodeById.has(activity.wbsId)) {
        orphans.push(activity);
        continue;
      }
      const group = activitiesByWbs.get(activity.wbsId) ?? [];
      group.push(activity);
      activitiesByWbs.set(activity.wbsId, group);
    }
    // One bottom-up pass computes each node's full activity set; a node is
    // shown only when it really contains at least one filtered activity.
    const subtree = new Map<string, WorkspaceActivityRow[]>();
    const collect = (node: WorkspaceWbsNode, guard: Set<string>): WorkspaceActivityRow[] => {
      const cached = subtree.get(node.id);
      if (cached) return cached;
      if (guard.has(node.id)) return [];
      guard.add(node.id);
      const collected = [...(activitiesByWbs.get(node.id) ?? [])];
      for (const child of tree.children.get(node.id) ?? []) {
        collected.push(...collect(child, guard));
      }
      subtree.set(node.id, collected);
      return collected;
    };
    for (const node of wbsNodes) collect(node, new Set());

    const visit = (node: WorkspaceWbsNode, nodeDepth: number): void => {
      const nodeMembers = subtree.get(node.id) ?? [];
      if (nodeMembers.length === 0) return;
      const direct = activitiesByWbs.get(node.id) ?? [];
      const childGroups = (tree.children.get(node.id) ?? []).filter((child) => (subtree.get(child.id)?.length ?? 0) > 0);
      const hasChildren = direct.length > 0 || childGroups.length > 0;
      // A top-level WBS band keeps the node id so the long-standing per-project
      // collapse preference and "Collapse To" continue to address it.
      const bandKey = parentKey ? `${parentKey}>wbs:${node.id}` : node.id;
      const collapsed = hasChildren && collapsedWbsIds.has(bandKey);
      rows.push({
        kind: "wbs",
        wbsId: node.id,
        bandKey,
        level: levelIndex,
        node,
        depth: depth + nodeDepth,
        hasChildren,
        collapsed,
        summary: summarize(nodeMembers),
      });
      if (collapsed) return;
      for (const child of childGroups) visit(child, nodeDepth + 1);
      if (direct.length > 0) emit(direct, levelIndex + 1, depth + nodeDepth + 1, bandKey);
    };
    for (const root of tree.children.get(null) ?? []) visit(root, 0);
    for (const node of wbsNodes) {
      if (node.parentKind !== "project" && !tree.nodeById.has(node.parentWbsId ?? "")) visit(node, 0);
    }
    // Orphans keep the caller's order and sit outside the tree, as before.
    emit(orphans, levelIndex + 1, depth, parentKey);
  };

  emit(activities, 0, 0, "");
  return rows;
}

type WbsIndex = {
  nodeById: ReadonlyMap<string, WorkspaceWbsNode>;
  children: ReadonlyMap<string | null, WorkspaceWbsNode[]>;
};

function buildWbsIndex(wbsNodes: readonly WorkspaceWbsNode[]): WbsIndex {
  return {
    nodeById: new Map(wbsNodes.map((node) => [node.id, node])),
    children: sortedChildren(wbsNodes),
  };
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
