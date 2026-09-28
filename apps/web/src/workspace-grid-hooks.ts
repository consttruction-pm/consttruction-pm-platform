import type { WorkspaceColumn, WorkspaceState } from "./workspace-model.js";
import type { P6FieldCatalogEntry } from "./p6-field-registry-client.js";
import type { WorkspaceLayout } from "./workspace-layout.js";

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

export type WorkspaceGridColumn = WorkspaceColumn &
  Readonly<{
    fieldId: string;
    alignment: "start" | "center" | "end";
    pinned: boolean;
    frozen: boolean;
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

/**
 * Projects the authoritative Field Catalog + persisted Layout into the grid view.
 * The client only projects display metadata; it does not calculate schedule values.
 */
export function projectGridColumns(
  layout: WorkspaceLayout,
  catalog: readonly P6FieldCatalogEntry[],
): readonly WorkspaceGridColumn[] {
  const byId = new Map(catalog.filter((field) => field.subjectArea === layout.subject_area).map((field) => [field.id, field]));
  return Object.freeze(
    [...layout.columns]
      .filter((column) => column.visible)
      .sort((a, b) => a.order - b.order)
      .flatMap((column) => {
        const field = byId.get(column.fieldId);
        if (!field) return [];
        return [
          Object.freeze({
            id: field.id,
            fieldId: field.id,
            label: column.labelOverride ?? field.label,
            dataType:
              field.dataType === "integer"
                ? "integer"
                : field.dataType === "decimal" ||
                    field.dataType === "double" ||
                    field.dataType === "percentage" ||
                    field.dataType === "cost" ||
                    field.dataType === "unit"
                  ? "decimal"
                  : field.dataType === "date" || field.dataType === "datetime"
                    ? "date"
                    : field.dataType === "duration"
                      ? "duration"
                      : field.dataType === "boolean"
                        ? "boolean"
                        : "text",
            editable: field.writable && !field.computed,
            formula: null,
            width: column.width,
            alignment: column.alignment,
            pinned: column.pinned,
            frozen: column.frozen,
          }),
        ];
      }),
  );
}

export function normalizeGridQuery(
  state: WorkspaceState,
  query: WorkspaceGridQuery,
  catalog: readonly P6FieldCatalogEntry[] = [],
): WorkspaceGridQuery {
  const known = new Set(state.columns.map((column) => column.id));
  const catalogById = new Map(catalog.map((field) => [field.id, field]));
  const validField = (fieldId: string) => known.has(fieldId) && (!catalog.length || catalogById.has(fieldId));
  const canSort = (fieldId: string) => validField(fieldId) && (!catalog.length || catalogById.get(fieldId)?.orderable === true);
  const canFilter = (fieldId: string) => validField(fieldId) && (!catalog.length || catalogById.get(fieldId)?.filterable === true);
  const canGroup = canSort;
  return Object.freeze({
    sort: Object.freeze(query.sort.filter((rule) => canSort(rule.fieldId))),
    group: Object.freeze(query.group.filter((rule) => canGroup(rule.fieldId))),
    filters: Object.freeze(query.filters.filter((rule) => canFilter(rule.fieldId))),
  });
}

export function createReportPrintSelection(
  state: WorkspaceState,
  selectedColumnIds: readonly string[] = [],
  selectedActivityIds: readonly string[] = [],
  includeGantt = true,
  layout?: WorkspaceLayout,
): WorkspaceReportPrintSelection {
  const orderedColumns = layout
    ? [...layout.columns].sort((a, b) => a.order - b.order).filter((column) => column.visible)
        .map((column) => state.columns.find((item) => item.id === column.fieldId))
        .filter((column): column is WorkspaceColumn => Boolean(column))
    : [...state.columns];
  const columnIds = selectedColumnIds.length
    ? new Set(selectedColumnIds)
    : new Set(orderedColumns.map((column) => column.id));
  const activityIds = selectedActivityIds.length
    ? new Set(selectedActivityIds)
    : new Set(state.activities.map((activity) => activity.id));

  return Object.freeze({
    columns: Object.freeze(orderedColumns.filter((column) => columnIds.has(column.id))),
    activityIds: Object.freeze(state.activities.filter((activity) => activityIds.has(activity.id)).map((activity) => activity.id)),
    includeGantt,
  });
}
