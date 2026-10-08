export const P6_PRESENTATION_CONTRACT_ID =
  "constructionpm://contracts/p6-presentation/v1" as const;
export const P6_PRESENTATION_CONTRACT_VERSION = "1.0" as const;
export const P6_FIELD_REGISTRY_VERSION = "p6-field-registry.v1" as const;
export const P6_LAYOUT_SCHEMA_VERSION = "p6-layout.v1" as const;
export const P6_FORMULA_AUTHORITY_VERSION = "p6-formula-authority-api.v1" as const;

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
  allowed_values?: readonly string[] | null;
};

export type FieldRegistry = {
  registry_version: typeof P6_FIELD_REGISTRY_VERSION;
  reference_product: "Oracle Primavera P6 Professional";
  reference_version: string;
  status: string;
  fields: readonly P6Field[];
};

export type ColumnPresentation = {
  field_id: string;
  visible: boolean;
  order: number;
  label?: string;
  width: number;
  alignment: "start" | "center" | "end";
  pinned: boolean;
  frozen: boolean;
};

export type LayoutScope = "global" | "project" | "user";

export type LayoutDefinition = {
  schema_version: typeof P6_LAYOUT_SCHEMA_VERSION;
  scope: LayoutScope;
  view_id: string;
  revision: number;
  columns: readonly ColumnPresentation[];
  metadata?: Readonly<Record<string, unknown>>;
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

export type P6PresentationBundle = Readonly<{
  contract_version: typeof P6_PRESENTATION_CONTRACT_VERSION;
  registry: FieldRegistry;
  layout: LayoutDefinition;
  formula_authoritative: FormulaAuthoritativeResult;
}>;

export type P6PresentationAdapter = Readonly<{
  validate(bundle: P6PresentationBundle): P6PresentationBundle;
  normalizeLayout(layout: LayoutDefinition): LayoutDefinition;
}>;

function requireNonEmpty(value: unknown, error: string): asserts value is string {
  if (typeof value !== "string" || !value.trim()) throw new Error(error);
}

const FIELD_TYPES: ReadonlySet<string> = new Set([
  "string", "date", "datetime", "duration", "decimal", "percentage",
  "boolean", "enum", "integer", "double", "cost", "unit",
  "object-id", "object-id-array", "string-array", "complex", "spread",
]);

function validateField(field: P6Field): void {
  requireNonEmpty(field.field_id, "INVALID_P6_FIELD_ID");
  requireNonEmpty(field.subject_area, "INVALID_P6_FIELD_SUBJECT_AREA");
  requireNonEmpty(field.p6_field, "INVALID_P6_FIELD_NAME");
  requireNonEmpty(field.display_name, "INVALID_P6_FIELD_DISPLAY_NAME");
  if (!FIELD_TYPES.has(field.data_type)) throw new Error("INVALID_P6_FIELD_DATA_TYPE");
  requireNonEmpty(field.disposition, "INVALID_P6_FIELD_DISPOSITION");
  if (typeof field.writable !== "boolean" || typeof field.computed !== "boolean") {
    throw new Error("INVALID_P6_FIELD_FLAGS");
  }
  if (field.allowed_values !== undefined && field.allowed_values !== null) {
    if (!Array.isArray(field.allowed_values) || field.allowed_values.some((value) => typeof value !== "string")) {
      throw new Error("INVALID_P6_FIELD_ALLOWED_VALUES");
    }
  }
}

export function validateFieldRegistry(registry: FieldRegistry): FieldRegistry {
  if (registry.registry_version !== P6_FIELD_REGISTRY_VERSION) {
    throw new Error("INVALID_P6_FIELD_REGISTRY_VERSION");
  }
  if (registry.reference_product !== "Oracle Primavera P6 Professional") {
    throw new Error("INVALID_P6_FIELD_REGISTRY_PRODUCT");
  }
  requireNonEmpty(registry.reference_version, "INVALID_P6_FIELD_REGISTRY_REFERENCE");
  requireNonEmpty(registry.status, "INVALID_P6_FIELD_REGISTRY_STATUS");
  if (!Array.isArray(registry.fields)) throw new Error("INVALID_P6_FIELD_REGISTRY_FIELDS");
  const ids = new Set<string>();
  for (const field of registry.fields) {
    if (ids.has(field.field_id)) throw new Error("DUPLICATE_P6_FIELD_ID");
    ids.add(field.field_id);
    validateField(field);
  }
  return registry;
}

export function validateLayout(layout: LayoutDefinition, registry?: FieldRegistry): LayoutDefinition {
  if (layout.schema_version !== P6_LAYOUT_SCHEMA_VERSION) {
    throw new Error("INVALID_P6_LAYOUT_SCHEMA");
  }
  if (!["global", "project", "user"].includes(layout.scope)) {
    throw new Error("INVALID_P6_LAYOUT_SCOPE");
  }
  requireNonEmpty(layout.view_id, "INVALID_P6_LAYOUT_VIEW");
  if (!Number.isInteger(layout.revision) || layout.revision < 0) {
    throw new Error("INVALID_P6_LAYOUT_REVISION");
  }
  if (!Array.isArray(layout.columns)) throw new Error("INVALID_P6_LAYOUT_COLUMNS");
  const fieldIds = new Set(registry?.fields.map((field) => field.field_id));
  const seen = new Set<string>();
  for (const column of layout.columns) {
    requireNonEmpty(column.field_id, "INVALID_P6_COLUMN_FIELD");
    if (seen.has(column.field_id)) throw new Error("DUPLICATE_P6_COLUMN_FIELD");
    seen.add(column.field_id);
    if (registry && !fieldIds.has(column.field_id)) throw new Error("P6_COLUMN_FIELD_NOT_IN_REGISTRY");
    if (!Number.isInteger(column.order) || column.order < 0) throw new Error("INVALID_P6_COLUMN_ORDER");
    if (typeof column.visible !== "boolean" || typeof column.pinned !== "boolean" || typeof column.frozen !== "boolean") {
      throw new Error("INVALID_P6_COLUMN_FLAGS");
    }
    if (!Number.isFinite(column.width) || column.width <= 0) throw new Error("INVALID_P6_COLUMN_WIDTH");
    if (!["start", "center", "end"].includes(column.alignment)) {
      throw new Error("INVALID_P6_COLUMN_ALIGNMENT");
    }
  }
  return layout;
}

export function validateFormulaAuthoritativeResult(
  result: FormulaAuthoritativeResult,
): FormulaAuthoritativeResult {
  if (typeof result.validation?.valid !== "boolean") throw new Error("INVALID_P6_FORMULA_VALIDATION");
  if (result.validation.error_code !== null && typeof result.validation.error_code !== "string") {
    throw new Error("INVALID_P6_FORMULA_ERROR_CODE");
  }
  if (result.validation.message_key !== null && typeof result.validation.message_key !== "string") {
    throw new Error("INVALID_P6_FORMULA_MESSAGE_KEY");
  }
  if (!Array.isArray(result.dependencies?.field_ids) ||
      result.dependencies.field_ids.some((id) => typeof id !== "string" || !id.trim())) {
    throw new Error("INVALID_P6_FORMULA_DEPENDENCIES");
  }
  if (!FIELD_TYPES.has(result.result_type?.data_type)) {
    throw new Error("INVALID_P6_FORMULA_RESULT_TYPE");
  }
  return result;
}

export function validateP6PresentationBundle(bundle: P6PresentationBundle): P6PresentationBundle {
  if (bundle.contract_version !== P6_PRESENTATION_CONTRACT_VERSION) {
    throw new Error("INVALID_P6_PRESENTATION_CONTRACT_VERSION");
  }
  const registry = validateFieldRegistry(bundle.registry);
  validateLayout(bundle.layout, registry);
  validateFormulaAuthoritativeResult(bundle.formula_authoritative);
  return bundle;
}

export function normalizeLayout(layout: LayoutDefinition): LayoutDefinition {
  return {
    ...layout,
    columns: [...layout.columns]
      .sort((a, b) => a.order - b.order)
      .map((column, index) => ({ ...column, order: index })),
  };
}

export function createColumnPresentation(
  field: P6Field,
  order: number,
  overrides: Partial<Omit<ColumnPresentation, "field_id" | "order">> = {},
): ColumnPresentation {
  validateField(field);
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
  const existing = layout.columns.find((column) => column.field_id === field.field_id);
  if (existing) {
    if (existing.visible) throw new Error("FIELD_ALREADY_IN_LAYOUT");
    return updateFieldPresentation(layout, field.field_id, { visible: true, ...overrides });
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
  const requested = new Set(orderedFieldIds);
  if (
    current.size !== orderedFieldIds.length ||
    requested.size !== current.size ||
    orderedFieldIds.some((id) => !current.has(id))
  ) {
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
  return { ...model, authoritative: validateFormulaAuthoritativeResult(result) };
}

export function createP6PresentationAdapter(): P6PresentationAdapter {
  return {
    validate: validateP6PresentationBundle,
    normalizeLayout: (layout) => normalizeLayout(validateLayout(layout)),
  };
}
