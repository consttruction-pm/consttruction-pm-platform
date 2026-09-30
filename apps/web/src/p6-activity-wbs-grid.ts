import {
  FieldRegistry,
  LayoutDefinition,
  P6Field,
  addField,
  removeField,
  updateFieldPresentation,
  reorderFields,
} from "./p6-field-layout-foundation";

export type P6GridViewId = "activity" | "wbs";

export type P6GridSortDirection = "ascending" | "descending";

export interface P6GridSort {
  field_id: string;
  direction: P6GridSortDirection;
  order: number;
}

export interface P6GridGroup {
  field_id: string;
  order: number;
}

export interface P6GridFilter {
  field_id: string;
  operator:
    | "equals"
    | "not-equals"
    | "contains"
    | "starts-with"
    | "ends-with"
    | "greater-than"
    | "greater-than-or-equal"
    | "less-than"
    | "less-than-or-equal"
    | "is-empty"
    | "is-not-empty";
  value?: unknown;
}

export interface P6GridState {
  view_id: P6GridViewId;
  layout: LayoutDefinition;
  sorts: P6GridSort[];
  groups: P6GridGroup[];
  filters: P6GridFilter[];
}

export interface P6GridDataSource {
  readonly view_id: P6GridViewId;
  getRows(): readonly Record<string, unknown>[];
}

export interface P6GridSelectionHooks {
  onLayoutChange(layout: LayoutDefinition): void;
  onSortChange(sorts: readonly P6GridSort[]): void;
  onGroupChange(groups: readonly P6GridGroup[]): void;
  onFilterChange(filters: readonly P6GridFilter[]): void;
  onPrintFieldsChange(field_ids: readonly string[]): void;
}

export interface P6GridPresentationModel {
  view_id: P6GridViewId;
  fields: readonly P6Field[];
  layout: LayoutDefinition;
  sorts: readonly P6GridSort[];
  groups: readonly P6GridGroup[];
  filters: readonly P6GridFilter[];
}

function assertView(view_id: P6GridViewId): void {
  if (view_id !== "activity" && view_id !== "wbs") {
    throw new Error(`Unsupported P6 grid view: ${view_id}`);
  }
}

function assertField(registry: FieldRegistry, field_id: string): P6Field {
  const field = registry.fields.find((candidate) => candidate.field_id === field_id);
  if (!field) {
    throw new Error(`Unknown P6 field: ${field_id}`);
  }
  return field;
}

function normalizeOrder<T extends { order: number }>(items: readonly T[]): T[] {
  return [...items]
    .sort((a, b) => a.order - b.order)
    .map((item, order) => ({ ...item, order }));
}

export function createP6GridPresentation(
  view_id: P6GridViewId,
  registry: FieldRegistry,
  layout: LayoutDefinition,
  sorts: readonly P6GridSort[] = [],
  groups: readonly P6GridGroup[] = [],
  filters: readonly P6GridFilter[] = [],
): P6GridPresentationModel {
  assertView(view_id);
  const fields = layout.columns
    .map((column) => assertField(registry, column.field_id))
    .filter((field) => field.field_id.length > 0);

  return {
    view_id,
    fields,
    layout,
    sorts: normalizeOrder(sorts),
    groups: normalizeOrder(groups),
    filters: [...filters],
  };
}

export function addGridField(
  registry: FieldRegistry,
  layout: LayoutDefinition,
  field_id: string,
): LayoutDefinition {
  assertField(registry, field_id);
  return addField(layout, field_id);
}

export function removeGridField(
  registry: FieldRegistry,
  layout: LayoutDefinition,
  field_id: string,
): LayoutDefinition {
  assertField(registry, field_id);
  return removeField(layout, field_id);
}

export function updateGridField(
  registry: FieldRegistry,
  layout: LayoutDefinition,
  field_id: string,
  patch: Parameters<typeof updateFieldPresentation>[2],
): LayoutDefinition {
  assertField(registry, field_id);
  return updateFieldPresentation(layout, field_id, patch);
}

export function reorderGridFields(
  registry: FieldRegistry,
  layout: LayoutDefinition,
  field_ids: readonly string[],
): LayoutDefinition {
  for (const field_id of field_ids) {
    assertField(registry, field_id);
  }
  return reorderFields(layout, field_ids);
}

export function setGridSorts(
  registry: FieldRegistry,
  sorts: readonly P6GridSort[],
): P6GridSort[] {
  for (const sort of sorts) {
    assertField(registry, sort.field_id);
  }
  return normalizeOrder(sorts);
}

export function setGridGroups(
  registry: FieldRegistry,
  groups: readonly P6GridGroup[],
): P6GridGroup[] {
  for (const group of groups) {
    assertField(registry, group.field_id);
  }
  return normalizeOrder(groups);
}

export function setGridFilters(
  registry: FieldRegistry,
  filters: readonly P6GridFilter[],
): P6GridFilter[] {
  for (const filter of filters) {
    assertField(registry, filter.field_id);
  }
  return [...filters];
}
