/**
 * P6-3 client foundation.
 *
 * The client consumes field metadata and formula validation/dependency/type
 * results supplied by authoritative shared contracts/APIs. It does not own a
 * field catalog, formula parser/evaluator, or scheduling calculations.
 */

export type P6FieldDataType =
  | "string" | "date" | "datetime" | "duration" | "decimal" | "percentage"
  | "boolean" | "enum" | "integer" | "double" | "cost" | "unit"
  | "object-id" | "object-id-array" | "string-array" | "complex" | "spread";

export type P6Field = {
  field_id: string;
  subject_area: string;
  p6_field: string;
  display_name: string;
  data_type: P6FieldDataType;
  writable: boolean;
  computed: boolean;
  disposition: string;
  unit?: string | null;
  filterable?: boolean | null;
  orderable?: boolean | null;
  nullable?: boolean | null;
};

export type FieldRegistry = {
  registry_version: "p6-field-registry.v1";
  reference_product: "Oracle Primavera P6 Professional";
  reference_version: string;
  status: string;
  fields: readonly P6Field[];
};

export type ColumnPresentation = {
  field_id: string;
  visible: boolean;
  order: number;
  label?: string | null;
  width: number;
  alignment: "start" | "center" | "end";
  pinned: boolean;
  frozen: boolean;
};

export type LayoutScope = "global" | "project" | "user";

export type LayoutDefinition = {
  schema_version: "p6-layout.v1";
  scope: LayoutScope;
  view_id: string;
  revision: number;
  columns: readonly ColumnPresentation[];
};

export type FormulaValidationResult = {
  valid: boolean;
  error_code: string | null;
  message_key: string | null;
};

export type FormulaDependencyResult = {
  field_ids: readonly string[];
};

export type FormulaTypeResult = {
  data_type: P6FieldDataType;
};

export type FormulaAuthoritativeResult = {
  validation: FormulaValidationResult;
  dependencies: FormulaDependencyResult;
  result_type: FormulaTypeResult;
};

export type FormulaEditorModel = {
  field_id: string;
  expression: string;
  authoritative: FormulaAuthoritativeResult | null;
};

export type P6FieldRegistryProvider = {
  getFields(subjectArea?: string): Promise<readonly P6Field[]>;
};

export type P6LayoutPersistence = {
  load(scope: LayoutScope, viewId: string): Promise<LayoutDefinition | null>;
  save(layout: LayoutDefinition): Promise<LayoutDefinition>;
};

export type P6FormulaAuthority = {
  validate(expression: string, contextFieldId?: string): Promise<FormulaAuthoritativeResult>;
};

export function createColumnPresentation(
  field: P6Field,
  order: number,
  overrides: Partial<Omit<ColumnPresentation, "field_id" | "order">> = {},
): ColumnPresentation {
  return {
    field_id: field.field_id,
    visible: true,
    order,
    width: 120,
    alignment: field.data_type === "string" ? "start" : "end",
    pinned: false,
    frozen: false,
    ...overrides,
  };
}

export function addField(
  layout: LayoutDefinition,
  field: P6Field,
  overrides: Partial<Omit<ColumnPresentation, "field_id" | "order">> = {},
): LayoutDefinition {
  if (layout.columns.some((column) => column.field_id === field.field_id)) {
    throw new Error("FIELD_ALREADY_IN_LAYOUT");
  }
  return normalizeLayout({
    ...layout,
    revision: layout.revision + 1,
    columns: [...layout.columns, createColumnPresentation(field, layout.columns.length, overrides)],
  });
}

export function removeField(layout: LayoutDefinition, fieldId: string): LayoutDefinition {
  return normalizeLayout({
    ...layout,
    revision: layout.revision + 1,
    columns: layout.columns.filter((column) => column.field_id !== fieldId),
  });
}

export function updateFieldPresentation(
  layout: LayoutDefinition,
  fieldId: string,
  patch: Partial<Omit<ColumnPresentation, "field_id">>,
): LayoutDefinition {
  let found = false;
  const columns = layout.columns.map((column) => {
    if (column.field_id !== fieldId) return column;
    found = true;
    return { ...column, ...patch };
  });
  if (!found) throw new Error("FIELD_NOT_IN_LAYOUT");
  return normalizeLayout({ ...layout, revision: layout.revision + 1, columns });
}

export function reorderFields(layout: LayoutDefinition, orderedFieldIds: readonly string[]): LayoutDefinition {
  const current = new Set(layout.columns.map((column) => column.field_id));
  if (current.size !== orderedFieldIds.length || orderedFieldIds.some((id) => !current.has(id))) {
    throw new Error("INVALID_LAYOUT_ORDER");
  }
  const byId = new Map(layout.columns.map((column) => [column.field_id, column]));
  return normalizeLayout({
    ...layout,
    revision: layout.revision + 1,
    columns: orderedFieldIds.map((id, order) => ({ ...byId.get(id)!, order })),
  });
}

export function applyFormulaAuthority(
  model: FormulaEditorModel,
  result: FormulaAuthoritativeResult,
): FormulaEditorModel {
  return { ...model, authoritative: result };
}

export function normalizeLayout(layout: LayoutDefinition): LayoutDefinition {
  return {
    ...layout,
    columns: layout.columns
      .map((column, index) => ({ ...column, order: index }))
      .sort((a, b) => a.order - b.order),
  };
}
