import type { WorkspaceColumn, WorkspaceState } from "./workspace-model.js";

export type WorkspaceSortDirection = "asc" | "desc";
export type WorkspaceSortRule = Readonly<{ fieldId: string; direction: WorkspaceSortDirection }>;
export type WorkspaceGroupRule = Readonly<{ fieldId: string }>;
export type WorkspaceFilterRule = Readonly<{
  fieldId: string;
  operator: "equals" | "contains" | "gt" | "gte" | "lt" | "lte" | "isNull" | "notNull";
  value: string | number | boolean | null;
}>;

export type WorkspaceGridQuery = Readonly<{
  sort: readonly WorkspaceSortRule[];
  group: readonly WorkspaceGroupRule[];
  filters: readonly WorkspaceFilterRule[];
}>;

export type WorkspaceSelectionHooks = Readonly<{
  selectedColumnIds: readonly string[];
  selectedActivityIds: readonly string[];
}>;

export type WorkspaceReportPrintSelection = Readonly<{
  columns: readonly WorkspaceColumn[];
  activityIds: readonly string[];
  includeGantt: boolean;
}>;

export function createEmptyGridQuery(): WorkspaceGridQuery {
  return Object.freeze({ sort: Object.freeze([]), group: Object.freeze([]), filters: Object.freeze([]) });
}

export function normalizeGridQuery(state: WorkspaceState, query: WorkspaceGridQuery): WorkspaceGridQuery {
  const known = new Set(state.columns.map((column) => column.id));
  const validField = (fieldId: string) => known.has(fieldId);
  return Object.freeze({
    sort: Object.freeze(query.sort.filter((rule) => validField(rule.fieldId))),
    group: Object.freeze(query.group.filter((rule) => validField(rule.fieldId))),
    filters: Object.freeze(query.filters.filter((rule) => validField(rule.fieldId))),
  });
}

export function createReportPrintSelection(
  state: WorkspaceState,
  selectedColumnIds: readonly string[] = [],
  selectedActivityIds: readonly string[] = [],
  includeGantt = true,
): WorkspaceReportPrintSelection {
  const columnIds = selectedColumnIds.length
    ? new Set(selectedColumnIds)
    : new Set(state.columns.map((column) => column.id));
  const activityIds = selectedActivityIds.length
    ? new Set(selectedActivityIds)
    : new Set(state.activities.map((activity) => activity.id));

  return Object.freeze({
    columns: Object.freeze(state.columns.filter((column) => columnIds.has(column.id))),
    activityIds: Object.freeze(state.activities.filter((activity) => activityIds.has(activity.id)).map((activity) => activity.id)),
    includeGantt,
  });
}
