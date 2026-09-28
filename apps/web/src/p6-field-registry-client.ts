export const P6_FIELD_REGISTRY_API_VERSION = "p6-field-registry-api.v1" as const;

export type P6FieldDataType =
  | "string" | "date" | "datetime" | "duration" | "decimal" | "percentage"
  | "boolean" | "enum" | "integer" | "double" | "cost" | "unit"
  | "object-id" | "object-id-array" | "string-array" | "complex" | "spread";

export type P6FieldRegistryDTO = Readonly<{
  contract_version: typeof P6_FIELD_REGISTRY_API_VERSION;
  kind: "field";
  scope: Readonly<{ tenant_id: string; project_id: string; project_revision: number }>;
  registry_version: string;
  field: Readonly<{
    field_id: string;
    subject_area: string;
    p6_field: string;
    display_name: string;
    data_type: P6FieldDataType;
    writable: boolean;
    computed: boolean;
    unit: string | null;
  }>;
}>;

export type P6UserDefinedFieldDTO = Readonly<{
  contract_version: typeof P6_FIELD_REGISTRY_API_VERSION;
  kind: "user_defined_field";
  scope: Readonly<{ tenant_id: string; project_id: string; project_revision: number }>;
  registry_version: string;
  udf: Readonly<{
    udf_id: string;
    subject_area: string;
    display_name: string;
    data_type: P6FieldDataType;
    writable: boolean;
    nullable: boolean;
    unit: string | null;
    allowed_values: readonly string[];
  }>;
}>;

export type P6FieldCatalogEntry = Readonly<{
  id: string;
  source: "standard" | "udf";
  subjectArea: string;
  label: string;
  dataType: P6FieldDataType;
  writable: boolean;
  computed: boolean;
  unit: string | null;
  nullable: boolean | null;
  allowedValues: readonly string[];
  p6Field: string;
  filterable: boolean;
  orderable: boolean;
}>;

export function projectFieldCatalogEntry(dto: P6FieldRegistryDTO): P6FieldCatalogEntry {
  assertFieldScope(dto);
  if (dto.kind !== "field" || dto.contract_version !== P6_FIELD_REGISTRY_API_VERSION) {
    throw new Error("UNSUPPORTED_P6_FIELD_REGISTRY_CONTRACT");
  }
  assertNonEmpty(dto.field.field_id, "INVALID_P6_FIELD_ID");
  assertNonEmpty(dto.field.display_name, "INVALID_P6_FIELD_DISPLAY_NAME");
  return Object.freeze({
    id: dto.field.field_id,
    source: "standard",
    subjectArea: dto.field.subject_area,
    label: dto.field.display_name,
    dataType: dto.field.data_type,
    writable: dto.field.writable,
    computed: dto.field.computed,
    unit: dto.field.unit,
    nullable: null,
    allowedValues: Object.freeze([]),
    p6Field: dto.field.p6_field,
    filterable: true,
    orderable: true,
  });
}

export function projectUdfCatalogEntry(dto: P6UserDefinedFieldDTO): P6FieldCatalogEntry {
  assertFieldScope(dto);
  if (dto.kind !== "user_defined_field" || dto.contract_version !== P6_FIELD_REGISTRY_API_VERSION) {
    throw new Error("UNSUPPORTED_P6_FIELD_REGISTRY_CONTRACT");
  }
  assertNonEmpty(dto.udf.udf_id, "INVALID_P6_UDF_ID");
  assertNonEmpty(dto.udf.display_name, "INVALID_P6_UDF_DISPLAY_NAME");
  return Object.freeze({
    id: dto.udf.udf_id,
    source: "udf",
    subjectArea: dto.udf.subject_area,
    label: dto.udf.display_name,
    dataType: dto.udf.data_type,
    writable: dto.udf.writable,
    computed: false,
    unit: dto.udf.unit,
    nullable: dto.udf.nullable,
    allowedValues: Object.freeze([...dto.udf.allowed_values]),
    p6Field: dto.udf.udf_id,
    filterable: true,
    orderable: true,
  });
}

function assertFieldScope(dto: P6FieldRegistryDTO | P6UserDefinedFieldDTO): void {
  if (!dto.scope.tenant_id || !dto.scope.project_id || !Number.isInteger(dto.scope.project_revision) || dto.scope.project_revision < 0) {
    throw new Error("INVALID_P6_FIELD_SCOPE");
  }
  if (!dto.registry_version) throw new Error("INVALID_P6_FIELD_REGISTRY_VERSION");
}

function assertNonEmpty(value: string, code: string): void {
  if (!value.trim()) throw new Error(code);
}
