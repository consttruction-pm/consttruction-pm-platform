import type {
  WorkspaceActivityRow,
  WorkspaceActivitySort,
  WorkspaceCellValue,
} from "./workspace-model.js";

function cellValue(activity: WorkspaceActivityRow, columnId: string): WorkspaceCellValue {
  if (columnId === "activity_id") return activity.id;
  if (columnId === "activity_code") return activity.code;
  if (columnId === "activity_name") return activity.name;
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
 * calculates schedule values and never changes the underlying rows. The
 * optional WBS filter follows a server-provided group identity; it is an
 * exact match, not a text search.
 */
export function filterAndSortActivities(
  activities: readonly WorkspaceActivityRow[],
  filterText: string,
  sort: WorkspaceActivitySort | null,
  wbsId: string | null = null,
): readonly WorkspaceActivityRow[] {
  const tokens = filterText
    .trim()
    .toLocaleLowerCase()
    .split(/\s+/u)
    .filter((token) => token.length > 0);

  let rows: readonly WorkspaceActivityRow[] =
    wbsId === null ? activities : activities.filter((activity) => activity.wbsId === wbsId);
  if (tokens.length > 0) {
    rows = rows.filter((activity) => {
      const text = searchableText(activity);
      return tokens.every((token) => text.includes(token));
    });
  }

  if (!sort) return rows;
  const direction = sort.direction === "desc" ? -1 : 1;
  return [...rows].sort((left, right) => {
    const a = cellValue(left, sort.columnId);
    const b = cellValue(right, sort.columnId);
    const aMissing = a === null || a === undefined || a === "";
    const bMissing = b === null || b === undefined || b === "";
    if (aMissing || bMissing) {
      if (aMissing && bMissing) return naturalCompare(left.id, right.id);
      return aMissing ? 1 : -1;
    }
    return direction * compareValues(a, b, left.id, right.id);
  });
}

function compareValues(
  a: WorkspaceCellValue,
  b: WorkspaceCellValue,
  leftId: string,
  rightId: string,
): number {
  if (typeof a === "number" && typeof b === "number") {
    return a === b ? naturalCompare(leftId, rightId) : a < b ? -1 : 1;
  }
  if (typeof a === "boolean" && typeof b === "boolean") {
    return a === b ? naturalCompare(leftId, rightId) : a ? -1 : 1;
  }
  return naturalCompare(String(a), String(b)) || naturalCompare(leftId, rightId);
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
