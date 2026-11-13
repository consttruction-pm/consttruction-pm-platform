import type { WorkspaceWbsNode } from "./workspace-model.js";

/**
 * One row of the authoritative WBS hierarchy in display order.
 *
 * `depth` is 1-based so it can be written directly to `aria-level`. Nodes whose
 * parent is missing from the loaded snapshot are promoted to the project root
 * (never dropped) and flagged with `orphan`, so a partial read degrades visibly
 * instead of silently hiding persisted records.
 */
export type WbsHierarchyRow = {
  node: WorkspaceWbsNode;
  depth: number;
  hasChildren: boolean;
  orphan: boolean;
};

function siblingOrder(a: WorkspaceWbsNode, b: WorkspaceWbsNode): number {
  return (
    a.sequenceNumber - b.sequenceNumber ||
    a.localCode.localeCompare(b.localCode) ||
    a.id.localeCompare(b.id)
  );
}

/**
 * Flatten the loaded WBS nodes into project order.
 *
 * The result is the single ordering source for both the table and chart views:
 * siblings sort by sequence number, then local code, then ID; descendants are
 * emitted depth-first immediately after their parent. Cycles and duplicate
 * parent links cannot produce an infinite walk or duplicate rows because every
 * node ID is visited at most once.
 */
export function buildWbsHierarchy(nodes: readonly WorkspaceWbsNode[]): WbsHierarchyRow[] {
  const byId = new Map<string, WorkspaceWbsNode>();
  for (const node of nodes) {
    if (!byId.has(node.id)) byId.set(node.id, node);
  }
  const children = new Map<string, WorkspaceWbsNode[]>();
  const roots: WorkspaceWbsNode[] = [];
  const orphans = new Set<string>();
  for (const node of byId.values()) {
    const parentId = node.parentKind === "wbs" ? node.parentWbsId : null;
    if (!parentId || !byId.has(parentId) || parentId === node.id) {
      roots.push(node);
      if (parentId && parentId !== node.id && !byId.has(parentId)) orphans.add(node.id);
      continue;
    }
    const siblings = children.get(parentId) ?? [];
    siblings.push(node);
    children.set(parentId, siblings);
  }
  roots.sort(siblingOrder);
  for (const siblings of children.values()) siblings.sort(siblingOrder);

  const rows: WbsHierarchyRow[] = [];
  const visited = new Set<string>();
  const walk = (node: WorkspaceWbsNode, depth: number): void => {
    if (visited.has(node.id)) return;
    visited.add(node.id);
    const nested = (children.get(node.id) ?? []).filter((child) => !visited.has(child.id));
    rows.push({
      node,
      depth,
      hasChildren: (children.get(node.id) ?? []).length > 0,
      orphan: orphans.has(node.id),
    });
    for (const child of nested) walk(child, depth + 1);
  };
  for (const root of roots) walk(root, 1);

  // A pure cycle has no root; emit its nodes once at the root level rather than
  // pretending the project has no WBS. The server rejects cycles, so this path
  // only reflects a damaged snapshot.
  for (const node of byId.values()) {
    if (!visited.has(node.id)) {
      walk(node, 1);
    }
  }
  return rows;
}

/** Activity counts per WBS node, keyed by the persisted WBS ID. */
export function wbsActivityCounts(
  activities: readonly { wbsId: string }[],
): ReadonlyMap<string, number> {
  const counts = new Map<string, number>();
  for (const activity of activities) {
    counts.set(activity.wbsId, (counts.get(activity.wbsId) ?? 0) + 1);
  }
  return counts;
}

/** The selected node plus every descendant, using the same ordering rules. */
export function wbsSubtreeIds(
  nodes: readonly WorkspaceWbsNode[],
  wbsId: string,
): ReadonlySet<string> {
  const ids = new Set<string>();
  const rows = buildWbsHierarchy(nodes);
  const start = rows.findIndex((row) => row.node.id === wbsId);
  if (start < 0) return ids;
  const depth = rows[start].depth;
  ids.add(wbsId);
  for (let index = start + 1; index < rows.length; index += 1) {
    if (rows[index].depth <= depth) break;
    ids.add(rows[index].node.id);
  }
  return ids;
}
