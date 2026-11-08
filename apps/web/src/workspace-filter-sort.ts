import type {
  WorkspaceActivityGroupBy,
  WorkspaceActivityRow,
  WorkspaceActivitySort,
  WorkspaceCellValue,
  WorkspaceWbsNode,
} from "./workspace-model.js";

function cellValue(activity: WorkspaceActivityRow, columnId: string): WorkspaceCellValue {
  if (columnId === "activity_id") return activity.id;
  if (columnId === "activity_code") return activity.code;
  if (columnId === "activity_name") return activity.name;
  if (columnId === "wbs") return activity.wbsId;
  return activity.cells?.[columnId] ?? null;
}

function searchableText(activity: WorkspaceActivityRow): string {
  const values: string[] = [activity.id, activity.code, activity.name, activity.wbsId];
  if (activity.cells) {
    for (const value of Object.values(activity.cells)) {
      if (value !== null && value !== undefined) values.push(String(value));
    }
  }
  return values.join(" ").toLocaleLowerCase();
}

/**
 * Filters and sorts persisted activity rows for display only. It never
 * calculates schedule values and never changes the underlying rows.
 */
/**
 * Filters and groups persisted activity rows for display only. Group order follows
 * the WBS tree; an optional secondary sort is applied inside each WBS group.
 * The browser never changes rows or calculates schedule values.
 */
export function filterAndSortActivities(
  activities: readonly WorkspaceActivityRow[],
  filterText: string,
  sort: WorkspaceActivitySort | null,
  groupBy: WorkspaceActivityGroupBy = "none",
  wbsNodes: readonly WorkspaceWbsNode[] = [],
  sortLevels: readonly WorkspaceActivitySort[] = [],
): readonly WorkspaceActivityRow[] {
  const tokens = filterText
    .trim()
    .toLocaleLowerCase()
    .split(/\s+/u)
    .filter((token) => token.length > 0);

  let rows: readonly WorkspaceActivityRow[] = activities;
  if (tokens.length > 0) {
    rows = activities.filter((activity) => {
      const text = searchableText(activity);
      return tokens.every((token) => text.includes(token));
    });
  }

  const levels = sortLevels.length > 0 ? sortLevels : sort ? [sort] : [];
  const wbsOrder = buildWbsOrder(wbsNodes);
  const wbsRanks = new Map(wbsOrder.map((id, index) => [id, index] as const));

  if (groupBy === "wbs") {
    const groups = new Map<string, WorkspaceActivityRow[]>();
    for (const row of rows) {
      const group = groups.get(row.wbsId) ?? [];
      group.push(row);
      groups.set(row.wbsId, group);
    }
    const orderedGroups = [...groups.keys()].sort((left, right) =>
      compareWbsIds(left, right, wbsRanks),
    );
    return orderedGroups.flatMap((wbsId) => {
      const members = groups.get(wbsId) ?? [];
      // WBS is the primary grouping key, so it is removed from the in-group
      // sort plan. Remaining levels apply in the documented order.
      const memberLevels = levels.filter((level) => level.columnId !== "wbs");
      if (memberLevels.length === 0) return members;
      return [...members].sort((left, right) =>
        compareRowsByLevels(left, right, memberLevels, wbsRanks),
      );
    });
  }

  if (levels.length === 0) return rows;
  return [...rows].sort((left, right) => compareRowsByLevels(left, right, levels, wbsRanks));
}

function compareRowsByLevels(
  left: WorkspaceActivityRow,
  right: WorkspaceActivityRow,
  levels: readonly WorkspaceActivitySort[],
  wbsRanks: ReadonlyMap<string, number>,
): number {
  for (const level of levels) {
    const result = compareRows(left, right, level, wbsRanks);
    if (result !== 0) return result;
  }
  // A stable, deterministic tie-break only after every requested level.
  return naturalCompare(left.id, right.id);
}

function buildWbsOrder(nodes: readonly WorkspaceWbsNode[]): string[] {
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
      || naturalCompare(left.localCode, right.localCode)
      || naturalCompare(left.id, right.id),
    );
  }

  const ordered: string[] = [];
  const visited = new Set<string>();
  const visit = (parentId: string | null): void => {
    for (const node of children.get(parentId) ?? []) {
      if (visited.has(node.id)) continue;
      visited.add(node.id);
      ordered.push(node.id);
      visit(node.id);
    }
  };
  visit(null);
  // Keep orphaned/cyclic nodes deterministic and visible rather than dropping them.
  for (const node of nodes) {
    if (visited.has(node.id)) continue;
    visited.add(node.id);
    ordered.push(node.id);
    visit(node.id);
  }
  return ordered;
}

function compareWbsIds(
  leftId: string,
  rightId: string,
  ranks: ReadonlyMap<string, number>,
): number {
  if (leftId === rightId) return 0;
  const leftRank = ranks.get(leftId);
  const rightRank = ranks.get(rightId);
  if (leftRank !== undefined && rightRank !== undefined && leftRank !== rightRank) {
    return leftRank < rightRank ? -1 : 1;
  }
  if (leftRank !== undefined && rightRank === undefined) return -1;
  if (leftRank === undefined && rightRank !== undefined) return 1;
  return naturalCompare(leftId, rightId);
}

function compareRows(
  left: WorkspaceActivityRow,
  right: WorkspaceActivityRow,
  sort: WorkspaceActivitySort,
  wbsRanks: ReadonlyMap<string, number>,
): number {
  const direction = sort.direction === "desc" ? -1 : 1;
  if (sort.columnId === "wbs") {
    return direction * compareWbsIds(left.wbsId, right.wbsId, wbsRanks);
  }
  const a = cellValue(left, sort.columnId);
  const b = cellValue(right, sort.columnId);
  const aMissing = a === null || a === undefined || a === "";
  const bMissing = b === null || b === undefined || b === "";
  if (aMissing || bMissing) {
    if (aMissing && bMissing) return 0;
    // Blank values stay at the end regardless of the sort direction.
    return aMissing ? 1 : -1;
  }
  return direction * compareValues(a, b);
}

function compareValues(a: WorkspaceCellValue, b: WorkspaceCellValue): number {
  if (typeof a === "number" && typeof b === "number") {
    return a === b ? 0 : a < b ? -1 : 1;
  }
  if (typeof a === "boolean" && typeof b === "boolean") {
    return a === b ? 0 : a ? -1 : 1;
  }
  return naturalCompare(String(a), String(b));
}

function naturalCompare(left: string, right: string): number {
  const leftParts = left.match(/\d+|\D+/gu) ?? [];
  const rightParts = right.match(/\d+|\D+/gu) ?? [];
  const length = Math.max(leftParts.length, rightParts.length);
  for (let index = 0; index < length; index += 1) {
    const a = leftParts[index];
    const b = rightParts[index];
    if (a === undefined) return -1;
    if (b === undefined) return 1;
    const aNumeric = /^\d+$/u.test(a);
    const bNumeric = /^\d+$/u.test(b);
    if (aNumeric && bNumeric) {
      const difference = Number(a) - Number(b);
      if (difference !== 0) return difference < 0 ? -1 : 1;
      continue;
    }
    const comparison = a.localeCompare(b, undefined, { sensitivity: "base" });
    if (comparison !== 0) return comparison < 0 ? -1 : 1;
  }
  return 0;
}
