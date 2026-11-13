/**
 * Group and sort settings travel with the saved Activities layout.
 *
 * The layout contract already carries an opaque metadata record (the same one
 * that stores table presentation). Storing the group mode and the ordered sort
 * plan there lets a reload or a layout switch restore the table the user saved
 * without adding schedule data to the layout or changing any activity row.
 */
import type { LayoutDefinition } from "./p6-field-layout-foundation.js";
import type {
  WorkspaceActivityGroupBy,
  WorkspaceActivitySortLevel,
} from "./workspace-model.js";

export const GROUP_SORT_METADATA_KEY = "groupSort";
export const GROUP_SORT_UPDATED_KEY = "groupSortUpdatedAt";
export const WBS_COLLAPSE_METADATA_KEY = "wbsCollapse";
export const MAX_LAYOUT_SORT_LEVELS = 3;
export const MAX_SAVED_COLLAPSED_WBS = 500;

export type SavedGroupSort = {
  groupBy: WorkspaceActivityGroupBy;
  sortLevels: readonly WorkspaceActivitySortLevel[];
};

/**
 * Reads a stored group/sort plan. Unknown modes, malformed levels and extra
 * fields are dropped rather than trusted; null means the layout never stored
 * one and the current workspace defaults stay in place.
 */
export function readGroupSortMetadata(
  metadata: Readonly<Record<string, unknown>> | undefined,
): SavedGroupSort | null {
  const raw = metadata?.[GROUP_SORT_METADATA_KEY];
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const record = raw as Record<string, unknown>;
  if (record.groupBy !== "wbs" && record.groupBy !== "none") return null;
  const sortLevels: WorkspaceActivitySortLevel[] = [];
  if (Array.isArray(record.sortLevels)) {
    for (const item of record.sortLevels) {
      if (sortLevels.length >= MAX_LAYOUT_SORT_LEVELS) break;
      if (!item || typeof item !== "object" || Array.isArray(item)) continue;
      const level = item as Record<string, unknown>;
      if (typeof level.columnId !== "string" || level.columnId.trim() === "") continue;
      sortLevels.push({
        columnId: level.columnId,
        direction: level.direction === "desc" ? "desc" : "asc",
      });
    }
  }
  return { groupBy: record.groupBy, sortLevels };
}

/** Metadata fields to merge into a layout definition that is being saved. */
export function groupSortMetadata(
  groupBy: WorkspaceActivityGroupBy,
  sortLevels: readonly WorkspaceActivitySortLevel[],
  updatedAt: number,
): Readonly<Record<string, unknown>> {
  return {
    [GROUP_SORT_METADATA_KEY]: {
      groupBy,
      sortLevels: sortLevels.slice(0, MAX_LAYOUT_SORT_LEVELS).map((level) => ({
        columnId: level.columnId,
        direction: level.direction === "desc" ? "desc" : "asc",
      })),
    },
    [GROUP_SORT_UPDATED_KEY]: Math.max(0, Math.round(updatedAt)),
  };
}

/** Returns the layout with the current group/sort plan merged into metadata. */
export function withGroupSortMetadata(
  layout: LayoutDefinition,
  groupBy: WorkspaceActivityGroupBy,
  sortLevels: readonly WorkspaceActivitySortLevel[],
  updatedAt: number,
): LayoutDefinition {
  return {
    ...layout,
    metadata: {
      ...(layout.metadata ?? {}),
      ...groupSortMetadata(groupBy, sortLevels, updatedAt),
    },
  };
}

/**
 * Reads the collapsed WBS branches a layout was saved with. A missing key means
 * the layout never stored a collapse preference (the current view stays as it
 * is); an empty array means the author saved every branch expanded.
 */
export function readCollapsedWbsMetadata(
  metadata: Readonly<Record<string, unknown>> | undefined,
): ReadonlySet<string> | null {
  const raw = metadata?.[WBS_COLLAPSE_METADATA_KEY];
  if (raw === undefined || raw === null || !Array.isArray(raw)) return null;
  const ids = new Set<string>();
  for (const item of raw) {
    if (ids.size >= MAX_SAVED_COLLAPSED_WBS) break;
    if (typeof item !== "string") continue;
    const id = item.trim();
    if (id !== "") ids.add(id);
  }
  return ids;
}

/** Collapsed WBS ids to store inside a layout definition that is being saved. */
export function collapsedWbsMetadata(ids: Iterable<string>): Readonly<Record<string, unknown>> {
  const collapsed: string[] = [];
  const seen = new Set<string>();
  for (const item of ids) {
    if (typeof item !== "string") continue;
    const id = item.trim();
    if (id === "" || seen.has(id) || collapsed.length >= MAX_SAVED_COLLAPSED_WBS) continue;
    seen.add(id);
    collapsed.push(id);
  }
  collapsed.sort();
  return { [WBS_COLLAPSE_METADATA_KEY]: collapsed };
}

/** Returns the layout with the current collapsed branches merged into metadata. */
export function withCollapsedWbsMetadata(
  layout: LayoutDefinition,
  ids: Iterable<string>,
): LayoutDefinition {
  return {
    ...layout,
    metadata: {
      ...(layout.metadata ?? {}),
      ...collapsedWbsMetadata(ids),
    },
  };
}
