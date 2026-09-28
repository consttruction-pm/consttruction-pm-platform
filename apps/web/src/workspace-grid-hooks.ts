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
  layout?: WorkspaceLayout,
): WorkspaceGridQuery {
  const known = new Set(state.columns.map((column) => column.id));
  const catalogById = new Map(catalog.map((field) => [field.id, field]));
  const layoutFields = layout
    ? new Set(layout.columns.map((column) => column.fieldId))
    : null;
  const validField = (fieldId: string) => {
    if (!known.has(fieldId)) return false;
    const field = catalogById.get(fieldId);
    if (catalog.length && (!field || (layout && field.subjectArea !== layout.subject_area))) return false;
    if (layoutFields && !layoutFields.has(fieldId)) return false;
    return true;
  };
  const canSort = (fieldId: string) => validField(fieldId) && (!catalog.length || catalogById.get(fieldId)?.orderable === true);
  const canFilter = (fieldId: string) => validField(fieldId) && (!catalog.length || catalogById.get(fieldId)?.filterable === true);
  const canGroup = canSort;
  const canUseOperator = (fieldId: string, operator: WorkspaceFilterRule["operator"]) => {
    if (!canFilter(fieldId)) return false;
    const field = catalogById.get(fieldId);
    if (!field) return true;
    return isFilterOperatorAllowed(field.dataType, operator);
  };

  const sort: WorkspaceSortRule[] = [];
  const sortSeen = new Set<string>();
  for (const rule of query.sort) {
    if (!canSort(rule.fieldId) || sortSeen.has(rule.fieldId)) continue;
    sortSeen.add(rule.fieldId);
    sort.push(Object.freeze({ ...rule }));
  }

  const group: WorkspaceGroupRule[] = [];
  const groupSeen = new Set<string>();
  for (const rule of query.group) {
    if (!canGroup(rule.fieldId) || groupSeen.has(rule.fieldId)) continue;
    groupSeen.add(rule.fieldId);
    group.push(Object.freeze({ ...rule }));
  }

  const filters = query.filters
    .filter((rule) => canUseOperator(rule.fieldId, rule.operator))
    .map((rule) => Object.freeze({ ...rule }));

  return Object.freeze({
    sort: Object.freeze(sort),
    group: Object.freeze(group),
    filters: Object.freeze(filters),
  });
}

function isFilterOperatorAllowed(
  dataType: P6FieldCatalogEntry["dataType"],
  operator: WorkspaceFilterRule["operator"],
): boolean {
  if (operator === "isNull" || operator === "notNull") return true;

  switch (dataType) {
    case "string":
    case "enum":
      return operator === "equals" || operator === "contains";
    case "integer":
    case "decimal":
    case "double":
    case "percentage":
    case "cost":
    case "unit":
    case "duration":
    case "date":
    case "datetime":
      return operator === "equals" || operator === "gt" || operator === "gte" || operator === "lt" || operator === "lte";
    case "boolean":
      return operator === "equals";
    case "object-id":
    case "object-id-array":
    case "string-array":
    case "complex":
    case "spread":
      return operator === "equals";
    default:
      return false;
  }
}

export function createReportPrintSelection(
  state: WorkspaceState,
  selectedColumnIds: readonly string[] = [],
  selectedActivityIds: readonly string[] = [],
  includeGantt = true,
  layout?: WorkspaceLayout,
  catalog: readonly P6FieldCatalogEntry[] = [],
): WorkspaceReportPrintSelection {
  const orderedColumns = layout
    ? catalog.length
      ? projectGridColumns(layout, catalog).map(({ fieldId, label, dataType, editable, formula, width }) => ({
          id: fieldId,
          label,
          dataType,
          editable,
          formula,
          width,
        }))
      : [...layout.columns]
          .sort((a, b) => a.order - b.order)
          .filter((column) => column.visible)
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
