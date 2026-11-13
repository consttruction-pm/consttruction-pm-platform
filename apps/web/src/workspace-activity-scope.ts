/**
 * Activity scope arithmetic for the Version 26 Activities toolbar.
 *
 * Every count and every export row is derived from the authoritative
 * workspace read model (`state.activities`), never from rendered DOM rows or
 * a fixture constant. Collapse and grouping change only what is painted, so a
 * hidden activity remains searchable, selectable and exportable.
 *
 * Selection is presentation state: nothing in this module writes schedule
 * values or mutates a persisted activity.
 */
import type { WorkspaceActivityRow, WorkspaceCellValue, WorkspaceColumn } from "./workspace-model.js";

export type ActivityCounts = {
  /** Every activity the read model returned for the allowed project scope. */
  total: number;
  /** Activities that satisfy the checked Activity Filters. */
  filterMatched: number;
  /** Activities that satisfy the quick search inside the filtered scope. */
  searchMatched: number;
  /** Activity rows actually painted after grouping and collapse. */
  visible: number;
  /** Selected activities that still exist in the read model. */
  selected: number;
  /** Selected activities inside the current filter/search scope. */
  selectedInScope: number;
};

export type ActivityExportScope = "all" | "filtered" | "selected";

export const ACTIVITY_EXPORT_SCOPES: readonly ActivityExportScope[] = ["all", "filtered", "selected"];

export type ActivityScopeSources = {
  /** The full allowed read-model population. */
  activities: readonly WorkspaceActivityRow[];
  /** Rows after Activity Filters and the quick search (collapse is not applied). */
  filtered: readonly WorkspaceActivityRow[];
  /** Selected ids, in selection order. */
  selectedIds: readonly string[];
};

/** Resolves the stored cell for a layout column, including the identity fields. */
export function activityCellValue(activity: WorkspaceActivityRow, columnId: string): WorkspaceCellValue {
  if (columnId === "activity_id" || columnId === "activity.id") return activity.id;
  if (columnId === "activity_code" || columnId === "activity.code") return activity.code;
  if (columnId === "activity_name" || columnId === "activity.name") return activity.name;
  if (columnId === "wbs" || columnId === "activity.wbs_id") return activity.wbsId;
  return activity.cells?.[columnId] ?? null;
}

export function computeActivityCounts(args: {
  activities: readonly WorkspaceActivityRow[];
  filterMatchedIds: ReadonlySet<string>;
  /** Filter + search scope before collapse. */
  scopeActivities: readonly WorkspaceActivityRow[];
  visibleIds: readonly string[];
  selectedIds: readonly string[];
}): ActivityCounts {
  const projectIds = new Set(args.activities.map((activity) => activity.id));
  const scopeIds = new Set(args.scopeActivities.map((activity) => activity.id));
  const selected = args.selectedIds.filter((id) => projectIds.has(id));
  return {
    total: args.activities.length,
    filterMatched: [...args.filterMatchedIds].filter((id) => projectIds.has(id)).length,
    searchMatched: args.scopeActivities.length,
    visible: args.visibleIds.length,
    selected: selected.length,
    selectedInScope: selected.filter((id) => scopeIds.has(id)).length,
  };
}

/**
 * Resolves the rows an export scope must contain.
 *
 * `all` is the complete read model, `filtered` is the current filter/search
 * scope (collapsed rows included) and `selected` is exactly the in-memory
 * selection, ordered like the current scope. No scope ever adds a row the
 * user could not see or select and none drops a row by DOM presence.
 */
export function activitiesForExport(
  scope: ActivityExportScope,
  sources: ActivityScopeSources,
): readonly WorkspaceActivityRow[] {
  if (scope === "all") return sources.activities;
  if (scope === "filtered") return sources.filtered;
  const selected = new Set(sources.selectedIds);
  const ordered = sources.filtered.filter((activity) => selected.has(activity.id));
  const included = new Set(ordered.map((activity) => activity.id));
  const remaining = sources.activities.filter((activity) => selected.has(activity.id) && !included.has(activity.id));
  return [...ordered, ...remaining];
}

function csvCell(value: WorkspaceCellValue): string {
  if (value === null || value === undefined) return "";
  const text = typeof value === "boolean" ? (value ? "true" : "false") : String(value);
  if (!/[",\r\n]/u.test(text)) return text;
  return `"${text.replace(/"/gu, '""')}"`;
}

/**
 * Renders a deterministic RFC 4180 CSV from the requested layout columns.
 * The header uses the layout labels the user sees; values come from the
 * stored read model, so a hidden or collapsed row is never lost.
 */
export function activitiesToCsv(
  activities: readonly WorkspaceActivityRow[],
  columns: readonly WorkspaceColumn[],
): string {
  const header = columns.map((column) => csvCell(column.label)).join(",");
  const lines = activities.map((activity) =>
    columns.map((column) => csvCell(activityCellValue(activity, column.id))).join(","),
  );
  return [header, ...lines].join("\r\n");
}

export function activityExportFileName(scope: ActivityExportScope, projectId: string): string {
  const project = projectId.replace(/[^A-Za-z0-9._-]+/gu, "-").replace(/^-+|-+$/gu, "") || "project";
  return `${project}-activities-${scope}.csv`;
}

export function activityExportScopeCount(scope: ActivityExportScope, counts: ActivityCounts): number {
  if (scope === "all") return counts.total;
  if (scope === "filtered") return counts.searchMatched;
  return counts.selected;
}
